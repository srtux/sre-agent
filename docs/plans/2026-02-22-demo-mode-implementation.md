# Demo Mode: Full-Stack Synthetic Data Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make every feature in Auto SRE work with realistic synthetic data when logged in as a guest, showcasing a Cymbal Shops AI Shopping Assistant incident investigation.

**Architecture:** Backend-side synthetic data injection — extend the existing `is_guest_mode()` / `SyntheticDataProvider` pattern. New files define the Cymbal Assistant agent architecture and generate 400 traces over 7 days (80 sessions, 12 users, multiple regions). The `agent_graph.py` router gets guest mode guards on all 17 endpoints. The chat endpoint streams pre-recorded responses with all event types (dashboard, council_graph, agent_activity, memory, trace_info). No frontend changes needed.

**Tech Stack:** Python 3.10+, FastAPI, Pydantic 2, pytest 8+, existing `SyntheticDataProvider` pattern

**Design Doc:** `docs/plans/2026-02-22-demo-mode-design.md`

---

## Task 1: Create Cymbal Assistant Scenario Definition

**Files:**
- Create: `sre_agent/tools/synthetic/cymbal_assistant.py`
- Test: `tests/unit/sre_agent/tools/synthetic/test_cymbal_assistant.py`

This file defines the entire Cymbal Shops AI Shopping Assistant architecture as data: agents, tools, MCP servers, users, infrastructure, and the incident timeline.

**Step 1: Write the test**

```python
# tests/unit/sre_agent/tools/synthetic/test_cymbal_assistant.py
"""Tests for Cymbal Assistant demo scenario definition."""
import pytest
from sre_agent.tools.synthetic.cymbal_assistant import (
    AGENTS,
    MCP_SERVERS,
    DEMO_USERS,
    JOURNEY_TEMPLATES,
    INCIDENT_TIMELINE,
    RESOURCE_ATTRIBUTES,
    AgentDef,
    MCPServerDef,
    DemoUser,
    JourneyTemplate,
)


class TestAgentDefinitions:
    def test_root_agent_exists(self):
        root = AGENTS["cymbal-assistant"]
        assert root.agent_type == "root"
        assert root.model == "gemini-2.5-flash"

    def test_six_sub_agents(self):
        sub_agents = [a for a in AGENTS.values() if a.agent_type == "sub_agent"]
        assert len(sub_agents) == 6

    def test_agent_to_agent_invocations(self):
        product = AGENTS["product-discovery"]
        assert "personalization" in product.delegates_to
        checkout = AGENTS["checkout"]
        assert "personalization" in checkout.delegates_to
        assert "fulfillment" in checkout.delegates_to
        order_mgmt = AGENTS["order-management"]
        assert "fulfillment" in order_mgmt.delegates_to

    def test_all_tools_mapped_to_mcp_servers(self):
        all_tool_names = set()
        for server in MCP_SERVERS.values():
            all_tool_names.update(server.tools)
        for agent in AGENTS.values():
            for tool in agent.tools:
                assert tool in all_tool_names, f"Tool {tool} not in any MCP server"


class TestMCPServers:
    def test_eight_mcp_servers(self):
        assert len(MCP_SERVERS) == 8

    def test_all_cloud_run(self):
        for server in MCP_SERVERS.values():
            assert server.platform == "cloud_run"


class TestDemoUsers:
    def test_twelve_users(self):
        assert len(DEMO_USERS) == 12

    def test_unique_regions(self):
        regions = {u.gcp_region for u in DEMO_USERS}
        assert len(regions) >= 8


class TestJourneyTemplates:
    def test_six_journey_types(self):
        assert len(JOURNEY_TEMPLATES) == 6

    def test_weights_sum_to_100(self):
        total = sum(j.weight_pct for j in JOURNEY_TEMPLATES)
        assert total == 100


class TestResourceAttributes:
    def test_cloud_platform_is_agent_engine(self):
        attrs = RESOURCE_ATTRIBUTES
        assert attrs["cloud.platform"] == "gcp.agent_engine"

    def test_service_name(self):
        assert RESOURCE_ATTRIBUTES["service.name"] == "cymbal-assistant"


class TestIncidentTimeline:
    def test_has_release_and_rollback(self):
        events = [e["event"] for e in INCIDENT_TIMELINE]
        assert "release_v2.4.1" in events
        assert "rollback_v2.4.0" in events
```

**Step 2: Run test to verify it fails**

Run: `cd /home/raj/work/sre-agent && uv run pytest tests/unit/sre_agent/tools/synthetic/test_cymbal_assistant.py -v --no-header -x`
Expected: FAIL — `ModuleNotFoundError: No module named 'sre_agent.tools.synthetic.cymbal_assistant'`

**Step 3: Implement `cymbal_assistant.py`**

