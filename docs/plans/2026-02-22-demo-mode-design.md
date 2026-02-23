# Demo Mode: Full-Stack Synthetic Data for Guest Users

> **Date**: 2026-02-22
> **Status**: Design approved, ready for implementation

## Problem

Guest users (no login) on the cymbal-shops-demo project only see logs working. All other features — Agent Graph, AgentOps dashboard, trace explorer, Sankey trajectory, chat interface, canvases, council synthesis — are broken because they depend on BigQuery, Vertex AI, or real GCP credentials.

## Solution

Expand the existing guest mode infrastructure to serve realistic synthetic data for **every** feature. The demo tells the story of a real AI agent application (Cymbal Shops Shopping Assistant) experiencing an incident caused by a bad prompt release.

---

## Cymbal Shops AI Shopping Assistant Architecture

### Agent Hierarchy

```
Customer (user)
    │
    ▼
Cymbal Assistant (root-agent, gemini-2.5-flash)
    ├── Product Discovery Agent (sub-agent)
    │       ├── search_products (Catalog MCP)
    │       ├── get_product_details (Catalog MCP)
    │       ├── get_reviews (Catalog MCP)
    │       └── ► Personalization Agent (agent-to-agent)
    │
    ├── Order Management Agent (sub-agent)
    │       ├── get_order_status (Order MCP)
    │       ├── list_orders (Order MCP)
    │       ├── create_return (Order MCP)
    │       ├── modify_order (Order MCP)
    │       ├── get_customer_profile (Customer MCP)
    │       └── ► Fulfillment Agent (agent-to-agent)
    │
    ├── Checkout Agent (sub-agent)
    │       ├── add_to_cart (Cart MCP)
    │       ├── get_cart (Cart MCP)
    │       ├── process_payment (Payment MCP)
    │       ├── validate_coupon (Payment MCP)
    │       ├── get_payment_methods (Payment MCP)
    │       ├── ► Personalization Agent (agent-to-agent, upsells)
    │       └── ► Fulfillment Agent (agent-to-agent, shipping)
    │
    ├── Support Agent (sub-agent)
    │       ├── search_knowledge_base (Support MCP)
    │       ├── create_ticket (Support MCP)
    │       ├── escalate_to_human (Support MCP)
    │       ├── get_customer_profile (Customer MCP)
    │       └── get_loyalty_points (Customer MCP)
    │
    ├── Personalization Agent (shared sub-agent)
    │       ├── get_customer_profile (Customer MCP)
    │       ├── get_purchase_history (Customer MCP)
    │       ├── update_preferences (Customer MCP)
    │       ├── get_personalized_recs (Recommendation MCP)
    │       ├── get_similar_products (Recommendation MCP)
    │       └── get_loyalty_points (Customer MCP)
    │
    └── Fulfillment Agent (shared sub-agent)
            ├── check_availability (Inventory MCP)
            ├── get_warehouse_stock (Inventory MCP)
            ├── reserve_inventory (Inventory MCP)
            ├── calculate_shipping (Logistics MCP)
            ├── get_delivery_estimate (Logistics MCP)
            └── track_shipment (Logistics MCP)
```

### MCP Servers (8 total)

| MCP Server | Deployment | Tools |
|------------|-----------|-------|
| Catalog MCP | Cloud Run | search_products, get_product_details, get_reviews |
| Recommendation MCP | Cloud Run | get_personalized_recs, get_trending, get_similar_products |
| Order MCP | Cloud Run | get_order_status, list_orders, create_return, modify_order |
| Payment MCP | Cloud Run | process_payment, validate_coupon, get_payment_methods |
| Inventory MCP | Cloud Run | check_availability, get_warehouse_stock, reserve_inventory |
| Customer MCP | Cloud Run | get_customer_profile, get_purchase_history, update_preferences, get_loyalty_points |
| Logistics MCP | Cloud Run | calculate_shipping, get_delivery_estimate, track_shipment |
| Support MCP | Cloud Run | search_knowledge_base, create_ticket, escalate_to_human |
| Cart MCP | Cloud Run | add_to_cart, get_cart, remove_from_cart |

