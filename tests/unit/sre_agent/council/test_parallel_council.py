"""Tests for the parallel council pipeline assembly.

Validates that the council pipeline is correctly composed from
ParallelAgent (panels) → SequentialAgent (pipeline).
"""

from google.adk.agents import ParallelAgent, SequentialAgent

from sre_agent.council.parallel_council import create_council_pipeline
from sre_agent.council.schemas import CouncilConfig, InvestigationMode


class TestCreateCouncilPipeline:
    """Tests for council pipeline creation."""

    def test_returns_sequential_agent(self) -> None:
        """Pipeline should be a SequentialAgent."""
        pipeline = create_council_pipeline()
        assert isinstance(pipeline, SequentialAgent)

    def test_pipeline_name(self) -> None:
        """Pipeline should have the expected name."""
        pipeline = create_council_pipeline()
        assert pipeline.name == "council_pipeline"

    def test_has_two_stages(self) -> None:
        """Pipeline should have 2 stages: parallel panels + synthesizer."""
        pipeline = create_council_pipeline()
        assert len(pipeline.sub_agents) == 2

    def test_first_stage_is_parallel(self) -> None:
        """First stage should be a ParallelAgent with 4 panels."""
        pipeline = create_council_pipeline()
        parallel_stage = pipeline.sub_agents[0]
        assert isinstance(parallel_stage, ParallelAgent)
        assert parallel_stage.name == "parallel_panels"
        assert len(parallel_stage.sub_agents) == 4

    def test_panel_names_in_parallel(self) -> None:
        """Parallel stage should contain all 4 specialist panels."""
        pipeline = create_council_pipeline()
        parallel_stage = pipeline.sub_agents[0]
        panel_names = {agent.name for agent in parallel_stage.sub_agents}
        assert panel_names == {
            "trace_panel",
            "metrics_panel",
            "logs_panel",
            "alerts_panel",
        }

    def test_second_stage_is_synthesizer(self) -> None:
        """Second stage should be the council synthesizer."""
        pipeline = create_council_pipeline()
        synthesizer = pipeline.sub_agents[1]
        assert synthesizer.name == "council_synthesizer"

    def test_accepts_custom_config(self) -> None:
        """Pipeline should accept a custom CouncilConfig."""
        config = CouncilConfig(mode=InvestigationMode.DEBATE, max_debate_rounds=5)
        pipeline = create_council_pipeline(config)
        assert isinstance(pipeline, SequentialAgent)

    def test_creates_independent_instances(self) -> None:
        """Each call should create a new pipeline instance."""
        p1 = create_council_pipeline()
        p2 = create_council_pipeline()
        assert p1 is not p2

    def test_default_config_when_none(self) -> None:
        """Should use default config when None is passed."""
        pipeline = create_council_pipeline(None)
        assert isinstance(pipeline, SequentialAgent)
        assert len(pipeline.sub_agents) == 2
