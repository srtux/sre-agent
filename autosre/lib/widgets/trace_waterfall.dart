
import 'package:flutter/material.dart';
import 'dart:ui' as ui;

import '../models/adk_schema.dart';

class TraceWaterfall extends StatelessWidget {
  final Trace trace;

  const TraceWaterfall({super.key, required this.trace});

  @override
  Widget build(BuildContext context) {
    if (trace.spans.isEmpty) {
      return const Center(child: Text("No spans in trace"));
    }

    // Sort spans by start time
    final sortedSpans = List<SpanInfo>.from(trace.spans)
      ..sort((a, b) => a.startTime.compareTo(b.startTime));

    final startTime = sortedSpans.first.startTime;
    final totalDuration = sortedSpans.last.endTime.difference(startTime).inMicroseconds;

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(8.0),
          child: Text("Trace: ${trace.traceId} (${totalDuration / 1000} ms)", style: Theme.of(context).textTheme.titleMedium),
        ),
        Expanded(
          child: SingleChildScrollView(
            scrollDirection: Axis.vertical,
            child: SizedBox(
                height: sortedSpans.length * 40.0 + 50, // Height based on row count
                child: CustomPaint(
                painter: _WaterfallPainter(
                    spans: sortedSpans,
                    traceStartTime: startTime,
                    traceDurationMicros: totalDuration,
                    theme: Theme.of(context),
                ),
                size: Size.infinite,
                ),
            ),
          ),
        ),
      ],
    );
  }
}

class _WaterfallPainter extends CustomPainter {
  final List<SpanInfo> spans;
  final DateTime traceStartTime;
  final int traceDurationMicros;
  final ThemeData theme;

  _WaterfallPainter({
    required this.spans,
    required this.traceStartTime,
    required this.traceDurationMicros,
    required this.theme,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..style = PaintingStyle.fill;
    final textPainter = TextPainter(textDirection: ui.TextDirection.ltr);

    // Draw background rows
    double rowHeight = 40.0;
    for (int i = 0; i < spans.length; i++) {
        if (i % 2 == 0) {
            paint.color = theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.3);
            canvas.drawRect(Rect.fromLTWH(0, i * rowHeight, size.width, rowHeight), paint);
        }
    }

    // Draw Spans
    for (int i = 0; i < spans.length; i++) {
      final span = spans[i];
      final offsetMicros = span.startTime.difference(traceStartTime).inMicroseconds;
      final durationMicros = span.duration.inMicroseconds;

      // Calculate X position and Width as percentage of total duration
      double startX = (offsetMicros / traceDurationMicros) * size.width;
      double width = (durationMicros / traceDurationMicros) * size.width;

      // Min width for visibility
      if (width < 2) width = 2;

      // Draw Span Bar
      paint.color = span.status == 'ERROR' ? theme.colorScheme.error : theme.colorScheme.primary;

      // Slight padding within the row
      final rect = Rect.fromLTWH(startX, i * rowHeight + 8, width, rowHeight - 16);
      canvas.drawRRect(RRect.fromRectAndRadius(rect, const Radius.circular(4)), paint);

      // Draw Label
      textPainter.text = TextSpan(
        text: "${span.name} (${span.duration.inMilliseconds}ms)",
        style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.onSurface),
      );
      textPainter.layout();

      // Label placement (right of bar if safe, otherwise inside/left)
      double textX = startX + width + 5;
      if (textX + textPainter.width > size.width) {
          textX = startX - textPainter.width - 5;
      }
      textPainter.paint(canvas, Offset(textX, i * rowHeight + 12));
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}
