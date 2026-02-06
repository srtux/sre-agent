"""Tests for ADK model callbacks for cost/token tracking.

Validates that:
- UsageTracker records model call metrics correctly
- Token budget enforcement works
- Cost estimation is accurate
- before_model_callback enforces token budgets
- after_model_callback records usage from LLM responses
- Thread safety of the usage tracker
- Singleton pattern and reset behavior
"""

import os
import threading
from unittest.mock import MagicMock, patch

import pytest

from sre_agent.core.model_callbacks import (
    ModelCallMetrics,
    UsageTracker,
    _estimate_cost,
    after_model_callback,
    before_model_callback,
    get_usage_tracker,
    reset_usage_tracker,
)


@pytest.fixture(autouse=True)
def _reset_tracker() -> None:
    """Reset the usage tracker singleton between tests."""
    reset_usage_tracker()


class TestUsageTracker:
    """Tests for the UsageTracker accumulator."""

    def test_initial_state(self) -> None:
        """Tracker should start with zero values."""
        tracker = UsageTracker()
        assert tracker.total_input_tokens == 0
        assert tracker.total_output_tokens == 0
        assert tracker.total_tokens == 0
        assert tracker.total_cost_usd == 0.0
        assert tracker.total_calls == 0

    def test_record_single_call(self) -> None:
        """Recording a single call should update all counters."""
        tracker = UsageTracker()
        metrics = ModelCallMetrics(
            agent_name="trace_panel",
            model="gemini-2.5-flash",
            input_tokens=1000,
            output_tokens=500,
            duration_ms=200.0,
            estimated_cost_usd=0.001,
        )
        tracker.record(metrics)

        assert tracker.total_input_tokens == 1000
        assert tracker.total_output_tokens == 500
        assert tracker.total_tokens == 1500
        assert tracker.total_cost_usd == 0.001
        assert tracker.total_calls == 1

    def test_record_multiple_calls(self) -> None:
        """Multiple recordings should accumulate correctly."""
        tracker = UsageTracker()
        for i in range(3):
            metrics = ModelCallMetrics(
                agent_name=f"agent_{i}",
                model="gemini-2.5-flash",
                input_tokens=100,
                output_tokens=50,
                estimated_cost_usd=0.001,
            )
            tracker.record(metrics)

        assert tracker.total_input_tokens == 300
        assert tracker.total_output_tokens == 150
        assert tracker.total_calls == 3

    def test_per_agent_tracking(self) -> None:
        """Should track per-agent statistics."""
        tracker = UsageTracker()
        tracker.record(
            ModelCallMetrics(
                agent_name="trace_panel",
                model="gemini-2.5-flash",
                input_tokens=100,
                output_tokens=50,
            )
        )
        tracker.record(
            ModelCallMetrics(
                agent_name="metrics_panel",
                model="gemini-2.5-flash",
                input_tokens=200,
                output_tokens=100,
            )
        )
        tracker.record(
            ModelCallMetrics(
                agent_name="trace_panel",
                model="gemini-2.5-flash",
                input_tokens=150,
                output_tokens=75,
            )
        )

        summary = tracker.get_summary()
        assert summary["per_agent"]["trace_panel"]["calls"] == 2
        assert summary["per_agent"]["trace_panel"]["input_tokens"] == 250
        assert summary["per_agent"]["metrics_panel"]["calls"] == 1
        assert summary["per_agent"]["metrics_panel"]["input_tokens"] == 200

    def test_get_summary(self) -> None:
        """Summary should include all expected fields."""
        tracker = UsageTracker()
        tracker.record(
            ModelCallMetrics(
                agent_name="test",
                model="gemini-2.5-flash",
                input_tokens=100,
                output_tokens=50,
                estimated_cost_usd=0.001,
            )
        )
        summary = tracker.get_summary()

        assert "total_calls" in summary
        assert "total_input_tokens" in summary
        assert "total_output_tokens" in summary
        assert "total_tokens" in summary
        assert "estimated_cost_usd" in summary
        assert "per_agent" in summary
        assert summary["total_tokens"] == 150

    def test_reset(self) -> None:
        """Reset should clear all metrics."""
        tracker = UsageTracker()
        tracker.record(
            ModelCallMetrics(
                agent_name="test",
                model="gemini-2.5-flash",
                input_tokens=100,
                output_tokens=50,
            )
        )
        tracker.reset()

        assert tracker.total_calls == 0
        assert tracker.total_tokens == 0

    def test_is_over_budget_disabled(self) -> None:
        """With budget=0 (disabled), should never be over budget."""
        tracker = UsageTracker()
        tracker.record(
            ModelCallMetrics(
                agent_name="test",
                model="gemini-2.5-flash",
                input_tokens=1_000_000,
                output_tokens=1_000_000,
            )
        )
        with patch.dict(os.environ, {"SRE_AGENT_TOKEN_BUDGET": "0"}):
            assert tracker.is_over_budget() is False

    def test_is_over_budget_under(self) -> None:
        """Should not be over budget when under limit."""
        tracker = UsageTracker()
        tracker.record(
            ModelCallMetrics(
                agent_name="test",
                model="gemini-2.5-flash",
                input_tokens=100,
                output_tokens=50,
            )
        )
        with patch.dict(os.environ, {"SRE_AGENT_TOKEN_BUDGET": "1000"}):
            assert tracker.is_over_budget() is False

    def test_is_over_budget_exceeded(self) -> None:
        """Should be over budget when exceeding limit."""
        tracker = UsageTracker()
        tracker.record(
            ModelCallMetrics(
                agent_name="test",
                model="gemini-2.5-flash",
                input_tokens=600,
                output_tokens=500,
            )
        )
        with patch.dict(os.environ, {"SRE_AGENT_TOKEN_BUDGET": "1000"}):
            assert tracker.is_over_budget() is True

    def test_thread_safety(self) -> None:
        """Recording from multiple threads should be safe."""
        tracker = UsageTracker()
        errors: list[Exception] = []

        def record_calls() -> None:
            try:
                for _ in range(100):
                    tracker.record(
                        ModelCallMetrics(
                            agent_name="test",
                            model="gemini-2.5-flash",
                            input_tokens=10,
                            output_tokens=5,
                        )
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_calls) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert tracker.total_calls == 400
        assert tracker.total_input_tokens == 4000


