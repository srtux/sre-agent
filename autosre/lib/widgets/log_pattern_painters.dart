import 'dart:math' as math;
import 'package:flutter/material.dart';

/// Mini sparkline painter for log pattern frequency distribution.
class FrequencySparklinePainter extends CustomPainter {
  final List<double> values;
  final Color color;
  final double animation;

  FrequencySparklinePainter({
    required this.values,
    required this.color,
    required this.animation,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (values.isEmpty) return;

    final maxVal = values.reduce(math.max);
    if (maxVal == 0) return;

    final barWidth = size.width / values.length - 1;
    final paint = Paint()..color = color.withValues(alpha: 0.6);

    for (var i = 0; i < values.length; i++) {
      final normalizedHeight = (values[i] / maxVal) * size.height * animation;
      final rect = Rect.fromLTWH(
        i * (barWidth + 1),
        size.height - normalizedHeight,
        barWidth,
        normalizedHeight,
      );
      canvas.drawRRect(
        RRect.fromRectAndRadius(rect, const Radius.circular(1)),
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant FrequencySparklinePainter oldDelegate) {
    return oldDelegate.animation != animation;
  }
}

/// Bar chart painter for log pattern frequency distribution detail view.
class FrequencyBarPainter extends CustomPainter {
  final List<double> values;
  final Color color;

  FrequencyBarPainter({required this.values, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    if (values.isEmpty) return;

    final maxVal = values.reduce(math.max);
    if (maxVal == 0) return;

    final barWidth = size.width / values.length - 2;

    for (var i = 0; i < values.length; i++) {
      final normalizedHeight = (values[i] / maxVal) * size.height;
      final rect = Rect.fromLTWH(
        i * (barWidth + 2),
        size.height - normalizedHeight,
        barWidth,
        normalizedHeight,
      );

      final gradient = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [color, color.withValues(alpha: 0.5)],
      );

      final paint = Paint()..shader = gradient.createShader(rect);
      canvas.drawRRect(
        RRect.fromRectAndRadius(rect, const Radius.circular(2)),
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
