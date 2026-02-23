# Demo Mode (Guest Account)

Auto SRE includes a fully functional demo mode that serves synthetic data when a user logs in as a guest. This allows prospective users, conference demos, and CI/CD screenshot tests to experience every feature without a GCP project, credentials, or live telemetry.

---

## Overview

Demo mode is activated when a user clicks **"Continue as Guest"** on the login page. Every API request made during the session carries an `X-Guest-Mode: true` header. The backend middleware detects this header and sets a request-scoped `ContextVar`, which downstream route handlers check via `is_guest_mode()`. When true, handlers return pre-generated synthetic data instead of calling real GCP APIs.

**Key properties:**

- **No credentials required** — Guest users have no GCP project, no OAuth token, and no Firestore state.
- **Deterministic** — All synthetic data is seeded (`random.Random(seed=42)`), producing identical results across runs for reproducible tests.
- **Full coverage** — Every API endpoint that a logged-in user can reach also works in guest mode.
- **Isolated** — Guest mode uses a dedicated project ID (`cymbal-shops-demo`) and user (`guest@demo.autosre.dev`) that cannot collide with real data.

---

## Architecture

The demo mode pipeline has four layers:

```
┌─────────────────────────────────────────────────────────────────┐
│  Flutter / React UI                                             │
│  Sets X-Guest-Mode header, auto-selects cymbal-shops-demo       │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP (X-Guest-Mode: true)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI Middleware (sre_agent/api/middleware.py)                │
│  Detects header → set_guest_mode(True)                          │
│  Sets project_id = "cymbal-shops-demo"                          │
│  Sets user_id = "guest@demo.autosre.dev"                        │
└────────────────────────────┬────────────────────────────────────┘
                             │ ContextVar: _guest_mode_context = True
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Route Handlers (agent_graph.py, tools.py, dashboards.py, ...)  │
│  if is_guest_mode(): return synthetic_data(...)                  │
└────────────────────────────┬────────────────────────────────────┘
                             │ calls
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Synthetic Data Layer (sre_agent/tools/synthetic/)              │
│  cymbal_assistant.py  — Scenario definition                     │
│  demo_data_generator.py — Trace/graph/dashboard data            │
│  demo_chat_responses.py — Pre-recorded chat turns               │
│  demo_bigquery.py — SQL analytics data                          │
└─────────────────────────────────────────────────────────────────┘
```

---

## How Guest Mode Is Triggered

### 1. Frontend: Flutter Login

When the user clicks "Continue as Guest", the Flutter `AuthService` enters guest mode. Every subsequent HTTP request made by the `ProjectInterceptorClient` includes:

```
Authorization: Bearer dev-mode-bypass-token
X-Guest-Mode: true
```

The Flutter app also auto-selects the `cymbal-shops-demo` project and skips the project selection dialog.

### 2. Frontend: AgentOps React Iframe

The AgentOps dashboard is a React app rendered inside a Flutter `HtmlElementView` iframe. Since iframes cannot inherit parent-page HTTP headers, guest mode is propagated via a URL query parameter:

```
Flutter (agent_graph_iframe_web.dart)
  → builds iframe src: /graph/?project_id=cymbal-shops-demo&guest_mode=true

React (main.tsx)
  → reads URL params at startup
  → if guest_mode=true, sets axios default headers:
       X-Guest-Mode: true
       Authorization: Bearer dev-mode-bypass-token

React (App.tsx)
  → isGuestMode() helper reads URL param
  → auto-sets serviceName to "cymbal-assistant"
  → skips BigQuery onboarding wizard
  → preserves guest_mode param in URL rewrites
```

### 3. Backend: Middleware Detection

The auth middleware in `sre_agent/api/middleware.py` (line ~127) checks for the header:

```python
guest_header = request.headers.get("X-Guest-Mode")
if guest_header and guest_header.lower() == "true":
    set_guest_mode(True)
    set_current_project_id("cymbal-shops-demo")
    set_current_user_id("guest@demo.autosre.dev")
    creds = Credentials(token="guest-mode-token")
    set_current_credentials(creds)
```

This sets three `ContextVar` values that persist for the lifetime of the request. No real token validation occurs.

### 4. Route Handler: Guard Pattern

Every route handler that serves data uses the same guard pattern:

```python
from sre_agent.auth import is_guest_mode

@router.get("/endpoint")
async def my_endpoint(...):
    if is_guest_mode():
        return synthetic_response()
    # ... real GCP API call ...
```

---

## Synthetic Data Scenario

The demo data simulates a **Cymbal Shops AI Shopping Assistant** — a multi-agent e-commerce system built on Vertex AI Agent Engine. The scenario includes an incident where a bad prompt release (v2.4.1) causes excessive tool calls and degraded latency.