```python
# sre_agent/tools/synthetic/cymbal_assistant.py
"""Cymbal Shops AI Shopping Assistant — demo scenario definition.

Defines the agent hierarchy, MCP servers, users, journey templates,
and incident timeline for the guest-mode demo.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# ── Constants ──────────────────────────────────────────────────────
DEMO_PROJECT_ID = "cymbal-shops-demo"
DEMO_REGION = "us-central1"
REASONING_ENGINE_ID = (
    f"projects/{DEMO_PROJECT_ID}/locations/{DEMO_REGION}"
    "/reasoningEngines/cymbal-assistant-001"
)
AGENT_VERSION_NORMAL = "v2.4.0"
AGENT_VERSION_BAD = "v2.4.1"


# ── Data Classes ───────────────────────────────────────────────────
@dataclass(frozen=True)
class AgentDef:
    name: str
    display_name: str
    agent_type: str  # root | sub_agent
    model: str
    tools: list[str] = field(default_factory=list)
    delegates_to: list[str] = field(default_factory=list)
    description: str = ""


@dataclass(frozen=True)
class MCPServerDef:
    name: str
    display_name: str
    platform: str  # cloud_run
    tools: list[str] = field(default_factory=list)
    url: str = ""


@dataclass(frozen=True)
class DemoUser:
    user_id: str
    display_name: str
    city: str
    country: str
    gcp_region: str
    geo_region: str  # e.g. "US-CA"


@dataclass(frozen=True)
class JourneyTemplate:
    journey_type: str
    display_name: str
    weight_pct: int
    turns_range: tuple[int, int]
    agents_involved: list[str]
    description: str = ""


# ── Resource Attributes (OTel) ────────────────────────────────────
RESOURCE_ATTRIBUTES: dict[str, str] = {
    "service.name": "cymbal-assistant",
    "service.version": AGENT_VERSION_NORMAL,
    "cloud.provider": "gcp",
    "cloud.region": DEMO_REGION,
    "cloud.platform": "gcp.agent_engine",
    "cloud.resource_id": REASONING_ENGINE_ID,
}


# ── Agent Definitions ─────────────────────────────────────────────
AGENTS: dict[str, AgentDef] = {
    "cymbal-assistant": AgentDef(
        name="cymbal-assistant",
        display_name="Cymbal Assistant",
        agent_type="root",
        model="gemini-2.5-flash",
        tools=[],  # Root only delegates
        delegates_to=[
            "product-discovery",
            "order-management",
            "checkout",
            "support",
        ],
        description="Root orchestrator for Cymbal Shops AI assistant",
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
        description="Searches catalog, browses products, shows reviews",
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
        description="Tracks orders, processes returns and modifications",
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
        description="Manages cart, processes payments, coordinates shipping",
    ),
    "support": AgentDef(
        name="support",
        display_name="Support Agent",
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
        description="Answers FAQs, handles complaints, escalates issues",
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
        description="Builds taste profiles, personalizes results, suggests upsells",
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
        description="Warehouse selection, shipping, delivery estimation, tracking",
    ),
}


# ── MCP Server Definitions ────────────────────────────────────────
MCP_SERVERS: dict[str, MCPServerDef] = {
    "catalog-mcp": MCPServerDef(
        name="catalog-mcp",
        display_name="Product Catalog MCP",
        platform="cloud_run",
        tools=["search_products", "get_product_details", "get_reviews"],
        url="https://catalog-mcp-abc123-uc.a.run.app",
    ),
    "recommendation-mcp": MCPServerDef(
        name="recommendation-mcp",
        display_name="Recommendation MCP",
        platform="cloud_run",
        tools=["get_personalized_recs", "get_trending", "get_similar_products"],
        url="https://rec-mcp-abc123-uc.a.run.app",
    ),
    "order-mcp": MCPServerDef(
        name="order-mcp",
        display_name="Order MCP",
        platform="cloud_run",
        tools=["get_order_status", "list_orders", "create_return", "modify_order"],
        url="https://order-mcp-abc123-uc.a.run.app",
    ),
    "payment-mcp": MCPServerDef(
        name="payment-mcp",
        display_name="Payment MCP",
        platform="cloud_run",
        tools=["process_payment", "validate_coupon", "get_payment_methods"],
        url="https://payment-mcp-abc123-uc.a.run.app",
    ),
    "inventory-mcp": MCPServerDef(
        name="inventory-mcp",
        display_name="Inventory MCP",
        platform="cloud_run",
        tools=["check_availability", "get_warehouse_stock", "reserve_inventory"],
        url="https://inventory-mcp-abc123-uc.a.run.app",
    ),
    "customer-mcp": MCPServerDef(
        name="customer-mcp",
        display_name="Customer MCP",
        platform="cloud_run",
        tools=[
            "get_customer_profile",
            "get_purchase_history",
            "update_preferences",
            "get_loyalty_points",
        ],
        url="https://customer-mcp-abc123-uc.a.run.app",
    ),
    "logistics-mcp": MCPServerDef(
        name="logistics-mcp",
        display_name="Logistics MCP",
        platform="cloud_run",
        tools=["calculate_shipping", "get_delivery_estimate", "track_shipment"],
        url="https://logistics-mcp-abc123-uc.a.run.app",
    ),
    "support-mcp": MCPServerDef(
        name="support-mcp",
        display_name="Support MCP",
        platform="cloud_run",
        tools=["search_knowledge_base", "create_ticket", "escalate_to_human"],
        url="https://support-mcp-abc123-uc.a.run.app",
    ),
}


# ── Tool → MCP Server Mapping ─────────────────────────────────────
TOOL_TO_MCP: dict[str, str] = {}
for _server_name, _server in MCP_SERVERS.items():
    for _tool in _server.tools:
        TOOL_TO_MCP[_tool] = _server_name

# Also add cart tools to inventory-mcp (shared infra)
TOOL_TO_MCP["add_to_cart"] = "inventory-mcp"
TOOL_TO_MCP["get_cart"] = "inventory-mcp"


# ── Demo Users ─────────────────────────────────────────────────────
DEMO_USERS: list[DemoUser] = [
    DemoUser("alice@gmail.com", "Alice Chen", "San Francisco", "US", "us-west1", "US-CA"),
    DemoUser("bob@outlook.com", "Bob Martinez", "New York", "US", "us-east4", "US-NY"),
    DemoUser("carol@yahoo.com", "Carol Johnson", "Chicago", "US", "us-central1", "US-IL"),
    DemoUser("dave@gmail.com", "Dave Williams", "London", "GB", "europe-west2", "GB-LND"),
    DemoUser("emma@gmail.com", "Emma Tanaka", "Tokyo", "JP", "asia-northeast1", "JP-13"),
    DemoUser("frank@company.com", "Frank O'Brien", "Sydney", "AU", "australia-southeast1", "AU-NSW"),
    DemoUser("grace@gmail.com", "Grace Kim", "Toronto", "CA", "northamerica-northeast1", "CA-ON"),
    DemoUser("hiro@outlook.com", "Hiro Silva", "São Paulo", "BR", "southamerica-east1", "BR-SP"),
    DemoUser("isabella@gmail.com", "Isabella Patel", "Mumbai", "IN", "asia-south1", "IN-MH"),
    DemoUser("james@yahoo.com", "James Müller", "Berlin", "DE", "europe-west3", "DE-BE"),
    DemoUser("kate@gmail.com", "Kate Thompson", "Seattle", "US", "us-west1", "US-WA"),
    DemoUser("liam@outlook.com", "Liam Dubois", "Paris", "FR", "europe-west1", "FR-IDF"),
]


# ── Journey Templates ─────────────────────────────────────────────
JOURNEY_TEMPLATES: list[JourneyTemplate] = [
    JourneyTemplate(
        "search_browse_buy", "Search → Browse → Buy", 30, (5, 7),
        ["product-discovery", "personalization", "checkout", "fulfillment"],
    ),
    JourneyTemplate(
        "search_compare", "Search → Compare", 25, (3, 5),
        ["product-discovery", "personalization"],
    ),
    JourneyTemplate(
        "order_tracking", "Order Tracking", 15, (2, 3),
        ["order-management", "fulfillment"],
    ),
    JourneyTemplate(
        "return_refund", "Return / Refund", 10, (4, 6),
        ["order-management", "support"],
    ),
    JourneyTemplate(
        "support_question", "Support Question", 10, (2, 4),
        ["support"],
    ),
    JourneyTemplate(
        "browse_abandon_return", "Browse → Abandon → Return", 10, (6, 8),
        ["product-discovery", "personalization", "checkout"],
    ),
]


# ── Incident Timeline ─────────────────────────────────────────────
# Days are relative to the start of the 7-day window
INCIDENT_TIMELINE: list[dict[str, object]] = [
    {"day": 3, "hour": 2, "minute": 15, "event": "release_v2.4.1",
     "description": "Product Discovery Agent prompt updated"},
    {"day": 3, "hour": 2, "minute": 30, "event": "degradation_start",
     "description": "Tool call volume increasing"},
    {"day": 3, "hour": 8, "minute": 0, "event": "rate_limiting_start",
     "description": "Payment MCP rate limiting (429s)"},
    {"day": 5, "hour": 11, "minute": 30, "event": "alert_fired",
     "description": "Anomalous tool call volume alert"},
    {"day": 5, "hour": 15, "minute": 45, "event": "rollback_v2.4.0",
     "description": "Rolled back to v2.4.0"},
    {"day": 5, "hour": 16, "minute": 0, "event": "recovery_start",
     "description": "Metrics returning to baseline"},
]


# ── Anomalous Tool Calls (added by bad prompt in v2.4.1) ──────────
ANOMALOUS_TOOLS_IN_PRODUCT_DISCOVERY: list[str] = [
    "check_availability",   # From Inventory MCP — shouldn't be called here
    "validate_coupon",      # From Payment MCP — shouldn't be called here
]

ANOMALOUS_DELEGATION = "fulfillment"  # Product Discovery should NOT delegate to Fulfillment
```

