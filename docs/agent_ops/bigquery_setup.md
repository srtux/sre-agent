# BigQuery Setup for Agent Graph Visualization

This guide describes the necessary BigQuery configuration to power the **Agent Graph** visualization in AutoSRE.

## 1. Table Schema: `agent_spans_raw`

The visualization aggregates data from a BigQuery table named `agent_spans_raw`. This table should contain the following columns:

| Column | Type | Description |
| :--- | :--- | :--- |
| `trace_id` | STRING | ID of the trace (span group). **(Clustered)** |
| `session_id` | STRING | ID of the user session. **(Clustered)** |
| `span_id` | STRING | ID of the individual span. |
| `parent_id` | STRING | ID of the parent span (nullable). |
| `node_label` | STRING | Display label for the node (e.g., "SQL Generator"). **(Clustered)** |
| `node_type` | STRING | Category of node (e.g., "Agent", "Tool", "LLM"). |
| `start_time` | TIMESTAMP | Start timestamp of the operation. **(Partitioned)** |
| `duration_ms` | FLOAT64 | Duration of the operation in milliseconds.|
| `status_code` | INT64 | Status (1: OK, 2: Error). |
| `input_tokens` | INT64 | Tokens consumed. |
| `output_tokens` | INT64 | Tokens generated. |
| `error_type` | STRING | Error type/description. |
| `agent_description`| STRING | Role/Description of an Agent node. |
| `tool_description` | STRING | Description of a Tool node. |
| `request_model` | STRING | The model requested (e.g. gemini-1.5-pro). |
| `response_model` | STRING| The actual model that responded. |
| `finish_reasons` | STRING | Reason the LLM stopped generating. |
| `project_id` | STRING | The GCP Project ID (extracted from resource attributes). |

## 2. Setup: Standard View (Recommended)

To avoid limitations with "Incremental" Materialized Views (such as the `ARRAY function` error), start with a standard **View**. BigQuery's "Smart Tuning" will still optimize queries against this view.

```sql
CREATE OR REPLACE VIEW `my-project.GRAPH_DATASET.agent_spans_raw`
AS
SELECT
  span_id,
  parent_span_id AS parent_id,
  trace_id,
  start_time,
  -- Grouping IDs
  JSON_VALUE(attributes, '$.\"gen_ai.conversation.id\"') AS session_id,
  JSON_VALUE(resource.attributes, '$.\"gcp.project_id\"') AS project_id,
  -- Performance
  CAST(duration_nano AS FLOAT64) / 1000000.0 AS duration_ms,
  status.code AS status_code,
  JSON_VALUE(attributes, '$.\"error.type\"') AS error_type,
  -- GenAI Metadata
  SAFE_CAST(JSON_VALUE(attributes, '$.\"gen_ai.usage.input_tokens\"') AS INT64) AS input_tokens,
  SAFE_CAST(JSON_VALUE(attributes, '$.\"gen_ai.usage.output_tokens\"') AS INT64) AS output_tokens,
  JSON_VALUE(attributes, '$.\"gen_ai.request.model\"') AS request_model,
  JSON_VALUE(attributes, '$.\"gen_ai.response.model\"') AS response_model,
  -- UI Rich Metadata
  JSON_VALUE(attributes, '$.\"gen_ai.agent.description\"') AS agent_description,
  JSON_VALUE(attributes, '$.\"gen_ai.tool.description\"') AS tool_description,
  -- Node Classification
  CASE
    WHEN JSON_VALUE(attributes, '$.\"gen_ai.operation.name\"') = 'invoke_agent' THEN 'Agent'
    WHEN JSON_VALUE(attributes, '$.\"gen_ai.operation.name\"') = 'execute_tool' THEN 'Tool'
    WHEN JSON_VALUE(attributes, '$.\"gen_ai.operation.name\"') = 'generate_content' THEN 'LLM'
    ELSE 'Glue'
  END AS node_type,
  -- Display Label
  COALESCE(
    JSON_VALUE(attributes, '$.\"gen_ai.agent.name\"'),
    JSON_VALUE(attributes, '$.\"gen_ai.tool.name\"'),
    JSON_VALUE(attributes, '$.\"gen_ai.response.model\"'),
    name
  ) AS node_label
FROM `my-project.traces._AllSpans`
WHERE JSON_VALUE(resource.attributes, '$.\"service.name\"') = "sre-agent";
```

## 3. Optimization: Materialized View

