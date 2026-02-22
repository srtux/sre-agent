# Dashboard Query Language Guide

This guide explains how to use the interactive querying capabilities built into the Auto SRE Investigation Dashboard. With recent updates, the dashboard is no longer just a passive display of agent actions—it functions as a full Observability Explorer.

## Manual Query Bar
Every major dashboard panel (Metrics, Logs, Traces, Alerts) features a `ManualQueryBar`. This allows you to pause the automated investigation and dig into the raw GCP telemetry yourself.

When you submit a manual query, the dashboard fetches data directly from GCP via the backend REST endpoints (e.g., `/api/tools/metrics/query`, `/api/tools/logs/query`) using an isolated background thread (`AppIsolate`) to prevent UI freezing.

## Query Languages Supported

The UI includes a language toggle (MQL/PromQL/SQL) tailored to the specific data source you are querying.

### 1. Monitoring Query Language (MQL)
**Used in:** Metrics Panel
MQL is Google Cloud's native time-series language. It's powerful for complex aggregations and cross-metric joins.

**Example:**
```mql
fetch k8s_container
| metric 'kubernetes.io/container/cpu/core_usage_time'
| align rate(1m)
| every 1m
| group_by [resource.cluster_name], [value_core_usage_time_aggregate: aggregate(value.core_usage_time)]
```

### 2. PromQL (Prometheus Query Language)
**Used in:** Metrics Panel
Auto SRE natively supports PromQL for Cloud Monitoring. This is often the preferred choice for teams migrating from Prometheus or those who prefer simpler syntax for standard metric aggregation.

**Example:**
```promql
sum(rate(kubernetes_io_container_cpu_core_usage_time[5m])) by (cluster_name)
```

### 3. Log Queries (Logging Syntax)
**Used in:** Logs Panel
Standard Cloud Logging filtering syntax.

**Example:**
```text
resource.type="k8s_container"
severity>=ERROR
textPayload:"Connection refused"
```

### 4. BigQuery SQL
**Used in:** Data Panel, Agent Graph Dashboard
For fleet-wide property graph traversal or custom analytical queries across the `agent_graph` table.

**Example:**
```sql
SELECT
  JSON_EXTRACT_SCALAR(payload, '$.agent_id') as agent
FROM
  `your-project.agent_registry.agent_graph_hourly`
WHERE
  timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
```

## Autocomplete & Natural Language (Upcoming/Experimental)
The dashboard features a `QueryAutocompleteOverlay` that assists with:
- **Metric Descriptors**: Auto-suggesting valid GCP metric types as you type.
- **Resource Labels**: Suggesting common labels (e.g., `project_id`, `cluster_name`) to filter by.

Auto SRE's LLM can also assist in writing MQL/PromQL queries. You can ask the agent in the chat window to "Write an MQL query to show latency for the checkout service," and the agent will synthesize the correct syntax utilizing its internal tool set.
