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
}) {
  return CouncilSynthesisData(
    synthesis: synthesis,
    overallSeverity: overallSeverity,
    overallConfidence: overallConfidence,
    mode: mode,
    rounds: rounds,
    panels: panels ?? [],
    criticReport: criticReport,
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
      expect(_makePanelFinding(panel: 'metrics').displayName, 'Metrics Analysis');
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
            body: LiveCouncilPanel(items: items),
          ),
        ),
      );

      expect(find.text('Council of Experts'), findsOneWidget);
      expect(find.text('STANDARD'), findsOneWidget);
      expect(find.text('WARNING'), findsOneWidget);
      expect(find.text('Council Confidence'), findsOneWidget);
      expect(find.text('87%'), findsOneWidget);
      expect(
        find.text('Redis pool exhaustion causing checkout latency.'),
        findsOneWidget,
      );
    });

    testWidgets('shows debate mode with round count', (tester) async {
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
          home: Scaffold(
            body: LiveCouncilPanel(items: items),
          ),
        ),
      );

      expect(find.text('DEBATE'), findsOneWidget);
      expect(find.text('CRITICAL'), findsOneWidget);
      expect(find.text('3 debates'), findsOneWidget);
      expect(find.text('92%'), findsOneWidget);
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
            body: LiveCouncilPanel(items: items),
          ),
        ),
      );

      expect(find.text('Expert Findings'), findsOneWidget);
      expect(find.text('Trace Analysis'), findsOneWidget);
      expect(find.text('Metrics Analysis'), findsOneWidget);
      expect(find.text('Latency in payment service.'), findsOneWidget);
      expect(find.text('CPU utilization normal.'), findsOneWidget);
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
        mode: 'debate',
        rounds: 2,
        criticReport: criticReport,
      );
      final items = [_makeCouncilItem(data)];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: LiveCouncilPanel(items: items),
          ),
        ),
      );

      expect(find.text('Debate Analysis'), findsOneWidget);
      expect(find.text('1 agreement'), findsOneWidget);
    });

    testWidgets('fast mode does not show rounds', (tester) async {
      tester.view.physicalSize = const Size(800, 600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      final data = _makeCouncilData(mode: 'fast', rounds: 1);
      final items = [_makeCouncilItem(data)];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: LiveCouncilPanel(items: items),
          ),
        ),
      );

      expect(find.text('FAST'), findsOneWidget);
      expect(find.textContaining('debate'), findsNothing);
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
            body: LiveCouncilPanel(items: items),
          ),
        ),
      );

      expect(find.text('Council of Experts'), findsOneWidget);
      expect(find.text('Council Synthesis'), findsNothing);
    });

    testWidgets('renders empty list gracefully', (tester) async {
      tester.view.physicalSize = const Size(800, 600);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: LiveCouncilPanel(items: []),
          ),
        ),
      );

      expect(find.text('Council of Experts'), findsNothing);
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
            body: LiveCouncilPanel(items: items),
          ),
        ),
      );

      expect(find.text('HEALTHY'), findsOneWidget);
    });
  });
}
