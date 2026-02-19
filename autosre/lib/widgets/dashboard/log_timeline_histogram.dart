import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:flutter/material.dart';

import '../../features/logs/domain/models.dart';

import '../../models/time_range.dart';
import '../../theme/app_theme.dart';
import '../../theme/design_tokens.dart';

/// Compact bar chart showing log frequency over time, color-coded by severity.
///
/// When [histogramData] is provided (from the `/logs/histogram` backend
/// endpoint), the chart shows the full time-range distribution instead of
/// only the locally loaded entries. Falls back to client-side bucketing of
/// [entries] when [histogramData] is null.
///
/// Each bar is a stacked column with per-severity segments. Hover shows a
/// tooltip with bucket details; tap fires [onBucketTap] for drill-down.
class LogTimelineHistogram extends StatefulWidget {
  /// All log entries currently loaded (fallback data source).
  final List<LogEntry> entries;

  /// Current time range for computing buckets.
  final TimeRange timeRange;

  /// Pre-aggregated histogram from the backend (preferred data source).
  final LogHistogramData? histogramData;

  /// Whether a histogram request is in flight.
  final bool isLoadingHistogram;

  /// Optional callback when a histogram bar/bucket is tapped for drill-down.
  final void Function(DateTime bucketStart, DateTime bucketEnd)? onBucketTap;

  /// Chart height controlled by the parent. Falls back to [defaultHeight].
  final double? chartHeight;

  /// Fired when the user drags the resize handle. The parent should persist
  /// the new value and pass it back via [chartHeight].
  final ValueChanged<double>? onHeightChanged;

  /// Default height when no [chartHeight] is provided.
  static const double defaultHeight = 96;

  /// Minimum allowed chart height.
  static const double minHeight = 40;

  /// Maximum allowed chart height.
  static const double maxHeight = 300;

  const LogTimelineHistogram({
    super.key,
    required this.entries,
    required this.timeRange,
    this.histogramData,
    this.isLoadingHistogram = false,
    this.onBucketTap,
    this.chartHeight,
    this.onHeightChanged,
  });

  @override
  State<LogTimelineHistogram> createState() => _LogTimelineHistogramState();
}

class _LogTimelineHistogramState extends State<LogTimelineHistogram> {
  int? _hoveredBucketIndex;
  Offset? _hoverPosition;

  double get _chartHeight =>
      widget.chartHeight ?? LogTimelineHistogram.defaultHeight;
  static const double _barGap = 1.5;
  static const double _leftMargin = 36;

  // Cached buckets to avoid recomputation per frame.
  List<_HistogramBucket>? _cachedBuckets;
  int _cachedEntryCount = -1;
  LogHistogramData? _cachedHistogramData;

  // ---- Bucket computation (client-side fallback) ----

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

  List<_HistogramBucket> _bucketsFromEntries(
    List<LogEntry> entries,
    TimeRange range,
  ) {
    if (entries.isEmpty) return [];

    var minTime = range.start.toUtc();
    var maxTime = range.end.toUtc();

    for (final entry in entries) {
      final t = entry.timestamp.toUtc();
      if (t.isBefore(minTime)) minTime = t;
      if (t.isAfter(maxTime)) maxTime = t;
    }

    if (minTime.isAtSameMomentAs(maxTime)) {
      minTime = minTime.subtract(const Duration(minutes: 1));
      maxTime = maxTime.add(const Duration(minutes: 1));
    }

    final totalDuration = maxTime.difference(minTime);
    final bucketDuration = _bucketSize(totalDuration);
    final buckets = <_HistogramBucket>[];

    var current = minTime;
    while (current.isBefore(maxTime)) {
      final bucketEnd = current.add(bucketDuration);
      buckets.add(
        _HistogramBucket(
          start: current,
          end: bucketEnd.isAfter(maxTime) ? maxTime : bucketEnd,
        ),
      );
      current = bucketEnd;
    }

    for (final entry in entries) {
      final entryTime = entry.timestamp.toUtc();
      for (final bucket in buckets) {
        if (!entryTime.isBefore(bucket.start) &&
            (entryTime.isBefore(bucket.end) ||
                entryTime.isAtSameMomentAs(maxTime) &&
                    bucket.end.isAtSameMomentAs(maxTime))) {
          switch (entry.severity.toUpperCase()) {
            case 'CRITICAL':
            case 'EMERGENCY':
            case 'ALERT':
              bucket.criticalCount++;
              break;
            case 'ERROR':
              bucket.errorCount++;
              break;
            case 'WARNING':
              bucket.warningCount++;
              break;
            case 'INFO':
            case 'NOTICE':
              bucket.infoCount++;
              break;
            default:
              bucket.debugCount++;
              break;
          }
          break;
        }
      }
    }

    return buckets;
  }

