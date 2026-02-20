import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../../shared/data/dio_provider.dart';
import '../domain/models.dart';

part 'agent_graph_repository.g.dart';

/// Default BigQuery dataset containing the agent trace property graph.
const kDefaultDataset = 'summitt-gcp.agent_graph';

@riverpod
AgentGraphRepository agentGraphRepository(Ref ref) {
  return AgentGraphRepository(ref.watch(dioProvider));
}

/// Minimum time range (in hours) to use the pre-aggregated hourly table.
/// Sub-hour ranges fall back to the live GRAPH_TABLE query since data volume
/// is small enough to be fast.
const kPrecomputedMinHours = 1;

class AgentGraphRepository {
  final Dio _dio;

  AgentGraphRepository(this._dio);

  /// Builds a lightweight SQL query against the pre-aggregated `agent_graph_hourly`
  /// table. This avoids the expensive GRAPH_TABLE recursive traversal and runs
  /// in sub-second time even for large graphs.
  ///
  /// Used for time ranges >= [kPrecomputedMinHours] hours.
  String buildPrecomputedGraphSql({
    required String dataset,
    required int timeRangeHours,
    int? sampleLimit,
  }) {
    // For precomputed queries, sampling is approximated by limiting to the
    // N most-active edges (by call_count).
    final edgeLimitClause = sampleLimit != null
        ? 'ORDER BY call_count DESC LIMIT $sampleLimit'
        : '';
    return '''
WITH HourlyData AS (
  SELECT * FROM `$dataset.agent_graph_hourly`
  WHERE time_bucket >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL $timeRangeHours HOUR)
),
AggregatedEdges AS (
  SELECT
    source_id, target_id,
    ANY_VALUE(source_type) AS source_type,
    ANY_VALUE(target_type) AS target_type,
    SUM(call_count) AS call_count,
    SUM(error_count) AS error_count,
    ROUND(SAFE_DIVIDE(SUM(error_count), SUM(call_count)) * 100, 2) AS error_rate_pct,
    ROUND(SAFE_DIVIDE(SUM(edge_tokens), SUM(call_count)), 0) AS avg_tokens_per_call,
    ROUND(SAFE_DIVIDE(SUM(sum_duration_ms), SUM(call_count)), 2) AS avg_duration_ms,
    ROUND(MAX(max_p95_duration_ms), 2) AS p95_duration_ms,
    ANY_VALUE(sample_error) AS sample_error,
    SUM(edge_tokens) AS edge_tokens,
    SUM(input_tokens) AS input_tokens,
    SUM(output_tokens) AS output_tokens,
    SUM(unique_sessions) AS unique_sessions,
    ROUND(SUM(total_cost), 6) AS total_cost
  FROM HourlyData
  GROUP BY source_id, target_id
  $edgeLimitClause
),
NodeSubcallCounts AS (
  SELECT source_id AS id,
    SUM(tool_call_count) AS tool_call_count,
    SUM(llm_call_count) AS llm_call_count
  FROM HourlyData
  GROUP BY source_id
),
BaseNodes AS (
  SELECT
    target_id AS id,
    ANY_VALUE(target_type) AS type,
    ANY_VALUE(node_description) AS description,
    SUM(node_total_tokens) AS total_tokens,
    SUM(node_input_tokens) AS input_tokens,
    SUM(node_output_tokens) AS output_tokens,
    LOGICAL_OR(node_has_error) AS has_error,
    ROUND(SAFE_DIVIDE(SUM(node_sum_duration_ms), SUM(node_call_count)), 2) AS avg_duration_ms,
    ROUND(MAX(node_max_p95_duration_ms), 2) AS p95_duration_ms,
    ROUND(SAFE_DIVIDE(SUM(node_error_count), SUM(node_call_count)) * 100, 2) AS error_rate_pct,
    ROUND(SUM(node_total_cost), 6) AS total_cost
  FROM HourlyData
  GROUP BY target_id
  UNION DISTINCT
  SELECT
    source_id AS id,
    ANY_VALUE(source_type) AS type,
    NULL AS description,
    0 AS total_tokens, 0 AS input_tokens, 0 AS output_tokens,
    FALSE AS has_error, 0.0 AS avg_duration_ms, 0.0 AS p95_duration_ms,
    0.0 AS error_rate_pct, 0.0 AS total_cost
  FROM HourlyData
  GROUP BY source_id
),
AggregatedNodes AS (
  SELECT bn.*,
    IF(bn.id NOT IN (SELECT target_id FROM AggregatedEdges), TRUE, FALSE) AS is_root,
    IF(bn.id NOT IN (SELECT source_id FROM AggregatedEdges), TRUE, FALSE) AS is_leaf,
    IF(bn.id NOT IN (SELECT target_id FROM AggregatedEdges) AND bn.type = 'Agent', TRUE, FALSE) AS is_user_entry_point,
    COALESCE(nsc.tool_call_count, 0) AS tool_call_count,
    COALESCE(nsc.llm_call_count, 0) AS llm_call_count
  FROM BaseNodes bn
  LEFT JOIN NodeSubcallCounts nsc ON bn.id = nsc.id
  QUALIFY ROW_NUMBER() OVER(PARTITION BY bn.id ORDER BY bn.total_tokens DESC) = 1
)
SELECT TO_JSON_STRING(STRUCT(
  (SELECT ARRAY_AGG(STRUCT(id, type, description, total_tokens, input_tokens, output_tokens, has_error, avg_duration_ms, p95_duration_ms, error_rate_pct, total_cost, tool_call_count, llm_call_count, is_root, is_leaf, is_user_entry_point)) FROM AggregatedNodes) AS nodes,
  (SELECT ARRAY_AGG(STRUCT(source_id, target_id, source_type, target_type, call_count, error_count, error_rate_pct, sample_error, edge_tokens, input_tokens, output_tokens, avg_tokens_per_call, avg_duration_ms, p95_duration_ms, unique_sessions, total_cost)) FROM AggregatedEdges) AS edges
)) AS flutter_graph_payload;
''';
  }

