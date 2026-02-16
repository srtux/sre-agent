import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../models/log_models.dart';
import '../../models/time_range.dart';
import '../../theme/app_theme.dart';
import '../../theme/design_tokens.dart';

/// Compact bar chart showing log frequency over time, color-coded by severity.
///
/// Buckets are auto-sized based on the time range duration. Each bar is a
/// stacked column with DEBUG/INFO/WARNING/ERROR/CRITICAL segments. Hover
/// shows a tooltip with bucket details; tap fires [onBucketTap] for drill-down.
class LogTimelineHistogram extends StatefulWidget {
  /// All log entries to visualize.
  final List<LogEntry> entries;

  /// Current time range for computing buckets.
  final TimeRange timeRange;

  /// Optional callback when a histogram bar/bucket is tapped for drill-down.
  final void Function(DateTime bucketStart, DateTime bucketEnd)? onBucketTap;

  const LogTimelineHistogram({
    super.key,
    required this.entries,
    required this.timeRange,
    this.onBucketTap,
  });

  @override
  State<LogTimelineHistogram> createState() => _LogTimelineHistogramState();
}

class _LogTimelineHistogramState extends State<LogTimelineHistogram> {
  int? _hoveredBucketIndex;
  Offset? _hoverPosition;

  static const double _chartHeight = 72;
  static const double _barGap = 1;

  Duration _bucketSize(Duration totalDuration) {
    final minutes = totalDuration.inMinutes;
    if (minutes < 30) return const Duration(minutes: 1);
    if (minutes < 60) return const Duration(minutes: 2);
    if (minutes < 360) return const Duration(minutes: 5);
    if (minutes < 1440) return const Duration(minutes: 30);
    final days = totalDuration.inDays;
    if (days < 7) return const Duration(hours: 1);
    if (days < 30) return const Duration(hours: 6);
    return const Duration(days: 1);
  }

  List<_HistogramBucket> _computeBuckets(
    List<LogEntry> entries,
    TimeRange range,
  ) {
    final bucketDuration = _bucketSize(range.duration);
    final buckets = <_HistogramBucket>[];

    final rangeStart = range.start.toUtc();
    final rangeEnd = range.end.toUtc();

    var current = rangeStart;
    while (current.isBefore(rangeEnd)) {
      final bucketEnd = current.add(bucketDuration);
      buckets.add(
        _HistogramBucket(
          start: current,
          end: bucketEnd.isAfter(rangeEnd) ? rangeEnd : bucketEnd,
        ),
      );
      current = bucketEnd;
    }

    for (final entry in entries) {
      final entryTime = entry.timestamp.toUtc();
      for (final bucket in buckets) {
        if (!entryTime.isBefore(bucket.start) &&
            entryTime.isBefore(bucket.end)) {
          switch (entry.severity.toUpperCase()) {
            case 'CRITICAL':
            case 'EMERGENCY':
            case 'ALERT':
              bucket.criticalCount++;
            case 'ERROR':
              bucket.errorCount++;
            case 'WARNING':
              bucket.warningCount++;
            case 'INFO':
            case 'NOTICE':
              bucket.infoCount++;
            default:
              bucket.debugCount++;
          }
          break;
        }
      }
    }

    return buckets;
  }

  int? _bucketIndexAtX(double x, int bucketCount, double width) {
    if (bucketCount == 0 || width <= 0) return null;
    final barWidth = (width - (bucketCount - 1) * _barGap) / bucketCount;
    if (barWidth < 1) return null;
    final index = x ~/ (barWidth + _barGap);
    if (index < 0 || index >= bucketCount) return null;
    return index;
  }

