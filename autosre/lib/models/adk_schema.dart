class SpanInfo {
  final String spanId;
  final String traceId;
  final String name;
  final DateTime startTime;
  final DateTime endTime;
  final Map<String, dynamic> attributes;
  final String status; // 'OK', 'ERROR'
  final String? parentSpanId;

  SpanInfo({
    required this.spanId,
    required this.traceId,
    required this.name,
    required this.startTime,
    required this.endTime,
    required this.attributes,
    required this.status,
    this.parentSpanId,
  });

  Duration get duration => endTime.difference(startTime);

  factory SpanInfo.fromJson(Map<String, dynamic> json) {
    return SpanInfo(
      spanId: json['span_id'],
      traceId: json['trace_id'],
      name: json['name'],
      startTime: DateTime.parse(json['start_time']),
      endTime: DateTime.parse(json['end_time']),
      attributes: Map<String, dynamic>.from(json['attributes'] ?? {}),
      status: json['status'] ?? 'OK',
      parentSpanId: json['parent_span_id'],
    );
  }
}

class Trace {
  final String traceId;
  final List<SpanInfo> spans;

  Trace({required this.traceId, required this.spans});

  factory Trace.fromJson(Map<String, dynamic> json) {
    // Safely handle null or missing spans with default empty list
    final rawSpans = json['spans'];
    final List spansList;

    if (rawSpans == null) {
      spansList = [];
    } else if (rawSpans is List) {
      spansList = rawSpans;
    } else {
      // If spans is neither null nor a List, use empty list
      spansList = [];
    }

    // Parse each span, filtering out any that fail to parse
    final parsedSpans = <SpanInfo>[];
    for (final item in spansList) {
      try {
        if (item is Map) {
          parsedSpans.add(SpanInfo.fromJson(Map<String, dynamic>.from(item)));
        }
      } catch (e) {
        // Skip malformed spans rather than failing the entire trace
        continue;
      }
    }

    return Trace(traceId: json['trace_id'] ?? 'unknown', spans: parsedSpans);
  }
}

class MetricPoint {
  final DateTime timestamp;
  final double value;
  final bool isAnomaly;

  MetricPoint({
    required this.timestamp,
    required this.value,
    this.isAnomaly = false,
  });

  factory MetricPoint.fromJson(Map<String, dynamic> json) {
    return MetricPoint(
      timestamp: DateTime.parse(json['timestamp']),
      value: (json['value'] as num).toDouble(),
      isAnomaly: json['is_anomaly'] ?? false,
    );
  }
}

class MetricSeries {
  final String metricName;
  final List<MetricPoint> points;
  final Map<String, dynamic> labels;

  MetricSeries({
    required this.metricName,
    required this.points,
    required this.labels,
  });

  factory MetricSeries.fromJson(Map<String, dynamic> json) {
    var list = json['points'] as List;
    var pointsList = list
        .map((i) => MetricPoint.fromJson(i))
        .toList();
    return MetricSeries(
      metricName: json['metric_name'],
      points: pointsList,
      labels: Map<String, dynamic>.from(json['labels'] ?? {}),
    );
  }
}

class LogPattern {
  final String template;
  final int count;
  final Map<String, int> severityCounts;

  LogPattern({
    required this.template,
    required this.count,
    required this.severityCounts,
  });

  factory LogPattern.fromJson(Map<String, dynamic> json) {
    return LogPattern(
      template: json['template'],
      count: json['count'],
      severityCounts: Map<String, int>.from(json['severity_counts'] ?? {}),
    );
  }
}

class RemediationStep {
  final String command;
  final String description;

  RemediationStep({required this.command, required this.description});

  factory RemediationStep.fromJson(Map<String, dynamic> json) {
    return RemediationStep(
      command: json['command'],
      description: json['description'],
    );
  }
}

class RemediationPlan {
  final String issue;
  final String risk; // 'low', 'medium', 'high'
  final List<RemediationStep> steps;

  RemediationPlan({
    required this.issue,
    required this.risk,
    required this.steps,
  });

