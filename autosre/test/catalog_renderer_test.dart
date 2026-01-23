import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/catalog.dart';
import 'package:autosre/widgets/error_placeholder.dart';
import 'package:autosre/widgets/log_pattern_viewer.dart';
import 'package:genui/genui.dart';

class FakeCatalogItemContext implements CatalogItemContext {
  @override
  final Object data;

  FakeCatalogItemContext(this.data);

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  group('A2UI Catalog Renderer Tests', () {
    final catalog = CatalogRegistry.createSreCatalog();

    // Helper to pump widget with proper environment
    Future<void> pumpTestWidget(WidgetTester tester, Widget widget) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SizedBox(width: 800, height: 600, child: widget),
          ),
        ),
      );
      await tester.pump();
    }

    final testData = {
      'incident_id': 'inc-123',
      'title': 'Test Title',
      'start_time': '2024-01-01T00:00:00Z',
      'status': 'completed',
      'tool_name': 'test_tool',
      'args': <String, dynamic>{},
      'trace_id': '123',
      'spans': [
        {
          'span_id': 's1',
          'trace_id': '123',
          'name': 'test-span',
          'start_time': '2024-01-01T00:00:00Z',
          'end_time': '2024-01-01T00:00:01Z',
          'attributes': <String, dynamic>{},
          'status': 'OK',
        }
      ],
      'metric_name': 'test-metric',
      'unit': 'ms',
      'current_value': 100.0,
      'points': [
        {'timestamp': '2024-01-01T00:00:00Z', 'value': 1.0}
      ],
      'labels': <String, dynamic>{},
      'issue': 'test-issue',
      'risk': 'low',
      'steps': [
        {
          'id': 'step1',
          'type': 'observation',
          'content': 'test step',
          'description': 'remediation step',
          'command': 'ls'
        }
      ],
      'entries': [
        {
          'insert_id': 'id1',
          'timestamp': '2024-01-01T00:00:00Z',
          'severity': 'INFO',
          'payload': 'test',
          'resource_labels': <String, String>{},
          'resource_type': 'test-resource',
        }
      ],
      'nodes': [
        {
          'id': 'n1',
          'name': 'node 1',
          'type': 'coordinator',
          'status': 'completed'
        }
      ],
      'services': [
        {'id': 's1', 'name': 'svc 1', 'type': 'backend', 'health': 'healthy'}
      ],
      'events': [
        {
          'id': 'e1',
          'timestamp': '2024-01-01T00:00:00Z',
          'type': 'info',
          'title': 'evt 1',
          'severity': 'info',
        }
      ],
      'metrics': [
        {'id': 'm1', 'name': 'met 1', 'current_value': 10, 'status': 'normal'}
      ],
      'template': 'test-template',
      'count': 1,
      'severity_counts': <String, int>{},
      'agent_name': 'Test Agent',
      'current_task': 'Test Task',
      'conclusion': 'test-conclusion',
    };

    final widgetsToTest = [
      'x-sre-trace-waterfall',
      'x-sre-metric-chart',
      'x-sre-remediation-plan',
      'x-sre-log-entries-viewer',
      'x-sre-tool-log',
      'x-sre-agent-activity',
      'x-sre-service-topology',
      'x-sre-incident-timeline',
      'x-sre-metrics-dashboard',
      'x-sre-ai-reasoning',
    ];

    for (final name in widgetsToTest) {
      testWidgets('$name handles "wrapped" A2UI data format', (tester) async {
        final item = catalog.items.firstWhere((i) => i.name == name);
        final wrappedData = {name: testData};

        final widget = item.widgetBuilder(FakeCatalogItemContext(wrappedData));
        await pumpTestWidget(tester, widget);

        final errorFinder = find.byType(ErrorPlaceholder);
        if (tester.any(errorFinder)) {
          final errorWidget = tester.widget<ErrorPlaceholder>(errorFinder);
          fail('$name failed to unwrap A2UI data: ${errorWidget.error}');
        }
      });
    }

    testWidgets('All widgets handle invalid types gracefully', (
      WidgetTester tester,
    ) async {
      for (final name in widgetsToTest) {
        final item = catalog.items.firstWhere((i) => i.name == name);
        final widget = item.widgetBuilder(FakeCatalogItemContext("Not a Map"));
        await pumpTestWidget(tester, widget);

        expect(
          find.byType(ErrorPlaceholder),
          findsOneWidget,
          reason: '$name should return ErrorPlaceholder on invalid input',
        );
      }
    });
  });
}
