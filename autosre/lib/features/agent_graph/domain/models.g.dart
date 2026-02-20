// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_MultiTraceNode _$MultiTraceNodeFromJson(Map<String, dynamic> json) =>
    _MultiTraceNode(
      id: json['id'] as String,
      type: json['type'] as String,
      label: json['label'] as String?,
      description: json['description'] as String?,
      executionCount: (json['execution_count'] as num?)?.toInt() ?? 0,
      totalTokens: (json['total_tokens'] as num?)?.toInt() ?? 0,
      inputTokens: (json['input_tokens'] as num?)?.toInt() ?? 0,
      outputTokens: (json['output_tokens'] as num?)?.toInt() ?? 0,
      errorCount: (json['error_count'] as num?)?.toInt() ?? 0,
      hasError: json['has_error'] as bool? ?? false,
      avgDurationMs: (json['avg_duration_ms'] as num?)?.toDouble() ?? 0.0,
      p95DurationMs: (json['p95_duration_ms'] as num?)?.toDouble() ?? 0.0,
      errorRatePct: (json['error_rate_pct'] as num?)?.toDouble() ?? 0.0,
      totalCost: (json['total_cost'] as num?)?.toDouble(),
      toolCallCount: (json['tool_call_count'] as num?)?.toInt() ?? 0,
      llmCallCount: (json['llm_call_count'] as num?)?.toInt() ?? 0,
      uniqueSessions: (json['unique_sessions'] as num?)?.toInt() ?? 0,
      isRoot: json['is_root'] as bool? ?? false,
      isLeaf: json['is_leaf'] as bool? ?? false,
      isUserEntryPoint: json['is_user_entry_point'] as bool? ?? false,
      isUserNode: json['is_user_node'] as bool? ?? false,
      childNodeIds:
          (json['child_node_ids'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
      depth: (json['depth'] as num?)?.toInt() ?? 0,
      downstreamTotalTokens:
          (json['downstream_total_tokens'] as num?)?.toInt() ?? 0,
      downstreamTotalCost: (json['downstream_total_cost'] as num?)?.toDouble(),
      downstreamToolCallCount:
          (json['downstream_tool_call_count'] as num?)?.toInt() ?? 0,
      downstreamLlmCallCount:
          (json['downstream_llm_call_count'] as num?)?.toInt() ?? 0,
    );

Map<String, dynamic> _$MultiTraceNodeToJson(_MultiTraceNode instance) =>
    <String, dynamic>{
      'id': instance.id,
      'type': instance.type,
      'label': instance.label,
      'description': instance.description,
      'execution_count': instance.executionCount,
      'total_tokens': instance.totalTokens,
      'input_tokens': instance.inputTokens,
      'output_tokens': instance.outputTokens,
      'error_count': instance.errorCount,
      'has_error': instance.hasError,
      'avg_duration_ms': instance.avgDurationMs,
      'p95_duration_ms': instance.p95DurationMs,
      'error_rate_pct': instance.errorRatePct,
      'total_cost': instance.totalCost,
      'tool_call_count': instance.toolCallCount,
      'llm_call_count': instance.llmCallCount,
      'unique_sessions': instance.uniqueSessions,
      'is_root': instance.isRoot,
      'is_leaf': instance.isLeaf,
      'is_user_entry_point': instance.isUserEntryPoint,
      'is_user_node': instance.isUserNode,
      'child_node_ids': instance.childNodeIds,
      'depth': instance.depth,
      'downstream_total_tokens': instance.downstreamTotalTokens,
      'downstream_total_cost': instance.downstreamTotalCost,
      'downstream_tool_call_count': instance.downstreamToolCallCount,
      'downstream_llm_call_count': instance.downstreamLlmCallCount,
    };

_MultiTraceEdge _$MultiTraceEdgeFromJson(Map<String, dynamic> json) =>
    _MultiTraceEdge(
      sourceId: json['source_id'] as String,
      targetId: json['target_id'] as String,
      sourceType: json['source_type'] as String? ?? '',
      targetType: json['target_type'] as String? ?? '',
      callCount: (json['call_count'] as num?)?.toInt() ?? 0,
      errorCount: (json['error_count'] as num?)?.toInt() ?? 0,
      errorRatePct: (json['error_rate_pct'] as num?)?.toDouble() ?? 0.0,
      sampleError: json['sample_error'] as String?,
      edgeTokens: (json['total_tokens'] as num?)?.toInt() ?? 0,
      inputTokens: (json['input_tokens'] as num?)?.toInt() ?? 0,
      outputTokens: (json['output_tokens'] as num?)?.toInt() ?? 0,
      avgTokensPerCall: (json['avg_tokens_per_call'] as num?)?.toInt() ?? 0,
      avgDurationMs: (json['avg_duration_ms'] as num?)?.toDouble() ?? 0.0,
      p95DurationMs: (json['p95_duration_ms'] as num?)?.toDouble() ?? 0.0,
      uniqueSessions: (json['unique_sessions'] as num?)?.toInt() ?? 0,
      totalCost: (json['total_cost'] as num?)?.toDouble(),
      isBackEdge: json['is_back_edge'] as bool? ?? false,
      flowWeight: (json['flow_weight'] as num?)?.toDouble() ?? 0.5,
    );

Map<String, dynamic> _$MultiTraceEdgeToJson(_MultiTraceEdge instance) =>
    <String, dynamic>{
      'source_id': instance.sourceId,
      'target_id': instance.targetId,
      'source_type': instance.sourceType,
      'target_type': instance.targetType,
      'call_count': instance.callCount,
      'error_count': instance.errorCount,
      'error_rate_pct': instance.errorRatePct,
      'sample_error': instance.sampleError,
      'total_tokens': instance.edgeTokens,
      'input_tokens': instance.inputTokens,
      'output_tokens': instance.outputTokens,
      'avg_tokens_per_call': instance.avgTokensPerCall,
      'avg_duration_ms': instance.avgDurationMs,
      'p95_duration_ms': instance.p95DurationMs,
      'unique_sessions': instance.uniqueSessions,
      'total_cost': instance.totalCost,
      'is_back_edge': instance.isBackEdge,
      'flow_weight': instance.flowWeight,
    };

_MultiTraceGraphPayload _$MultiTraceGraphPayloadFromJson(
  Map<String, dynamic> json,
) => _MultiTraceGraphPayload(
  nodes:
      (json['nodes'] as List<dynamic>?)
          ?.map((e) => MultiTraceNode.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const [],
  edges:
      (json['edges'] as List<dynamic>?)
          ?.map((e) => MultiTraceEdge.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const [],
);

Map<String, dynamic> _$MultiTraceGraphPayloadToJson(
  _MultiTraceGraphPayload instance,
) => <String, dynamic>{'nodes': instance.nodes, 'edges': instance.edges};
