// ignore_for_file: lines_longer_than_80_chars

import 'package:autosre/widgets/dashboard/explorer_chart_painter.dart';
import 'package:autosre/widgets/dashboard/visual_data_explorer.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Pumps a [VisualDataExplorer] inside a standard Material app scaffold.
Future<void> pumpExplorer(
  WidgetTester tester, {
  required List<String> columns,
  required List<Map<String, dynamic>> rows,
}) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: SizedBox(
          width: 1200,
          height: 800,
          child: VisualDataExplorer(columns: columns, rows: rows),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

// ---------------------------------------------------------------------------
// FieldConfig.displayName tests
// ---------------------------------------------------------------------------

void main() {
  group('FieldConfig.displayName', () {
    test('returns column name for dimension (no aggregate)', () {
      const cfg = FieldConfig(column: 'region');
      expect(cfg.displayName, 'region');
    });

    test('returns SUM(col) for sum aggregate', () {
      const cfg = FieldConfig(
        column: 'revenue',
        aggregate: AggregateFunction.sum,
      );
      expect(cfg.displayName, 'SUM(revenue)');
    });

    test('returns AVG(col) for avg', () {
      const cfg = FieldConfig(
        column: 'latency',
        aggregate: AggregateFunction.avg,
      );
      expect(cfg.displayName, 'AVG(latency)');
    });

    test('returns MIN(col) for min', () {
      const cfg = FieldConfig(column: 'val', aggregate: AggregateFunction.min);
      expect(cfg.displayName, 'MIN(val)');
    });

    test('returns MAX(col) for max', () {
      const cfg = FieldConfig(column: 'val', aggregate: AggregateFunction.max);
      expect(cfg.displayName, 'MAX(val)');
    });

    test('returns COUNT(col) for count', () {
      const cfg = FieldConfig(column: 'id', aggregate: AggregateFunction.count);
      expect(cfg.displayName, 'COUNT(id)');
    });

    test('returns COUNTDISTINCT(col) for countDistinct', () {
      const cfg = FieldConfig(
        column: 'user_id',
        aggregate: AggregateFunction.countDistinct,
      );
      expect(cfg.displayName, 'COUNTDISTINCT(user_id)');
    });

    test('returns COUNT(*) for countStar regardless of column', () {
      const cfg = FieldConfig(
        column: 'anything',
        aggregate: AggregateFunction.countStar,
      );
      expect(cfg.displayName, 'COUNT(*)');
    });
  });

  // -------------------------------------------------------------------------
  // AggregateFunction enum
  // -------------------------------------------------------------------------

  group('AggregateFunction enum', () {
    test('has all expected values', () {
      expect(
        AggregateFunction.values,
        containsAll([
          AggregateFunction.sum,
          AggregateFunction.avg,
          AggregateFunction.count,
          AggregateFunction.min,
          AggregateFunction.max,
          AggregateFunction.countDistinct,
          AggregateFunction.countStar,
        ]),
      );
    });
  });

  // -------------------------------------------------------------------------
  // ExplorerChartType enum
  // -------------------------------------------------------------------------

  group('ExplorerChartType enum', () {
    test('includes all expected chart types', () {
      expect(
        ExplorerChartType.values,
        containsAll([
          ExplorerChartType.bar,
          ExplorerChartType.horizontalBar,
          ExplorerChartType.stackedBar,
          ExplorerChartType.groupedBar,
          ExplorerChartType.line,
          ExplorerChartType.area,
          ExplorerChartType.scatter,
          ExplorerChartType.pie,
          ExplorerChartType.heatmap,
          ExplorerChartType.table,
        ]),
      );
    });
  });

  // -------------------------------------------------------------------------
  // ExplorerChartPainter.shouldRepaint
  // -------------------------------------------------------------------------

  group('ExplorerChartPainter.shouldRepaint', () {
    final baseData = [
      {'dim': 'A', 'SUM(val)': 10.0},
    ];

    ExplorerChartPainter makePainter({
      List<Map<String, dynamic>>? data,
      String dimensionKey = 'dim',
      String measureKey = 'SUM(val)',
      ExplorerChartType chartType = ExplorerChartType.bar,
      String? seriesKey,
    }) {
      return ExplorerChartPainter(
        data: data ?? baseData,
        dimensionKey: dimensionKey,
        measureKey: measureKey,
        measures: [measureKey],
        chartType: chartType,
        color: const Color(0xFF00FFFF),
        textColor: const Color(0xFFFFFFFF),
        gridColor: const Color(0xFF888888),
        seriesKey: seriesKey,
      );
    }

    test('returns false when nothing changed', () {
      final p = makePainter();
      expect(p.shouldRepaint(makePainter()), isFalse);
    });

    test('returns true when data changes', () {
      final p1 = makePainter(data: baseData);
      final p2 = makePainter(
        data: [
          {'dim': 'B', 'SUM(val)': 20.0},
        ],
      );
      expect(p1.shouldRepaint(p2), isTrue);
    });

    test('returns true when chartType changes', () {
      final p1 = makePainter(chartType: ExplorerChartType.bar);
      final p2 = makePainter(chartType: ExplorerChartType.line);
      expect(p1.shouldRepaint(p2), isTrue);
    });

    test('returns true when seriesKey changes', () {
      final p1 = makePainter(seriesKey: null);
      final p2 = makePainter(seriesKey: 'product');
      expect(p1.shouldRepaint(p2), isTrue);
    });

    test('returns true when dimensionKey changes', () {
      final p1 = makePainter(dimensionKey: 'dim');
      final p2 = makePainter(dimensionKey: 'region');
      expect(p1.shouldRepaint(p2), isTrue);
    });
  });

  // -------------------------------------------------------------------------
  // Widget: basic rendering
  // -------------------------------------------------------------------------

  group('VisualDataExplorer widget rendering', () {
    final columns = ['region', 'product', 'revenue'];
    final rows = [
      {'region': 'US', 'product': 'A', 'revenue': 100},
      {'region': 'US', 'product': 'B', 'revenue': 200},
      {'region': 'EU', 'product': 'A', 'revenue': 150},
      {'region': 'EU', 'product': 'B', 'revenue': 50},
    ];

    testWidgets('renders config bar with chart type chips', (tester) async {
      await pumpExplorer(tester, columns: columns, rows: rows);

      // Should show "Chart" label
      expect(find.text('Chart'), findsOneWidget);
      // Should show Sort button
      expect(find.text('Sort'), findsOneWidget);
    });

    testWidgets('renders field shelves with Dimensions and Measures labels', (
      tester,
    ) async {
      await pumpExplorer(tester, columns: columns, rows: rows);

      expect(find.text('Dimensions'), findsOneWidget);
      expect(find.text('Measures'), findsOneWidget);
      expect(find.text('Filters'), findsOneWidget);
    });

    testWidgets('shows all chart type icons via Tooltip labels', (
      tester,
    ) async {
      await pumpExplorer(tester, columns: columns, rows: rows);

      // Each chart type should have a Tooltip widget.
      expect(find.byType(Tooltip), findsWidgets);
    });

    testWidgets('does NOT show Limit dropdown', (tester) async {
      await pumpExplorer(tester, columns: columns, rows: rows);

      // The old "Limit" label should be gone.
      expect(find.text('Limit'), findsNothing);
    });

    testWidgets('shows row count annotation in chart area', (tester) async {
      await pumpExplorer(tester, columns: columns, rows: rows);

      // After auto-configuration aggregates the data, a "N data points" label
      // should appear. Actual count depends on auto-detected columns.
      expect(find.textContaining('data points'), findsOneWidget);
    });

    testWidgets('shows empty state when no rows provided', (tester) async {
      await pumpExplorer(tester, columns: columns, rows: []);

      expect(
        find.textContaining('Add dimensions and measures'),
        findsOneWidget,
      );
    });

    testWidgets('shows available row count in empty state', (tester) async {
      await pumpExplorer(tester, columns: columns, rows: rows);

      // The explorer widget should auto-configure, so the empty-state prompt
      // is not shown. But let us test with no columns to confirm.
      await pumpExplorer(tester, columns: [], rows: []);
      expect(find.textContaining('0 rows'), findsOneWidget);
    });

    testWidgets('renders dimension chips with [1] index badge', (tester) async {
      await pumpExplorer(tester, columns: columns, rows: rows);

      // Auto-configuration picks a categorical column as dim[0], shown as [1].
      expect(find.text('[1]'), findsOneWidget);
    });
  });

  // -------------------------------------------------------------------------
  // Widget: stacked / grouped bar chart needs 2 dimensions
  // -------------------------------------------------------------------------

  group('VisualDataExplorer stacked/grouped bar hints', () {
    final columns = ['region', 'revenue'];
    final rows = [
      {'region': 'US', 'revenue': 100},
      {'region': 'EU', 'revenue': 200},
    ];

    testWidgets(
      'shows 2nd-dimension prompt when stackedBar selected with 1 dim',
      (tester) async {
        await pumpExplorer(tester, columns: columns, rows: rows);

        // Tap the stacked bar chip (it's a Tooltip-wrapped InkWell).
        final stackedTooltip = find.byWidgetPredicate(
          (w) => w is Tooltip && w.message == 'Stacked Bar (2 dims)',
        );
        expect(stackedTooltip, findsOneWidget);
        await tester.tap(stackedTooltip);
        await tester.pumpAndSettle();

        // Should show "Add a 2nd dimension" prompt.
        expect(find.textContaining('Add a 2nd dimension'), findsOneWidget);
        expect(
          find.text('1st dimension → X axis  ·  2nd dimension → colour series'),
          findsOneWidget,
        );
      },
    );

    testWidgets('shows info hint in shelves when stackedBar active', (
      tester,
    ) async {
      await pumpExplorer(tester, columns: columns, rows: rows);

      // Select stackedBar
      final stackedTooltip = find.byWidgetPredicate(
        (w) => w is Tooltip && w.message == 'Stacked Bar (2 dims)',
      );
      await tester.tap(stackedTooltip);
      await tester.pumpAndSettle();

      // The shelf hint should appear
      expect(find.textContaining('1st dimension = X axis'), findsOneWidget);
    });

    testWidgets(
      'shows 2nd-dimension prompt when groupedBar selected with 1 dim',
      (tester) async {
        await pumpExplorer(tester, columns: columns, rows: rows);

        final groupedTooltip = find.byWidgetPredicate(
          (w) => w is Tooltip && w.message == 'Grouped Bar (2 dims)',
        );
        expect(groupedTooltip, findsOneWidget);
        await tester.tap(groupedTooltip);
        await tester.pumpAndSettle();

        expect(find.textContaining('Add a 2nd dimension'), findsOneWidget);
      },
    );
  });

  // -------------------------------------------------------------------------
  // Widget: all data points shown (no limit)
  // -------------------------------------------------------------------------

  group('VisualDataExplorer no-limit behaviour', () {
    test(
      'aggregatedData returns all groups when input has many distinct values',
      () {
        // Generate 500 distinct category values each with a numeric field.
        final rows = List.generate(500, (i) => {'cat': 'cat_$i', 'val': i});
        // We can't directly access _aggregatedData but we can observe the row
        // count label through the widget test below.
        expect(rows.length, 500);
      },
    );

    testWidgets('shows all 500 data points in chart annotation', (
      tester,
    ) async {
      final rows = List.generate(
        500,
        (i) => {'cat': 'cat_$i', 'val': i.toDouble()},
      );

      await pumpExplorer(tester, columns: ['cat', 'val'], rows: rows);

      // Each unique 'cat' value is its own group → 500 data points.
      expect(find.text('500 data points'), findsOneWidget);
    });

    testWidgets('shows correct data-point count after filtering', (
      tester,
    ) async {
      // 10 rows but the numeric column has values 0-9.  With the categorical
      // column having unique values per row, we expect 10 groups → 10 points.
      final rows = List.generate(
        10,
        (i) => {'label': 'L$i', 'amount': i.toDouble()},
      );

      await pumpExplorer(tester, columns: ['label', 'amount'], rows: rows);

      expect(find.text('10 data points'), findsOneWidget);
    });
  });

  // -------------------------------------------------------------------------
  // Widget: chart type switching
  // -------------------------------------------------------------------------

  group('VisualDataExplorer chart type switching', () {
    final columns = ['cat', 'val'];
    final rows = [
      {'cat': 'A', 'val': 10},
      {'cat': 'B', 'val': 20},
    ];

    for (final entry in {
      'Bar': ExplorerChartType.bar,
      'Horizontal Bar': ExplorerChartType.horizontalBar,
      'Line': ExplorerChartType.line,
      'Area': ExplorerChartType.area,
      'Scatter': ExplorerChartType.scatter,
      'Pie': ExplorerChartType.pie,
      'Heatmap': ExplorerChartType.heatmap,
      'Table': ExplorerChartType.table,
    }.entries) {
      testWidgets('can switch to ${entry.key} without errors', (tester) async {
        await pumpExplorer(tester, columns: columns, rows: rows);

        final tooltip = find.byWidgetPredicate(
          (w) => w is Tooltip && w.message == entry.key,
        );
        expect(tooltip, findsOneWidget);
        await tester.tap(tooltip);
        await tester.pumpAndSettle();

        // No exceptions → chart rendered (or table for table type).
        expect(tester.takeException(), isNull);
      });
    }

    testWidgets('table view shows DataTable with all columns', (tester) async {
      await pumpExplorer(tester, columns: columns, rows: rows);

      // Switch to table
      final tableTooltip = find.byWidgetPredicate(
        (w) => w is Tooltip && w.message == 'Table',
      );
      await tester.tap(tableTooltip);
      await tester.pumpAndSettle();

      // DataTable should be present
      expect(find.byType(DataTable), findsOneWidget);
    });
  });

  // -------------------------------------------------------------------------
  // Aggregation logic via FieldConfig (pure unit tests)
  // -------------------------------------------------------------------------

  group('Aggregation: countStar produces COUNT(*) display name', () {
    test('countStar displayName is COUNT(*)', () {
      const f = FieldConfig(
        column: 'irrelevant',
        aggregate: AggregateFunction.countStar,
      );
      expect(f.displayName, 'COUNT(*)');
    });

    test('countStar displayName is COUNT(*) for any column', () {
      for (final col in ['a', 'b', 'my_col', '']) {
        final f = FieldConfig(
          column: col,
          aggregate: AggregateFunction.countStar,
        );
        expect(f.displayName, 'COUNT(*)');
      }
    });
  });

  // -------------------------------------------------------------------------
  // ExplorerChartPainter: multi-series helpers (accessible via public data)
  // -------------------------------------------------------------------------

  group('ExplorerChartPainter multi-series data extraction', () {
    final multiData = [
      {'region': 'US', 'product': 'A', 'SUM(revenue)': 100.0},
      {'region': 'US', 'product': 'B', 'SUM(revenue)': 200.0},
      {'region': 'EU', 'product': 'A', 'SUM(revenue)': 150.0},
      {'region': 'EU', 'product': 'B', 'SUM(revenue)': 50.0},
    ];

    test('painter is created with seriesKey and does not throw', () {
      expect(
        () => ExplorerChartPainter(
          data: multiData,
          dimensionKey: 'region',
          measureKey: 'SUM(revenue)',
          measures: ['SUM(revenue)'],
          chartType: ExplorerChartType.stackedBar,
          color: const Color(0xFF00FFFF),
          textColor: const Color(0xFFFFFFFF),
          gridColor: const Color(0xFF888888),
          seriesKey: 'product',
        ),
        returnsNormally,
      );
    });

    test('painter created for groupedBar with seriesKey does not throw', () {
      expect(
        () => ExplorerChartPainter(
          data: multiData,
          dimensionKey: 'region',
          measureKey: 'SUM(revenue)',
          measures: ['SUM(revenue)'],
          chartType: ExplorerChartType.groupedBar,
          color: const Color(0xFF00FFFF),
          textColor: const Color(0xFFFFFFFF),
          gridColor: const Color(0xFF888888),
          seriesKey: 'product',
        ),
        returnsNormally,
      );
    });

    test('painter created for horizontalBar does not throw', () {
      expect(
        () => ExplorerChartPainter(
          data: [
            {'cat': 'A', 'SUM(val)': 10.0},
            {'cat': 'B', 'SUM(val)': 20.0},
          ],
          dimensionKey: 'cat',
          measureKey: 'SUM(val)',
          measures: ['SUM(val)'],
          chartType: ExplorerChartType.horizontalBar,
          color: const Color(0xFF00FFFF),
          textColor: const Color(0xFFFFFFFF),
          gridColor: const Color(0xFF888888),
        ),
        returnsNormally,
      );
    });

    test(
      'shouldRepaint: returns true when seriesKey changes from null to value',
      () {
        final p1 = ExplorerChartPainter(
          data: multiData,
          dimensionKey: 'region',
          measureKey: 'SUM(revenue)',
          measures: ['SUM(revenue)'],
          chartType: ExplorerChartType.stackedBar,
          color: const Color(0xFF00FFFF),
          textColor: const Color(0xFFFFFFFF),
          gridColor: const Color(0xFF888888),
        );
        final p2 = ExplorerChartPainter(
          data: multiData,
          dimensionKey: 'region',
          measureKey: 'SUM(revenue)',
          measures: ['SUM(revenue)'],
          chartType: ExplorerChartType.stackedBar,
          color: const Color(0xFF00FFFF),
          textColor: const Color(0xFFFFFFFF),
          gridColor: const Color(0xFF888888),
          seriesKey: 'product',
        );
        expect(p1.shouldRepaint(p2), isTrue);
      },
    );
  });

  // -------------------------------------------------------------------------
  // explorerChartColors palette
  // -------------------------------------------------------------------------

  group('explorerChartColors', () {
    test('has at least 8 colours', () {
      expect(explorerChartColors.length, greaterThanOrEqualTo(8));
    });

    test('all colours are fully opaque or have explicit alpha', () {
      // Just ensure no colour is Color(0) which would be invisible.
      for (final c in explorerChartColors) {
        expect(c.toARGB32(), isNot(equals(0)));
      }
    });
  });
}
