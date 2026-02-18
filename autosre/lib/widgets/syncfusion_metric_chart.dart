import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:syncfusion_flutter_charts/charts.dart';
import '../models/adk_schema.dart';
import '../theme/app_theme.dart';
import '../theme/chart_theme.dart';

/// Syncfusion-based metric chart that replaces the FL Chart [MetricCorrelationChart].
///
/// Displays a time-series line chart with:
/// - Main data line with gradient fill
/// - Anomaly scatter points (diamond markers)
/// - Moving average trend line (5-point window, toggleable)
/// - Threshold lines for average and P95 (toggleable)
/// - Trackball tooltips, zoom/pan, and toggleable legend
/// - Statistics row (Min, Max, Avg, P95)
class SyncfusionMetricChart extends StatefulWidget {
  final MetricSeries series;

  const SyncfusionMetricChart({super.key, required this.series});

  @override
  State<SyncfusionMetricChart> createState() => _SyncfusionMetricChartState();
}

class _SyncfusionMetricChartState extends State<SyncfusionMetricChart> {
  bool _showTrendLine = true;
  bool _showThreshold = true;

  // Cached derived data — only recomputed when widget.series changes.
  List<MetricPoint> _sortedPoints = [];
  List<MetricPoint> _anomalyPoints = [];
  List<MetricPoint> _movingAvgPoints = [];
  double _minValue = 0;
  double _maxValue = 0;
  double _avgValue = 0;
  double _p95Value = 0;

  @override
  void initState() {
    super.initState();
    _recomputeData();
  }

