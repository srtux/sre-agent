"""Tests for the council synthesizer agent.

Validates that the synthesizer is correctly configured to
read panel findings and produce unified assessments.
"""

from google.adk.agents import LlmAgent

from sre_agent.council.synthesizer import create_synthesizer


class TestCreateSynthesizer:
    """Tests for synthesizer creation."""

    def test_returns_llm_agent(self) -> None:
        """Factory should return an LlmAgent instance."""
        synthesizer = create_synthesizer()
        assert isinstance(synthesizer, LlmAgent)

    def test_correct_name(self) -> None:
        """Synthesizer should have the expected name."""
        synthesizer = create_synthesizer()
        assert synthesizer.name == "council_synthesizer"

    def test_correct_output_key(self) -> None:
        """Synthesizer should write to 'council_synthesis'."""
        synthesizer = create_synthesizer()
        assert synthesizer.output_key == "council_synthesis"

    def test_no_tools(self) -> None:
        """Synthesizer should not have any tools — it only reads state."""
        synthesizer = create_synthesizer()
        assert len(synthesizer.tools) == 0

    def test_creates_independent_instances(self) -> None:
        """Each call should create a new synthesizer instance."""
        s1 = create_synthesizer()
        s2 = create_synthesizer()
        assert s1 is not s2
