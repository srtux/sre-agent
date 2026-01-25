import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../theme/app_theme.dart';

/// Model for a single metric in the dashboard
class DashboardMetric {
  final String id;
  final String name;
  final String unit;
  final double currentValue;
  final double? previousValue;
  final double? threshold;
  final List<MetricDataPoint> history;
  final String status; // 'normal', 'warning', 'critical'
  final String? anomalyDescription;

  DashboardMetric({
    required this.id,
    required this.name,
    required this.unit,
    required this.currentValue,
    this.previousValue,
    this.threshold,
    this.history = const [],
    this.status = 'normal',
    this.anomalyDescription,
  });

  factory DashboardMetric.fromJson(Map<String, dynamic> json) {
    return DashboardMetric(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      unit: json['unit'] ?? '',
      currentValue: (json['current_value'] as num?)?.toDouble() ?? 0,
      previousValue: (json['previous_value'] as num?)?.toDouble(),
      threshold: (json['threshold'] as num?)?.toDouble(),
      history: (json['history'] as List? ?? [])
          .map((p) => MetricDataPoint.fromJson(Map<String, dynamic>.from(p)))
          .toList(),
      status: json['status'] ?? 'normal',
      anomalyDescription: json['anomaly_description'],
    );
  }

  double get changePercent {
    if (previousValue == null || previousValue == 0) return 0;
    return ((currentValue - previousValue!) / previousValue!) * 100;
  }
}

/// Model for a metric data point
class MetricDataPoint {
  final DateTime timestamp;
  final double value;

  MetricDataPoint({required this.timestamp, required this.value});

  factory MetricDataPoint.fromJson(Map<String, dynamic> json) {
    return MetricDataPoint(
      timestamp: DateTime.parse(json['timestamp']),
      value: (json['value'] as num?)?.toDouble() ?? 0,
    );
  }
}

/// Model for the metrics dashboard
class MetricsDashboardData {
  final String title;
  final String? serviceName;
  final List<DashboardMetric> metrics;
  final DateTime? lastUpdated;

  MetricsDashboardData({
    required this.title,
    this.serviceName,
    required this.metrics,
    this.lastUpdated,
  });

  factory MetricsDashboardData.fromJson(Map<String, dynamic> json) {
    return MetricsDashboardData(
      title: json['title'] ?? 'Metrics Dashboard',
      serviceName: json['service_name'],
      metrics: (json['metrics'] as List? ?? [])
          .map((m) => DashboardMetric.fromJson(Map<String, dynamic>.from(m)))
          .toList(),
      lastUpdated: json['last_updated'] != null
          ? DateTime.parse(json['last_updated'])
          : null,
    );
  }
}

/// Metrics Dashboard Canvas - Real-time multi-metric visualization
class MetricsDashboardCanvas extends StatefulWidget {
  final MetricsDashboardData data;

  const MetricsDashboardCanvas({super.key, required this.data});

  @override
  State<MetricsDashboardCanvas> createState() => _MetricsDashboardCanvasState();
}

