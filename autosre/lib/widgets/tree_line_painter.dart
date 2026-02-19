import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class TreeLinePainter extends CustomPainter {
  final int depth;
  final bool hasChildren;
  final bool isLastChild;

  TreeLinePainter({
    required this.depth,
    required this.hasChildren,
    this.isLastChild = false,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (depth == 0) return;

    final paint = Paint()
      ..color = AppColors.surfaceBorder
      ..strokeWidth = 1.0
      ..style = PaintingStyle.stroke;

    final halfHeight = size.height / 2;

    for (var i = 0; i < depth; i++) {
      final xOffset = i * 16.0 + 8.0;

      // Draw vertical line for all ancestors if not the last child
      // (Simplified for now: we draw the vertical line down)

      if (i == depth - 1) {
        // Draw the L or T shape for the current node
        canvas.drawLine(
          Offset(xOffset, 0),
          Offset(xOffset, isLastChild ? halfHeight : size.height),
          paint,
        );
        // Draw the horizontal connector
        canvas.drawLine(
          Offset(xOffset, halfHeight),
          Offset(xOffset + 8.0, halfHeight),
          paint,
        );
      } else {
        // Draw vertical line for ancestors
        canvas.drawLine(
          Offset(xOffset, 0),
          Offset(xOffset, size.height),
          paint,
        );
      }
    }
  }

  @override
  bool shouldRepaint(covariant TreeLinePainter oldDelegate) {
    return oldDelegate.depth != depth ||
        oldDelegate.hasChildren != hasChildren ||
        oldDelegate.isLastChild != isLastChild;
  }
}
