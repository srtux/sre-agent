import 'package:intl/intl.dart';

/// Presets for commonly used time ranges.
///
/// Each variant carries its own [duration] and [label], eliminating the need
/// for separate switch statements when constructing or rendering time ranges.
enum TimeRangePreset {
  fiveMinutes(Duration(minutes: 5), 'Last 5 minutes'),
  fifteenMinutes(Duration(minutes: 15), 'Last 15 minutes'),
  thirtyMinutes(Duration(minutes: 30), 'Last 30 minutes'),
  oneHour(Duration(hours: 1), 'Last 1 hour'),
  threeHours(Duration(hours: 3), 'Last 3 hours'),
  sixHours(Duration(hours: 6), 'Last 6 hours'),
  twelveHours(Duration(hours: 12), 'Last 12 hours'),
  oneDay(Duration(days: 1), 'Last 1 day'),
  twoDays(Duration(days: 2), 'Last 2 days'),
  oneWeek(Duration(days: 7), 'Last 7 days'),
  fourteenDays(Duration(days: 14), 'Last 14 days'),
  thirtyDays(Duration(days: 30), 'Last 30 days'),
  custom(Duration(hours: 1), null); // null label → computed from range bounds

  /// Default lookback window for this preset.
  final Duration duration;

  /// Static display label, or `null` for [custom] (computed dynamically).
  final String? label;

  const TimeRangePreset(this.duration, this.label);
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
    return TimeRange(
      start: now.subtract(preset.duration),
      end: now,
      preset: preset,
    );
  }

  Duration get duration => end.difference(start);

  int get minutesAgo => duration.inMinutes;

  String get displayLabel {
    if (preset.label case String label) return label;
    final fmt = DateFormat('MMM d HH:mm');
    return '${fmt.format(start)} - ${fmt.format(end)}';
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
