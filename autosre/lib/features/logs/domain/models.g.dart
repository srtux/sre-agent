// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_LogPattern _$LogPatternFromJson(Map<String, dynamic> json) => _LogPattern(
  template: json['template'] as String? ?? '',
  count: (json['count'] as num?)?.toInt() ?? 0,
  severityCounts:
      (json['severity_counts'] as Map<String, dynamic>?)?.map(
        (k, e) => MapEntry(k, (e as num).toInt()),
      ) ??
      const {},
);

Map<String, dynamic> _$LogPatternToJson(_LogPattern instance) =>
    <String, dynamic>{
      'template': instance.template,
      'count': instance.count,
      'severity_counts': instance.severityCounts,
    };

_LogEntry _$LogEntryFromJson(Map<String, dynamic> json) => _LogEntry(
  insertId: json['insert_id'] as String,
  timestamp: DateTime.parse(json['timestamp'] as String),
  severity: json['severity'] as String? ?? 'INFO',
  payload: json['payload'],
  resourceLabels:
      (json['resource_labels'] as Map<String, dynamic>?)?.map(
        (k, e) => MapEntry(k, e as String),
      ) ??
      const {},
  resourceType: json['resource_type'] as String? ?? 'unknown',
  traceId: json['trace_id'] as String?,
  spanId: json['span_id'] as String?,
  httpRequest: json['http_request'] as Map<String, dynamic>?,
);

Map<String, dynamic> _$LogEntryToJson(_LogEntry instance) => <String, dynamic>{
  'insert_id': instance.insertId,
  'timestamp': instance.timestamp.toIso8601String(),
  'severity': instance.severity,
  'payload': instance.payload,
  'resource_labels': instance.resourceLabels,
  'resource_type': instance.resourceType,
  'trace_id': instance.traceId,
  'span_id': instance.spanId,
  'http_request': instance.httpRequest,
};

_LogEntriesData _$LogEntriesDataFromJson(Map<String, dynamic> json) =>
    _LogEntriesData(
      entries: (json['entries'] as List<dynamic>)
          .map((e) => LogEntry.fromJson(e as Map<String, dynamic>))
          .toList(),
      filter: json['filter'] as String?,
      projectId: json['project_id'] as String?,
      nextPageToken: json['next_page_token'] as String?,
    );

Map<String, dynamic> _$LogEntriesDataToJson(_LogEntriesData instance) =>
    <String, dynamic>{
      'entries': instance.entries,
      'filter': instance.filter,
      'project_id': instance.projectId,
      'next_page_token': instance.nextPageToken,
    };
