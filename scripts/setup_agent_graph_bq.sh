#!/bin/bash
set -e

# BigQuery Agent Graph Setup Script
# This automates the creation of the Materialized View and Property Graph
# required for the AutoSRE Agent Graph visualization.
#
# See docs/AGENT_GRAPH_SETUP.md for detailed architecture and schema verification.
#
# OTel GenAI Semantic Conventions Verification:
#   This script relies on the following OpenTelemetry attributes being present
#   on spans exported to Google Cloud Trace / BigQuery export:
#     - cloud.platform = "gcp.agent_engine"      (filters out non-agent traffic)
#     - service.name                             (differentiates backend services)
#     - gen_ai.operation.name                    (classified into LLM, Tool, Agent)
#     - gen_ai.agent.name / gen_ai.agent.description
#     - gen_ai.tool.name / gen_ai.tool.description
#     - gen_ai.response.model
#     - gen_ai.usage.input_tokens / gen_ai.usage.output_tokens
#
# BigQuery Dry-Run Testing:
#   To verify that these views and queries compile cleanly for your dataset,
#   you can run dry-run tests using the bq CLI natively:
#   bq query --use_legacy_sql=false --dry_run "SELECT * FROM \\\`$PROJECT_ID.${GRAPH_DATASET:-agent_graph}.agent_registry\\\`"
#   bq query --use_legacy_sql=false --dry_run "SELECT * FROM \\\`$PROJECT_ID.${GRAPH_DATASET:-agent_graph}.tool_registry\\\`"
#   bq query --use_legacy_sql=false --dry_run "SELECT * FROM \\\`$PROJECT_ID.${GRAPH_DATASET:-agent_graph}.agent_topology_edges\\\`"
#
# Usage: ./scripts/setup_agent_graph_bq.sh [project_id] [trace_dataset] [graph_dataset] [service_name]
# Sourcing .env if it exists
if [ -f .env ]; then
  # shellcheck source=.env
  source .env
fi

# Usage: ./scripts/setup_agent_graph_bq.sh [project_id] [trace_dataset] [graph_dataset] [service_name]
PROJECT_ID=${1:-${PROJECT_ID}}
TRACE_DATASET=${2:-${TRACE_DATASET:-traces}}
GRAPH_DATASET=${3:-${GRAPH_DATASET:-agent_graph}}
SERVICE_NAME=${4:-${SERVICE_NAME:-sre-agent}}

