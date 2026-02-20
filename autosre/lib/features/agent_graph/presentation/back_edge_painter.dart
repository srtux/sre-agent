import 'dart:math' as math;

import 'package:flutter/material.dart';

/// Describes a single back-edge arc to be rendered by [BackEdgePainter].
class BackEdgePath {
  /// Center of the source node.
  final Offset start;

  /// Center of the target node.
  final Offset end;

  /// Stroke color.
  final Color color;

  /// Stroke width.
  final double thickness;

  /// Source node identifier (for highlight matching).
  final String sourceId;

  /// Target node identifier (for highlight matching).
  final String targetId;

  /// Index used to stagger arc heights when multiple back-edges overlap.
  final int edgeIndex;

  const BackEdgePath({
    required this.start,
    required this.end,
    required this.color,
    this.thickness = 2.0,
    required this.sourceId,
    required this.targetId,
    this.edgeIndex = 0,
  });
}

/// [CustomPainter] that draws sweeping cubic bezier arcs for graph back-edges.
///
/// Rendered BEHIND the `FlNodeEditorWidget` in the Stack so arcs appear under
/// regular DAG edges and nodes. Supports:
/// - Marching-ants animation via [marchingAntsPhase]
/// - Arrow heads at the target end, rotated to match bezier tangent
/// - Path highlighting — dims edges not connected to [highlightedPath]
class BackEdgePainter extends CustomPainter {
  /// The back-edge arcs to draw.
  final List<BackEdgePath> edges;

  /// Animation phase for marching ants (0.0–1.0), driven by a repeating
  /// [AnimationController].
  final double marchingAntsPhase;

  /// When non-empty, only edges whose source or target is in this set are
  /// drawn at full opacity.
  final Set<String> highlightedPath;

  /// Opacity applied to edges not in the highlighted path.
  final double dimOpacity;

  BackEdgePainter({
    required this.edges,
    required this.marchingAntsPhase,
    this.highlightedPath = const {},
    this.dimOpacity = 0.2,
  }) : super(repaint: null); // repainted via AnimationController listener

  @override
  void paint(Canvas canvas, Size size) {
    for (final edge in edges) {
      _drawBackEdge(canvas, size, edge);
    }
  }

  void _drawBackEdge(Canvas canvas, Size size, BackEdgePath edge) {
    final isHighlighted = highlightedPath.isEmpty ||
        highlightedPath.contains(edge.sourceId) ||
        highlightedPath.contains(edge.targetId);
    final effectiveOpacity = isHighlighted ? 1.0 : dimOpacity;

    // Compute the graph bounding box center from the two endpoints
    // (in practice we'd want the full graph bounds, but the two endpoints
    // give a good enough local reference).
    final midY = (edge.start.dy + edge.end.dy) / 2;
    final spanY = (edge.start.dy - edge.end.dy).abs();
    final margin = 80.0 + 30.0 * edge.edgeIndex;

    // All arcs sweep to the left of the leftmost endpoint (natural direction
    // for back-edges in a left-to-right layout). Even-indexed arcs curve
    // upward, odd-indexed arcs curve downward to reduce overlap.
    final arcSign = edge.edgeIndex.isEven ? -1.0 : 1.0;
    final cpX = math.min(edge.start.dx, edge.end.dx) - margin;
    final cpOffsetY = (spanY / 2 + margin) * arcSign;

    final cp1 = Offset(cpX, midY + cpOffsetY);
    final cp2 = Offset(cpX, midY + cpOffsetY);

    final path = Path()
      ..moveTo(edge.start.dx, edge.start.dy)
      ..cubicTo(
        cp1.dx,
        cp1.dy,
        cp2.dx,
        cp2.dy,
        edge.end.dx,
        edge.end.dy,
      );

    // Base dashed stroke.
    final basePaint = Paint()
      ..color = edge.color.withValues(alpha: 0.3 * effectiveOpacity)
      ..strokeWidth = edge.thickness
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    canvas.drawPath(path, basePaint);

    // Marching ants overlay.
    _drawMarchingAnts(canvas, path, edge, effectiveOpacity);

    // Arrow head at endpoint.
    _drawArrowHead(canvas, edge, cp2, effectiveOpacity);
  }

  void _drawMarchingAnts(
    Canvas canvas,
    Path path,
    BackEdgePath edge,
    double effectiveOpacity,
  ) {
    const dashLength = 6.0;
    const gapLength = 10.0;
    const cycleLength = dashLength + gapLength;

    final metrics = path.computeMetrics();
    for (final metric in metrics) {
      final totalLength = metric.length;
      if (totalLength < 1.0) continue;

      final offset = marchingAntsPhase * totalLength;

      final antPaint = Paint()
        ..color = edge.color.withValues(alpha: 0.7 * effectiveOpacity)
        ..strokeWidth = edge.thickness * 0.6
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round;

      var pos = offset % cycleLength;
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
    BackEdgePath edge,
    Offset controlPoint,
    double effectiveOpacity,
  ) {
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
      ..color = edge.color.withValues(alpha: 0.8 * effectiveOpacity)
      ..style = PaintingStyle.fill;

    canvas.drawPath(arrowPath, arrowPaint);
  }

  @override
  bool shouldRepaint(covariant BackEdgePainter oldDelegate) =>
      marchingAntsPhase != oldDelegate.marchingAntsPhase ||
      edges != oldDelegate.edges ||
      highlightedPath != oldDelegate.highlightedPath ||
      dimOpacity != oldDelegate.dimOpacity;
}