### Scenario Definition (`cymbal_assistant.py`)

| Component | Details |
|-----------|---------|
| **Root Agent** | `cymbal-assistant` — orchestrates 6 sub-agents |
| **Sub-Agents** | `product-discovery`, `cart-manager`, `order-tracker`, `customer-support`, `recommendation-engine`, `payment-processor` |
| **MCP Servers** | 8 servers (product-catalog, inventory, pricing, user-profiles, order-management, payment-gateway, shipping, analytics) |
| **Users** | 12 demo users across 4 GCP regions |
| **Time Window** | 7 days of trace data (~5,500 spans across ~82 sessions) |
| **Incident** | Days 4–5: v2.4.1 release causes `product-discovery` to loop tool calls, tripling latency |
| **Journey Types** | 6 user journey templates (product search, add-to-cart, checkout, order status, return, recommendation) |

### Data Generator (`demo_data_generator.py`)

The `DemoDataGenerator` class produces all the data needed for the Agent Graph, dashboard, and topology views:

| Method | Returns | Used By |
|--------|---------|---------|
| `get_topology()` | `{nodes, edges}` — agent hierarchy | `/api/v1/graph/topology` |
| `get_trajectories()` | `{nodes, links}` — Sankey flow | `/api/v1/graph/trajectories` |
| `get_timeseries()` | `{series: {nodeId: [TimeSeriesPoint]}}` | `/api/v1/graph/timeseries` |
| `get_node_detail(node_id)` | Per-agent statistics | `/api/v1/graph/node/{id}` |
| `get_dashboard_kpis()` | KPI summary (sessions, invocations, etc.) | `/api/v1/graph/dashboard/kpis` |
| `get_dashboard_timeseries()` | `{latency, qps, tokens}` charts | `/api/v1/graph/dashboard/timeseries` |
| `get_dashboard_models()` | Model call breakdown | `/api/v1/graph/dashboard/models` |
| `get_dashboard_tools()` | Tool call breakdown | `/api/v1/graph/dashboard/tools` |
| `get_dashboard_logs()` | Agent log entries | `/api/v1/graph/dashboard/logs` |
| `get_dashboard_sessions()` | Session list | `/api/v1/graph/dashboard/sessions` |
| `get_dashboard_traces()` | Trace list | `/api/v1/graph/dashboard/traces` |
| `get_registry_agents()` | Agent registry | `/api/v1/graph/registry/agents` |
| `get_registry_tools()` | Tool registry | `/api/v1/graph/registry/tools` |

### Chat Responses (`demo_chat_responses.py`)

Pre-recorded 4-turn investigation conversation streamed as NDJSON:

| Turn | User Message | Events Emitted |
|------|-------------|----------------|
| 1 | "investigate latency" | session, text, tool-call, tool-response, dashboard (incident timeline, metrics), text, suggestions |
| 2 | "show me traces" | text, tool-call, tool-response, dashboard (trace waterfall), text, suggestions |
| 3 | "analyze error patterns" | text, tool-call, tool-response, dashboard (log entries, council graph), text, suggestions |
| 4 | "what should we do?" | text, dashboard (remediation plan, metrics dashboard), text, suggestions |

Any user message triggers the next unplayed turn. After all 4 turns are exhausted, responses cycle back.

### BigQuery Analytics (`demo_bigquery.py`)

Provides a synthetic BigQuery SQL Analytics experience:

| Function | Returns | Used By |
|----------|---------|---------|
| `get_demo_datasets()` | `["traces", "agentops"]` | `GET /api/tools/bigquery/datasets` |
| `get_demo_tables(dataset)` | Table list per dataset | `GET /api/tools/bigquery/datasets/{id}/tables` |
| `get_demo_table_schema(dataset, table)` | Column definitions with types | `GET .../schema` |
| `get_demo_json_keys(dataset, table, col)` | JSON key discovery | `GET .../json-keys` |
| `execute_demo_query(sql)` | `{columns, rows}` | `POST /api/tools/bigquery/query` |

The SQL executor supports: `SELECT`, `SELECT DISTINCT`, `WHERE` (=, !=, LIKE, AND), `GROUP BY` with aggregates (`COUNT`, `SUM`, `AVG`, `MIN`, `MAX`), `ORDER BY`, and `LIMIT`. It operates against ~5,500 flattened span rows derived from the same `DemoDataGenerator` trace data.

---

## Guarded Endpoints

The following routers have `is_guest_mode()` guards:

