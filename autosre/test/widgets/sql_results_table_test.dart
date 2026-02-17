import 'package:autosre/widgets/dashboard/sql_results_table.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('SqlResultsTable Tests', () {
    testWidgets('renders table with columns and generic data', (WidgetTester tester) async {
      final columns = ['id', 'name'];
      final rows = [
        {'id': 1, 'name': 'Alice'},
        {'id': 2, 'name': 'Bob'},
      ];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SqlResultsTable(columns: columns, rows: rows),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('id'), findsOneWidget);
      expect(find.text('name'), findsOneWidget);
      expect(find.text('Alice'), findsOneWidget);
      expect(find.text('Bob'), findsOneWidget);
    });

    testWidgets('paginates data properly', (WidgetTester tester) async {
      final columns = ['val'];
      final rows = List.generate(200, (i) => {'val': 'ID-$i'});

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SizedBox(
              width: 800,
              height: 600,
              child: SqlResultsTable(columns: columns, rows: rows),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // By default it should show page size 100
      expect(find.text('Rows per page:'), findsOneWidget);
      expect(find.text('1-100 of 200'), findsOneWidget);

      expect(find.text('ID-0'), findsWidgets); // index 0
      expect(find.text('ID-100'), findsNothing); // next page

      // Tap next page
      await tester.tap(find.byIcon(Icons.chevron_right));
      await tester.pumpAndSettle();

      expect(find.text('101-200 of 200'), findsOneWidget);
      expect(find.text('ID-100'), findsWidgets);
    });

    testWidgets('sorts data when column header is clicked', (WidgetTester tester) async {
      final columns = ['value'];
      final rows = [
        {'value': 10},
        {'value': 30},
        {'value': 20},
      ];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SqlResultsTable(columns: columns, rows: rows),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Click column header "value"
      await tester.tap(find.text('value'));
      await tester.pumpAndSettle();

      // First click: Ascending -> 10, 20, 30
      // Check order
      final texts = tester.widgetList<Text>(find.byType(Text))
          .map((t) => t.data)
          .where((data) => data == '10' || data == '20' || data == '30')
          .toList();

      expect(texts, ['10', '20', '30']);

      // Click again: Descending -> 30, 20, 10
      await tester.tap(find.text('value'));
      await tester.pumpAndSettle();

      final descTexts = tester.widgetList<Text>(find.byType(Text))
          .map((t) => t.data)
          .where((data) => data == '10' || data == '20' || data == '30')
          .toList();
      expect(descTexts, ['30', '20', '10']);
    });

    testWidgets('formats float timestamps correctly', (WidgetTester tester) async {
      final columns = ['timestamp'];
      final rows = [
        // Using a BigQuery-like numeric string that is > 1e9
        {'timestamp': '1.7040672e9'},
      ];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: SqlResultsTable(columns: columns, rows: rows),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // The table heuristic will detect "timestamp" in the column name + number > 1e9
      // It should format it as a YYYY-MM-DD HH:MM:SS string in local time.
      // 1704067200 is 2024-01-01 00:00:00 UTC. The exact local rendering will depend on timezone.
      // But it should NOT match "1.7040672e9" textually anymore.
      expect(find.text('1.7040672e9'), findsNothing);
      // We look for 202 in the formatted string to bypass timezone boundary logic
      expect(find.textContaining('202'), findsOneWidget);
    });
  });
}