  @override
  void didUpdateWidget(SyncfusionMetricChart oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.series.points.length != widget.series.points.length ||
        !identical(oldWidget.series, widget.series)) {
      _recomputeData();
    }
  }

  void _recomputeData() {
    final points = widget.series.points;
    if (points.isEmpty) return;

    _sortedPoints = List<MetricPoint>.from(points)
      ..sort((a, b) => a.timestamp.compareTo(b.timestamp));

    final values = _sortedPoints.map((p) => p.value).toList();
    final sortedValues = List<double>.from(values)..sort();

    _minValue = sortedValues.first;
    _maxValue = sortedValues.last;
    _avgValue = values.reduce((a, b) => a + b) / values.length;
    _p95Value = _calculatePercentile(sortedValues, 95);

    _anomalyPoints = _sortedPoints.where((p) => p.isAnomaly).toList();
    _movingAvgPoints = _calculateMovingAverage(_sortedPoints, 5);
  }

  /// Calculate moving average with a centered window.
  List<MetricPoint> _calculateMovingAverage(
    List<MetricPoint> points,
    int windowSize,
  ) {
    if (points.length < windowSize) {
      return points;
    }

    final result = <MetricPoint>[];
    for (var i = 0; i < points.length; i++) {
      final start = math.max(0, i - windowSize ~/ 2);
      final end = math.min(points.length, i + windowSize ~/ 2 + 1);
      var sum = 0.0;
      for (var j = start; j < end; j++) {
        sum += points[j].value;
      }
      result.add(
        MetricPoint(timestamp: points[i].timestamp, value: sum / (end - start)),
      );
    }
    return result;
  }

  /// Calculate the given percentile from a pre-sorted list of values.
  double _calculatePercentile(List<double> sortedValues, double percentile) {
    if (sortedValues.isEmpty) return 0;
    final index = ((percentile / 100) * (sortedValues.length - 1)).round();
    return sortedValues[index];
  }

  /// Format large numeric values compactly.
  String _formatValue(double value) {
    if (value.abs() >= 1000000) {
      return '${(value / 1000000).toStringAsFixed(1)}M';
    } else if (value.abs() >= 1000) {
      return '${(value / 1000).toStringAsFixed(1)}K';
    } else if (value.abs() < 0.01 && value != 0) {
      return value.toStringAsExponential(1);
    }
    return value.toStringAsFixed(value.abs() < 10 ? 2 : 1);
  }

  @override
  Widget build(BuildContext context) {
    if (widget.series.points.isEmpty) {
      return _buildEmptyState();
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildHeader(),
        const SizedBox(height: 8),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(4, 4, 12, 4),
            child: _buildChart(
              _sortedPoints,
              _anomalyPoints,
              _movingAvgPoints,
              _avgValue,
              _p95Value,
            ),
          ),
        ),
        const SizedBox(height: 8),
        _buildStatsRow(_minValue, _maxValue, _avgValue, _p95Value),
        if (widget.series.labels.isNotEmpty) ...[
          const SizedBox(height: 8),
          _buildLabelsFooter(),
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
              Icons.show_chart_outlined,
              size: 40,
              color: AppColors.textMuted,
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            'No metric data available',
            style: TextStyle(color: AppColors.textMuted, fontSize: 14),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppColors.primaryCyan.withValues(alpha: 0.2),
                  AppColors.primaryBlue.withValues(alpha: 0.15),
                ],
              ),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(
              Icons.insights,
              size: 18,
              color: AppColors.primaryCyan,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Metric Analysis',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  widget.series.metricName,
                  style: const TextStyle(
                    fontSize: 10,
                    color: AppColors.textMuted,
                    fontFamily: 'monospace',
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          _buildToggle(
            'Trend',
            _showTrendLine,
            (v) => setState(() => _showTrendLine = v),
            AppColors.warning,
          ),
          const SizedBox(width: 8),
          _buildToggle(
            'Threshold',
            _showThreshold,
            (v) => setState(() => _showThreshold = v),
            AppColors.primaryCyan,
          ),
        ],
      ),
    );
  }

  Widget _buildToggle(
    String label,
    bool value,
    ValueChanged<bool> onChanged,
    Color color,
  ) {
    return GestureDetector(
      onTap: () => onChanged(!value),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: value
              ? color.withValues(alpha: 0.15)
              : Colors.white.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: value
                ? color.withValues(alpha: 0.3)
                : AppColors.surfaceBorder,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              value ? Icons.check_box : Icons.check_box_outline_blank,
              size: 14,
              color: value ? color : AppColors.textMuted,
            ),
            const SizedBox(width: 6),
            Text(
              label,
              style: TextStyle(
                fontSize: 11,
                color: value ? color : AppColors.textMuted,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildChart(
    List<MetricPoint> sortedPoints,
    List<MetricPoint> anomalyPoints,
    List<MetricPoint> movingAvgPoints,
    double avgValue,
    double p95Value,
  ) {
    return SfCartesianChart(
      plotAreaBorderWidth: 0,
      primaryXAxis: ChartTheme.buildDateTimeAxis(),
      primaryYAxis: ChartTheme.buildNumericAxis(),
      trackballBehavior: ChartTheme.buildTrackball(),
      zoomPanBehavior: ChartTheme.buildZoomPan(),
      legend: ChartTheme.buildLegend(),
      annotations: _showThreshold
          ? <CartesianChartAnnotation>[
              // Average line annotation
              CartesianChartAnnotation(
                widget: Container(),
                coordinateUnit: CoordinateUnit.point,
                x: sortedPoints.first.timestamp,
                y: avgValue,
              ),
            ]
          : null,
      series: <CartesianSeries<MetricPoint, DateTime>>[
        // Main data line
        LineSeries<MetricPoint, DateTime>(
          name: 'Value',
          dataSource: sortedPoints,
          xValueMapper: (MetricPoint p, _) => p.timestamp,
          yValueMapper: (MetricPoint p, _) => p.value,
          color: AppColors.primaryCyan,
          width: 2,
          animationDuration: 1000,
        ),

        // Anomaly scatter points
        if (anomalyPoints.isNotEmpty)
          ScatterSeries<MetricPoint, DateTime>(
            name: 'Anomalies',
            dataSource: anomalyPoints,
            xValueMapper: (MetricPoint p, _) => p.timestamp,
            yValueMapper: (MetricPoint p, _) => p.value,
            color: AppColors.error,
            markerSettings: const MarkerSettings(
              isVisible: true,
              shape: DataMarkerType.diamond,
              width: 10,
              height: 10,
              borderColor: AppColors.error,
              borderWidth: 2,
            ),
            animationDuration: 1200,
          ),

        // Moving average trend line (dashed)
        if (_showTrendLine)
          LineSeries<MetricPoint, DateTime>(
            name: 'Trend (5pt avg)',
            dataSource: movingAvgPoints,
            xValueMapper: (MetricPoint p, _) => p.timestamp,
            yValueMapper: (MetricPoint p, _) => p.value,
            color: AppColors.warning.withValues(alpha: 0.6),
            width: 1.5,
            dashArray: const <double>[6, 3],
            animationDuration: 1000,
          ),

        // Average threshold line
        if (_showThreshold)
          LineSeries<MetricPoint, DateTime>(
            name: 'Avg',
            dataSource: [sortedPoints.first, sortedPoints.last],
            xValueMapper: (MetricPoint p, _) => p.timestamp,
            yValueMapper: (_, _) => avgValue,
            color: AppColors.primaryTeal.withValues(alpha: 0.5),
            width: 1,
            dashArray: const <double>[8, 4],
            animationDuration: 800,
          ),

        // P95 threshold line
        if (_showThreshold)
          LineSeries<MetricPoint, DateTime>(
            name: 'P95',
            dataSource: [sortedPoints.first, sortedPoints.last],
            xValueMapper: (MetricPoint p, _) => p.timestamp,
            yValueMapper: (_, _) => p95Value,
            color: AppColors.warning.withValues(alpha: 0.5),
            width: 1,
            dashArray: const <double>[8, 4],
            animationDuration: 800,
          ),
      ],
    );
  }

  Widget _buildStatsRow(double min, double max, double avg, double p95) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          _buildStatCard(
            'Min',
            _formatValue(min),
            AppColors.info,
            Icons.arrow_downward,
          ),
          const SizedBox(width: 8),
          _buildStatCard(
            'Max',
            _formatValue(max),
            AppColors.warning,
            Icons.arrow_upward,
          ),
          const SizedBox(width: 8),
          _buildStatCard(
            'Avg',
            _formatValue(avg),
            AppColors.primaryTeal,
            Icons.remove,
          ),
          const SizedBox(width: 8),
          _buildStatCard(
            'P95',
            _formatValue(p95),
            AppColors.primaryCyan,
            Icons.show_chart,
          ),
        ],
      ),
    );
  }

  Widget _buildStatCard(
    String label,
    String value,
    Color color,
    IconData icon,
  ) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 6),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: color.withValues(alpha: 0.15)),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 10, color: color),
            const SizedBox(width: 4),
            Text(
              label,
              style: const TextStyle(
                fontSize: 9,
                fontWeight: FontWeight.w500,
                color: AppColors.textMuted,
              ),
            ),
            const SizedBox(width: 6),
            Text(
              value,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: color,
                fontFamily: 'monospace',
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLabelsFooter() {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.03),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.surfaceBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Resource Labels',
            style: TextStyle(
              fontSize: 9,
              fontWeight: FontWeight.w600,
              color: AppColors.textMuted,
            ),
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: 6,
            runSpacing: 4,
            children: widget.series.labels.entries.take(6).map((e) {
              return Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                decoration: BoxDecoration(
                  color: AppColors.primaryTeal.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  '${e.key}: ${e.value}',
                  style: const TextStyle(
                    fontSize: 9,
                    color: AppColors.textSecondary,
                    fontFamily: 'monospace',
                  ),
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}
