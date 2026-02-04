from sre_agent.agent import TOOL_NAME_MAP, base_tools
from sre_agent.tools.config import TOOL_DEFINITIONS


def test_tool_name_map_consistency():
    """Verify that all tools in TOOL_NAME_MAP have corresponding definitions in TOOL_DEFINITIONS."""
    defined_tool_names = {config.name for config in TOOL_DEFINITIONS}
    mapped_tool_names = set(TOOL_NAME_MAP.keys())

    # Tools in map but missing from definitions
    missing_definitions = mapped_tool_names - defined_tool_names

    # We allow some exceptions if they are truly internal, but ideally they should all be defined
    # to be configurable.
    allowed_missing_defs = set()

    actual_missing = missing_definitions - allowed_missing_defs
    assert not actual_missing, (
        f"Tools in TOOL_NAME_MAP missing from TOOL_DEFINITIONS: {actual_missing}"
    )


def test_tool_definitions_consistency():
    """Verify that all tools in TOOL_DEFINITIONS are also presence in TOOL_NAME_MAP or list of orchestration tools."""
    defined_tool_names = {config.name for config in TOOL_DEFINITIONS}
    mapped_tool_names = set(TOOL_NAME_MAP.keys())

    # Tools in definitions but missing from map
    missing_from_map = defined_tool_names - mapped_tool_names

    # Some tools might be orchestration tools that don't need to be in TOOL_NAME_MAP
    # if they are handled by other mechanisms, but they should generally be in base_tools.
    # However, for the agent to use them, they should be in TOOL_NAME_MAP.

    # For now, let's see which ones are missing.
    allowed_missing_map = set()

    actual_missing = missing_from_map - allowed_missing_map
    assert not actual_missing, (
        f"Tools in TOOL_DEFINITIONS missing from TOOL_NAME_MAP: {actual_missing}"
    )


def test_base_tools_presence():
    """Verify that all tools in base_tools have definitions."""
    defined_tool_names = {config.name for config in TOOL_DEFINITIONS}

    # We need to map tool functions to names
    tool_to_name = {v: k for k, v in TOOL_NAME_MAP.items()}

    missing_defs = []
    for tool in base_tools:
        name = tool_to_name.get(tool)
        if name and name not in defined_tool_names:
            missing_defs.append(name)

    assert not missing_defs, (
        f"Tools in base_tools missing from TOOL_DEFINITIONS: {missing_defs}"
    )
