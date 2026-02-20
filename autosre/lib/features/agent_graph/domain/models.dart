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
    String? label,
    String? description,
    @JsonKey(name: 'execution_count') @Default(0) int executionCount,
    @JsonKey(name: 'total_tokens') @Default(0) int totalTokens,
    @JsonKey(name: 'input_tokens') @Default(0) int inputTokens,
    @JsonKey(name: 'output_tokens') @Default(0) int outputTokens,
    @JsonKey(name: 'error_count') @Default(0) int errorCount,
    @JsonKey(name: 'has_error') @Default(false) bool hasError,
    @JsonKey(name: 'avg_duration_ms') @Default(0.0) double avgDurationMs,
    @JsonKey(name: 'p95_duration_ms') @Default(0.0) double p95DurationMs,
    @JsonKey(name: 'error_rate_pct') @Default(0.0) double errorRatePct,
    @JsonKey(name: 'total_cost') double? totalCost,
    @JsonKey(name: 'tool_call_count') @Default(0) int toolCallCount,
    @JsonKey(name: 'llm_call_count') @Default(0) int llmCallCount,
    @JsonKey(name: 'unique_sessions') @Default(0) int uniqueSessions,
    @JsonKey(name: 'is_root') @Default(false) bool isRoot,
    @JsonKey(name: 'is_leaf') @Default(false) bool isLeaf,
    @JsonKey(name: 'is_user_entry_point') @Default(false) bool isUserEntryPoint,

    // User node flag
    @JsonKey(name: 'is_user_node') @Default(false) bool isUserNode,

    // Tree/DAG hierarchy support
    @JsonKey(name: 'child_node_ids') @Default([]) List<String> childNodeIds,
    @JsonKey(includeFromJson: false, includeToJson: false)
    @Default(true)
    bool isExpanded,
    @JsonKey(name: 'depth') @Default(0) int depth,

    // Hierarchical rollup metrics (includes all downstream descendants)
    @JsonKey(name: 'downstream_total_tokens') @Default(0) int downstreamTotalTokens,
    @JsonKey(name: 'downstream_total_cost') double? downstreamTotalCost,
    @JsonKey(name: 'downstream_tool_call_count')
    @Default(0)
    int downstreamToolCallCount,
    @JsonKey(name: 'downstream_llm_call_count')
    @Default(0)
    int downstreamLlmCallCount,
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
    @JsonKey(name: 'total_tokens') @Default(0) int edgeTokens,
    @JsonKey(name: 'input_tokens') @Default(0) int inputTokens,
    @JsonKey(name: 'output_tokens') @Default(0) int outputTokens,
    @JsonKey(name: 'avg_tokens_per_call') @Default(0) int avgTokensPerCall,
    @JsonKey(name: 'avg_duration_ms') @Default(0.0) double avgDurationMs,
    @JsonKey(name: 'p95_duration_ms') @Default(0.0) double p95DurationMs,
    @JsonKey(name: 'unique_sessions') @Default(0) int uniqueSessions,
    @JsonKey(name: 'total_cost') double? totalCost,

    // Back-edge detection (for cycle rendering)
    @JsonKey(name: 'is_back_edge') @Default(false) bool isBackEdge,

    // Normalized flow weight (0.0 to 1.0) for animation speed
    @JsonKey(name: 'flow_weight') @Default(0.5) double flowWeight,
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
  const factory SelectedGraphElement.path(List<String> nodeIds, {String? label}) =
      SelectedPath;
}
