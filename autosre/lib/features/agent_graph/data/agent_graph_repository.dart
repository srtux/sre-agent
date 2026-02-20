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
/// Sub-hour ranges fall back to the live topology view query. Note: the UI
/// currently clamps time ranges to a minimum of 1 hour, so the live path
/// is only reachable programmatically.
const kPrecomputedMinHours = 1;

class AgentGraphRepository {
  final Dio _dio;

  AgentGraphRepository(this._dio);

  /// Builds a lightweight SQL query against the pre-aggregated `agent_graph_hourly`
  /// table. This avoids the expensive recursive traversal and runs
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
    SUM(edge_tokens) AS total_tokens,
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
  (SELECT ARRAY_AGG(STRUCT(source_id, target_id, source_type, target_type, call_count, error_count, error_rate_pct, sample_error, total_tokens, input_tokens, output_tokens, avg_tokens_per_call, avg_duration_ms, p95_duration_ms, unique_sessions, total_cost)) FROM AggregatedEdges) AS edges
)) AS flutter_graph_payload;
''';
  }

  /// Builds the live topology SQL for the multi-trace agent graph.
  ///
  /// This queries the pre-built topology views (`agent_topology_nodes`,
  /// `agent_topology_edges`) which use a recursive CTE to skip Glue spans.
  /// Used as a fallback for sub-hour time ranges where pre-aggregated data
  /// is not available.
  ///
  /// [dataset] is the fully-qualified BQ dataset (e.g. `summitt-gcp.agent_graph`).
  /// [timeRangeHours] is the lookback window in hours.
  String buildGraphSql({
    required String dataset,
    required int timeRangeHours,
    int? sampleLimit,
  }) {
    // Note: sampleLimit is ignored for now as we aggregate everything.
    // In the future we could limit to top N traces if needed.

    return '''
DECLARE start_ts TIMESTAMP DEFAULT TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL $timeRangeHours HOUR);

WITH
FilteredNodes AS (
  SELECT
    logical_node_id AS id,
    ANY_VALUE(node_type) AS type,
    ANY_VALUE(node_label) AS label,
    SUM(execution_count) AS execution_count,
    AVG(total_duration_ms / execution_count) AS avg_duration_ms,
    SUM(total_input_tokens + total_output_tokens) AS total_tokens,
    SUM(error_count) AS error_count,
    ROUND(SAFE_DIVIDE(SUM(error_count), SUM(execution_count)) * 100, 2) as error_rate_pct,
    COUNT(DISTINCT session_id) AS unique_sessions
  FROM `$dataset.agent_topology_nodes`
  WHERE start_time >= start_ts
  GROUP BY 1
),
FilteredEdges AS (
  SELECT
    source_node_id AS source_id,
    destination_node_id AS target_id,
    SUM(edge_weight) AS call_count,
    SUM(total_duration_ms) / SUM(edge_weight) AS avg_duration_ms,
    SUM(total_tokens) AS total_tokens,
    SUM(error_count) AS error_count,
    ROUND(SAFE_DIVIDE(SUM(error_count), SUM(edge_weight)) * 100, 2) as error_rate_pct,
    COUNT(DISTINCT session_id) AS unique_sessions
  FROM `$dataset.agent_topology_edges`
  WHERE trace_id IN (SELECT trace_id FROM `$dataset.agent_topology_nodes` WHERE start_time >= start_ts)
  GROUP BY 1, 2
)
SELECT TO_JSON_STRING(STRUCT(
  (SELECT ARRAY_AGG(STRUCT(
     id, type, label, execution_count, total_tokens, error_count,
     error_count > 0 AS has_error, avg_duration_ms, error_rate_pct, unique_sessions,
     NOT EXISTS(SELECT 1 FROM FilteredEdges WHERE target_id = id) AS is_root,
     NOT EXISTS(SELECT 1 FROM FilteredEdges WHERE source_id = id) AS is_leaf
   ))
   FROM FilteredNodes
  ) AS nodes,
  (SELECT ARRAY_AGG(STRUCT(
     source_id, target_id, call_count, error_count, error_rate_pct,
     total_tokens, avg_duration_ms, unique_sessions
   )) FROM FilteredEdges
  ) AS edges
)) AS flutter_graph_payload;
''';
  }

  /// Executes the graph SQL and returns a parsed [MultiTraceGraphPayload].
  ///
  /// For time ranges >= [kPrecomputedMinHours], uses the pre-aggregated hourly
  /// table for sub-second performance. For sub-hour ranges, falls back to the
  /// live topology view query.
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

  /// Fetches extended details for a single node (percentiles, top errors).
  Future<Map<String, dynamic>> fetchNodeDetails({
    required String dataset,
    required String nodeId,
    required int timeRangeHours,
    String? projectId,
  }) async {
    final sql =
        '''