### Infrastructure

- **Shopping App Frontend**: Cloud Run (`cymbal-shops-frontend`), us-central1
- **Agent Engine**: Vertex AI Agent Engine (`cymbal-assistant-001`), us-central1
- **MCP Servers**: Cloud Run sidecars, us-central1
- **Agent version**: v2.4.0 (pre-incident), v2.4.1 (bad release), v2.4.0 (rollback)

---

## The Incident: Bad Prompt Release (v2.4.1)

### Timeline

| Time (UTC) | Event |
|------------|-------|
| Feb 15, 00:00 | Data starts, v2.4.0 running normally |
| Feb 18, 02:15 | Release v2.4.1 deployed (bad Product Discovery prompt) |
| Feb 18, 02:30 | Tool call volume begins increasing |
| Feb 18, 08:00 | Payment MCP rate limiting starts (429s) |
| Feb 20, 11:30 | Alert fires: "Anomalous tool call volume" |
| Feb 20, 15:45 | Rollback to v2.4.0 |
| Feb 20, 16:00 | Metrics start recovering |
| Feb 22, 00:00 | Data ends, fully recovered |

### Root Cause

Product Discovery Agent's new prompt tells it to "ensure every result has verified real-time availability and the best current pricing including any applicable promotions". This causes:

1. **check_availability** called 5× per search (Inventory MCP) — was 0×
2. **validate_coupon** called 3× per search (Payment MCP) — was 0×
3. **Fulfillment Agent** invoked by Product Discovery (should never happen) — warehouse-level stock checks
4. Payment MCP rate-limits → 429 errors
5. Latency: 500ms → 3200ms, Error rate: 0.1% → 8.5%

---

## Data Generation

### Users (12)

| User ID | Display Name | Region | GCP Region |
|---------|-------------|--------|------------|
| alice@gmail.com | Alice Chen | San Francisco, US | us-west1 |
| bob@outlook.com | Bob Martinez | New York, US | us-east4 |
| carol@yahoo.com | Carol Johnson | Chicago, US | us-central1 |
| dave@gmail.com | Dave Williams | London, UK | europe-west2 |
| emma@gmail.com | Emma Tanaka | Tokyo, JP | asia-northeast1 |
| frank@company.com | Frank O'Brien | Sydney, AU | australia-southeast1 |
| grace@gmail.com | Grace Kim | Toronto, CA | northamerica-northeast1 |
| hiro@outlook.com | Hiro Silva | São Paulo, BR | southamerica-east1 |
| isabella@gmail.com | Isabella Patel | Mumbai, IN | asia-south1 |
| james@yahoo.com | James Müller | Berlin, DE | europe-west3 |
| kate@gmail.com | Kate Thompson | Seattle, US | us-west1 |
| liam@outlook.com | Liam Dubois | Paris, FR | europe-west1 |

### Volume

| Metric | Value |
|--------|-------|
| Total sessions | ~80 |
| Sessions/day | 10-12 |
| Turns/session | 3-8 (avg 5) |
| Total traces | ~400 |
| Spans/trace (normal) | 8-12 |
| Spans/trace (degraded) | 18-25 |
| Total spans | ~5,000-6,000 |

### Session Journey Templates

| Journey | % | Turns | Agents |
|---------|---|-------|--------|
| Search → browse → buy | 30% | 5-7 | Product Discovery, Personalization, Checkout, Fulfillment |
| Search → compare | 25% | 3-5 | Product Discovery, Personalization |
| Order tracking | 15% | 2-3 | Order Management, Fulfillment |
| Return/refund | 10% | 4-6 | Order Management, Support |
| Support question | 10% | 2-4 | Support |
| Browse → abandon → return | 10% | 6-8 | Product Discovery, Personalization, Checkout |

### OTel Span Attributes