**Step 4: Run test to verify it passes**

Run: `cd /home/raj/work/sre-agent && uv run pytest tests/unit/sre_agent/tools/synthetic/test_cymbal_assistant.py -v --no-header`
Expected: All PASS

**Step 5: Commit**

```bash
git add sre_agent/tools/synthetic/cymbal_assistant.py tests/unit/sre_agent/tools/synthetic/test_cymbal_assistant.py
git commit -m "feat(demo): add Cymbal Assistant agent scenario definition"
```

---

## Task 2: Create Demo Data Generator

**Files:**
- Create: `sre_agent/tools/synthetic/demo_data_generator.py`
- Test: `tests/unit/sre_agent/tools/synthetic/test_demo_data_generator.py`

Generates ~400 traces across ~80 sessions over 7 days. Uses deterministic seeding so the same data is generated every time. Produces data in the exact format that `agent_graph.py` endpoints return from BigQuery.

**Step 1: Write the test**

```python
# tests/unit/sre_agent/tools/synthetic/test_demo_data_generator.py
"""Tests for demo data generator."""
import pytest
from datetime import datetime, timezone
from sre_agent.tools.synthetic.demo_data_generator import DemoDataGenerator


@pytest.fixture
def generator():
    return DemoDataGenerator()


class TestSessionGeneration:
    def test_generates_expected_session_count(self, generator):
        sessions = generator.get_sessions()
        assert 70 <= len(sessions) <= 90

    def test_sessions_span_seven_days(self, generator):
        sessions = generator.get_sessions()
        timestamps = [s["timestamp"] for s in sessions]
        first = min(timestamps)
        last = max(timestamps)
        span_hours = (last - first).total_seconds() / 3600
        assert span_hours >= 144  # ~6 days minimum

    def test_sessions_have_required_fields(self, generator):
        session = generator.get_sessions()[0]
        required = {"session_id", "user_id", "timestamp", "journey_type", "turns"}
        assert required.issubset(session.keys())

    def test_sessions_use_known_users(self, generator):
        from sre_agent.tools.synthetic.cymbal_assistant import DEMO_USERS
        valid_ids = {u.user_id for u in DEMO_USERS}
        for session in generator.get_sessions():
            assert session["user_id"] in valid_ids


class TestTraceGeneration:
    def test_generates_expected_trace_count(self, generator):
        traces = generator.get_all_traces()
        assert 350 <= len(traces) <= 450

    def test_trace_has_otel_fields(self, generator):
        trace = generator.get_all_traces()[0]
        assert "trace_id" in trace
        assert "spans" in trace
        assert len(trace["spans"]) >= 5

    def test_span_has_genai_attributes(self, generator):
        trace = generator.get_all_traces()[0]
        span = trace["spans"][0]
        assert "gen_ai.operation.name" in span.get("attributes", {})

    def test_resource_has_agent_engine_platform(self, generator):
        trace = generator.get_all_traces()[0]
        span = trace["spans"][0]
        resource = span.get("resource", {}).get("attributes", {})
        assert resource.get("cloud.platform") == "gcp.agent_engine"

    def test_degraded_traces_have_more_spans(self, generator):
        traces = generator.get_all_traces()
        normal = [t for t in traces if not t["is_degraded"]]
        degraded = [t for t in traces if t["is_degraded"]]
        if normal and degraded:
            avg_normal = sum(len(t["spans"]) for t in normal) / len(normal)
            avg_degraded = sum(len(t["spans"]) for t in degraded) / len(degraded)
            assert avg_degraded > avg_normal

    def test_degraded_traces_have_errors(self, generator):
        degraded = [t for t in generator.get_all_traces() if t["is_degraded"]]
        has_errors = [t for t in degraded if any(
            s.get("status", {}).get("code") == 2 for s in t["spans"]
        )]
        assert len(has_errors) > 0


class TestTopologyAggregation:
    def test_topology_has_nodes_and_edges(self, generator):
        topo = generator.get_topology(hours=168)
        assert len(topo["nodes"]) >= 10
        assert len(topo["edges"]) >= 15

    def test_topology_node_format(self, generator):
        topo = generator.get_topology(hours=168)
        node = topo["nodes"][0]
        assert "id" in node
        assert "type" in node
        assert "data" in node
        assert "label" in node["data"]

    def test_topology_edge_format(self, generator):
        topo = generator.get_topology(hours=168)
        edge = topo["edges"][0]
        assert "source" in edge
        assert "target" in edge
        assert "data" in edge


class TestSankeyAggregation:
    def test_sankey_has_nodes_and_links(self, generator):
        sankey = generator.get_trajectories(hours=168)
        assert len(sankey["nodes"]) >= 8
        assert len(sankey["links"]) >= 10

    def test_sankey_link_format(self, generator):
        sankey = generator.get_trajectories(hours=168)
        link = sankey["links"][0]
        assert "source" in link
        assert "target" in link
        assert "value" in link


class TestDashboardKPIs:
    def test_kpis_have_required_fields(self, generator):
        kpis = generator.get_dashboard_kpis(hours=168)
        required = {
            "totalSessions", "avgTurns", "rootInvocations", "errorRate",
            "totalSessionsTrend", "avgTurnsTrend", "rootInvocationsTrend",
            "errorRateTrend",
        }
        assert required.issubset(kpis.keys())


class TestDeterminism:
    def test_same_data_each_time(self):
        g1 = DemoDataGenerator()
        g2 = DemoDataGenerator()
        assert g1.get_sessions()[0]["session_id"] == g2.get_sessions()[0]["session_id"]
        assert g1.get_all_traces()[0]["trace_id"] == g2.get_all_traces()[0]["trace_id"]
```

