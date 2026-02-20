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
      dst.agent_description AS agent_description, dst.tool_description AS tool_description
    )
  )
)$sampleClause,
AggregatedEdges AS (
  SELECT source_id, target_id, source_type, target_type,
    COUNT(DISTINCT session_id) AS unique_sessions, COUNT(*) AS call_count, COUNTIF(status_code = 2) AS error_count,
    ROUND(SAFE_DIVIDE(COUNTIF(status_code = 2), COUNT(*)) * 100, 2) AS error_rate_pct,
    ROUND(SAFE_DIVIDE(SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)), COUNT(*)), 0) AS avg_tokens_per_call,
    ROUND(AVG(duration_ms), 2) AS avg_duration_ms, ROUND(APPROX_QUANTILES(duration_ms, 100)[OFFSET(95)], 2) AS p95_duration_ms,
    ANY_VALUE(error_type) AS sample_error, SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)) AS edge_tokens
    ROUND(AVG(duration_ms), 2) AS avg_duration_ms, ROUND(APPROX_QUANTILES(duration_ms, 100)[OFFSET(95)], 2) AS p95_duration_ms,
    ANY_VALUE(error_type) AS sample_error, SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)) AS edge_tokens
  FROM FilteredPaths GROUP BY source_id, target_id, source_type, target_type
),
BaseNodes AS (
  SELECT target_id AS id, target_type AS type, ANY_VALUE(COALESCE(agent_description, tool_description)) AS description,
    SUM(COALESCE(input_tokens, 0) + COALESCE(output_tokens, 0)) AS total_tokens,
    COUNTIF(status_code = 2) > 0 AS has_error,
    ROUND(AVG(duration_ms), 2) AS avg_duration_ms,
    ROUND(SAFE_DIVIDE(COUNTIF(status_code = 2), COUNT(*)) * 100, 2) AS error_rate_pct
    ROUND(AVG(duration_ms), 2) AS avg_duration_ms,
    ROUND(SAFE_DIVIDE(COUNTIF(status_code = 2), COUNT(*)) * 100, 2) AS error_rate_pct
  FROM FilteredPaths GROUP BY target_id, target_type
  UNION DISTINCT
  SELECT source_id AS id, source_type AS type, NULL AS description, 0 AS total_tokens, FALSE AS has_error, 0.0 AS avg_duration_ms, 0.0 AS error_rate_pct
  FROM FilteredPaths GROUP BY source_id, source_type
),
AggregatedNodes AS (
  SELECT bn.*,
    IF(bn.id NOT IN (SELECT target_id FROM AggregatedEdges), TRUE, FALSE) AS is_root,
    IF(bn.id NOT IN (SELECT source_id FROM AggregatedEdges), TRUE, FALSE) AS is_leaf
  FROM BaseNodes bn QUALIFY ROW_NUMBER() OVER(PARTITION BY id ORDER BY total_tokens DESC) = 1
)
SELECT TO_JSON_STRING(STRUCT(
  (SELECT ARRAY_AGG(STRUCT(id, type, description, total_tokens, has_error, avg_duration_ms, error_rate_pct, is_root, is_leaf)) FROM AggregatedNodes) AS nodes,
  (SELECT ARRAY_AGG(STRUCT(source_id, target_id, source_type, target_type, call_count, error_count, error_rate_pct, sample_error, edge_tokens, avg_tokens_per_call, avg_duration_ms, p95_duration_ms, unique_sessions)) FROM AggregatedEdges) AS edges
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
}