If you have millions of traces and the graph is slow, you can use a **Materialized View**. Note that MVs have stricter SQL requirements.

```sql
CREATE MATERIALIZED VIEW `my-project.agent_graph.agent_spans_raw`
CLUSTER BY trace_id, session_id, node_label
OPTIONS (
  enable_refresh = true,
  refresh_interval_minutes = 60,
  max_staleness = INTERVAL "1" HOUR,
  allow_non_incremental_definition = true
)
AS
SELECT
  span_id,
  parent_span_id AS parent_id,
  trace_id,
  start_time,
  -- Grouping IDs
  JSON_VALUE(attributes, '$.\"gen_ai.conversation.id\"') AS session_id,
  JSON_VALUE(resource.attributes, '$.\"gcp.project_id\"') AS project_id,
  -- Performance
  CAST(duration_nano AS FLOAT64) / 1000000.0 AS duration_ms,
  status.code AS status_code,
  JSON_VALUE(attributes, '$.\"error.type\"') AS error_type,
  -- GenAI Metadata
  SAFE_CAST(JSON_VALUE(attributes, '$.\"gen_ai.usage.input_tokens\"') AS INT64) AS input_tokens,
  SAFE_CAST(JSON_VALUE(attributes, '$.\"gen_ai.usage.output_tokens\"') AS INT64) AS output_tokens,
  JSON_VALUE(attributes, '$.\"gen_ai.request.model\"') AS request_model,
  JSON_VALUE(attributes, '$.\"gen_ai.response.model\"') AS response_model,
  -- UI Rich Metadata
  JSON_VALUE(attributes, '$.\"gen_ai.agent.description\"') AS agent_description,
  JSON_VALUE(attributes, '$.\"gen_ai.tool.description\"') AS tool_description,
  -- Node Classification
  CASE
    WHEN JSON_VALUE(attributes, '$.\"gen_ai.operation.name\"') = 'invoke_agent' THEN 'Agent'
    WHEN JSON_VALUE(attributes, '$.\"gen_ai.operation.name\"') = 'execute_tool' THEN 'Tool'
    WHEN JSON_VALUE(attributes, '$.\"gen_ai.operation.name\"') = 'generate_content' THEN 'LLM'
    ELSE 'Glue'
  END AS node_type,
  -- Display Label
  COALESCE(
    JSON_VALUE(attributes, '$.\"gen_ai.agent.name\"'),
    JSON_VALUE(attributes, '$.\"gen_ai.tool.name\"'),
    JSON_VALUE(attributes, '$.\"gen_ai.response.model\"'),
    name
  ) AS node_label
FROM `my-project.TRACE_DATASET._AllSpans`
WHERE JSON_VALUE(resource.attributes, '$.\"service.name\"') = "sre-agent";
```


## 4. BigQuery Property Graph

The application uses the **BigQuery Property Graph** feature to model relationships between spans. Create the property graph referencing your Materialized View:

```sql
CREATE OR REPLACE PROPERTY GRAPH `my-project.GRAPH_DATASET.agent_trace_graph`
  NODE TABLES (
    `my-project.GRAPH_DATASET.agent_spans_raw` AS Span
      KEY (span_id)
      LABEL Span
      PROPERTIES ALL COLUMNS
  )
  EDGE TABLES (
    `my-project.GRAPH_DATASET.agent_spans_raw` AS ParentOf
      KEY (span_id)
      SOURCE KEY (parent_id) REFERENCES Span (span_id)
      DESTINATION KEY (span_id) REFERENCES Span (span_id)
      LABEL ParentOf
  );
```

## 5. Sample Aggregation Queries

The AutoSRE application uses the following patterns to extract insights from the property graph.

### 5.1 The "Gold Standard" Production Query
This query generates the full JSON payload for the Multi-Trace Graph UI, including call counts, error rates, and p95 latency.