  /// Builds the GRAPH_TABLE SQL for the multi-trace agent graph.
  ///
  /// This is the "live" query that performs the expensive recursive GRAPH_TABLE
  /// traversal. Used as a fallback for sub-hour time ranges where data volume
  /// is small enough to be fast.
  ///
  /// [dataset] is the fully-qualified BQ dataset (e.g. `summitt-gcp.agent_graph`).
  /// [timeRangeHours] is the lookback window in hours.
  String buildGraphSql({
    required String dataset,
    required int timeRangeHours,
    int? sampleLimit,
  }) {
    // If sampling is requested, we first identify the latest N trace_ids,
    // then filter the graph paths to only include those traces.
    final sampleClause = sampleLimit != null
        ? '''
      , SampledTraces AS (
        SELECT DISTINCT trace_id
        FROM GraphPaths
        LIMIT $sampleLimit
      ),
      FilteredPaths AS (
        SELECT gp.*
        FROM GraphPaths gp
        INNER JOIN SampledTraces st ON gp.trace_id = st.trace_id
      )
      '''
        : ', FilteredPaths AS (SELECT * FROM GraphPaths)';
    return '''
WITH GraphPaths AS (
  SELECT * FROM GRAPH_TABLE(
    `$dataset.agent_trace_graph`
    MATCH (src:Span)-[:ParentOf]->{1,5}(dst:Span)
    WHERE src.node_type != 'Glue' AND dst.node_type != 'Glue' AND src.node_label != dst.node_label
      AND src.start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL $timeRangeHours HOUR)
    COLUMNS (
      src.node_label AS source_id, src.node_type AS source_type,
      dst.node_label AS target_id, dst.node_type AS target_type,
      dst.trace_id AS trace_id, dst.session_id AS session_id,
      dst.duration_ms AS duration_ms, dst.input_tokens AS input_tokens, dst.output_tokens AS output_tokens,
      dst.status_code AS status_code, dst.error_type AS error_type,
      dst.agent_description AS agent_description, dst.tool_description AS tool_description,
      dst.response_model AS response_model
    )
  )
)$sampleClause,
-- Cost lookup: approximate USD cost per token based on model
CostPaths AS (
  SELECT fp.*,
    COALESCE(input_tokens, 0) * CASE
      WHEN response_model LIKE '%flash%' THEN 0.00000015   -- \$0.15 per 1M input tokens
      WHEN response_model LIKE '%2.5-pro%' THEN 0.00000125 -- \$1.25 per 1M input tokens
      WHEN response_model LIKE '%1.5-pro%' THEN 0.00000125 -- \$1.25 per 1M input tokens
      ELSE 0.0000005                                         -- default fallback
    END
    + COALESCE(output_tokens, 0) * CASE
      WHEN response_model LIKE '%flash%' THEN 0.0000006    -- \$0.60 per 1M output tokens
      WHEN response_model LIKE '%2.5-pro%' THEN 0.00001    -- \$10.00 per 1M output tokens
      WHEN response_model LIKE '%1.5-pro%' THEN 0.000005   -- \$5.00 per 1M output tokens
      ELSE 0.000002                                          -- default fallback
    END AS span_cost
  FROM FilteredPaths fp
),
AggregatedEdges AS (
  SELECT source_id, target_id, source_type, target_type,
    COUNT(DISTINCT session_id) AS unique_sessions,
    COUNT(*) AS call_count,
    COUNTIF(status_code = 2) AS error_count,
    ROUND(SAFE_DIVIDE(COUNTIF(status_code = 2), COUNT(*)) * 100, 2) AS error_rate_pct,
    ROUND(SAFE_DIVIDE(SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)), COUNT(*)), 0) AS avg_tokens_per_call,
    ROUND(AVG(duration_ms), 2) AS avg_duration_ms,
    ROUND(APPROX_QUANTILES(duration_ms, 100)[OFFSET(95)], 2) AS p95_duration_ms,
    ANY_VALUE(error_type) AS sample_error,
    SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)) AS edge_tokens,
    SUM(COALESCE(input_tokens, 0)) AS input_tokens,
    SUM(COALESCE(output_tokens, 0)) AS output_tokens,
    ROUND(SUM(span_cost), 6) AS total_cost
  FROM CostPaths GROUP BY source_id, target_id, source_type, target_type
),
-- Count downstream tool and LLM calls per source node
NodeSubcallCounts AS (
  SELECT source_id AS id,
    COUNTIF(target_type = 'Tool') AS tool_call_count,
    COUNTIF(target_type = 'LLM') AS llm_call_count
  FROM CostPaths
  GROUP BY source_id
),
BaseNodes AS (
  SELECT target_id AS id, target_type AS type,
    ANY_VALUE(COALESCE(agent_description, tool_description)) AS description,
    SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)) AS total_tokens,
    SUM(COALESCE(input_tokens, 0)) AS input_tokens,
    SUM(COALESCE(output_tokens, 0)) AS output_tokens,
    COUNTIF(status_code = 2) > 0 AS has_error,
    ROUND(AVG(duration_ms), 2) AS avg_duration_ms,
    ROUND(APPROX_QUANTILES(duration_ms, 100)[OFFSET(95)], 2) AS p95_duration_ms,
    ROUND(SAFE_DIVIDE(COUNTIF(status_code = 2), COUNT(*)) * 100, 2) AS error_rate_pct,
    ROUND(SUM(span_cost), 6) AS total_cost
  FROM CostPaths GROUP BY target_id, target_type
  UNION DISTINCT
  SELECT source_id AS id, source_type AS type, NULL AS description,
    0 AS total_tokens, 0 AS input_tokens, 0 AS output_tokens,
    FALSE AS has_error, 0.0 AS avg_duration_ms, 0.0 AS p95_duration_ms,
    0.0 AS error_rate_pct, 0.0 AS total_cost
  FROM CostPaths GROUP BY source_id, source_type
),
AggregatedNodes AS (
  SELECT bn.*,
    IF(bn.id NOT IN (SELECT target_id FROM AggregatedEdges), TRUE, FALSE) AS is_root,
    IF(bn.id NOT IN (SELECT source_id FROM AggregatedEdges), TRUE, FALSE) AS is_leaf,
    -- A root node with type Agent is the user entry point
    IF(bn.id NOT IN (SELECT target_id FROM AggregatedEdges) AND bn.type = 'Agent', TRUE, FALSE) AS is_user_entry_point,
    COALESCE(nsc.tool_call_count, 0) AS tool_call_count,
    COALESCE(nsc.llm_call_count, 0) AS llm_call_count
  FROM BaseNodes bn
  LEFT JOIN NodeSubcallCounts nsc ON bn.id = nsc.id
  QUALIFY ROW_NUMBER() OVER(PARTITION BY bn.id ORDER BY bn.total_tokens DESC) = 1
)
SELECT TO_JSON_STRING(STRUCT(
  (SELECT ARRAY_AGG(STRUCT(id, type, description, total_tokens, input_tokens, output_tokens, has_error, avg_duration_ms, p95_duration_ms, error_rate_pct, total_cost, tool_call_count, llm_call_count, is_root, is_leaf, is_user_entry_point)) FROM AggregatedNodes) AS nodes,
  (SELECT ARRAY_AGG(STRUCT(source_id, target_id, source_type, target_type, call_count, error_count, error_rate_pct, sample_error, edge_tokens, input_tokens, output_tokens, avg_tokens_per_call, avg_duration_ms, p95_duration_ms, unique_sessions, total_cost)) FROM AggregatedEdges) AS edges
)) AS flutter_graph_payload;
''';
  }

