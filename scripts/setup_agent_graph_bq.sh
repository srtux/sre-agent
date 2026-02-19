#!/bin/bash
set -e

# BigQuery Agent Graph Setup Script
# This automates the creation of the Materialized View and Property Graph
# required for the AutoSRE Agent Graph visualization.

# Usage: ./scripts/setup_agent_graph_bq.sh <project_id> <trace_dataset> [graph_dataset]
PROJECT_ID=$1
TRACE_DATASET=$2
GRAPH_DATASET=${3:-agent_graph}

if [[ -z "$PROJECT_ID" || -z "$TRACE_DATASET" ]]; then
  echo "Usage: $0 <project_id> <trace_dataset> [graph_dataset]"
  echo ""
  echo "Arguments:"
  echo "  project_id:    The GCP Project ID where traces are stored (e.g. my-sre-project)"
  echo "  trace_dataset: The dataset name containing the _AllSpans table (e.g. traces)"
  echo "  graph_dataset: (Optional) The target dataset for the graph objects. Defaults to 'agent_graph'."
  echo ""
  echo "Example: $0 summitt-gcp traces agent_graph"
  exit 1
fi

echo "🚀 Starting BigQuery Agent Graph Setup..."
echo "📍 Project: $PROJECT_ID"
echo "📊 Source:  $TRACE_DATASET._AllSpans"
echo "🕸️  Target:  $GRAPH_DATASET.agent_trace_graph"

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
  "DROP PROPERTY GRAPH IF EXISTS \`$PROJECT_ID.$GRAPH_DATASET.agent_trace_graph\`" || true

# Try deleting as both Materialized View and Table
bq rm -f -m "$PROJECT_ID:$GRAPH_DATASET.agent_spans_raw" > /dev/null 2>&1 || true
bq rm -f -t "$PROJECT_ID:$GRAPH_DATASET.agent_spans_raw" > /dev/null 2>&1 || true

# 3. Create Materialized View
# We use allow_non_incremental_definition to support JSON parsing and complex keys
echo "🔹 Creating Materialized View: agent_spans_raw..."
MV_SQL="
CREATE MATERIALIZED VIEW \`$PROJECT_ID.$GRAPH_DATASET.agent_spans_raw\`
CLUSTER BY trace_id, session_id, node_label
OPTIONS (
  enable_refresh = true,
  refresh_interval_minutes = 60,
  max_staleness = INTERVAL '1' HOUR,
  allow_non_incremental_definition = true
)
AS
SELECT
  span_id,
  parent_span_id AS parent_id,
  trace_id,
  start_time,
  -- Grouping IDs
  JSON_VALUE(attributes, '\$.\"gen_ai.conversation.id\"') AS session_id,
  JSON_VALUE(resource.attributes, '\$.\"gcp.project_id\"') AS project_id,
  -- Performance
  CAST(duration_nano AS FLOAT64) / 1000000.0 AS duration_ms,
  status.code AS status_code,
  JSON_VALUE(attributes, '\$.\"error.type\"') AS error_type,
  -- GenAI Metadata
  SAFE_CAST(JSON_VALUE(attributes, '\$.\"gen_ai.usage.input_tokens\"') AS INT64) AS input_tokens,
  SAFE_CAST(JSON_VALUE(attributes, '\$.\"gen_ai.usage.output_tokens\"') AS INT64) AS output_tokens,
  JSON_VALUE(attributes, '\$.\"gen_ai.request.model\"') AS request_model,
  JSON_VALUE(attributes, '\$.\"gen_ai.response.model\"') AS response_model,
  -- UI Rich Metadata
  JSON_VALUE(attributes, '\$.\"gen_ai.agent.description\"') AS agent_description,
  JSON_VALUE(attributes, '\$.\"gen_ai.tool.description\"') AS tool_description,
  -- Node Classification
  CASE
    WHEN JSON_VALUE(attributes, '\$.\"gen_ai.operation.name\"') = 'invoke_agent' THEN 'Agent'
    WHEN JSON_VALUE(attributes, '\$.\"gen_ai.operation.name\"') = 'execute_tool' THEN 'Tool'
    WHEN JSON_VALUE(attributes, '\$.\"gen_ai.operation.name\"') = 'generate_content' THEN 'LLM'
    ELSE 'Glue'
  END AS node_type,
  -- Display Label
  COALESCE(
    JSON_VALUE(attributes, '\$.\"gen_ai.agent.name\"'),
    JSON_VALUE(attributes, '\$.\"gen_ai.tool.name\"'),
    JSON_VALUE(attributes, '\$.\"gen_ai.response.model\"'),
    name
  ) AS node_label
FROM \`$PROJECT_ID.$TRACE_DATASET._AllSpans\`
WHERE JSON_VALUE(resource.attributes, '\$.\"service.name\"') = 'sre-agent';
"

bq query --use_legacy_sql=false --project_id "$PROJECT_ID" "$MV_SQL"

# 4. Create Property Graph
echo "🔹 Creating Property Graph: agent_trace_graph..."
GRAPH_SQL="
CREATE OR REPLACE PROPERTY GRAPH \`$PROJECT_ID.$GRAPH_DATASET.agent_trace_graph\`
  NODE TABLES (
    \`$PROJECT_ID.$GRAPH_DATASET.agent_spans_raw\` AS Span
      KEY (span_id)
      LABEL Span
      PROPERTIES ALL COLUMNS
  )
  EDGE TABLES (
    \`$PROJECT_ID.$GRAPH_DATASET.agent_spans_raw\` AS ParentOf
      KEY (span_id)
      SOURCE KEY (parent_id) REFERENCES Span (span_id)
      DESTINATION KEY (span_id) REFERENCES Span (span_id)
      LABEL ParentOf
  );
"

bq query --use_legacy_sql=false --project_id "$PROJECT_ID" "$GRAPH_SQL"

echo "---------------------------------------------------"
echo "✅ Setup Successful!"
echo "---------------------------------------------------"
echo "You can now visualize your agent chains in AutoSRE."
echo "Use dataset path: $PROJECT_ID.$GRAPH_DATASET"
echo "---------------------------------------------------"
