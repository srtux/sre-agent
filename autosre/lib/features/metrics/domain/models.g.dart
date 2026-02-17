// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_MetricPoint _$MetricPointFromJson(Map<String, dynamic> json) => _MetricPoint(
  timestamp: DateTime.parse(json['timestamp'] as String),
  value: (json['value'] as num?)?.toDouble() ?? 0.0,
  isAnomaly: json['is_anomaly'] as bool? ?? false,
);

Map<String, dynamic> _$MetricPointToJson(_MetricPoint instance) =>
    <String, dynamic>{
      'timestamp': instance.timestamp.toIso8601String(),
      'value': instance.value,
      'is_anomaly': instance.isAnomaly,
    };

_MetricSeries _$MetricSeriesFromJson(Map<String, dynamic> json) =>
    _MetricSeries(
      metricName: json['metric_name'] as String,
      points: (json['points'] as List<dynamic>)
          .map((e) => MetricPoint.fromJson(e as Map<String, dynamic>))
          .toList(),
      labels: json['labels'] as Map<String, dynamic>? ?? const {},
    );

Map<String, dynamic> _$MetricSeriesToJson(_MetricSeries instance) =>
    <String, dynamic>{
      'metric_name': instance.metricName,
      'points': instance.points,
      'labels': instance.labels,
    };

_MetricDataPoint _$MetricDataPointFromJson(Map<String, dynamic> json) =>
    _MetricDataPoint(
      timestamp: DateTime.parse(json['timestamp'] as String),
      value: (json['value'] as num).toDouble(),
    );

Map<String, dynamic> _$MetricDataPointToJson(_MetricDataPoint instance) =>
    <String, dynamic>{
      'timestamp': instance.timestamp.toIso8601String(),
      'value': instance.value,
    };

_DashboardMetric _$DashboardMetricFromJson(Map<String, dynamic> json) =>
    _DashboardMetric(
      id: json['id'] as String,
      name: json['name'] as String,
      unit: json['unit'] as String,
      currentValue: (json['current_value'] as num).toDouble(),
      previousValue: (json['previous_value'] as num?)?.toDouble(),
      threshold: (json['threshold'] as num?)?.toDouble(),
      history:
          (json['history'] as List<dynamic>?)
              ?.map((e) => MetricDataPoint.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      status: json['status'] as String? ?? 'normal',
      anomalyDescription: json['anomaly_description'] as String?,
    );

Map<String, dynamic> _$DashboardMetricToJson(_DashboardMetric instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'unit': instance.unit,
      'current_value': instance.currentValue,
      'previous_value': instance.previousValue,
      'threshold': instance.threshold,
      'history': instance.history,
      'status': instance.status,
      'anomaly_description': instance.anomalyDescription,
    };

_MetricsDashboardData _$MetricsDashboardDataFromJson(
  Map<String, dynamic> json,
) => _MetricsDashboardData(
  title: json['title'] as String? ?? 'Metrics Dashboard',
  serviceName: json['service_name'] as String?,
  metrics: (json['metrics'] as List<dynamic>)
      .map((e) => DashboardMetric.fromJson(e as Map<String, dynamic>))
      .toList(),
  lastUpdated: json['last_updated'] == null
      ? null
      : DateTime.parse(json['last_updated'] as String),
);

Map<String, dynamic> _$MetricsDashboardDataToJson(
  _MetricsDashboardData instance,
) => <String, dynamic>{
  'title': instance.title,
  'service_name': instance.serviceName,
  'metrics': instance.metrics,
  'last_updated': instance.lastUpdated?.toIso8601String(),
};