**Step 2: Run test, confirm failure**

Run: `cd /home/raj/work/sre-agent && uv run pytest tests/unit/sre_agent/tools/synthetic/test_demo_data_generator.py -v --no-header -x`

**Step 3: Implement `demo_data_generator.py`**

This is the largest file. Key design:
- Uses `random.Random(seed=42)` for determinism
- `_base_time` is a fixed datetime (Feb 15, 2026 00:00 UTC) — the start of the 7-day window
- Generates sessions first, then traces for each turn in each session
- Trace generation uses journey templates from `cymbal_assistant.py`
- Normal traces: 8-12 spans, ~500ms
- Degraded traces (post-release): 18-25 spans, ~3200ms, some errors
- All aggregation methods (topology, sankey, KPIs, etc.) operate on the pre-generated trace data
- Results are cached after first generation (module-level singleton)

The generator must produce data matching these exact response formats (from AgentOps UI hooks):

**Topology nodes:**
```python
{"id": str, "type": str, "data": {"label": str, "nodeType": str,
 "executionCount": int, "totalTokens": int, "errorCount": int,
 "avgDurationMs": float}, "position": {"x": float, "y": float}}
```

**Topology edges:**
```python
{"id": str, "source": str, "target": str, "data": {"callCount": int,
 "avgDurationMs": float, "errorCount": int, "totalTokens": int}}
```

