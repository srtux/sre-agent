import 'dart:math';

import 'package:flutter/material.dart';

import '../../theme/app_theme.dart';

/// Chart type for the visual data explorer.
enum ExplorerChartType { bar, line, area, scatter, pie, heatmap, table }

/// Shared chart color palette for the visual data explorer.
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
/// Supports bar, line, area, scatter, pie, and heatmap chart types.
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

  ExplorerChartPainter({
    required this.data,
    required this.dimensionKey,
    required this.measureKey,
    required this.measures,
    required this.chartType,
    required this.color,
    required this.textColor,
    required this.gridColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (data.isEmpty) return;

    final values = data.map((row) {
      final v = row[measureKey];
      if (v is num) return v.toDouble();
      return double.tryParse(v?.toString() ?? '') ?? 0.0;
    }).toList();

    final labels = data.map((row) => row[dimensionKey]?.toString() ?? '').toList();

    if (values.isEmpty) return;

    final maxVal = values.reduce(max);
    final minVal = values.reduce(min);
    final range = maxVal - minVal;

    final chartArea = Rect.fromLTRB(60, 20, size.width - 20, size.height - 40);

    switch (chartType) {
      case ExplorerChartType.bar:
        _drawGrid(canvas, chartArea, maxVal, minVal);
        _drawBarChart(canvas, chartArea, values, labels, maxVal, range);
        _drawAxisLabels(canvas, chartArea, labels);
        break;
      case ExplorerChartType.line:
      case ExplorerChartType.area:
        _drawGrid(canvas, chartArea, maxVal, minVal);
        _drawLineChart(canvas, chartArea, values, labels, minVal, maxVal, range,
            fill: chartType == ExplorerChartType.area);
        _drawAxisLabels(canvas, chartArea, labels);
        break;
      case ExplorerChartType.scatter:
        _drawGrid(canvas, chartArea, maxVal, minVal);
        _drawScatterChart(canvas, chartArea, values, labels, minVal, range);
        _drawAxisLabels(canvas, chartArea, labels);
        break;
      case ExplorerChartType.pie:
        _drawPieChart(canvas, size, values, labels);
        break;
      case ExplorerChartType.heatmap:
        _drawHeatmap(canvas, chartArea, values, labels, minVal, maxVal);
        _drawAxisLabels(canvas, chartArea, labels);
        break;
      case ExplorerChartType.table:
        // Handled by widget, not painter
        break;
    }
  }

  void _drawGrid(Canvas canvas, Rect area, double maxVal, double minVal) {
    final paint = Paint()
      ..color = gridColor.withValues(alpha: 0.15)
      ..strokeWidth = 0.5;

    const gridLines = 5;
    for (var i = 0; i <= gridLines; i++) {
      final y = area.top + (area.height * i / gridLines);
      canvas.drawLine(Offset(area.left, y), Offset(area.right, y), paint);

      // Y-axis labels
      final val = maxVal - (maxVal - minVal) * i / gridLines;
      final tp = TextPainter(
        text: TextSpan(
          text: _formatAxisValue(val),
          style: TextStyle(fontSize: 9, color: textColor.withValues(alpha: 0.6)),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      tp.paint(canvas, Offset(area.left - tp.width - 6, y - tp.height / 2));
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

  void _drawBarChart(Canvas canvas, Rect area, List<double> values,
      List<String> labels, double maxVal, double range) {
    if (maxVal == 0) return;
    final barWidth = (area.width / values.length) * 0.7;
    final gap = (area.width / values.length) * 0.15;

    for (var i = 0; i < values.length; i++) {
      final x = area.left + (area.width * i / values.length) + gap;
      final barHeight = (values[i] / maxVal) * area.height;
      final y = area.bottom - barHeight;

      final paint = Paint()
        ..color = color.withValues(alpha: 0.7)
        ..style = PaintingStyle.fill;

      canvas.drawRRect(
        RRect.fromRectAndCorners(
          Rect.fromLTWH(x, y, barWidth, barHeight),
          topLeft: const Radius.circular(3),
          topRight: const Radius.circular(3),
        ),
        paint,
      );

      // Value label on top of bar
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
        tp.paint(canvas,
            Offset(x + barWidth / 2 - tp.width / 2, y - tp.height - 2));
      }
    }
  }

  void _drawLineChart(Canvas canvas, Rect area, List<double> values,
      List<String> labels, double minVal, double maxVal, double range,
      {bool fill = false}) {
    if (values.length < 2) return;

    // Handle constant values (range == 0) — draw a horizontal line at midpoint
    final effectiveRange = range == 0 ? 1.0 : range;
    final effectiveMin = range == 0 ? minVal - 0.5 : minVal;

    final points = <Offset>[];
    for (var i = 0; i < values.length; i++) {
      final x = area.left + (area.width * i / (values.length - 1));
      final normalized = (values[i] - effectiveMin) / effectiveRange;
      final y = area.bottom - (normalized * area.height);
      points.add(Offset(x, y));
    }

    // Fill area
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

    // Draw line
    final linePaint = Paint()
      ..color = color
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;

    final linePath = Path()..moveTo(points.first.dx, points.first.dy);
    for (final p in points.skip(1)) {
      linePath.lineTo(p.dx, p.dy);
    }
    canvas.drawPath(linePath, linePaint);

    // Draw dots
    for (final p in points) {
      canvas.drawCircle(p, 3, Paint()..color = color);
      canvas.drawCircle(
          p,
          2,
          Paint()
            ..color = AppColors.backgroundDark
            ..style = PaintingStyle.fill);
    }
  }

  void _drawScatterChart(Canvas canvas, Rect area, List<double> values,
      List<String> labels, double minVal, double range) {
    // Handle constant values gracefully
    final effectiveRange = range == 0 ? 1.0 : range;
    final effectiveMin = range == 0 ? minVal - 0.5 : minVal;

    for (var i = 0; i < values.length; i++) {
      final x = area.left + (area.width * i / values.length) + (area.width / values.length / 2);
      final normalized = (values[i] - effectiveMin) / effectiveRange;
      final y = area.bottom - (normalized * area.height);
      canvas.drawCircle(
          Offset(x, y), 4, Paint()..color = color.withValues(alpha: 0.7));
    }
  }

  void _drawPieChart(
      Canvas canvas, Size size, List<double> values, List<String> labels) {
    final total = values.fold(0.0, (a, b) => a + b.abs());
    if (total == 0) return;

    final center = Offset(size.width * 0.4, size.height / 2);
    final radius = min(size.width * 0.35, size.height / 2.5);
    var startAngle = -pi / 2;

    // Draw slices
    for (var i = 0; i < values.length; i++) {
      final sweep = (values[i].abs() / total) * 2 * pi;
      final paint = Paint()
        ..color = explorerChartColors[i % explorerChartColors.length].withValues(alpha: 0.7)
        ..style = PaintingStyle.fill;

      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        startAngle,
        sweep,
        true,
        paint,
      );

      // Slice border for separation
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

    // Draw legend on the right side
    final legendX = size.width * 0.7;
    var legendY = max(20.0, (size.height - values.length * 18) / 2);
    for (var i = 0; i < values.length && i < 15; i++) {
      final color = explorerChartColors[i % explorerChartColors.length];
      final label = labels[i].length > 18
          ? '${labels[i].substring(0, 18)}...'
          : labels[i];
      final pct = (values[i].abs() / total * 100).toStringAsFixed(1);

      // Color swatch
      canvas.drawRRect(
        RRect.fromRectAndRadius(
          Rect.fromLTWH(legendX, legendY, 8, 8),
          const Radius.circular(2),
        ),
        Paint()..color = color.withValues(alpha: 0.7),
      );

      // Label
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

  void _drawHeatmap(Canvas canvas, Rect area, List<double> values,
      List<String> labels, double minVal, double maxVal) {
    if (values.isEmpty) return;

    final range = maxVal - minVal;
    final cellWidth = area.width / values.length;
    final cellHeight = area.height;

    for (var i = 0; i < values.length; i++) {
      // Normalize to 0..1 for color intensity
      final normalized = range == 0 ? 0.5 : (values[i] - minVal) / range;

      // Interpolate from cool (low) to hot (high)
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

      // Value label inside cell
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

    // Color scale legend at top-right
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
    // Scale labels
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
        canvas, Offset(scaleX + scaleWidth - highTp.width, scaleY - highTp.height - 1));
  }

  void _drawAxisLabels(Canvas canvas, Rect area, List<String> labels) {
    // Determine max label length based on available space
    final labelWidth = area.width / labels.length;
    final maxChars = max(4, min(20, (labelWidth / 6).floor()));

    for (var i = 0; i < labels.length; i++) {
      final x = area.left + (area.width * i / labels.length) + (area.width / labels.length / 2);
      final label = labels[i].length > maxChars
          ? '${labels[i].substring(0, maxChars)}..'
          : labels[i];
      final tp = TextPainter(
        text: TextSpan(
          text: label,
          style: TextStyle(fontSize: 8, color: textColor.withValues(alpha: 0.6)),
        ),
        textDirection: TextDirection.ltr,
      )..layout();

      // Rotate labels if many items
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

  @override
  bool shouldRepaint(covariant ExplorerChartPainter oldDelegate) =>
      data != oldDelegate.data ||
      dimensionKey != oldDelegate.dimensionKey ||
      measureKey != oldDelegate.measureKey ||
      chartType != oldDelegate.chartType ||
      measures != oldDelegate.measures;
}
