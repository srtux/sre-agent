import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:flutter/foundation.dart';

part 'models.freezed.dart';
part 'models.g.dart';

@freezed
abstract class AgentNode with _$AgentNode {
  const factory AgentNode({
    required String id,
    required String name,
    required String type, // 'coordinator', 'sub_agent', 'tool', 'data_source'
    required String status, // 'idle', 'active', 'completed', 'error'
    @Default([]) List<String> connections,
    Map<String, dynamic>? metadata,
  }) = _AgentNode;

  factory AgentNode.fromJson(Map<String, dynamic> json) =>
      _$AgentNodeFromJson(json);
}

@freezed
abstract class AgentActivityData with _$AgentActivityData {
  const factory AgentActivityData({
    required List<AgentNode> nodes,
    @JsonKey(name: 'current_phase') required String currentPhase,
    @JsonKey(name: 'active_node_id') String? activeNodeId,
    @JsonKey(name: 'completed_steps') @Default([]) List<String> completedSteps,
    String? message,
  }) = _AgentActivityData;

  factory AgentActivityData.fromJson(Map<String, dynamic> json) =>
      _$AgentActivityDataFromJson(json);
}
