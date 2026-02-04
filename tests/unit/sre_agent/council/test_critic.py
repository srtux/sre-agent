"""Tests for the council critic agent.

Validates that the critic is correctly configured to
cross-examine panel findings and produce a CriticReport.
"""

from google.adk.agents import LlmAgent

from sre_agent.council.critic import create_critic


class TestCreateCritic:
    """Tests for critic creation."""

    def test_returns_llm_agent(self) -> None:
        """Factory should return an LlmAgent instance."""
        critic = create_critic()
        assert isinstance(critic, LlmAgent)

    def test_correct_name(self) -> None:
        """Critic should have the expected name."""
        critic = create_critic()
        assert critic.name == "council_critic"

    def test_correct_output_key(self) -> None:
        """Critic should write to 'critic_report'."""
        critic = create_critic()
        assert critic.output_key == "critic_report"

    def test_no_tools(self) -> None:
        """Critic should not have any tools — it only reads state."""
        critic = create_critic()
        assert len(critic.tools) == 0

    def test_creates_independent_instances(self) -> None:
        """Each call should create a new critic instance."""
        c1 = create_critic()
        c2 = create_critic()
        assert c1 is not c2
