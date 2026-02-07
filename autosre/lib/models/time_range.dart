import 'package:intl/intl.dart';

/// Presets for commonly used time ranges.
enum TimeRangePreset { oneHour, sixHours, oneDay, oneWeek, custom }

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
      case TimeRangePreset.oneHour:
        return TimeRange(
          start: now.subtract(const Duration(hours: 1)),
          end: now,
          preset: preset,
        );
      case TimeRangePreset.sixHours:
        return TimeRange(
          start: now.subtract(const Duration(hours: 6)),
          end: now,
          preset: preset,
        );
      case TimeRangePreset.oneDay:
        return TimeRange(
          start: now.subtract(const Duration(days: 1)),
          end: now,
          preset: preset,
        );
      case TimeRangePreset.oneWeek:
        return TimeRange(
          start: now.subtract(const Duration(days: 7)),
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
      case TimeRangePreset.oneHour:
        return '1H';
      case TimeRangePreset.sixHours:
        return '6H';
      case TimeRangePreset.oneDay:
        return '1D';
      case TimeRangePreset.oneWeek:
        return '1W';
      case TimeRangePreset.custom:
        final fmt = DateFormat('MMM d HH:mm');
        return '${fmt.format(start)} - ${fmt.format(end)}';
    }
  }

  /// Returns a refreshed version with updated times.
  ///
  /// For standard presets (1H, 6H, 1D, 1W), recalculates from current time.
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
