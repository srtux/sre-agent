"""Test integration of Memory Module."""

from sre_agent.agent import TOOL_NAME_MAP
from sre_agent.tools.config import ToolCategory, get_tool_config_manager


def test_memory_tools_registered():
    """Verify memory tools are registered in agent.py."""
    assert "add_finding_to_memory" in TOOL_NAME_MAP
    assert "search_memory" in TOOL_NAME_MAP


def test_memory_tools_enabled():
    """Verify memory tools are enabled in config.py."""
    manager = get_tool_config_manager()
    enabled = manager.get_enabled_tools()

    assert "add_finding_to_memory" in enabled
    assert "search_memory" in enabled


def test_tool_categories():
    """Verify memory tools have correct category."""
    manager = get_tool_config_manager()

    config_add = manager.get_config("add_finding_to_memory")
    assert config_add.category == ToolCategory.MEMORY

    config_search = manager.get_config("search_memory")
    assert config_search.category == ToolCategory.MEMORY
