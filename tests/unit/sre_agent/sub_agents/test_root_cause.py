"""Unit tests for the root_cause_analyst sub-agent configuration."""

from google.adk.agents import LlmAgent

from sre_agent.sub_agents.root_cause import (
    ROOT_CAUSE_ANALYST_PROMPT,
    root_cause_analyst,
)


class TestRootCauseAnalystAgent:
    """Tests for the root_cause_analyst LlmAgent instance."""

    def test_root_cause_analyst_is_llm_agent(self):
        """Verify root_cause_analyst is an LlmAgent instance."""
        assert isinstance(root_cause_analyst, LlmAgent)

    def test_root_cause_analyst_has_name(self):
        """Verify root_cause_analyst has a non-empty name."""
        assert root_cause_analyst.name
        assert root_cause_analyst.name == "root_cause_analyst"

    def test_root_cause_analyst_has_model(self):
        """Verify root_cause_analyst has a model configured."""
        assert root_cause_analyst.model is not None
        model_name = (
            root_cause_analyst.model
            if isinstance(root_cause_analyst.model, str)
            else str(root_cause_analyst.model)
        )
        assert len(model_name) > 0

    def test_root_cause_analyst_has_tools(self):
        """Verify root_cause_analyst has a non-empty tools list."""
        assert root_cause_analyst.tools
        assert len(root_cause_analyst.tools) > 0

    def test_root_cause_analyst_has_description(self):
        """Verify root_cause_analyst has a description."""
        assert root_cause_analyst.description
        assert "root cause" in root_cause_analyst.description.lower()

    def test_root_cause_analyst_tools_include_causal_analysis(self):
        """Verify tools include causal analysis capabilities."""
        tool_names = [
            getattr(t, "name", getattr(t, "__name__", str(t)))
            for t in root_cause_analyst.tools
        ]
        assert any(
            "causal" in name.lower() or "correlation" in name.lower()
            for name in tool_names
        )


class TestRootCauseAnalystPrompt:
    """Tests for the ROOT_CAUSE_ANALYST_PROMPT constant."""

    def test_prompt_is_non_empty_string(self):
        """Verify ROOT_CAUSE_ANALYST_PROMPT is a non-empty string."""
        assert isinstance(ROOT_CAUSE_ANALYST_PROMPT, str)
        assert len(ROOT_CAUSE_ANALYST_PROMPT) > 100

    def test_prompt_contains_role(self):
        """Verify prompt defines the agent role."""
        assert "<role>" in ROOT_CAUSE_ANALYST_PROMPT
        assert "Root Cause Analyst" in ROOT_CAUSE_ANALYST_PROMPT

    def test_prompt_contains_tool_strategy(self):
        """Verify prompt includes tool usage strategy."""
        assert "<tool_strategy>" in ROOT_CAUSE_ANALYST_PROMPT
        assert "perform_causal_analysis" in ROOT_CAUSE_ANALYST_PROMPT

    def test_prompt_contains_output_format(self):
        """Verify prompt defines output format."""
        assert "<output_format>" in ROOT_CAUSE_ANALYST_PROMPT

    def test_prompt_mentions_cross_signal_synthesis(self):
        """Verify prompt covers multi-signal synthesis."""
        assert "Traces" in ROOT_CAUSE_ANALYST_PROMPT
        assert "Logs" in ROOT_CAUSE_ANALYST_PROMPT
        assert "Metrics" in ROOT_CAUSE_ANALYST_PROMPT