  List<_HistogramBucket> _bucketsFromHistogramData(LogHistogramData data) {
    return data.buckets.map((b) {
      final bucket = _HistogramBucket(start: b.start, end: b.end);
      bucket.debugCount = b.debug;
      bucket.infoCount = b.info;
      bucket.warningCount = b.warning;
      bucket.errorCount = b.error;
      bucket.criticalCount = b.critical;
      return bucket;
    }).toList();
  }

  List<_HistogramBucket> _getEffectiveBuckets() {
    // Prefer backend histogram data when available.
    if (widget.histogramData != null) {
      if (_cachedHistogramData != widget.histogramData) {
        _cachedBuckets = _bucketsFromHistogramData(widget.histogramData!);
        _cachedHistogramData = widget.histogramData;
      }
      return _cachedBuckets ?? [];
    }

    // Fallback to client-side bucketing.
    if (_cachedBuckets == null ||
        _cachedEntryCount != widget.entries.length ||
        _cachedHistogramData != null) {
      _cachedBuckets = _bucketsFromEntries(widget.entries, widget.timeRange);
      _cachedEntryCount = widget.entries.length;
      _cachedHistogramData = null;
    }
    return _cachedBuckets ?? [];
  }

  int? _bucketIndexAtX(double x, int bucketCount, double chartWidth) {
    if (bucketCount == 0 || chartWidth <= 0) return null;
    final adjustedX = x - _leftMargin;
    if (adjustedX < 0) return null;
    final barWidth = (chartWidth - (bucketCount - 1) * _barGap) / bucketCount;
    if (barWidth < 1) return null;
    final index = adjustedX ~/ (barWidth + _barGap);
    if (index < 0 || index >= bucketCount) return null;
    return index;
  }

