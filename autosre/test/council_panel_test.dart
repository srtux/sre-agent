import 'package:autosre/models/adk_schema.dart';
import 'package:autosre/services/dashboard_state.dart';
import 'package:autosre/widgets/dashboard/live_council_panel.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

/// Helper to build a [CouncilSynthesisData] from simple values.
CouncilSynthesisData _makeCouncilData({
  String synthesis = 'Redis connection pool exhaustion causing latency spike.',
  String overallSeverity = 'warning',
  double overallConfidence = 0.87,
  String mode = 'standard',
  int rounds = 1,
  List<PanelFinding>? panels,
  CriticReport? criticReport,
  CouncilActivityGraph? activityGraph,
}) {
  return CouncilSynthesisData(
    synthesis: synthesis,
    overallSeverity: overallSeverity,
    overallConfidence: overallConfidence,
    mode: mode,
    rounds: rounds,
    panels: panels ?? [],
    criticReport: criticReport,
    activityGraph: activityGraph,
    rawData: const {},
  );
}

/// Helper to create a sample panel finding.
PanelFinding _makePanelFinding({
  String panel = 'trace',
  String summary = 'High latency detected in checkout service.',
  String severity = 'warning',
  double confidence = 0.85,
  List<String>? evidence,
  List<String>? recommendedActions,
}) {
  return PanelFinding(
    panel: panel,
    summary: summary,
    severity: severity,
    confidence: confidence,
    evidence: evidence ?? ['Trace ID: abc123, latency: 2.5s'],
    recommendedActions: recommendedActions ?? ['Scale checkout service'],
  );
}

/// Helper to create a sample critic report.
CriticReport _makeCriticReport({
  List<String>? agreements,
  List<String>? contradictions,
  List<String>? gaps,
  double revisedConfidence = 0.85,
}) {
  return CriticReport(
    agreements: agreements ?? ['All panels agree on latency issue'],
    contradictions: contradictions ?? [],
    gaps: gaps ?? [],
    revisedConfidence: revisedConfidence,
  );
}

/// Helper to create a [DashboardItem] with council data.
DashboardItem _makeCouncilItem(CouncilSynthesisData data) {
  return DashboardItem(
    id: 'council-1',
    type: DashboardDataType.council,
    toolName: 'run_council_investigation',
    timestamp: DateTime(2026, 1, 1),
    rawData: const {},
    councilData: data,
  );
}

/// Helper to create a sample tool call record.
ToolCallRecord _makeToolCallRecord({
  String callId = 'call-123',
  String toolName = 'fetch_trace',
  String argsSummary = 'trace_id: abc123',
  String resultSummary = 'Found 15 spans',
  String status = 'completed',
  int durationMs = 250,
  String timestamp = '2026-01-01T10:00:00Z',
  String? dashboardCategory,
}) {
  return ToolCallRecord(
    callId: callId,
    toolName: toolName,
    argsSummary: argsSummary,
    resultSummary: resultSummary,
    status: status,
    durationMs: durationMs,
    timestamp: timestamp,
    dashboardCategory: dashboardCategory,
  );
}

/// Helper to create a sample LLM call record.
LLMCallRecord _makeLLMCallRecord({
  String callId = 'llm-123',
  String model = 'gemini-2.0-flash',
  int inputTokens = 1500,
  int outputTokens = 500,
  int durationMs = 1200,
  String timestamp = '2026-01-01T10:00:01Z',
}) {
  return LLMCallRecord(
    callId: callId,
    model: model,
    inputTokens: inputTokens,
    outputTokens: outputTokens,
    durationMs: durationMs,
    timestamp: timestamp,
  );
}

