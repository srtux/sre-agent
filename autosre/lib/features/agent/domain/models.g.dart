// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_AgentNode _$AgentNodeFromJson(Map<String, dynamic> json) => _AgentNode(
  id: json['id'] as String,
  name: json['name'] as String,
  type: json['type'] as String,
  status: json['status'] as String,
  connections:
      (json['connections'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList() ??
      const [],
  metadata: json['metadata'] as Map<String, dynamic>?,
);

Map<String, dynamic> _$AgentNodeToJson(_AgentNode instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'type': instance.type,
      'status': instance.status,
      'connections': instance.connections,
      'metadata': instance.metadata,
    };

_AgentActivityData _$AgentActivityDataFromJson(Map<String, dynamic> json) =>
    _AgentActivityData(
      nodes: (json['nodes'] as List<dynamic>)
          .map((e) => AgentNode.fromJson(e as Map<String, dynamic>))
          .toList(),
      currentPhase: json['current_phase'] as String,
      activeNodeId: json['active_node_id'] as String?,
      completedSteps:
          (json['completed_steps'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
      message: json['message'] as String?,
    );

Map<String, dynamic> _$AgentActivityDataToJson(_AgentActivityData instance) =>
    <String, dynamic>{
      'nodes': instance.nodes,
      'current_phase': instance.currentPhase,
      'active_node_id': instance.activeNodeId,
      'completed_steps': instance.completedSteps,
      'message': instance.message,
    };
