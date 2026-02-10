from sre_agent.agent import base_tools, sre_agent
from sre_agent.tools.clients.monitoring import list_time_series


def test_sre_agent_has_list_time_series():
    """Verify that list_time_series is included in the agent's tools."""
    # check if list_time_series is in the base_tools list
    assert list_time_series in base_tools

    # Check if list_time_series is in the agent's tools
    # Note: sre_agent.tools might be a list of functions or tool objects depending on LlmAgent implementation
    # The LlmAgent usually wraps tools, but let's check if we can find it.

    # In agent.py: tools=get_enabled_base_tools() (which defaults to slim_tools)
    import os

    if os.environ.get("SRE_AGENT_SLIM_TOOLS", "true").lower() != "false":
        # In slim mode (default), list_time_series is delegated to metrics_analyzer panel
        assert list_time_series not in sre_agent.tools
    else:
        # In full mode, it's present
        assert list_time_series in sre_agent.tools
