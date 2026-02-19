import 'package:flutter/foundation.dart';

// =============================================================================
// Agent Activity Models (moved from agent_activity_canvas.dart)
// =============================================================================

/// A node in the agent activity visualization.
final class AgentNode {
  final String id;
  final String name;
  final String type; // 'coordinator', 'sub_agent', 'tool', 'data_source'
  final String status; // 'idle', 'active', 'completed', 'error'
  final List<String> connections;
  final Map<String, dynamic>? metadata;

  AgentNode({
    required this.id,
    required this.name,
    required this.type,
    required this.status,
    this.connections = const [],
    this.metadata,
  });

  factory AgentNode.fromJson(Map<String, dynamic> json) {
    return AgentNode(
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      type: json['type'] as String? ?? 'tool',
      status: json['status'] as String? ?? 'idle',
      connections: (json['connections'] as List? ?? [])
          .map((e) => e.toString())
          .toList(),
      metadata: json['metadata'] is Map
          ? Map<String, dynamic>.from(json['metadata'] as Map)
          : null,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is AgentNode &&
          runtimeType == other.runtimeType &&
          id == other.id &&
          name == other.name &&
          type == other.type &&
          status == other.status &&
          listEquals(connections, other.connections);

  @override
  int get hashCode => Object.hash(id, name, type, status, connections.length);
}

/// Data model for the agent activity visualization.
final class AgentActivityData {
  final List<AgentNode> nodes;
  final String currentPhase;
  final String? activeNodeId;
  final List<String> completedSteps;
  final String? message;

  AgentActivityData({
    required this.nodes,
    required this.currentPhase,
    this.activeNodeId,
    this.completedSteps = const [],
    this.message,
  });

  factory AgentActivityData.fromJson(Map<String, dynamic> json) {
    final nodesList = (json['nodes'] as List? ?? [])
        .whereType<Map>()
        .map((n) => AgentNode.fromJson(Map<String, dynamic>.from(n)))
        .toList();
    return AgentActivityData(
      nodes: nodesList,
      currentPhase: json['current_phase'] as String? ?? 'Analyzing',
      activeNodeId: json['active_node_id'] as String?,
      completedSteps: (json['completed_steps'] as List? ?? [])
          .map((e) => e.toString())
          .toList(),
      message: json['message'] as String?,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is AgentActivityData &&
          runtimeType == other.runtimeType &&
          listEquals(nodes, other.nodes) &&
          currentPhase == other.currentPhase &&
          activeNodeId == other.activeNodeId &&
          listEquals(completedSteps, other.completedSteps) &&
          message == other.message;

  @override
  int get hashCode =>
      Object.hash(nodes.length, currentPhase, activeNodeId, message);
}

// =============================================================================
// Agent Trace / Graph Models
// =============================================================================

/// A single node in the flattened agent trace timeline.
final class AgentTraceNode {
  final String spanId;
  final String? parentSpanId;
  final String name;
  final String
  kind; // agent_invocation, llm_call, tool_execution, sub_agent_delegation
  final String operation; // invoke_agent, execute_tool, generate_content
  final double startOffsetMs;
  final double durationMs;
  final int depth;
  final int? inputTokens;
  final int? outputTokens;
  final String? modelUsed;
  final String? toolName;
  final String? agentName;
  final bool hasError;

  AgentTraceNode({
    required this.spanId,
    this.parentSpanId,
    required this.name,
    required this.kind,
    required this.operation,
    required this.startOffsetMs,
    required this.durationMs,
    required this.depth,
    this.inputTokens,
    this.outputTokens,
    this.modelUsed,
    this.toolName,
    this.agentName,
    required this.hasError,
  });

  factory AgentTraceNode.fromJson(Map<String, dynamic> json) {
    return AgentTraceNode(
      spanId: json['span_id'] as String? ?? '',
      parentSpanId: json['parent_span_id'] as String?,
      name: json['name'] as String? ?? '',
      kind: json['kind'] as String? ?? 'unknown',
      operation: json['operation'] as String? ?? 'unknown',
      startOffsetMs: (json['start_offset_ms'] as num?)?.toDouble() ?? 0,
      durationMs: (json['duration_ms'] as num?)?.toDouble() ?? 0,
      depth: (json['depth'] as num?)?.toInt() ?? 0,
      inputTokens: (json['input_tokens'] as num?)?.toInt(),
      outputTokens: (json['output_tokens'] as num?)?.toInt(),
      modelUsed: json['model_used'] as String?,
      toolName: json['tool_name'] as String?,
      agentName: json['agent_name'] as String?,
      hasError: json['has_error'] as bool? ?? false,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is AgentTraceNode &&
          runtimeType == other.runtimeType &&
          spanId == other.spanId &&
          parentSpanId == other.parentSpanId &&
          name == other.name &&
          kind == other.kind &&
          operation == other.operation &&
          startOffsetMs == other.startOffsetMs &&
          durationMs == other.durationMs &&
          depth == other.depth &&
          inputTokens == other.inputTokens &&
          outputTokens == other.outputTokens &&
          modelUsed == other.modelUsed &&
          toolName == other.toolName &&
          agentName == other.agentName &&
          hasError == other.hasError;

  @override
  int get hashCode => Object.hash(
    spanId,
    parentSpanId,
    name,
    kind,
    operation,
    startOffsetMs,
    durationMs,
    depth,
    inputTokens,
    outputTokens,
    modelUsed,
    toolName,
    agentName,
    hasError,
  );
}

/// Data model for the agent trace timeline widget.
final class AgentTraceData {
  final String traceId;
  final String? rootAgentName;
  final List<AgentTraceNode> nodes;
  final int totalInputTokens;
  final int totalOutputTokens;
  final double totalDurationMs;
  final int llmCallCount;
  final int toolCallCount;
  final List<String> uniqueAgents;
  final List<String> uniqueTools;
  final List<Map<String, dynamic>> antiPatterns;

  AgentTraceData({
    required this.traceId,
    this.rootAgentName,
    required this.nodes,
    required this.totalInputTokens,
    required this.totalOutputTokens,
    required this.totalDurationMs,
    required this.llmCallCount,
    required this.toolCallCount,
    required this.uniqueAgents,
    required this.uniqueTools,
    required this.antiPatterns,
  });

  factory AgentTraceData.fromJson(Map<String, dynamic> json) {
    return AgentTraceData(
      traceId: json['trace_id'] as String? ?? '',
      rootAgentName: json['root_agent_name'] as String?,
      nodes: (json['nodes'] as List? ?? [])
          .whereType<Map>()
          .map((n) => AgentTraceNode.fromJson(Map<String, dynamic>.from(n)))
          .toList(),
      totalInputTokens: (json['total_input_tokens'] as num?)?.toInt() ?? 0,
      totalOutputTokens: (json['total_output_tokens'] as num?)?.toInt() ?? 0,
      totalDurationMs: (json['total_duration_ms'] as num?)?.toDouble() ?? 0,
      llmCallCount: (json['llm_call_count'] as num?)?.toInt() ?? 0,
      toolCallCount: (json['tool_call_count'] as num?)?.toInt() ?? 0,
      uniqueAgents: (json['unique_agents'] as List? ?? [])
          .map((e) => e.toString())
          .toList(),
      uniqueTools: (json['unique_tools'] as List? ?? [])
          .map((e) => e.toString())
          .toList(),
      antiPatterns: (json['anti_patterns'] as List? ?? [])
          .whereType<Map>()
          .map((e) => Map<String, dynamic>.from(e))
          .toList(),
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is AgentTraceData &&
          runtimeType == other.runtimeType &&
          traceId == other.traceId &&
          rootAgentName == other.rootAgentName &&
          listEquals(nodes, other.nodes) &&
          totalInputTokens == other.totalInputTokens &&
          totalOutputTokens == other.totalOutputTokens &&
          totalDurationMs == other.totalDurationMs &&
          llmCallCount == other.llmCallCount &&
          toolCallCount == other.toolCallCount &&
          listEquals(uniqueAgents, other.uniqueAgents) &&
          listEquals(uniqueTools, other.uniqueTools);

  @override
  int get hashCode => Object.hash(
    traceId,
    rootAgentName,
    nodes.length,
    totalInputTokens,
    totalOutputTokens,
    totalDurationMs,
    llmCallCount,
    toolCallCount,
  );
}

/// A node in the agent dependency graph.
///
/// Supports progressive disclosure: agent/sub_agent nodes may be [expandable],
/// with [childrenCount] indicating how many scoped children (tools, models,
/// sub-agents) are hidden until the node is expanded. [parentAgentId]
/// identifies which agent scope owns this node, and [depth] encodes the
/// hierarchy level (0 = user, 1 = root agent, 2+ = deeper).
final class AgentGraphNode {
  final String id;
  final String label;
  final String type; // user, agent, tool, llm_model, sub_agent
  final int? totalTokens;
  final int? callCount;
  final bool hasError;

  /// Hierarchy depth: 0 = user, 1 = root agents, 2+ = deeper scopes.
  final int depth;

  /// The agent node ID that owns this node's scope (null for user/root agents).
  final String? parentAgentId;

  /// Number of direct children hidden behind this node (tools + models + sub-agents).
  final int childrenCount;

  /// Whether this node can be expanded to reveal children.
  final bool expandable;

  AgentGraphNode({
    required this.id,
    required this.label,
    required this.type,
    this.totalTokens,
    this.callCount,
    required this.hasError,
    this.depth = 0,
    this.parentAgentId,
    this.childrenCount = 0,
    this.expandable = false,
  });

  factory AgentGraphNode.fromJson(Map<String, dynamic> json) {
    return AgentGraphNode(
      id: json['id'] as String? ?? '',
      label: json['label'] as String? ?? '',
      type: json['type'] as String? ?? 'unknown',
      totalTokens: (json['total_tokens'] as num?)?.toInt(),
      callCount: (json['call_count'] as num?)?.toInt(),
      hasError: json['has_error'] as bool? ?? false,
      depth: (json['depth'] as num?)?.toInt() ?? 0,
      parentAgentId: json['parent_agent_id'] as String?,
      childrenCount: (json['children_count'] as num?)?.toInt() ?? 0,
      expandable: json['expandable'] as bool? ?? false,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is AgentGraphNode &&
          runtimeType == other.runtimeType &&
          id == other.id &&
          label == other.label &&
          type == other.type &&
          totalTokens == other.totalTokens &&
          callCount == other.callCount &&
          hasError == other.hasError &&
          depth == other.depth &&
          parentAgentId == other.parentAgentId &&
          childrenCount == other.childrenCount &&
          expandable == other.expandable;

  @override
  int get hashCode => Object.hash(
    id, label, type, totalTokens, callCount, hasError,
    depth, parentAgentId, childrenCount, expandable,
  );
}

/// An edge in the agent dependency graph.
final class AgentGraphEdge {
  final String sourceId;
  final String targetId;
  final String label; // invokes, calls, delegates_to, generates
  final int callCount;
  final double avgDurationMs;
  final int? totalTokens;
  final bool hasError;

  /// The max depth of source/target nodes. Used for progressive disclosure
  /// filtering — edges are only shown when both endpoints are visible.
  final int depth;

  AgentGraphEdge({
    required this.sourceId,
    required this.targetId,
    required this.label,
    required this.callCount,
    required this.avgDurationMs,
    this.totalTokens,
    required this.hasError,
    this.depth = 0,
  });

  factory AgentGraphEdge.fromJson(Map<String, dynamic> json) {
    return AgentGraphEdge(
      sourceId: json['source_id'] as String? ?? '',
      targetId: json['target_id'] as String? ?? '',
      label: json['label'] as String? ?? '',
      callCount: (json['call_count'] as num?)?.toInt() ?? 0,
      avgDurationMs: (json['avg_duration_ms'] as num?)?.toDouble() ?? 0,
      totalTokens: (json['total_tokens'] as num?)?.toInt(),
      hasError: json['has_error'] as bool? ?? false,
      depth: (json['depth'] as num?)?.toInt() ?? 0,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is AgentGraphEdge &&
          runtimeType == other.runtimeType &&
          sourceId == other.sourceId &&
          targetId == other.targetId &&
          label == other.label &&
          callCount == other.callCount &&
          avgDurationMs == other.avgDurationMs &&
          totalTokens == other.totalTokens &&
          hasError == other.hasError &&
          depth == other.depth;

  @override
  int get hashCode => Object.hash(
    sourceId,
    targetId,
    label,
    callCount,
    avgDurationMs,
    totalTokens,
    hasError,
    depth,
  );
}

/// Data model for the agent dependency graph widget.
final class AgentGraphData {
  final List<AgentGraphNode> nodes;
  final List<AgentGraphEdge> edges;
  final String? rootAgentName;

  AgentGraphData({
    required this.nodes,
    required this.edges,
    this.rootAgentName,
  });

  factory AgentGraphData.fromJson(Map<String, dynamic> json) {
    return AgentGraphData(
      nodes: (json['nodes'] as List? ?? [])
          .whereType<Map>()
          .map((n) => AgentGraphNode.fromJson(Map<String, dynamic>.from(n)))
          .toList(),
      edges: (json['edges'] as List? ?? [])
          .whereType<Map>()
          .map((e) => AgentGraphEdge.fromJson(Map<String, dynamic>.from(e)))
          .toList(),
      rootAgentName: json['root_agent_name'] as String?,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is AgentGraphData &&
          runtimeType == other.runtimeType &&
          listEquals(nodes, other.nodes) &&
          listEquals(edges, other.edges) &&
          rootAgentName == other.rootAgentName;

  @override
  int get hashCode => Object.hash(nodes.length, edges.length, rootAgentName);
}