  @override
  Widget build(BuildContext context) {
    if (widget.entries.isEmpty) {
      return _buildEmptyState();
    }

    final buckets = _computeBuckets(widget.entries, widget.timeRange);

    return Container(
      height: _chartHeight,
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(
            color: AppColors.surfaceBorder.withValues(alpha: 0.3),
          ),
        ),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          return Stack(
            children: [
              MouseRegion(
                onHover: (event) {
                  final index = _bucketIndexAtX(
                    event.localPosition.dx,
                    buckets.length,
                    constraints.maxWidth,
                  );
                  if (index != _hoveredBucketIndex) {
                    setState(() {
                      _hoveredBucketIndex = index;
                      _hoverPosition = event.localPosition;
                    });
                  }
                },
                onExit: (_) => setState(() {
                  _hoveredBucketIndex = null;
                  _hoverPosition = null;
                }),
                child: GestureDetector(
                  onTapUp: (details) {
                    if (widget.onBucketTap == null) return;
                    final index = _bucketIndexAtX(
                      details.localPosition.dx,
                      buckets.length,
                      constraints.maxWidth,
                    );
                    if (index != null && index < buckets.length) {
                      widget.onBucketTap!(
                        buckets[index].start,
                        buckets[index].end,
                      );
                    }
                  },
                  child: CustomPaint(
                    painter: _HistogramPainter(
                      buckets: buckets,
                      hoveredIndex: _hoveredBucketIndex,
                    ),
                    size: Size(constraints.maxWidth, _chartHeight),
                  ),
                ),
              ),
              if (_hoveredBucketIndex != null &&
                  _hoverPosition != null &&
                  _hoveredBucketIndex! < buckets.length)
                _buildTooltip(
                  buckets[_hoveredBucketIndex!],
                  constraints.maxWidth,
                ),
            ],
          );
        },
      ),
    );
  }

  Widget _buildEmptyState() {
    return Container(
      height: _chartHeight,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(
            color: AppColors.surfaceBorder.withValues(alpha: 0.3),
          ),
        ),
      ),
      child: Text(
        'No log data in selected range',
        style: TextStyle(
          fontSize: 10,
          color: AppColors.textMuted.withValues(alpha: 0.6),
        ),
      ),
    );
  }

  Widget _buildTooltip(_HistogramBucket bucket, double containerWidth) {
    final barWidth =
        (containerWidth - (math.max(1, _hoveredBucketIndex!) * _barGap)) /
        math.max(1, _hoveredBucketIndex! + 1);
    final barCenterX =
        _hoveredBucketIndex! * (barWidth + _barGap) + barWidth / 2;

    // Clamp tooltip so it doesn't overflow the container
    const tooltipWidth = 160.0;
    var left = barCenterX - tooltipWidth / 2;
    if (left < 0) left = 0;
    if (left + tooltipWidth > containerWidth) {
      left = containerWidth - tooltipWidth;
    }

    final timeFormat = _labelFormat(bucket.end.difference(bucket.start));
    final startStr = _formatTime(bucket.start, timeFormat);
    final endStr = _formatTime(bucket.end, timeFormat);

    final severities = <MapEntry<String, _SeverityInfo>>[];
    if (bucket.criticalCount > 0) {
      severities.add(
        MapEntry(
          'Critical',
          _SeverityInfo(bucket.criticalCount, SeverityColors.critical),
        ),
      );
    }
    if (bucket.errorCount > 0) {
      severities.add(
        MapEntry('Error', _SeverityInfo(bucket.errorCount, AppColors.error)),
      );
    }
    if (bucket.warningCount > 0) {
      severities.add(
        MapEntry(
          'Warning',
          _SeverityInfo(bucket.warningCount, AppColors.warning),
        ),
      );
    }
    if (bucket.infoCount > 0) {
      severities.add(
        MapEntry('Info', _SeverityInfo(bucket.infoCount, AppColors.info)),
      );
    }
    if (bucket.debugCount > 0) {
      severities.add(
        MapEntry(
          'Debug',
          _SeverityInfo(bucket.debugCount, AppColors.textMuted),
        ),
      );
    }

    return Positioned(
      left: left,
      top: 0,
      child: IgnorePointer(
        child: Container(
          width: tooltipWidth,
          padding: const EdgeInsets.symmetric(
            horizontal: Spacing.sm,
            vertical: Spacing.xs,
          ),
          decoration: BoxDecoration(
            color: AppColors.backgroundElevated.withValues(alpha: 0.95),
            borderRadius: Radii.borderMd,
            border: Border.all(color: AppColors.surfaceBorder),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.4),
                blurRadius: 8,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                '$startStr – $endStr',
                style: const TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                '${bucket.total} entries',
                style: TextStyle(
                  fontSize: 9,
                  color: AppColors.textSecondary.withValues(alpha: 0.8),
                ),
              ),
              if (severities.isNotEmpty) ...[
                const SizedBox(height: Spacing.xs),
                ...severities.map(
                  (e) => Padding(
                    padding: const EdgeInsets.only(top: 1),
                    child: Row(
                      children: [
                        Container(
                          width: 6,
                          height: 6,
                          decoration: BoxDecoration(
                            color: e.value.color,
                            borderRadius: BorderRadius.circular(1),
                          ),
                        ),
                        const SizedBox(width: Spacing.xs),
                        Expanded(
                          child: Text(
                            e.key,
                            style: const TextStyle(
                              fontSize: 9,
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ),
                        Text(
                          '${e.value.count}',
                          style: const TextStyle(
                            fontSize: 9,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textPrimary,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }

  _TimeFormat _labelFormat(Duration bucketDuration) {
    if (bucketDuration.inDays >= 1) return _TimeFormat.date;
    return _TimeFormat.time;
  }

  String _formatTime(DateTime dt, _TimeFormat format) {
    switch (format) {
      case _TimeFormat.time:
        final h = dt.hour.toString().padLeft(2, '0');
        final m = dt.minute.toString().padLeft(2, '0');
        return '$h:$m';
      case _TimeFormat.date:
        const months = [
          'Jan',
          'Feb',
          'Mar',
          'Apr',
          'May',
          'Jun',
          'Jul',
          'Aug',
          'Sep',
          'Oct',
          'Nov',
          'Dec',
        ];
        return '${months[dt.month - 1]} ${dt.day}';
    }
  }
}

enum _TimeFormat { time, date }

class _SeverityInfo {
  final int count;
  final Color color;
  const _SeverityInfo(this.count, this.color);
}

class _HistogramBucket {
  final DateTime start;
  final DateTime end;
  int debugCount = 0;
  int infoCount = 0;
  int warningCount = 0;
  int errorCount = 0;
  int criticalCount = 0;

  _HistogramBucket({required this.start, required this.end});

  int get total =>
      debugCount + infoCount + warningCount + errorCount + criticalCount;
}

class _HistogramPainter extends CustomPainter {
  final List<_HistogramBucket> buckets;
  final int? hoveredIndex;

  static const double _barGap = 1;
  static const double _bottomMargin = 16;
  static const double _minBarHeight = 2;
  static const double _minBarWidth = 2;

  _HistogramPainter({required this.buckets, this.hoveredIndex});

  @override
  void paint(Canvas canvas, Size size) {
    if (buckets.isEmpty) {
      _paintEmpty(canvas, size);
      return;
    }

    final chartHeight = size.height - _bottomMargin;
    final maxTotal = buckets.fold<int>(0, (prev, b) => math.max(prev, b.total));

    if (maxTotal == 0) {
      _paintEmpty(canvas, size);
      return;
    }

    final numBuckets = buckets.length;
    var barWidth = (size.width - (numBuckets - 1) * _barGap) / numBuckets;
    if (barWidth < _minBarWidth) barWidth = _minBarWidth;

    // Gridlines at 25%, 50%, 75%
    _paintGridlines(canvas, size, chartHeight);

    // Bars
    for (var i = 0; i < numBuckets; i++) {
      final bucket = buckets[i];
      if (bucket.total == 0) continue;

      final x = i * (barWidth + _barGap);
      final totalHeight = math.max(
        _minBarHeight,
        (bucket.total / maxTotal) * chartHeight,
      );

      final isHovered = i == hoveredIndex;
      final alphaMultiplier = isHovered ? 1.5 : 1.0;

      _paintStackedBar(
        canvas,
        x,
        chartHeight,
        barWidth,
        totalHeight,
        bucket,
        maxTotal,
        alphaMultiplier,
      );

      // Hover highlight border
      if (isHovered) {
        final highlightPaint = Paint()
          ..color = AppColors.primaryCyan.withValues(alpha: 0.8)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1;
        final rect = RRect.fromRectAndCorners(
          Rect.fromLTWH(x, chartHeight - totalHeight, barWidth, totalHeight),
          topLeft: const Radius.circular(1),
          topRight: const Radius.circular(1),
        );
        canvas.drawRRect(rect, highlightPaint);
      }
    }

    // X-axis labels
    _paintXAxisLabels(canvas, size, barWidth);
  }

  void _paintStackedBar(
    Canvas canvas,
    double x,
    double chartHeight,
    double barWidth,
    double totalHeight,
    _HistogramBucket bucket,
    int maxTotal,
    double alphaMultiplier,
  ) {
    // Cloud Logging uses a cleaner, single mostly-blue aesthetic with error highlights on top
    final hasErrors = bucket.errorCount > 0 || bucket.criticalCount > 0;

    // Base blue layer
    final blueHeight = hasErrors && bucket.total > 0
        ? math.max(
            1.0,
            ((bucket.total - bucket.errorCount - bucket.criticalCount) /
                    bucket.total) *
                totalHeight,
          )
        : totalHeight;

    final redHeight = hasErrors ? totalHeight - blueHeight : 0.0;

    var yPosition = chartHeight;

    if (blueHeight > 0) {
      final paint = Paint()
        ..color = AppColors.primaryCyan
            .withValues(alpha: (0.6 * alphaMultiplier).clamp(0.0, 1.0))
        ..style = PaintingStyle.fill;

      final rrect = RRect.fromRectAndCorners(
        Rect.fromLTWH(x, yPosition - blueHeight, barWidth, blueHeight),
        topLeft: hasErrors ? Radius.zero : const Radius.circular(1),
        topRight: hasErrors ? Radius.zero : const Radius.circular(1),
      );
      canvas.drawRRect(rrect, paint);
      yPosition -= blueHeight;
    }

    if (redHeight > 0) {
      final paint = Paint()
        ..color = AppColors.error
            .withValues(alpha: (0.8 * alphaMultiplier).clamp(0.0, 1.0))
        ..style = PaintingStyle.fill;

      final rrect = RRect.fromRectAndCorners(
        Rect.fromLTWH(x, yPosition - redHeight, barWidth, redHeight),
        topLeft: const Radius.circular(1),
        topRight: const Radius.circular(1),
      );
      canvas.drawRRect(rrect, paint);
    }
  }

  void _paintGridlines(Canvas canvas, Size size, double chartHeight) {
    final linePaint = Paint()
      ..color = AppColors.surfaceBorder.withValues(alpha: 0.15)
      ..strokeWidth = 1;

    for (final fraction in [0.25, 0.5, 0.75]) {
      final y = chartHeight * (1 - fraction);
      canvas.drawLine(Offset(0, y), Offset(size.width, y), linePaint);
    }
  }

  void _paintXAxisLabels(Canvas canvas, Size size, double barWidth) {
    if (buckets.isEmpty) return;

    // Show ~5-6 labels
    final labelCount = math.min(6, buckets.length);
    if (labelCount == 0) return;

    final step = math.max(1, buckets.length ~/ labelCount);
    final useDateFormat =
        buckets.first.end.difference(buckets.first.start).inDays >= 1;

    for (var i = 0; i < buckets.length; i += step) {
      final bucket = buckets[i];
      final label = useDateFormat
          ? _formatDate(bucket.start)
          : _formatTimeLabel(bucket.start);

      final tp = TextPainter(
        text: TextSpan(
          text: label,
          style: TextStyle(
            fontSize: 9,
            color: AppColors.textMuted.withValues(alpha: 0.7),
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();

      final x = i * (barWidth + _barGap) + barWidth / 2 - tp.width / 2;
      final clampedX = x.clamp(0.0, size.width - tp.width);
      tp.paint(canvas, Offset(clampedX, size.height - _bottomMargin + 3));
    }
  }

  void _paintEmpty(Canvas canvas, Size size) {
    final linePaint = Paint()
      ..color = AppColors.textMuted.withValues(alpha: 0.2)
      ..strokeWidth = 1;
    final y = size.height - _bottomMargin;
    canvas.drawLine(Offset(0, y), Offset(size.width, y), linePaint);

    final tp = TextPainter(
      text: TextSpan(
        text: 'No data in range',
        style: TextStyle(
          fontSize: 10,
          color: AppColors.textMuted.withValues(alpha: 0.5),
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(
      canvas,
      Offset((size.width - tp.width) / 2, (size.height - tp.height) / 2),
    );
  }

  String _formatTimeLabel(DateTime dt) {
    final h = dt.hour.toString().padLeft(2, '0');
    final m = dt.minute.toString().padLeft(2, '0');
    return '$h:$m';
  }

  String _formatDate(DateTime dt) {
    const months = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];
    return '${months[dt.month - 1]} ${dt.day}';
  }

  @override
  bool shouldRepaint(_HistogramPainter oldDelegate) =>
      oldDelegate.hoveredIndex != hoveredIndex ||
      oldDelegate.buckets != buckets;
}
