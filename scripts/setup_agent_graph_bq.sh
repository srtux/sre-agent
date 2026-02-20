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
  ROUND(APPROX_QUANTILES(duration_ms, 100)[OFFSET(95)], 2) AS max_p95_duration_ms,
  COUNT(DISTINCT session_id) AS unique_sessions,
  ANY_VALUE(error_type) AS sample_error,
  -- Target-node metrics
  SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)) AS node_total_tokens,
  SUM(COALESCE(input_tokens, 0)) AS node_input_tokens,
  SUM(COALESCE(output_tokens, 0)) AS node_output_tokens,
  COUNTIF(status_code = 2) > 0 AS node_has_error,
  SUM(duration_ms) AS node_sum_duration_ms,
  ROUND(APPROX_QUANTILES(duration_ms, 100)[OFFSET(95)], 2) AS node_max_p95_duration_ms,
  COUNTIF(status_code = 2) AS node_error_count,
  COUNT(*) AS node_call_count,
  ROUND(SUM(span_cost), 6) AS node_total_cost,
  ANY_VALUE(COALESCE(agent_description, tool_description)) AS node_description,
  -- Subcall counts
  COUNTIF(target_type = 'Tool') AS tool_call_count,
  COUNTIF(target_type = 'LLM') AS llm_call_count,
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
  ROUND(APPROX_QUANTILES(duration_ms, 100)[OFFSET(95)], 2) AS max_p95_duration_ms,
  COUNT(DISTINCT session_id) AS unique_sessions,
  ANY_VALUE(error_type) AS sample_error,
  SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)) AS node_total_tokens,
  SUM(COALESCE(input_tokens, 0)) AS node_input_tokens,
  SUM(COALESCE(output_tokens, 0)) AS node_output_tokens,
  COUNTIF(status_code = 2) > 0 AS node_has_error,
  SUM(duration_ms) AS node_sum_duration_ms,
  ROUND(APPROX_QUANTILES(duration_ms, 100)[OFFSET(95)], 2) AS node_max_p95_duration_ms,
  COUNTIF(status_code = 2) AS node_error_count,
  COUNT(*) AS node_call_count,
  ROUND(SUM(span_cost), 6) AS node_total_cost,
  ANY_VALUE(COALESCE(agent_description, tool_description)) AS node_description,
  COUNTIF(target_type = 'Tool') AS tool_call_count,
  COUNTIF(target_type = 'LLM') AS llm_call_count,
  ARRAY_AGG(DISTINCT session_id) AS session_ids
FROM NewPaths
GROUP BY time_bucket, source_id, target_id, source_type, target_type;
SCHEDULED_QUERY_EOF

echo "---------------------------------------------------"
echo "✅ Setup Successful!"
echo "---------------------------------------------------"
echo "You can now visualize your agent chains in AutoSRE."
echo "Use dataset path: $PROJECT_ID.$GRAPH_DATASET"
echo ""
echo "Pre-aggregation:"
echo "  Table: $PROJECT_ID.$GRAPH_DATASET.agent_graph_hourly"
echo "  Backfilled with last 30 days of data."
echo "  Set up the scheduled query above for hourly incremental updates."
echo "---------------------------------------------------"