class TestSingleton:
    """Tests for the module-level singleton."""

    def test_get_usage_tracker_returns_same_instance(self) -> None:
        """get_usage_tracker should return the same instance."""
        t1 = get_usage_tracker()
        t2 = get_usage_tracker()
        assert t1 is t2

    def test_reset_creates_new_instance(self) -> None:
        """reset_usage_tracker should clear the singleton."""
        t1 = get_usage_tracker()
        t1.record(
            ModelCallMetrics(
                agent_name="test",
                model="gemini-2.5-flash",
                input_tokens=100,
                output_tokens=50,
            )
        )
        reset_usage_tracker()
        t2 = get_usage_tracker()
        assert t2.total_calls == 0


class TestCostEstimation:
    """Tests for the _estimate_cost function."""

    def test_flash_model_cost(self) -> None:
        """Gemini 2.5 Flash cost should use correct pricing."""
        cost = _estimate_cost("gemini-2.5-flash", 1_000_000, 1_000_000)
        # input: 1M * $0.15/1M = $0.15, output: 1M * $0.60/1M = $0.60
        assert abs(cost - 0.75) < 0.001

    def test_pro_model_cost(self) -> None:
        """Gemini 2.5 Pro cost should use correct pricing."""
        cost = _estimate_cost("gemini-2.5-pro", 1_000_000, 1_000_000)
        # input: 1M * $1.25/1M = $1.25, output: 1M * $10.00/1M = $10.00
        assert abs(cost - 11.25) < 0.001

    def test_unknown_model_uses_default(self) -> None:
        """Unknown model should use default pricing."""
        cost = _estimate_cost("some-unknown-model", 1_000_000, 0)
        # input: 1M * $0.50/1M = $0.50
        assert abs(cost - 0.50) < 0.001

    def test_prefix_matching(self) -> None:
        """Models with version suffixes should match base pricing."""
        cost = _estimate_cost("gemini-2.5-flash-latest", 1_000_000, 0)
        # Should match gemini-2.5-flash pricing
        assert abs(cost - 0.15) < 0.001

    def test_zero_tokens(self) -> None:
        """Zero tokens should result in zero cost."""
        cost = _estimate_cost("gemini-2.5-flash", 0, 0)
        assert cost == 0.0


