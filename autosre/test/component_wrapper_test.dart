import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/catalog.dart';
import 'package:autosre/widgets/tool_log.dart';
import 'package:genui/genui.dart';

class FakeCatalogItemContext implements CatalogItemContext {
  @override
  final Object data;

  FakeCatalogItemContext(this.data);

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  testWidgets('Catalog handles legacy "component" wrapper for tool logs',
      (WidgetTester tester) async {
    final catalog = CatalogRegistry.createSreCatalog();
    final item = catalog.items.firstWhere((i) => i.name == 'x-sre-tool-log');

    // Data with the legacy "component" wrapper
    final wrappedData = {
      'component': {
        'x-sre-tool-log': {
          'tool_name': 'list_gcp_projects',
          'args': {},
          'status': 'running'
        }
      }
    };

    final widget = item.widgetBuilder(FakeCatalogItemContext(wrappedData));

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: widget,
        ),
      ),
    );

    // Should find the ToolLogWidget
    expect(find.byType(ToolLogWidget), findsOneWidget);
    expect(find.text('List Gcp Projects'), findsOneWidget);
  });

  testWidgets('Catalog handles A2UI v0.8 format with "id" and "component"',
      (WidgetTester tester) async {
    final catalog = CatalogRegistry.createSreCatalog();
    final item = catalog.items.firstWhere((i) => i.name == 'x-sre-tool-log');

    // Data in A2UI v0.8 format: {"id": "...", "component": {"x-sre-tool-log": {...}}}
    final a2uiV08Data = {
      'id': 'tool-log-abc12345',
      'component': {
        'x-sre-tool-log': {
          'tool_name': 'fetch_trace',
          'args': {'trace_id': 'abc123'},
          'status': 'completed',
          'result': {'spans': []},
        }
      }
    };

    final widget = item.widgetBuilder(FakeCatalogItemContext(a2uiV08Data));

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: widget,
        ),
      ),
    );

    // Should find the ToolLogWidget
    expect(find.byType(ToolLogWidget), findsOneWidget);
    expect(find.text('Fetch Trace'), findsOneWidget);
  });

  testWidgets('Catalog handles direct data format',
      (WidgetTester tester) async {
    final catalog = CatalogRegistry.createSreCatalog();
    final item = catalog.items.firstWhere((i) => i.name == 'x-sre-tool-log');

    // Direct data format (no wrapping)
    final directData = {
      'tool_name': 'analyze_logs',
      'args': {'filter': 'severity>=ERROR'},
      'status': 'running',
    };

    final widget = item.widgetBuilder(FakeCatalogItemContext(directData));

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: widget,
        ),
      ),
    );

    // Should find the ToolLogWidget
    expect(find.byType(ToolLogWidget), findsOneWidget);
    expect(find.text('Analyze Logs'), findsOneWidget);
  });
}