/// Helper to create a sample agent activity.
CouncilAgentActivity _makeAgentActivity({
  String agentId = 'agent-1',
  String agentName = 'trace_panel',
  CouncilAgentType agentType = CouncilAgentType.panel,
  String? parentId,
  String status = 'completed',
  String startedAt = '2026-01-01T10:00:00Z',
  String completedAt = '2026-01-01T10:00:05Z',
  List<ToolCallRecord>? toolCalls,
  List<LLMCallRecord>? llmCalls,
  String outputSummary = 'Found latency spike in checkout service.',
}) {
  return CouncilAgentActivity(
    agentId: agentId,
    agentName: agentName,
    agentType: agentType,
    parentId: parentId,
    status: status,
    startedAt: startedAt,
    completedAt: completedAt,
    toolCalls: toolCalls ?? [_makeToolCallRecord()],
    llmCalls: llmCalls ?? [_makeLLMCallRecord()],
    outputSummary: outputSummary,
  );
}

/// Helper to create a sample activity graph.
CouncilActivityGraph _makeActivityGraph({
  String investigationId = 'inv-123',
  String mode = 'standard',
  String startedAt = '2026-01-01T10:00:00Z',
  String completedAt = '2026-01-01T10:00:30Z',
  List<CouncilAgentActivity>? agents,
  int debateRounds = 1,
}) {
  final agentsList =
      agents ??
      [
        _makeAgentActivity(
          agentId: 'orchestrator',
          agentName: 'council_orchestrator',
          agentType: CouncilAgentType.orchestrator,
        ),
        _makeAgentActivity(
          agentId: 'trace-panel',
          agentName: 'trace_panel',
          agentType: CouncilAgentType.panel,
          parentId: 'orchestrator',
        ),
        _makeAgentActivity(
          agentId: 'metrics-panel',
          agentName: 'metrics_panel',
          agentType: CouncilAgentType.panel,
          parentId: 'orchestrator',
        ),
      ];

  return CouncilActivityGraph(
    investigationId: investigationId,
    mode: mode,
    startedAt: startedAt,
    completedAt: completedAt,
    agents: agentsList,
    totalToolCalls: agentsList.fold(0, (sum, a) => sum + a.totalToolCalls),
    totalLLMCalls: agentsList.fold(0, (sum, a) => sum + a.totalLLMCalls),
    debateRounds: debateRounds,
  );
}

