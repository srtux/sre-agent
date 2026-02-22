# Agent Dashboard

The Agent Dashboard provides fleet-wide visibility into multi-agent performance, model utilization, tool efficacy, and operational logs within the AgentOps UI.

## Accessing the Dashboard

Navigate to the **Dashboard** tab in the AgentOps UI (`/graph/?tab=dashboard`). The dashboard is the fifth tab alongside Agents, Tools, Agent Graph, and Trajectory Flow.

## Dashboard Sections

### Global Controls (Toolbar)

The toolbar at the top provides three filter controls that affect all sections:

- **Time Range**: Select from 1h, 6h, 24h, 7d, or 30d windows
- **Agent Filter**: Multi-select dropdown to filter by specific agents (empty = all agents)
- **Group By Agent**: Toggle to aggregate or group data by individual agent
- **Reset**: Returns all filters to defaults (24h, all agents, no grouping)

### Section 1: KPI Cards

Four key performance indicators displayed as cards with trend arrows:

| KPI | Description |
|-----|-------------|
| Total Sessions | Number of agent sessions in the time window |
| Avg Turns | Average conversation turns per session |
| Root Invocations | Number of root agent invocations |
| Error Rate | Percentage of requests resulting in errors |

Each card shows a trend indicator comparing to the previous period.

### Section 2: Interaction Metrics (Charts)

Three ECharts-based visualizations:

- **Latency Over Time**: Multi-line chart showing P50 and P95 latency
- **QPS & Error Rate**: Dual Y-axis chart with bar (QPS) and line (error rate)
- **Token Usage**: Stacked area chart showing input vs output token consumption

### Section 3: Model & Tool Performance (Tables)

Two side-by-side virtualized data tables (responsive — stacks on mobile):

**Model Usage Table**:
| Column | Description |
|--------|-------------|
| Model | Model name (e.g., gemini-2.5-flash) |
| Calls | Total invocations |
| P95 Latency | 95th percentile response time |
| Error Rate | Percentage of failed calls (red if > 5%) |
| Quota Exits | Number of quota-limited requests |
| Tokens | Total tokens consumed |

**Tool Performance Table**:
| Column | Description |
|--------|-------------|
| Tool | Tool name (e.g., fetch_traces) |
| Calls | Total invocations |
| P95 Latency | 95th percentile execution time |
| Error Rate | Percentage of failed calls (red if > 5%) |

Both tables support sorting by clicking column headers and are virtualized for efficient rendering of 1000+ rows.

### Section 4: Agent Logs

A full-width virtualized log table showing:

- **Timestamp**: Log entry time (formatted by locale)
- **Agent**: Which agent generated the log
- **Severity**: Color-coded badge (INFO/WARNING/ERROR/DEBUG)
- **Message**: Log message (truncated with ellipsis, full text on hover)
- **Trace ID**: First 12 characters of the trace ID for cross-referencing

## Technical Details

### Data Flow

The dashboard queries real BigQuery data via the Agent Graph router. The React hooks (`useDashboardMetrics`, `useDashboardTables`) call these backend endpoints using axios and React Query:

| Endpoint | Method | Description | Cache TTL |
|----------|--------|-------------|-----------|
| `/api/v1/graph/dashboard/kpis` | GET | KPI metrics with trend comparisons (current vs previous period) | 300s |
| `/api/v1/graph/dashboard/timeseries` | GET | Latency (P50/P95), QPS, token usage time series | 300s |
| `/api/v1/graph/dashboard/models` | GET | Per-model call counts, P95 latency, error rate, token usage | 300s |
| `/api/v1/graph/dashboard/tools` | GET | Per-tool call counts, P95 latency, error rate | 300s |
| `/api/v1/graph/dashboard/logs` | GET | Agent activity log stream with derived severity | 60s |

All endpoints accept these query parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `project_id` | string | required | GCP project that owns the BigQuery dataset |
| `dataset` | string | `agentops` | BigQuery dataset name |
| `hours` | float | 24.0 | Look-back window (1–720 hours) |
| `service_name` | string | optional | Filter by agent service name |

The `/dashboard/logs` endpoint also accepts a `limit` parameter (100–5000, default 2000).

### BigQuery Tables

- **KPIs, Models, Tools, Logs**: Query `agent_spans_raw` (materialized view of OTel spans)
- **Timeseries**: Query `agent_graph_hourly` (pre-aggregated hourly table)

See [bq_schema.md](bq_schema.md) for full column definitions.

### Backend Caching

All dashboard endpoints are decorated with `@async_ttl_cache` (found in `sre_agent/api/helpers/cache.py`). The KPI, timeseries, models, and tools endpoints use a 300-second TTL. The logs endpoint uses a 60-second TTL for fresher data.

This TTL memory cache significantly reduces the load on BigQuery by reusing aggregated analytics results, aligning with the default 30-second `staleTime` and background refetch behaviors of the React Query frontend.

### Dependencies

- **React Query** (`@tanstack/react-query`): Data fetching, caching, background refetch
- **ECharts** (`echarts-for-react`): Canvas-rendered charts with dark theme
- **TanStack Table** (`@tanstack/react-table`): Headless table logic with sorting
- **TanStack Virtual** (`@tanstack/react-virtual`): Row virtualization for large datasets
- **Lucide React**: Icons for toolbar controls and trend indicators

### Testing

All dashboard components have comprehensive tests:

**Backend** (pytest):
```
tests/unit/sre_agent/api/routers/test_agent_graph.py  # 26 dashboard tests
  TestDashboardKpis       — 6 tests (success, empty, 404, 500, validation, service_name filter)
  TestDashboardTimeseries — 4 tests (success, empty, 404, validation)
  TestDashboardModels     — 4 tests (success, empty, 404, multiple models)
  TestDashboardTools      — 4 tests (success, empty, 404, validation)
  TestDashboardLogs       — 8 tests (success, severity mapping, limit, 404, validation)
```

Run with: `uv run pytest tests/unit/sre_agent/api/routers/test_agent_graph.py -k Dashboard`

**Frontend** (vitest):
```
src/contexts/DashboardFilterContext.test.tsx    # 8 tests
src/hooks/useDashboardMetrics.test.ts           # 6 tests
src/hooks/useDashboardTables.test.ts            # 5 tests
src/components/dashboard/AgentDashboard.test.tsx # 6 tests
src/components/dashboard/DashboardToolbar.test.tsx # 10 tests
src/components/dashboard/panels/KpiGrid.test.tsx # 5 tests
src/components/dashboard/panels/InteractionMetricsPanel.test.tsx # 6 tests
src/components/dashboard/panels/ModelAndToolPanel.test.tsx # 6 tests
src/components/dashboard/panels/AgentLogsPanel.test.tsx # 7 tests
src/components/charts/EChartWrapper.test.tsx     # 9 tests
src/components/tables/VirtualizedDataTable.test.tsx # 10 tests
```

Run with: `cd agent_ops_ui && npm run test`
