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
      await tester.pumpAndSettle();
    }

    testWidgets('LogPatternViewer accepts List input', (
      WidgetTester tester,
    ) async {
      final item = catalog.items.firstWhere(
        (i) => i.name == 'x-sre-log-pattern-viewer',
      );

      final validList = [
        {
          "template": "Error connecting to database",
          "count": 5,
          "severity_counts": {"ERROR": 5},
        },
      ];

      final widget = item.widgetBuilder(FakeCatalogItemContext(validList));
      await pumpTestWidget(tester, widget);

      expect(find.byType(LogPatternViewer), findsOneWidget);
      expect(find.text('Error connecting to database'), findsOneWidget);
    });

    testWidgets('LogPatternViewer accepts Map input (patterns key)', (
      WidgetTester tester,
    ) async {
      final item = catalog.items.firstWhere(
        (i) => i.name == 'x-sre-log-pattern-viewer',
      );

      final validMap = {
        "patterns": [
          {
            "template": "Timeout waiting for service",
            "count": 3,
            "severity_counts": {"WARNING": 3},
          },
        ],
      };

      final widget = item.widgetBuilder(FakeCatalogItemContext(validMap));
      await pumpTestWidget(tester, widget);

      expect(find.byType(LogPatternViewer), findsOneWidget);
      expect(find.text('Timeout waiting for service'), findsOneWidget);
    });

    testWidgets('LogPatternViewer accepts Map input (data key fallback)', (
      WidgetTester tester,
    ) async {
      final item = catalog.items.firstWhere(
        (i) => i.name == 'x-sre-log-pattern-viewer',
      );

      final validMap = {
        "data": [
          {
            "template": "Data key fallback",
            "count": 1,
            "severity_counts": {"INFO": 1},
          },
        ],
      };

      final widget = item.widgetBuilder(FakeCatalogItemContext(validMap));
      await pumpTestWidget(tester, widget);

      expect(find.byType(LogPatternViewer), findsOneWidget);
      expect(find.text('Data key fallback'), findsOneWidget);
    });

    testWidgets('LogPatternViewer handles invalid input gracefully', (
      WidgetTester tester,
    ) async {
      final item = catalog.items.firstWhere(
        (i) => i.name == 'x-sre-log-pattern-viewer',
      );

      // Invalid: String instead of List/Map
      final widget = item.widgetBuilder(
        FakeCatalogItemContext("Invalid String Data"),
      );
      await pumpTestWidget(tester, widget);

      // Should show ErrorPlaceholder, not crash
      expect(find.byType(ErrorPlaceholder), findsOneWidget);
      expect(find.textContaining('Expected List or Map'), findsOneWidget);
    });

    testWidgets('All widgets handle invalid types gracefully', (
      WidgetTester tester,
    ) async {
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
        final item = catalog.items.firstWhere((i) => i.name == name);

        // Pass a String, which should fail the _ensureMap check
        final widget = item.widgetBuilder(FakeCatalogItemContext("Not a Map"));
        await pumpTestWidget(tester, widget);

        // Verify it rendered an ErrorPlaceholder
        expect(
          find.byType(ErrorPlaceholder),
          findsOneWidget,
          reason: '$name should return ErrorPlaceholder on invalid input',
        );

        // Verify the error message contains the type mismatch info
        expect(
          find.textContaining('Expected Map<String, dynamic>'),
          findsOneWidget,
          reason: '$name should report type mismatch',
        );
      }
    });
  });
}
