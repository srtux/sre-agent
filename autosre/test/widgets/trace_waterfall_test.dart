import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/widgets/trace_waterfall.dart';
import 'package:autosre/models/adk_schema.dart';

void main() {
  testWidgets('TraceWaterfall renders without error', (
    WidgetTester tester,
  ) async {
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
            child: TraceWaterfall(trace: trace),
          ),
        ),
      ),
    );

    // Allow chart to render (Syncfusion charts use animations)
    await tester.pump(const Duration(seconds: 1));

    // Verify widget renders
    expect(find.byType(TraceWaterfall), findsOneWidget);

    // Verify trace ID is displayed in header
    expect(find.text('test-trace'), findsOneWidget);

    // Verify span count badge
    expect(find.text('1 spans'), findsOneWidget);

    // Verify new horizontal scroll structure
    expect(find.byType(SingleChildScrollView), findsNWidgets(2));

    // Verify tooltips wrap the layout spans directly
    expect(find.byType(Tooltip), findsWidgets);
  });

  testWidgets('TraceWaterfall shows empty state for empty trace', (
    WidgetTester tester,
  ) async {
    final trace = Trace(traceId: 'empty-trace', spans: []);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 800,
            height: 600,
            child: TraceWaterfall(trace: trace),
          ),
        ),
      ),
    );

    await tester.pump(const Duration(seconds: 1));

    // Widget should still render gracefully
    expect(find.byType(TraceWaterfall), findsOneWidget);
  });

  testWidgets('TraceWaterfall renders service legend', (
    WidgetTester tester,
  ) async {
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
            child: TraceWaterfall(trace: trace),
          ),
        ),
      ),
    );

    await tester.pump(const Duration(seconds: 1));

    // Verify widget renders with multiple spans
    expect(find.byType(TraceWaterfall), findsOneWidget);

    // Verify service names appear in legend and structure
    expect(find.text('frontend'), findsWidgets);
    expect(find.text('backend'), findsWidgets);
  });

  testWidgets('TraceWaterfall displays GenAI semantic attributes', (
    WidgetTester tester,
  ) async {
    final now = DateTime.now();
    final trace = Trace(
      traceId: 'genai-trace',
      spans: [
        SpanInfo(
          spanId: 's1',
          traceId: 'genai-trace',
          name: 'generate_content',
          startTime: now,
          endTime: now.add(const Duration(milliseconds: 200)),
          attributes: <String, dynamic>{
            'gen_ai.system': 'vertex_ai',
            'gen_ai.request.model': 'gemini-2.5-flash',
            'gen_ai.usage.input_tokens': 1500,
            'gen_ai.usage.output_tokens': 42,
          },
          status: 'OK',
        ),
      ],
    );

    // We need to inject ExplorerQueryService to fetch logs for the panel
    // but since we are just testing layout, we can let it fail gracefully.
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 1200,
            height: 800,
            child: TraceWaterfall(trace: trace),
          ),
        ),
      ),
    );

    await tester.pump(const Duration(seconds: 1));

    // Verify side pane is not present initially
    expect(find.text('GenAI Tokens'), findsNothing);

    // Ensure the text is scrolled into view (if applicable) and then tap it
    final rowTextFinder = find.text('generate_content').last;
    await tester.ensureVisible(rowTextFinder);
    await tester.tap(rowTextFinder);
    await tester.pumpAndSettle();

    // Verify side pane renders tokens
    expect(find.text('GenAI Tokens'), findsOneWidget);
    expect(find.text('1.5K (in), 42 (out)'), findsOneWidget);
    expect(find.text('Related Attributes'), findsOneWidget);

    // SelectableText creates an EditableText child, so find.text might not spot it reliably in some configs
    final selectableTexts = tester.widgetList<SelectableText>(
      find.byType(SelectableText),
    );
    expect(
      selectableTexts.any((st) => st.data == 'gen_ai.request.model'),
      isTrue,
    );
    expect(selectableTexts.any((st) => st.data == 'gemini-2.5-flash'), isTrue);
  });

  testWidgets('TraceWaterfall toggles Graph layout mode', (
    WidgetTester tester,
  ) async {
    final now = DateTime.now();
    final trace = Trace(
      traceId: 'graph-trace',
      spans: [
        SpanInfo(
          spanId: 'root',
          traceId: 'graph-trace',
          name: 'root',
          startTime: now,
          endTime: now.add(const Duration(milliseconds: 200)),
          attributes: <String, dynamic>{},
          status: 'OK',
        ),
      ],
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            width: 1200,
            height: 800,
            child: TraceWaterfall(trace: trace),
          ),
        ),
      ),
    );

    await tester.pump(const Duration(seconds: 1));

    // 'Graph' text button should be visible in the toggle group
    expect(find.text('Graph'), findsOneWidget);

    // Ensure it's in view (e.g. if inside a scrolling header)
    final graphToggleFinder = find.text('Graph').last;
    await tester.ensureVisible(graphToggleFinder);
    await tester.tap(graphToggleFinder);
    await tester.pumpAndSettle();

    // At this point _buildGraphView is called, which centers "Graph View Placeholder"
    // or renders graphview. Let's look for our InteractiveViewer or custom text.
    expect(find.byType(InteractiveViewer), findsWidgets);
  });
}
