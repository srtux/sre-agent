"""Tests for tool configuration integration with the agent.

Tests the new functions added to agent.py for tool enable/disable functionality:
- get_enabled_tools()
- get_enabled_base_tools()
- is_tool_enabled()
- create_configured_agent()
"""

import pytest

from sre_agent.agent import (
    TOOL_NAME_MAP,
    base_tools,
    create_configured_agent,
    get_enabled_base_tools,
    get_enabled_tools,
    is_tool_enabled,
)
from sre_agent.tools.config import get_tool_config_manager


class TestGetEnabledTools:
    """Tests for get_enabled_tools function."""

    def test_returns_list(self) -> None:
        """Test that get_enabled_tools returns a list."""
        tools = get_enabled_tools()
        assert isinstance(tools, list)

    def test_returns_tool_functions(self) -> None:
        """Test that returned items are callable."""
        tools = get_enabled_tools()
        for tool in tools:
            assert callable(tool)

    def test_respects_disabled_tools(self) -> None:
        """Test that disabled tools are not returned."""
        manager = get_tool_config_manager()

        # Get a tool that's enabled and in TOOL_NAME_MAP
        test_tool = "list_traces"
        assert test_tool in TOOL_NAME_MAP

        # Disable it
        manager.set_enabled(test_tool, False)

        try:
            tools = get_enabled_tools()
            tool_func = TOOL_NAME_MAP[test_tool]
            assert tool_func not in tools
        finally:
            # Re-enable it
            manager.set_enabled(test_tool, True)


class TestGetEnabledBaseTools:
    """Tests for get_enabled_base_tools function."""

    def test_returns_list(self) -> None:
        """Test that get_enabled_base_tools returns a list."""
        tools = get_enabled_base_tools()
        assert isinstance(tools, list)

    def test_returns_subset_of_base_tools(self) -> None:
        """Test that returned tools are subset of base_tools."""
        filtered_tools = get_enabled_base_tools()
        # All returned tools should be in base_tools
        for tool in filtered_tools:
            assert tool in base_tools

    def test_respects_disabled_tools(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that disabled tools are filtered from base_tools."""
        monkeypatch.setenv("SRE_AGENT_SLIM_TOOLS", "false")
        manager = get_tool_config_manager()

        # Find a tool that's both in base_tools and TOOL_NAME_MAP
        test_tool_name = None
        test_tool_func = None
        tool_to_name = {v: k for k, v in TOOL_NAME_MAP.items()}

        for tool in base_tools:
            if tool in tool_to_name:
                test_tool_name = tool_to_name[tool]
                test_tool_func = tool
                break

        if test_tool_name is None:
            pytest.skip("No tool found that's in both base_tools and TOOL_NAME_MAP")

        # Disable it
        manager.set_enabled(test_tool_name, False)

        try:
            tools = get_enabled_base_tools()
            assert test_tool_func not in tools
        finally:
            # Re-enable it
            manager.set_enabled(test_tool_name, True)

    def test_includes_orchestration_tools(self) -> None:
        """Test that orchestration tools are included even if not in TOOL_NAME_MAP."""
        # Orchestration tools like run_aggregate_analysis should always be included
        # They might not be in TOOL_NAME_MAP but are in base_tools
        from sre_agent.agent import run_aggregate_analysis

        tools = get_enabled_base_tools()
        assert run_aggregate_analysis in tools


class TestIsToolEnabled:
    """Tests for is_tool_enabled function."""

    def test_enabled_tool(self) -> None:
        """Test checking an enabled tool."""
        manager = get_tool_config_manager()
        manager.set_enabled("list_traces", True)

        assert is_tool_enabled("list_traces") is True

    def test_disabled_tool(self) -> None:
        """Test checking a disabled tool."""
        manager = get_tool_config_manager()
        manager.set_enabled("list_traces", False)

        try:
            assert is_tool_enabled("list_traces") is False
        finally:
            manager.set_enabled("list_traces", True)

    def test_nonexistent_tool(self) -> None:
        """Test checking a non-existent tool."""
        assert is_tool_enabled("nonexistent_tool_xyz") is False


class TestCreateConfiguredAgent:
    """Tests for create_configured_agent function."""

    def test_returns_agent(self) -> None:
        """Test that create_configured_agent returns an LlmAgent."""
        from google.adk.agents import LlmAgent

        agent = create_configured_agent()
        # The agent is wrapped by emojify_agent, but should still be an LlmAgent
        assert isinstance(agent, LlmAgent)

    def test_returns_same_root_agent(self) -> None:
        """Test that create_configured_agent returns the root_agent instance.

        Note: Due to ADK's design, sub-agents can only be bound to one parent,
        so create_configured_agent returns the existing root_agent.
        """
        from sre_agent.agent import root_agent

        agent = create_configured_agent()
        assert agent is root_agent

    def test_has_sub_agents(self) -> None:
        """Test that the agent has sub-agents configured."""
        agent = create_configured_agent()
        assert len(agent.sub_agents) == 7  # 7 sub-agents

    def test_has_tools(self) -> None:
        """Test that the agent has tools configured."""
        agent = create_configured_agent()
        assert len(agent.tools) > 0


class TestToolNameMapConsistency:
    """Tests for TOOL_NAME_MAP consistency."""

    def test_all_mapped_tools_are_callable(self) -> None:
        """Test that all tools in TOOL_NAME_MAP are callable."""
        for name, tool in TOOL_NAME_MAP.items():
            assert callable(tool), f"Tool {name} is not callable"

    def test_tool_names_match_function_names(self) -> None:
        """Test that tool names are reasonable (not checking exact match)."""
        for name in TOOL_NAME_MAP:
            # Tool names should be lowercase with underscores
            assert name == name.lower(), f"Tool name {name} should be lowercase"
            assert " " not in name, f"Tool name {name} should not have spaces"


class TestBaseToolsConsistency:
    """Tests for base_tools consistency."""

    def test_base_tools_are_callable(self) -> None:
        """Test that all tools in base_tools are callable."""
        for tool in base_tools:
            assert callable(tool)

    def test_base_tools_not_empty(self) -> None:
        """Test that base_tools is not empty."""
        assert len(base_tools) > 0

    def test_critical_tools_in_base_tools(self) -> None:
        """Test that critical tools are in base_tools."""
        from sre_agent.tools import fetch_trace, list_log_entries, query_promql

        assert fetch_trace in base_tools
        assert list_log_entries in base_tools
        assert query_promql in base_tools
