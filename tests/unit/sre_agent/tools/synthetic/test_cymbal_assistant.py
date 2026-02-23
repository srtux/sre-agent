"""Tests for Cymbal Assistant scenario definition.

Validates agent hierarchy, MCP servers, demo users, journey templates,
resource attributes, and incident timeline for the AI Shopping Assistant
demo scenario.
"""

from __future__ import annotations

from sre_agent.tools.synthetic.cymbal_assistant import (
    AGENTS,
    ANOMALOUS_DELEGATION,
    ANOMALOUS_TOOLS_IN_PRODUCT_DISCOVERY,
    DEMO_USERS,
    INCIDENT_TIMELINE,
    JOURNEY_TEMPLATES,
    MCP_SERVERS,
    RESOURCE_ATTRIBUTES,
    TOOL_TO_MCP,
    AgentDef,
    DemoUser,
    JourneyTemplate,
    MCPServerDef,
)


# ---------------------------------------------------------------------------
# Agent Definitions
# ---------------------------------------------------------------------------


class TestAgentDefinitions:
    """Validate AGENTS dictionary and agent hierarchy."""

    def test_root_agent_exists(self) -> None:
        root = AGENTS["cymbal-assistant"]
        assert root.agent_type == "root"
        assert root.model == "gemini-2.5-flash"

    def test_six_sub_agents(self) -> None:
        sub_agents = [a for a in AGENTS.values() if a.agent_type == "sub_agent"]
        assert len(sub_agents) == 6

    def test_agent_to_agent_invocations(self) -> None:
        # product-discovery delegates to personalization
        assert "personalization" in AGENTS["product-discovery"].delegates_to

        # checkout delegates to personalization AND fulfillment
        checkout_delegates = AGENTS["checkout"].delegates_to
        assert "personalization" in checkout_delegates
        assert "fulfillment" in checkout_delegates

        # order-management delegates to fulfillment
        assert "fulfillment" in AGENTS["order-management"].delegates_to

    def test_all_tools_mapped_to_mcp_servers(self) -> None:
        """Every tool declared in every agent must exist in some MCP server."""
        all_mcp_tools: set[str] = set()
        for server in MCP_SERVERS.values():
            all_mcp_tools.update(server.tools)
        # Also include manual TOOL_TO_MCP overrides
        all_mcp_tools.update(TOOL_TO_MCP.keys())

        for agent_name, agent_def in AGENTS.items():
            for tool in agent_def.tools:
                assert tool in all_mcp_tools, (
                    f"Agent '{agent_name}' tool '{tool}' not found in any MCP server"
                )

    def test_seven_total_agents(self) -> None:
        assert len(AGENTS) == 7

    def test_agent_keys_match_names(self) -> None:
        for key, agent_def in AGENTS.items():
            assert key == agent_def.name, (
                f"Key '{key}' != agent name '{agent_def.name}'"
            )

    def test_all_agents_are_agentdef_instances(self) -> None:
        for key, agent_def in AGENTS.items():
            assert isinstance(agent_def, AgentDef), f"{key} is not an AgentDef"

    def test_delegates_reference_known_agents(self) -> None:
        for key, agent_def in AGENTS.items():
            for delegate in agent_def.delegates_to:
                assert delegate in AGENTS, (
                    f"Agent '{key}' delegates to unknown agent '{delegate}'"
                )


# ---------------------------------------------------------------------------
# MCP Servers
# ---------------------------------------------------------------------------


