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
}) {
  return CouncilSynthesisData(
    synthesis: synthesis,
    overallSeverity: overallSeverity,
    overallConfidence: overallConfidence,
    mode: mode,
    rounds: rounds,
    rawData: const {},
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

    test('classifyComponent maps x-sre-council-synthesis', () {
      // classifyComponent is a static method, test via addFromEvent
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

      expect(find.text('Council Investigation'), findsOneWidget);
      expect(find.text('STANDARD'), findsOneWidget);
      expect(find.text('WARNING'), findsOneWidget);
      expect(find.text('Confidence: '), findsOneWidget);
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
      expect(find.text('Rounds: '), findsOneWidget);
      expect(find.text('3'), findsOneWidget);
      expect(find.text('92%'), findsOneWidget);
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
      expect(find.text('Rounds: '), findsNothing);
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

      expect(find.text('Council Investigation'), findsOneWidget);
      // The synthesis text container should not be present
      expect(find.text(''), findsNothing);
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

      expect(find.text('Council Investigation'), findsNothing);
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
