from sre_agent.agent import base_tools, sre_agent
from sre_agent.tools.clients.monitoring import list_time_series


def test_sre_agent_has_list_time_series():
    """Verify that list_time_series is included in the agent's tools."""
    # check if list_time_series is in the base_tools list
    assert list_time_series in base_tools

    # OPT-2: list_time_series is now in slim_tools for DIRECT routing tier
    assert list_time_series in sre_agent.tools
