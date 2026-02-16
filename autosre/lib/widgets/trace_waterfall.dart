import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../models/adk_schema.dart';
import '../theme/app_theme.dart';
import '../theme/chart_theme.dart';

class _SpanBarData {
  final String spanName;
  final double startOffsetMs;
  final double endOffsetMs;
  final String serviceName;
  final String status;
  final bool isCriticalPath;
  final SpanInfo span;
  final int depth;
  final bool hasChildren;

  _SpanBarData({
    required this.spanName,
    required this.startOffsetMs,
    required this.endOffsetMs,
    required this.serviceName,
    required this.status,
    required this.isCriticalPath,
    required this.span,
    required this.depth,
    required this.hasChildren,
  });

  double get durationMs => endOffsetMs - startOffsetMs;
  bool get isError => status == 'ERROR';
}

class TraceWaterfall extends StatefulWidget {
  final Trace trace;

  const TraceWaterfall({super.key, required this.trace});

  @override
  State<TraceWaterfall> createState() => _TraceWaterfallState();
}

class _TraceWaterfallState extends State<TraceWaterfall> {
  late List<_SpanBarData> _spanBars;
  late Map<String, Color> _serviceColors;
  late double _totalDurationMs;
  SpanInfo? _selectedSpan;
  Set<String> _collapsedSpanIds = {};

  @override
  void initState() {
    super.initState();
    _buildSpanData();
  }

