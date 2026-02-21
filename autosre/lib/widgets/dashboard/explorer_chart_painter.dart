import 'dart:math';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../../theme/app_theme.dart';

/// Chart type for the visual data explorer.
enum ExplorerChartType {
  /// Vertical bar chart — single dimension → X axis, measure → bar height.
  bar,

  /// Horizontal bar chart — dimension labels on Y axis, measure → bar length.
  horizontalBar,

  /// Stacked bar chart — requires 2 dimensions: dim[0] → X axis, dim[1] → colour series.
  stackedBar,

  /// Grouped / clustered bar chart — same as stacked but bars are side-by-side.
  groupedBar,

  /// Line chart with optional dots.
  line,

  /// Area chart (filled line).
  area,

  /// Scatter / dot plot.
  scatter,

  /// Pie / donut chart.
  pie,

  /// Heatmap (colour intensity per cell).
  heatmap,

  /// Raw data table rendered as a Flutter [DataTable].
  table,
}

/// Shared chart colour palette for the visual data explorer.
const explorerChartColors = <Color>[
  AppColors.primaryCyan,
  AppColors.warning,
  AppColors.success,
  AppColors.error,
  AppColors.secondaryPurple,
  AppColors.primaryBlue,
  AppColors.info,
  AppColors.primaryTeal,
];

/// Custom painter for rendering explorer charts.
///
/// Supports bar, horizontal bar, stacked bar, grouped bar, line, area,
/// scatter, pie, and heatmap chart types.
///
/// For [ExplorerChartType.stackedBar] and [ExplorerChartType.groupedBar],
/// set [seriesKey] to the name of the second dimension column. Each unique
/// value of that column becomes a colour-coded series.
///
/// Extracted from [VisualDataExplorer] for maintainability.
class ExplorerChartPainter extends CustomPainter {
  final List<Map<String, dynamic>> data;
  final String dimensionKey;
  final String measureKey;
  final List<String> measures;
  final ExplorerChartType chartType;
  final Color color;
  final Color textColor;
  final Color gridColor;

  /// Optional second dimension used as the series grouping key for stacked /
  /// grouped bar charts. Ignored for other chart types.
  final String? seriesKey;

  ExplorerChartPainter({
    required this.data,
    required this.dimensionKey,
    required this.measureKey,
    required this.measures,
    required this.chartType,
    required this.color,
    required this.textColor,
    required this.gridColor,
    this.seriesKey,
  });

  // ---------------------------------------------------------------------------
  // Entry point
  // ---------------------------------------------------------------------------

  @override
  void paint(Canvas canvas, Size size) {
    if (data.isEmpty) return;

    // Chart area geometry differs between horizontal and standard orientations.
    final isHorizontal = chartType == ExplorerChartType.horizontalBar;
    final chartArea = isHorizontal
        ? Rect.fromLTRB(110, 10, size.width - 50, size.height - 10)
        : Rect.fromLTRB(60, 20, size.width - 20, size.height - 40);

    switch (chartType) {
      case ExplorerChartType.bar:
        final values = _extractValues();
        final labels = _extractLabels();
        final maxVal = values.isEmpty ? 0.0 : values.reduce(max);
        final minVal = values.isEmpty ? 0.0 : values.reduce(min);
        _drawGrid(canvas, chartArea, maxVal, minVal);
        _drawBarChart(
          canvas,
          chartArea,
          values,
          labels,
          maxVal,
          maxVal - minVal,
        );
        _drawAxisLabels(canvas, chartArea, labels);

      case ExplorerChartType.horizontalBar:
        final values = _extractValues();
        final labels = _extractLabels();
        final maxVal = values.isEmpty ? 0.0 : values.reduce(max);
        _drawHorizontalBarChart(canvas, chartArea, values, labels, maxVal);

      case ExplorerChartType.stackedBar:
        _drawStackedBarChart(canvas, chartArea);

      case ExplorerChartType.groupedBar:
        _drawGroupedBarChart(canvas, chartArea);

      case ExplorerChartType.line:
      case ExplorerChartType.area:
        final values = _extractValues();
        final labels = _extractLabels();
        if (values.isEmpty) return;
        final maxVal = values.reduce(max);
        final minVal = values.reduce(min);
        _drawGrid(canvas, chartArea, maxVal, minVal);
        _drawLineChart(
          canvas,
          chartArea,
          values,
          labels,
          minVal,
          maxVal,
          maxVal - minVal,
          fill: chartType == ExplorerChartType.area,
        );
        _drawAxisLabels(canvas, chartArea, labels);

      case ExplorerChartType.scatter:
        final values = _extractValues();
        final labels = _extractLabels();
        if (values.isEmpty) return;
        final maxVal = values.reduce(max);
        final minVal = values.reduce(min);
        _drawGrid(canvas, chartArea, maxVal, minVal);
        _drawScatterChart(
          canvas,
          chartArea,
          values,
          labels,
          minVal,
          maxVal - minVal,
        );
        _drawAxisLabels(canvas, chartArea, labels);

      case ExplorerChartType.pie:
        final values = _extractValues();
        final labels = _extractLabels();
        _drawPieChart(canvas, size, values, labels);

      case ExplorerChartType.heatmap:
        final values = _extractValues();
        final labels = _extractLabels();
        if (values.isEmpty) return;
        final maxVal = values.reduce(max);
        final minVal = values.reduce(min);
        _drawHeatmap(canvas, chartArea, values, labels, minVal, maxVal);
        _drawAxisLabels(canvas, chartArea, labels);

      case ExplorerChartType.table:
        // Handled by widget, not painter.
        break;
    }
  }

