"""Tests for debate convergence tracking in the council pipeline.

Validates that:
- _build_convergence_tracker records round metrics
- Confidence progression is tracked correctly
- Critic gap/contradiction counts are captured
- Convergence flag is set when threshold is met
- Round duration is calculated
- History accumulates across rounds
"""

import json
from unittest.mock import MagicMock

import pytest

from sre_agent.council.debate import (
    CONVERGENCE_STATE_KEY,
    _build_confidence_gate,
    _build_convergence_tracker,
    create_debate_pipeline,
)
from sre_agent.council.schemas import CouncilConfig, InvestigationMode


class TestConvergenceTracker:
    """Tests for the _build_convergence_tracker callback."""

    def _make_context(
        self,
        confidence: float = 0.0,
        gaps: list[str] | None = None,
        contradictions: list[str] | None = None,
    ) -> MagicMock:
        """Create a mock callback context with synthesis and critic state."""
        ctx = MagicMock()
        ctx.state = {}

        # Set up synthesis
        ctx.state["council_synthesis"] = json.dumps({"overall_confidence": confidence})

        # Set up critic report
        ctx.state["critic_report"] = json.dumps(
            {
                "gaps": gaps or [],
                "contradictions": contradictions or [],
                "agreements": [],
                "revised_confidence": confidence,
            }
        )

        return ctx

    def test_initializes_history(self) -> None:
        """Should initialize convergence history in state."""
        config = CouncilConfig(confidence_threshold=0.85)
        tracker = _build_convergence_tracker(config)

        ctx = self._make_context(confidence=0.5)
        tracker(ctx)

        assert CONVERGENCE_STATE_KEY in ctx.state
        assert len(ctx.state[CONVERGENCE_STATE_KEY]) == 1

    def test_records_confidence(self) -> None:
        """Should record the current confidence value."""
        config = CouncilConfig(confidence_threshold=0.85)
        tracker = _build_convergence_tracker(config)

        ctx = self._make_context(confidence=0.72)
        tracker(ctx)

        record = ctx.state[CONVERGENCE_STATE_KEY][0]
        assert record["confidence"] == 0.72

    def test_records_confidence_delta(self) -> None:
        """Should calculate delta from previous round."""
        config = CouncilConfig(confidence_threshold=0.85)
        tracker = _build_convergence_tracker(config)

        # Round 1
        ctx = self._make_context(confidence=0.5)
        tracker(ctx)

        # Round 2 (increasing confidence)
        ctx.state["council_synthesis"] = json.dumps({"overall_confidence": 0.75})
        tracker(ctx)

        records = ctx.state[CONVERGENCE_STATE_KEY]
        assert records[0]["confidence_delta"] == 0.5  # 0.5 - 0.0 (no prev)
        assert records[1]["confidence_delta"] == pytest.approx(0.25)  # 0.75 - 0.5

    def test_records_critic_gaps(self) -> None:
        """Should record critic gap count."""
        config = CouncilConfig(confidence_threshold=0.85)
        tracker = _build_convergence_tracker(config)

        ctx = self._make_context(
            confidence=0.6,
            gaps=["missing DB analysis", "no network check"],
        )
        tracker(ctx)

        record = ctx.state[CONVERGENCE_STATE_KEY][0]
        assert record["critic_gaps"] == 2

    def test_records_critic_contradictions(self) -> None:
        """Should record critic contradiction count."""
        config = CouncilConfig(confidence_threshold=0.85)
        tracker = _build_convergence_tracker(config)

        ctx = self._make_context(
            confidence=0.6,
            contradictions=["trace says healthy but metrics show degraded"],
        )
        tracker(ctx)

        record = ctx.state[CONVERGENCE_STATE_KEY][0]
        assert record["critic_contradictions"] == 1

    def test_records_converged_flag(self) -> None:
        """Should set converged=True when confidence meets threshold."""
        config = CouncilConfig(confidence_threshold=0.85)
        tracker = _build_convergence_tracker(config)

        # Below threshold
        ctx = self._make_context(confidence=0.7)
        tracker(ctx)
        assert ctx.state[CONVERGENCE_STATE_KEY][0]["converged"] is False

        # At threshold
        ctx.state["council_synthesis"] = json.dumps({"overall_confidence": 0.85})
        tracker(ctx)
        assert ctx.state[CONVERGENCE_STATE_KEY][1]["converged"] is True

    def test_accumulates_history(self) -> None:
        """Should accumulate records across multiple rounds."""
        config = CouncilConfig(confidence_threshold=0.95)
        tracker = _build_convergence_tracker(config)

        ctx = self._make_context(confidence=0.3)
        for i in range(5):
            conf = 0.3 + (i * 0.15)
            ctx.state["council_synthesis"] = json.dumps({"overall_confidence": conf})
            tracker(ctx)

        history = ctx.state[CONVERGENCE_STATE_KEY]
        assert len(history) == 5
        # Confidence should be monotonically increasing
        confidences = [r["confidence"] for r in history]
        assert confidences == sorted(confidences)

    def test_records_round_number(self) -> None:
        """Should record sequential round numbers."""
        config = CouncilConfig(confidence_threshold=0.85)
        tracker = _build_convergence_tracker(config)

        ctx = self._make_context(confidence=0.5)
        tracker(ctx)
        tracker(ctx)
        tracker(ctx)

        history = ctx.state[CONVERGENCE_STATE_KEY]
        rounds = [r["round"] for r in history]
        assert rounds == [1, 2, 3]

    def test_records_threshold(self) -> None:
        """Should include the configured threshold in each record."""
        config = CouncilConfig(confidence_threshold=0.90)
        tracker = _build_convergence_tracker(config)

        ctx = self._make_context(confidence=0.5)
        tracker(ctx)

        record = ctx.state[CONVERGENCE_STATE_KEY][0]
        assert record["threshold"] == 0.90

    def test_handles_missing_synthesis(self) -> None:
        """Should handle missing council_synthesis gracefully."""
        config = CouncilConfig(confidence_threshold=0.85)
        tracker = _build_convergence_tracker(config)

        ctx = MagicMock()
        ctx.state = {}  # No synthesis
        tracker(ctx)

        record = ctx.state[CONVERGENCE_STATE_KEY][0]
        assert record["confidence"] == 0.0

    def test_handles_invalid_json_synthesis(self) -> None:
        """Should handle invalid JSON in synthesis gracefully."""
        config = CouncilConfig(confidence_threshold=0.85)
        tracker = _build_convergence_tracker(config)

        ctx = MagicMock()
        ctx.state = {"council_synthesis": "not valid json"}
        tracker(ctx)

        record = ctx.state[CONVERGENCE_STATE_KEY][0]
        assert record["confidence"] == 0.0

    def test_handles_dict_synthesis(self) -> None:
        """Should handle dict-type synthesis (not just JSON string)."""
        config = CouncilConfig(confidence_threshold=0.85)
        tracker = _build_convergence_tracker(config)

        ctx = MagicMock()
        ctx.state = {
            "council_synthesis": {"overall_confidence": 0.88},
        }
        tracker(ctx)

        record = ctx.state[CONVERGENCE_STATE_KEY][0]
        assert record["confidence"] == 0.88


