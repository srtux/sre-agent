import 'package:intl/intl.dart';

/// Presets for commonly used time ranges.
enum TimeRangePreset {
  fiveMinutes,
  fifteenMinutes,
  thirtyMinutes,
  oneHour,
  threeHours,
  sixHours,
  twelveHours,
  oneDay,
  twoDays,
  oneWeek,
  fourteenDays,
  thirtyDays,
  custom,
}

/// Represents a time range for telemetry queries.
class TimeRange {
  final DateTime start;
  final DateTime end;
  final TimeRangePreset preset;

  const TimeRange({
    required this.start,
    required this.end,
    required this.preset,
  });

  factory TimeRange.fromPreset(TimeRangePreset preset) {
    final now = DateTime.now();
    switch (preset) {
      case TimeRangePreset.fiveMinutes:
        return TimeRange(
          start: now.subtract(const Duration(minutes: 5)),
          end: now,
          preset: preset,
        );
      case TimeRangePreset.fifteenMinutes:
        return TimeRange(
          start: now.subtract(const Duration(minutes: 15)),
          end: now,
          preset: preset,
        );
      case TimeRangePreset.thirtyMinutes:
        return TimeRange(
          start: now.subtract(const Duration(minutes: 30)),
          end: now,
          preset: preset,
        );
      case TimeRangePreset.oneHour:
        return TimeRange(
          start: now.subtract(const Duration(hours: 1)),
          end: now,
          preset: preset,
        );
      case TimeRangePreset.threeHours:
        return TimeRange(
          start: now.subtract(const Duration(hours: 3)),
          end: now,
          preset: preset,
        );
      case TimeRangePreset.sixHours:
        return TimeRange(
          start: now.subtract(const Duration(hours: 6)),
          end: now,
          preset: preset,
        );
      case TimeRangePreset.twelveHours:
        return TimeRange(
          start: now.subtract(const Duration(hours: 12)),
          end: now,
          preset: preset,
        );
      case TimeRangePreset.oneDay:
        return TimeRange(
          start: now.subtract(const Duration(days: 1)),
          end: now,
          preset: preset,
        );
      case TimeRangePreset.twoDays:
        return TimeRange(
          start: now.subtract(const Duration(days: 2)),
          end: now,
          preset: preset,
        );
      case TimeRangePreset.oneWeek:
        return TimeRange(
          start: now.subtract(const Duration(days: 7)),
          end: now,
          preset: preset,
        );
      case TimeRangePreset.fourteenDays:
        return TimeRange(
          start: now.subtract(const Duration(days: 14)),
          end: now,
          preset: preset,
        );
      case TimeRangePreset.thirtyDays:
        return TimeRange(
          start: now.subtract(const Duration(days: 30)),
          end: now,
          preset: preset,
        );
      case TimeRangePreset.custom:
        return TimeRange(
          start: now.subtract(const Duration(hours: 1)),
          end: now,
          preset: preset,
        );
    }
  }

  Duration get duration => end.difference(start);

  int get minutesAgo => duration.inMinutes;

  String get displayLabel {
    switch (preset) {
      case TimeRangePreset.fiveMinutes:
        return 'Last 5 minutes';
      case TimeRangePreset.fifteenMinutes:
        return 'Last 15 minutes';
      case TimeRangePreset.thirtyMinutes:
        return 'Last 30 minutes';
      case TimeRangePreset.oneHour:
        return 'Last 1 hour';
      case TimeRangePreset.threeHours:
        return 'Last 3 hours';
      case TimeRangePreset.sixHours:
        return 'Last 6 hours';
      case TimeRangePreset.twelveHours:
        return 'Last 12 hours';
      case TimeRangePreset.oneDay:
        return 'Last 1 day';
      case TimeRangePreset.twoDays:
        return 'Last 2 days';
      case TimeRangePreset.oneWeek:
        return 'Last 7 days';
      case TimeRangePreset.fourteenDays:
        return 'Last 14 days';
      case TimeRangePreset.thirtyDays:
        return 'Last 30 days';
      case TimeRangePreset.custom:
        final fmt = DateFormat('MMM d HH:mm');
        return '${fmt.format(start)} - ${fmt.format(end)}';
    }
  }

  /// Returns a refreshed version with updated times.
  ///
  /// For standard presets, recalculates from current time.
  /// For custom ranges, preserves the same duration window anchored to now.
  TimeRange refresh() {
    if (preset == TimeRangePreset.custom) {
      final dur = duration;
      final now = DateTime.now();
      return TimeRange(start: now.subtract(dur), end: now, preset: preset);
    }
    return TimeRange.fromPreset(preset);
  }
}
