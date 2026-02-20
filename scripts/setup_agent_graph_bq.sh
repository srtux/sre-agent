#!/bin/bash
set -e

# BigQuery Agent Graph Setup Script
# This automates the creation of the Materialized View and Property Graph
# required for the AutoSRE Agent Graph visualization.
#
# See docs/AGENT_GRAPH_SETUP.md for detailed architecture and schema verification.

# Usage: ./scripts/setup_agent_graph_bq.sh <project_id> <trace_dataset> [graph_dataset]
# Sourcing .env if it exists
if [ -f .env ]; then
  # shellcheck source=.env
  source .env
fi

# Usage: ./scripts/setup_agent_graph_bq.sh [project_id] [trace_dataset] [graph_dataset]
PROJECT_ID=${1:-${PROJECT_ID}}
# If TRACE_DATASET is not set, try to default to 'traces' if PROJECT_ID is set
TRACE_DATASET=${2:-${TRACE_DATASET:-traces}}
GRAPH_DATASET=${3:-${GRAPH_DATASET:-agent_graph}}

if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: $0 [project_id] [trace_dataset] [graph_dataset]"
  echo ""
  echo "Arguments (optional if set in .env):"
  echo "  project_id:    The GCP Project ID where traces are stored (e.g. my-sre-project)"
  echo "  trace_dataset: The dataset name containing the _AllSpans table (default: traces)"
  echo "  graph_dataset: The target dataset for the graph objects (default: agent_graph)"
  echo ""
  echo "Example: $0 summitt-gcp traces agent_graph"
  exit 1
fi

echo "🚀 Starting BigQuery Agent Graph Setup..."
echo "📍 Project: $PROJECT_ID"
echo "📊 Source:  $TRACE_DATASET._AllSpans"
echo "🕸️  Target:  $GRAPH_DATASET.agent_topology_graph"

# 1. Create target dataset if it doesn't exist
if ! bq ls --project_id "$PROJECT_ID" "$GRAPH_DATASET" > /dev/null 2>&1; then
  echo "🔹 Creating target dataset: $PROJECT_ID:$GRAPH_DATASET..."
  bq mk --project_id "$PROJECT_ID" --location="US" "$GRAPH_DATASET"
else
  echo "✅ Dataset $GRAPH_DATASET already exists."
fi

# 2. Cleanup existing objects to ensure a fresh start
echo "🔹 Cleaning up existing objects (if any)..."

# Delete Property Graph first (as it depends on the table/view)
bq query --use_legacy_sql=false --project_id "$PROJECT_ID" \
  "DROP PROPERTY GRAPH IF EXISTS \`$PROJECT_ID.$GRAPH_DATASET.agent_topology_graph\`" || true
bq query --use_legacy_sql=false --project_id "$PROJECT_ID" \
  "DROP PROPERTY GRAPH IF EXISTS \`$PROJECT_ID.$GRAPH_DATASET.agent_trace_graph\`" || true

# Drop the views that depend on the raw table
bq rm -f -t "$PROJECT_ID:$GRAPH_DATASET.agent_topology_edges" > /dev/null 2>&1 || true
bq rm -f -t "$PROJECT_ID:$GRAPH_DATASET.agent_topology_nodes" > /dev/null 2>&1 || true

# Try deleting as both Materialized View and Table
bq rm -f -m "$PROJECT_ID:$GRAPH_DATASET.agent_spans_raw" > /dev/null 2>&1 || true
bq rm -f -t "$PROJECT_ID:$GRAPH_DATASET.agent_spans_raw" > /dev/null 2>&1 || true