| Router | File | Guard Count | Features Covered |
|--------|------|-------------|-----------------|
| **Agent Graph** | `api/routers/agent_graph.py` | 17 | Topology, trajectories, timeseries, node detail, dashboard KPIs/charts/tables, registry |
| **Agent Chat** | `api/routers/agent.py` | 1 | Chat streaming (NDJSON events) |
| **Tools (BigQuery)** | `api/routers/tools.py` | 6 | Datasets, tables, schema, JSON keys, SQL query, NL query |
| **Dashboards** | `api/routers/dashboards.py` | 14 | Custom dashboards CRUD, widget CRUD |
| **Preferences** | `api/routers/preferences.py` | 15 | All user preference endpoints (project, theme, layout, etc.) |
| **Graph Setup** | `api/routers/agent_graph_setup.py` | 5 | Bucket check, dataset link, LRO status, verify, schema steps |
| **Config** | `api/routers/system.py` | 1 | `guest_mode_enabled` flag in `/api/config` |

**Total: ~59 guarded endpoints.**

---

## Data Flow Diagrams

### Agent Graph (Topology View)

```
User opens AgentOps tab in guest mode
       │
       ▼
Flutter builds iframe with ?guest_mode=true
       │
       ▼
React reads param → sets axios headers (X-Guest-Mode: true)
       │
       ▼
React fetches /api/v1/graph/topology?project_id=cymbal-shops-demo
       │
       ▼
Backend: is_guest_mode() → True
       │
       ▼
DemoDataGenerator().get_topology()
  → Returns 7 nodes (root + 6 sub-agents) and 6 edges
       │
       ▼
React Flow renders interactive graph with sparkline overlays
  (sparklines from /api/v1/graph/timeseries → get_timeseries())
```

### Chat Investigation

```
User types "investigate latency" in chat pane
       │
       ▼
Flutter POST /api/genui/chat with X-Guest-Mode: true
  body: {"messages": [{"role": "user", "text": "investigate latency"}]}
       │
       ▼
Backend: is_guest_mode() → True
       │
       ▼
get_demo_turns() → selects turn 1 events
       │
       ▼
_guest_event_generator() yields NDJSON lines:
  {"type": "session", ...}
  {"type": "text", "text": "I'll investigate..."}
  {"type": "tool-call", "name": "analyze_latency_patterns", ...}
  {"type": "tool-response", ...}
  {"type": "dashboard", "dataType": "incident_timeline", ...}
  {"type": "dashboard", "dataType": "metric_chart", ...}
  {"type": "text", "text": "Analysis shows..."}
  {"type": "suggestions", "suggestions": [...]}
       │
       ▼
Flutter renders each event: text bubbles, tool cards,
  dashboard panels (incident timeline, metric chart), suggestion chips
```

### BigQuery SQL Analytics

```
User navigates to SQL Analytics tab in guest mode
       │
       ▼
Frontend GET /api/tools/bigquery/datasets
  → {"datasets": ["traces", "agentops"]}
       │
       ▼
User selects "traces" dataset
  GET /api/tools/bigquery/datasets/traces/tables
  → {"tables": ["_AllSpans", "_AllLogs"]}
       │
       ▼
User selects "_AllSpans" table
  GET .../schema → column definitions (span_id, trace_id, name, ...)
  GET .../columns/attributes/json-keys → GenAI semantic convention keys
       │
       ▼
User writes SQL: "SELECT name, COUNT(*) as cnt FROM traces._AllSpans
                   GROUP BY name ORDER BY cnt DESC LIMIT 10"
  POST /api/tools/bigquery/query
       │
       ▼
execute_demo_query() parses SQL with regex, applies GROUP BY + ORDER BY
  → {"columns": ["name", "cnt"], "rows": [{...}, ...]}
       │
       ▼
Frontend renders results table and chart visualization
```

---

## Adding Guest Mode to a New Endpoint

When adding a new API endpoint that should work in demo mode:

1. **Import the guard** in your router file:
   ```python
   from sre_agent.auth import is_guest_mode
   ```

2. **Add the guard** at the top of your endpoint function:
   ```python
   @router.get("/my-new-endpoint")
   async def my_endpoint(project_id: str):
       if is_guest_mode():
           return {"data": "synthetic response"}
       # ... real implementation ...
   ```

3. **Create synthetic data** if needed. For simple responses, inline data is fine. For complex responses, add a function to the appropriate module in `sre_agent/tools/synthetic/`:
   - `demo_data_generator.py` — Trace/graph/dashboard data
   - `demo_chat_responses.py` — Chat conversation events
   - `demo_bigquery.py` — SQL analytics data
   - Or create a new module for a distinct feature area