if [[ -z "$PROJECT_ID" ]]; then
  echo "Usage: $0 [project_id] [trace_dataset] [graph_dataset] [service_name]"
  echo ""
  echo "Arguments (optional if set in .env):"
  echo "  project_id:    The GCP Project ID where traces are stored (e.g. my-project)"
  echo "  trace_dataset: The dataset name containing the _AllSpans table (default: traces)"
  echo "  graph_dataset: The target dataset for the graph objects (default: agent_graph)"
  echo "  service_name:  The service name emitting traces (default: sre-agent)"
  echo ""
  echo "Example: $0 my-project traces agent_graph sre-agent"
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
bq rm -f -t "$PROJECT_ID:$GRAPH_DATASET.agent_trajectories" > /dev/null 2>&1 || true
bq rm -f -t "$PROJECT_ID:$GRAPH_DATASET.agent_span_payloads" > /dev/null 2>&1 || true

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
  status.message AS status_desc,
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
  -- NEW: Extract service.name for multi-agent filtering
  JSON_VALUE(resource.attributes, '\$.\"service.name\"') AS service_name,
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
WHERE JSON_VALUE(resource.attributes, '\$.\"cloud.platform\"') = 'gcp.agent_engine';
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
  ANY_VALUE(service_name) AS service_name,
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
  ANY_VALUE(service_name) AS service_name,
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
    status_code,
    start_time
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
    child.status_code,
    child.start_time
  FROM \`$PROJECT_ID.$GRAPH_DATASET.agent_spans_raw\` child
  JOIN span_tree parent ON child.parent_id = parent.span_id
)
SELECT
  trace_id,
  session_id,
  ANY_VALUE(service_name) AS service_name,
  ancestor_logical_id AS source_node_id,
  logical_node_id AS destination_node_id,
  COUNT(*) as edge_weight,
  SUM(duration_ms) as total_duration_ms,
  SUM(IFNULL(input_tokens, 0) + IFNULL(output_tokens, 0)) as total_tokens,
  SUM(IFNULL(input_tokens, 0)) as input_tokens,
  SUM(IFNULL(output_tokens, 0)) as output_tokens,
  COUNTIF(status_code = 'ERROR') as error_count,
  MIN(start_time) as start_time
FROM span_tree
WHERE node_type != 'Glue'
  AND ancestor_logical_id IS NOT NULL
  AND ancestor_logical_id != logical_node_id
GROUP BY 1, 2, 4, 5

UNION ALL

-- Synthetic User -> Root Agent edges
-- Root agents are those with no meaningful (non-Glue) ancestor
SELECT
  trace_id,
  session_id,
  ANY_VALUE(service_name) AS service_name,
  'User::session' AS source_node_id,
  logical_node_id AS destination_node_id,
  COUNT(*) as edge_weight,
  SUM(duration_ms) as total_duration_ms,
  SUM(IFNULL(input_tokens, 0) + IFNULL(output_tokens, 0)) as total_tokens,
  SUM(IFNULL(input_tokens, 0)) as input_tokens,
  SUM(IFNULL(output_tokens, 0)) as output_tokens,
  COUNTIF(status_code = 'ERROR') as error_count,
  MIN(start_time) as start_time
FROM span_tree
WHERE node_type = 'Agent'
  AND ancestor_logical_id IS NULL
GROUP BY 1, 2, 4, 5;
"
bq query --use_legacy_sql=false --project_id "$PROJECT_ID" "$EDGES_SQL"

# 3b. Create the Path Trajectories View (for Sankey diagrams)
# This view sequences meaningful spans chronologically within each trace_id,
# then self-joins to create step-to-step links for trajectory visualization.
echo "🔹 Cleaning up existing trajectory view..."
bq rm -f -t "$PROJECT_ID:$GRAPH_DATASET.agent_trajectories" > /dev/null 2>&1 || true

echo "🔹 Creating Path Trajectories View: agent_trajectories..."
TRAJECTORIES_SQL="
CREATE OR REPLACE VIEW \`$PROJECT_ID.$GRAPH_DATASET.agent_trajectories\` AS
WITH sequenced_steps AS (
  -- Sequence meaningful spans chronologically within each trace
  SELECT
    trace_id,
    session_id,
    service_name,
    span_id,
    node_type,
    node_label,
    logical_node_id,
    start_time,
    duration_ms,
    status_code,
    input_tokens,
    output_tokens,
    ROW_NUMBER() OVER(
      PARTITION BY trace_id
      ORDER BY start_time ASC
    ) AS step_sequence
  FROM \`$PROJECT_ID.$GRAPH_DATASET.agent_spans_raw\`
  WHERE node_type != 'Glue'
),
trajectory_links AS (
  -- Self-join to create chronological step-to-step links
  SELECT
    a.trace_id,
    a.session_id,
    a.service_name,
    a.logical_node_id AS source_node,
    a.node_type AS source_type,
    a.node_label AS source_label,
    b.logical_node_id AS target_node,
    b.node_type AS target_type,
    b.node_label AS target_label,
    a.step_sequence AS source_step,
    b.step_sequence AS target_step,
    a.duration_ms AS source_duration_ms,
    b.duration_ms AS target_duration_ms,
    a.status_code AS source_status,
    b.status_code AS target_status,
    COALESCE(a.input_tokens, 0) + COALESCE(a.output_tokens, 0) AS source_tokens,
    COALESCE(b.input_tokens, 0) + COALESCE(b.output_tokens, 0) AS target_tokens
  FROM sequenced_steps a
  JOIN sequenced_steps b
    ON a.trace_id = b.trace_id
    AND a.step_sequence + 1 = b.step_sequence
)
-- Aggregate across traces to get flow volumes
SELECT
  ANY_VALUE(service_name) AS service_name,
  source_node,
  source_type,
  source_label,
  target_node,
  target_type,
  target_label,
  COUNT(DISTINCT trace_id) AS trace_count,
  SUM(source_duration_ms) AS total_source_duration_ms,
  SUM(target_duration_ms) AS total_target_duration_ms,
  SUM(source_tokens) AS total_source_tokens,
  SUM(target_tokens) AS total_target_tokens,
  COUNTIF(source_status = 'ERROR' OR target_status = 'ERROR') AS error_transition_count
FROM trajectory_links
GROUP BY 2, 3, 4, 5, 6, 7;
"
bq query --use_legacy_sql=false --project_id "$PROJECT_ID" "$TRAJECTORIES_SQL"


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
  source_id STRING,
  target_id STRING,
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
  -- Downstream rollup (populated with direct values; full rollup computed at query time)
  downstream_total_tokens INT64,
  downstream_total_cost FLOAT64,
  downstream_tool_call_count INT64,
  downstream_llm_call_count INT64,
  -- Session tracking (stored as repeated for cross-bucket dedup)
  session_ids ARRAY<STRING>,
  -- Multi-agent grouping
  service_name STRING
)
PARTITION BY DATE(time_bucket)
CLUSTER BY service_name, source_id, target_id
OPTIONS (
  description = 'Pre-aggregated hourly agent graph data for sub-second UI queries'
);
"

bq query --use_legacy_sql=false --project_id "$PROJECT_ID" "$HOURLY_TABLE_SQL"

# 6. Backfill the hourly table with the last 30 days of data
echo "🔹 Backfilling hourly table (last 30 days)..."
BACKFILL_SQL="
INSERT INTO \`$PROJECT_ID.$GRAPH_DATASET.agent_graph_hourly\`
WITH RawEdges AS (
  SELECT
    e.trace_id, e.session_id,
    TIMESTAMP_TRUNC(n_dst.start_time, HOUR) as time_bucket,
    e.source_node_id as source_id, n_src.node_type as source_type,
    e.destination_node_id as target_id, n_dst.node_type as target_type,
    e.edge_weight as call_count,
    e.total_duration_ms,
    e.total_tokens,
    e.error_count as edge_error_count,
    n_dst.total_input_tokens as input_tokens,
    n_dst.total_output_tokens as output_tokens,
    n_dst.start_time
  FROM \`$PROJECT_ID.$GRAPH_DATASET.agent_topology_edges\` e
  JOIN \`$PROJECT_ID.$GRAPH_DATASET.agent_topology_nodes\` n_dst
    ON e.trace_id = n_dst.trace_id AND e.destination_node_id = n_dst.logical_node_id
  LEFT JOIN \`$PROJECT_ID.$GRAPH_DATASET.agent_topology_nodes\` n_src
    ON e.trace_id = n_src.trace_id AND e.source_node_id = n_src.logical_node_id
  WHERE n_dst.start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 720 HOUR)
),
CostPaths AS (
  SELECT re.*,
    COALESCE(input_tokens, 0) * CASE
      WHEN target_id LIKE '%flash%' THEN 0.00000015
      WHEN target_id LIKE '%2.5-pro%' THEN 0.00000125
      WHEN target_id LIKE '%1.5-pro%' THEN 0.00000125
      ELSE 0.0000005
    END
    + COALESCE(output_tokens, 0) * CASE
      WHEN target_id LIKE '%flash%' THEN 0.0000006
      WHEN target_id LIKE '%2.5-pro%' THEN 0.00001
      WHEN target_id LIKE '%1.5-pro%' THEN 0.000005
      ELSE 0.000002
    END AS span_cost
  FROM RawEdges re
)
SELECT
  time_bucket,
  ANY_VALUE(service_name) AS service_name,
  source_id, target_id, source_type, target_type,
  -- Edge metrics
  SUM(call_count) AS call_count,
  SUM(edge_error_count) AS error_count,
  SUM(total_tokens) AS edge_tokens,
  SUM(input_tokens) AS input_tokens,
  SUM(output_tokens) AS output_tokens,
  ROUND(SUM(span_cost), 6) AS total_cost,
  SUM(total_duration_ms) AS sum_duration_ms,
  ROUND(MAX(total_duration_ms), 2) AS max_p95_duration_ms,
  COUNT(DISTINCT session_id) AS unique_sessions,
  CAST(NULL AS STRING) AS sample_error,
  -- Target-node metrics
  SUM(total_tokens) AS node_total_tokens,
  SUM(input_tokens) AS node_input_tokens,
  SUM(output_tokens) AS node_output_tokens,
  SUM(edge_error_count) > 0 AS node_has_error,
  SUM(total_duration_ms) AS node_sum_duration_ms,
  ROUND(MAX(total_duration_ms), 2) AS node_max_p95_duration_ms,
  SUM(edge_error_count) AS node_error_count,
  SUM(call_count) AS node_call_count,
  ROUND(SUM(span_cost), 6) AS node_total_cost,
  target_id AS node_description,
  -- Subcall counts
  SUM(IF(target_type = 'Tool', call_count, 0)) AS tool_call_count,
  SUM(IF(target_type = 'LLM', call_count, 0)) AS llm_call_count,
  -- Downstream rollup (populated with direct values; full rollup computed at query time)
  SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)) AS downstream_total_tokens,
  ROUND(SUM(span_cost), 6) AS downstream_total_cost,
  SUM(IF(target_type = 'Tool', call_count, 0)) AS downstream_tool_call_count,
  SUM(IF(target_type = 'LLM', call_count, 0)) AS downstream_llm_call_count,
  -- Session IDs for cross-bucket dedup
  ARRAY_AGG(DISTINCT session_id IGNORE NULLS) AS session_ids
FROM CostPaths
GROUP BY time_bucket, service_name, source_id, target_id, source_type, target_type;
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
WITH RawEdges AS (
  SELECT
    e.trace_id, e.session_id,
    TIMESTAMP_TRUNC(n_dst.start_time, HOUR) as time_bucket,
    e.source_node_id as source_id, n_src.node_type as source_type,
    e.destination_node_id as target_id, n_dst.node_type as target_type,
    e.edge_weight as call_count,
    e.total_duration_ms,
    e.total_tokens,
    e.error_count as edge_error_count,
    n_dst.total_input_tokens as input_tokens,
    n_dst.total_output_tokens as output_tokens,
    n_dst.start_time
  FROM `<PROJECT_ID>.<GRAPH_DATASET>.agent_topology_edges` e
  JOIN `<PROJECT_ID>.<GRAPH_DATASET>.agent_topology_nodes` n_dst
    ON e.trace_id = n_dst.trace_id AND e.destination_node_id = n_dst.logical_node_id
  JOIN `<PROJECT_ID>.<GRAPH_DATASET>.agent_topology_nodes` n_src
    ON e.trace_id = n_src.trace_id AND e.source_node_id = n_src.logical_node_id
  WHERE n_dst.start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 2 HOUR)
    AND n_dst.start_time < TIMESTAMP_TRUNC(CURRENT_TIMESTAMP(), HOUR)
),
CostPaths AS (
  SELECT re.*,
    COALESCE(input_tokens, 0) * CASE
      WHEN target_id LIKE '%flash%' THEN 0.00000015
      WHEN target_id LIKE '%2.5-pro%' THEN 0.00000125
      WHEN target_id LIKE '%1.5-pro%' THEN 0.00000125
      ELSE 0.0000005
    END
    + COALESCE(output_tokens, 0) * CASE
      WHEN target_id LIKE '%flash%' THEN 0.0000006
      WHEN target_id LIKE '%2.5-pro%' THEN 0.00001
      WHEN target_id LIKE '%1.5-pro%' THEN 0.000005
      ELSE 0.000002
    END AS span_cost
  FROM RawEdges re
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
  ANY_VALUE(service_name) AS service_name,
  source_id, target_id, source_type, target_type,
  SUM(call_count) AS call_count,
  SUM(edge_error_count) AS error_count,
  SUM(total_tokens) AS edge_tokens,
  SUM(input_tokens) AS input_tokens,
  SUM(output_tokens) AS output_tokens,
  ROUND(SUM(span_cost), 6) AS total_cost,
  SUM(total_duration_ms) AS sum_duration_ms,
  ROUND(MAX(total_duration_ms), 2) AS max_p95_duration_ms,
  COUNT(DISTINCT session_id) AS unique_sessions,
  CAST(NULL AS STRING) AS sample_error,
  SUM(total_tokens) AS node_total_tokens,
  SUM(input_tokens) AS node_input_tokens,
  SUM(output_tokens) AS node_output_tokens,
  SUM(edge_error_count) > 0 AS node_has_error,
  SUM(total_duration_ms) AS node_sum_duration_ms,
  ROUND(MAX(total_duration_ms), 2) AS node_max_p95_duration_ms,
  SUM(edge_error_count) AS node_error_count,
  SUM(call_count) AS node_call_count,
  ROUND(SUM(span_cost), 6) AS node_total_cost,
  target_id AS node_description,
  SUM(IF(target_type = 'Tool', call_count, 0)) AS tool_call_count,
  SUM(IF(target_type = 'LLM', call_count, 0)) AS llm_call_count,
  -- Downstream rollup (populated with direct values; full rollup computed at query time)
  SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)) AS downstream_total_tokens,
  ROUND(SUM(span_cost), 6) AS downstream_total_cost,
  SUM(IF(target_type = 'Tool', call_count, 0)) AS downstream_tool_call_count,
  SUM(IF(target_type = 'LLM', call_count, 0)) AS downstream_llm_call_count,
  ARRAY_AGG(DISTINCT session_id IGNORE NULLS) AS session_ids
FROM NewPaths
GROUP BY time_bucket, service_name, source_id, target_id, source_type, target_type;
SCHEDULED_QUERY_EOF

# 8. Create Agent Registry
echo "🔹 Creating Agent Registry view..."
AGENT_REGISTRY_SQL="
CREATE OR REPLACE VIEW \`$PROJECT_ID.$GRAPH_DATASET.agent_registry\` AS
WITH ParsedAgents AS (
  SELECT
    trace_id,
    session_id,
    TIMESTAMP_TRUNC(start_time, HOUR) as time_bucket,
    service_name,
    logical_node_id,
    duration_ms,
    input_tokens,
    output_tokens,
    status_code,
    node_label,
    node_type
  FROM \`$PROJECT_ID.$GRAPH_DATASET.agent_spans_raw\`
  WHERE node_type = 'Agent'
)
SELECT
  time_bucket,
  service_name,
  logical_node_id AS agent_id,
  ANY_VALUE(node_label) AS agent_name,
  COUNT(DISTINCT session_id) AS total_sessions,
  COUNT(*) AS total_turns,
  SUM(input_tokens) AS total_input_tokens,
  SUM(output_tokens) AS total_output_tokens,
  COUNTIF(status_code = 'ERROR') AS error_count,
  APPROX_QUANTILES(duration_ms, 100)[OFFSET(50)] AS p50_duration_ms,
  APPROX_QUANTILES(duration_ms, 100)[OFFSET(95)] AS p95_duration_ms
FROM ParsedAgents
GROUP BY time_bucket, service_name, agent_id;
"
bq query --use_legacy_sql=false --project_id "$PROJECT_ID" "$AGENT_REGISTRY_SQL"


# 9. Create Tool Registry
echo "🔹 Creating Tool Registry view..."
TOOL_REGISTRY_SQL="
CREATE OR REPLACE VIEW \`$PROJECT_ID.$GRAPH_DATASET.tool_registry\` AS
WITH ParsedTools AS (
  SELECT
    trace_id,
    session_id,
    TIMESTAMP_TRUNC(start_time, HOUR) as time_bucket,
    service_name,
    logical_node_id,
    duration_ms,
    status_code,
    node_label,
    node_type
  FROM \`$PROJECT_ID.$GRAPH_DATASET.agent_spans_raw\`
  WHERE node_type = 'Tool'
)
SELECT
  time_bucket,
  service_name,
  logical_node_id AS tool_id,
  ANY_VALUE(node_label) AS tool_name,
  COUNT(*) AS execution_count,
  COUNTIF(status_code = 'ERROR') AS error_count,
  SAFE_DIVIDE(COUNTIF(status_code = 'ERROR'), COUNT(*)) AS error_rate,
  AVG(duration_ms) AS avg_duration_ms,
  APPROX_QUANTILES(duration_ms, 100)[OFFSET(95)] AS p95_duration_ms
FROM ParsedTools
GROUP BY time_bucket, service_name, tool_id;
"
bq query --use_legacy_sql=false --project_id "$PROJECT_ID" "$TOOL_REGISTRY_SQL"

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
echo ""
echo "Registries Created:"
echo "  - $PROJECT_ID.$GRAPH_DATASET.agent_registry"
echo "  - $PROJECT_ID.$GRAPH_DATASET.tool_registry"
echo "---------------------------------------------------"