```json
{
  "resource": {
    "service.name": "cymbal-assistant",
    "service.version": "v2.4.0",
    "cloud.provider": "gcp",
    "cloud.region": "us-central1",
    "cloud.platform": "gcp_vertex_ai",
    "cloud.resource_id": "projects/cymbal-shops-demo/locations/us-central1/reasoningEngines/cymbal-assistant-001"
  },
  "attributes": {
    "gen_ai.system": "vertex_ai",
    "gen_ai.operation.name": "invoke_agent|execute_tool|generate_content",
    "gen_ai.agent.name": "product-discovery",
    "gen_ai.agent.id": "product-discovery-v1",
    "gen_ai.conversation.id": "session-abc-123",
    "gen_ai.request.model": "gemini-2.5-flash",
    "gen_ai.response.model": "gemini-2.5-flash-001",
    "gen_ai.usage.input_tokens": 1250,
    "gen_ai.usage.output_tokens": 380,
    "gen_ai.response.finish_reasons": ["stop"],
    "gen_ai.tool.name": "search_products",
    "gen_ai.tool.call.id": "call_abc123",
    "user.id": "alice@gmail.com",
    "user.geo.region": "US-CA",
    "cymbal.release_version": "v2.4.0",
    "cymbal.journey_type": "search_browse_buy"
  }
}
```

---

## Implementation Components

### Backend Changes

1. **`sre_agent/tools/synthetic/cymbal_assistant.py`** (NEW)
   - Cymbal Assistant agent architecture definition
   - Agent hierarchy, tool mappings, MCP server configs
   - Normal vs degraded trace templates

2. **`sre_agent/tools/synthetic/demo_data_generator.py`** (NEW)
   - Deterministic session/trace/span generation over 7 days
   - User pool, journey templates, trace builders
   - Pre-computed and cached (not generated on each request)

3. **`sre_agent/tools/synthetic/demo_chat_responses.py`** (NEW)
   - Pre-recorded chat responses with GenUI events
   - Dashboard events (all canvas types)
   - Council synthesis results

4. **Modify `sre_agent/api/routers/agent_graph.py`**
   - Add `is_guest_mode()` checks to all endpoints
   - Return synthetic topology, sankey, node/edge details, traces, metrics

5. **Modify `sre_agent/api/routers/agent.py`**
   - Add `is_guest_mode()` check to chat endpoint
   - Stream pre-recorded responses

6. **Modify `sre_agent/api/routers/dashboards.py`**
   - Return demo dashboards in guest mode

7. **Expand `sre_agent/tools/synthetic/provider.py`**
   - Point existing methods at Cymbal Assistant scenario (not just N+1 DB bug)

### Frontend Changes

- None required (guest mode header mechanism already works)
- AgentOps UI already consumes the API — just needs data

### Tests

- Unit tests for demo data generator (schema validation)
- Integration test: guest mode → every router returns valid data
- Snapshot tests for pre-recorded chat responses

---

## Pre-Recorded Chat Demo Flow

When a guest user sends any message, the system returns a pre-recorded investigation that showcases ALL features:

### Turn 1: "Investigate the latency spike in checkout"
- Agent text: "I'll investigate the checkout latency issue..."
- Dashboard events: Metrics panel (latency chart), Alerts panel (4 alerts)
- Canvas: Incident Timeline

### Turn 2: (auto-continue or user prompt)
- Agent text: "I found a significant increase in tool calls after release v2.4.1..."
- Dashboard events: Trace panel (degraded trace), Logs panel (error logs)
- Canvas: Agent Trace (showing the bloated trace)

### Turn 3:
- Agent text: "The root cause is a prompt change in Product Discovery Agent..."
- Dashboard events: All panels updated
- Canvas: Service Topology (showing Cymbal Assistant architecture)
- Canvas: AI Reasoning (showing the investigation logic)

### Turn 4:
- Agent text: "Recommendation: Roll back to v2.4.0..."
- Canvas: Metrics Dashboard (before/after comparison)
- Council synthesis event (all panel findings)