  @override
  void didUpdateWidget(covariant TraceWaterfall oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.trace.traceId != widget.trace.traceId) {
      _collapsedSpanIds.clear();
      _buildSpanData();
      _selectedSpan = null;
    }
  }

  void _buildSpanData() {
    if (widget.trace.spans.isEmpty) {
      _spanBars = [];
      _serviceColors = {};
      _totalDurationMs = 0;
      return;
    }

    final sortedSpans = List<SpanInfo>.from(widget.trace.spans)
      ..sort((a, b) => a.startTime.compareTo(b.startTime));

    final traceStart = sortedSpans.first.startTime;
    final traceEnd = sortedSpans
        .map((s) => s.endTime)
        .reduce((a, b) => a.isAfter(b) ? a : b);
    _totalDurationMs = traceEnd.difference(traceStart).inMicroseconds / 1000.0;
    if (_totalDurationMs <= 0) _totalDurationMs = 1;

    final childrenMap = <String?, List<SpanInfo>>{};
    for (final span in sortedSpans) {
      childrenMap.putIfAbsent(span.parentSpanId, () => []).add(span);
    }

    final allSpanIds = sortedSpans.map((s) => s.spanId).toSet();
    final rootSpans = sortedSpans
        .where(
          (s) => s.parentSpanId == null || !allSpanIds.contains(s.parentSpanId),
        )
        .toList();

    rootSpans.sort((a, b) => a.startTime.compareTo(b.startTime));

    final criticalPathIds = _findCriticalPath(rootSpans, childrenMap);

    final flatData = <_SpanBarData>[];
    _serviceColors = {};
    var colorIndex = 0;

    void flatten(SpanInfo span, int depth) {
      final children = childrenMap[span.spanId] ?? [];
      final hasChildren = children.isNotEmpty;

      final service = _extractServiceName(span.name);
      if (!_serviceColors.containsKey(service)) {
        _serviceColors[service] = ChartTheme
            .seriesColors[colorIndex % ChartTheme.seriesColors.length];
        colorIndex++;
      }

      final offsetMs =
          span.startTime.difference(traceStart).inMicroseconds / 1000.0;
      final endMs = span.endTime.difference(traceStart).inMicroseconds / 1000.0;

      flatData.add(
        _SpanBarData(
          spanName: span.name,
          startOffsetMs: offsetMs,
          endOffsetMs: math.max(endMs, offsetMs + 0.1),
          serviceName: service,
          status: span.status,
          isCriticalPath: criticalPathIds.contains(span.spanId),
          span: span,
          depth: depth,
          hasChildren: hasChildren,
        ),
      );

      if (!_collapsedSpanIds.contains(span.spanId)) {
        children.sort((a, b) => a.startTime.compareTo(b.startTime));
        for (final child in children) {
          flatten(child, depth + 1);
        }
      }
    }

    for (final root in rootSpans) {
      flatten(root, 0);
    }

    _spanBars = flatData;
  }

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

  void _toggleCollapse(String spanId) {
    setState(() {
      if (_collapsedSpanIds.contains(spanId)) {
        _collapsedSpanIds.remove(spanId);
      } else {
        _collapsedSpanIds.add(spanId);
      }
      _buildSpanData();
    });
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
            padding: const EdgeInsets.symmetric(horizontal: 16.0),
            child: _buildTreeTable(),
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
                        '${widget.trace.spans.length} spans',
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
          const SizedBox(width: 8),
          IconButton(
            icon: const Icon(Icons.unfold_more, size: 16),
            tooltip: 'Expand All',
            onPressed: () {
              setState(() {
                _collapsedSpanIds.clear();
                _buildSpanData();
              });
            },
            color: AppColors.textSecondary,
          ),
          IconButton(
            icon: const Icon(Icons.unfold_less, size: 16),
            tooltip: 'Collapse All',
            onPressed: () {
              setState(() {
                _collapsedSpanIds = widget.trace.spans
                    .map((s) => s.spanId)
                    .toSet();
                _buildSpanData();
              });
            },
            color: AppColors.textSecondary,
          ),
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

  Widget _buildTreeTable() {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.backgroundCard,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.surfaceBorder),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final tableWidth = math.max(
            constraints.maxWidth,
            1000.0,
          ); // Minimum width to ensure horizontal scroll

          return SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: SizedBox(
              width: tableWidth,
              child: Column(
                children: [
                  _buildTableHeader(),
                  const Divider(height: 1, color: AppColors.surfaceBorder),
                  Expanded(
                    child: ListView.builder(
                      itemCount: _spanBars.length,
                      itemBuilder: (context, index) {
                        return _buildTableRow(_spanBars[index]);
                      },
                    ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _buildTableHeader() {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 8),
      decoration: const BoxDecoration(
        color: AppColors.backgroundElevated,
        borderRadius: BorderRadius.vertical(top: Radius.circular(8)),
      ),
      child: Row(
        children: [
          const Expanded(
            flex: 3,
            child: Text(
              'Name',
              style: TextStyle(
                color: AppColors.textSecondary,
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          const Expanded(
            flex: 1,
            child: Text(
              'Service',
              style: TextStyle(
                color: AppColors.textSecondary,
                fontSize: 12,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
          Expanded(
            flex: 5,
            child: LayoutBuilder(
              builder: (context, constraints) {
                return Stack(
                  children: [
                    SizedBox(height: 14, width: constraints.maxWidth),
                    const Positioned(
                      left: 0,
                      child: Text(
                        '0s',
                        style: TextStyle(
                          color: AppColors.textMuted,
                          fontSize: 10,
                        ),
                      ),
                    ),
                    Positioned(
                      right: 0,
                      child: Text(
                        '${_totalDurationMs.toStringAsFixed(1)}ms',
                        style: const TextStyle(
                          color: AppColors.textMuted,
                          fontSize: 10,
                        ),
                      ),
                    ),
                    Positioned(
                      left: constraints.maxWidth * 0.25,
                      child: Text(
                        '${(_totalDurationMs * 0.25).toStringAsFixed(0)}ms',
                        style: const TextStyle(
                          color: AppColors.textMuted,
                          fontSize: 10,
                        ),
                      ),
                    ),
                    Positioned(
                      left: constraints.maxWidth * 0.5,
                      child: Text(
                        '${(_totalDurationMs * 0.5).toStringAsFixed(0)}ms',
                        style: const TextStyle(
                          color: AppColors.textMuted,
                          fontSize: 10,
                        ),
                      ),
                    ),
                    Positioned(
                      left: constraints.maxWidth * 0.75,
                      child: Text(
                        '${(_totalDurationMs * 0.75).toStringAsFixed(0)}ms',
                        style: const TextStyle(
                          color: AppColors.textMuted,
                          fontSize: 10,
                        ),
                      ),
                    ),
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTableRow(_SpanBarData bar) {
    final isSelected = _selectedSpan?.spanId == bar.span.spanId;
    final isCollapsed = _collapsedSpanIds.contains(bar.span.spanId);
    final rowBg = isSelected
        ? AppColors.primaryTeal.withValues(alpha: 0.1)
        : Colors.transparent;

    return InkWell(
      onTap: () => setState(() {
        _selectedSpan = isSelected ? null : bar.span;
      }),
      child: Container(
        color: rowBg,
        padding: const EdgeInsets.symmetric(vertical: 2, horizontal: 8),
        constraints: const BoxConstraints(minHeight: 28),
        child: Row(
          children: [
            Expanded(
              flex: 3,
              child: Padding(
                padding: EdgeInsets.only(left: bar.depth * 16.0),
                child: Row(
                  children: [
                    if (bar.hasChildren)
                      InkWell(
                        onTap: () => _toggleCollapse(bar.span.spanId),
                        child: Icon(
                          isCollapsed
                              ? Icons.arrow_right
                              : Icons.arrow_drop_down,
                          size: 20,
                          color: AppColors.textMuted,
                        ),
                      )
                    else
                      const SizedBox(width: 20),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(
                        bar.spanName,
                        style: const TextStyle(
                          color: AppColors.textPrimary,
                          fontSize: 12,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            Expanded(
              flex: 1,
              child: Text(
                bar.serviceName,
                style: const TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 11,
                ),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            Expanded(
              flex: 5,
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final width = constraints.maxWidth;
                  final left = (bar.startOffsetMs / _totalDurationMs) * width;
                  final barWidth = (bar.durationMs / _totalDurationMs) * width;

                  final safeWidth = math.max(barWidth, 3.0);
                  final safeLeft = left.clamp(0.0, width);

                  final barColor = bar.isError
                      ? AppColors.error
                      : (_serviceColors[bar.serviceName] ??
                            AppColors.primaryTeal);

                  return SizedBox(
                    height: 18,
                    child: Stack(
                      clipBehavior: Clip.none,
                      children: [
                        Container(
                          margin: const EdgeInsets.only(top: 8),
                          width: width,
                          height: 1,
                          color: AppColors.surfaceBorder.withValues(alpha: 0.3),
                        ),
                        Positioned(
                          left: safeLeft,
                          width: safeWidth,
                          top: 2,
                          bottom: 2,
                          child: Tooltip(
                            message:
                                '${bar.spanName}\nService: ${bar.serviceName}\nDuration: ${bar.durationMs.toStringAsFixed(2)}ms\nStatus: ${bar.status}',
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: AppColors.backgroundCard,
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(
                                color: AppColors.surfaceBorder,
                              ),
                            ),
                            textStyle: const TextStyle(
                              color: AppColors.textPrimary,
                              fontSize: 11,
                            ),
                            child: Container(
                              decoration: BoxDecoration(
                                color: barColor.withValues(alpha: 0.7),
                                border: Border.all(color: barColor, width: 1),
                                borderRadius: BorderRadius.circular(4),
                              ),
                            ),
                          ),
                        ),
                        if (safeLeft + safeWidth + 40 < width)
                          Positioned(
                            left: safeLeft + safeWidth + 4,
                            top: 2,
                            child: Tooltip(
                              message: '${bar.durationMs.toStringAsFixed(2)}ms',
                              child: Text(
                                '${bar.durationMs.toStringAsFixed(2)}ms',
                                style: const TextStyle(
                                  color: AppColors.textMuted,
                                  fontSize: 9,
                                ),
                                maxLines: 1,
                                overflow: TextOverflow.visible,
                              ),
                            ),
                          ),
                      ],
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildSpanDetailPanel(SpanInfo span) {
    final service = _extractServiceName(span.name);
    final serviceColor = _serviceColors[service] ?? AppColors.primaryTeal;

    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 12),
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
