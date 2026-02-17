import 'package:flutter/foundation.dart';

/// A single data point in a metric time series.
class MetricPoint {
  final DateTime timestamp;
  final double value;
  final bool isAnomaly;

  MetricPoint({
    required this.timestamp,
    required this.value,
    this.isAnomaly = false,
  });

  factory MetricPoint.fromJson(Map<String, dynamic> json) {
    DateTime ts;
    try {
      ts = DateTime.parse(json['timestamp']?.toString() ?? '');
    } catch (_) {
      ts = DateTime.now();
    }
    return MetricPoint(
      timestamp: ts,
      value: (json['value'] as num?)?.toDouble() ?? 0.0,
      isAnomaly: json['is_anomaly'] as bool? ?? false,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is MetricPoint &&
          runtimeType == other.runtimeType &&
          timestamp == other.timestamp &&
          value == other.value &&
          isAnomaly == other.isAnomaly;

  @override
  int get hashCode => Object.hash(timestamp, value, isAnomaly);
}

/// A named series of metric data points with labels.
class MetricSeries {
  final String metricName;
  final List<MetricPoint> points;
  final Map<String, dynamic> labels;

  MetricSeries({
    required this.metricName,
    required this.points,
    required this.labels,
  });

  factory MetricSeries.fromJson(Map<String, dynamic> json) {
    final pointsList = (json['points'] as List? ?? [])
        .whereType<Map>()
        .map((i) => MetricPoint.fromJson(Map<String, dynamic>.from(i)))
        .toList();
    return MetricSeries(
      metricName: json['metric_name'] as String? ?? '',
      points: pointsList,
      labels: Map<String, dynamic>.from(json['labels'] as Map? ?? {}),
    );
  }

  MetricSeries copyWith({
    String? metricName,
    List<MetricPoint>? points,
    Map<String, dynamic>? labels,
  }) {
    return MetricSeries(
      metricName: metricName ?? this.metricName,
      points: points ?? this.points,
      labels: labels ?? this.labels,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'metric_name': metricName,
      'points': points.map((p) => {
        'timestamp': p.timestamp.toIso8601String(),
        'value': p.value,
        'is_anomaly': p.isAnomaly,
      }).toList(),
      'labels': labels,
    };
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is MetricSeries &&
          runtimeType == other.runtimeType &&
          metricName == other.metricName &&
          listEquals(points, other.points) &&
          mapEquals(labels, other.labels);

  @override
  int get hashCode => Object.hash(metricName, points.length);
}

/// A single data point for dashboard metrics (timestamp + value only).
class MetricDataPoint {
  final DateTime timestamp;
  final double value;

  MetricDataPoint({required this.timestamp, required this.value});

  factory MetricDataPoint.fromJson(Map<String, dynamic> json) {
    DateTime ts;
    try {
      ts = DateTime.parse(json['timestamp']?.toString() ?? '');
    } catch (_) {
      ts = DateTime.now();
    }
    return MetricDataPoint(
      timestamp: ts,
      value: (json['value'] as num?)?.toDouble() ?? 0,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is MetricDataPoint &&
          runtimeType == other.runtimeType &&
          timestamp == other.timestamp &&
          value == other.value;

  @override
  int get hashCode => Object.hash(timestamp, value);
}

/// A metric displayed on the dashboard with current/previous values and history.
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
      id: json['id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      unit: json['unit'] as String? ?? '',
      currentValue: (json['current_value'] as num?)?.toDouble() ?? 0,
      previousValue: (json['previous_value'] as num?)?.toDouble(),
      threshold: (json['threshold'] as num?)?.toDouble(),
      history: (json['history'] as List? ?? [])
          .whereType<Map>()
          .map((p) => MetricDataPoint.fromJson(Map<String, dynamic>.from(p)))
          .toList(),
      status: json['status'] as String? ?? 'normal',
      anomalyDescription: json['anomaly_description'] as String?,
    );
  }

  double get changePercent {
    if (previousValue == null || previousValue == 0) return 0;
    return ((currentValue - previousValue!) / previousValue!) * 100;
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is DashboardMetric &&
          runtimeType == other.runtimeType &&
          id == other.id &&
          name == other.name &&
          unit == other.unit &&
          currentValue == other.currentValue &&
          previousValue == other.previousValue &&
          threshold == other.threshold &&
          listEquals(history, other.history) &&
          status == other.status &&
          anomalyDescription == other.anomalyDescription;

  @override
  int get hashCode => Object.hash(
    id,
    name,
    unit,
    currentValue,
    previousValue,
    threshold,
    history.length,
    status,
    anomalyDescription,
  );
}

/// Container for a metrics dashboard with multiple metrics.
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
    DateTime? lastUpdated;
    if (json['last_updated'] != null) {
      try {
        lastUpdated = DateTime.parse(json['last_updated'].toString());
      } catch (_) {
        lastUpdated = null;
      }
    }

    return MetricsDashboardData(
      title: json['title'] as String? ?? 'Metrics Dashboard',
      serviceName: json['service_name'] as String?,
      metrics: (json['metrics'] as List? ?? [])
          .whereType<Map>()
          .map((m) => DashboardMetric.fromJson(Map<String, dynamic>.from(m)))
          .toList(),
      lastUpdated: lastUpdated,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is MetricsDashboardData &&
          runtimeType == other.runtimeType &&
          title == other.title &&
          serviceName == other.serviceName &&
          listEquals(metrics, other.metrics) &&
          lastUpdated == other.lastUpdated;

  @override
  int get hashCode =>
      Object.hash(title, serviceName, metrics.length, lastUpdated);
}