4. **Add an integration test** in `tests/integration/test_guest_mode_full.py`:
   ```python
   def test_my_endpoint(self, guest_client):
       r = guest_client.get("/my-new-endpoint", params=GRAPH_PARAMS)
       assert r.status_code == 200
       assert "data" in r.json()
   ```

5. **Run tests** to verify:
   ```bash
   uv run pytest tests/integration/test_guest_mode_full.py -v
   uv run pytest tests/unit/sre_agent/tools/synthetic/ -v
   ```

---

## Testing

### Integration Tests

`tests/integration/test_guest_mode_full.py` is the smoke test for the entire demo mode pipeline. It uses a `TestClient` with `X-Guest-Mode: true` headers and verifies every guarded endpoint returns valid, non-empty responses.

```bash
uv run pytest tests/integration/test_guest_mode_full.py -v
```

Test classes:
- `TestGuestModeAgentGraph` — topology, trajectories, timeseries, node detail, setup
- `TestGuestModeDashboard` — KPIs, timeseries, models, tools, logs, sessions, traces
- `TestGuestModeRegistry` — agents, tools
- `TestGuestModeChat` — streaming NDJSON, event types, suggestions
- `TestGuestModeDashboards` — custom dashboards CRUD
- `TestGuestModeBigQuery` — datasets, tables, schema, JSON keys, SQL queries
- `TestGuestModeConfig` — `guest_mode_enabled` flag

### Unit Tests

`tests/unit/sre_agent/tools/synthetic/test_demo_bigquery.py` validates the SQL executor in isolation (30 tests covering SELECT, WHERE, GROUP BY, ORDER BY, LIMIT, DISTINCT, type correctness, and fallback behavior).

```bash
uv run pytest tests/unit/sre_agent/tools/synthetic/test_demo_bigquery.py -v
```

---

## Files Reference

### Synthetic Data Modules

| File | Purpose |
|------|---------|
| `sre_agent/tools/synthetic/cymbal_assistant.py` | Scenario definition: agents, MCP servers, users, journey templates, incident timeline |
| `sre_agent/tools/synthetic/demo_data_generator.py` | `DemoDataGenerator` class: generates traces, topology, timeseries, dashboard data from the scenario |
| `sre_agent/tools/synthetic/demo_chat_responses.py` | 4-turn pre-recorded investigation conversation with all NDJSON event types |
| `sre_agent/tools/synthetic/demo_bigquery.py` | BigQuery analytics: datasets, tables, schemas, JSON keys, regex-based SQL executor |

### Backend Integration Points

| File | What It Does for Guest Mode |
|------|-----------------------------|
| `sre_agent/auth.py` | `set_guest_mode()` / `is_guest_mode()` — ContextVar-based flag |
| `sre_agent/api/middleware.py` | Detects `X-Guest-Mode` header, sets synthetic credentials and project ID |
| `sre_agent/api/routers/agent_graph.py` | 17 guards: topology, trajectories, timeseries, node detail, dashboard panels, registry |
| `sre_agent/api/routers/agent.py` | 1 guard: chat streaming with pre-recorded turns |
| `sre_agent/api/routers/tools.py` | 6 guards: BigQuery datasets, tables, schema, JSON keys, SQL query, NL query |
| `sre_agent/api/routers/dashboards.py` | 14 guards: custom dashboards and widgets CRUD |
| `sre_agent/api/routers/preferences.py` | 15 guards: all user preferences (returns sensible defaults) |
| `sre_agent/api/routers/agent_graph_setup.py` | 5 guards: BigQuery setup wizard steps (returns success) |
| `sre_agent/api/routers/system.py` | 1 guard: `guest_mode_enabled` in config response |

### Frontend Integration Points

| File | What It Does for Guest Mode |
|------|-----------------------------|
| `autosre/lib/services/auth_service.dart` | `isGuestMode` property, sets guest headers on login |
| `autosre/lib/services/api_client.dart` | `ProjectInterceptorClient` injects `X-Guest-Mode` header |
| `autosre/lib/widgets/dashboard/agent_graph_iframe_web.dart` | Passes `guest_mode=true` URL param to React iframe |
| `agent_ops_ui/src/main.tsx` | Reads URL param, sets axios default headers |
| `agent_ops_ui/src/App.tsx` | `isGuestMode()` helper, onboarding bypass, auto service name |

---

## Related Documentation

- [Default Dashboard Experience](default_experience.md) — How the standard (non-guest) sign-in flow works
- [Authentication](../authentication/authentication.md) — OAuth2, EUC, and token management
- [AgentOps Dashboard](../agent_ops/dashboard.md) — AgentOps dashboard architecture
- [Getting Started](getting_started.md) — Installation and first run
