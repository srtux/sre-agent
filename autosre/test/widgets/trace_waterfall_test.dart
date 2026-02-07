import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/widgets/syncfusion_trace_waterfall.dart';
import 'package:autosre/models/adk_schema.dart';

void main() {
  testWidgets('SyncfusionTraceWaterfall renders without error',
      (WidgetTester tester) async {
    final trace = Trace(
      traceId: 'test-trace',
      spans: [
        SpanInfo(
          spanId: 's1',
          traceId: 'test-trace',
          name: 'test-service:test-span',
          startTime: DateTime.now(),
          endTime: DateTime.now().add(const Duration(milliseconds: 100)),
          attributes: <String, dynamic>{},
          status: 'OK',
        ),
      ],
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 800,
            height: 600,
            child: SyncfusionTraceWaterfall(trace: trace),
          ),
        ),
      ),
    );

    // Allow chart to render (Syncfusion charts use animations)
    await tester.pump(const Duration(seconds: 1));

    // Verify widget renders
    expect(find.byType(SyncfusionTraceWaterfall), findsOneWidget);

    // Verify trace ID is displayed in header
    expect(find.text('test-trace'), findsOneWidget);

    // Verify span count badge
    expect(find.text('1 spans'), findsOneWidget);
  });

  testWidgets('SyncfusionTraceWaterfall shows empty state for empty trace',
      (WidgetTester tester) async {
    final trace = Trace(
      traceId: 'empty-trace',
      spans: [],
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 800,
            height: 600,
            child: SyncfusionTraceWaterfall(trace: trace),
          ),
        ),
      ),
    );

    await tester.pump(const Duration(seconds: 1));

    // Widget should still render gracefully
    expect(find.byType(SyncfusionTraceWaterfall), findsOneWidget);
  });

  testWidgets('SyncfusionTraceWaterfall renders service legend',
      (WidgetTester tester) async {
    final now = DateTime.now();
    final trace = Trace(
      traceId: 'multi-service-trace',
      spans: [
        SpanInfo(
          spanId: 's1',
          traceId: 'multi-service-trace',
          name: 'frontend:request',
          startTime: now,
          endTime: now.add(const Duration(milliseconds: 200)),
          attributes: <String, dynamic>{},
          status: 'OK',
        ),
        SpanInfo(
          spanId: 's2',
          traceId: 'multi-service-trace',
          name: 'backend:process',
          startTime: now.add(const Duration(milliseconds: 10)),
          endTime: now.add(const Duration(milliseconds: 150)),
          attributes: <String, dynamic>{},
          status: 'OK',
          parentSpanId: 's1',
        ),
      ],
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 800,
            height: 600,
            child: SyncfusionTraceWaterfall(trace: trace),
          ),
        ),
      ),
    );

    await tester.pump(const Duration(seconds: 1));

    // Verify widget renders with multiple spans
    expect(find.byType(SyncfusionTraceWaterfall), findsOneWidget);

    // Verify service names appear in legend
    expect(find.text('frontend'), findsOneWidget);
    expect(find.text('backend'), findsOneWidget);
  });
}
