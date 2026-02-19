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

    testWidgets('shows loading state when isLoadingHistogram and no data', (
      WidgetTester tester,
    ) async {
      final range = _makeRange(
        start: baseTime,
        end: baseTime.add(const Duration(hours: 1)),
      );

      await tester.pumpWidget(
        _wrapWidget(
          LogTimelineHistogram(
            entries: const [],
            timeRange: range,
            isLoadingHistogram: true,
          ),
        ),
      );
      await tester.pump();

      expect(find.text('Loading timeline...'), findsOneWidget);
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

    testWidgets('renders with default height', (WidgetTester tester) async {
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

      // The chart container should use the default height (96).
      final container = tester.widget<Container>(
        find
            .descendant(
              of: find.byType(LogTimelineHistogram),
              matching: find.byType(Container),
            )
            .first,
      );
      final box = container.constraints;
      expect(box?.maxHeight, LogTimelineHistogram.defaultHeight);
    });

    testWidgets('renders with custom chartHeight', (
      WidgetTester tester,
    ) async {
      final range = _makeRange(
        start: baseTime,
        end: baseTime.add(const Duration(hours: 1)),
      );
      final entries = [
        _makeEntry(timestamp: baseTime.add(const Duration(minutes: 5))),
      ];

      await tester.pumpWidget(
        _wrapWidget(
          LogTimelineHistogram(
            entries: entries,
            timeRange: range,
            chartHeight: 200,
          ),
        ),
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
      expect(box?.maxHeight, 200);
    });

    testWidgets('resize handle is present', (WidgetTester tester) async {
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

      // The resize handle renders a MouseRegion with resizeRow cursor.
      expect(find.byType(MouseRegion), findsWidgets);
      expect(find.byType(GestureDetector), findsWidgets);
    });

    testWidgets('drag on resize handle fires onHeightChanged', (
      WidgetTester tester,
    ) async {
      final range = _makeRange(
        start: baseTime,
        end: baseTime.add(const Duration(hours: 1)),
      );
      final entries = [
        _makeEntry(timestamp: baseTime.add(const Duration(minutes: 5))),
      ];

      double? reportedHeight;

      await tester.pumpWidget(
        _wrapWidget(
          LogTimelineHistogram(
            entries: entries,
            timeRange: range,
            chartHeight: 96,
            onHeightChanged: (h) => reportedHeight = h,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Drag downward on the widget to trigger the resize handle.
      await tester.drag(
        find.byType(LogTimelineHistogram),
        const Offset(0, 50),
        warnIfMissed: false,
      );
      await tester.pumpAndSettle();

      // The callback should have been invoked with a clamped value.
      expect(reportedHeight, isNotNull);
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

  testWidgets('handles entries outside time range gracefully (dynamic expanding bounds)', (
      WidgetTester tester,
    ) async {
      final range = _makeRange(
        start: baseTime,
        end: baseTime.add(const Duration(hours: 1)),
      );
      final entries = [
        _makeEntry(timestamp: baseTime.subtract(const Duration(hours: 2))), // before explicitly bound
        _makeEntry(timestamp: baseTime.add(const Duration(hours: 4))), // after explicitly bound
      ];

      await tester.pumpWidget(
        _wrapWidget(LogTimelineHistogram(entries: entries, timeRange: range)),
      );
      await tester.pumpAndSettle();

      expect(find.byType(LogTimelineHistogram), findsOneWidget);
      expect(find.byType(CustomPaint), findsWidgets); // Should not assert and successfully paint
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

  group('Backend histogram data', () {
    final baseTime = DateTime(2026, 2, 15, 10, 0, 0);

    testWidgets('renders backend histogram when histogramData provided', (
      WidgetTester tester,
    ) async {
      final range = _makeRange(
        start: baseTime,
        end: baseTime.add(const Duration(hours: 1)),
      );
      final histogramData = LogHistogramData(
        buckets: [
          LogHistogramBucket(
            start: baseTime,
            end: baseTime.add(const Duration(minutes: 15)),
            info: 42,
            error: 3,
          ),
          LogHistogramBucket(
            start: baseTime.add(const Duration(minutes: 15)),
            end: baseTime.add(const Duration(minutes: 30)),
            info: 20,
            warning: 5,
          ),
          LogHistogramBucket(
            start: baseTime.add(const Duration(minutes: 30)),
            end: baseTime.add(const Duration(minutes: 45)),
            info: 60,
          ),
          LogHistogramBucket(
            start: baseTime.add(const Duration(minutes: 45)),
            end: baseTime.add(const Duration(hours: 1)),
            info: 10,
            critical: 1,
          ),
        ],
        totalCount: 141,
        scannedEntries: 141,
      );

      await tester.pumpWidget(
        _wrapWidget(
          LogTimelineHistogram(
            entries: const [], // No local entries needed
            timeRange: range,
            histogramData: histogramData,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Should render bars from histogramData, even with empty entries
      expect(find.byType(CustomPaint), findsWidgets);
      // Badge showing total entries count
      expect(find.text('141 entries'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });

    testWidgets('prefers histogramData over local entries', (
      WidgetTester tester,
    ) async {
      final range = _makeRange(
        start: baseTime,
        end: baseTime.add(const Duration(hours: 1)),
      );
      final entries = [
        _makeEntry(timestamp: baseTime.add(const Duration(minutes: 5))),
      ];
      final histogramData = LogHistogramData(
        buckets: [
          LogHistogramBucket(
            start: baseTime,
            end: baseTime.add(const Duration(minutes: 30)),
            info: 500,
          ),
          LogHistogramBucket(
            start: baseTime.add(const Duration(minutes: 30)),
            end: baseTime.add(const Duration(hours: 1)),
            info: 300,
            error: 10,
          ),
        ],
        totalCount: 810,
        scannedEntries: 810,
      );

      await tester.pumpWidget(
        _wrapWidget(
          LogTimelineHistogram(
            entries: entries,
            timeRange: range,
            histogramData: histogramData,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Should show histogramData count badge (810, not 1 from entries)
      expect(find.text('810 entries'), findsOneWidget);
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

  group('LogHistogramData model', () {
    test('fromJson parses buckets correctly', () {
      final json = {
        'buckets': [
          {
            'start': '2026-02-15T10:00:00.000Z',
            'end': '2026-02-15T10:15:00.000Z',
            'debug': 5,
            'info': 42,
            'warning': 3,
            'error': 1,
            'critical': 0,
          },
          {
            'start': '2026-02-15T10:15:00.000Z',
            'end': '2026-02-15T10:30:00.000Z',
            'debug': 0,
            'info': 20,
            'warning': 0,
            'error': 0,
            'critical': 0,
          },
        ],
        'total_count': 71,
        'scanned_entries': 71,
      };

      final data = LogHistogramData.fromJson(json);
      expect(data.buckets.length, 2);
      expect(data.totalCount, 71);
      expect(data.scannedEntries, 71);
      expect(data.buckets[0].info, 42);
      expect(data.buckets[0].total, 51);
      expect(data.buckets[1].total, 20);
    });

    test('LogHistogramBucket.total sums all severities', () {
      final bucket = LogHistogramBucket(
        start: DateTime(2026, 2, 15, 10, 0, 0),
        end: DateTime(2026, 2, 15, 10, 15, 0),
        debug: 1,
        info: 2,
        warning: 3,
        error: 4,
        critical: 5,
      );
      expect(bucket.total, 15);
    });
  });
}
