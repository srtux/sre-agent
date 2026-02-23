"""Cymbal Shops AI Shopping Assistant scenario definition.

Defines the full Cymbal Shops AI Shopping Assistant architecture as data:
agents, tools, MCP servers, users, infrastructure, and the incident timeline
for a 7-day demo window featuring a bad deployment (v2.4.1) that causes
anomalous tool-call patterns in the Product Discovery agent.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AgentDef:
    """Definition of an agent in the Cymbal Assistant hierarchy."""

    name: str
    display_name: str
    agent_type: str  # root | sub_agent
    model: str
    tools: list[str] = field(default_factory=list)
    delegates_to: list[str] = field(default_factory=list)
    description: str = ""


@dataclass(frozen=True)
class MCPServerDef:
    """Definition of an MCP server backing agent tools."""

    name: str
    display_name: str
    platform: str  # cloud_run
    tools: list[str] = field(default_factory=list)
    url: str = ""


@dataclass(frozen=True)
class DemoUser:
    """A synthetic user for demo session generation."""

    user_id: str
    display_name: str
    city: str
    country: str
    gcp_region: str
    geo_region: str


@dataclass(frozen=True)
class JourneyTemplate:
    """A user journey template for session generation."""

    journey_type: str
    display_name: str
    weight_pct: int
    turns_range: tuple[int, int]
    agents_involved: list[str] = field(default_factory=list)
    description: str = ""


# ---------------------------------------------------------------------------
# Project & Deployment Constants
# ---------------------------------------------------------------------------
DEMO_PROJECT_ID = "cymbal-shops-demo"
DEMO_REGION = "us-central1"
REASONING_ENGINE_ID = (
    "projects/cymbal-shops-demo/locations/us-central1"
    "/reasoningEngines/cymbal-assistant-001"
)
AGENT_VERSION_NORMAL = "v2.4.0"
AGENT_VERSION_BAD = "v2.4.1"

# ---------------------------------------------------------------------------
# OTel Resource Attributes
# ---------------------------------------------------------------------------
RESOURCE_ATTRIBUTES: dict[str, str] = {
    "service.name": "cymbal-assistant",
    "service.version": AGENT_VERSION_NORMAL,
    "cloud.provider": "gcp",
    "cloud.region": DEMO_REGION,
    "cloud.platform": "gcp.agent_engine",
    "cloud.resource_id": REASONING_ENGINE_ID,
}

# ---------------------------------------------------------------------------
# Agent Definitions (7 agents)
# ---------------------------------------------------------------------------
AGENTS: dict[str, AgentDef] = {
    "cymbal-assistant": AgentDef(
        name="cymbal-assistant",
        display_name="Cymbal Shopping Assistant",
        agent_type="root",
        model="gemini-2.5-flash",
        tools=[],
        delegates_to=[
            "product-discovery",
            "order-management",
            "checkout",
            "support",
        ],
        description="Root orchestrator for the Cymbal Shops AI Shopping Assistant",
    ),
    "product-discovery": AgentDef(
        name="product-discovery",
        display_name="Product Discovery Agent",
        agent_type="sub_agent",
        model="gemini-2.5-flash",
        tools=[
            "search_products",
            "get_product_details",
            "get_reviews",
        ],
        delegates_to=["personalization"],
        description="Handles product search, browsing, and detail retrieval",
    ),
    "order-management": AgentDef(
        name="order-management",
        display_name="Order Management Agent",
        agent_type="sub_agent",
        model="gemini-2.5-flash",
        tools=[
            "get_order_status",
            "list_orders",
            "create_return",
            "modify_order",
            "get_customer_profile",
        ],
        delegates_to=["fulfillment"],
        description="Manages order lifecycle: status, modifications, and returns",
    ),
    "checkout": AgentDef(
        name="checkout",
        display_name="Checkout Agent",
        agent_type="sub_agent",
        model="gemini-2.5-flash",
        tools=[
            "add_to_cart",
            "get_cart",
            "process_payment",
            "validate_coupon",
            "get_payment_methods",
        ],
        delegates_to=["personalization", "fulfillment"],
        description="Handles cart management, payment processing, and checkout flow",
    ),
    "support": AgentDef(
        name="support",
        display_name="Customer Support Agent",
        agent_type="sub_agent",
        model="gemini-2.5-flash",
        tools=[
            "search_knowledge_base",
            "create_ticket",
            "escalate_to_human",
            "get_customer_profile",
            "get_loyalty_points",
        ],
        delegates_to=[],
        description="Handles customer support queries, tickets, and escalations",
    ),
    "personalization": AgentDef(
        name="personalization",
        display_name="Personalization Agent",
        agent_type="sub_agent",
        model="gemini-2.5-pro",
        tools=[
            "get_customer_profile",
            "get_purchase_history",
            "update_preferences",
            "get_personalized_recs",
            "get_similar_products",
            "get_loyalty_points",
        ],
        delegates_to=[],
        description="Provides personalized recommendations and preference management",
    ),
    "fulfillment": AgentDef(
        name="fulfillment",
        display_name="Fulfillment Agent",
        agent_type="sub_agent",
        model="gemini-2.5-flash",
        tools=[
            "check_availability",
            "get_warehouse_stock",
            "reserve_inventory",
            "calculate_shipping",
            "get_delivery_estimate",
            "track_shipment",
        ],
        delegates_to=[],
        description="Handles inventory, shipping, and delivery tracking",
    ),
}

# ---------------------------------------------------------------------------
# MCP Server Definitions (8 servers)
# ---------------------------------------------------------------------------
MCP_SERVERS: dict[str, MCPServerDef] = {
    "catalog-mcp": MCPServerDef(
        name="catalog-mcp",
        display_name="Product Catalog MCP",
        platform="cloud_run",
        tools=["search_products", "get_product_details", "get_reviews"],
        url="https://catalog-mcp-cymbal-shops-demo.a.run.app",
    ),
    "recommendation-mcp": MCPServerDef(
        name="recommendation-mcp",
        display_name="Recommendation MCP",
        platform="cloud_run",
        tools=["get_personalized_recs", "get_trending", "get_similar_products"],
        url="https://recommendation-mcp-cymbal-shops-demo.a.run.app",
    ),
    "order-mcp": MCPServerDef(
        name="order-mcp",
        display_name="Order Management MCP",
        platform="cloud_run",
        tools=["get_order_status", "list_orders", "create_return", "modify_order"],
        url="https://order-mcp-cymbal-shops-demo.a.run.app",
    ),
    "payment-mcp": MCPServerDef(
        name="payment-mcp",
        display_name="Payment Processing MCP",
        platform="cloud_run",
        tools=["process_payment", "validate_coupon", "get_payment_methods"],
        url="https://payment-mcp-cymbal-shops-demo.a.run.app",
    ),
    "inventory-mcp": MCPServerDef(
        name="inventory-mcp",
        display_name="Inventory MCP",
        platform="cloud_run",
        tools=["check_availability", "get_warehouse_stock", "reserve_inventory"],
        url="https://inventory-mcp-cymbal-shops-demo.a.run.app",
    ),
    "customer-mcp": MCPServerDef(
        name="customer-mcp",
        display_name="Customer Data MCP",
        platform="cloud_run",
        tools=[
            "get_customer_profile",
            "get_purchase_history",
            "update_preferences",
            "get_loyalty_points",
        ],
        url="https://customer-mcp-cymbal-shops-demo.a.run.app",
    ),
    "logistics-mcp": MCPServerDef(
        name="logistics-mcp",
        display_name="Logistics MCP",
        platform="cloud_run",
        tools=["calculate_shipping", "get_delivery_estimate", "track_shipment"],
        url="https://logistics-mcp-cymbal-shops-demo.a.run.app",
    ),
    "support-mcp": MCPServerDef(
        name="support-mcp",
        display_name="Customer Support MCP",
        platform="cloud_run",
        tools=["search_knowledge_base", "create_ticket", "escalate_to_human"],
        url="https://support-mcp-cymbal-shops-demo.a.run.app",
    ),
}

# ---------------------------------------------------------------------------
# Tool-to-MCP mapping (auto-built from MCP_SERVERS + manual overrides)
# ---------------------------------------------------------------------------
TOOL_TO_MCP: dict[str, str] = {}
for _server_name, _server_def in MCP_SERVERS.items():
    for _tool_name in _server_def.tools:
        TOOL_TO_MCP[_tool_name] = _server_name

# Manual overrides for tools not directly listed in an MCP server
TOOL_TO_MCP["add_to_cart"] = "inventory-mcp"
TOOL_TO_MCP["get_cart"] = "inventory-mcp"

# ---------------------------------------------------------------------------
# Demo Users (12 users)
# ---------------------------------------------------------------------------
DEMO_USERS: list[DemoUser] = [
    DemoUser(
        user_id="alice@gmail.com",
        display_name="Alice Chen",
        city="San Francisco",
        country="US",
        gcp_region="us-west1",
        geo_region="US-CA",
    ),
    DemoUser(
        user_id="bob@outlook.com",
        display_name="Bob Martinez",
        city="New York",
        country="US",
        gcp_region="us-east4",
        geo_region="US-NY",
    ),
    DemoUser(
        user_id="carol@yahoo.com",
        display_name="Carol Johnson",
        city="Chicago",
        country="US",
        gcp_region="us-central1",
        geo_region="US-IL",
    ),
    DemoUser(
        user_id="dave@gmail.com",
        display_name="Dave Williams",
        city="London",
        country="GB",
        gcp_region="europe-west2",
        geo_region="GB-LND",
    ),
    DemoUser(
        user_id="emma@gmail.com",
        display_name="Emma Tanaka",
        city="Tokyo",
        country="JP",
        gcp_region="asia-northeast1",
        geo_region="JP-13",
    ),
    DemoUser(
        user_id="frank@company.com",
        display_name="Frank O'Brien",
        city="Sydney",
        country="AU",
        gcp_region="australia-southeast1",
        geo_region="AU-NSW",
    ),
    DemoUser(
        user_id="grace@gmail.com",
        display_name="Grace Kim",
        city="Toronto",
        country="CA",
        gcp_region="northamerica-northeast1",
        geo_region="CA-ON",
    ),
    DemoUser(
        user_id="hiro@outlook.com",
        display_name="Hiro Silva",
        city="Sao Paulo",
        country="BR",
        gcp_region="southamerica-east1",
        geo_region="BR-SP",
    ),
    DemoUser(
        user_id="isabella@gmail.com",
        display_name="Isabella Patel",
        city="Mumbai",
        country="IN",
        gcp_region="asia-south1",
        geo_region="IN-MH",
    ),
    DemoUser(
        user_id="james@yahoo.com",
        display_name="James Muller",
        city="Berlin",
        country="DE",
        gcp_region="europe-west3",
        geo_region="DE-BE",
    ),
    DemoUser(
        user_id="kate@gmail.com",
        display_name="Kate Thompson",
        city="Seattle",
        country="US",
        gcp_region="us-west1",
        geo_region="US-WA",
    ),
    DemoUser(
        user_id="liam@outlook.com",
        display_name="Liam Dubois",
        city="Paris",
        country="FR",
        gcp_region="europe-west1",
        geo_region="FR-IDF",
    ),
]

# ---------------------------------------------------------------------------
# Journey Templates (6 journeys, weights sum to 100)
# ---------------------------------------------------------------------------
JOURNEY_TEMPLATES: list[JourneyTemplate] = [
    JourneyTemplate(
        journey_type="search_browse_buy",
        display_name="Search, Browse & Buy",
        weight_pct=30,
        turns_range=(5, 7),
        agents_involved=[
            "product-discovery",
            "personalization",
            "checkout",
            "fulfillment",
        ],
        description="Full purchase flow: search products, get recommendations, checkout",
    ),
    JourneyTemplate(
        journey_type="search_compare",
        display_name="Search & Compare",
        weight_pct=25,
        turns_range=(3, 5),
        agents_involved=["product-discovery", "personalization"],
        description="Browse and compare products without purchasing",
    ),
    JourneyTemplate(
        journey_type="order_tracking",
        display_name="Order Tracking",
        weight_pct=15,
        turns_range=(2, 3),
        agents_involved=["order-management", "fulfillment"],
        description="Check order status and delivery tracking",
    ),
    JourneyTemplate(
        journey_type="return_refund",
        display_name="Return & Refund",
        weight_pct=10,
        turns_range=(4, 6),
        agents_involved=["order-management", "support"],
        description="Initiate a return and request refund",
    ),
    JourneyTemplate(
        journey_type="support_question",
        display_name="Support Question",
        weight_pct=10,
        turns_range=(2, 4),
        agents_involved=["support"],
        description="Ask a support question or create a ticket",
    ),
    JourneyTemplate(
        journey_type="browse_abandon_return",
        display_name="Browse, Abandon & Return",
        weight_pct=10,
        turns_range=(6, 8),
        agents_involved=["product-discovery", "personalization", "checkout"],
        description="Add items to cart, abandon checkout, then return later",
    ),
]

# ---------------------------------------------------------------------------
# Incident Timeline (days relative to 7-day window start)
# ---------------------------------------------------------------------------
INCIDENT_TIMELINE: list[dict[str, object]] = [
    {
        "event_id": "release_v2.4.1",
        "day": 3,
        "hour": 2,
        "minute": 15,
        "description": "Product Discovery Agent prompt updated",
    },
    {
        "event_id": "degradation_start",
        "day": 3,
        "hour": 2,
        "minute": 30,
        "description": "Tool call volume increasing",
    },
    {
        "event_id": "rate_limiting_start",
        "day": 3,
        "hour": 8,
        "minute": 0,
        "description": "Payment MCP rate limiting (429s)",
    },
    {
        "event_id": "alert_fired",
        "day": 5,
        "hour": 11,
        "minute": 30,
        "description": "Anomalous tool call volume alert",
    },
    {
        "event_id": "rollback_v2.4.0",
        "day": 5,
        "hour": 15,
        "minute": 45,
        "description": "Rolled back to v2.4.0",
    },
    {
        "event_id": "recovery_start",
        "day": 5,
        "hour": 16,
        "minute": 0,
        "description": "Metrics returning to baseline",
    },
]

# ---------------------------------------------------------------------------
# Anomaly Definitions
# ---------------------------------------------------------------------------
ANOMALOUS_TOOLS_IN_PRODUCT_DISCOVERY: list[str] = [
    "check_availability",
    "validate_coupon",
]

ANOMALOUS_DELEGATION: str = "fulfillment"