class TestMCPServers:
    """Validate MCP_SERVERS dictionary."""

    def test_eight_mcp_servers(self) -> None:
        assert len(MCP_SERVERS) == 8

    def test_all_cloud_run(self) -> None:
        for name, server in MCP_SERVERS.items():
            assert server.platform == "cloud_run", (
                f"MCP server '{name}' platform is '{server.platform}', expected 'cloud_run'"
            )

    def test_server_keys_match_names(self) -> None:
        for key, server in MCP_SERVERS.items():
            assert key == server.name, (
                f"Key '{key}' != server name '{server.name}'"
            )

    def test_all_servers_are_mcpserverdef_instances(self) -> None:
        for key, server in MCP_SERVERS.items():
            assert isinstance(server, MCPServerDef), f"{key} is not an MCPServerDef"

    def test_all_servers_have_tools(self) -> None:
        for name, server in MCP_SERVERS.items():
            assert len(server.tools) > 0, f"MCP server '{name}' has no tools"

    def test_all_servers_have_urls(self) -> None:
        for name, server in MCP_SERVERS.items():
            assert len(server.url) > 0, f"MCP server '{name}' has no URL"


# ---------------------------------------------------------------------------
# Demo Users
# ---------------------------------------------------------------------------


class TestDemoUsers:
    """Validate DEMO_USERS list."""

    def test_twelve_users(self) -> None:
        assert len(DEMO_USERS) == 12

    def test_unique_regions(self) -> None:
        regions = {user.gcp_region for user in DEMO_USERS}
        assert len(regions) >= 8, (
            f"Expected at least 8 unique gcp_regions, got {len(regions)}"
        )

    def test_all_users_are_demouser_instances(self) -> None:
        for user in DEMO_USERS:
            assert isinstance(user, DemoUser)

    def test_unique_user_ids(self) -> None:
        user_ids = [user.user_id for user in DEMO_USERS]
        assert len(user_ids) == len(set(user_ids)), "Duplicate user_ids found"

    def test_user_fields_non_empty(self) -> None:
        for user in DEMO_USERS:
            assert len(user.user_id) > 0
            assert len(user.display_name) > 0
            assert len(user.city) > 0
            assert len(user.country) > 0
            assert len(user.gcp_region) > 0
            assert len(user.geo_region) > 0


# ---------------------------------------------------------------------------
# Journey Templates
# ---------------------------------------------------------------------------


class TestJourneyTemplates:
    """Validate JOURNEY_TEMPLATES list."""

    def test_six_journey_types(self) -> None:
        assert len(JOURNEY_TEMPLATES) == 6

    def test_weights_sum_to_100(self) -> None:
        total = sum(j.weight_pct for j in JOURNEY_TEMPLATES)
        assert total == 100, f"Journey weights sum to {total}, expected 100"

    def test_all_journeys_are_journeytemplate_instances(self) -> None:
        for journey in JOURNEY_TEMPLATES:
            assert isinstance(journey, JourneyTemplate)

    def test_unique_journey_types(self) -> None:
        types = [j.journey_type for j in JOURNEY_TEMPLATES]
        assert len(types) == len(set(types)), "Duplicate journey types found"

    def test_turns_range_valid(self) -> None:
        for journey in JOURNEY_TEMPLATES:
            lo, hi = journey.turns_range
            assert lo > 0, f"{journey.journey_type}: turns_range low must be > 0"
            assert hi >= lo, (
                f"{journey.journey_type}: turns_range ({lo}, {hi}) invalid"
            )

    def test_agents_involved_are_known(self) -> None:
        for journey in JOURNEY_TEMPLATES:
            for agent_name in journey.agents_involved:
                assert agent_name in AGENTS, (
                    f"Journey '{journey.journey_type}' references unknown agent "
                    f"'{agent_name}'"
                )


# ---------------------------------------------------------------------------
# Resource Attributes
# ---------------------------------------------------------------------------


class TestResourceAttributes:
    """Validate OTel RESOURCE_ATTRIBUTES."""

    def test_cloud_platform_is_agent_engine(self) -> None:
        assert RESOURCE_ATTRIBUTES["cloud.platform"] == "gcp.agent_engine"

    def test_service_name(self) -> None:
        assert RESOURCE_ATTRIBUTES["service.name"] == "cymbal-assistant"

    def test_has_required_keys(self) -> None:
        required_keys = {
            "service.name",
            "service.version",
            "cloud.provider",
            "cloud.region",
            "cloud.platform",
            "cloud.resource_id",
        }
        assert required_keys.issubset(RESOURCE_ATTRIBUTES.keys())

    def test_cloud_provider_is_gcp(self) -> None:
        assert RESOURCE_ATTRIBUTES["cloud.provider"] == "gcp"