  /// Executes the graph SQL and returns a parsed [MultiTraceGraphPayload].
  ///
  /// For time ranges >= [kPrecomputedMinHours], uses the pre-aggregated hourly
  /// table for sub-second performance. For sub-hour ranges, falls back to the
  /// live GRAPH_TABLE query.
  Future<MultiTraceGraphPayload> fetchGraph({
    String dataset = kDefaultDataset,
    int timeRangeHours = 6,
    int? sampleLimit,
    String? projectId,
  }) async {
    final sql = timeRangeHours >= kPrecomputedMinHours
        ? buildPrecomputedGraphSql(
            dataset: dataset,
            timeRangeHours: timeRangeHours,
            sampleLimit: sampleLimit,
          )
        : buildGraphSql(
            dataset: dataset,
            timeRangeHours: timeRangeHours,
            sampleLimit: sampleLimit,
          );

    final response = await _dio.post(
      '/api/tools/bigquery/query',
      data: {'sql': sql, 'project_id': projectId},
    );

    final data = response.data as Map<String, dynamic>;
    final rows = (data['rows'] as List?) ?? [];

    if (rows.isEmpty) {
      return const MultiTraceGraphPayload();
    }

    // The query returns a single row with a JSON string column.
    final firstRow = rows.first;
    String jsonStr;
    if (firstRow is Map) {
      jsonStr = (firstRow['flutter_graph_payload'] ?? firstRow.values.first)
          .toString();
    } else {
      jsonStr = firstRow.toString();
    }

    final payload = jsonDecode(jsonStr) as Map<String, dynamic>;
    return MultiTraceGraphPayload.fromJson(payload);
  }
}