  @override
  void didUpdateWidget(LogTimelineHistogram oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.entries.length != widget.entries.length ||
        oldWidget.timeRange != widget.timeRange ||
        oldWidget.histogramData != widget.histogramData) {
      _cachedBuckets = null;
      _cachedHistogramData = null;
    }
  }

  @override
  Widget build(BuildContext context) {
    final hasEntries = widget.entries.isNotEmpty;
    final hasHistogram = widget.histogramData != null;

    if (!hasEntries && !hasHistogram) {
      return _buildEmptyState();
    }

    final buckets = _getEffectiveBuckets();

    if (buckets.isEmpty) {
      return _buildEmptyState();
    }

    final effectiveHeight = _chartHeight;

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          height: effectiveHeight,
          decoration: BoxDecoration(
            color: AppColors.backgroundDark.withValues(alpha: 0.3),
          ),
          child: LayoutBuilder(
            builder: (context, constraints) {
              final chartWidth = constraints.maxWidth - _leftMargin;
              return Stack(
                children: [
                  MouseRegion(
                    onHover: (event) {
                      final index = _bucketIndexAtX(
                        event.localPosition.dx,
                        buckets.length,
                        chartWidth,
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
                          chartWidth,
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
                          leftMargin: _leftMargin,
                        ),
                        size: Size(constraints.maxWidth, effectiveHeight),
                      ),
                    ),
                  ),
                  // Loading shimmer overlay
                  if (widget.isLoadingHistogram && !hasHistogram)
                    Positioned.fill(
                      child: Container(
                        color:
                            AppColors.backgroundDark.withValues(alpha: 0.4),
                        alignment: Alignment.center,
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            SizedBox(
                              width: 12,
                              height: 12,
                              child: CircularProgressIndicator(
                                strokeWidth: 1.5,
                                color: AppColors.primaryCyan.withValues(
                                  alpha: 0.7,
                                ),
                              ),
                            ),
                            const SizedBox(width: Spacing.sm),
                            Text(
                              'Loading full timeline...',
                              style: TextStyle(
                                fontSize: 10,
                                color: AppColors.textMuted.withValues(
                                  alpha: 0.7,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  // Source badge
                  if (hasHistogram)
                    Positioned(
                      right: Spacing.sm,
                      top: Spacing.xs,
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 5,
                          vertical: 1,
                        ),
                        decoration: BoxDecoration(
                          color: AppColors.success.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(3),
                          border: Border.all(
                            color: AppColors.success.withValues(alpha: 0.2),
                          ),
                        ),
                        child: Text(
                          '${_formatCount(widget.histogramData!.totalCount)} entries',
                          style: TextStyle(
                            fontSize: 8,
                            fontWeight: FontWeight.w500,
                            color: AppColors.success.withValues(
                              alpha: 0.8,
                            ),
                          ),
                        ),
                      ),
                    ),
                  // Tooltip
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
        ),
        // Resize drag handle
        _buildResizeHandle(),
      ],
    );
  }

  static String _formatCount(int count) {
    if (count >= 1000000) return '${(count / 1000000).toStringAsFixed(1)}M';
    if (count >= 1000) return '${(count / 1000).toStringAsFixed(1)}K';
    return count.toString();
  }

  Widget _buildEmptyState() {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          height: _chartHeight,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: AppColors.backgroundDark.withValues(alpha: 0.3),
          ),
          child: widget.isLoadingHistogram
              ? Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    SizedBox(
                      width: 12,
                      height: 12,
                      child: CircularProgressIndicator(
                        strokeWidth: 1.5,
                        color: AppColors.primaryCyan.withValues(alpha: 0.7),
                      ),
                    ),
                    const SizedBox(width: Spacing.sm),
                    Text(
                      'Loading timeline...',
                      style: TextStyle(
                        fontSize: 10,
                        color: AppColors.textMuted.withValues(alpha: 0.6),
                      ),
                    ),
                  ],
                )
              : Text(
                  'No log data in selected range',
                  style: TextStyle(
                    fontSize: 10,
                    color: AppColors.textMuted.withValues(alpha: 0.6),
                  ),
                ),
        ),
        _buildResizeHandle(),
      ],
    );
  }

  Widget _buildResizeHandle() {
    return MouseRegion(
      cursor: SystemMouseCursors.resizeRow,
      child: GestureDetector(
        onVerticalDragUpdate: (details) {
          if (widget.onHeightChanged == null) return;
          final newHeight = (_chartHeight + details.delta.dy).clamp(
            LogTimelineHistogram.minHeight,
            LogTimelineHistogram.maxHeight,
          );
          widget.onHeightChanged!(newHeight);
        },
        child: Container(
          height: 8,
          decoration: BoxDecoration(
            color: AppColors.backgroundDark.withValues(alpha: 0.3),
            border: Border(
              bottom: BorderSide(
                color: AppColors.surfaceBorder.withValues(alpha: 0.2),
              ),
            ),
          ),
          child: Center(
            child: Container(
              width: 32,
              height: 3,
              decoration: BoxDecoration(
                color: AppColors.surfaceBorder.withValues(alpha: 0.4),
                borderRadius: BorderRadius.circular(1.5),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildTooltip(_HistogramBucket bucket, double containerWidth) {
    final buckets = _getEffectiveBuckets();
    final numBuckets = buckets.length;
    final chartWidth = containerWidth - _leftMargin;
    final barWidth =
        (chartWidth - (numBuckets - 1) * _barGap) / numBuckets;
    final barCenterX =
        _leftMargin +
        _hoveredBucketIndex! * (barWidth + _barGap) +
        barWidth / 2;

    const tooltipWidth = 170.0;
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
            vertical: Spacing.xs + 2,
          ),
          decoration: BoxDecoration(
            color: AppColors.backgroundCard.withValues(alpha: 0.97),
            borderRadius: Radii.borderMd,
            border: Border.all(
              color: AppColors.primaryCyan.withValues(alpha: 0.3),
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.5),
                blurRadius: 12,
                offset: const Offset(0, 4),
              ),
              BoxShadow(
                color: AppColors.primaryCyan.withValues(alpha: 0.05),
                blurRadius: 20,
                spreadRadius: -2,
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
              const SizedBox(height: 3),
              Row(
                children: [
                  Text(
                    _formatCount(bucket.total),
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      color: AppColors.primaryCyan,
                    ),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    'entries',
                    style: TextStyle(
                      fontSize: 9,
                      color: AppColors.textSecondary.withValues(alpha: 0.7),
                    ),
                  ),
                ],
              ),
              if (severities.isNotEmpty) ...[
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 3),
                  child: Divider(
                    height: 1,
                    color: AppColors.surfaceBorder.withValues(alpha: 0.3),
                  ),
                ),
                ...severities.map(
                  (e) => Padding(
                    padding: const EdgeInsets.only(top: 1),
                    child: Row(
                      children: [
                        Container(
                          width: 8,
                          height: 8,
                          decoration: BoxDecoration(
                            color: e.value.color,
                            borderRadius: BorderRadius.circular(2),
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
                          _formatCount(e.value.count),
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
          'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
          'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
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

// ---------------------------------------------------------------------------
// Custom painter — improved visual design
// ---------------------------------------------------------------------------
class _HistogramPainter extends CustomPainter {
  final List<_HistogramBucket> buckets;
  final int? hoveredIndex;
  final double leftMargin;

  static const double _barGap = 1.5;
  static const double _bottomMargin = 18;
  static const double _topPadding = 4;
  static const double _minBarHeight = 2;
  static const double _minBarWidth = 2;
  static const double _barRadius = 2.0;

  // Severity gradient colors (bottom to top: info → warning → error → critical)
  static const Color _infoColor = Color(0xFF38BDF8); // Sky 400
  static const Color _warningColor = Color(0xFFFBBF24); // Amber 400
  static const Color _errorColor = Color(0xFFF87171); // Red 400
  static const Color _criticalColor = Color(0xFFFF1744); // Deep red

  _HistogramPainter({
    required this.buckets,
    this.hoveredIndex,
    this.leftMargin = 36,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (buckets.isEmpty) {
      _paintEmpty(canvas, size);
      return;
    }

    final chartHeight = size.height - _bottomMargin - _topPadding;
    final chartWidth = size.width - leftMargin;
    final maxTotal = buckets.fold<int>(0, (prev, b) => math.max(prev, b.total));

    if (maxTotal == 0) {
      _paintEmpty(canvas, size);
      return;
    }

    // Y-axis labels
    _paintYAxisLabels(canvas, size, chartHeight, maxTotal);

    // Background gradient behind bars
    _paintBackground(canvas, size, chartHeight);

    final numBuckets = buckets.length;
    var barWidth = (chartWidth - (numBuckets - 1) * _barGap) / numBuckets;
    if (barWidth < _minBarWidth) barWidth = _minBarWidth;

    // Gridlines
    _paintGridlines(canvas, size, chartHeight);

    // Bars
    for (var i = 0; i < numBuckets; i++) {
      final bucket = buckets[i];
      if (bucket.total == 0) continue;

      final x = leftMargin + i * (barWidth + _barGap);
      final totalHeight = math.max(
        _minBarHeight,
        (bucket.total / maxTotal) * chartHeight,
      );

      final isHovered = i == hoveredIndex;
      _paintStackedBar(
        canvas,
        x,
        chartHeight + _topPadding,
        barWidth,
        totalHeight,
        bucket,
        isHovered,
      );

      // Hover column highlight
      if (isHovered) {
        final highlightPaint = Paint()
          ..color = Colors.white.withValues(alpha: 0.06)
          ..style = PaintingStyle.fill;
        canvas.drawRect(
          Rect.fromLTWH(x - 0.5, _topPadding, barWidth + 1, chartHeight),
          highlightPaint,
        );

        final borderPaint = Paint()
          ..color = AppColors.primaryCyan.withValues(alpha: 0.8)
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.5;
        final barTop = chartHeight + _topPadding - totalHeight;
        canvas.drawRRect(
          RRect.fromRectAndCorners(
            Rect.fromLTWH(x, barTop, barWidth, totalHeight),
            topLeft: Radius.circular(_barRadius),
            topRight: Radius.circular(_barRadius),
          ),
          borderPaint,
        );
      }
    }

    // X-axis labels
    _paintXAxisLabels(canvas, size, barWidth);

    // Baseline
    final baselinePaint = Paint()
      ..color = AppColors.surfaceBorder.withValues(alpha: 0.3)
      ..strokeWidth = 1;
    final baseY = chartHeight + _topPadding;
    canvas.drawLine(
      Offset(leftMargin, baseY),
      Offset(size.width, baseY),
      baselinePaint,
    );
  }

  void _paintBackground(Canvas canvas, Size size, double chartHeight) {
    final rect = Rect.fromLTWH(
      leftMargin,
      _topPadding,
      size.width - leftMargin,
      chartHeight,
    );
    final gradient = ui.Gradient.linear(
      Offset(leftMargin, _topPadding),
      Offset(leftMargin, chartHeight + _topPadding),
      [
        Colors.white.withValues(alpha: 0.01),
        Colors.transparent,
      ],
    );
    canvas.drawRect(rect, Paint()..shader = gradient);
  }

  void _paintStackedBar(
    Canvas canvas,
    double x,
    double baseline,
    double barWidth,
    double totalHeight,
    _HistogramBucket bucket,
    bool isHovered,
  ) {
    final alphaMult = isHovered ? 1.0 : 0.85;

    // Segment proportions
    final segments = <_BarSegment>[];
    if (bucket.debugCount > 0) {
      segments.add(_BarSegment(bucket.debugCount, _infoColor.withValues(alpha: 0.4 * alphaMult)));
    }
    if (bucket.infoCount > 0) {
      segments.add(_BarSegment(bucket.infoCount, _infoColor.withValues(alpha: 0.7 * alphaMult)));
    }
    if (bucket.warningCount > 0) {
      segments.add(_BarSegment(bucket.warningCount, _warningColor.withValues(alpha: 0.8 * alphaMult)));
    }
    if (bucket.errorCount > 0) {
      segments.add(_BarSegment(bucket.errorCount, _errorColor.withValues(alpha: 0.85 * alphaMult)));
    }
    if (bucket.criticalCount > 0) {
      segments.add(_BarSegment(bucket.criticalCount, _criticalColor.withValues(alpha: 0.9 * alphaMult)));
    }

    if (segments.isEmpty) return;

    var yPos = baseline;

    for (var s = 0; s < segments.length; s++) {
      final seg = segments[s];
      final segHeight = (seg.count / bucket.total) * totalHeight;
      if (segHeight < 0.5) continue;

      final isTop = s == segments.length - 1;
      final isBottom = s == 0;
      final topRadius = isTop ? Radius.circular(_barRadius) : Radius.zero;
      final bottomRadius = isBottom ? Radius.zero : Radius.zero;

      final paint = Paint()
        ..color = seg.color
        ..style = PaintingStyle.fill;

      final rrect = RRect.fromRectAndCorners(
        Rect.fromLTWH(x, yPos - segHeight, barWidth, segHeight),
        topLeft: topRadius,
        topRight: topRadius,
        bottomLeft: bottomRadius,
        bottomRight: bottomRadius,
      );
      canvas.drawRRect(rrect, paint);
      yPos -= segHeight;
    }

    // Subtle top glow for bars with errors
    if (bucket.errorCount > 0 || bucket.criticalCount > 0) {
      final glowPaint = Paint()
        ..shader = ui.Gradient.linear(
          Offset(x, yPos),
          Offset(x, yPos + 4),
          [
            _errorColor.withValues(alpha: 0.3),
            Colors.transparent,
          ],
        );
      canvas.drawRect(
        Rect.fromLTWH(x, yPos - 2, barWidth, 6),
        glowPaint,
      );
    }
  }

  void _paintGridlines(Canvas canvas, Size size, double chartHeight) {
    final linePaint = Paint()
      ..color = AppColors.surfaceBorder.withValues(alpha: 0.1)
      ..strokeWidth = 0.5;

    for (final fraction in [0.25, 0.5, 0.75]) {
      final y = _topPadding + chartHeight * (1 - fraction);
      canvas.drawLine(
        Offset(leftMargin, y),
        Offset(size.width, y),
        linePaint,
      );
    }
  }

  void _paintYAxisLabels(
    Canvas canvas,
    Size size,
    double chartHeight,
    int maxTotal,
  ) {
    for (final fraction in [0.0, 0.5, 1.0]) {
      final value = (maxTotal * fraction).round();
      final label = _formatAxisCount(value);
      final y = _topPadding + chartHeight * (1 - fraction);

      final tp = TextPainter(
        text: TextSpan(
          text: label,
          style: TextStyle(
            fontSize: 8,
            color: AppColors.textMuted.withValues(alpha: 0.5),
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();

      tp.paint(
        canvas,
        Offset(leftMargin - tp.width - 4, y - tp.height / 2),
      );
    }
  }

  void _paintXAxisLabels(Canvas canvas, Size size, double barWidth) {
    if (buckets.isEmpty) return;

    final chartWidth = size.width - leftMargin;
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
            color: AppColors.textMuted.withValues(alpha: 0.6),
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout();

      final x =
          leftMargin + i * (barWidth + _barGap) + barWidth / 2 - tp.width / 2;
      final clampedX = x.clamp(leftMargin, size.width - tp.width);
      tp.paint(
        canvas,
        Offset(clampedX, size.height - _bottomMargin + 4),
      );
    }
  }

  void _paintEmpty(Canvas canvas, Size size) {
    final chartHeight = size.height - _bottomMargin - _topPadding;
    final linePaint = Paint()
      ..color = AppColors.textMuted.withValues(alpha: 0.15)
      ..strokeWidth = 1;
    final y = chartHeight + _topPadding;
    canvas.drawLine(Offset(leftMargin, y), Offset(size.width, y), linePaint);

    final tp = TextPainter(
      text: TextSpan(
        text: 'No data in range',
        style: TextStyle(
          fontSize: 10,
          color: AppColors.textMuted.withValues(alpha: 0.4),
        ),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    tp.paint(
      canvas,
      Offset(
        leftMargin + (size.width - leftMargin - tp.width) / 2,
        (size.height - tp.height) / 2,
      ),
    );
  }

  static String _formatAxisCount(int count) {
    if (count >= 1000000) return '${(count / 1000000).toStringAsFixed(0)}M';
    if (count >= 1000) return '${(count / 1000).toStringAsFixed(0)}K';
    return count.toString();
  }

  String _formatTimeLabel(DateTime dt) {
    final h = dt.hour.toString().padLeft(2, '0');
    final m = dt.minute.toString().padLeft(2, '0');
    return '$h:$m';
  }

  String _formatDate(DateTime dt) {
    const months = [
      'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
      'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
    ];
    return '${months[dt.month - 1]} ${dt.day}';
  }

  @override
  bool shouldRepaint(_HistogramPainter oldDelegate) =>
      oldDelegate.hoveredIndex != hoveredIndex ||
      oldDelegate.buckets != buckets;
}

class _BarSegment {
  final int count;
  final Color color;
  const _BarSegment(this.count, this.color);
}
