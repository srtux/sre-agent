"""Tests for the CouncilOrchestrator BaseAgent subclass.

Validates the custom orchestrator's structure and factory function.
"""

from google.adk.agents import BaseAgent

from sre_agent.council.orchestrator import (
    CouncilOrchestrator,
    create_council_orchestrator,
)
from sre_agent.council.schemas import CouncilConfig, InvestigationMode


class TestCouncilOrchestrator:
    """Tests for CouncilOrchestrator."""

    def test_is_base_agent(self) -> None:
        """CouncilOrchestrator should be a BaseAgent subclass."""
        orchestrator = CouncilOrchestrator(name="test")
        assert isinstance(orchestrator, BaseAgent)

    def test_default_config(self) -> None:
        """Should use default CouncilConfig."""
        orchestrator = CouncilOrchestrator(name="test")
        assert orchestrator.council_config.mode == InvestigationMode.STANDARD
        assert orchestrator.council_config.max_debate_rounds == 3

    def test_custom_config(self) -> None:
        """Should accept custom CouncilConfig."""
        config = CouncilConfig(
            mode=InvestigationMode.DEBATE,
            max_debate_rounds=5,
            confidence_threshold=0.9,
        )
        orchestrator = CouncilOrchestrator(name="test", council_config=config)
        assert orchestrator.council_config.mode == InvestigationMode.DEBATE
        assert orchestrator.council_config.max_debate_rounds == 5

    def test_has_sub_agents_field(self) -> None:
        """Should support sub_agents field from BaseAgent."""
        orchestrator = CouncilOrchestrator(name="test", sub_agents=[])
        assert orchestrator.sub_agents == []


class TestCreateCouncilOrchestrator:
    """Tests for the factory function."""

    def test_returns_orchestrator(self) -> None:
        """Factory should return a CouncilOrchestrator instance."""
        orchestrator = create_council_orchestrator()
        assert isinstance(orchestrator, CouncilOrchestrator)

    def test_correct_name(self) -> None:
        """Factory should set the name to 'sre_agent'."""
        orchestrator = create_council_orchestrator()
        assert orchestrator.name == "sre_agent"

    def test_default_config(self) -> None:
        """Factory should use default config when None."""
        orchestrator = create_council_orchestrator()
        assert orchestrator.council_config.mode == InvestigationMode.STANDARD

    def test_custom_config(self) -> None:
        """Factory should accept custom config."""
        config = CouncilConfig(mode=InvestigationMode.DEBATE)
        orchestrator = create_council_orchestrator(config=config)
        assert orchestrator.council_config.mode == InvestigationMode.DEBATE

    def test_with_sub_agents(self) -> None:
        """Factory should accept sub_agents list."""
        from google.adk.agents import LlmAgent

        dummy = LlmAgent(name="dummy", model="gemini-2.0-flash", instruction="test")
        orchestrator = create_council_orchestrator(sub_agents=[dummy])
        assert len(orchestrator.sub_agents) == 1
        assert orchestrator.sub_agents[0].name == "dummy"

    def test_creates_independent_instances(self) -> None:
        """Each call should create a new orchestrator."""
        o1 = create_council_orchestrator()
        o2 = create_council_orchestrator()
        assert o1 is not o2
