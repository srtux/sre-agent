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
  testWidgets('Catalog handles "component" wrapper for tool logs',
      (WidgetTester tester) async {
    final catalog = CatalogRegistry.createSreCatalog();
    final item = catalog.items.firstWhere((i) => i.name == 'x-sre-tool-log');

    // Data with the "component" wrapper, exactly as sent by the backend logic
    final wrappedData = {
      "component": {
        "x-sre-tool-log": {
          "tool_name": "list_gcp_projects",
          "args": {},
          "status": "running"
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
}