  factory RemediationPlan.fromJson(Map<String, dynamic> json) {
    var list = json['steps'] as List;
    var stepsList = list
        .map((i) => RemediationStep.fromJson(i))
        .toList();
    return RemediationPlan(
      issue: json['issue'],
      risk: json['risk'],
      steps: stepsList,
    );
  }
}

/// Represents a finding from a specialist panel in the council.
class PanelFinding {
  final String panel; // trace, metrics, logs, alerts
  final String summary;
  final String severity; // critical, warning, info, healthy
  final double confidence;
  final List<String> evidence;
  final List<String> recommendedActions;

  PanelFinding({
    required this.panel,
    required this.summary,
    required this.severity,
    required this.confidence,
    required this.evidence,
    required this.recommendedActions,
  });

  factory PanelFinding.fromJson(Map<String, dynamic> json) {
    return PanelFinding(
      panel: json['panel'] as String? ?? 'unknown',
      summary: json['summary'] as String? ?? '',
      severity: json['severity'] as String? ?? 'info',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      evidence: (json['evidence'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      recommendedActions: (json['recommended_actions'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
    );
  }

  /// Returns the display name for the panel
  String get displayName {
    switch (panel.toLowerCase()) {
      case 'trace':
        return 'Trace Analysis';
      case 'metrics':
        return 'Metrics Analysis';
      case 'logs':
        return 'Logs Analysis';
      case 'alerts':
        return 'Alerts Analysis';
      default:
        return panel;
    }
  }

  /// Returns the icon name for the panel
  String get iconName {
    switch (panel.toLowerCase()) {
      case 'trace':
        return 'timeline';
      case 'metrics':
        return 'analytics';
      case 'logs':
        return 'description';
      case 'alerts':
        return 'notifications_active';
      default:
        return 'help';
    }
  }
}

/// Represents a critic's cross-examination report in debate mode.
class CriticReport {
  final List<String> agreements;
  final List<String> contradictions;
  final List<String> gaps;
  final double revisedConfidence;

  CriticReport({
    required this.agreements,
    required this.contradictions,
    required this.gaps,
    required this.revisedConfidence,
  });

  factory CriticReport.fromJson(Map<String, dynamic> json) {
    return CriticReport(
      agreements: (json['agreements'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      contradictions: (json['contradictions'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      gaps: (json['gaps'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      revisedConfidence:
          (json['revised_confidence'] as num?)?.toDouble() ?? 0.0,
    );
  }

  /// Whether there are any contradictions
  bool get hasContradictions => contradictions.isNotEmpty;

  /// Whether there are any gaps
  bool get hasGaps => gaps.isNotEmpty;

  /// Whether there is strong agreement
  bool get hasStrongAgreement =>
      agreements.length >= 2 && contradictions.isEmpty;
}

/// Represents a council investigation synthesis result.
class CouncilSynthesisData {
  final String synthesis;
  final String overallSeverity;
  final double overallConfidence;
  final String mode;
  final int rounds;
  final List<PanelFinding> panels;
  final CriticReport? criticReport;
  final CouncilActivityGraph? activityGraph;
  final Map<String, dynamic> rawData;

  CouncilSynthesisData({
    required this.synthesis,
    required this.overallSeverity,
    required this.overallConfidence,
    required this.mode,
    required this.rounds,
    required this.panels,
    this.criticReport,
    this.activityGraph,
    required this.rawData,
  });

  factory CouncilSynthesisData.fromJson(Map<String, dynamic> json) {
    // The result may be nested under 'result' key from BaseToolResponse
    final data = json.containsKey('result') && json['result'] is Map
        ? Map<String, dynamic>.from(json['result'] as Map)
        : json;

    // Parse panels
    List<PanelFinding> panels = [];
    if (data['panels'] != null && data['panels'] is List) {
      panels = (data['panels'] as List)
          .map((p) => PanelFinding.fromJson(Map<String, dynamic>.from(p)))
          .toList();
    }

    // Parse critic report
    CriticReport? criticReport;
    if (data['critic_report'] != null && data['critic_report'] is Map) {
      criticReport = CriticReport.fromJson(
          Map<String, dynamic>.from(data['critic_report'] as Map));
    }

    // Parse activity graph
    CouncilActivityGraph? activityGraph;
    if (data['activity_graph'] != null && data['activity_graph'] is Map) {
      activityGraph = CouncilActivityGraph.fromJson(
          Map<String, dynamic>.from(data['activity_graph'] as Map));
    }

    return CouncilSynthesisData(
      synthesis: data['synthesis'] as String? ?? '',
      overallSeverity: data['overall_severity'] as String? ?? 'info',
      overallConfidence:
          (data['overall_confidence'] as num?)?.toDouble() ?? 0.0,
      mode: data['mode'] as String? ?? 'standard',
      rounds: data['rounds'] as int? ?? 1,
      panels: panels,
      criticReport: criticReport,
      activityGraph: activityGraph,
      rawData: json,
    );
  }

  /// Whether this is a debate mode investigation
  bool get isDebateMode => mode.toLowerCase() == 'debate';

  /// Whether critic report is available
  bool get hasCriticReport => criticReport != null;

  /// Whether activity graph is available
  bool get hasActivityGraph => activityGraph != null;

  /// Get panel by type
  PanelFinding? getPanelByType(String type) {
    try {
      return panels.firstWhere((p) => p.panel.toLowerCase() == type.toLowerCase());
    } catch (_) {
      return null;
    }
  }

  /// Get total tool calls from activity graph
  int get totalToolCalls => activityGraph?.totalToolCalls ?? 0;

  /// Get total LLM calls from activity graph
  int get totalLLMCalls => activityGraph?.totalLLMCalls ?? 0;
}

class ToolLog {
  final String toolName;
  final Map<String, dynamic> args;
  final String status; // 'running', 'completed', 'error'
  final String? result;
  final String? timestamp;
  final String? duration;

  ToolLog({
    required this.toolName,
    required this.args,
    required this.status,
    this.result,
    this.timestamp,
    this.duration,
  });

  factory ToolLog.fromJson(Map<String, dynamic> json) {
    return ToolLog(
      toolName: json['tool_name'],
      args: Map<String, dynamic>.from(json['args'] ?? {}),
      status: json['status'] ?? 'unknown',
      result: json['result']
          ?.toString(), // Handle both string and complex object results by stringifying for now
      timestamp: json['timestamp'],
      duration: json['duration'],
    );
  }
}

/// Individual log entry with full payload for expandable JSON view
class LogEntry {
  final String insertId;
  final DateTime timestamp;
  final String severity; // 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
  final dynamic payload; // Can be String (text) or Map (JSON)
  final Map<String, String> resourceLabels;
  final String resourceType;
  final String? traceId;
  final String? spanId;
  final Map<String, dynamic>? httpRequest;

  LogEntry({
    required this.insertId,
    required this.timestamp,
    required this.severity,
    required this.payload,
    required this.resourceLabels,
    required this.resourceType,
    this.traceId,
    this.spanId,
    this.httpRequest,
  });

  bool get isJsonPayload => payload is Map;

  String get payloadPreview {
    if (payload is String) {
      return payload.length > 200 ? '${payload.substring(0, 200)}...' : payload;
    }
    if (payload is Map) {
      final message = payload['message'] ?? payload['msg'] ?? payload['text'];
      if (message != null) return message.toString();
      return payload.toString().length > 200
          ? '${payload.toString().substring(0, 200)}...'
          : payload.toString();
    }
    return payload?.toString() ?? '';
  }

  factory LogEntry.fromJson(Map<String, dynamic> json) {
    return LogEntry(
      insertId: json['insert_id'] ?? '',
      timestamp: DateTime.parse(json['timestamp']),
      severity: json['severity'] ?? 'INFO',
      payload: json['payload'],
      resourceLabels: Map<String, String>.from(json['resource_labels'] ?? {}),
      resourceType: json['resource_type'] ?? 'unknown',
      traceId: json['trace_id'],
      spanId: json['span_id'],
      httpRequest: json['http_request'] != null
          ? Map<String, dynamic>.from(json['http_request'])
          : null,
    );
  }
}

/// Container for log entries viewer
class LogEntriesData {
  final List<LogEntry> entries;
  final String? filter;
  final String? projectId;
  final String? nextPageToken;

  LogEntriesData({
    required this.entries,
    this.filter,
    this.projectId,
    this.nextPageToken,
  });

  factory LogEntriesData.fromJson(Map<String, dynamic> json) {
    final entriesList = (json['entries'] as List? ?? [])
        .map((e) => LogEntry.fromJson(Map<String, dynamic>.from(e)))
        .toList();
    return LogEntriesData(
      entries: entriesList,
      filter: json['filter'],
      projectId: json['project_id'],
      nextPageToken: json['next_page_token'],
    );
  }
}

/// Model for a single metric in the dashboard
class DashboardMetric {
  final String id;
  final String name;
  final String unit;
  final double currentValue;
  final double? previousValue;
  final double? threshold;
  final List<MetricDataPoint> history;
  final String status; // 'normal', 'warning', 'critical'
  final String? anomalyDescription;

  DashboardMetric({
    required this.id,
    required this.name,
    required this.unit,
    required this.currentValue,
    this.previousValue,
    this.threshold,
    this.history = const [],
    this.status = 'normal',
    this.anomalyDescription,
  });

  factory DashboardMetric.fromJson(Map<String, dynamic> json) {
    return DashboardMetric(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      unit: json['unit'] ?? '',
      currentValue: (json['current_value'] as num?)?.toDouble() ?? 0,
      previousValue: (json['previous_value'] as num?)?.toDouble(),
      threshold: (json['threshold'] as num?)?.toDouble(),
      history: (json['history'] as List? ?? [])
          .map((p) => MetricDataPoint.fromJson(Map<String, dynamic>.from(p)))
          .toList(),
      status: json['status'] ?? 'normal',
      anomalyDescription: json['anomaly_description'],
    );
  }

  double get changePercent {
    if (previousValue == null || previousValue == 0) return 0;
    return ((currentValue - previousValue!) / previousValue!) * 100;
  }
}

/// Model for a metric data point
class MetricDataPoint {
  final DateTime timestamp;
  final double value;

  MetricDataPoint({required this.timestamp, required this.value});

  factory MetricDataPoint.fromJson(Map<String, dynamic> json) {
    return MetricDataPoint(
      timestamp: DateTime.parse(json['timestamp']),
      value: (json['value'] as num?)?.toDouble() ?? 0,
    );
  }
}

/// Model for the metrics dashboard
class MetricsDashboardData {
  final String title;
  final String? serviceName;
  final List<DashboardMetric> metrics;
  final DateTime? lastUpdated;

  MetricsDashboardData({
    required this.title,
    this.serviceName,
    required this.metrics,
    this.lastUpdated,
  });

  factory MetricsDashboardData.fromJson(Map<String, dynamic> json) {
    return MetricsDashboardData(
      title: json['title'] ?? 'Metrics Dashboard',
      serviceName: json['service_name'],
      metrics: (json['metrics'] as List? ?? [])
          .map((m) => DashboardMetric.fromJson(Map<String, dynamic>.from(m)))
          .toList(),
      lastUpdated: json['last_updated'] != null
          ? DateTime.parse(json['last_updated'])
          : null,
    );
  }
}

/// Model for a timeline event
class TimelineEvent {
  final String id;
  final DateTime timestamp;
  final String
  type; // 'alert', 'deployment', 'config_change', 'scaling', 'incident', 'recovery', 'agent_action'
  final String title;
  final String? description;
  final String severity; // 'critical', 'high', 'medium', 'low', 'info'
  final Map<String, dynamic>? metadata;
  final bool isCorrelatedToIncident;

  TimelineEvent({
    required this.id,
    required this.timestamp,
    required this.type,
    required this.title,
    this.description,
    this.severity = 'info',
    this.metadata,
    this.isCorrelatedToIncident = false,
  });

  factory TimelineEvent.fromJson(Map<String, dynamic> json) {
    return TimelineEvent(
      id: json['id'] ?? '',
      timestamp: DateTime.parse(json['timestamp']),
      type: json['type'] ?? 'info',
      title: json['title'] ?? '',
      description: json['description'],
      severity: json['severity'] ?? 'info',
      metadata: json['metadata'],
      isCorrelatedToIncident: json['is_correlated'] ?? false,
    );
  }
}

/// Model for the incident timeline
class IncidentTimelineData {
  final String incidentId;
  final String title;
  final DateTime startTime;
  final DateTime? endTime;
  final String status; // 'ongoing', 'mitigated', 'resolved'
  final List<TimelineEvent> events;
  final String? rootCause;
  final Duration? timeToDetect;
  final Duration? timeToMitigate;

  IncidentTimelineData({
    required this.incidentId,
    required this.title,
    required this.startTime,
    this.endTime,
    required this.status,
    required this.events,
    this.rootCause,
    this.timeToDetect,
    this.timeToMitigate,
  });

  factory IncidentTimelineData.fromJson(Map<String, dynamic> json) {
    return IncidentTimelineData(
      incidentId: json['incident_id'] ?? '',
      title: json['title'] ?? 'Incident',
      startTime: DateTime.parse(json['start_time']),
      endTime: json['end_time'] != null
          ? DateTime.parse(json['end_time'])
          : null,
      status: json['status'] ?? 'ongoing',
      events: (json['events'] as List? ?? [])
          .map((e) => TimelineEvent.fromJson(Map<String, dynamic>.from(e)))
          .toList(),
      rootCause: json['root_cause'],
      timeToDetect: json['ttd_seconds'] != null
          ? Duration(seconds: json['ttd_seconds'])
          : null,
      timeToMitigate: json['ttm_seconds'] != null
          ? Duration(seconds: json['ttm_seconds'])
          : null,
    );
  }
}

// =============================================================================
// Agent Trace / Graph Models
// =============================================================================

/// A single node in the flattened agent trace timeline.
class AgentTraceNode {
  final String spanId;
  final String? parentSpanId;
  final String name;
  final String kind; // agent_invocation, llm_call, tool_execution, sub_agent_delegation
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
      spanId: json['span_id'] ?? '',
      parentSpanId: json['parent_span_id'],
      name: json['name'] ?? '',
      kind: json['kind'] ?? 'unknown',
      operation: json['operation'] ?? 'unknown',
      startOffsetMs: (json['start_offset_ms'] as num?)?.toDouble() ?? 0,
      durationMs: (json['duration_ms'] as num?)?.toDouble() ?? 0,
      depth: (json['depth'] as num?)?.toInt() ?? 0,
      inputTokens: (json['input_tokens'] as num?)?.toInt(),
      outputTokens: (json['output_tokens'] as num?)?.toInt(),
      modelUsed: json['model_used'],
      toolName: json['tool_name'],
      agentName: json['agent_name'],
      hasError: json['has_error'] ?? false,
    );
  }
}

/// Data model for the agent trace timeline widget.
class AgentTraceData {
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
      traceId: json['trace_id'] ?? '',
      rootAgentName: json['root_agent_name'],
      nodes: (json['nodes'] as List? ?? [])
          .map((n) => AgentTraceNode.fromJson(Map<String, dynamic>.from(n)))
          .toList(),
      totalInputTokens: (json['total_input_tokens'] as num?)?.toInt() ?? 0,
      totalOutputTokens: (json['total_output_tokens'] as num?)?.toInt() ?? 0,
      totalDurationMs:
          (json['total_duration_ms'] as num?)?.toDouble() ?? 0,
      llmCallCount: (json['llm_call_count'] as num?)?.toInt() ?? 0,
      toolCallCount: (json['tool_call_count'] as num?)?.toInt() ?? 0,
      uniqueAgents: (json['unique_agents'] as List? ?? [])
          .map((e) => e.toString())
          .toList(),
      uniqueTools: (json['unique_tools'] as List? ?? [])
          .map((e) => e.toString())
          .toList(),
      antiPatterns: (json['anti_patterns'] as List? ?? [])
          .map((e) => Map<String, dynamic>.from(e as Map))
          .toList(),
    );
  }
}

/// A node in the agent dependency graph.
class AgentGraphNode {
  final String id;
  final String label;
  final String type; // user, agent, tool, llm_model, sub_agent
  final int? totalTokens;
  final int? callCount;
  final bool hasError;

  AgentGraphNode({
    required this.id,
    required this.label,
    required this.type,
    this.totalTokens,
    this.callCount,
    required this.hasError,
  });

  factory AgentGraphNode.fromJson(Map<String, dynamic> json) {
    return AgentGraphNode(
      id: json['id'] ?? '',
      label: json['label'] ?? '',
      type: json['type'] ?? 'unknown',
      totalTokens: (json['total_tokens'] as num?)?.toInt(),
      callCount: (json['call_count'] as num?)?.toInt(),
      hasError: json['has_error'] ?? false,
    );
  }
}

/// An edge in the agent dependency graph.
class AgentGraphEdge {
  final String sourceId;
  final String targetId;
  final String label; // invokes, calls, delegates_to, generates
  final int callCount;
  final double avgDurationMs;
  final int? totalTokens;
  final bool hasError;

  AgentGraphEdge({
    required this.sourceId,
    required this.targetId,
    required this.label,
    required this.callCount,
    required this.avgDurationMs,
    this.totalTokens,
    required this.hasError,
  });

  factory AgentGraphEdge.fromJson(Map<String, dynamic> json) {
    return AgentGraphEdge(
      sourceId: json['source_id'] ?? '',
      targetId: json['target_id'] ?? '',
      label: json['label'] ?? '',
      callCount: (json['call_count'] as num?)?.toInt() ?? 0,
      avgDurationMs: (json['avg_duration_ms'] as num?)?.toDouble() ?? 0,
      totalTokens: (json['total_tokens'] as num?)?.toInt(),
      hasError: json['has_error'] ?? false,
    );
  }
}

/// Data model for the agent dependency graph widget.
class AgentGraphData {
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
          .map((n) => AgentGraphNode.fromJson(Map<String, dynamic>.from(n)))
          .toList(),
      edges: (json['edges'] as List? ?? [])
          .map((e) => AgentGraphEdge.fromJson(Map<String, dynamic>.from(e)))
          .toList(),
      rootAgentName: json['root_agent_name'],
    );
  }
}

// =============================================================================
// Council Agent Activity Tracking Models
// =============================================================================

/// Enum for agent types in the council hierarchy.
enum CouncilAgentType {
  root,
  orchestrator,
  panel,
  critic,
  synthesizer,
  subAgent;

  static CouncilAgentType fromString(String value) {
    switch (value.toLowerCase()) {
      case 'root':
        return CouncilAgentType.root;
      case 'orchestrator':
        return CouncilAgentType.orchestrator;
      case 'panel':
        return CouncilAgentType.panel;
      case 'critic':
        return CouncilAgentType.critic;
      case 'synthesizer':
        return CouncilAgentType.synthesizer;
      case 'sub_agent':
      case 'subagent':
        return CouncilAgentType.subAgent;
      default:
        return CouncilAgentType.subAgent;
    }
  }

  String get displayName {
    switch (this) {
      case CouncilAgentType.root:
        return 'Root Agent';
      case CouncilAgentType.orchestrator:
        return 'Orchestrator';
      case CouncilAgentType.panel:
        return 'Expert Panel';
      case CouncilAgentType.critic:
        return 'Critic';
      case CouncilAgentType.synthesizer:
        return 'Synthesizer';
      case CouncilAgentType.subAgent:
        return 'Sub-Agent';
    }
  }
}

/// Record of a single tool call made by an agent.
class ToolCallRecord {
  final String callId;
  final String toolName;
  final String argsSummary;
  final String resultSummary;
  final String status; // pending, completed, error
  final int durationMs;
  final String timestamp;
  final String? dashboardCategory; // traces, metrics, logs, alerts, etc.

  ToolCallRecord({
    required this.callId,
    required this.toolName,
    this.argsSummary = '',
    this.resultSummary = '',
    this.status = 'completed',
    this.durationMs = 0,
    this.timestamp = '',
    this.dashboardCategory,
  });

  factory ToolCallRecord.fromJson(Map<String, dynamic> json) {
    return ToolCallRecord(
      callId: json['call_id'] ?? '',
      toolName: json['tool_name'] ?? '',
      argsSummary: json['args_summary'] ?? '',
      resultSummary: json['result_summary'] ?? '',
      status: json['status'] ?? 'completed',
      durationMs: (json['duration_ms'] as num?)?.toInt() ?? 0,
      timestamp: json['timestamp'] ?? '',
      dashboardCategory: json['dashboard_category'],
    );
  }

  bool get isError => status == 'error';
  bool get isPending => status == 'pending';
  bool get isCompleted => status == 'completed';
  bool get hasDashboardData => dashboardCategory != null;
}

/// Record of an LLM inference call made by an agent.
class LLMCallRecord {
  final String callId;
  final String model;
  final int inputTokens;
  final int outputTokens;
  final int durationMs;
  final String timestamp;

  LLMCallRecord({
    required this.callId,
    required this.model,
    this.inputTokens = 0,
    this.outputTokens = 0,
    this.durationMs = 0,
    this.timestamp = '',
  });

  factory LLMCallRecord.fromJson(Map<String, dynamic> json) {
    return LLMCallRecord(
      callId: json['call_id'] ?? '',
      model: json['model'] ?? '',
      inputTokens: (json['input_tokens'] as num?)?.toInt() ?? 0,
      outputTokens: (json['output_tokens'] as num?)?.toInt() ?? 0,
      durationMs: (json['duration_ms'] as num?)?.toInt() ?? 0,
      timestamp: json['timestamp'] ?? '',
    );
  }

  int get totalTokens => inputTokens + outputTokens;
}

/// Activity record for a single agent in the council hierarchy.
class CouncilAgentActivity {
  final String agentId;
  final String agentName;
  final CouncilAgentType agentType;
  final String? parentId;
  final String status; // pending, running, completed, error
  final String startedAt;
  final String completedAt;
  final List<ToolCallRecord> toolCalls;
  final List<LLMCallRecord> llmCalls;
  final String outputSummary;

  CouncilAgentActivity({
    required this.agentId,
    required this.agentName,
    required this.agentType,
    this.parentId,
    this.status = 'pending',
    this.startedAt = '',
    this.completedAt = '',
    this.toolCalls = const [],
    this.llmCalls = const [],
    this.outputSummary = '',
  });

  factory CouncilAgentActivity.fromJson(Map<String, dynamic> json) {
    return CouncilAgentActivity(
      agentId: json['agent_id'] ?? '',
      agentName: json['agent_name'] ?? '',
      agentType: CouncilAgentType.fromString(json['agent_type'] ?? 'sub_agent'),
      parentId: json['parent_id'],
      status: json['status'] ?? 'pending',
      startedAt: json['started_at'] ?? '',
      completedAt: json['completed_at'] ?? '',
      toolCalls: (json['tool_calls'] as List? ?? [])
          .map((t) => ToolCallRecord.fromJson(Map<String, dynamic>.from(t)))
          .toList(),
      llmCalls: (json['llm_calls'] as List? ?? [])
          .map((l) => LLMCallRecord.fromJson(Map<String, dynamic>.from(l)))
          .toList(),
      outputSummary: json['output_summary'] ?? '',
    );
  }

  bool get isRoot => parentId == null;
  bool get isRunning => status == 'running';
  bool get isCompleted => status == 'completed';
  bool get hasError => status == 'error';

  int get totalToolCalls => toolCalls.length;
  int get totalLLMCalls => llmCalls.length;
  int get errorCount => toolCalls.where((t) => t.isError).length;

  /// Get tool calls that produced dashboard data for a specific category.
  List<ToolCallRecord> getToolCallsForCategory(String category) {
    return toolCalls.where((t) => t.dashboardCategory == category).toList();
  }

  /// Get the display icon for this agent type.
  String get iconName {
    switch (agentType) {
      case CouncilAgentType.root:
        return 'account_tree';
      case CouncilAgentType.orchestrator:
        return 'hub';
      case CouncilAgentType.panel:
        return 'psychology';
      case CouncilAgentType.critic:
        return 'forum';
      case CouncilAgentType.synthesizer:
        return 'summarize';
      case CouncilAgentType.subAgent:
        return 'smart_toy';
    }
  }
}

/// Complete activity graph for a council investigation.
class CouncilActivityGraph {
  final String investigationId;
  final String mode;
  final String startedAt;
  final String completedAt;
  final List<CouncilAgentActivity> agents;
  final int totalToolCalls;
  final int totalLLMCalls;
  final int debateRounds;

  CouncilActivityGraph({
    required this.investigationId,
    required this.mode,
    required this.startedAt,
    this.completedAt = '',
    this.agents = const [],
    this.totalToolCalls = 0,
    this.totalLLMCalls = 0,
    this.debateRounds = 1,
  });

  factory CouncilActivityGraph.fromJson(Map<String, dynamic> json) {
    final agents = (json['agents'] as List? ?? [])
        .map((a) => CouncilAgentActivity.fromJson(Map<String, dynamic>.from(a)))
        .toList();

    return CouncilActivityGraph(
      investigationId: json['investigation_id'] ?? '',
      mode: json['mode'] ?? 'standard',
      startedAt: json['started_at'] ?? '',
      completedAt: json['completed_at'] ?? '',
      agents: agents,
      totalToolCalls: (json['total_tool_calls'] as num?)?.toInt() ??
          agents.fold(0, (sum, a) => sum + a.totalToolCalls),
      totalLLMCalls: (json['total_llm_calls'] as num?)?.toInt() ??
          agents.fold(0, (sum, a) => sum + a.totalLLMCalls),
      debateRounds: (json['debate_rounds'] as num?)?.toInt() ?? 1,
    );
  }

  /// Find an agent by its ID.
  CouncilAgentActivity? getAgentById(String agentId) {
    try {
      return agents.firstWhere((a) => a.agentId == agentId);
    } catch (_) {
      return null;
    }
  }

  /// Get all direct children of an agent.
  List<CouncilAgentActivity> getChildren(String parentId) {
    return agents.where((a) => a.parentId == parentId).toList();
  }

  /// Get root agents (no parent).
  List<CouncilAgentActivity> get rootAgents {
    return agents.where((a) => a.isRoot).toList();
  }

  /// Get all panel agents.
  List<CouncilAgentActivity> get panelAgents {
    return agents.where((a) => a.agentType == CouncilAgentType.panel).toList();
  }

  /// Get the critic agent if present.
  CouncilAgentActivity? get criticAgent {
    try {
      return agents.firstWhere((a) => a.agentType == CouncilAgentType.critic);
    } catch (_) {
      return null;
    }
  }

  /// Get the synthesizer agent if present.
  CouncilAgentActivity? get synthesizerAgent {
    try {
      return agents
          .firstWhere((a) => a.agentType == CouncilAgentType.synthesizer);
    } catch (_) {
      return null;
    }
  }

  /// Get all tool calls across all agents, sorted by timestamp.
  List<ToolCallRecord> get allToolCallsSorted {
    final allCalls = agents.expand((a) => a.toolCalls).toList();
    allCalls.sort((a, b) => a.timestamp.compareTo(b.timestamp));
    return allCalls;
  }

  /// Get tool calls that produced dashboard data.
  Map<String, List<ToolCallRecord>> get toolCallsByDashboardCategory {
    final Map<String, List<ToolCallRecord>> result = {};
    for (final agent in agents) {
      for (final call in agent.toolCalls) {
        if (call.dashboardCategory != null) {
          result.putIfAbsent(call.dashboardCategory!, () => []).add(call);
        }
      }
    }
    return result;
  }
}
