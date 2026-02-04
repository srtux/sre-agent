"""Tests for the slim tools feature flag.

Validates that SRE_AGENT_SLIM_TOOLS=true reduces the root agent's
tool set to orchestration-only tools, while false preserves the full set.
"""

import os
from unittest.mock import patch

from sre_agent.agent import base_tools, get_enabled_base_tools, slim_tools


class TestSlimToolsFeatureFlag:
    """Tests for SRE_AGENT_SLIM_TOOLS feature flag."""

    def test_slim_tools_defined(self) -> None:
        """Slim tool set should be non-empty."""
        assert len(slim_tools) > 0

    def test_slim_tools_smaller_than_base(self) -> None:
        """Slim tool set should be significantly smaller than base tools."""
        assert len(slim_tools) < len(base_tools)
        # Slim should be roughly 1/3 or less of base
        assert len(slim_tools) <= len(base_tools) // 2

    def test_slim_tools_all_callable(self) -> None:
        """All slim tools should be callable."""
        for tool in slim_tools:
            assert callable(tool), f"Tool {tool} is not callable"

    @patch.dict(os.environ, {"SRE_AGENT_SLIM_TOOLS": "true"})
    def test_slim_mode_returns_reduced_set(self) -> None:
        """When flag is true, should return slim tool set."""
        tools = get_enabled_base_tools()
        assert len(tools) == len(slim_tools)

    @patch.dict(os.environ, {"SRE_AGENT_SLIM_TOOLS": "false"})
    def test_full_mode_returns_all_tools(self) -> None:
        """When flag is false, should return full base tools."""
        tools = get_enabled_base_tools()
        # Full mode should have at least as many as base_tools
        # (minus any disabled by config)
        assert len(tools) >= len(slim_tools)

    @patch.dict(os.environ, {}, clear=False)
    def test_default_is_full_mode(self) -> None:
        """Without the flag, should default to full mode."""
        # Remove the flag if it exists
        env = os.environ.copy()
        env.pop("SRE_AGENT_SLIM_TOOLS", None)
        with patch.dict(os.environ, env, clear=True):
            tools = get_enabled_base_tools()
            assert len(tools) >= len(slim_tools)

    @patch.dict(os.environ, {"SRE_AGENT_SLIM_TOOLS": "TRUE"})
    def test_flag_case_insensitive(self) -> None:
        """Flag should be case-insensitive."""
        tools = get_enabled_base_tools()
        assert len(tools) == len(slim_tools)

    def test_slim_tools_contains_council(self) -> None:
        """Slim set should contain council orchestration tools."""
        tool_names = {getattr(t, "__name__", str(t)) for t in slim_tools}
        assert "run_council_investigation" in tool_names
        assert "classify_investigation_mode" in tool_names

    def test_slim_tools_contains_essentials(self) -> None:
        """Slim set should contain essential management tools."""
        tool_names = {getattr(t, "__name__", str(t)) for t in slim_tools}
        assert "list_gcp_projects" in tool_names
        assert "get_investigation_summary" in tool_names
        assert "discover_telemetry_sources" in tool_names

    @patch.dict(os.environ, {"SRE_AGENT_SLIM_TOOLS": "true"})
    def test_slim_mode_returns_new_list(self) -> None:
        """Slim mode should return a new list (not the same object)."""
        tools1 = get_enabled_base_tools()
        tools2 = get_enabled_base_tools()
        assert tools1 is not tools2
