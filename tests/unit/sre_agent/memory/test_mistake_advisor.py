"""Tests for the MistakeAdvisor — pre-tool guidance and prompt lessons."""

from unittest.mock import patch

import pytest

from sre_agent.memory.mistake_advisor import (
    MistakeAdvisor,
    format_lesson,
    format_tool_advice,
)
from sre_agent.memory.mistake_store import MistakeMemoryStore
from sre_agent.schema import MistakeCategory, MistakeRecord

# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def store() -> MistakeMemoryStore:
    """Create a fresh in-memory MistakeMemoryStore."""
    return MistakeMemoryStore()


@pytest.fixture
def advisor(store: MistakeMemoryStore) -> MistakeAdvisor:
    """Create an advisor backed by the store."""
    return MistakeAdvisor(store=store)


def _make_record(
    tool_name: str = "list_log_entries",
    category: MistakeCategory = MistakeCategory.INVALID_FILTER,
    error_message: str = "Invalid filter: missing prefix",
    correction: str | None = None,
    occurrence_count: int = 3,
) -> MistakeRecord:
    """Helper to create a MistakeRecord for testing."""
    return MistakeRecord(
        tool_name=tool_name,
        category=category,
        error_message=error_message,
        failed_args={"filter": 'container_name="app"'},
        correction=correction,
        corrected_args={"filter": 'resource.labels.container_name="app"'}
        if correction
        else None,
        occurrence_count=occurrence_count,
        first_seen="2026-01-01T00:00:00Z",
        last_seen="2026-02-01T00:00:00Z",
        fingerprint="abc123",
    )


# ── Unit Tests: Format Functions ──────────────────────────────────────


class TestFormatLesson:
    """Tests for format_lesson output."""

    def test_with_correction(self) -> None:
        record = _make_record(
            correction="Use resource.labels.container_name instead of container_name"
        )
        lesson = format_lesson(record)
        assert "[list_log_entries]" in lesson
        assert "invalid_filter" in lesson
        assert "seen 3x" in lesson
        assert "resource.labels" in lesson

    def test_without_correction(self) -> None:
        record = _make_record(correction=None)
        lesson = format_lesson(record)
        assert "AVOID" in lesson
        assert "Invalid filter" in lesson

    def test_truncates_long_error(self) -> None:
        record = _make_record(error_message="x" * 200, correction=None)
        lesson = format_lesson(record)
        assert len(lesson) < 400  # Should be truncated


class TestFormatToolAdvice:
    """Tests for format_tool_advice output."""

    def test_empty_records(self) -> None:
        assert format_tool_advice([]) == ""

    def test_single_record(self) -> None:
        records = [_make_record()]
        advice = format_tool_advice(records)
        assert "PAST MISTAKES" in advice
        assert "list_log_entries" in advice
        assert "1 known pitfall" in advice

    def test_multiple_records(self) -> None:
        records = [
            _make_record(error_message="error 1"),
            _make_record(error_message="error 2"),
        ]
        advice = format_tool_advice(records)
        assert "2 known pitfall" in advice


# ── Integration Tests: Advisor Operations ─────────────────────────────


class TestGetToolAdvice:
    """Tests for get_tool_advice method."""

    @pytest.mark.asyncio
    async def test_returns_advice_for_known_tool(
        self, advisor: MistakeAdvisor, store: MistakeMemoryStore
    ) -> None:
        with patch("sre_agent.memory.factory.get_memory_manager"):
            await store.record_mistake(
                "list_log_entries",
                "Invalid filter: use prefix",
                {"filter": 'container_name="app"'},
            )

        advice = await advisor.get_tool_advice("list_log_entries")
        assert "list_log_entries" in advice
        assert "PAST MISTAKES" in advice

    @pytest.mark.asyncio
    async def test_returns_empty_for_unknown_tool(
        self, advisor: MistakeAdvisor
    ) -> None:
        advice = await advisor.get_tool_advice("never_used_tool")
        assert advice == ""


class TestGetPromptLessons:
    """Tests for get_prompt_lessons method."""

    @pytest.mark.asyncio
    async def test_returns_lessons_block(
        self, advisor: MistakeAdvisor, store: MistakeMemoryStore
    ) -> None:
        with patch("sre_agent.memory.factory.get_memory_manager"):
            await store.record_mistake(
                "list_log_entries",
                "Invalid filter: missing prefix",
                {"filter": "bad"},
            )
            await store.record_correction(
                "list_log_entries",
                "Invalid filter: missing prefix",
                "Use resource.labels prefix",
                {"filter": "good"},
            )
            await store.record_mistake(
                "query_promql",
                "syntax error in expression",
                {"query": "bad("},
            )

        lessons = await advisor.get_prompt_lessons()
        assert "Learned Lessons" in lessons
        assert "list_log_entries" in lessons
        assert "query_promql" in lessons

    @pytest.mark.asyncio
    async def test_prioritizes_corrected_mistakes(
        self, advisor: MistakeAdvisor, store: MistakeMemoryStore
    ) -> None:
        with patch("sre_agent.memory.factory.get_memory_manager"):
            # Record many uncorrected mistakes
            for i in range(10):
                await store.record_mistake(f"tool_{i}", f"invalid filter #{i}", {})

            # Record one corrected mistake
            await store.record_mistake(
                "important_tool",
                "invalid filter: critical lesson",
                {"f": "bad"},
            )
            await store.record_correction(
                "important_tool",
                "invalid filter: critical lesson",
                "This is the fix",
                {"f": "good"},
            )

        lessons = await advisor.get_prompt_lessons(limit=3)
        assert "important_tool" in lessons
        assert "This is the fix" in lessons

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_mistakes(self, advisor: MistakeAdvisor) -> None:
        lessons = await advisor.get_prompt_lessons()
        assert lessons == ""


class TestGetMistakeSummary:
    """Tests for get_mistake_summary diagnostic method."""

    @pytest.mark.asyncio
    async def test_summary_empty_store(self, advisor: MistakeAdvisor) -> None:
        summary = await advisor.get_mistake_summary()
        assert summary["total_mistakes"] == 0
        assert summary["correction_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_summary_with_data(
        self, advisor: MistakeAdvisor, store: MistakeMemoryStore
    ) -> None:
        with patch("sre_agent.memory.factory.get_memory_manager"):
            await store.record_mistake("tool_a", "invalid filter", {})
            await store.record_mistake("tool_a", "invalid filter", {})
            await store.record_mistake("tool_b", "syntax error", {})
            await store.record_correction("tool_a", "invalid filter", "fix", {})

        summary = await advisor.get_mistake_summary()
        assert summary["total_mistakes"] == 2
        assert summary["corrected_count"] == 1
        assert summary["correction_rate"] == 0.5
        assert "tool_a" in summary["top_tools"]
