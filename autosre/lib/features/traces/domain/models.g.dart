// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_SpanInfo _$SpanInfoFromJson(Map<String, dynamic> json) => _SpanInfo(
  spanId: json['span_id'] as String,
  traceId: json['trace_id'] as String,
  name: json['name'] as String,
  startTime: DateTime.parse(json['start_time'] as String),
  endTime: DateTime.parse(json['end_time'] as String),
  attributes: json['attributes'] as Map<String, dynamic>? ?? const {},
  status: json['status'] as String? ?? 'OK',
  parentSpanId: json['parent_span_id'] as String?,
);

Map<String, dynamic> _$SpanInfoToJson(_SpanInfo instance) => <String, dynamic>{
  'span_id': instance.spanId,
  'trace_id': instance.traceId,
  'name': instance.name,
  'start_time': instance.startTime.toIso8601String(),
  'end_time': instance.endTime.toIso8601String(),
  'attributes': instance.attributes,
  'status': instance.status,
  'parent_span_id': instance.parentSpanId,
};

_Trace _$TraceFromJson(Map<String, dynamic> json) => _Trace(
  traceId: json['trace_id'] as String,
  spans: (json['spans'] as List<dynamic>)
      .map((e) => SpanInfo.fromJson(e as Map<String, dynamic>))
      .toList(),
);

Map<String, dynamic> _$TraceToJson(_Trace instance) => <String, dynamic>{
  'trace_id': instance.traceId,
  'spans': instance.spans,
};