# 1. Base Materialized View (Your existing view with a Logical Node ID added)
echo "🔹 Creating Materialized View: agent_spans_raw..."
MV_SQL="
CREATE MATERIALIZED VIEW \`$PROJECT_ID.$GRAPH_DATASET.agent_spans_raw\`
CLUSTER BY trace_id, session_id, node_label
OPTIONS (
  enable_refresh = true,
  refresh_interval_minutes = 5,
  max_staleness = INTERVAL "30" MINUTE,
  allow_non_incremental_definition = true
)
AS
SELECT
  span_id,
  parent_span_id AS parent_id,
  trace_id,
  start_time,
  JSON_VALUE(attributes, '\$.\"gen_ai.conversation.id\"') AS session_id,
  CAST(duration_nano AS FLOAT64) / 1000000.0 AS duration_ms,
  CASE status.code
    WHEN 0 THEN 'UNSET'
    WHEN 1 THEN 'OK'
    WHEN 2 THEN 'ERROR'
    ELSE CAST(status.code AS STRING)
  END AS status_code,
  SAFE_CAST(JSON_VALUE(attributes, '\$.\"gen_ai.usage.input_tokens\"') AS INT64) AS input_tokens,
  SAFE_CAST(JSON_VALUE(attributes, '\$.\"gen_ai.usage.output_tokens\"') AS INT64) AS output_tokens,
  -- Node Classification
  CASE
    WHEN JSON_VALUE(attributes, '\$.\"gen_ai.operation.name\"') = 'invoke_agent' THEN 'Agent'
    WHEN JSON_VALUE(attributes, '\$.\"gen_ai.operation.name\"') = 'execute_tool' THEN 'Tool'
    WHEN JSON_VALUE(attributes, '\$.\"gen_ai.operation.name\"') = 'generate_content' THEN 'LLM'
    ELSE 'Glue'
  END AS node_type,
  COALESCE(
    JSON_VALUE(attributes, '\$.\"gen_ai.agent.name\"'),
    JSON_VALUE(attributes, '\$.\"gen_ai.tool.name\"'),
    JSON_VALUE(attributes, '\$.\"gen_ai.response.model\"'),
    name
  ) AS node_label,
  -- NEW: Create a unique logical identifier for the topology
  CONCAT(
    CASE
      WHEN JSON_VALUE(attributes, '\$.\"gen_ai.operation.name\"') = 'invoke_agent' THEN 'Agent'
      WHEN JSON_VALUE(attributes, '\$.\"gen_ai.operation.name\"') = 'execute_tool' THEN 'Tool'
      WHEN JSON_VALUE(attributes, '\$.\"gen_ai.operation.name\"') = 'generate_content' THEN 'LLM'
      ELSE 'Glue'
    END,
    '::',
    COALESCE(JSON_VALUE(attributes, '\$.\"gen_ai.agent.name\"'), JSON_VALUE(attributes, '\$.\"gen_ai.tool.name\"'), JSON_VALUE(attributes, '\$.\"gen_ai.response.model\"'), name)
  ) AS logical_node_id
FROM \`$PROJECT_ID.$TRACE_DATASET._AllSpans\`
WHERE JSON_VALUE(resource.attributes, '\$.\"service.name\"') = 'sre-agent';
"
bq query --use_legacy_sql=false --project_id "$PROJECT_ID" "$MV_SQL"


# 2. Create the Topological Nodes View
# This pre-aggregates metrics per component per trace so the UI can easily colorize them (e.g., Red for errors).
# Includes a synthetic 'User::session' node so the graph always has a visible entry point.
echo "🔹 Creating Topological Nodes View (with User entry node)..."
NODES_SQL="
CREATE OR REPLACE VIEW \`$PROJECT_ID.$GRAPH_DATASET.agent_topology_nodes\` AS
-- Real agent/tool/LLM nodes from spans
SELECT
  trace_id,
  session_id,
  logical_node_id,
  ANY_VALUE(node_type) AS node_type,
  ANY_VALUE(node_label) AS node_label,
  COUNT(span_id) AS execution_count,
  SUM(duration_ms) AS total_duration_ms,
  SUM(input_tokens) AS total_input_tokens,
  SUM(output_tokens) AS total_output_tokens,
  COUNTIF(status_code = 'ERROR') AS error_count,
  MIN(start_time) AS start_time
FROM \`$PROJECT_ID.$GRAPH_DATASET.agent_spans_raw\`
WHERE node_type != 'Glue'
GROUP BY 1, 2, 3

UNION ALL

-- Synthetic User node: one per (trace, session), aggregating all root agent metrics
SELECT
  trace_id,
  session_id,
  'User::session' AS logical_node_id,
  'User' AS node_type,
  'session' AS node_label,
  COUNT(DISTINCT span_id) AS execution_count,
  SUM(duration_ms) AS total_duration_ms,
  SUM(input_tokens) AS total_input_tokens,
  SUM(output_tokens) AS total_output_tokens,
  COUNTIF(status_code = 'ERROR') AS error_count,
  MIN(start_time) AS start_time
FROM \`$PROJECT_ID.$GRAPH_DATASET.agent_spans_raw\`
WHERE node_type = 'Agent'
  AND (parent_id IS NULL OR parent_id NOT IN (
    SELECT span_id FROM \`$PROJECT_ID.$GRAPH_DATASET.agent_spans_raw\`
    WHERE node_type != 'Glue'
  ))
GROUP BY 1, 2;
"
bq query --use_legacy_sql=false --project_id "$PROJECT_ID" "$NODES_SQL"


# 3. Create the Topological Edges View (The Magic Bridge)
# This uses a Recursive CTE to traverse up the span tree and skip "Glue" spans,
# ensuring your Tools and LLMs connect directly to the Agent that invoked them.
echo "🔹 Creating Topological Edges View (Skipping Glue spans)..."
EDGES_SQL="
CREATE OR REPLACE VIEW \`$PROJECT_ID.$GRAPH_DATASET.agent_topology_edges\` AS
WITH RECURSIVE span_tree AS (
  -- Base case: Roots or spans where we can't find a parent in this dataset
  SELECT
    span_id,
    trace_id,
    session_id,
    node_type,
    logical_node_id,
    CAST(NULL AS STRING) AS ancestor_logical_id,
    duration_ms,
    input_tokens,
    output_tokens,
    status_code
  FROM \`$PROJECT_ID.$GRAPH_DATASET.agent_spans_raw\`
  WHERE parent_id IS NULL OR parent_id NOT IN (SELECT span_id FROM \`$PROJECT_ID.$GRAPH_DATASET.agent_spans_raw\`)

  UNION ALL

  -- Recursive step: Traverse down to children
  SELECT
    child.span_id,
    child.trace_id,
    child.session_id,
    child.node_type,
    child.logical_node_id,
    -- If the parent was meaningful, it becomes the ancestor for the child.
    -- If the parent was Glue, we pass down the inherited ancestor from higher up.
    IF(parent.node_type != 'Glue', parent.logical_node_id, parent.ancestor_logical_id),
    child.duration_ms,
    child.input_tokens,
    child.output_tokens,
    child.status_code
  FROM \`$PROJECT_ID.$GRAPH_DATASET.agent_spans_raw\` child
  JOIN span_tree parent ON child.parent_id = parent.span_id
)
SELECT
  trace_id,
  session_id,
  ancestor_logical_id AS source_node_id,
  logical_node_id AS destination_node_id,
  COUNT(*) as edge_weight,
  SUM(duration_ms) as total_duration_ms,
  SUM(IFNULL(input_tokens, 0) + IFNULL(output_tokens, 0)) as total_tokens,
  SUM(IFNULL(input_tokens, 0)) as input_tokens,
  SUM(IFNULL(output_tokens, 0)) as output_tokens,
  COUNTIF(status_code = 'ERROR') as error_count
FROM span_tree
WHERE node_type != 'Glue'
  AND ancestor_logical_id IS NOT NULL
  AND ancestor_logical_id != logical_node_id
GROUP BY 1, 2, 3, 4

UNION ALL

-- Synthetic User -> Root Agent edges
-- Root agents are those with no meaningful (non-Glue) ancestor
SELECT
  trace_id,
  session_id,
  'User::session' AS source_node_id,
  logical_node_id AS destination_node_id,
  COUNT(*) as edge_weight,
  SUM(duration_ms) as total_duration_ms,
  SUM(IFNULL(input_tokens, 0) + IFNULL(output_tokens, 0)) as total_tokens,
  SUM(IFNULL(input_tokens, 0)) as input_tokens,
  SUM(IFNULL(output_tokens, 0)) as output_tokens,
  COUNTIF(status_code = 'ERROR') as error_count
FROM span_tree
WHERE node_type = 'Agent'
  AND ancestor_logical_id IS NULL
GROUP BY 1, 2, 3, 4;
"
bq query --use_legacy_sql=false --project_id "$PROJECT_ID" "$EDGES_SQL"


# 4. Create the Logical Property Graph
echo "🔹 Creating Logical Property Graph: agent_topology_graph..."
GRAPH_SQL="
CREATE OR REPLACE PROPERTY GRAPH \`$PROJECT_ID.$GRAPH_DATASET.agent_topology_graph\`
  NODE TABLES (
    \`$PROJECT_ID.$GRAPH_DATASET.agent_topology_nodes\` AS Node
      KEY (trace_id, logical_node_id)
      LABEL Component
      PROPERTIES ALL COLUMNS
  )
  EDGE TABLES (
    \`$PROJECT_ID.$GRAPH_DATASET.agent_topology_edges\` AS Interaction
      KEY (trace_id, source_node_id, destination_node_id)
      SOURCE KEY (trace_id, source_node_id) REFERENCES Node (trace_id, logical_node_id)
      DESTINATION KEY (trace_id, destination_node_id) REFERENCES Node (trace_id, logical_node_id)
      LABEL Interaction
      PROPERTIES ALL COLUMNS
  );
"
bq query --use_legacy_sql=false --project_id "$PROJECT_ID" "$GRAPH_SQL"

# 5. Create pre-aggregated hourly table
# This table stores hourly pre-computed edge and node aggregations,
# avoiding the expensive GRAPH_TABLE recursive traversal at query time.
echo "🔹 Creating pre-aggregated hourly table: agent_graph_hourly..."
bq rm -f -t "$PROJECT_ID:$GRAPH_DATASET.agent_graph_hourly" > /dev/null 2>&1 || true

HOURLY_TABLE_SQL="
CREATE TABLE \`$PROJECT_ID.$GRAPH_DATASET.agent_graph_hourly\`
(
  -- Bucketing
  time_bucket TIMESTAMP NOT NULL,
  -- Edge identity
  source_id STRING NOT NULL,
  target_id STRING NOT NULL,
  source_type STRING,
  target_type STRING,
  -- Edge metrics (pre-aggregated per hour)
  call_count INT64,
  error_count INT64,
  edge_tokens INT64,
  input_tokens INT64,
  output_tokens INT64,
  total_cost FLOAT64,
  sum_duration_ms FLOAT64,
  max_p95_duration_ms FLOAT64,
  unique_sessions INT64,
  sample_error STRING,
  -- Target-node metrics (pre-aggregated per hour for the dst span)
  node_total_tokens INT64,
  node_input_tokens INT64,
  node_output_tokens INT64,
  node_has_error BOOL,
  node_sum_duration_ms FLOAT64,
  node_max_p95_duration_ms FLOAT64,
  node_error_count INT64,
  node_call_count INT64,
  node_total_cost FLOAT64,
  node_description STRING,
  -- Source-node subcall counts
  tool_call_count INT64,
  llm_call_count INT64,
  -- Hierarchical rollup metrics (downstream totals, computed at query time)
  downstream_total_tokens INT64,
  downstream_total_cost FLOAT64,
  downstream_tool_call_count INT64,
  downstream_llm_call_count INT64,
  -- Session tracking (stored as repeated for cross-bucket dedup)
  session_ids ARRAY<STRING>
)
PARTITION BY DATE(time_bucket)
CLUSTER BY source_id, target_id
OPTIONS (
  description = 'Pre-aggregated hourly agent graph data for sub-second UI queries'
);
"

bq query --use_legacy_sql=false --project_id "$PROJECT_ID" "$HOURLY_TABLE_SQL"

# 6. Backfill the hourly table with the last 30 days of data
echo "🔹 Backfilling hourly table (last 30 days)..."
BACKFILL_SQL="
INSERT INTO \`$PROJECT_ID.$GRAPH_DATASET.agent_graph_hourly\`
WITH GraphPaths AS (
  SELECT * FROM GRAPH_TABLE(
    \`$PROJECT_ID.$GRAPH_DATASET.agent_trace_graph\`
    MATCH (src:Span)-[:ParentOf]->{1,5}(dst:Span)
    WHERE src.node_type != 'Glue' AND dst.node_type != 'Glue' AND src.node_label != dst.node_label
      AND src.start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 720 HOUR)
    COLUMNS (
      src.node_label AS source_id, src.node_type AS source_type,
      dst.node_label AS target_id, dst.node_type AS target_type,
      dst.trace_id AS trace_id, dst.session_id AS session_id,
      dst.duration_ms AS duration_ms,
      dst.input_tokens AS input_tokens, dst.output_tokens AS output_tokens,
      dst.status_code AS status_code, dst.error_type AS error_type,
      dst.agent_description AS agent_description, dst.tool_description AS tool_description,
      dst.response_model AS response_model,
      dst.start_time AS start_time
    )
  )
),
CostPaths AS (
  SELECT gp.*,
    TIMESTAMP_TRUNC(start_time, HOUR) AS time_bucket,
    COALESCE(input_tokens, 0) * CASE
      WHEN response_model LIKE '%flash%' THEN 0.00000015
      WHEN response_model LIKE '%2.5-pro%' THEN 0.00000125
      WHEN response_model LIKE '%1.5-pro%' THEN 0.00000125
      ELSE 0.0000005
    END
    + COALESCE(output_tokens, 0) * CASE
      WHEN response_model LIKE '%flash%' THEN 0.0000006
      WHEN response_model LIKE '%2.5-pro%' THEN 0.00001
      WHEN response_model LIKE '%1.5-pro%' THEN 0.000005
      ELSE 0.000002
    END AS span_cost
  FROM GraphPaths gp
)
SELECT
  time_bucket,
  source_id, target_id, source_type, target_type,
  -- Edge metrics
  COUNT(*) AS call_count,
  COUNTIF(status_code = 2) AS error_count,
  SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)) AS edge_tokens,
  SUM(COALESCE(input_tokens, 0)) AS input_tokens,
  SUM(COALESCE(output_tokens, 0)) AS output_tokens,
  ROUND(SUM(span_cost), 6) AS total_cost,
  SUM(duration_ms) AS sum_duration_ms,
  ROUND(APPROX_QUANTILES(IFNULL(duration_ms, 0), 100)[OFFSET(95)], 2) AS max_p95_duration_ms,
  COUNT(DISTINCT session_id) AS unique_sessions,
  ANY_VALUE(error_type) AS sample_error,
  -- Target-node metrics
  SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)) AS node_total_tokens,
  SUM(COALESCE(input_tokens, 0)) AS node_input_tokens,
  SUM(COALESCE(output_tokens, 0)) AS node_output_tokens,
  COUNTIF(status_code = 2) > 0 AS node_has_error,
  SUM(duration_ms) AS node_sum_duration_ms,
  ROUND(APPROX_QUANTILES(IFNULL(duration_ms, 0), 100)[OFFSET(95)], 2) AS node_max_p95_duration_ms,
  COUNTIF(status_code = 2) AS node_error_count,
  COUNT(*) AS node_call_count,
  ROUND(SUM(span_cost), 6) AS node_total_cost,
  ANY_VALUE(COALESCE(agent_description, tool_description)) AS node_description,
  -- Subcall counts
  COUNTIF(target_type = 'Tool') AS tool_call_count,
  COUNTIF(target_type = 'LLM') AS llm_call_count,
  -- Downstream rollup (populated with direct values; full rollup computed at query time)
  SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)) AS downstream_total_tokens,
  ROUND(SUM(span_cost), 6) AS downstream_total_cost,
  COUNTIF(target_type = 'Tool') AS downstream_tool_call_count,
  COUNTIF(target_type = 'LLM') AS downstream_llm_call_count,
  -- Session IDs for cross-bucket dedup
  ARRAY_AGG(DISTINCT session_id) AS session_ids
FROM CostPaths
GROUP BY time_bucket, source_id, target_id, source_type, target_type;
"

bq query --use_legacy_sql=false --project_id "$PROJECT_ID" "$BACKFILL_SQL"

# 7. Create scheduled query for hourly incremental updates
echo "🔹 Creating scheduled query for hourly updates..."
echo "NOTE: Run the following command to create a scheduled query via bq CLI or Cloud Console:"
echo ""
cat << 'SCHEDULED_QUERY_EOF'
-- Scheduled Query: agent_graph_hourly_refresh
-- Schedule: Every 1 hour
-- Destination: agent_graph_hourly (WRITE_APPEND)
--
-- Create via Cloud Console > BigQuery > Scheduled Queries, or use:
--   bq mk --transfer_config \
--     --project_id=<PROJECT_ID> \
--     --target_dataset=<GRAPH_DATASET> \
--     --display_name="Agent Graph Hourly Refresh" \
--     --schedule="every 1 hours" \
--     --data_source=scheduled_query \
--     --params='{"query":"<SQL>","destination_table_name_template":"agent_graph_hourly","write_disposition":"WRITE_APPEND"}'

INSERT INTO `<PROJECT_ID>.<GRAPH_DATASET>.agent_graph_hourly`
WITH GraphPaths AS (
  SELECT * FROM GRAPH_TABLE(
    `<PROJECT_ID>.<GRAPH_DATASET>.agent_trace_graph`
    MATCH (src:Span)-[:ParentOf]->{1,5}(dst:Span)
    WHERE src.node_type != 'Glue' AND dst.node_type != 'Glue' AND src.node_label != dst.node_label
      AND src.start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 HOUR)
      AND src.start_time < TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), HOUR)
    COLUMNS (
      src.node_label AS source_id, src.node_type AS source_type,
      dst.node_label AS target_id, dst.node_type AS target_type,
      dst.trace_id AS trace_id, dst.session_id AS session_id,
      dst.duration_ms AS duration_ms,
      dst.input_tokens AS input_tokens, dst.output_tokens AS output_tokens,
      dst.status_code AS status_code, dst.error_type AS error_type,
      dst.agent_description AS agent_description, dst.tool_description AS tool_description,
      dst.response_model AS response_model,
      dst.start_time AS start_time
    )
  )
),
CostPaths AS (
  SELECT gp.*,
    TIMESTAMP_TRUNC(start_time, HOUR) AS time_bucket,
    COALESCE(input_tokens, 0) * CASE
      WHEN response_model LIKE '%flash%' THEN 0.00000015
      WHEN response_model LIKE '%2.5-pro%' THEN 0.00000125
      WHEN response_model LIKE '%1.5-pro%' THEN 0.00000125
      ELSE 0.0000005
    END
    + COALESCE(output_tokens, 0) * CASE
      WHEN response_model LIKE '%flash%' THEN 0.0000006
      WHEN response_model LIKE '%2.5-pro%' THEN 0.00001
      WHEN response_model LIKE '%1.5-pro%' THEN 0.000005
      ELSE 0.000002
    END AS span_cost
  FROM GraphPaths gp
),
-- Deduplicate: skip buckets that were already processed
ExistingBuckets AS (
  SELECT DISTINCT time_bucket FROM `<PROJECT_ID>.<GRAPH_DATASET>.agent_graph_hourly`
  WHERE time_bucket >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 HOUR)
),
NewPaths AS (
  SELECT cp.* FROM CostPaths cp
  LEFT JOIN ExistingBuckets eb ON cp.time_bucket = eb.time_bucket
  WHERE eb.time_bucket IS NULL
)
SELECT
  time_bucket,
  source_id, target_id, source_type, target_type,
  COUNT(*) AS call_count,
  COUNTIF(status_code = 2) AS error_count,
  SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)) AS edge_tokens,
  SUM(COALESCE(input_tokens, 0)) AS input_tokens,
  SUM(COALESCE(output_tokens, 0)) AS output_tokens,
  ROUND(SUM(span_cost), 6) AS total_cost,
  SUM(duration_ms) AS sum_duration_ms,
  ROUND(APPROX_QUANTILES(IFNULL(duration_ms, 0), 100)[OFFSET(95)], 2) AS max_p95_duration_ms,
  COUNT(DISTINCT session_id) AS unique_sessions,
  ANY_VALUE(error_type) AS sample_error,
  SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)) AS node_total_tokens,
  SUM(COALESCE(input_tokens, 0)) AS node_input_tokens,
  SUM(COALESCE(output_tokens, 0)) AS node_output_tokens,
  COUNTIF(status_code = 2) > 0 AS node_has_error,
  SUM(duration_ms) AS node_sum_duration_ms,
  ROUND(APPROX_QUANTILES(IFNULL(duration_ms, 0), 100)[OFFSET(95)], 2) AS node_max_p95_duration_ms,
  COUNTIF(status_code = 2) AS node_error_count,
  COUNT(*) AS node_call_count,
  ROUND(SUM(span_cost), 6) AS node_total_cost,
  ANY_VALUE(COALESCE(agent_description, tool_description)) AS node_description,
  COUNTIF(target_type = 'Tool') AS tool_call_count,
  COUNTIF(target_type = 'LLM') AS llm_call_count,
  -- Downstream rollup (populated with direct values; full rollup computed at query time)
  SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)) AS downstream_total_tokens,
  ROUND(SUM(span_cost), 6) AS downstream_total_cost,
  COUNTIF(target_type = 'Tool') AS downstream_tool_call_count,
  COUNTIF(target_type = 'LLM') AS downstream_llm_call_count,
  ARRAY_AGG(DISTINCT session_id) AS session_ids
FROM NewPaths
GROUP BY time_bucket, source_id, target_id, source_type, target_type;
SCHEDULED_QUERY_EOF

echo "---------------------------------------------------"
echo "✅ Setup Successful!"
echo "---------------------------------------------------"
echo "You can now visualize your agent topology in AutoSRE."
echo "Use dataset path: $PROJECT_ID.$GRAPH_DATASET"
echo ""
echo "Pre-aggregation:"
echo "  Table: $PROJECT_ID.$GRAPH_DATASET.agent_graph_hourly"
echo "  Backfilled with last 30 days of data."
echo "  Set up the scheduled query above for hourly incremental updates."
echo "---------------------------------------------------"
