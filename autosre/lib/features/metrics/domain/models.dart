import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:flutter/foundation.dart';

part 'models.freezed.dart';
part 'models.g.dart';

@freezed
class MetricPoint with _$MetricPoint {
  const factory MetricPoint({
    required DateTime timestamp,
    @Default(0.0) double value,
    @Default(false) @JsonKey(name: 'is_anomaly') bool isAnomaly,
  }) = _MetricPoint;

  factory MetricPoint.fromJson(Map<String, dynamic> json) => _$MetricPointFromJson(json);
}

@freezed
class MetricSeries with _$MetricSeries {
  const factory MetricSeries({
    @JsonKey(name: 'metric_name') required String metricName,
    required List<MetricPoint> points,
    @Default({}) Map<String, dynamic> labels,
  }) = _MetricSeries;

  factory MetricSeries.fromJson(Map<String, dynamic> json) => _$MetricSeriesFromJson(json);
}

@freezed
class MetricDataPoint with _$MetricDataPoint {
  const factory MetricDataPoint({
    required DateTime timestamp,
    required double value,
  }) = _MetricDataPoint;

  factory MetricDataPoint.fromJson(Map<String, dynamic> json) => _$MetricDataPointFromJson(json);
}

@freezed
class DashboardMetric with _$DashboardMetric {
  const DashboardMetric._();

  const factory DashboardMetric({
    required String id,
    required String name,
    required String unit,
    @JsonKey(name: 'current_value') required double currentValue,
    @JsonKey(name: 'previous_value') double? previousValue,
    double? threshold,
    @Default([]) List<MetricDataPoint> history,
    @Default('normal') String status, // 'normal', 'warning', 'critical'
    @JsonKey(name: 'anomaly_description') String? anomalyDescription,
  }) = _DashboardMetric;

  factory DashboardMetric.fromJson(Map<String, dynamic> json) => _$DashboardMetricFromJson(json);

  double get changePercent {
    if (previousValue == null || previousValue == 0) return 0;
    return ((currentValue - previousValue!) / previousValue!) * 100;
  }
}

@freezed
class MetricsDashboardData with _$MetricsDashboardData {
  const factory MetricsDashboardData({
    @Default('Metrics Dashboard') String title,
    @JsonKey(name: 'service_name') String? serviceName,
    required List<DashboardMetric> metrics,
    @JsonKey(name: 'last_updated') DateTime? lastUpdated,
  }) = _MetricsDashboardData;

  factory MetricsDashboardData.fromJson(Map<String, dynamic> json) => _$MetricsDashboardDataFromJson(json);
}
