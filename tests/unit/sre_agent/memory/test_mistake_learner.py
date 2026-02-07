"""Tests for the MistakeLearner — mistake capture and self-correction detection."""

from unittest.mock import AsyncMock, patch

import pytest

from sre_agent.memory.mistake_learner import MistakeLearner, _RecentFailure
from sre_agent.memory.mistake_store import MistakeMemoryStore
from sre_agent.schema import MistakeCategory


@pytest.fixture
def store() -> MistakeMemoryStore:
    """Create a fresh in-memory MistakeMemoryStore."""
    return MistakeMemoryStore()


@pytest.fixture
def learner(store: MistakeMemoryStore) -> MistakeLearner:
    """Create a learner backed by the store."""
    return MistakeLearner(store=store)


class TestOnToolFailure:
    """Tests for capturing mistakes from tool failures."""

    @pytest.mark.asyncio
    async def test_records_learnable_failure(self, learner: MistakeLearner) -> None:
        with (
            patch.object(learner, "_recent_failures", {}),
            patch("sre_agent.memory.factory.get_memory_manager"),
        ):
            await learner.on_tool_failure(
                tool_name="list_log_entries",
                args={"filter": 'container_name="app"'},
                error_message="Invalid filter expression: missing quotes around value",
                session_id="sess-1",
                user_id="user@example.com",
            )

            # Verify stored in session cache
            records = await learner.store.get_mistakes_for_tool("list_log_entries")
            assert len(records) == 1
            assert records[0].category == MistakeCategory.INVALID_FILTER

    @pytest.mark.asyncio
    async def test_ignores_transient_errors(self, learner: MistakeLearner) -> None:
        await learner.on_tool_failure(
            tool_name="fetch_trace",
            args={"trace_id": "abc"},
            error_message="Connection timeout after 30s",
        )

        records = await learner.store.get_mistakes_for_tool("fetch_trace")
        assert len(records) == 0

    @pytest.mark.asyncio
    async def test_buffers_recent_failure(self, learner: MistakeLearner) -> None:
        with patch("sre_agent.memory.factory.get_memory_manager"):
            await learner.on_tool_failure(
                tool_name="query_promql",
                args={"query": "bad(query"},
                error_message="syntax error in expression",
            )

        assert "query_promql" in learner._recent_failures
        assert len(learner._recent_failures["query_promql"]) == 1

    @pytest.mark.asyncio
    async def test_caps_recent_failures(self, learner: MistakeLearner) -> None:
        with patch("sre_agent.memory.factory.get_memory_manager"):
            for i in range(10):
                await learner.on_tool_failure(
                    tool_name="tool_a",
                    args={"i": i},
                    error_message=f"invalid filter #{i}",
                )

        # Should be capped at _MAX_RECENT_FAILURES (5)
        assert len(learner._recent_failures["tool_a"]) <= 5


class TestOnToolSuccess:
    """Tests for self-correction detection."""

    @pytest.mark.asyncio
    async def test_detects_self_correction(self, learner: MistakeLearner) -> None:
        with patch("sre_agent.memory.factory.get_memory_manager"):
            # First, record a failure
            await learner.on_tool_failure(
                tool_name="list_log_entries",
                args={"filter": 'container_name="app"'},
                error_message="Invalid filter: use prefix",
            )

            # Then, record a success with corrected args
            await learner.on_tool_success(
                tool_name="list_log_entries",
                args={"filter": 'resource.labels.container_name="app"'},
                session_id="sess-1",
                user_id="user@example.com",
            )

        # Verify the correction was recorded
        corrected = await learner.store.get_corrected_mistakes()
        assert len(corrected) == 1
        assert corrected[0].correction is not None
        assert "filter" in corrected[0].correction

    @pytest.mark.asyncio
    async def test_no_correction_without_prior_failure(
        self, learner: MistakeLearner
    ) -> None:
        await learner.on_tool_success(
            tool_name="fetch_trace",
            args={"trace_id": "abc"},
        )

        corrected = await learner.store.get_corrected_mistakes()
        assert len(corrected) == 0

    @pytest.mark.asyncio
    async def test_correction_pops_failure_from_buffer(
        self, learner: MistakeLearner
    ) -> None:
        with patch("sre_agent.memory.factory.get_memory_manager"):
            await learner.on_tool_failure(
                tool_name="tool_a",
                args={"q": "bad"},
                error_message="invalid filter expression",
            )
            assert len(learner._recent_failures["tool_a"]) == 1

            await learner.on_tool_success(
                tool_name="tool_a",
                args={"q": "good"},
            )
            assert len(learner._recent_failures["tool_a"]) == 0


class TestOnToolException:
    """Tests for exception-based mistake capture."""

    @pytest.mark.asyncio
    async def test_records_learnable_exception(self, learner: MistakeLearner) -> None:
        with patch("sre_agent.memory.factory.get_memory_manager"):
            error = ValueError("invalid_argument: unknown metric type")
            await learner.on_tool_exception(
                tool_name="query_promql",
                args={"query": "rate(bad_metric[5m])"},
                error=error,
            )

        records = await learner.store.get_mistakes_for_tool("query_promql")
        assert len(records) == 1
        assert "ValueError" in records[0].error_message

    @pytest.mark.asyncio
    async def test_ignores_transient_exception(self, learner: MistakeLearner) -> None:
        error = ConnectionError("Connection refused")
        await learner.on_tool_exception(
            tool_name="fetch_trace",
            args={},
            error=error,
        )

        records = await learner.store.get_mistakes_for_tool("fetch_trace")
        assert len(records) == 0


class TestDescribeCorrection:
    """Tests for correction description generation."""

    def test_describes_arg_changes(self, learner: MistakeLearner) -> None:
        failure = _RecentFailure(
            tool_name="list_log_entries",
            error_message="Invalid filter",
            category=MistakeCategory.INVALID_FILTER,
            args={"filter": 'container_name="app"'},
        )
        description = learner._describe_correction(
            failure,
            {"filter": 'resource.labels.container_name="app"'},
        )
        assert "filter" in description
        assert "Invalid filter" in description

    def test_handles_no_changes(self, learner: MistakeLearner) -> None:
        failure = _RecentFailure(
            tool_name="tool_a",
            error_message="some error",
            category=MistakeCategory.OTHER,
            args={"q": "same"},
        )
        description = learner._describe_correction(failure, {"q": "same"})
        assert "different approach" in description


class TestNeverBreaks:
    """Ensure the learner never breaks tool execution."""

    @pytest.mark.asyncio
    async def test_failure_never_raises(self) -> None:
        """Even with a broken store, on_tool_failure should not raise."""
        learner = MistakeLearner(store=None)
        # Force store access to fail
        with patch(
            "sre_agent.memory.mistake_learner.get_mistake_store",
            side_effect=RuntimeError("boom"),
        ):
            # This should not raise
            learner._store = None
            await learner.on_tool_failure(
                tool_name="tool_a",
                args={},
                error_message="invalid filter expression",
            )

    @pytest.mark.asyncio
    async def test_success_never_raises(self, learner: MistakeLearner) -> None:
        """on_tool_success should not raise even with internal errors."""
        # Add a failure manually so there's something to pop
        learner._recent_failures["tool_a"].append(
            _RecentFailure("tool_a", "err", MistakeCategory.OTHER, {})
        )

        with patch.object(
            learner.store,
            "record_correction",
            new_callable=AsyncMock,
            side_effect=RuntimeError("boom"),
        ):
            # Should not raise
            await learner.on_tool_success(
                tool_name="tool_a",
                args={"q": "good"},
            )
