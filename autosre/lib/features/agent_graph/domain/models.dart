import 'package:freezed_annotation/freezed_annotation.dart';

part 'models.freezed.dart';
part 'models.g.dart';

/// A node in the multi-trace agent graph, representing an agent or tool
/// aggregated across multiple traces and sessions.
@freezed
abstract class MultiTraceNode with _$MultiTraceNode {
  const factory MultiTraceNode({
    required String id,
    required String type,
    String? description,
    @JsonKey(name: 'total_tokens') @Default(0) int totalTokens,
    @JsonKey(name: 'has_error') @Default(false) bool hasError,
    @JsonKey(name: 'avg_duration_ms') @Default(0.0) double avgDurationMs,
    @JsonKey(name: 'error_rate_pct') @Default(0.0) double errorRatePct,
    @JsonKey(name: 'is_root') @Default(false) bool isRoot,
    @JsonKey(name: 'is_leaf') @Default(false) bool isLeaf,
  }) = _MultiTraceNode;

  factory MultiTraceNode.fromJson(Map<String, dynamic> json) =>
      _$MultiTraceNodeFromJson(json);
}

/// An edge in the multi-trace agent graph, representing an aggregated
/// call relationship between two nodes across multiple traces.
@freezed
abstract class MultiTraceEdge with _$MultiTraceEdge {
  const factory MultiTraceEdge({
    @JsonKey(name: 'source_id') required String sourceId,
    @JsonKey(name: 'target_id') required String targetId,
    @JsonKey(name: 'source_type') @Default('') String sourceType,
    @JsonKey(name: 'target_type') @Default('') String targetType,
    @JsonKey(name: 'call_count') @Default(0) int callCount,
    @JsonKey(name: 'error_count') @Default(0) int errorCount,
    @JsonKey(name: 'error_rate_pct') @Default(0.0) double errorRatePct,
    @JsonKey(name: 'sample_error') String? sampleError,
    @JsonKey(name: 'edge_tokens') @Default(0) int edgeTokens,
    @JsonKey(name: 'avg_tokens_per_call') @Default(0) int avgTokensPerCall,
    @JsonKey(name: 'avg_duration_ms') @Default(0.0) double avgDurationMs,
    @JsonKey(name: 'p95_duration_ms') @Default(0.0) double p95DurationMs,
    @JsonKey(name: 'unique_sessions') @Default(0) int uniqueSessions,
  }) = _MultiTraceEdge;

  factory MultiTraceEdge.fromJson(Map<String, dynamic> json) =>
      _$MultiTraceEdgeFromJson(json);
}

/// The full payload returned by the BigQuery graph query,
/// containing all aggregated nodes and edges.
@freezed
abstract class MultiTraceGraphPayload with _$MultiTraceGraphPayload {
  const factory MultiTraceGraphPayload({
    @Default([]) List<MultiTraceNode> nodes,
    @Default([]) List<MultiTraceEdge> edges,
  }) = _MultiTraceGraphPayload;

  factory MultiTraceGraphPayload.fromJson(Map<String, dynamic> json) =>
      _$MultiTraceGraphPayloadFromJson(json);
}

/// Union type representing either a selected node or edge in the graph.
@freezed
sealed class SelectedGraphElement with _$SelectedGraphElement {
  const factory SelectedGraphElement.node(MultiTraceNode node) = SelectedNode;
  const factory SelectedGraphElement.edge(MultiTraceEdge edge) = SelectedEdge;
}
