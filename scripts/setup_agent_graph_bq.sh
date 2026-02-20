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
echo "🔹 Creating Topological Nodes View..."
NODES_SQL="
CREATE OR REPLACE VIEW \`$PROJECT_ID.$GRAPH_DATASET.agent_topology_nodes\` AS
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
GROUP BY 1, 2, 3;
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
  COUNTIF(status_code = 'ERROR') as error_count
FROM span_tree
WHERE node_type != 'Glue'
  AND ancestor_logical_id IS NOT NULL
  AND ancestor_logical_id != logical_node_id
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


echo "---------------------------------------------------"
echo "✅ Setup Successful!"
echo "---------------------------------------------------"
echo "You can now visualize your agent topology in AutoSRE."
echo "Use dataset path: $PROJECT_ID.$GRAPH_DATASET"
echo "---------------------------------------------------"
