import 'dart:math' as math;

import 'package:flutter/material.dart';

/// Describes a directed edge path between two graph nodes for rendering.
class EdgePath {
  /// Starting point of the edge.
  final Offset start;

  /// Ending point of the edge.
  final Offset end;

  /// Color of the edge stroke.
  final Color color;

  /// Stroke width (1-6), typically scaled by call count.
  final double thickness;

  /// Whether this edge represents a back-edge (cycle).
  final bool isBackEdge;

  /// Normalized flow weight (0-1) controlling animation speed.
  final double flowWeight;

  /// Source node identifier for highlight matching.
  final String sourceId;

  /// Target node identifier for highlight matching.
  final String targetId;

  const EdgePath({
    required this.start,
    required this.end,
    required this.color,
    this.thickness = 2.0,
    this.isBackEdge = false,
    this.flowWeight = 0.5,
    required this.sourceId,
    required this.targetId,
  });
}

/// A [CustomPainter] that draws animated "marching ants" flowing-particle
/// edges between agent graph nodes using Bezier curves.
///
/// The animation is driven by [animationValue] (0.0–1.0) from an external
/// [AnimationController]. When [highlightedNodeIds] is set, edges not
/// connected to highlighted nodes are dimmed to [dimOpacity].
class AnimatedEdgePainter extends CustomPainter {
  /// The list of edge paths to draw.
  final List<EdgePath> edges;

  /// Current animation progress (0.0–1.0) for the marching-ants effect.
  final double animationValue;

  /// When non-null, only edges connected to these nodes are fully opaque.
  final Set<String>? highlightedNodeIds;

  /// Opacity applied to edges not connected to any highlighted node.
  final double dimOpacity;

  AnimatedEdgePainter({
    required this.edges,
    required this.animationValue,
    this.highlightedNodeIds,
    this.dimOpacity = 0.2,
  }) : super(repaint: null);

  @override
  void paint(Canvas canvas, Size size) {
    for (final edge in edges) {
      _drawEdge(canvas, edge);
    }
  }

  void _drawEdge(Canvas canvas, EdgePath edge) {
    final isHighlighted = highlightedNodeIds == null ||
        highlightedNodeIds!.contains(edge.sourceId) ||
        highlightedNodeIds!.contains(edge.targetId);

    final effectiveOpacity = isHighlighted ? 1.0 : dimOpacity;

    // Build the Bezier path
    final path = Path();
    path.moveTo(edge.start.dx, edge.start.dy);

    final dx = edge.end.dx - edge.start.dx;
    final controlOffset = edge.isBackEdge ? 0.6 : 0.3;

    final cp1 = Offset(
      edge.start.dx + dx * controlOffset,
      edge.start.dy,
    );
    final cp2 = Offset(
      edge.end.dx - dx * controlOffset,
      edge.end.dy,
    );
    path.cubicTo(cp1.dx, cp1.dy, cp2.dx, cp2.dy, edge.end.dx, edge.end.dy);

    // Base stroke
    final basePaint = Paint()
      ..color = edge.color.withValues(alpha: 0.35 * effectiveOpacity)
      ..strokeWidth = edge.thickness
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    if (edge.isBackEdge) {
      basePaint.strokeWidth = edge.thickness * 0.8;
    }

    canvas.drawPath(path, basePaint);

    // Marching-ants overlay
    _drawMarchingAnts(canvas, path, edge, effectiveOpacity);

    // Arrow head at the end
    _drawArrowHead(canvas, edge, cp2, effectiveOpacity);
  }

  void _drawMarchingAnts(
    Canvas canvas,
    Path path,
    EdgePath edge,
    double effectiveOpacity,
  ) {
    const dashLength = 8.0;
    const gapLength = 12.0;
    const cycleLength = dashLength + gapLength;

    final metrics = path.computeMetrics();
    for (final metric in metrics) {
      final totalLength = metric.length;
      if (totalLength < 1.0) continue;

      final speed = 0.5 + edge.flowWeight * 0.5;
      final offset = animationValue * totalLength * speed;

      final antPaint = Paint()
        ..color = edge.color.withValues(alpha: 0.85 * effectiveOpacity)
        ..strokeWidth = edge.thickness * 0.6
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round;

      var pos = (offset % cycleLength);
      while (pos < totalLength) {
        final dashEnd = math.min(pos + dashLength, totalLength);
        if (dashEnd > pos) {
          final dashPath = metric.extractPath(pos, dashEnd);
          canvas.drawPath(dashPath, antPaint);
        }
        pos += cycleLength;
      }
    }
  }

  void _drawArrowHead(
    Canvas canvas,
    EdgePath edge,
    Offset controlPoint,
    double effectiveOpacity,
  ) {
    // Direction from last control point to end
    final dir = edge.end - controlPoint;
    final len = dir.distance;
    if (len < 1.0) return;

    final unitDir = dir / len;
    final perp = Offset(-unitDir.dy, unitDir.dx);

    const arrowSize = 6.0;
    final tip = edge.end;
    final left = tip - unitDir * arrowSize + perp * (arrowSize * 0.5);
    final right = tip - unitDir * arrowSize - perp * (arrowSize * 0.5);

    final arrowPath = Path()
      ..moveTo(tip.dx, tip.dy)
      ..lineTo(left.dx, left.dy)
      ..lineTo(right.dx, right.dy)
      ..close();

    final arrowPaint = Paint()
      ..color = edge.color.withValues(alpha: 0.9 * effectiveOpacity)
      ..style = PaintingStyle.fill;

    canvas.drawPath(arrowPath, arrowPaint);
  }

  @override
  bool shouldRepaint(covariant AnimatedEdgePainter oldDelegate) =>
      animationValue != oldDelegate.animationValue ||
      edges != oldDelegate.edges ||
      highlightedNodeIds != oldDelegate.highlightedNodeIds ||
      dimOpacity != oldDelegate.dimOpacity;
}