class _MetricsDashboardCanvasState extends State<MetricsDashboardCanvas>
    with TickerProviderStateMixin {
  late AnimationController _entranceController;
  late AnimationController _pulseController;
  late Animation<double> _entranceAnimation;
  late Animation<double> _pulseAnimation;

  String? _selectedMetricId;

  @override
  void initState() {
    super.initState();
    _entranceController = AnimationController(
      duration: const Duration(milliseconds: 1000),
      vsync: this,
    );
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    )..repeat(reverse: true);

    _entranceAnimation = CurvedAnimation(
      parent: _entranceController,
      curve: Curves.easeOutCubic,
    );
    _pulseAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _entranceController.forward();
  }

  @override
  void dispose() {
    _entranceController.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'critical':
        return AppColors.error;
      case 'warning':
        return AppColors.warning;
      default:
        return AppColors.success;
    }
  }

  IconData _getStatusIcon(String status) {
    switch (status) {
      case 'critical':
        return Icons.error;
      case 'warning':
        return Icons.warning;
      default:
        return Icons.check_circle;
    }
  }

  @override
  Widget build(BuildContext context) {
    final criticalCount = widget.data.metrics
        .where((m) => m.status == 'critical')
        .length;
    final warningCount = widget.data.metrics
        .where((m) => m.status == 'warning')
        .length;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildHeader(criticalCount, warningCount),
        Expanded(
          child: AnimatedBuilder(
            animation: Listenable.merge([_entranceAnimation, _pulseAnimation]),
            builder: (context, child) {
              return Container(
                margin: const EdgeInsets.symmetric(horizontal: 16),
                child: _buildMetricsGrid(),
              );
            },
          ),
        ),
        if (_selectedMetricId != null) _buildMetricDetails(),
      ],
    );
  }

  Widget _buildHeader(int criticalCount, int warningCount) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
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
              Icons.dashboard,
              size: 18,
              color: AppColors.primaryCyan,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.data.title,
                  style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 2),
                if (widget.data.serviceName != null)
                  Text(
                    widget.data.serviceName!,
                    style: const TextStyle(
                      fontSize: 11,
                      color: AppColors.textMuted,
                    ),
                  ),
              ],
            ),
          ),
          if (criticalCount > 0) ...[
            _buildAlertBadge(criticalCount, 'critical', AppColors.error),
            const SizedBox(width: 8),
          ],
          if (warningCount > 0)
            _buildAlertBadge(warningCount, 'warning', AppColors.warning),
          const SizedBox(width: 8),
          if (widget.data.lastUpdated != null)
            Text(
              'Updated ${DateFormat('HH:mm:ss').format(widget.data.lastUpdated!)}',
              style: const TextStyle(fontSize: 9, color: AppColors.textMuted),
            ),
        ],
      ),
    );
  }

  Widget _buildAlertBadge(int count, String type, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(_getStatusIcon(type), size: 12, color: color),
          const SizedBox(width: 4),
          Text(
            '$count',
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMetricsGrid() {
    final metrics = widget.data.metrics;
    final crossAxisCount = metrics.length <= 4 ? 2 : 3;

    return GridView.builder(
      padding: const EdgeInsets.only(bottom: 8),
      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: crossAxisCount,
        childAspectRatio: 1.3,
        crossAxisSpacing: 12,
        mainAxisSpacing: 12,
      ),
      itemCount: metrics.length,
      itemBuilder: (context, index) {
        final metric = metrics[index];
        final delay = index * 0.1;
        final animProgress =
            (_entranceAnimation.value - delay).clamp(0.0, 1.0) / (1.0 - delay);

        return Opacity(
          opacity: animProgress,
          child: Transform.scale(
            scale: 0.8 + 0.2 * animProgress,
            child: _buildMetricCard(metric),
          ),
        );
      },
    );
  }

  Widget _buildMetricCard(DashboardMetric metric) {
    final isSelected = metric.id == _selectedMetricId;
    final statusColor = _getStatusColor(metric.status);
    final isAnomalous = metric.status != 'normal';

    return GestureDetector(
      onTap: () => setState(
        () => _selectedMetricId = _selectedMetricId == metric.id
            ? null
            : metric.id,
      ),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        decoration: BoxDecoration(
          color: isSelected
              ? statusColor.withValues(alpha: 0.15)
              : AppColors.backgroundCard,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected ? statusColor : AppColors.surfaceBorder,
            width: isSelected ? 2 : 1,
          ),
          boxShadow: [
            if (isAnomalous)
              BoxShadow(
                color: statusColor.withValues(
                  alpha: 0.2 + 0.1 * _pulseAnimation.value,
                ),
                blurRadius: 8 + 4 * _pulseAnimation.value,
                spreadRadius: 0,
              ),
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header row
              Row(
                children: [
                  Expanded(
                    child: Text(
                      metric.name,
                      style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w500,
                        color: AppColors.textSecondary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: statusColor,
                      shape: BoxShape.circle,
                      boxShadow: isAnomalous
                          ? [
                              BoxShadow(
                                color: statusColor.withValues(alpha: 0.5),
                                blurRadius: 4,
                                spreadRadius: 1,
                              ),
                            ]
                          : null,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              // Current value
              Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    _formatValue(metric.currentValue),
                    style: TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                      color: isAnomalous ? statusColor : AppColors.textPrimary,
                      fontFamily: 'monospace',
                    ),
                  ),
                  const SizedBox(width: 4),
                  Padding(
                    padding: const EdgeInsets.only(bottom: 3),
                    child: Text(
                      metric.unit,
                      style: const TextStyle(
                        fontSize: 10,
                        color: AppColors.textMuted,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 6),
              // Change indicator
              _buildChangeIndicator(metric),
              const Spacer(),
              // Sparkline
              if (metric.history.isNotEmpty)
                SizedBox(
                  height: 30,
                  child: CustomPaint(
                    size: const Size(double.infinity, 30),
                    painter: _SparklinePainter(
                      points: metric.history,
                      color: statusColor,
                      threshold: metric.threshold,
                      animProgress: _entranceAnimation.value,
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildChangeIndicator(DashboardMetric metric) {
    final change = metric.changePercent;
    final isPositive = change > 0;
    final isNegative = change < 0;
    final changeColor = isPositive
        ? AppColors.error
        : isNegative
        ? AppColors.success
        : AppColors.textMuted;

    return Row(
      children: [
        if (isPositive)
          Icon(Icons.arrow_upward, size: 12, color: changeColor)
        else if (isNegative)
          Icon(Icons.arrow_downward, size: 12, color: changeColor)
        else
          Icon(Icons.remove, size: 12, color: changeColor),
        const SizedBox(width: 2),
        Text(
          '${change.abs().toStringAsFixed(1)}%',
          style: TextStyle(
            fontSize: 10,
            fontWeight: FontWeight.w500,
            color: changeColor,
          ),
        ),
        if (metric.threshold != null) ...[
          const SizedBox(width: 8),
          Text(
            'Threshold: ${_formatValue(metric.threshold!)}',
            style: const TextStyle(fontSize: 9, color: AppColors.textMuted),
          ),
        ],
      ],
    );
  }

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

  Widget _buildMetricDetails() {
    final metric = widget.data.metrics.firstWhere(
      (m) => m.id == _selectedMetricId,
      orElse: () => widget.data.metrics.first,
    );

    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: _getStatusColor(metric.status).withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: _getStatusColor(metric.status).withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                _getStatusIcon(metric.status),
                size: 16,
                color: _getStatusColor(metric.status),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  metric.name,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: _getStatusColor(metric.status).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  metric.status.toUpperCase(),
                  style: TextStyle(
                    fontSize: 9,
                    fontWeight: FontWeight.w600,
                    color: _getStatusColor(metric.status),
                  ),
                ),
              ),
            ],
          ),
          if (metric.anomalyDescription != null) ...[
            const SizedBox(height: 8),
            Text(
              metric.anomalyDescription!,
              style: const TextStyle(
                fontSize: 11,
                color: AppColors.textSecondary,
              ),
            ),
          ],
          const SizedBox(height: 8),
          // Stats row
          Row(
            children: [
              _buildDetailStat(
                'Current',
                '${_formatValue(metric.currentValue)} ${metric.unit}',
              ),
              if (metric.previousValue != null)
                _buildDetailStat(
                  'Previous',
                  '${_formatValue(metric.previousValue!)} ${metric.unit}',
                ),
              _buildDetailStat(
                'Change',
                '${metric.changePercent >= 0 ? '+' : ''}${metric.changePercent.toStringAsFixed(1)}%',
              ),
              if (metric.threshold != null)
                _buildDetailStat(
                  'Threshold',
                  '${_formatValue(metric.threshold!)} ${metric.unit}',
                ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildDetailStat(String label, String value) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(fontSize: 9, color: AppColors.textMuted),
          ),
          Text(
            value,
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: AppColors.textSecondary,
              fontFamily: 'monospace',
            ),
          ),
        ],
      ),
    );
  }
}

/// Sparkline painter for metric cards
class _SparklinePainter extends CustomPainter {
  final List<MetricDataPoint> points;
  final Color color;
  final double? threshold;
  final double animProgress;

  _SparklinePainter({
    required this.points,
    required this.color,
    this.threshold,
    required this.animProgress,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (points.isEmpty) return;

    final values = points.map((p) => p.value).toList();
    final minVal = values.reduce(math.min);
    final maxVal = values.reduce(math.max);
    final range = maxVal - minVal;

    // Draw threshold line if exists
    if (threshold != null && range > 0) {
      final thresholdY =
          size.height - ((threshold! - minVal) / range) * size.height;
      if (thresholdY >= 0 && thresholdY <= size.height) {
        final thresholdPaint = Paint()
          ..color = AppColors.warning.withValues(alpha: 0.4 * animProgress)
          ..strokeWidth = 1
          ..style = PaintingStyle.stroke;

        canvas.drawLine(
          Offset(0, thresholdY),
          Offset(size.width * animProgress, thresholdY),
          thresholdPaint,
        );
      }
    }

    // Draw sparkline
    final linePath = Path();
    final fillPath = Path();

    for (var i = 0; i < points.length; i++) {
      final x = (i / (points.length - 1)) * size.width * animProgress;
      final normalizedY = range > 0 ? (points[i].value - minVal) / range : 0.5;
      final y =
          size.height - (normalizedY * size.height * 0.9 + size.height * 0.05);

      if (i == 0) {
        linePath.moveTo(x, y);
        fillPath.moveTo(x, size.height);
        fillPath.lineTo(x, y);
      } else {
        linePath.lineTo(x, y);
        fillPath.lineTo(x, y);
      }
    }

    // Complete fill path
    fillPath.lineTo(size.width * animProgress, size.height);
    fillPath.close();

    // Draw fill
    final fillPaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          color.withValues(alpha: 0.3 * animProgress),
          color.withValues(alpha: 0.05 * animProgress),
        ],
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height))
      ..style = PaintingStyle.fill;

    canvas.drawPath(fillPath, fillPaint);

    // Draw line
    final linePaint = Paint()
      ..color = color.withValues(alpha: animProgress)
      ..strokeWidth = 1.5
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    canvas.drawPath(linePath, linePaint);

    // Draw current value dot
    if (points.isNotEmpty && animProgress > 0.9) {
      final lastValue = values.last;
      final lastY = range > 0
          ? size.height -
                ((lastValue - minVal) / range * size.height * 0.9 +
                    size.height * 0.05)
          : size.height / 2;

      final dotPaint = Paint()
        ..color = color
        ..style = PaintingStyle.fill;

      canvas.drawCircle(Offset(size.width * animProgress, lastY), 3, dotPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _SparklinePainter oldDelegate) {
    return oldDelegate.animProgress != animProgress;
  }
}