# ---------------------------------------------------------------------------
# Incident Timeline
# ---------------------------------------------------------------------------


class TestIncidentTimeline:
    """Validate INCIDENT_TIMELINE list."""

    def test_has_release_and_rollback(self) -> None:
        event_ids = {e["event_id"] for e in INCIDENT_TIMELINE}
        assert "release_v2.4.1" in event_ids, "Missing release_v2.4.1 event"
        assert "rollback_v2.4.0" in event_ids, "Missing rollback_v2.4.0 event"

    def test_timeline_has_six_events(self) -> None:
        assert len(INCIDENT_TIMELINE) == 6

    def test_events_have_required_fields(self) -> None:
        required = {"event_id", "day", "hour", "minute", "description"}
        for i, event in enumerate(INCIDENT_TIMELINE):
            missing = required - event.keys()
            assert not missing, f"Event[{i}] missing fields: {missing}"

    def test_events_in_chronological_order(self) -> None:
        for i in range(1, len(INCIDENT_TIMELINE)):
            prev = INCIDENT_TIMELINE[i - 1]
            curr = INCIDENT_TIMELINE[i]
            prev_mins = int(str(prev["day"])) * 1440 + int(str(prev["hour"])) * 60 + int(str(prev["minute"]))
            curr_mins = int(str(curr["day"])) * 1440 + int(str(curr["hour"])) * 60 + int(str(curr["minute"]))
            assert curr_mins >= prev_mins, (
                f"Event '{curr['event_id']}' is before '{prev['event_id']}'"
            )


# ---------------------------------------------------------------------------
# Tool-to-MCP Mapping
# ---------------------------------------------------------------------------


class TestToolToMCP:
    """Validate TOOL_TO_MCP auto-built mapping."""

    def test_add_to_cart_maps_to_inventory(self) -> None:
        assert TOOL_TO_MCP["add_to_cart"] == "inventory-mcp"

    def test_get_cart_maps_to_inventory(self) -> None:
        assert TOOL_TO_MCP["get_cart"] == "inventory-mcp"

    def test_all_mcp_tools_in_mapping(self) -> None:
        """Every tool in every MCP server should appear in TOOL_TO_MCP."""
        for server_name, server in MCP_SERVERS.items():
            for tool in server.tools:
                assert tool in TOOL_TO_MCP, (
                    f"Tool '{tool}' from '{server_name}' not in TOOL_TO_MCP"
                )
                assert TOOL_TO_MCP[tool] == server_name


# ---------------------------------------------------------------------------
# Anomaly Definitions
# ---------------------------------------------------------------------------


class TestAnomalyDefinitions:
    """Validate anomaly scenario data."""

    def test_anomalous_tools_not_normally_in_product_discovery(self) -> None:
        """The anomalous tools should NOT be in product-discovery's normal tool set."""
        pd_tools = set(AGENTS["product-discovery"].tools)
        for tool in ANOMALOUS_TOOLS_IN_PRODUCT_DISCOVERY:
            assert tool not in pd_tools, (
                f"Tool '{tool}' should not be in product-discovery's normal tools"
            )

    def test_anomalous_delegation_is_known_agent(self) -> None:
        assert ANOMALOUS_DELEGATION in AGENTS

    def test_anomalous_delegation_not_normal_for_product_discovery(self) -> None:
        """Product Discovery should NOT normally delegate to the anomalous agent."""
        assert ANOMALOUS_DELEGATION not in AGENTS["product-discovery"].delegates_to