**Sankey nodes:** `{"id": str, "nodeColor": str}`
**Sankey links:** `{"source": str, "target": str, "value": int}`

**KPIs:**
```python
{"totalSessions": int, "avgTurns": float, "rootInvocations": int,
 "errorRate": float, "totalSessionsTrend": float, "avgTurnsTrend": float,
 "rootInvocationsTrend": float, "errorRateTrend": float}
```

**Dashboard timeseries:**
```python
{"latency": [{"timestamp": str, "p50": float, "p95": float}],
 "qps": [{"timestamp": str, "qps": float, "errorRate": float}],
 "tokens": [{"timestamp": str, "input": int, "output": int}]}
```

**Dashboard models:**
```python
{"modelCalls": [{"modelName": str, "totalCalls": int, "p95Duration": float,
 "errorRate": float, "quotaExits": int, "tokensUsed": int}]}
```

**Dashboard tools:**
```python
{"toolCalls": [{"toolName": str, "totalCalls": int, "p95Duration": float,
 "errorRate": float}]}
```

**Dashboard logs:**
```python
{"agentLogs": [{"timestamp": str, "agentId": str, "severity": str,
 "message": str, "traceId": str, "spanId": str, "agentName": str,
 "resourceId": str}]}
```

**Dashboard sessions:**
```python
{"agentSessions": [{"timestamp": str, "sessionId": str, "turns": int,
 "latestTraceId": str, "totalTokens": int, "errorCount": int,
 "avgLatencyMs": float, "p95LatencyMs": float, "agentName": str,
 "resourceId": str, "spanCount": int, "llmCallCount": int,
 "toolCallCount": int, "toolErrorCount": int, "llmErrorCount": int}]}
```

**Dashboard traces:**
```python
{"agentTraces": [{"timestamp": str, "traceId": str, "sessionId": str,
 "totalTokens": int, "errorCount": int, "latencyMs": float,
 "agentName": str, "resourceId": str, "spanCount": int,
 "llmCallCount": int, "toolCallCount": int, "toolErrorCount": int,
 "llmErrorCount": int}]}
```

**Registry agents:**
```python
{"agents": [{"serviceName": str, "agentId": str, "agentName": str,
 "totalSessions": int, "totalTurns": int, "inputTokens": int,
 "outputTokens": int, "errorCount": int, "errorRate": float,
 "p50DurationMs": float, "p95DurationMs": float}]}
```

**Registry tools:**
```python
{"tools": [{"serviceName": str, "toolId": str, "toolName": str,
 "executionCount": int, "errorCount": int, "errorRate": float,
 "avgDurationMs": float, "p95DurationMs": float}]}
```

**Node detail:**
```python
{"nodeId": str, "nodeType": str, "label": str, "totalInvocations": int,
 "errorRate": float, "errorCount": int, "inputTokens": int,
 "outputTokens": int, "estimatedCost": float,
 "latency": {"p50": float, "p95": float, "p99": float},
 "topErrors": [{"message": str, "count": int}],
 "recentPayloads": [{"traceId": str, "spanId": str, "timestamp": str,
  "nodeType": str, "prompt": str|None, "completion": str|None,
  "toolInput": str|None, "toolOutput": str|None}]}
```

**Edge detail:**
```python
{"sourceId": str, "targetId": str, "callCount": int, "errorCount": int,
 "errorRate": float, "avgDurationMs": float, "p95DurationMs": float,
 "p99DurationMs": float, "totalTokens": int, "inputTokens": int,
 "outputTokens": int}
```

**Span details:**
```python
{"traceId": str, "spanId": str, "statusCode": int, "statusMessage": str,
 "exceptions": [{"message": str, "stacktrace": str, "type": str}],
 "attributes": dict}
```

**Trace logs:**
```python
{"traceId": str, "logs": [{"timestamp": str, "severity": str, "payload": Any}]}
```

