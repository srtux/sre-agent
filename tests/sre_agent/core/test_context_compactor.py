"""Tests for the Context Compactor."""

import json

import pytest

from sre_agent.core.context_compactor import (
    CompactionConfig,
    ContextCompactor,
    WorkingContext,
    get_context_compactor,
)
from sre_agent.core.prompt_composer import SessionSummary


class TestCompactionConfig:
    """Tests for CompactionConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = CompactionConfig()

        assert config.token_budget == 32000
        assert config.compaction_trigger_tokens == 24000
        assert config.recent_events_count == 5
        assert config.min_events_for_compaction == 10
        assert config.chars_per_token == 4


class TestContextCompactor:
    """Tests for ContextCompactor."""

    @pytest.fixture
    def compactor(self) -> ContextCompactor:
        """Create a compactor with small thresholds for testing."""
        config = CompactionConfig(
            token_budget=1000,
            compaction_trigger_tokens=500,
            recent_events_count=3,
            min_events_for_compaction=5,
            chars_per_token=4,
        )
        return ContextCompactor(config=config)

    def test_get_working_context_empty(self, compactor: ContextCompactor) -> None:
        """Test getting working context with no events."""
        context = compactor.get_working_context(
            session_id="test-session",
            events=[],
        )

        assert isinstance(context, WorkingContext)
        assert context.recent_events == []
        assert context.compaction_applied is False

    def test_get_working_context_few_events(self, compactor: ContextCompactor) -> None:
        """Test getting working context with few events (no compaction)."""
        events = [
            {"type": "user_message", "content": "Hello"},
            {"type": "model_thought", "content": "Thinking..."},
        ]

        context = compactor.get_working_context(
            session_id="test-session",
            events=events,
        )

        assert len(context.recent_events) == 2
        assert context.compaction_applied is False

    def test_get_working_context_with_compaction(
        self, compactor: ContextCompactor
    ) -> None:
        """Test getting working context with compaction triggered."""
        # Create events that exceed compaction threshold
        events = []
        for _ in range(20):
            events.append(
                {
                    "type": "tool_output",
                    "content": json.dumps(
                        {"status": "success", "result": {"data": "x" * 200}}
                    ),
                }
            )

        context = compactor.get_working_context(
            session_id="test-session",
            events=events,
        )

        # Should have compaction applied
        assert context.compaction_applied is True
        # Recent events should be limited
        assert len(context.recent_events) <= compactor.config.recent_events_count

    def test_recent_events_are_newest(self, compactor: ContextCompactor) -> None:
        """Test that recent events are the newest ones."""
        events = [
            {"type": "user_message", "content": "First message", "order": 1},
            {"type": "user_message", "content": "Second message", "order": 2},
            {"type": "user_message", "content": "Third message", "order": 3},
            {"type": "user_message", "content": "Fourth message", "order": 4},
            {"type": "user_message", "content": "Fifth message", "order": 5},
        ]

        context = compactor.get_working_context(
            session_id="test-session",
            events=events,
        )

        # Recent events should be the last 3 (based on config)
        assert len(context.recent_events) == 3
        assert context.recent_events[-1]["content"] == "Fifth message"
        assert context.recent_events[0]["content"] == "Third message"

    def test_should_compact_below_threshold(self, compactor: ContextCompactor) -> None:
        """Test should_compact returns False below threshold."""
        events = [{"type": "user_message", "content": "Short"}]

        assert compactor.should_compact(events) is False

    def test_should_compact_above_threshold(self, compactor: ContextCompactor) -> None:
        """Test should_compact returns True above threshold."""
        # Create events that exceed threshold
        events = []
        for _ in range(15):
            events.append(
                {"type": "tool_output", "content": json.dumps({"data": "x" * 500})}
            )

        assert compactor.should_compact(events) is True

    def test_should_compact_respects_min_events(
        self, compactor: ContextCompactor
    ) -> None:
        """Test should_compact respects minimum events requirement."""
        # Create 3 events with lots of content (below min_events_for_compaction=5)
        events = [
            {"type": "tool_output", "content": json.dumps({"data": "x" * 5000})}
            for _ in range(3)
        ]

        assert compactor.should_compact(events) is False

    def test_existing_summary_preserved(self, compactor: ContextCompactor) -> None:
        """Test that existing summary is used when available."""
        existing_summary = SessionSummary(
            summary_text="Previous investigation summary",
            key_findings=["Found bottleneck"],
            tools_used=["fetch_trace"],
            last_compaction_turn=5,
        )

        events = [{"type": "user_message", "content": "Hello"} for _ in range(8)]

        context = compactor.get_working_context(
            session_id="test-session",
            events=events,
            existing_summary=existing_summary,
        )

        assert "Previous investigation" in context.summary.summary_text

    def test_get_compaction_stats(self, compactor: ContextCompactor) -> None:
        """Test getting compaction statistics."""
        # First, trigger a compaction
        events = [
            {"type": "tool_output", "content": json.dumps({"data": "x" * 500})}
            for _ in range(15)
        ]

        compactor.get_working_context(session_id="test-session", events=events)

        stats = compactor.get_compaction_stats("test-session")

        assert "last_compaction" in stats
        assert "events_compacted" in stats
        assert "summary_tokens" in stats

    def test_clear_session(self, compactor: ContextCompactor) -> None:
        """Test clearing session state."""
        # Create some state
        events = [
            {"type": "tool_output", "content": json.dumps({"data": "x" * 500})}
            for _ in range(15)
        ]
        compactor.get_working_context(session_id="test-session", events=events)

        # Clear it
        compactor.clear_session("test-session")

        # Stats should be empty
        stats = compactor.get_compaction_stats("test-session")
        assert stats["events_compacted"] == 0

    def test_token_estimation(self, compactor: ContextCompactor) -> None:
        """Test token estimation accuracy."""
        # 100 characters should be ~25 tokens with 4 chars/token
        events = [{"type": "user_message", "content": "x" * 100}]

        tokens = compactor._estimate_tokens(events)

        assert tokens == 25

    def test_incremental_compaction(self, compactor: ContextCompactor) -> None:
        """Test incremental compaction with existing summary."""
        existing_summary = SessionSummary(
            summary_text="First half of investigation",
            key_findings=["Finding 1"],
            tools_used=["tool1"],
            last_compaction_turn=10,
        )

        # Add more events than the last compaction point
        events = [
            {"type": "tool_output", "content": json.dumps({"data": "x" * 500})}
            for _ in range(20)
        ]

        context = compactor.get_working_context(
            session_id="test-session",
            events=events,
            existing_summary=existing_summary,
        )

        # Should have merged summaries
        assert "First half" in context.summary.summary_text
        assert "Subsequent" in context.summary.summary_text


class TestContextCompactorSingleton:
    """Tests for singleton access."""

    def test_get_context_compactor_singleton(self) -> None:
        """Test that get_context_compactor returns singleton."""
        compactor1 = get_context_compactor()
        compactor2 = get_context_compactor()

        assert compactor1 is compactor2


class TestWorkingContext:
    """Tests for WorkingContext dataclass."""

    def test_working_context_creation(self) -> None:
        """Test creating a working context."""
        summary = SessionSummary(summary_text="Test summary")
        context = WorkingContext(
            summary=summary,
            recent_events=[{"type": "user_message", "content": "Hello"}],
            total_token_estimate=100,
            compaction_applied=True,
            last_compaction_timestamp="2026-01-25T10:00:00Z",
        )

        assert context.summary.summary_text == "Test summary"
        assert len(context.recent_events) == 1
        assert context.total_token_estimate == 100
        assert context.compaction_applied is True
