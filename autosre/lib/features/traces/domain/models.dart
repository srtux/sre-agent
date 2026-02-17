import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:flutter/foundation.dart';

part 'models.freezed.dart';
part 'models.g.dart';

@freezed
abstract class SpanInfo with _$SpanInfo {
  const SpanInfo._();

  const factory SpanInfo({
    @JsonKey(name: 'span_id') required String spanId,
    @JsonKey(name: 'trace_id') required String traceId,
    required String name,
    @JsonKey(name: 'start_time') required DateTime startTime,
    @JsonKey(name: 'end_time') required DateTime endTime,
    @Default({}) Map<String, dynamic> attributes,
    @Default('OK') String status, // 'OK', 'ERROR'
    @JsonKey(name: 'parent_span_id') String? parentSpanId,
  }) = _SpanInfo;

  factory SpanInfo.fromJson(Map<String, dynamic> json) => _$SpanInfoFromJson(json);

  Duration get duration => endTime.difference(startTime);
}

@freezed
abstract class Trace with _$Trace {
  const factory Trace({
    @JsonKey(name: 'trace_id') required String traceId,
    required List<SpanInfo> spans,
  }) = _Trace;

  factory Trace.fromJson(Map<String, dynamic> json) => _$TraceFromJson(json);
}
