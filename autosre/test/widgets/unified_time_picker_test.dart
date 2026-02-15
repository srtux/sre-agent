import 'package:autosre/models/time_range.dart';
import 'package:autosre/widgets/common/unified_time_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/intl.dart';

Widget _wrapWidget(Widget child) {
  return MaterialApp(
    home: Scaffold(body: child),
  );
}

void main() {
  group('TimeRange model', () {
    test('fromPreset creates correct duration for each preset', () {
      final cases = <TimeRangePreset, Duration>{
        TimeRangePreset.fiveMinutes: const Duration(minutes: 5),
        TimeRangePreset.fifteenMinutes: const Duration(minutes: 15),
        TimeRangePreset.thirtyMinutes: const Duration(minutes: 30),
        TimeRangePreset.oneHour: const Duration(hours: 1),
        TimeRangePreset.threeHours: const Duration(hours: 3),
        TimeRangePreset.sixHours: const Duration(hours: 6),
        TimeRangePreset.twelveHours: const Duration(hours: 12),
        TimeRangePreset.oneDay: const Duration(days: 1),
        TimeRangePreset.twoDays: const Duration(days: 2),
        TimeRangePreset.oneWeek: const Duration(days: 7),
        TimeRangePreset.fourteenDays: const Duration(days: 14),
        TimeRangePreset.thirtyDays: const Duration(days: 30),
      };

      for (final entry in cases.entries) {
        final range = TimeRange.fromPreset(entry.key);
        // Allow 1 second tolerance for test execution time
        expect(range.duration.inSeconds, closeTo(entry.value.inSeconds, 1),
            reason: '${entry.key} should have duration ${entry.value}');
        expect(range.preset, entry.key);
      }
    });

    test('displayLabel returns correct string for each preset', () {
      final cases = <TimeRangePreset, String>{
        TimeRangePreset.fiveMinutes: 'Last 5 minutes',
        TimeRangePreset.fifteenMinutes: 'Last 15 minutes',
        TimeRangePreset.thirtyMinutes: 'Last 30 minutes',
        TimeRangePreset.oneHour: 'Last 1 hour',
        TimeRangePreset.threeHours: 'Last 3 hours',
        TimeRangePreset.sixHours: 'Last 6 hours',
        TimeRangePreset.twelveHours: 'Last 12 hours',
        TimeRangePreset.oneDay: 'Last 1 day',
        TimeRangePreset.twoDays: 'Last 2 days',
        TimeRangePreset.oneWeek: 'Last 7 days',
        TimeRangePreset.fourteenDays: 'Last 14 days',
        TimeRangePreset.thirtyDays: 'Last 30 days',
      };

      for (final entry in cases.entries) {
        final range = TimeRange.fromPreset(entry.key);
        expect(range.displayLabel, entry.value, reason: '${entry.key}');
      }
    });

    test('custom displayLabel shows formatted date range', () {
      final start = DateTime(2025, 3, 15, 10, 30);
      final end = DateTime(2025, 3, 15, 14, 45);
      final range = TimeRange(
        start: start,
        end: end,
        preset: TimeRangePreset.custom,
      );

      final fmt = DateFormat('MMM d HH:mm');
      final expected = '${fmt.format(start)} - ${fmt.format(end)}';
      expect(range.displayLabel, expected);
    });

    test('refresh re-anchors preset to now', () {
      final range = TimeRange.fromPreset(TimeRangePreset.oneHour);
      final originalEnd = range.end;

      // Refresh creates a new range anchored to the current time
      final refreshed = range.refresh();

      expect(refreshed.preset, TimeRangePreset.oneHour);
      expect(refreshed.duration.inMinutes, 60);
      // Refreshed end should be >= original end
      expect(
        refreshed.end.millisecondsSinceEpoch,
        greaterThanOrEqualTo(originalEnd.millisecondsSinceEpoch),
      );
    });

    test('refresh preserves custom duration', () {
      final now = DateTime.now();
      final customDuration = const Duration(hours: 3, minutes: 17);
      final range = TimeRange(
        start: now.subtract(customDuration),
        end: now,
        preset: TimeRangePreset.custom,
      );

      final refreshed = range.refresh();

      expect(refreshed.preset, TimeRangePreset.custom);
      expect(refreshed.duration.inSeconds,
          closeTo(customDuration.inSeconds, 1));
    });
  });

  group('UnifiedTimePicker widget', () {
    testWidgets('renders current range display label',
        (WidgetTester tester) async {
      final range = TimeRange.fromPreset(TimeRangePreset.oneHour);

      await tester.pumpWidget(_wrapWidget(
        UnifiedTimePicker(
          currentRange: range,
          onChanged: (_) {},
        ),
      ));

      expect(find.text('Last 1 hour'), findsOneWidget);
    });

    testWidgets('renders refresh button by default',
        (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWidget(
        UnifiedTimePicker(
          currentRange: TimeRange.fromPreset(TimeRangePreset.oneHour),
          onChanged: (_) {},
        ),
      ));

      expect(find.byIcon(Icons.refresh), findsOneWidget);
    });

    testWidgets('hides refresh button when disabled',
        (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWidget(
        UnifiedTimePicker(
          currentRange: TimeRange.fromPreset(TimeRangePreset.oneHour),
          onChanged: (_) {},
          showRefreshButton: false,
        ),
      ));

      expect(find.byIcon(Icons.refresh), findsNothing);
    });

    testWidgets('calls onRefresh when refresh tapped',
        (WidgetTester tester) async {
      var refreshCalled = false;

      await tester.pumpWidget(_wrapWidget(
        UnifiedTimePicker(
          currentRange: TimeRange.fromPreset(TimeRangePreset.oneHour),
          onChanged: (_) {},
          onRefresh: () => refreshCalled = true,
        ),
      ));

      await tester.tap(find.byIcon(Icons.refresh));
      await tester.pumpAndSettle();

      expect(refreshCalled, isTrue);
    });

    testWidgets('shows auto-refresh toggle when enabled',
        (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWidget(
        UnifiedTimePicker(
          currentRange: TimeRange.fromPreset(TimeRangePreset.oneHour),
          onChanged: (_) {},
          showAutoRefresh: true,
        ),
      ));

      expect(find.text('Auto'), findsOneWidget);
    });

    testWidgets('hides auto-refresh toggle by default',
        (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWidget(
        UnifiedTimePicker(
          currentRange: TimeRange.fromPreset(TimeRangePreset.oneHour),
          onChanged: (_) {},
        ),
      ));

      expect(find.text('Auto'), findsNothing);
    });

    testWidgets('calls onAutoRefreshToggle when auto-refresh tapped',
        (WidgetTester tester) async {
      var toggleCalled = false;

      await tester.pumpWidget(_wrapWidget(
        UnifiedTimePicker(
          currentRange: TimeRange.fromPreset(TimeRangePreset.oneHour),
          onChanged: (_) {},
          showAutoRefresh: true,
          onAutoRefreshToggle: () => toggleCalled = true,
        ),
      ));

      await tester.tap(find.byType(Switch));
      await tester.pumpAndSettle();

      expect(toggleCalled, isTrue);
    });

    testWidgets('opens dropdown menu on tap', (WidgetTester tester) async {
      await tester.pumpWidget(_wrapWidget(
        UnifiedTimePicker(
          currentRange: TimeRange.fromPreset(TimeRangePreset.oneHour),
          onChanged: (_) {},
        ),
      ));

      // Tap the trigger button (the PopupMenuButton area showing the label)
      await tester.tap(find.text('Last 1 hour'));
      await tester.pumpAndSettle();

      // Verify section headers and preset items appear
      expect(find.text('QUICK'), findsOneWidget);
      expect(find.text('HOURS'), findsOneWidget);
      expect(find.text('DAYS'), findsOneWidget);
      expect(find.text('CUSTOM'), findsOneWidget);
      expect(find.text('Last 5 minutes'), findsOneWidget);
    });

    testWidgets(
        'calls onChanged with correct preset when menu item selected',
        (WidgetTester tester) async {
      TimeRange? selectedRange;

      await tester.pumpWidget(_wrapWidget(
        UnifiedTimePicker(
          currentRange: TimeRange.fromPreset(TimeRangePreset.oneHour),
          onChanged: (range) => selectedRange = range,
        ),
      ));

      // Open the dropdown
      await tester.tap(find.text('Last 1 hour'));
      await tester.pumpAndSettle();

      // Select "Last 30 minutes"
      await tester.tap(find.text('Last 30 minutes'));
      await tester.pumpAndSettle();

      expect(selectedRange, isNotNull);
      expect(selectedRange!.preset, TimeRangePreset.thirtyMinutes);
      expect(selectedRange!.duration.inMinutes, closeTo(30, 1));
    });
  });
}