DECLARE start_ts TIMESTAMP DEFAULT TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL $timeRangeHours HOUR);

SELECT TO_JSON_STRING(STRUCT(
  (
    SELECT STRUCT(
      IFNULL(APPROX_QUANTILES(duration_ms, 100)[OFFSET(50)], 0) as p50,
      IFNULL(APPROX_QUANTILES(duration_ms, 100)[OFFSET(90)], 0) as p90,
      IFNULL(APPROX_QUANTILES(duration_ms, 100)[OFFSET(99)], 0) as p99,
      IFNULL(MAX(duration_ms), 0) as max_val
    )
    FROM `$dataset.agent_spans_raw`
    WHERE logical_node_id = '$nodeId' AND start_time >= start_ts
  ) as latency,
  (
    SELECT ARRAY_AGG(DISTINCT status_desc IGNORE NULLS)
    FROM `$dataset.agent_spans_raw`
    WHERE logical_node_id = '$nodeId' AND status_code = 'ERROR' AND start_time >= start_ts
    LIMIT 3
  ) as top_errors
)) as details;
''';

    final response = await _dio.post(
      '/api/tools/bigquery/query',
      data: {'sql': sql, 'project_id': projectId},
    );

    final data = response.data as Map<String, dynamic>;
    final rows = (data['rows'] as List?) ?? [];
    if (rows.isEmpty) return {};

    final firstRow = rows.first;
    String jsonStr;
    if (firstRow is Map) {
      jsonStr = (firstRow['details'] ?? firstRow.values.first).toString();
    } else {
      jsonStr = firstRow.toString();
    }

    return jsonDecode(jsonStr) as Map<String, dynamic>;
  }

  /// Fetches extended details for a single edge (percentiles, top errors).
  Future<Map<String, dynamic>> fetchEdgeDetails({
    required String dataset,
    required String sourceId,
    required String targetId,
    required int timeRangeHours,
    String? projectId,
  }) async {
    // For edges, we use the `agent_topology_edges` view which aggregates by span_id.
    final sql =
        '''
DECLARE start_ts TIMESTAMP DEFAULT TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL $timeRangeHours HOUR);

WITH EdgeRaw AS (
  SELECT total_duration_ms, (SELECT STRING_AGG(DISTINCT status_desc IGNORE NULLS) FROM `$dataset.agent_spans_raw` WHERE span_id = e.destination_node_id) as err
  FROM `$dataset.agent_topology_edges` e
  WHERE source_node_id = '$sourceId' AND destination_node_id = '$targetId'
)
SELECT TO_JSON_STRING(STRUCT(
  (
    SELECT STRUCT(
      IFNULL(APPROX_QUANTILES(total_duration_ms, 100)[OFFSET(50)], 0) as p50,
      IFNULL(APPROX_QUANTILES(total_duration_ms, 100)[OFFSET(90)], 0) as p90,
      IFNULL(APPROX_QUANTILES(total_duration_ms, 100)[OFFSET(99)], 0) as p99,
      IFNULL(MAX(total_duration_ms), 0) as max_val
    )
    FROM EdgeRaw
  ) as latency,
  (
    SELECT ARRAY_AGG(err IGNORE NULLS)
    FROM EdgeRaw
    WHERE err IS NOT NULL
    LIMIT 3
  ) as top_errors
)) as details;
''';

    final response = await _dio.post(
      '/api/tools/bigquery/query',
      data: {'sql': sql, 'project_id': projectId},
    );

    final data = response.data as Map<String, dynamic>;
    final rows = (data['rows'] as List?) ?? [];
    if (rows.isEmpty) return {};

    final firstRow = rows.first;
    String jsonStr;
    if (firstRow is Map) {
      jsonStr = (firstRow['details'] ?? firstRow.values.first).toString();
    } else {
      jsonStr = firstRow.toString();
    }

    return jsonDecode(jsonStr) as Map<String, dynamic>;
  }
}