  // ---------------------------------------------------------------------------
  // Data extraction helpers
  // ---------------------------------------------------------------------------

  List<double> _extractValues() {
    return data.map((row) {
      final v = row[measureKey];
      if (v is num) return v.toDouble();
      return double.tryParse(v?.toString() ?? '') ?? 0.0;
    }).toList();
  }

  List<String> _extractLabels() {
    return data.map((row) => row[dimensionKey]?.toString() ?? '').toList();
  }

  double _getDoubleValue(dynamic v) {
    if (v == null) return 0.0;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString()) ?? 0.0;
  }

  /// Ordered unique values of [dimensionKey] preserving insertion order.
  List<String> _uniqueDim0Values() {
    final seen = <String>{};
    final result = <String>[];
    for (final row in data) {
      final v = row[dimensionKey]?.toString() ?? '';
      if (seen.add(v)) result.add(v);
    }
    return result;
  }

  /// Ordered unique values of [seriesKey] preserving insertion order.
  List<String> _uniqueSeriesValues() {
    if (seriesKey == null) return [];
    final seen = <String>{};
    final result = <String>[];
    for (final row in data) {
      final v = row[seriesKey!]?.toString() ?? '';
      if (seen.add(v)) result.add(v);
    }
    return result;
  }

  /// Build a two-level lookup: `{dim0Value: {seriesValue: measureValue}}`.
  Map<String, Map<String, double>> _buildLookup(List<String> seriesValues) {
    final lookup = <String, Map<String, double>>{};
    for (final row in data) {
      final d0 = row[dimensionKey]?.toString() ?? '';
      final s = seriesKey != null
          ? (row[seriesKey!]?.toString() ?? '')
          : 'value';
      final val = _getDoubleValue(row[measureKey]);
      lookup.putIfAbsent(d0, () => {})[s] = val;
    }
    return lookup;
  }

  // ---------------------------------------------------------------------------
  // Standard bar chart
  // ---------------------------------------------------------------------------

  void _drawBarChart(
    Canvas canvas,
    Rect area,
    List<double> values,
    List<String> labels,
    double maxVal,
    double range,
  ) {
    if (maxVal == 0) return;
    final barWidth = (area.width / values.length) * 0.7;
    final gap = (area.width / values.length) * 0.15;

    for (var i = 0; i < values.length; i++) {
      final x = area.left + (area.width * i / values.length) + gap;
      final barHeight = (values[i] / maxVal) * area.height;
      final y = area.bottom - barHeight;

      canvas.drawRRect(
        RRect.fromRectAndCorners(
          Rect.fromLTWH(x, y, barWidth, barHeight),
          topLeft: const Radius.circular(3),
          topRight: const Radius.circular(3),
        ),
        Paint()
          ..color = color.withValues(alpha: 0.7)
          ..style = PaintingStyle.fill,
      );

      // Value label on top of bar (only when there are ≤ 20 bars).
      if (values.length <= 20) {
        final tp = TextPainter(
          text: TextSpan(
            text: _formatAxisValue(values[i]),
            style: TextStyle(
              fontSize: 8,
              color: textColor.withValues(alpha: 0.7),
            ),
          ),
          textDirection: TextDirection.ltr,
        )..layout();
        tp.paint(
          canvas,
          Offset(x + barWidth / 2 - tp.width / 2, y - tp.height - 2),
        );
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Horizontal bar chart
  // ---------------------------------------------------------------------------

  void _drawHorizontalBarChart(
    Canvas canvas,
    Rect area,
    List<double> values,
    List<String> labels,
    double maxVal,
  ) {
    if (maxVal == 0 || values.isEmpty) return;

    final slotHeight = area.height / values.length;
    final barHeight = slotHeight * 0.65;
    final barGap = slotHeight * 0.175;

    // Vertical grid lines (X-axis value markers).
    const gridLines = 5;
    final gridPaint = Paint()
      ..color = gridColor.withValues(alpha: 0.15)
      ..strokeWidth = 0.5;

    for (var i = 0; i <= gridLines; i++) {
      final x = area.left + (area.width * i / gridLines);
      canvas.drawLine(Offset(x, area.top), Offset(x, area.bottom), gridPaint);

      // Value label below the chart area.
      final val = maxVal * i / gridLines;
      final tp = TextPainter(
        text: TextSpan(
          text: _formatAxisValue(val),
          style: TextStyle(
            fontSize: 8,
            color: textColor.withValues(alpha: 0.6),
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      tp.paint(canvas, Offset(x - tp.width / 2, area.bottom + 3));
    }

    // Draw bars.
    for (var i = 0; i < values.length; i++) {
      final y = area.top + slotHeight * i + barGap;
      final barWidth = maxVal > 0 ? (values[i] / maxVal) * area.width : 0.0;

      canvas.drawRRect(
        RRect.fromRectAndCorners(
          Rect.fromLTWH(area.left, y, barWidth, barHeight),
          topRight: const Radius.circular(3),
          bottomRight: const Radius.circular(3),
        ),
        Paint()
          ..color = color.withValues(alpha: 0.75)
          ..style = PaintingStyle.fill,
      );

      // Category label on the left.
      final maxLabelChars = max(4, min(16, ((area.left - 8) / 6.5).floor()));
      final rawLabel = labels[i];
      final labelText = rawLabel.length > maxLabelChars
          ? '${rawLabel.substring(0, maxLabelChars)}..'
          : rawLabel;

      final labelTp = TextPainter(
        text: TextSpan(
          text: labelText,
          style: TextStyle(
            fontSize: 9,
            color: textColor.withValues(alpha: 0.8),
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout(maxWidth: area.left - 8);
      labelTp.paint(
        canvas,
        Offset(
          area.left - labelTp.width - 4,
          y + barHeight / 2 - labelTp.height / 2,
        ),
      );

      // Value label at end of bar.
      if (values.length <= 40) {
        final valTp = TextPainter(
          text: TextSpan(
            text: _formatAxisValue(values[i]),
            style: TextStyle(
              fontSize: 8,
              color: textColor.withValues(alpha: 0.7),
            ),
          ),
          textDirection: TextDirection.ltr,
        )..layout();
        valTp.paint(
          canvas,
          Offset(
            area.left + barWidth + 3,
            y + barHeight / 2 - valTp.height / 2,
          ),
        );
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Stacked bar chart
  // ---------------------------------------------------------------------------

  void _drawStackedBarChart(Canvas canvas, Rect area) {
    final dim0Values = _uniqueDim0Values();
    final seriesValues = seriesKey != null ? _uniqueSeriesValues() : ['value'];
    if (dim0Values.isEmpty) return;

    final lookup = _buildLookup(seriesValues);

    // Compute max stacked height (sum of all series for each dim0 group).
    var maxStacked = 0.0;
    for (final d0 in dim0Values) {
      final groupVals = lookup[d0] ?? {};
      final total = seriesValues.fold(
        0.0,
        (sum, s) => sum + (groupVals[s] ?? 0.0),
      );
      if (total > maxStacked) maxStacked = total;
    }
    if (maxStacked == 0) return;

    _drawGrid(canvas, area, maxStacked, 0);

    final slotWidth = area.width / dim0Values.length;
    final barWidth = slotWidth * 0.7;
    final barGap = slotWidth * 0.15;

    for (var xi = 0; xi < dim0Values.length; xi++) {
      final d0 = dim0Values[xi];
      final x = area.left + slotWidth * xi + barGap;
      final groupVals = lookup[d0] ?? {};

      var stackBottom = area.bottom;

      for (var si = 0; si < seriesValues.length; si++) {
        final s = seriesValues[si];
        final val = groupVals[s] ?? 0.0;
        if (val <= 0) continue;

        final segH = (val / maxStacked) * area.height;
        final isTop =
            si == seriesValues.length - 1 ||
            seriesValues
                .skip(si + 1)
                .every((ns) => (groupVals[ns] ?? 0.0) <= 0);

        final barColor = explorerChartColors[si % explorerChartColors.length];

        canvas.drawRRect(
          RRect.fromRectAndCorners(
            Rect.fromLTWH(x, stackBottom - segH, barWidth, segH),
            topLeft: isTop ? const Radius.circular(3) : Radius.zero,
            topRight: isTop ? const Radius.circular(3) : Radius.zero,
          ),
          Paint()
            ..color = barColor.withValues(alpha: 0.75)
            ..style = PaintingStyle.fill,
        );

        stackBottom -= segH;
      }
    }

    _drawAxisLabels(canvas, area, dim0Values);
  }

  // ---------------------------------------------------------------------------
  // Grouped / clustered bar chart
  // ---------------------------------------------------------------------------

  void _drawGroupedBarChart(Canvas canvas, Rect area) {
    final dim0Values = _uniqueDim0Values();
    final seriesValues = seriesKey != null ? _uniqueSeriesValues() : ['value'];
    if (dim0Values.isEmpty) return;

    final lookup = _buildLookup(seriesValues);

    // Max individual bar value across all groups.
    var maxVal = 0.0;
    for (final d0 in dim0Values) {
      final groupVals = lookup[d0] ?? {};
      for (final s in seriesValues) {
        final v = groupVals[s] ?? 0.0;
        if (v > maxVal) maxVal = v;
      }
    }
    if (maxVal == 0) return;

    _drawGrid(canvas, area, maxVal, 0);

    final groupSlotWidth = area.width / dim0Values.length;
    final numSeries = seriesValues.length;
    final subBarWidth =
        (groupSlotWidth * 0.85) / (numSeries == 0 ? 1 : numSeries);
    final groupGap = groupSlotWidth * 0.075;

    for (var xi = 0; xi < dim0Values.length; xi++) {
      final d0 = dim0Values[xi];
      final groupLeft = area.left + groupSlotWidth * xi + groupGap;
      final groupVals = lookup[d0] ?? {};

      for (var si = 0; si < seriesValues.length; si++) {
        final s = seriesValues[si];
        final val = groupVals[s] ?? 0.0;
        final barH = (val / maxVal) * area.height;
        final x = groupLeft + subBarWidth * si;
        final y = area.bottom - barH;

        final barColor = explorerChartColors[si % explorerChartColors.length];

        canvas.drawRRect(
          RRect.fromRectAndCorners(
            Rect.fromLTWH(x, y, subBarWidth - 1, barH),
            topLeft: const Radius.circular(2),
            topRight: const Radius.circular(2),
          ),
          Paint()
            ..color = barColor.withValues(alpha: 0.75)
            ..style = PaintingStyle.fill,
        );
      }
    }

    _drawAxisLabels(canvas, area, dim0Values);
  }

  // ---------------------------------------------------------------------------
  // Line / area chart
  // ---------------------------------------------------------------------------

  void _drawLineChart(
    Canvas canvas,
    Rect area,
    List<double> values,
    List<String> labels,
    double minVal,
    double maxVal,
    double range, {
    bool fill = false,
  }) {
    if (values.length < 2) return;

    // Handle constant values — draw a horizontal line at midpoint.
    final effectiveRange = range == 0 ? 1.0 : range;
    final effectiveMin = range == 0 ? minVal - 0.5 : minVal;

    final points = <Offset>[];
    for (var i = 0; i < values.length; i++) {
      final x = area.left + (area.width * i / (values.length - 1));
      final normalized = (values[i] - effectiveMin) / effectiveRange;
      final y = area.bottom - (normalized * area.height);
      points.add(Offset(x, y));
    }

    // Fill area under the curve.
    if (fill && points.isNotEmpty) {
      final path = Path()
        ..moveTo(points.first.dx, area.bottom)
        ..lineTo(points.first.dx, points.first.dy);
      for (final p in points.skip(1)) {
        path.lineTo(p.dx, p.dy);
      }
      path.lineTo(points.last.dx, area.bottom);
      path.close();

      canvas.drawPath(
        path,
        Paint()
          ..color = color.withValues(alpha: 0.15)
          ..style = PaintingStyle.fill,
      );
    }

    // Line.
    final linePaint = Paint()
      ..color = color
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;

    final linePath = Path()..moveTo(points.first.dx, points.first.dy);
    for (final p in points.skip(1)) {
      linePath.lineTo(p.dx, p.dy);
    }
    canvas.drawPath(linePath, linePaint);

    // Dots.
    for (final p in points) {
      canvas.drawCircle(p, 3, Paint()..color = color);
      canvas.drawCircle(
        p,
        2,
        Paint()
          ..color = AppColors.backgroundDark
          ..style = PaintingStyle.fill,
      );
    }
  }

  // ---------------------------------------------------------------------------
  // Scatter chart
  // ---------------------------------------------------------------------------

  void _drawScatterChart(
    Canvas canvas,
    Rect area,
    List<double> values,
    List<String> labels,
    double minVal,
    double range,
  ) {
    final effectiveRange = range == 0 ? 1.0 : range;
    final effectiveMin = range == 0 ? minVal - 0.5 : minVal;

    for (var i = 0; i < values.length; i++) {
      final x =
          area.left +
          (area.width * i / values.length) +
          (area.width / values.length / 2);
      final normalized = (values[i] - effectiveMin) / effectiveRange;
      final y = area.bottom - (normalized * area.height);
      canvas.drawCircle(
        Offset(x, y),
        4,
        Paint()..color = color.withValues(alpha: 0.7),
      );
    }
  }

  // ---------------------------------------------------------------------------
  // Pie chart
  // ---------------------------------------------------------------------------

  void _drawPieChart(
    Canvas canvas,
    Size size,
    List<double> values,
    List<String> labels,
  ) {
    final total = values.fold(0.0, (a, b) => a + b.abs());
    if (total == 0) return;

    final center = Offset(size.width * 0.4, size.height / 2);
    final radius = min(size.width * 0.35, size.height / 2.5);
    var startAngle = -pi / 2;

    // Draw slices.
    for (var i = 0; i < values.length; i++) {
      final sweep = (values[i].abs() / total) * 2 * pi;
      final paint = Paint()
        ..color = explorerChartColors[i % explorerChartColors.length]
            .withValues(alpha: 0.7)
        ..style = PaintingStyle.fill;

      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        startAngle,
        sweep,
        true,
        paint,
      );

      // Separation border.
      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        startAngle,
        sweep,
        true,
        Paint()
          ..color = AppColors.backgroundDark
          ..strokeWidth = 1.5
          ..style = PaintingStyle.stroke,
      );

      startAngle += sweep;
    }

    // Legend on the right.
    final legendX = size.width * 0.7;
    var legendY = max(20.0, (size.height - values.length * 18) / 2);
    for (var i = 0; i < values.length && i < 15; i++) {
      final c = explorerChartColors[i % explorerChartColors.length];
      final label = labels[i].length > 18
          ? '${labels[i].substring(0, 18)}...'
          : labels[i];
      final pct = (values[i].abs() / total * 100).toStringAsFixed(1);

      canvas.drawRRect(
        RRect.fromRectAndRadius(
          Rect.fromLTWH(legendX, legendY, 8, 8),
          const Radius.circular(2),
        ),
        Paint()..color = c.withValues(alpha: 0.7),
      );

      final tp = TextPainter(
        text: TextSpan(
          text: '$label ($pct%)',
          style: TextStyle(
            fontSize: 9,
            color: textColor.withValues(alpha: 0.8),
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout(maxWidth: size.width - legendX - 12);
      tp.paint(canvas, Offset(legendX + 12, legendY - 1));

      legendY += 18;
    }
  }

  // ---------------------------------------------------------------------------
  // Heatmap
  // ---------------------------------------------------------------------------

  void _drawHeatmap(
    Canvas canvas,
    Rect area,
    List<double> values,
    List<String> labels,
    double minVal,
    double maxVal,
  ) {
    if (values.isEmpty) return;

    final range = maxVal - minVal;
    final cellWidth = area.width / values.length;
    final cellHeight = area.height;

    for (var i = 0; i < values.length; i++) {
      final normalized = range == 0 ? 0.5 : (values[i] - minVal) / range;
      final cellColor = Color.lerp(
        AppColors.primaryCyan.withValues(alpha: 0.1),
        AppColors.error.withValues(alpha: 0.8),
        normalized,
      )!;

      final x = area.left + cellWidth * i;
      canvas.drawRect(
        Rect.fromLTWH(x, area.top, cellWidth - 1, cellHeight),
        Paint()..color = cellColor,
      );

      if (values.length <= 30) {
        final tp = TextPainter(
          text: TextSpan(
            text: _formatAxisValue(values[i]),
            style: TextStyle(
              fontSize: 9,
              color: normalized > 0.5
                  ? Colors.white.withValues(alpha: 0.9)
                  : textColor.withValues(alpha: 0.7),
              fontWeight: FontWeight.w500,
            ),
          ),
          textDirection: TextDirection.ltr,
        )..layout();
        tp.paint(
          canvas,
          Offset(
            x + cellWidth / 2 - tp.width / 2,
            area.top + cellHeight / 2 - tp.height / 2,
          ),
        );
      }
    }

    // Colour scale legend at top-right.
    const scaleWidth = 80.0;
    const scaleHeight = 8.0;
    final scaleX = area.right - scaleWidth;
    final scaleY = area.top - 16;
    for (var i = 0; i < scaleWidth.toInt(); i++) {
      final t = i / scaleWidth;
      final c = Color.lerp(
        AppColors.primaryCyan.withValues(alpha: 0.1),
        AppColors.error.withValues(alpha: 0.8),
        t,
      )!;
      canvas.drawRect(
        Rect.fromLTWH(scaleX + i, scaleY, 1, scaleHeight),
        Paint()..color = c,
      );
    }

    final lowTp = TextPainter(
      text: TextSpan(
        text: _formatAxisValue(minVal),
        style: TextStyle(fontSize: 7, color: textColor.withValues(alpha: 0.5)),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    lowTp.paint(canvas, Offset(scaleX, scaleY - lowTp.height - 1));

    final highTp = TextPainter(
      text: TextSpan(
        text: _formatAxisValue(maxVal),
        style: TextStyle(fontSize: 7, color: textColor.withValues(alpha: 0.5)),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    highTp.paint(
      canvas,
      Offset(scaleX + scaleWidth - highTp.width, scaleY - highTp.height - 1),
    );
  }

  // ---------------------------------------------------------------------------
  // Shared helpers
  // ---------------------------------------------------------------------------

  void _drawGrid(Canvas canvas, Rect area, double maxVal, double minVal) {
    final paint = Paint()
      ..color = gridColor.withValues(alpha: 0.15)
      ..strokeWidth = 0.5;

    const gridLines = 5;
    for (var i = 0; i <= gridLines; i++) {
      final y = area.top + (area.height * i / gridLines);
      canvas.drawLine(Offset(area.left, y), Offset(area.right, y), paint);

      final val = maxVal - (maxVal - minVal) * i / gridLines;
      final tp = TextPainter(
        text: TextSpan(
          text: _formatAxisValue(val),
          style: TextStyle(
            fontSize: 9,
            color: textColor.withValues(alpha: 0.6),
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      tp.paint(canvas, Offset(area.left - tp.width - 6, y - tp.height / 2));
    }
  }

  void _drawAxisLabels(Canvas canvas, Rect area, List<String> labels) {
    final labelWidth = area.width / labels.length;
    final maxChars = max(4, min(20, (labelWidth / 6).floor()));

    for (var i = 0; i < labels.length; i++) {
      final x =
          area.left +
          (area.width * i / labels.length) +
          (area.width / labels.length / 2);
      final label = labels[i].length > maxChars
          ? '${labels[i].substring(0, maxChars)}..'
          : labels[i];
      final tp = TextPainter(
        text: TextSpan(
          text: label,
          style: TextStyle(
            fontSize: 8,
            color: textColor.withValues(alpha: 0.6),
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();

      if (labels.length > 8) {
        canvas.save();
        canvas.translate(x, area.bottom + 4);
        canvas.rotate(0.5); // ~30 degrees
        tp.paint(canvas, Offset.zero);
        canvas.restore();
      } else {
        tp.paint(canvas, Offset(x - tp.width / 2, area.bottom + 4));
      }
    }
  }

  String _formatAxisValue(double val) {
    if (val.abs() >= 1e9) return '${(val / 1e9).toStringAsFixed(1)}B';
    if (val.abs() >= 1e6) return '${(val / 1e6).toStringAsFixed(1)}M';
    if (val.abs() >= 1e3) return '${(val / 1e3).toStringAsFixed(1)}K';
    return val == val.roundToDouble()
        ? val.toInt().toString()
        : val.toStringAsFixed(1);
  }

  @override
  bool shouldRepaint(covariant ExplorerChartPainter oldDelegate) =>
      data != oldDelegate.data ||
      dimensionKey != oldDelegate.dimensionKey ||
      measureKey != oldDelegate.measureKey ||
      chartType != oldDelegate.chartType ||
      !listEquals(measures, oldDelegate.measures) ||
      seriesKey != oldDelegate.seriesKey;
}
