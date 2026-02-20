// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_MultiTraceNode _$MultiTraceNodeFromJson(Map<String, dynamic> json) =>
    _MultiTraceNode(
      id: json['id'] as String,
      type: json['type'] as String,
      description: json['description'] as String?,
      totalTokens: (json['total_tokens'] as num?)?.toInt() ?? 0,
      inputTokens: (json['input_tokens'] as num?)?.toInt() ?? 0,
      outputTokens: (json['output_tokens'] as num?)?.toInt() ?? 0,
      hasError: json['has_error'] as bool? ?? false,
      avgDurationMs: (json['avg_duration_ms'] as num?)?.toDouble() ?? 0.0,
      p95DurationMs: (json['p95_duration_ms'] as num?)?.toDouble() ?? 0.0,
      errorRatePct: (json['error_rate_pct'] as num?)?.toDouble() ?? 0.0,
      totalCost: (json['total_cost'] as num?)?.toDouble(),
      toolCallCount: (json['tool_call_count'] as num?)?.toInt() ?? 0,
      llmCallCount: (json['llm_call_count'] as num?)?.toInt() ?? 0,
      isRoot: json['is_root'] as bool? ?? false,
      isLeaf: json['is_leaf'] as bool? ?? false,
      isUserEntryPoint: json['is_user_entry_point'] as bool? ?? false,
    );

Map<String, dynamic> _$MultiTraceNodeToJson(_MultiTraceNode instance) =>
    <String, dynamic>{
      'id': instance.id,
      'type': instance.type,
      'description': instance.description,
      'total_tokens': instance.totalTokens,
      'input_tokens': instance.inputTokens,
      'output_tokens': instance.outputTokens,
      'has_error': instance.hasError,
      'avg_duration_ms': instance.avgDurationMs,
      'p95_duration_ms': instance.p95DurationMs,
      'error_rate_pct': instance.errorRatePct,
      'total_cost': instance.totalCost,
      'tool_call_count': instance.toolCallCount,
      'llm_call_count': instance.llmCallCount,
      'is_root': instance.isRoot,
      'is_leaf': instance.isLeaf,
      'is_user_entry_point': instance.isUserEntryPoint,
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
      edgeTokens: (json['edge_tokens'] as num?)?.toInt() ?? 0,
      inputTokens: (json['input_tokens'] as num?)?.toInt() ?? 0,
      outputTokens: (json['output_tokens'] as num?)?.toInt() ?? 0,
      avgTokensPerCall: (json['avg_tokens_per_call'] as num?)?.toInt() ?? 0,
      avgDurationMs: (json['avg_duration_ms'] as num?)?.toDouble() ?? 0.0,
      p95DurationMs: (json['p95_duration_ms'] as num?)?.toDouble() ?? 0.0,
      uniqueSessions: (json['unique_sessions'] as num?)?.toInt() ?? 0,
      totalCost: (json['total_cost'] as num?)?.toDouble(),
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
      'edge_tokens': instance.edgeTokens,
      'input_tokens': instance.inputTokens,
      'output_tokens': instance.outputTokens,
      'avg_tokens_per_call': instance.avgTokensPerCall,
      'avg_duration_ms': instance.avgDurationMs,
      'p95_duration_ms': instance.p95DurationMs,
      'unique_sessions': instance.uniqueSessions,
      'total_cost': instance.totalCost,
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