Each span in every trace must include these OTel attributes:
- `resource.attributes.cloud.platform` = `"gcp.agent_engine"`
- `resource.attributes.service.name` = `"cymbal-assistant"`
- `resource.attributes.service.version` = `"v2.4.0"` or `"v2.4.1"`
- `resource.attributes.cloud.resource_id` = reasoning engine ID
- `attributes.gen_ai.operation.name` = `"invoke_agent"` | `"execute_tool"` | `"generate_content"`
- `attributes.gen_ai.agent.name` = agent name
- `attributes.gen_ai.system` = `"vertex_ai"`
- `attributes.gen_ai.conversation.id` = session ID
- For LLM spans: `gen_ai.request.model`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`
- For tool spans: `gen_ai.tool.name`, `gen_ai.tool.call.id`
- `attributes.user.id` = user email
- `attributes.cymbal.release_version` = `"v2.4.0"` or `"v2.4.1"`

**Step 4: Run tests, confirm pass**

**Step 5: Commit**

```bash
git add sre_agent/tools/synthetic/demo_data_generator.py tests/unit/sre_agent/tools/synthetic/test_demo_data_generator.py
git commit -m "feat(demo): add demo data generator for 7-day trace dataset"
```

---

## Task 3: Add Guest Mode to agent_graph.py — Graph Endpoints

**Files:**
- Modify: `sre_agent/api/routers/agent_graph.py` (add guest mode guards to topology, trajectories, node, edge, timeseries endpoints)
- Test: `tests/unit/sre_agent/api/routers/test_agent_graph.py` (add guest mode tests)

**Step 1: Write tests for guest mode graph endpoints**

Add tests to the existing test file (or create if doesn't exist):

```python
# tests/unit/sre_agent/api/routers/test_agent_graph.py (additions)
"""Tests for agent_graph guest mode endpoints."""
import pytest
from unittest.mock import patch
from sre_agent.auth import set_guest_mode


@pytest.fixture(autouse=True)
def _enable_guest_mode():
    set_guest_mode(True)
    yield
    set_guest_mode(False)


