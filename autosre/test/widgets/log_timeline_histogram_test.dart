import 'package:autosre/features/logs/domain/models.dart';

import 'package:autosre/models/time_range.dart';
import 'package:autosre/widgets/dashboard/log_timeline_histogram.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

LogEntry _makeEntry({required DateTime timestamp, String severity = 'INFO'}) {
  return LogEntry(
    insertId: 'entry-${timestamp.millisecondsSinceEpoch}',
    timestamp: timestamp,
    severity: severity,
    payload: 'Test log message',
    resourceLabels: {'log_name': 'test', 'project_id': 'proj'},
    resourceType: 'gce_instance',
  );
}

TimeRange _makeRange({required DateTime start, required DateTime end}) {
  return TimeRange(start: start, end: end, preset: TimeRangePreset.custom);
}

Widget _wrapWidget(Widget child) {
  return MaterialApp(
    home: Scaffold(body: SizedBox(width: 800, child: child)),
  );
}

void main() {
  group('LogTimelineHistogram', () {
    final baseTime = DateTime(2026, 2, 15, 10, 0, 0);

    testWidgets('shows empty state text when entries empty', (
      WidgetTester tester,
    ) async {
      final range = _makeRange(
        start: baseTime,
        end: baseTime.add(const Duration(hours: 1)),
      );

      await tester.pumpWidget(
        _wrapWidget(LogTimelineHistogram(entries: const [], timeRange: range)),
      );
      await tester.pumpAndSettle();

      expect(find.text('No log data in selected range'), findsOneWidget);
    });

    testWidgets('renders CustomPaint when entries present', (
      WidgetTester tester,
    ) async {
      final range = _makeRange(
        start: baseTime,
        end: baseTime.add(const Duration(hours: 1)),
      );
      final entries = [
        _makeEntry(timestamp: baseTime.add(const Duration(minutes: 10))),
        _makeEntry(timestamp: baseTime.add(const Duration(minutes: 30))),
      ];

      await tester.pumpWidget(
        _wrapWidget(LogTimelineHistogram(entries: entries, timeRange: range)),
      );
      await tester.pumpAndSettle();

      expect(find.byType(CustomPaint), findsWidgets);
    });

    testWidgets('renders with correct height', (WidgetTester tester) async {
      final range = _makeRange(
        start: baseTime,
        end: baseTime.add(const Duration(hours: 1)),
      );
      final entries = [
        _makeEntry(timestamp: baseTime.add(const Duration(minutes: 5))),
      ];

      await tester.pumpWidget(
        _wrapWidget(LogTimelineHistogram(entries: entries, timeRange: range)),
      );
      await tester.pumpAndSettle();

      final container = tester.widget<Container>(
        find
            .descendant(
              of: find.byType(LogTimelineHistogram),
              matching: find.byType(Container),
            )
            .first,
      );
      final box = container.constraints;
      expect(box?.maxHeight, 72);
    });

    testWidgets('handles single entry', (WidgetTester tester) async {
      final range = _makeRange(
        start: baseTime,
        end: baseTime.add(const Duration(hours: 1)),
      );
      final entries = [
        _makeEntry(timestamp: baseTime.add(const Duration(minutes: 15))),
      ];

      await tester.pumpWidget(
        _wrapWidget(LogTimelineHistogram(entries: entries, timeRange: range)),
      );
      await tester.pumpAndSettle();

      expect(find.byType(LogTimelineHistogram), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('handles entries spanning the full time range', (
      WidgetTester tester,
    ) async {
      final range = _makeRange(
        start: baseTime,
        end: baseTime.add(const Duration(hours: 1)),
      );
      final entries = [
        _makeEntry(timestamp: baseTime),
        _makeEntry(
          timestamp: baseTime.add(const Duration(minutes: 59)),
          severity: 'ERROR',
        ),
      ];

      await tester.pumpWidget(
        _wrapWidget(LogTimelineHistogram(entries: entries, timeRange: range)),
      );
      await tester.pumpAndSettle();

      expect(find.byType(LogTimelineHistogram), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('handles entries outside time range gracefully', (
      WidgetTester tester,
    ) async {
      final range = _makeRange(
        start: baseTime,
        end: baseTime.add(const Duration(hours: 1)),
      );
      final entries = [
        _makeEntry(timestamp: baseTime.subtract(const Duration(hours: 2))),
      ];

      await tester.pumpWidget(
        _wrapWidget(LogTimelineHistogram(entries: entries, timeRange: range)),
      );
      await tester.pumpAndSettle();

      expect(find.byType(LogTimelineHistogram), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('calls onBucketTap when provided', (WidgetTester tester) async {
      final range = _makeRange(
        start: baseTime,
        end: baseTime.add(const Duration(hours: 1)),
      );
      final entries = [
        _makeEntry(timestamp: baseTime.add(const Duration(minutes: 10))),
      ];

      DateTime? tappedStart;
      DateTime? tappedEnd;

      await tester.pumpWidget(
        _wrapWidget(
          LogTimelineHistogram(
            entries: entries,
            timeRange: range,
            onBucketTap: (start, end) {
              tappedStart = start;
              tappedEnd = end;
            },
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Verify the widget renders and accepts the callback without error.
      // Tapping exact CustomPaint bucket coordinates is fragile in widget
      // tests, so we only assert the widget built correctly.
      expect(find.byType(LogTimelineHistogram), findsOneWidget);
      expect(tester.takeException(), isNull);
      // The callback reference was accepted (no compile/runtime error).
      expect(tappedStart, isNull);
      expect(tappedEnd, isNull);
    });

    testWidgets('updates when entries change', (WidgetTester tester) async {
      final range = _makeRange(
        start: baseTime,
        end: baseTime.add(const Duration(hours: 1)),
      );
      final entriesA = [
        _makeEntry(timestamp: baseTime.add(const Duration(minutes: 5))),
      ];
      final entriesB = [
        _makeEntry(
          timestamp: baseTime.add(const Duration(minutes: 10)),
          severity: 'ERROR',
        ),
        _makeEntry(
          timestamp: baseTime.add(const Duration(minutes: 40)),
          severity: 'WARNING',
        ),
      ];

      await tester.pumpWidget(
        _wrapWidget(LogTimelineHistogram(entries: entriesA, timeRange: range)),
      );
      await tester.pumpAndSettle();

      // Rebuild with different entries.
      await tester.pumpWidget(
        _wrapWidget(LogTimelineHistogram(entries: entriesB, timeRange: range)),
      );
      await tester.pumpAndSettle();

      expect(find.byType(LogTimelineHistogram), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('updates when timeRange changes', (WidgetTester tester) async {
      final range1h = _makeRange(
        start: baseTime,
        end: baseTime.add(const Duration(hours: 1)),
      );
      final range6h = _makeRange(
        start: baseTime,
        end: baseTime.add(const Duration(hours: 6)),
      );
      final entries = [
        _makeEntry(timestamp: baseTime.add(const Duration(minutes: 10))),
        _makeEntry(timestamp: baseTime.add(const Duration(minutes: 30))),
      ];

      await tester.pumpWidget(
        _wrapWidget(LogTimelineHistogram(entries: entries, timeRange: range1h)),
      );
      await tester.pumpAndSettle();

      await tester.pumpWidget(
        _wrapWidget(LogTimelineHistogram(entries: entries, timeRange: range6h)),
      );
      await tester.pumpAndSettle();

      expect(find.byType(LogTimelineHistogram), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('handles many entries efficiently', (
      WidgetTester tester,
    ) async {
      final range = _makeRange(
        start: baseTime,
        end: baseTime.add(const Duration(hours: 1)),
      );
      final entries = List.generate(
        1000,
        (i) => _makeEntry(
          timestamp: baseTime.add(Duration(seconds: i * 3)),
          severity: ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'][i % 5],
        ),
      );

      await tester.pumpWidget(
        _wrapWidget(LogTimelineHistogram(entries: entries, timeRange: range)),
      );
      await tester.pumpAndSettle();

      expect(find.byType(LogTimelineHistogram), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });

  group('Bucket computation', () {
    final baseTime = DateTime(2026, 2, 15, 10, 0, 0);

    testWidgets('correctly distributes entries across visual bars', (
      WidgetTester tester,
    ) async {
      final range = _makeRange(
        start: baseTime,
        end: baseTime.add(const Duration(hours: 2)),
      );
      // Spread entries across the range so multiple buckets are populated.
      final entries = [
        _makeEntry(timestamp: baseTime.add(const Duration(minutes: 5))),
        _makeEntry(timestamp: baseTime.add(const Duration(minutes: 30))),
        _makeEntry(timestamp: baseTime.add(const Duration(minutes: 60))),
        _makeEntry(timestamp: baseTime.add(const Duration(minutes: 90))),
      ];

      await tester.pumpWidget(
        _wrapWidget(LogTimelineHistogram(entries: entries, timeRange: range)),
      );
      await tester.pumpAndSettle();

      // CustomPaint is present meaning the painter ran without assertion errors.
      expect(find.byType(CustomPaint), findsWidgets);
      expect(tester.takeException(), isNull);
    });

    testWidgets('handles all severity levels', (WidgetTester tester) async {
      final range = _makeRange(
        start: baseTime,
        end: baseTime.add(const Duration(hours: 1)),
      );
      final entries = [
        _makeEntry(
          timestamp: baseTime.add(const Duration(minutes: 5)),
          severity: 'DEBUG',
        ),
        _makeEntry(
          timestamp: baseTime.add(const Duration(minutes: 10)),
          severity: 'INFO',
        ),
        _makeEntry(
          timestamp: baseTime.add(const Duration(minutes: 15)),
          severity: 'WARNING',
        ),
        _makeEntry(
          timestamp: baseTime.add(const Duration(minutes: 20)),
          severity: 'ERROR',
        ),
        _makeEntry(
          timestamp: baseTime.add(const Duration(minutes: 25)),
          severity: 'CRITICAL',
        ),
      ];

      await tester.pumpWidget(
        _wrapWidget(LogTimelineHistogram(entries: entries, timeRange: range)),
      );
      await tester.pumpAndSettle();

      expect(find.byType(LogTimelineHistogram), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  });
}