```sql
WITH GraphPaths AS (
  -- 1. Traverse the graph to find parent->child paths (1 to 5 hops)
  SELECT *
  FROM GRAPH_TABLE(
    `my-project.GRAPH_DATASET.agent_trace_graph`
    MATCH (src:Span)-[:ParentOf]->{1,5}(dst:Span)
    -- Filter out 'Glue' noise and self-referential loops
    WHERE src.node_type != 'Glue'
      AND dst.node_type != 'Glue'
      AND src.node_label != dst.node_label
    COLUMNS (
      src.node_label AS source_id, src.node_type AS source_type,
      dst.node_label AS target_id, dst.node_type AS target_type,
      dst.trace_id AS trace_id, dst.session_id AS session_id,
      dst.duration_ms AS duration_ms, dst.input_tokens AS input_tokens,
      dst.output_tokens AS output_tokens, dst.status_code AS status_code,
      dst.error_type AS error_type, dst.agent_description AS agent_description,
      dst.tool_description AS tool_description
    )
  )
),
AggregatedEdges AS (
  -- 2. Calculate edge statistics (Call Counts, Errors, Latency)
  SELECT
    source_id, target_id, source_type, target_type,
    COUNT(DISTINCT session_id) AS unique_sessions,
    COUNT(*) AS call_count,
    COUNTIF(status_code = 2) AS error_count,
    ROUND(SAFE_DIVIDE(COUNTIF(status_code = 2), COUNT(*)) * 100, 2) AS error_rate_pct,
    ROUND(AVG(duration_ms), 2) AS avg_duration_ms,
    ROUND(APPROX_QUANTILES(duration_ms, 100)[OFFSET(95)], 2) AS p95_duration_ms,
    SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)) AS edge_tokens
  FROM GraphPaths
  GROUP BY 1, 2, 3, 4
),
BaseNodes AS (
  -- 3. Extract unique Nodes and their summary metrics
  SELECT target_id AS id, target_type AS type, ANY_VALUE(COALESCE(agent_description, tool_description)) AS description,
    SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)) AS total_tokens,
    COUNTIF(status_code = 2) > 0 AS has_error
  FROM GraphPaths GROUP BY 1, 2
  UNION DISTINCT
  SELECT source_id AS id, source_type AS type, NULL AS description, 0 AS total_tokens, FALSE AS has_error
  FROM GraphPaths GROUP BY 1, 2
),
AggregatedNodes AS (
  -- 4. Deduplicate and calculate Topology Flags (Root vs Leaf)
  SELECT bn.*,
    IF(bn.id NOT IN (SELECT target_id FROM AggregatedEdges), TRUE, FALSE) AS is_root,
    IF(bn.id NOT IN (SELECT source_id FROM AggregatedEdges), TRUE, FALSE) AS is_leaf
  FROM BaseNodes bn
  QUALIFY ROW_NUMBER() OVER(PARTITION BY id ORDER BY total_tokens DESC) = 1
)
-- 5. Final JSON Output for Flutter
SELECT TO_JSON_STRING(STRUCT(
  (SELECT ARRAY_AGG(STRUCT(id, type, description, total_tokens, has_error, is_root, is_leaf)) FROM AggregatedNodes) AS nodes,
  (SELECT ARRAY_AGG(STRUCT(source_id, target_id, source_type, target_type, call_count, error_count, error_rate_pct, edge_tokens, avg_duration_ms, p95_duration_ms, unique_sessions)) FROM AggregatedEdges) AS edges
)) AS flutter_graph_payload;
```

### 5.2 Discovery: Top Latency Bottlenecks
Find which specific agent-to-tool connections are contributing most to tail latency (p95) across all traces.

```sql
SELECT
  source_id,
  target_id,
  ROUND(APPROX_QUANTILES(duration_ms, 100)[OFFSET(95)], 2) AS p95_latency_ms,
  COUNT(*) as call_volume
FROM GRAPH_TABLE(
  `my-project.GRAPH_DATASET.agent_trace_graph`
  MATCH (src:Span)-[:ParentOf]->(dst:Span)
  COLUMNS (src.node_label AS source_id, dst.node_label AS target_id, dst.duration_ms)
)
GROUP BY 1, 2
ORDER BY p95_latency_ms DESC
LIMIT 10;
```

### 5.3 Efficiency: Token Usage by Sub-Agent Chain
Identify which high-level agents generate the most token-heavy downstream calls.

```sql
SELECT
  src.node_label AS root_agent,
  dst.node_label AS downstream_tool,
  dst.node_type AS tool_type,
  SUM(dst.input_tokens + dst.output_tokens) AS accumulated_tokens
FROM GRAPH_TABLE(
  `my-project.GRAPH_DATASET.agent_trace_graph`
  MATCH (src:Span)-[:ParentOf]->{1,10}(dst:Span)
  WHERE src.node_type = 'Agent'
  COLUMNS (src.node_label, dst.node_label, dst.node_type, dst.input_tokens, dst.output_tokens)
)
GROUP BY 1, 2, 3
ORDER BY accumulated_tokens DESC
LIMIT 10;
```

