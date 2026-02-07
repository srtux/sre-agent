import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:syncfusion_flutter_charts/charts.dart';
import '../models/adk_schema.dart';
import '../theme/app_theme.dart';
import '../theme/chart_theme.dart';

/// Data model for a single span bar in the waterfall chart.
class _SpanBarData {
  final String spanName;
  final double startOffsetMs;
  final double endOffsetMs;
  final String serviceName;
  final String status;
  final bool isCriticalPath;
  final SpanInfo span;

  _SpanBarData({
    required this.spanName,
    required this.startOffsetMs,
    required this.endOffsetMs,
    required this.serviceName,
    required this.status,
    required this.isCriticalPath,
    required this.span,
  });

  double get durationMs => endOffsetMs - startOffsetMs;
  bool get isError => status == 'ERROR';
}

/// Syncfusion-based trace waterfall chart that replaces the custom [TraceWaterfall].
///
/// Displays a transposed (horizontal) range bar chart where each bar represents
/// a span's execution window. Features include:
/// - Horizontal span bars colored by service
/// - Critical path highlighting with glow border
/// - Service legend with unique color mapping
/// - Tooltip with span details on hover/tap
/// - Span detail panel on bar tap
class SyncfusionTraceWaterfall extends StatefulWidget {
  final Trace trace;

  const SyncfusionTraceWaterfall({super.key, required this.trace});

  @override
  State<SyncfusionTraceWaterfall> createState() =>
      _SyncfusionTraceWaterfallState();
}

class _SyncfusionTraceWaterfallState extends State<SyncfusionTraceWaterfall> {
  late List<_SpanBarData> _spanBars;
  late Map<String, Color> _serviceColors;
  late double _totalDurationMs;
  SpanInfo? _selectedSpan;

  @override
  void initState() {
    super.initState();
    _buildSpanData();
  }

