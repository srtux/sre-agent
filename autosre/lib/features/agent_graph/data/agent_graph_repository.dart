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

class AgentGraphRepository {
  final Dio _dio;

  AgentGraphRepository(this._dio);

  /// Builds the GRAPH_TABLE SQL for the multi-trace agent graph.
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
  Future<MultiTraceGraphPayload> fetchGraph({
    String dataset = kDefaultDataset,
    int timeRangeHours = 6,
    int? sampleLimit,
    String? projectId,
  }) async {
    final sql = buildGraphSql(
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
      jsonStr = (firstRow['flutter_graph_payload'] ??
              firstRow.values.first)
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
    // Wait, `agent_topology_edges` provides `total_duration_ms` per EDGE occurrence.
    final sql =
        '''
DECLARE start_ts TIMESTAMP DEFAULT TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL $timeRangeHours HOUR);

WITH EdgeRaw AS (
  SELECT total_duration_ms, (SELECT STRING_AGG(DISTINCT status_desc IGNORE NULLS) FROM `$dataset.agent_spans_raw` WHERE span_id = e.destination_node_id) as err
  FROM `$dataset.agent_topology_edges` e
  WHERE source_node_id = '$sourceId' AND destination_node_id = '$targetId'
  -- We don't have start_time in the view easily, but we assume time filtering by trace_id was done if trace_id is filtered, or we can just fetch all recent
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
