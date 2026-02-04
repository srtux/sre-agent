"""Tests for the debate pipeline with confidence gating.

Validates the debate pipeline assembly and confidence gate logic.
"""

import json

from google.adk.agents import LoopAgent, ParallelAgent, SequentialAgent

from sre_agent.council.debate import (
    _build_confidence_gate,
    create_debate_pipeline,
)
from sre_agent.council.schemas import CouncilConfig


class _MockState(dict):
    """Mock state dict for testing callbacks."""

    pass


class _MockCallbackContext:
    """Minimal mock of CallbackContext for testing confidence gate."""

    def __init__(self, state: dict | None = None) -> None:
        self.state = _MockState(state or {})


class TestConfidenceGate:
    """Tests for the confidence gate callback."""

    def test_returns_none_when_no_synthesis(self) -> None:
        """Gate should return None when no synthesis in state."""
        config = CouncilConfig(confidence_threshold=0.85)
        gate = _build_confidence_gate(config)
        ctx = _MockCallbackContext({})
        assert gate(ctx) is None

    def test_returns_none_below_threshold(self) -> None:
        """Gate should return None when confidence is below threshold."""
        config = CouncilConfig(confidence_threshold=0.85)
        gate = _build_confidence_gate(config)
        synthesis = json.dumps({"overall_confidence": 0.5})
        ctx = _MockCallbackContext({"council_synthesis": synthesis})
        assert gate(ctx) is None

    def test_returns_content_at_threshold(self) -> None:
        """Gate should return Content when confidence meets threshold."""
        config = CouncilConfig(confidence_threshold=0.85)
        gate = _build_confidence_gate(config)
        synthesis = json.dumps({"overall_confidence": 0.85})
        ctx = _MockCallbackContext({"council_synthesis": synthesis})
        result = gate(ctx)
        assert result is not None
        assert len(result.parts) > 0

    def test_returns_content_above_threshold(self) -> None:
        """Gate should return Content when confidence exceeds threshold."""
        config = CouncilConfig(confidence_threshold=0.85)
        gate = _build_confidence_gate(config)
        synthesis = json.dumps({"overall_confidence": 0.95})
        ctx = _MockCallbackContext({"council_synthesis": synthesis})
        result = gate(ctx)
        assert result is not None

    def test_handles_dict_synthesis(self) -> None:
        """Gate should handle synthesis as a dict (not just JSON string)."""
        config = CouncilConfig(confidence_threshold=0.85)
        gate = _build_confidence_gate(config)
        ctx = _MockCallbackContext({"council_synthesis": {"overall_confidence": 0.9}})
        result = gate(ctx)
        assert result is not None

    def test_handles_invalid_json(self) -> None:
        """Gate should return None on invalid JSON in synthesis."""
        config = CouncilConfig(confidence_threshold=0.85)
        gate = _build_confidence_gate(config)
        ctx = _MockCallbackContext({"council_synthesis": "not-json"})
        assert gate(ctx) is None

    def test_handles_missing_confidence_key(self) -> None:
        """Gate should return None when confidence key is missing."""
        config = CouncilConfig(confidence_threshold=0.85)
        gate = _build_confidence_gate(config)
        ctx = _MockCallbackContext(
            {"council_synthesis": json.dumps({"synthesis": "test"})}
        )
        assert gate(ctx) is None

    def test_custom_threshold(self) -> None:
        """Gate should respect custom threshold values."""
        config = CouncilConfig(confidence_threshold=0.5)
        gate = _build_confidence_gate(config)
        synthesis = json.dumps({"overall_confidence": 0.5})
        ctx = _MockCallbackContext({"council_synthesis": synthesis})
        result = gate(ctx)
        assert result is not None


class TestCreateDebatePipeline:
    """Tests for debate pipeline creation."""

    def test_returns_sequential_agent(self) -> None:
        """Pipeline should be a SequentialAgent."""
        pipeline = create_debate_pipeline()
        assert isinstance(pipeline, SequentialAgent)

    def test_pipeline_name(self) -> None:
        """Pipeline should have the expected name."""
        pipeline = create_debate_pipeline()
        assert pipeline.name == "debate_pipeline"

    def test_has_three_stages(self) -> None:
        """Pipeline should have 3 stages: initial panels + synthesizer + debate loop."""
        pipeline = create_debate_pipeline()
        assert len(pipeline.sub_agents) == 3

    def test_first_stage_is_parallel(self) -> None:
        """First stage should be initial parallel panels."""
        pipeline = create_debate_pipeline()
        first_stage = pipeline.sub_agents[0]
        assert isinstance(first_stage, ParallelAgent)
        assert first_stage.name == "initial_panels"
        assert len(first_stage.sub_agents) == 4

    def test_second_stage_is_synthesizer(self) -> None:
        """Second stage should be initial synthesizer."""
        pipeline = create_debate_pipeline()
        second_stage = pipeline.sub_agents[1]
        assert second_stage.name == "council_synthesizer"

    def test_third_stage_is_loop(self) -> None:
        """Third stage should be a LoopAgent for debate."""
        pipeline = create_debate_pipeline()
        debate_loop = pipeline.sub_agents[2]
        assert isinstance(debate_loop, LoopAgent)
        assert debate_loop.name == "debate_loop"

    def test_loop_has_correct_sub_agents(self) -> None:
        """Debate loop should have critic + panels + synthesizer."""
        pipeline = create_debate_pipeline()
        debate_loop = pipeline.sub_agents[2]
        assert len(debate_loop.sub_agents) == 3
        assert debate_loop.sub_agents[0].name == "council_critic"
        assert isinstance(debate_loop.sub_agents[1], ParallelAgent)
        assert debate_loop.sub_agents[2].name == "council_synthesizer"

    def test_loop_max_iterations(self) -> None:
        """Debate loop should respect max_debate_rounds from config."""
        config = CouncilConfig(max_debate_rounds=5)
        pipeline = create_debate_pipeline(config)
        debate_loop = pipeline.sub_agents[2]
        assert isinstance(debate_loop, LoopAgent)
        assert debate_loop.max_iterations == 5

    def test_default_max_iterations(self) -> None:
        """Debate loop should default to 3 iterations."""
        pipeline = create_debate_pipeline()
        debate_loop = pipeline.sub_agents[2]
        assert isinstance(debate_loop, LoopAgent)
        assert debate_loop.max_iterations == 3

    def test_loop_has_confidence_gate(self) -> None:
        """Debate loop should have a before_agent_callback."""
        pipeline = create_debate_pipeline()
        debate_loop = pipeline.sub_agents[2]
        assert isinstance(debate_loop, LoopAgent)
        assert debate_loop.before_agent_callback is not None

    def test_creates_independent_instances(self) -> None:
        """Each call should create a new pipeline instance."""
        p1 = create_debate_pipeline()
        p2 = create_debate_pipeline()
        assert p1 is not p2

    def test_accepts_none_config(self) -> None:
        """Should use default config when None is passed."""
        pipeline = create_debate_pipeline(None)
        assert isinstance(pipeline, SequentialAgent)