class TestTopologyGuestMode:
    @pytest.mark.asyncio
    async def test_topology_returns_nodes_and_edges(self, client):
        resp = client.get(
            "/api/v1/graph/topology",
            params={"project_id": "cymbal-shops-demo", "hours": 168},
            headers={"X-Guest-Mode": "true"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) >= 10

    @pytest.mark.asyncio
    async def test_topology_node_has_required_fields(self, client):
        resp = client.get(
            "/api/v1/graph/topology",
            params={"project_id": "cymbal-shops-demo", "hours": 168},
            headers={"X-Guest-Mode": "true"},
        )
        node = resp.json()["nodes"][0]
        assert "id" in node
        assert "data" in node
        assert "label" in node["data"]
        assert "executionCount" in node["data"]


class TestTrajectoriesGuestMode:
    @pytest.mark.asyncio
    async def test_trajectories_returns_sankey_data(self, client):
        resp = client.get(
            "/api/v1/graph/trajectories",
            params={"project_id": "cymbal-shops-demo", "hours": 168},
            headers={"X-Guest-Mode": "true"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "links" in data
```

**Step 2: Run tests, confirm failure**

**Step 3: Modify `agent_graph.py`**

At the top of each endpoint function, add guest mode guard:

```python
from sre_agent.auth import is_guest_mode
from sre_agent.tools.synthetic.demo_data_generator import DemoDataGenerator

# At the top of each endpoint:
@router.get("/topology")
@async_ttl_cache(ttl=300)
async def get_topology(project_id: str = Query(...), ...):
    if is_guest_mode():
        gen = DemoDataGenerator()
        return gen.get_topology(hours=hours)
    # ... existing BigQuery code ...
```

Do the same for: `/trajectories`, `/node/{id}`, `/edge/{s}/{t}`, `/timeseries`

**Step 4: Run tests, confirm pass**

**Step 5: Commit**

```bash
git add sre_agent/api/routers/agent_graph.py tests/unit/sre_agent/api/routers/test_agent_graph.py
git commit -m "feat(demo): add guest mode to agent_graph graph endpoints"
```

---

## Task 4: Add Guest Mode to agent_graph.py — Dashboard Endpoints

**Files:**
- Modify: `sre_agent/api/routers/agent_graph.py`
- Modify: `tests/unit/sre_agent/api/routers/test_agent_graph.py`

Same pattern as Task 3 but for: `/dashboard/kpis`, `/dashboard/timeseries`, `/dashboard/models`, `/dashboard/tools`, `/dashboard/logs`, `/dashboard/sessions`, `/dashboard/traces`

**Step 1: Write tests**

```python
class TestDashboardKPIsGuestMode:
    @pytest.mark.asyncio
    async def test_kpis_returns_metrics(self, client):
        resp = client.get(
            "/api/v1/graph/dashboard/kpis",
            params={"project_id": "cymbal-shops-demo", "hours": 168},
            headers={"X-Guest-Mode": "true"},
        )
        assert resp.status_code == 200
        kpis = resp.json()["kpis"]
        assert "totalSessions" in kpis
        assert kpis["totalSessions"] > 0

# Similar tests for timeseries, models, tools, logs, sessions, traces
```

**Step 2-5: Run → Implement → Run → Commit**

Each endpoint gets `if is_guest_mode(): return gen.get_dashboard_<type>(hours=hours)` at the top.

```bash
git commit -m "feat(demo): add guest mode to agent_graph dashboard endpoints"
```

---

## Task 5: Add Guest Mode to agent_graph.py — Registry & Detail Endpoints

**Files:**
- Modify: `sre_agent/api/routers/agent_graph.py`
- Modify: `tests/unit/sre_agent/api/routers/test_agent_graph.py`

Endpoints: `/registry/agents`, `/registry/tools`, `/trace/{id}/logs`, `/trace/{id}/span/{id}/details`

**Step 1-5: Test → Implement → Commit**

```bash
git commit -m "feat(demo): add guest mode to agent_graph registry and detail endpoints"
```

---

## Task 6: Create Pre-Recorded Chat Responses

**Files:**
- Create: `sre_agent/tools/synthetic/demo_chat_responses.py`
- Test: `tests/unit/sre_agent/tools/synthetic/test_demo_chat_responses.py`

This file produces the NDJSON event stream for pre-recorded agent chat responses. Each response is a sequence of events that triggers all dashboard panels and canvases.

**Event types to emit per the frontend contract:**
- `{"type": "session", "session_id": "..."}` — session init
- `{"type": "text", "content": "..."}` — agent text (markdown)
- `{"type": "tool-call", "tool_name": "...", "args": {...}, "id": "..."}` — tool invocation
- `{"type": "tool-response", "tool_name": "...", "result": {...}, "id": "..."}` — tool result
- `{"type": "dashboard", "category": "...", "widget_type": "...", "data": {...}}` — panel data
- `{"type": "agent_activity", "investigation_id": "...", "agent": {...}}` — activity tracking
- `{"type": "council_graph", "investigation_id": "...", "agents": [...]}` — council graph
- `{"type": "memory", "action": "...", "title": "...", ...}` — learning events
- `{"type": "trace_info", "trace_id": "...", "project_id": "..."}` — trace deep-link

**Pre-recorded flow (4 turns):**

Turn 1 — "Investigate the checkout latency spike":
- Text: Agent acknowledges, describes investigation plan
- Tool calls: `list_alerts`, `list_time_series`
- Dashboard: `x-sre-incident-timeline` (4 alerts), `x-sre-metric-chart` (latency spike)
- Agent activity: root agent running

Turn 2 — "Show me the traces":
- Text: Agent finds N+1 tool call pattern
- Tool calls: `fetch_trace` (degraded trace), `list_log_entries`
- Dashboard: `x-sre-trace-waterfall` (22-span degraded trace), `x-sre-log-entries-viewer`
- Agent activity: trace panel completing

Turn 3 — "What's the root cause?":
- Text: Agent identifies bad prompt in v2.4.1
- Dashboard: `x-sre-council-synthesis` (all panel findings), `x-sre-metrics-dashboard`
- Council graph: Full investigation with 5 panels + critic + synthesizer
- Memory: `pattern_learned` event

Turn 4 — "How do I fix it?":
- Text: Rollback recommendation with steps
- Dashboard: `x-sre-remediation-plan`
- Trace info: Link to Cloud Trace

**Step 1: Write test**

```python
class TestDemoChatResponses:
    def test_get_demo_turns_returns_four_turns(self):
        turns = get_demo_turns()
        assert len(turns) == 4

    def test_each_turn_has_events(self):
        for turn in get_demo_turns():
            assert len(turn) > 0

    def test_events_are_valid_json_lines(self):
        import json
        for turn in get_demo_turns():
            for event_line in turn:
                data = json.loads(event_line)
                assert "type" in data

    def test_all_widget_types_covered(self):
        import json
        widget_types = set()
        for turn in get_demo_turns():
            for line in turn:
                data = json.loads(line)
                if data.get("type") == "dashboard":
                    widget_types.add(data.get("widget_type"))
        expected = {
            "x-sre-trace-waterfall",
            "x-sre-metric-chart",
            "x-sre-log-entries-viewer",
            "x-sre-incident-timeline",
            "x-sre-council-synthesis",
            "x-sre-metrics-dashboard",
            "x-sre-remediation-plan",
        }
        assert expected.issubset(widget_types)

    def test_council_graph_event_emitted(self):
        import json
        all_events = [json.loads(l) for turn in get_demo_turns() for l in turn]
        council = [e for e in all_events if e["type"] == "council_graph"]
        assert len(council) >= 1
```

**Step 2-5: Run → Implement → Run → Commit**

```bash
git commit -m "feat(demo): add pre-recorded chat responses with all event types"
```

---

## Task 7: Add Guest Mode to Chat Endpoint

**Files:**
- Modify: `sre_agent/api/routers/agent.py`
- Test: `tests/unit/sre_agent/api/routers/test_agent_chat_guest.py`

**Step 1: Write test**

```python
class TestChatGuestMode:
    @pytest.mark.asyncio
    async def test_guest_chat_returns_streaming_response(self, client):
        resp = client.post(
            "/api/genui/chat",
            json={"messages": [{"role": "user", "content": "investigate latency"}]},
            headers={"X-Guest-Mode": "true", "Authorization": "Bearer guest"},
        )
        assert resp.status_code == 200
        assert "application/x-ndjson" in resp.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_guest_chat_emits_session_event(self, client):
        resp = client.post(
            "/api/genui/chat",
            json={"messages": [{"role": "user", "content": "hello"}]},
            headers={"X-Guest-Mode": "true", "Authorization": "Bearer guest"},
        )
        import json
        lines = resp.text.strip().split("\n")
        first = json.loads(lines[0])
        assert first["type"] == "session"
```

**Step 2-5: Run → Implement → Run → Commit**

Implementation: At the top of `chat_agent()`, add:
```python
if is_guest_mode():
    return StreamingResponse(
        _guest_event_generator(request),
        media_type="application/x-ndjson",
    )
```

Where `_guest_event_generator` yields events from `demo_chat_responses.get_demo_turns()`, matching the turn number to the session's turn count.

```bash
git commit -m "feat(demo): add guest mode to chat endpoint with pre-recorded responses"
```

---

## Task 8: Add Guest Mode to Dashboard & Remaining Routers

**Files:**
- Modify: `sre_agent/api/routers/dashboards.py`
- Test: `tests/unit/sre_agent/api/routers/test_dashboards_guest.py`

For dashboards, return a pre-built demo dashboard in guest mode:

```python
if is_guest_mode():
    return {"dashboards": [DEMO_DASHBOARD]}
```

The demo dashboard includes panels for: latency chart, error rate chart, alert timeline, log viewer.

Also ensure these routers gracefully handle guest mode:
- `preferences.py` — return cymbal-shops-demo as selected project
- `permissions.py` — return all-access in guest mode
- `system.py` — already works

```bash
git commit -m "feat(demo): add guest mode to dashboards and preferences routers"
```

---

## Task 9: Integration Test — Full Guest Mode Smoke Test

**Files:**
- Create: `tests/integration/test_guest_mode_full.py`

End-to-end test that hits every major endpoint with guest mode headers and verifies non-empty, schema-valid responses.

```python
"""Full guest mode integration test — ensures every feature works."""
import json
import pytest
from fastapi.testclient import TestClient
from sre_agent.api.app import create_app


@pytest.fixture
def guest_client():
    app = create_app()
    client = TestClient(app)
    client.headers.update({
        "X-Guest-Mode": "true",
        "Authorization": "Bearer dev-mode-bypass-token",
    })
    return client


GRAPH_BASE = "/api/v1/graph"
GRAPH_PARAMS = {"project_id": "cymbal-shops-demo", "hours": 168}


class TestGuestModeSmoke:
    def test_config(self, guest_client):
        r = guest_client.get("/api/config")
        assert r.json()["guest_mode_enabled"] is True

    def test_topology(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/topology", params=GRAPH_PARAMS)
        assert r.status_code == 200
        assert len(r.json()["nodes"]) > 0

    def test_trajectories(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/trajectories", params=GRAPH_PARAMS)
        assert r.status_code == 200
        assert len(r.json()["nodes"]) > 0

    def test_dashboard_kpis(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/dashboard/kpis", params=GRAPH_PARAMS)
        assert r.status_code == 200
        assert r.json()["kpis"]["totalSessions"] > 0

    def test_dashboard_timeseries(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/dashboard/timeseries", params=GRAPH_PARAMS)
        assert r.status_code == 200

    def test_dashboard_models(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/dashboard/models", params=GRAPH_PARAMS)
        assert r.status_code == 200
        assert len(r.json()["modelCalls"]) > 0

    def test_dashboard_tools(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/dashboard/tools", params=GRAPH_PARAMS)
        assert r.status_code == 200
        assert len(r.json()["toolCalls"]) > 0

    def test_dashboard_logs(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/dashboard/logs", params=GRAPH_PARAMS)
        assert r.status_code == 200

    def test_dashboard_sessions(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/dashboard/sessions", params=GRAPH_PARAMS)
        assert r.status_code == 200

    def test_dashboard_traces(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/dashboard/traces", params=GRAPH_PARAMS)
        assert r.status_code == 200

    def test_registry_agents(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/registry/agents", params=GRAPH_PARAMS)
        assert r.status_code == 200
        assert len(r.json()["agents"]) > 0

    def test_registry_tools(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/registry/tools", params=GRAPH_PARAMS)
        assert r.status_code == 200
        assert len(r.json()["tools"]) > 0

    def test_chat(self, guest_client):
        r = guest_client.post(
            "/api/genui/chat",
            json={"messages": [{"role": "user", "content": "hello"}]},
        )
        assert r.status_code == 200
        lines = r.text.strip().split("\n")
        assert len(lines) > 0
        first = json.loads(lines[0])
        assert first["type"] == "session"
```

```bash
git commit -m "test(demo): add full guest mode integration smoke test"
```

---

## Task 10: Lint, Full Test Suite, Final Verification

**Step 1:** Run linter
```bash
cd /home/raj/work/sre-agent && uv run poe lint
```

**Step 2:** Run full test suite
```bash
cd /home/raj/work/sre-agent && uv run poe test
```

**Step 3:** Fix any failures

**Step 4:** Manual verification — start dev server and log in as guest
```bash
cd /home/raj/work/sre-agent && uv run poe dev
```
- Click "Guest Login"
- Verify: AgentOps topology graph renders with Cymbal Assistant nodes
- Verify: Sankey trajectory shows agent flow
- Verify: Dashboard KPIs show session/turn/token counts
- Verify: Registry shows 7 agents and 30+ tools
- Verify: Chat returns pre-recorded investigation
- Verify: All dashboard panels populate (traces, logs, metrics, alerts)

**Step 5:** Final commit
```bash
git commit -m "feat(demo): complete guest mode for all features"
```

---

## Dependency Graph

```
Task 1 (scenario def)
    ↓
Task 2 (data generator) ← depends on Task 1
    ↓
Task 3 (graph endpoints) ← depends on Task 2
Task 4 (dashboard endpoints) ← depends on Task 2
Task 5 (registry endpoints) ← depends on Task 2
Task 6 (chat responses) ← depends on Task 2
    ↓
Task 7 (chat endpoint) ← depends on Task 6
Task 8 (dashboards router) ← independent
    ↓
Task 9 (integration test) ← depends on Tasks 3-8
    ↓
Task 10 (lint + verify) ← depends on Task 9
```

**Parallelizable:** Tasks 3, 4, 5, 6, 8 can all run in parallel after Task 2 completes.