  @override
  void didUpdateWidget(covariant SyncfusionTraceWaterfall oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.trace.traceId != widget.trace.traceId) {
      _buildSpanData();
      _selectedSpan = null;
    }
  }

  /// Build the flattened span bar data from the trace's span hierarchy.
  void _buildSpanData() {
    if (widget.trace.spans.isEmpty) {
      _spanBars = [];
      _serviceColors = {};
      _totalDurationMs = 0;
      return;
    }

    // Sort spans by start time.
    final sortedSpans = List<SpanInfo>.from(widget.trace.spans)
      ..sort((a, b) => a.startTime.compareTo(b.startTime));

    final traceStart = sortedSpans.first.startTime;
    final traceEnd = sortedSpans
        .map((s) => s.endTime)
        .reduce((a, b) => a.isAfter(b) ? a : b);
    _totalDurationMs = traceEnd.difference(traceStart).inMicroseconds / 1000.0;
    if (_totalDurationMs <= 0) _totalDurationMs = 1;

    // Build parent-child map for hierarchy ordering.
    final childrenMap = <String?, List<SpanInfo>>{};
    for (final span in sortedSpans) {
      childrenMap.putIfAbsent(span.parentSpanId, () => []).add(span);
    }

    // Identify root spans (no parent, or parent not present in trace).
    final allSpanIds = sortedSpans.map((s) => s.spanId).toSet();
    final rootSpans = sortedSpans.where(
      (s) => s.parentSpanId == null || !allSpanIds.contains(s.parentSpanId),
    );

    // Find critical path (longest execution chain).
    final criticalPathIds = _findCriticalPath(rootSpans.toList(), childrenMap);

    // Flatten hierarchy in depth-first order.
    final flatSpans = <SpanInfo>[];
    void flatten(SpanInfo span) {
      flatSpans.add(span);
      final children = childrenMap[span.spanId] ?? [];
      for (final child in children) {
        flatten(child);
      }
    }

    for (final root in rootSpans) {
      flatten(root);
    }

    // Assign service colors.
    _serviceColors = {};
    var colorIndex = 0;
    for (final span in flatSpans) {
      final service = _extractServiceName(span.name);
      if (!_serviceColors.containsKey(service)) {
        _serviceColors[service] = ChartTheme
            .seriesColors[colorIndex % ChartTheme.seriesColors.length];
        colorIndex++;
      }
    }

    // Build span bar data.
    _spanBars = flatSpans.map((span) {
      final offsetMs =
          span.startTime.difference(traceStart).inMicroseconds / 1000.0;
      final endMs = span.endTime.difference(traceStart).inMicroseconds / 1000.0;
      final service = _extractServiceName(span.name);

      return _SpanBarData(
        spanName: span.name,
        startOffsetMs: offsetMs,
        endOffsetMs: math.max(endMs, offsetMs + 0.5), // Minimum bar width
        serviceName: service,
        status: span.status,
        isCriticalPath: criticalPathIds.contains(span.spanId),
        span: span,
      );
    }).toList();
  }

  /// Find the critical path as the set of span IDs along the longest
  /// cumulative-duration chain from root to leaf.
  Set<String> _findCriticalPath(
    List<SpanInfo> roots,
    Map<String?, List<SpanInfo>> childrenMap,
  ) {
    var bestPath = <String>{};
    var bestDuration = 0;

    void walk(SpanInfo span, Set<String> path, int cumDuration) {
      path.add(span.spanId);
      final newDuration = cumDuration + span.duration.inMicroseconds;
      final children = childrenMap[span.spanId] ?? [];

      if (children.isEmpty) {
        if (newDuration > bestDuration) {
          bestDuration = newDuration;
          bestPath = Set<String>.from(path);
        }
      } else {
        for (final child in children) {
          walk(child, Set<String>.from(path), newDuration);
        }
      }
    }

    for (final root in roots) {
      walk(root, {}, 0);
    }
    return bestPath;
  }

  /// Extract a service name from a span name using common delimiter patterns.
  String _extractServiceName(String spanName) {
    final colonIndex = spanName.indexOf(':');
    final slashIndex = spanName.indexOf('/');
    final dotIndex = spanName.indexOf('.');

    var splitIndex = spanName.length;
    if (colonIndex > 0) splitIndex = math.min(splitIndex, colonIndex);
    if (slashIndex > 0) splitIndex = math.min(splitIndex, slashIndex);
    if (dotIndex > 0) splitIndex = math.min(splitIndex, dotIndex);

    return spanName.substring(0, splitIndex);
  }

  @override
  Widget build(BuildContext context) {
    if (widget.trace.spans.isEmpty) {
      return _buildEmptyState();
    }

    final errorCount = widget.trace.spans
        .where((s) => s.status == 'ERROR')
        .length;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildHeader(errorCount),
        const SizedBox(height: 8),
        _buildServiceLegend(),
        const SizedBox(height: 8),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(4, 4, 12, 4),
            child: _buildChart(),
          ),
        ),
        if (_selectedSpan != null) ...[
          const SizedBox(height: 8),
          _buildSpanDetailPanel(_selectedSpan!),
        ],
      ],
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.textMuted.withValues(alpha: 0.1),
              shape: BoxShape.circle,
            ),
            child: const Icon(
              Icons.timeline_outlined,
              size: 40,
              color: AppColors.textMuted,
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            'No spans in trace',
            style: TextStyle(color: AppColors.textMuted, fontSize: 14),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader(int errorCount) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppColors.primaryTeal.withValues(alpha: 0.2),
                  AppColors.primaryCyan.withValues(alpha: 0.15),
                ],
              ),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(
              Icons.account_tree,
              size: 18,
              color: AppColors.primaryTeal,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Text(
                      'Trace Waterfall',
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 6,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: AppColors.primaryTeal.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        '${_spanBars.length} spans',
                        style: const TextStyle(
                          fontSize: 10,
                          color: AppColors.primaryTeal,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                Row(
                  children: [
                    const Icon(
                      Icons.fingerprint,
                      size: 10,
                      color: AppColors.textMuted,
                    ),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(
                        widget.trace.traceId,
                        style: const TextStyle(
                          fontSize: 10,
                          fontFamily: 'monospace',
                          color: AppColors.textMuted,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          _buildStatChip(
            '${_totalDurationMs.toStringAsFixed(1)}ms',
            Icons.timer_outlined,
            AppColors.primaryCyan,
          ),
          if (errorCount > 0) ...[
            const SizedBox(width: 8),
            _buildStatChip(
              '$errorCount errors',
              Icons.error_outline,
              AppColors.error,
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildStatChip(String text, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.25)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 4),
          Text(
            text,
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w500,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildServiceLegend() {
    return Container(
      height: 28,
      margin: const EdgeInsets.symmetric(horizontal: 16),
      child: ListView(
        scrollDirection: Axis.horizontal,
        children: _serviceColors.entries.map((e) {
          return Container(
            margin: const EdgeInsets.only(right: 12),
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: e.value.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(4),
              border: Border.all(color: e.value.withValues(alpha: 0.3)),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: e.value,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  e.key,
                  style: TextStyle(
                    fontSize: 10,
                    color: e.value,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildChart() {
    return SfCartesianChart(
      isTransposed: true,
      plotAreaBorderWidth: 0,
      primaryXAxis: CategoryAxis(
        majorGridLines: const MajorGridLines(width: 0),
        labelStyle: const TextStyle(
          color: AppColors.textSecondary,
          fontSize: 10,
        ),
        axisLine: AxisLine(
          color: AppColors.surfaceBorder.withValues(alpha: 0.3),
        ),
      ),
      primaryYAxis: NumericAxis(
        title: const AxisTitle(
          text: 'Duration (ms)',
          textStyle: TextStyle(color: AppColors.textMuted, fontSize: 10),
        ),
        majorGridLines: MajorGridLines(
          color: AppColors.surfaceBorder.withValues(alpha: 0.15),
          dashArray: const <double>[4, 4],
        ),
        minorGridLines: const MinorGridLines(width: 0),
        labelStyle: const TextStyle(color: AppColors.textMuted, fontSize: 10),
        axisLine: const AxisLine(width: 0),
        minimum: 0,
        maximum: _totalDurationMs * 1.05,
      ),
      tooltipBehavior: TooltipBehavior(
        enable: true,
        color: AppColors.backgroundCard,
        textStyle: const TextStyle(color: AppColors.textPrimary, fontSize: 11),
        borderColor: AppColors.primaryCyan,
        borderWidth: 1,
        builder:
            (
              dynamic data,
              dynamic point,
              dynamic series,
              int pointIndex,
              int seriesIndex,
            ) {
              final bar = _spanBars[pointIndex];
              return Container(
                padding: const EdgeInsets.all(10),
                constraints: const BoxConstraints(maxWidth: 250),
                decoration: BoxDecoration(
                  color: AppColors.backgroundCard,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: AppColors.primaryCyan),
                ),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      bar.spanName,
                      style: const TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Service: ${bar.serviceName}',
                      style: const TextStyle(
                        color: AppColors.textSecondary,
                        fontSize: 10,
                      ),
                    ),
                    Text(
                      'Duration: ${bar.durationMs.toStringAsFixed(2)}ms',
                      style: const TextStyle(
                        color: AppColors.textSecondary,
                        fontSize: 10,
                      ),
                    ),
                    Text(
                      'Status: ${bar.status}',
                      style: TextStyle(
                        color: bar.isError
                            ? AppColors.error
                            : AppColors.success,
                        fontSize: 10,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    if (bar.isCriticalPath)
                      const Text(
                        'On Critical Path',
                        style: TextStyle(
                          color: AppColors.warning,
                          fontSize: 10,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                  ],
                ),
              );
            },
      ),
      series: <CartesianSeries<_SpanBarData, String>>[
        RangeColumnSeries<_SpanBarData, String>(
          dataSource: _spanBars,
          xValueMapper: (_SpanBarData bar, _) => _truncateLabel(bar.spanName),
          lowValueMapper: (_SpanBarData bar, _) => bar.startOffsetMs,
          highValueMapper: (_SpanBarData bar, _) => bar.endOffsetMs,
          pointColorMapper: (_SpanBarData bar, _) {
            if (bar.isError) return AppColors.error;
            return _serviceColors[bar.serviceName] ?? AppColors.primaryTeal;
          },
          borderColor: Colors.transparent,
          borderWidth: 0,
          borderRadius: const BorderRadius.all(Radius.circular(3)),
          animationDuration: 800,
          onPointTap: (ChartPointDetails details) {
            final idx = details.pointIndex;
            if (idx != null && idx >= 0 && idx < _spanBars.length) {
              setState(() {
                final tapped = _spanBars[idx].span;
                _selectedSpan = _selectedSpan?.spanId == tapped.spanId
                    ? null
                    : tapped;
              });
            }
          },
        ),
      ],
    );
  }

  /// Truncate long span names for chart Y-axis labels.
  String _truncateLabel(String name) {
    if (name.length <= 30) return name;
    return '${name.substring(0, 27)}...';
  }

  Widget _buildSpanDetailPanel(SpanInfo span) {
    final service = _extractServiceName(span.name);
    final serviceColor = _serviceColors[service] ?? AppColors.primaryTeal;

    return Container(
      margin: const EdgeInsets.fromLTRB(12, 0, 12, 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.backgroundElevated,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.surfaceBorder),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.3),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
          BoxShadow(
            color: (span.status == 'ERROR' ? AppColors.error : serviceColor)
                .withValues(alpha: 0.15),
            blurRadius: 24,
            spreadRadius: -4,
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: serviceColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Icon(
                  span.status == 'ERROR' ? Icons.error : Icons.check_circle,
                  size: 16,
                  color: span.status == 'ERROR'
                      ? AppColors.error
                      : serviceColor,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      span.name,
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    Text(
                      service,
                      style: TextStyle(fontSize: 10, color: serviceColor),
                    ),
                  ],
                ),
              ),
              IconButton(
                icon: const Icon(Icons.close, size: 16),
                onPressed: () => setState(() => _selectedSpan = null),
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
                color: AppColors.textMuted,
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 12,
            runSpacing: 6,
            children: [
              _buildDetailChip(
                'Span ID',
                span.spanId.substring(0, math.min(8, span.spanId.length)),
                serviceColor,
              ),
              _buildDetailChip(
                'Duration',
                '${span.duration.inMilliseconds}ms',
                AppColors.primaryCyan,
              ),
              _buildDetailChip(
                'Status',
                span.status,
                span.status == 'ERROR' ? AppColors.error : AppColors.success,
              ),
              if (span.parentSpanId != null)
                _buildDetailChip(
                  'Parent',
                  span.parentSpanId!.substring(
                    0,
                    math.min(8, span.parentSpanId!.length),
                  ),
                  AppColors.textMuted,
                ),
            ],
          ),
          if (span.attributes.isNotEmpty) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Attributes',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textMuted,
                    ),
                  ),
                  const SizedBox(height: 6),
                  ...span.attributes.entries
                      .take(6)
                      .map(
                        (e) => Padding(
                          padding: const EdgeInsets.only(bottom: 3),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              SizedBox(
                                width: 100,
                                child: Text(
                                  '${e.key}:',
                                  style: const TextStyle(
                                    fontSize: 10,
                                    color: AppColors.textMuted,
                                  ),
                                ),
                              ),
                              Expanded(
                                child: Text(
                                  '${e.value}',
                                  style: const TextStyle(
                                    fontSize: 10,
                                    color: AppColors.textSecondary,
                                    fontFamily: 'monospace',
                                  ),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildDetailChip(String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withValues(alpha: 0.2)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '$label: ',
            style: const TextStyle(fontSize: 10, color: AppColors.textMuted),
          ),
          Text(
            value,
            style: TextStyle(
              fontSize: 10,
              color: color,
              fontWeight: FontWeight.w500,
              fontFamily: 'monospace',
            ),
          ),
        ],
      ),
    );
  }
}

// Note: Critical path highlighting is handled via pointColorMapper above.
// Future enhancement: custom rendering can be added via SelectionBehavior
// or by overlaying additional series for glow effects.
