import 'dart:convert';

import 'package:flutter/foundation.dart';

/// Represents a finding from a specialist panel in the council.
final class PanelFinding {
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
      evidence:
          (json['evidence'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      recommendedActions:
          (json['recommended_actions'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
    );
  }

  /// Returns the display name for the panel
  String get displayName => switch (panel.toLowerCase()) {
    'trace' => 'Trace Analysis',
    'metrics' => 'Metrics Analysis',
    'logs' => 'Logs Analysis',
    'alerts' => 'Alerts Analysis',
    _ => panel,
  };

  /// Returns the icon name for the panel
  String get iconName => switch (panel.toLowerCase()) {
    'trace' => 'timeline',
    'metrics' => 'analytics',
    'logs' => 'description',
    'alerts' => 'notifications_active',
    _ => 'help',
  };

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is PanelFinding &&
          runtimeType == other.runtimeType &&
          panel == other.panel &&
          summary == other.summary &&
          severity == other.severity &&
          confidence == other.confidence &&
          listEquals(evidence, other.evidence) &&
          listEquals(recommendedActions, other.recommendedActions);

  @override
  int get hashCode => Object.hash(
    panel,
    summary,
    severity,
    confidence,
    evidence.length,
    recommendedActions.length,
  );
}

/// Represents a critic's cross-examination report in debate mode.
final class CriticReport {
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
      agreements:
          (json['agreements'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      contradictions:
          (json['contradictions'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      gaps:
          (json['gaps'] as List<dynamic>?)?.map((e) => e.toString()).toList() ??
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

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is CriticReport &&
          runtimeType == other.runtimeType &&
          listEquals(agreements, other.agreements) &&
          listEquals(contradictions, other.contradictions) &&
          listEquals(gaps, other.gaps) &&
          revisedConfidence == other.revisedConfidence;

  @override
  int get hashCode => Object.hash(
    agreements.length,
    contradictions.length,
    gaps.length,
    revisedConfidence,
  );
}

/// Represents a Vega-Lite chart returned by the CA Data Agent.
final class VegaChartData {
  final String question;
  final String answer;
  final String? agentId;
  final String? projectId;
  final List<Map<String, dynamic>> vegaLiteCharts;

  VegaChartData({
    required this.question,
    required this.answer,
    this.agentId,
    this.projectId,
    this.vegaLiteCharts = const [],
  });

  factory VegaChartData.fromJson(Map<String, dynamic> json) {
    return VegaChartData(
      question: json['question'] as String? ?? '',
      answer: json['answer'] as String? ?? '',
      agentId: json['agent_id'] as String?,
      projectId: json['project_id'] as String?,
      vegaLiteCharts: (json['vega_lite_charts'] as List? ?? [])
          .whereType<Map>()
          .map((c) => Map<String, dynamic>.from(c))
          .toList(),
    );
  }

  bool get hasCharts => vegaLiteCharts.isNotEmpty;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is VegaChartData &&
          runtimeType == other.runtimeType &&
          question == other.question &&
          answer == other.answer &&
          agentId == other.agentId &&
          projectId == other.projectId &&
          vegaLiteCharts.length == other.vegaLiteCharts.length;

  @override
  int get hashCode =>
      Object.hash(question, answer, agentId, projectId, vegaLiteCharts.length);
}

// =============================================================================
// Council Agent Activity Tracking Models
// =============================================================================

/// Enum for agent types in the council hierarchy.
///
/// Each variant carries its own [displayName] and [iconName], eliminating the
/// need for separate switch statements when rendering UI.
enum CouncilAgentType {
  root('Root Agent', 'account_tree'),
  orchestrator('Orchestrator', 'hub'),
  panel('Expert Panel', 'psychology'),
  critic('Critic', 'forum'),
  synthesizer('Synthesizer', 'summarize'),
  subAgent('Sub-Agent', 'smart_toy');

  /// Human-readable label shown in the UI.
  final String displayName;

  /// Material icon name used for this agent type.
  final String iconName;

  const CouncilAgentType(this.displayName, this.iconName);

  static CouncilAgentType fromString(String value) =>
      switch (value.toLowerCase()) {
        'root' => root,
        'orchestrator' => orchestrator,
        'panel' => panel,
        'critic' => critic,
        'synthesizer' => synthesizer,
        'sub_agent' || 'subagent' => subAgent,
        _ => subAgent,
      };
}

/// Record of a single tool call made by an agent.
final class ToolCallRecord {
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
      callId: json['call_id'] as String? ?? '',
      toolName: json['tool_name'] as String? ?? '',
      argsSummary: json['args_summary'] as String? ?? '',
      resultSummary: json['result_summary'] as String? ?? '',
      status: json['status'] as String? ?? 'completed',
      durationMs: (json['duration_ms'] as num?)?.toInt() ?? 0,
      timestamp: json['timestamp'] as String? ?? '',
      dashboardCategory: json['dashboard_category'] as String?,
    );
  }

  bool get isError => status == 'error';
  bool get isPending => status == 'pending';
  bool get isCompleted => status == 'completed';
  bool get hasDashboardData => dashboardCategory != null;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is ToolCallRecord &&
          runtimeType == other.runtimeType &&
          callId == other.callId &&
          toolName == other.toolName &&
          argsSummary == other.argsSummary &&
          resultSummary == other.resultSummary &&
          status == other.status &&
          durationMs == other.durationMs &&
          timestamp == other.timestamp &&
          dashboardCategory == other.dashboardCategory;

  @override
  int get hashCode => Object.hash(
    callId,
    toolName,
    status,
    durationMs,
    timestamp,
    dashboardCategory,
  );
}

/// Record of an LLM inference call made by an agent.
final class LLMCallRecord {
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
      callId: json['call_id'] as String? ?? '',
      model: json['model'] as String? ?? '',
      inputTokens: (json['input_tokens'] as num?)?.toInt() ?? 0,
      outputTokens: (json['output_tokens'] as num?)?.toInt() ?? 0,
      durationMs: (json['duration_ms'] as num?)?.toInt() ?? 0,
      timestamp: json['timestamp'] as String? ?? '',
    );
  }

  int get totalTokens => inputTokens + outputTokens;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is LLMCallRecord &&
          runtimeType == other.runtimeType &&
          callId == other.callId &&
          model == other.model &&
          inputTokens == other.inputTokens &&
          outputTokens == other.outputTokens &&
          durationMs == other.durationMs &&
          timestamp == other.timestamp;

  @override
  int get hashCode => Object.hash(
    callId,
    model,
    inputTokens,
    outputTokens,
    durationMs,
    timestamp,
  );
}

/// Activity record for a single agent in the council hierarchy.
final class CouncilAgentActivity {
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
      agentId: json['agent_id'] as String? ?? '',
      agentName: json['agent_name'] as String? ?? '',
      agentType: CouncilAgentType.fromString(
        json['agent_type'] as String? ?? 'sub_agent',
      ),
      parentId: json['parent_id'] as String?,
      status: json['status'] as String? ?? 'pending',
      startedAt: json['started_at'] as String? ?? '',
      completedAt: json['completed_at'] as String? ?? '',
      toolCalls: (json['tool_calls'] as List? ?? [])
          .whereType<Map>()
          .map((t) => ToolCallRecord.fromJson(Map<String, dynamic>.from(t)))
          .toList(),
      llmCalls: (json['llm_calls'] as List? ?? [])
          .whereType<Map>()
          .map((l) => LLMCallRecord.fromJson(Map<String, dynamic>.from(l)))
          .toList(),
      outputSummary: json['output_summary'] as String? ?? '',
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
  String get iconName => agentType.iconName;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is CouncilAgentActivity &&
          runtimeType == other.runtimeType &&
          agentId == other.agentId &&
          agentName == other.agentName &&
          agentType == other.agentType &&
          parentId == other.parentId &&
          status == other.status &&
          startedAt == other.startedAt &&
          completedAt == other.completedAt &&
          listEquals(toolCalls, other.toolCalls) &&
          listEquals(llmCalls, other.llmCalls) &&
          outputSummary == other.outputSummary;

  @override
  int get hashCode => Object.hash(
    agentId,
    agentName,
    agentType,
    parentId,
    status,
    startedAt,
    completedAt,
    toolCalls.length,
    llmCalls.length,
    outputSummary,
  );
}

/// Complete activity graph for a council investigation.
final class CouncilActivityGraph {
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
        .whereType<Map>()
        .map((a) => CouncilAgentActivity.fromJson(Map<String, dynamic>.from(a)))
        .toList();

    return CouncilActivityGraph(
      investigationId: json['investigation_id'] as String? ?? '',
      mode: json['mode'] as String? ?? 'standard',
      startedAt: json['started_at'] as String? ?? '',
      completedAt: json['completed_at'] as String? ?? '',
      agents: agents,
      totalToolCalls:
          (json['total_tool_calls'] as num?)?.toInt() ??
          agents.fold(0, (sum, a) => sum + a.totalToolCalls),
      totalLLMCalls:
          (json['total_llm_calls'] as num?)?.toInt() ??
          agents.fold(0, (sum, a) => sum + a.totalLLMCalls),
      debateRounds: (json['debate_rounds'] as num?)?.toInt() ?? 1,
    );
  }

  /// Find an agent by its ID.
  CouncilAgentActivity? getAgentById(String agentId) {
    for (final a in agents) {
      if (a.agentId == agentId) return a;
    }
    return null;
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
    for (final a in agents) {
      if (a.agentType == CouncilAgentType.critic) return a;
    }
    return null;
  }

  /// Get the synthesizer agent if present.
  CouncilAgentActivity? get synthesizerAgent {
    for (final a in agents) {
      if (a.agentType == CouncilAgentType.synthesizer) return a;
    }
    return null;
  }

  /// Get all tool calls across all agents, sorted by timestamp.
  List<ToolCallRecord> get allToolCallsSorted {
    final allCalls = agents.expand((a) => a.toolCalls).toList();
    allCalls.sort((a, b) => a.timestamp.compareTo(b.timestamp));
    return allCalls;
  }

  /// Get tool calls that produced dashboard data.
  Map<String, List<ToolCallRecord>> get toolCallsByDashboardCategory {
    final result = <String, List<ToolCallRecord>>{};
    for (final agent in agents) {
      for (final call in agent.toolCalls) {
        if (call.dashboardCategory != null) {
          result.putIfAbsent(call.dashboardCategory!, () => []).add(call);
        }
      }
    }
    return result;
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is CouncilActivityGraph &&
          runtimeType == other.runtimeType &&
          investigationId == other.investigationId &&
          mode == other.mode &&
          startedAt == other.startedAt &&
          completedAt == other.completedAt &&
          listEquals(agents, other.agents) &&
          totalToolCalls == other.totalToolCalls &&
          totalLLMCalls == other.totalLLMCalls &&
          debateRounds == other.debateRounds;

  @override
  int get hashCode => Object.hash(
    investigationId,
    mode,
    startedAt,
    completedAt,
    agents.length,
    totalToolCalls,
    totalLLMCalls,
    debateRounds,
  );
}

/// Represents a council investigation synthesis result.
final class CouncilSynthesisData {
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
    var data = json.containsKey('result') && json['result'] is Map
        ? Map<String, dynamic>.from(json['result'] as Map)
        : json;

    var synthesis = data['synthesis'] as String? ?? '';

    // If synthesis contains a markdown JSON block, try to parse it
    if (synthesis.contains('```json')) {
      try {
        final start = synthesis.indexOf('```json') + 7;
        final end = synthesis.lastIndexOf('```');
        if (end > start) {
          final jsonStr = synthesis.substring(start, end).trim();
          final nestedData = jsonDecode(jsonStr) as Map<String, dynamic>;

          if (nestedData.containsKey('synthesis')) {
            synthesis = nestedData['synthesis'] as String? ?? synthesis;
          }

          if ((data['panels'] == null || (data['panels'] as List).isEmpty) &&
              nestedData['panels'] != null) {
            data['panels'] = nestedData['panels'];
          }

          if (data['overall_severity'] == null ||
              data['overall_severity'] == 'info') {
            data['overall_severity'] = nestedData['overall_severity'];
          }

          if (data['overall_confidence'] == null ||
              (data['overall_confidence'] as num?) == 0) {
            data['overall_confidence'] = nestedData['overall_confidence'];
          }

          if (data['mode'] == null || data['mode'] == 'standard') {
            data['mode'] = nestedData['mode'];
          }

          if (data['rounds'] == null || (data['rounds'] as num?) == 1) {
            data['rounds'] = nestedData['rounds'];
          }
        }
      } catch (_) {
        // Fallback to original synthesis if parsing fails
      }
    }

    // Parse panels (Dart 3 if-case pattern)
    final panels = switch (data['panels']) {
      List list =>
        list
            .whereType<Map>()
            .map((p) => PanelFinding.fromJson(Map<String, dynamic>.from(p)))
            .toList(),
      _ => <PanelFinding>[],
    };

    // Parse critic report (Dart 3 if-case pattern)
    final criticReport = switch (data['critic_report']) {
      Map m => CriticReport.fromJson(Map<String, dynamic>.from(m)),
      _ => null,
    };

    // Parse activity graph (Dart 3 if-case pattern)
    final activityGraph = switch (data['activity_graph']) {
      Map m => CouncilActivityGraph.fromJson(Map<String, dynamic>.from(m)),
      _ => null,
    };

    return CouncilSynthesisData(
      synthesis: synthesis,
      overallSeverity: data['overall_severity'] as String? ?? 'info',
      overallConfidence:
          (data['overall_confidence'] as num?)?.toDouble() ?? 0.0,
      mode: data['mode'] as String? ?? 'standard',
      rounds: (data['rounds'] as num?)?.toInt() ?? 1,
      panels: panels,
      criticReport: criticReport,
      activityGraph: activityGraph,
      rawData: json,
    );
  }

  CouncilSynthesisData copyWith({
    String? synthesis,
    String? overallSeverity,
    double? overallConfidence,
    String? mode,
    int? rounds,
    List<PanelFinding>? panels,
    CriticReport? criticReport,
    CouncilActivityGraph? activityGraph,
    Map<String, dynamic>? rawData,
  }) {
    return CouncilSynthesisData(
      synthesis: synthesis ?? this.synthesis,
      overallSeverity: overallSeverity ?? this.overallSeverity,
      overallConfidence: overallConfidence ?? this.overallConfidence,
      mode: mode ?? this.mode,
      rounds: rounds ?? this.rounds,
      panels: panels ?? this.panels,
      criticReport: criticReport ?? this.criticReport,
      activityGraph: activityGraph ?? this.activityGraph,
      rawData: rawData ?? this.rawData,
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
    final lower = type.toLowerCase();
    for (final p in panels) {
      if (p.panel.toLowerCase() == lower) return p;
    }
    return null;
  }

  /// Get total tool calls from activity graph
  int get totalToolCalls => activityGraph?.totalToolCalls ?? 0;

  /// Get total LLM calls from activity graph
  int get totalLLMCalls => activityGraph?.totalLLMCalls ?? 0;

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is CouncilSynthesisData &&
          runtimeType == other.runtimeType &&
          synthesis == other.synthesis &&
          overallSeverity == other.overallSeverity &&
          overallConfidence == other.overallConfidence &&
          mode == other.mode &&
          rounds == other.rounds &&
          listEquals(panels, other.panels) &&
          criticReport == other.criticReport &&
          activityGraph == other.activityGraph;

  @override
  int get hashCode => Object.hash(
    synthesis,
    overallSeverity,
    overallConfidence,
    mode,
    rounds,
    panels.length,
    criticReport,
    activityGraph,
  );
}