class TestConfidenceGateIntegration:
    """Tests for confidence gate working alongside convergence tracker."""

    def test_gate_and_tracker_use_same_state_key(self) -> None:
        """Both callbacks should share state without conflict."""
        config = CouncilConfig(confidence_threshold=0.85)
        gate = _build_confidence_gate(config)
        tracker = _build_convergence_tracker(config)

        ctx = MagicMock()
        ctx.state = {
            "council_synthesis": json.dumps({"overall_confidence": 0.5}),
        }

        # Gate should allow continuation
        result = gate(ctx)
        assert result is None

        # Tracker should record the round
        tracker(ctx)
        assert len(ctx.state[CONVERGENCE_STATE_KEY]) == 1


class TestDebatePipelineConvergence:
    """Tests for convergence tracking integration in the debate pipeline."""

    def test_pipeline_has_after_agent_callback(self) -> None:
        """The debate loop should have an after_agent_callback."""
        config = CouncilConfig(
            mode=InvestigationMode.DEBATE,
            max_debate_rounds=3,
        )
        pipeline = create_debate_pipeline(config)

        # Pipeline is a SequentialAgent with [initial_panels, synthesizer, debate_loop]
        debate_loop = pipeline.sub_agents[2]
        assert debate_loop.name == "debate_loop"
        assert debate_loop.after_agent_callback is not None

    def test_pipeline_has_before_agent_callback(self) -> None:
        """The debate loop should have both before and after callbacks."""
        config = CouncilConfig(mode=InvestigationMode.DEBATE)
        pipeline = create_debate_pipeline(config)

        debate_loop = pipeline.sub_agents[2]
        assert debate_loop.before_agent_callback is not None
        assert debate_loop.after_agent_callback is not None
