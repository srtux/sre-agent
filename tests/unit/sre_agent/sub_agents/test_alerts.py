"""Unit tests for the alert_analyst sub-agent configuration."""

from google.adk.agents import LlmAgent

from sre_agent.sub_agents.alerts import ALERT_ANALYST_PROMPT, alert_analyst


class TestAlertAnalystAgent:
    """Tests for the alert_analyst LlmAgent instance."""

    def test_alert_analyst_is_llm_agent(self):
        """Verify alert_analyst is an LlmAgent instance."""
        assert isinstance(alert_analyst, LlmAgent)

    def test_alert_analyst_has_name(self):
        """Verify alert_analyst has a non-empty name."""
        assert alert_analyst.name
        assert alert_analyst.name == "alert_analyst"

    def test_alert_analyst_has_model(self):
        """Verify alert_analyst has a model configured."""
        assert alert_analyst.model is not None
        model_name = (
            alert_analyst.model
            if isinstance(alert_analyst.model, str)
            else str(alert_analyst.model)
        )
        assert len(model_name) > 0

    def test_alert_analyst_has_tools(self):
        """Verify alert_analyst has a non-empty tools list."""
        assert alert_analyst.tools
        assert len(alert_analyst.tools) > 0

    def test_alert_analyst_has_description(self):
        """Verify alert_analyst has a description."""
        assert alert_analyst.description
        assert "alert" in alert_analyst.description.lower()

    def test_alert_analyst_tools_include_alert_tools(self):
        """Verify alert_analyst tools include alert-related tools."""
        tool_names = [
            getattr(t, "name", getattr(t, "__name__", str(t)))
            for t in alert_analyst.tools
        ]
        assert any("alert" in name.lower() for name in tool_names)


class TestAlertAnalystPrompt:
    """Tests for the ALERT_ANALYST_PROMPT constant."""

    def test_prompt_is_non_empty_string(self):
        """Verify ALERT_ANALYST_PROMPT is a non-empty string."""
        assert isinstance(ALERT_ANALYST_PROMPT, str)
        assert len(ALERT_ANALYST_PROMPT) > 100

    def test_prompt_contains_role(self):
        """Verify prompt defines the agent role."""
        assert "<role>" in ALERT_ANALYST_PROMPT
        assert "Alert Analyst" in ALERT_ANALYST_PROMPT

    def test_prompt_contains_tool_strategy(self):
        """Verify prompt includes tool usage strategy."""
        assert "<tool_strategy>" in ALERT_ANALYST_PROMPT
        assert "list_alerts" in ALERT_ANALYST_PROMPT

    def test_prompt_contains_output_format(self):
        """Verify prompt defines output format."""
        assert "<output_format>" in ALERT_ANALYST_PROMPT