## 6. Pre-Aggregated Hourly Table (Performance Optimization)

For sub-second graph loading on time ranges >= 1 hour, the system uses a pre-aggregated hourly table (`agent_graph_hourly`) instead of the expensive live `GRAPH_TABLE` recursive traversal.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Scheduled Query (every 1 hour)                             │
│  ┌──────────────────┐      ┌──────────────────────────┐     │
│  │ GRAPH_TABLE       │ ──▶  │ agent_graph_hourly        │     │
│  │ (recursive, slow) │      │ (pre-aggregated, fast)   │     │
│  └──────────────────┘      └──────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  Flutter UI Query Routing                                   │
│                                                             │
│  timeRange >= 1h  ──▶  SELECT ... FROM agent_graph_hourly   │
│                        (GROUP BY + SUM, sub-second)         │
│                                                             │
│  timeRange < 1h   ──▶  SELECT ... FROM GRAPH_TABLE(...)     │
│                        (live recursive fallback, 1-3s)      │
│                        NOTE: UI clamps min to 1h currently  │
└─────────────────────────────────────────────────────────────┘
```

### Table Schema: `agent_graph_hourly`

| Column | Type | Description |
| :--- | :--- | :--- |
| `time_bucket` | TIMESTAMP | Hour-aligned bucket (PARTITION key) |
| `source_id` | STRING | Source node label (CLUSTER key) |
| `target_id` | STRING | Target node label (CLUSTER key) |
| `source_type` | STRING | Source node type (Agent, Tool, LLM) |
| `target_type` | STRING | Target node type |
| `call_count` | INT64 | Number of calls in this hour |
| `error_count` | INT64 | Number of errors in this hour |
| `edge_tokens` | INT64 | Total tokens on this edge |
| `input_tokens` | INT64 | Input tokens on this edge |
| `output_tokens` | INT64 | Output tokens on this edge |
| `total_cost` | FLOAT64 | Estimated USD cost |
| `sum_duration_ms` | FLOAT64 | Sum of durations (for avg calculation) |
| `max_p95_duration_ms` | FLOAT64 | P95 duration within this hour |
| `unique_sessions` | INT64 | Distinct sessions in this hour |
| `sample_error` | STRING | Sample error message |
| `node_*` | various | Target-node metrics (tokens, errors, cost) |
| `tool_call_count` | INT64 | Downstream tool calls from source |
| `llm_call_count` | INT64 | Downstream LLM calls from source |
| `session_ids` | ARRAY\<STRING\> | Session IDs for cross-bucket dedup |

### Setup

Run the setup script which creates the table and backfills 30 days:

```bash
./scripts/setup_agent_graph_bq.sh <project_id> <trace_dataset> [graph_dataset]
```

Then set up the scheduled query (printed by the script) in Cloud Console > BigQuery > Scheduled Queries.

### Performance Characteristics

| Time Range | Query Path | Expected Latency |
| :--- | :--- | :--- |
| 1h – 30d | Pre-aggregated table | < 1s |

> **Note**: The UI currently clamps all time ranges to a minimum of 1 hour, so the pre-aggregated path is always used. The live GRAPH_TABLE fallback exists in the repository layer for programmatic use.

### Metric Approximations

When aggregating across hourly buckets:
- **avg_duration_ms**: Weighted average via `SUM(sum_duration_ms) / SUM(call_count)`
- **p95_duration_ms**: Conservative upper bound via `MAX(max_p95_duration_ms)` across buckets
- **unique_sessions**: Approximated by `SUM(unique_sessions)` (may overcount across bucket boundaries)
- **error_rate_pct**: Recomputed as `SUM(error_count) / SUM(call_count) * 100`

## 7. Configuration in AutoSRE

To use your custom dataset:
1.  Open `lib/features/agent_graph/data/agent_graph_repository.dart`.
2.  Update the `kDefaultDataset` constant:
    ```dart
    const kDefaultDataset = 'your-project-id.your_dataset_name';
    ```
3.  Alternatively, the application can be configured to fetch the dataset path from an environment variable or user settings in future updates.

## 8. Mock Data for Testing

If you are running in **Guest Mode**, the backend (`sre_agent/api/routers/tools.py`) will redirect calls to a synthetic demo project `cymbal-shops-demo`. You do not need a real BigQuery setup for local demonstration.
