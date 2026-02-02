import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/widgets/trace_waterfall.dart';
import 'package:autosre/models/adk_schema.dart';

void main() {
  testWidgets('TraceWaterfall shows warning banner for clock skew', (WidgetTester tester) async {
    final trace = Trace(
      traceId: 'test-trace',
      spans: [
        SpanInfo(
          spanId: 's1',
          traceId: 'test-trace',
          name: 'test-service:test-span',
          startTime: DateTime.now(),
          endTime: DateTime.now().add(const Duration(milliseconds: 100)),
          attributes: <String, dynamic>{
            '/agent/quality/type': 'clock_skew',
            '/agent/quality/issue': 'This span has clock skew',
          },
          status: 'OK',
        ),
      ],
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: TraceWaterfall(trace: trace),
        ),
      ),
    );

    await tester.pumpAndSettle(); // Allow animations to complete

    // Initial state: details not shown
    expect(find.text('This span has clock skew'), findsNothing);

    // Tap to show details - use Icon to be sure
    await tester.tap(find.byIcon(Icons.check_circle));
    await tester.pumpAndSettle();

    // Verify detail chip is shown (proving details section is built)
    expect(find.text('Duration: '), findsOneWidget);

    // Verify banner is shown
    // Note: It appears twice - once in the warning banner, and once in the raw attributes list
    expect(find.text('This span has clock skew'), findsNWidgets(2));
    expect(find.byIcon(Icons.warning_amber_rounded), findsOneWidget);
  });
}