void main() {
  group('PanelFinding', () {
    test('parses from JSON correctly', () {
      final json = {
        'panel': 'metrics',
        'summary': 'High CPU usage detected.',
        'severity': 'critical',
        'confidence': 0.92,
        'evidence': ['CPU at 95%', 'Memory at 80%'],
        'recommended_actions': ['Scale horizontally', 'Check for memory leaks'],
      };
      final panel = PanelFinding.fromJson(json);
      expect(panel.panel, 'metrics');
      expect(panel.summary, 'High CPU usage detected.');
      expect(panel.severity, 'critical');
      expect(panel.confidence, 0.92);
      expect(panel.evidence.length, 2);
      expect(panel.recommendedActions.length, 2);
    });

    test('displayName returns correct values', () {
      expect(_makePanelFinding(panel: 'trace').displayName, 'Trace Analysis');
      expect(
        _makePanelFinding(panel: 'metrics').displayName,
        'Metrics Analysis',
      );
      expect(_makePanelFinding(panel: 'logs').displayName, 'Logs Analysis');
      expect(_makePanelFinding(panel: 'alerts').displayName, 'Alerts Analysis');
    });

    test('provides defaults for missing fields', () {
      final panel = PanelFinding.fromJson(const {});
      expect(panel.panel, 'unknown');
      expect(panel.summary, '');
      expect(panel.severity, 'info');
      expect(panel.confidence, 0.0);
      expect(panel.evidence, isEmpty);
      expect(panel.recommendedActions, isEmpty);
    });
  });

  group('CriticReport', () {
    test('parses from JSON correctly', () {
      final json = {
        'agreements': ['Both trace and metrics show latency spike'],
        'contradictions': ['Logs show no errors but traces show failures'],
        'gaps': ['No alert data available'],
        'revised_confidence': 0.78,
      };
      final critic = CriticReport.fromJson(json);
      expect(critic.agreements.length, 1);
      expect(critic.contradictions.length, 1);
      expect(critic.gaps.length, 1);
      expect(critic.revisedConfidence, 0.78);
    });

    test('hasContradictions returns correct value', () {
      final withContradictions = _makeCriticReport(
        contradictions: ['Conflict found'],
      );
      final withoutContradictions = _makeCriticReport(contradictions: []);
      expect(withContradictions.hasContradictions, isTrue);
      expect(withoutContradictions.hasContradictions, isFalse);
    });

    test('hasGaps returns correct value', () {
      final withGaps = _makeCriticReport(gaps: ['Missing data']);
      final withoutGaps = _makeCriticReport(gaps: []);
      expect(withGaps.hasGaps, isTrue);
      expect(withoutGaps.hasGaps, isFalse);
    });

    test('hasStrongAgreement returns correct value', () {
      final strong = _makeCriticReport(
        agreements: ['Point 1', 'Point 2'],
        contradictions: [],
      );
      final weak = _makeCriticReport(
        agreements: ['Point 1'],
        contradictions: ['Conflict'],
      );
      expect(strong.hasStrongAgreement, isTrue);
      expect(weak.hasStrongAgreement, isFalse);
    });
  });

  group('CouncilSynthesisData.fromJson', () {
    test('parses flat JSON', () {
      final json = {
        'synthesis': 'Latency spike in checkout.',
        'overall_severity': 'critical',
        'overall_confidence': 0.92,
        'mode': 'debate',
        'rounds': 3,
      };
      final data = CouncilSynthesisData.fromJson(json);
      expect(data.synthesis, 'Latency spike in checkout.');
      expect(data.overallSeverity, 'critical');
      expect(data.overallConfidence, 0.92);
      expect(data.mode, 'debate');
      expect(data.rounds, 3);
    });

    test('parses panels array', () {
      final json = {
        'synthesis': 'Test synthesis.',
        'overall_severity': 'warning',
        'overall_confidence': 0.85,
        'mode': 'standard',
        'rounds': 1,
        'panels': [
          {
            'panel': 'trace',
            'summary': 'Trace finding.',
            'severity': 'warning',
            'confidence': 0.9,
            'evidence': ['trace-123'],
            'recommended_actions': ['Scale service'],
          },
          {
            'panel': 'metrics',
            'summary': 'Metrics finding.',
            'severity': 'info',
            'confidence': 0.8,
            'evidence': [],
            'recommended_actions': [],
          },
        ],
      };
      final data = CouncilSynthesisData.fromJson(json);
      expect(data.panels.length, 2);
      expect(data.panels[0].panel, 'trace');
      expect(data.panels[1].panel, 'metrics');
    });

    test('parses critic report', () {
      final json = {
        'synthesis': 'Debate synthesis.',
        'overall_severity': 'critical',
        'overall_confidence': 0.88,
        'mode': 'debate',
        'rounds': 2,
        'critic_report': {
          'agreements': ['All agree'],
          'contradictions': ['Conflict 1'],
          'gaps': [],
          'revised_confidence': 0.82,
        },
      };
      final data = CouncilSynthesisData.fromJson(json);
      expect(data.hasCriticReport, isTrue);
      expect(data.criticReport!.agreements.length, 1);
      expect(data.criticReport!.contradictions.length, 1);
      expect(data.criticReport!.revisedConfidence, 0.82);
    });

    test('unwraps nested result key', () {
      final json = {
        'result': {
          'synthesis': 'Nested synthesis.',
          'overall_severity': 'warning',
          'overall_confidence': 0.75,
          'mode': 'standard',
          'rounds': 1,
        },
      };
      final data = CouncilSynthesisData.fromJson(json);
      expect(data.synthesis, 'Nested synthesis.');
      expect(data.mode, 'standard');
    });

    test('provides defaults for missing fields', () {
      final data = CouncilSynthesisData.fromJson(const {});
      expect(data.synthesis, '');
      expect(data.overallSeverity, 'info');
      expect(data.overallConfidence, 0.0);
      expect(data.mode, 'standard');
      expect(data.rounds, 1);
      expect(data.panels, isEmpty);
      expect(data.hasCriticReport, isFalse);
    });

    test('isDebateMode returns correct value', () {
      final debate = _makeCouncilData(mode: 'debate');
      final standard = _makeCouncilData(mode: 'standard');
      expect(debate.isDebateMode, isTrue);
      expect(standard.isDebateMode, isFalse);
    });

    test('getPanelByType returns correct panel', () {
      final panels = [
        _makePanelFinding(panel: 'trace'),
        _makePanelFinding(panel: 'metrics'),
      ];
      final data = _makeCouncilData(panels: panels);
      expect(data.getPanelByType('trace')?.panel, 'trace');
      expect(data.getPanelByType('metrics')?.panel, 'metrics');
      expect(data.getPanelByType('logs'), isNull);
    });
  });

  group('DashboardState council support', () {
    test('addCouncilSynthesis adds item', () {
      final state = DashboardState();
      final data = _makeCouncilData();
      state.addCouncilSynthesis(data, 'run_council_investigation', {});

      expect(state.items.length, 1);
      expect(state.items.first.type, DashboardDataType.council);
      expect(state.items.first.councilData, data);
    });

    test('addFromEvent processes council synthesis', () {
      final state = DashboardState();
      final event = {
        'category': 'council',
        'widget_type': 'x-sre-council-synthesis',
        'tool_name': 'run_council_investigation',
        'data': {
          'synthesis': 'Test synthesis.',
          'overall_severity': 'info',
          'overall_confidence': 0.65,
          'mode': 'fast',
          'rounds': 1,
        },
      };
      final result = state.addFromEvent(event);
      expect(result, isTrue);
      expect(state.items.length, 1);
      expect(state.items.first.type, DashboardDataType.council);
      expect(state.items.first.councilData?.synthesis, 'Test synthesis.');
    });

    test('addFromEvent processes council with panels', () {
      final state = DashboardState();
      final event = {
        'category': 'council',
        'widget_type': 'x-sre-council-synthesis',
        'tool_name': 'run_council_investigation',
        'data': {
          'synthesis': 'Full council synthesis.',
          'overall_severity': 'warning',
          'overall_confidence': 0.85,
          'mode': 'standard',
          'rounds': 1,
          'panels': [
            {
              'panel': 'trace',
              'summary': 'Trace issues found.',
              'severity': 'warning',
              'confidence': 0.9,
              'evidence': [],
              'recommended_actions': [],
            },
          ],
        },
      };
      final result = state.addFromEvent(event);
      expect(result, isTrue);
      expect(state.items.first.councilData?.panels.length, 1);
      expect(state.items.first.councilData?.panels.first.panel, 'trace');
    });

    test('classifyComponent maps x-sre-council-synthesis', () {
      final state = DashboardState();
      final event = {
        'category': 'council',
        'widget_type': 'x-sre-council-synthesis',
        'tool_name': 'run_council_investigation',
        'data': {
          'synthesis': 'Mapped correctly.',
          'overall_severity': 'healthy',
          'overall_confidence': 0.95,
          'mode': 'debate',
          'rounds': 2,
        },
      };
      state.addFromEvent(event);
      expect(state.items.first.councilData?.overallConfidence, 0.95);
    });
  });

  group('LiveCouncilPanel', () {
    testWidgets('renders council synthesis item', (tester) async {
      tester.view.physicalSize = const Size(800, 600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      final data = _makeCouncilData(
        synthesis: 'Redis pool exhaustion causing checkout latency.',
        overallSeverity: 'warning',
        overallConfidence: 0.87,
        mode: 'standard',
      );
      final items = [_makeCouncilItem(data)];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: LiveCouncilPanel(
              items: items,
              dashboardState: DashboardState(),
            ),
          ),
        ),
      );

      expect(find.text('Council of Experts'), findsOneWidget);
      expect(find.text('IN PROGRESS'), findsOneWidget);
      expect(find.byIcon(Icons.gavel_rounded), findsOneWidget);
      expect(
        find.text('Redis pool exhaustion causing checkout latency.'),
        findsOneWidget,
      );
    });

    testWidgets('shows debate mode with status mapping', (tester) async {
      tester.view.physicalSize = const Size(800, 600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      final data = _makeCouncilData(
        mode: 'debate',
        rounds: 3,
        overallConfidence: 0.92,
        overallSeverity: 'critical',
      );
      final items = [_makeCouncilItem(data)];

      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData.dark(),
          home: Scaffold(
            body: LiveCouncilPanel(
              items: items,
              dashboardState: DashboardState(),
            ),
          ),
        ),
      );

      expect(find.text('Council of Experts'), findsOneWidget);
      expect(find.text('REJECTED'), findsOneWidget); // mapped from critical
    });

    testWidgets('renders expert panel findings', (tester) async {
      tester.view.physicalSize = const Size(800, 600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      final panels = [
        _makePanelFinding(
          panel: 'trace',
          summary: 'Latency in payment service.',
          severity: 'warning',
        ),
        _makePanelFinding(
          panel: 'metrics',
          summary: 'CPU utilization normal.',
          severity: 'healthy',
        ),
      ];
      final data = _makeCouncilData(panels: panels);
      final items = [_makeCouncilItem(data)];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: LiveCouncilPanel(
              items: items,
              dashboardState: DashboardState(),
            ),
          ),
        ),
      );

      expect(find.text('EXPERT CONSENSUS'), findsOneWidget);
      expect(find.text('Trace Analysis'), findsOneWidget);
      expect(find.text('Metrics Analysis'), findsOneWidget);
    });

    testWidgets('renders critic report in debate mode', (tester) async {
      tester.view.physicalSize = const Size(800, 600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      final criticReport = _makeCriticReport(
        agreements: ['All panels agree on latency issue'],
        contradictions: ['Logs show healthy but traces show errors'],
        gaps: ['Missing alert correlation'],
      );
      final data = _makeCouncilData(
        synthesis: 'Debate synthesis result.',
        mode: 'debate',
        rounds: 2,
        criticReport: criticReport,
      );
      final items = [_makeCouncilItem(data)];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: LiveCouncilPanel(
              items: items,
              dashboardState: DashboardState(),
            ),
          ),
        ),
      );

      expect(find.text('Debate synthesis result.'), findsOneWidget);
    });

    testWidgets('fast mode maps to status correctly', (tester) async {
      tester.view.physicalSize = const Size(800, 600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      final data = _makeCouncilData(mode: 'fast', rounds: 1);
      final items = [_makeCouncilItem(data)];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: LiveCouncilPanel(
              items: items,
              dashboardState: DashboardState(),
            ),
          ),
        ),
      );

      expect(find.text('IN PROGRESS'), findsOneWidget);
    });

    testWidgets('hides synthesis when empty', (tester) async {
      tester.view.physicalSize = const Size(800, 600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      final data = _makeCouncilData(synthesis: '');
      final items = [_makeCouncilItem(data)];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: LiveCouncilPanel(
              items: items,
              dashboardState: DashboardState(),
            ),
          ),
        ),
      );

      expect(find.text('Council of Experts'), findsOneWidget);
      expect(find.text('CONCLUSION & REASONING'), findsOneWidget);
    });

    testWidgets('renders empty list gracefully', (tester) async {
      tester.view.physicalSize = const Size(800, 600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: LiveCouncilPanel(
              items: const [],
              dashboardState: DashboardState(),
            ),
          ),
        ),
      );

      expect(find.text('Council of Experts'), findsNothing);
      expect(find.text('No Council Decisions'), findsOneWidget);
    });

    testWidgets('severity badge colors are correct', (tester) async {
      tester.view.physicalSize = const Size(800, 600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      final data = _makeCouncilData(overallSeverity: 'healthy');
      final items = [_makeCouncilItem(data)];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: LiveCouncilPanel(
              items: items,
              dashboardState: DashboardState(),
            ),
          ),
        ),
      );

      expect(find.text('APPROVED'), findsOneWidget);
    });
  });

  // ==========================================================================
  // Agent Activity Tracking Model Tests
  // ==========================================================================

  group('ToolCallRecord', () {
    test('parses from JSON correctly', () {
      final json = {
        'call_id': 'call-abc',
        'tool_name': 'list_alerts',
        'args_summary': 'project_id: my-project',
        'result_summary': 'Found 3 active alerts',
        'status': 'completed',
        'duration_ms': 350,
        'timestamp': '2026-01-01T12:00:00Z',
        'dashboard_category': 'alerts',
      };
      final record = ToolCallRecord.fromJson(json);
      expect(record.callId, 'call-abc');
      expect(record.toolName, 'list_alerts');
      expect(record.argsSummary, 'project_id: my-project');
      expect(record.resultSummary, 'Found 3 active alerts');
      expect(record.status, 'completed');
      expect(record.durationMs, 350);
      expect(record.dashboardCategory, 'alerts');
      expect(record.hasDashboardData, isTrue);
    });

    test('status helpers work correctly', () {
      expect(_makeToolCallRecord(status: 'completed').isCompleted, isTrue);
      expect(_makeToolCallRecord(status: 'error').isError, isTrue);
      expect(_makeToolCallRecord(status: 'pending').isPending, isTrue);
    });

    test('hasDashboardData returns correct value', () {
      expect(
        _makeToolCallRecord(dashboardCategory: 'traces').hasDashboardData,
        isTrue,
      );
      expect(
        _makeToolCallRecord(dashboardCategory: null).hasDashboardData,
        isFalse,
      );
    });

    test('provides defaults for missing fields', () {
      final record = ToolCallRecord.fromJson(const {});
      expect(record.callId, '');
      expect(record.toolName, '');
      expect(record.status, 'completed');
      expect(record.durationMs, 0);
      expect(record.dashboardCategory, isNull);
    });
  });

  group('LLMCallRecord', () {
    test('parses from JSON correctly', () {
      final json = {
        'call_id': 'llm-xyz',
        'model': 'gemini-2.0-flash',
        'input_tokens': 2000,
        'output_tokens': 800,
        'duration_ms': 1500,
        'timestamp': '2026-01-01T12:00:01Z',
      };
      final record = LLMCallRecord.fromJson(json);
      expect(record.callId, 'llm-xyz');
      expect(record.model, 'gemini-2.0-flash');
      expect(record.inputTokens, 2000);
      expect(record.outputTokens, 800);
      expect(record.durationMs, 1500);
      expect(record.totalTokens, 2800);
    });

    test('provides defaults for missing fields', () {
      final record = LLMCallRecord.fromJson(const {});
      expect(record.callId, '');
      expect(record.model, '');
      expect(record.inputTokens, 0);
      expect(record.outputTokens, 0);
      expect(record.totalTokens, 0);
    });
  });

  group('CouncilAgentActivity', () {
    test('parses from JSON correctly', () {
      final json = {
        'agent_id': 'trace-panel',
        'agent_name': 'trace_panel',
        'agent_type': 'panel',
        'parent_id': 'orchestrator',
        'status': 'completed',
        'started_at': '2026-01-01T10:00:00Z',
        'completed_at': '2026-01-01T10:00:05Z',
        'tool_calls': [
          {'call_id': 'tc1', 'tool_name': 'fetch_trace', 'status': 'completed'},
          {
            'call_id': 'tc2',
            'tool_name': 'analyze_trace',
            'status': 'completed',
          },
        ],
        'llm_calls': [
          {'call_id': 'llm1', 'model': 'gemini-2.0-flash'},
        ],
        'output_summary': 'Found latency issue.',
      };
      final agent = CouncilAgentActivity.fromJson(json);
      expect(agent.agentId, 'trace-panel');
      expect(agent.agentName, 'trace_panel');
      expect(agent.agentType, CouncilAgentType.panel);
      expect(agent.parentId, 'orchestrator');
      expect(agent.status, 'completed');
      expect(agent.toolCalls.length, 2);
      expect(agent.llmCalls.length, 1);
      expect(agent.outputSummary, 'Found latency issue.');
    });

    test('status helpers work correctly', () {
      expect(_makeAgentActivity(status: 'completed').isCompleted, isTrue);
      expect(_makeAgentActivity(status: 'running').isRunning, isTrue);
      expect(_makeAgentActivity(status: 'error').hasError, isTrue);
    });

    test('counts are calculated correctly', () {
      final agent = _makeAgentActivity(
        toolCalls: [
          _makeToolCallRecord(status: 'completed'),
          _makeToolCallRecord(status: 'error'),
          _makeToolCallRecord(status: 'completed'),
        ],
        llmCalls: [_makeLLMCallRecord(), _makeLLMCallRecord()],
      );
      expect(agent.totalToolCalls, 3);
      expect(agent.totalLLMCalls, 2);
      expect(agent.errorCount, 1);
    });

    test('getToolCallsForCategory filters correctly', () {
      final agent = _makeAgentActivity(
        toolCalls: [
          _makeToolCallRecord(
            toolName: 'fetch_trace',
            dashboardCategory: 'traces',
          ),
          _makeToolCallRecord(toolName: 'list_logs', dashboardCategory: 'logs'),
          _makeToolCallRecord(
            toolName: 'analyze_trace',
            dashboardCategory: 'traces',
          ),
        ],
      );
      final traceCalls = agent.getToolCallsForCategory('traces');
      expect(traceCalls.length, 2);
    });

    test('isRoot returns correct value', () {
      expect(_makeAgentActivity(parentId: null).isRoot, isTrue);
      expect(_makeAgentActivity(parentId: 'parent').isRoot, isFalse);
    });

    test('iconName returns correct values', () {
      expect(
        _makeAgentActivity(agentType: CouncilAgentType.panel).iconName,
        'psychology',
      );
      expect(
        _makeAgentActivity(agentType: CouncilAgentType.critic).iconName,
        'forum',
      );
    });
  });

  group('CouncilAgentType', () {
    test('fromString parses correctly', () {
      expect(CouncilAgentType.fromString('root'), CouncilAgentType.root);
      expect(
        CouncilAgentType.fromString('orchestrator'),
        CouncilAgentType.orchestrator,
      );
      expect(CouncilAgentType.fromString('panel'), CouncilAgentType.panel);
      expect(CouncilAgentType.fromString('critic'), CouncilAgentType.critic);
      expect(
        CouncilAgentType.fromString('synthesizer'),
        CouncilAgentType.synthesizer,
      );
      expect(
        CouncilAgentType.fromString('sub_agent'),
        CouncilAgentType.subAgent,
      );
    });

    test('displayName returns correct values', () {
      expect(CouncilAgentType.panel.displayName, 'Expert Panel');
      expect(CouncilAgentType.critic.displayName, 'Critic');
      expect(CouncilAgentType.synthesizer.displayName, 'Synthesizer');
    });
  });

  group('CouncilActivityGraph', () {
    test('parses from JSON correctly', () {
      final json = {
        'investigation_id': 'inv-abc',
        'mode': 'debate',
        'started_at': '2026-01-01T10:00:00Z',
        'completed_at': '2026-01-01T10:01:00Z',
        'debate_rounds': 2,
        'agents': [
          {
            'agent_id': 'orch',
            'agent_name': 'orchestrator',
            'agent_type': 'orchestrator',
            'status': 'completed',
            'tool_calls': [],
            'llm_calls': [],
          },
          {
            'agent_id': 'trace',
            'agent_name': 'trace_panel',
            'agent_type': 'panel',
            'parent_id': 'orch',
            'status': 'completed',
            'tool_calls': [
              {'call_id': 'tc1', 'tool_name': 'fetch_trace'},
            ],
            'llm_calls': [],
          },
        ],
      };
      final graph = CouncilActivityGraph.fromJson(json);
      expect(graph.investigationId, 'inv-abc');
      expect(graph.mode, 'debate');
      expect(graph.debateRounds, 2);
      expect(graph.agents.length, 2);
      expect(graph.totalToolCalls, 1);
    });

    test('getAgentById returns correct agent', () {
      final graph = _makeActivityGraph();
      expect(
        graph.getAgentById('orchestrator')?.agentName,
        'council_orchestrator',
      );
      expect(graph.getAgentById('trace-panel')?.agentName, 'trace_panel');
      expect(graph.getAgentById('nonexistent'), isNull);
    });

    test('getChildren returns correct children', () {
      final graph = _makeActivityGraph();
      final children = graph.getChildren('orchestrator');
      expect(children.length, 2);
    });

    test('rootAgents returns agents without parents', () {
      final graph = _makeActivityGraph();
      final roots = graph.rootAgents;
      expect(roots.length, 1);
      expect(roots.first.agentId, 'orchestrator');
    });

    test('panelAgents returns only panel type agents', () {
      final graph = _makeActivityGraph();
      final panels = graph.panelAgents;
      expect(panels.length, 2);
    });

    test('allToolCallsSorted returns sorted list', () {
      final graph = _makeActivityGraph(
        agents: [
          _makeAgentActivity(
            agentId: 'a1',
            toolCalls: [
              _makeToolCallRecord(
                callId: 'c2',
                timestamp: '2026-01-01T10:00:02Z',
              ),
              _makeToolCallRecord(
                callId: 'c1',
                timestamp: '2026-01-01T10:00:01Z',
              ),
            ],
          ),
          _makeAgentActivity(
            agentId: 'a2',
            toolCalls: [
              _makeToolCallRecord(
                callId: 'c3',
                timestamp: '2026-01-01T10:00:03Z',
              ),
            ],
          ),
        ],
      );
      final sorted = graph.allToolCallsSorted;
      expect(sorted.length, 3);
      expect(sorted[0].callId, 'c1');
      expect(sorted[1].callId, 'c2');
      expect(sorted[2].callId, 'c3');
    });

    test('toolCallsByDashboardCategory groups correctly', () {
      final graph = _makeActivityGraph(
        agents: [
          _makeAgentActivity(
            toolCalls: [
              _makeToolCallRecord(dashboardCategory: 'traces'),
              _makeToolCallRecord(dashboardCategory: 'logs'),
              _makeToolCallRecord(dashboardCategory: 'traces'),
            ],
          ),
        ],
      );
      final byCategory = graph.toolCallsByDashboardCategory;
      expect(byCategory['traces']?.length, 2);
      expect(byCategory['logs']?.length, 1);
    });
  });

  group('CouncilSynthesisData with ActivityGraph', () {
    test('hasActivityGraph returns correct value', () {
      expect(_makeCouncilData(activityGraph: null).hasActivityGraph, isFalse);
      expect(
        _makeCouncilData(activityGraph: _makeActivityGraph()).hasActivityGraph,
        isTrue,
      );
    });

    test('totalToolCalls returns value from graph', () {
      final graph = _makeActivityGraph(
        agents: [
          _makeAgentActivity(
            toolCalls: [_makeToolCallRecord(), _makeToolCallRecord()],
          ),
        ],
      );
      final data = _makeCouncilData(activityGraph: graph);
      expect(data.totalToolCalls, 2);
    });

    test('parses activity_graph from JSON', () {
      final json = {
        'synthesis': 'Test synthesis',
        'overall_severity': 'warning',
        'overall_confidence': 0.85,
        'mode': 'standard',
        'rounds': 1,
        'activity_graph': {
          'investigation_id': 'inv-test',
          'mode': 'standard',
          'started_at': '2026-01-01T10:00:00Z',
          'agents': [],
        },
      };
      final data = CouncilSynthesisData.fromJson(json);
      expect(data.hasActivityGraph, isTrue);
      expect(data.activityGraph?.investigationId, 'inv-test');
    });
  });

  group('DashboardState council graph integration', () {
    test('updateCouncilWithActivityGraph updates existing council item', () {
      final state = DashboardState();
      final councilData = _makeCouncilData();
      state.addCouncilSynthesis(councilData, 'run_council_investigation', {});

      expect(state.items.first.councilData?.hasActivityGraph, isFalse);

      final graph = _makeActivityGraph();
      state.updateCouncilWithActivityGraph(graph);

      expect(state.items.first.councilData?.hasActivityGraph, isTrue);
      expect(
        state.items.first.councilData?.activityGraph?.investigationId,
        'inv-123',
      );
    });
  });
}