class TestBeforeModelCallback:
    """Tests for the before_model_callback function."""

    def test_allows_call_under_budget(self) -> None:
        """Should return None (allow call) when under budget."""
        with patch.dict(os.environ, {"SRE_AGENT_TOKEN_BUDGET": "10000"}):
            ctx = MagicMock()
            ctx.state = {}
            result = before_model_callback(ctx, MagicMock())
            assert result is None

    def test_blocks_call_over_budget(self) -> None:
        """Should return LlmResponse when over budget."""
        tracker = get_usage_tracker()
        tracker.record(
            ModelCallMetrics(
                agent_name="test",
                model="gemini-2.5-flash",
                input_tokens=5000,
                output_tokens=6000,
            )
        )
        with patch.dict(os.environ, {"SRE_AGENT_TOKEN_BUDGET": "10000"}):
            ctx = MagicMock()
            ctx.state = {}
            result = before_model_callback(ctx, MagicMock())
            assert result is not None
            assert "budget" in result.content.parts[0].text.lower()

    def test_stores_start_time_in_state(self) -> None:
        """Should store start time in callback context state."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SRE_AGENT_TOKEN_BUDGET", None)
            ctx = MagicMock()
            ctx.state = {}
            before_model_callback(ctx, MagicMock())
            assert "_model_call_start_time" in ctx.state
            assert isinstance(ctx.state["_model_call_start_time"], float)

    def test_unlimited_budget_allows_all(self) -> None:
        """With unlimited budget (0), should always allow calls."""
        tracker = get_usage_tracker()
        tracker.record(
            ModelCallMetrics(
                agent_name="test",
                model="gemini-2.5-flash",
                input_tokens=999_999_999,
                output_tokens=999_999_999,
            )
        )
        with patch.dict(os.environ, {"SRE_AGENT_TOKEN_BUDGET": "0"}):
            ctx = MagicMock()
            ctx.state = {}
            result = before_model_callback(ctx, MagicMock())
            assert result is None


class TestAfterModelCallback:
    """Tests for the after_model_callback function."""

    def test_records_usage_from_response(self) -> None:
        """Should record token usage from the LLM response."""
        tracker = get_usage_tracker()

        ctx = MagicMock()
        ctx.state = {"_model_call_start_time": 0.0}
        ctx.agent_name = "trace_panel"

        response = MagicMock()
        response.usageMetadata.prompt_token_count = 500
        response.usageMetadata.candidates_token_count = 200
        response.modelVersion = "gemini-2.5-flash"

        after_model_callback(ctx, response)

        assert tracker.total_input_tokens == 500
        assert tracker.total_output_tokens == 200
        assert tracker.total_calls == 1

    def test_handles_missing_usage_metadata(self) -> None:
        """Should handle responses without usageMetadata gracefully."""
        tracker = get_usage_tracker()

        ctx = MagicMock()
        ctx.state = {}
        ctx.agent_name = "test"

        response = MagicMock()
        response.usageMetadata = None
        response.modelVersion = "unknown"

        result = after_model_callback(ctx, response)
        assert result is None
        assert tracker.total_calls == 1
        assert tracker.total_tokens == 0

    def test_returns_none(self) -> None:
        """Should always return None (doesn't modify response)."""
        ctx = MagicMock()
        ctx.state = {}
        ctx.agent_name = "test"
        response = MagicMock()
        response.usageMetadata = None
        response.modelVersion = "unknown"

        result = after_model_callback(ctx, response)
        assert result is None

    def test_clears_start_time_from_state(self) -> None:
        """Should clear the start time from state after recording."""
        # Use a real dict wrapped in a simple object to simulate State
        state_dict: dict[str, float | None] = {"_model_call_start_time": 100.0}

        class FakeState:
            def get(self, key: str, default: float | None = None) -> float | None:
                return state_dict.get(key, default)

            def __setitem__(self, key: str, value: float | None) -> None:
                state_dict[key] = value

        ctx = MagicMock()
        ctx.state = FakeState()
        ctx.agent_name = "test"
        response = MagicMock()
        response.usageMetadata = None
        response.modelVersion = "unknown"

        after_model_callback(ctx, response)
        assert state_dict["_model_call_start_time"] is None
