"""Unit tests for the agent_debugger sub-agent configuration."""

from google.adk.agents import LlmAgent

from sre_agent.sub_agents.agent_debugger import (
    AGENT_DEBUGGER_PROMPT,
    agent_debugger,
)


class TestAgentDebuggerAgent:
    """Tests for the agent_debugger LlmAgent instance."""

    def test_agent_debugger_is_llm_agent(self):
        """Verify agent_debugger is an LlmAgent instance."""
        assert isinstance(agent_debugger, LlmAgent)

    def test_agent_debugger_has_name(self):
        """Verify agent_debugger has a non-empty name."""
        assert agent_debugger.name
        assert agent_debugger.name == "agent_debugger"

    def test_agent_debugger_has_model(self):
        """Verify agent_debugger has a model configured."""
        assert agent_debugger.model is not None
        model_name = (
            agent_debugger.model
            if isinstance(agent_debugger.model, str)
            else str(agent_debugger.model)
        )
        assert len(model_name) > 0

    def test_agent_debugger_has_tools(self):
        """Verify agent_debugger has a non-empty tools list."""
        assert agent_debugger.tools
        assert len(agent_debugger.tools) > 0

    def test_agent_debugger_has_description(self):
        """Verify agent_debugger has a description."""
        assert agent_debugger.description
        assert "agent" in agent_debugger.description.lower()

    def test_agent_debugger_tools_include_agent_trace_tools(self):
        """Verify agent_debugger tools include agent trace analysis tools."""
        tool_names = [
            getattr(t, "name", getattr(t, "__name__", str(t)))
            for t in agent_debugger.tools
        ]
        assert "list_agent_traces" in tool_names
        assert "reconstruct_agent_interaction" in tool_names
        assert "analyze_agent_token_usage" in tool_names
        assert "detect_agent_anti_patterns" in tool_names

    def test_agent_debugger_tools_include_observability_tools(self):
        """Verify agent_debugger tools include general observability tools."""
        tool_names = [
            getattr(t, "name", getattr(t, "__name__", str(t)))
            for t in agent_debugger.tools
        ]
        assert "fetch_trace" in tool_names
        assert "list_log_entries" in tool_names
        assert "list_traces" in tool_names


class TestAgentDebuggerPrompt:
    """Tests for the AGENT_DEBUGGER_PROMPT constant."""

    def test_prompt_is_non_empty_string(self):
        """Verify AGENT_DEBUGGER_PROMPT is a non-empty string."""
        assert isinstance(AGENT_DEBUGGER_PROMPT, str)
        assert len(AGENT_DEBUGGER_PROMPT) > 100

    def test_prompt_contains_role(self):
        """Verify prompt defines the agent role."""
        assert "<role>" in AGENT_DEBUGGER_PROMPT
        assert "Agent Debugger" in AGENT_DEBUGGER_PROMPT

    def test_prompt_contains_domain_knowledge(self):
        """Verify prompt includes GenAI semantic conventions."""
        assert "<domain_knowledge>" in AGENT_DEBUGGER_PROMPT
        assert "gen_ai.operation.name" in AGENT_DEBUGGER_PROMPT

    def test_prompt_contains_anti_patterns(self):
        """Verify prompt documents anti-patterns to detect."""
        assert "<anti_patterns>" in AGENT_DEBUGGER_PROMPT
        assert "Excessive Retries" in AGENT_DEBUGGER_PROMPT
        assert "Token Waste" in AGENT_DEBUGGER_PROMPT

    def test_prompt_contains_output_format(self):
        """Verify prompt defines output format."""
        assert "<output_format>" in AGENT_DEBUGGER_PROMPT
