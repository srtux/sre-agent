import 'package:flutter/foundation.dart';

/// Information about a single span in a distributed trace.
final class SpanInfo {
  final String spanId;
  final String traceId;
  final String name;
  final DateTime startTime;
  final DateTime endTime;
  final Map<String, dynamic> attributes;
  final String status; // 'OK', 'ERROR'
  final String? parentSpanId;

  SpanInfo({
    required this.spanId,
    required this.traceId,
    required this.name,
    required this.startTime,
    required this.endTime,
    required this.attributes,
    required this.status,
    this.parentSpanId,
  });

  Duration get duration => endTime.difference(startTime);

  factory SpanInfo.fromJson(Map<String, dynamic> json) {
    DateTime parseTimeSafe(dynamic raw) {
      if (raw == null) return DateTime.now();
      try {
        return DateTime.parse(raw.toString());
      } catch (_) {
        return DateTime.now();
      }
    }

    return SpanInfo(
      spanId: json['span_id'] as String? ?? '',
      traceId: json['trace_id'] as String? ?? '',
      name: json['name'] as String? ?? '',
      startTime: parseTimeSafe(json['start_time']),
      endTime: parseTimeSafe(json['end_time']),
      attributes: Map<String, dynamic>.from(json['attributes'] as Map? ?? {}),
      status: json['status'] as String? ?? 'OK',
      parentSpanId: json['parent_span_id'] as String?,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is SpanInfo &&
          runtimeType == other.runtimeType &&
          spanId == other.spanId &&
          traceId == other.traceId &&
          name == other.name &&
          startTime == other.startTime &&
          endTime == other.endTime &&
          mapEquals(attributes, other.attributes) &&
          status == other.status &&
          parentSpanId == other.parentSpanId;

  @override
  int get hashCode => Object.hash(
    spanId,
    traceId,
    name,
    startTime,
    endTime,
    status,
    parentSpanId,
  );
}

/// A distributed trace containing multiple spans.
final class Trace {
  final String traceId;
  final List<SpanInfo> spans;

  Trace({required this.traceId, required this.spans});

  factory Trace.fromJson(Map<String, dynamic> json) {
    final rawSpans = json['spans'];
    final List<dynamic> spansList;

    if (rawSpans == null) {
      spansList = [];
    } else if (rawSpans is List) {
      spansList = rawSpans;
    } else {
      spansList = [];
    }

    // Parse each span, filtering out any that fail to parse
    final parsedSpans = <SpanInfo>[];
    for (final item in spansList) {
      try {
        if (item is Map) {
          parsedSpans.add(SpanInfo.fromJson(Map<String, dynamic>.from(item)));
        }
      } catch (_) {
        // Skip malformed spans rather than failing the entire trace
        continue;
      }
    }

    return Trace(
      traceId: json['trace_id'] as String? ?? 'unknown',
      spans: parsedSpans,
    );
  }

  Trace copyWith({String? traceId, List<SpanInfo>? spans}) {
    return Trace(traceId: traceId ?? this.traceId, spans: spans ?? this.spans);
  }

  Map<String, dynamic> toJson() {
    return {
      'trace_id': traceId,
      'spans': spans.map((s) => {
        'span_id': s.spanId,
        'trace_id': s.traceId,
        'name': s.name,
        'start_time': s.startTime.toIso8601String(),
        'end_time': s.endTime.toIso8601String(),
        'attributes': s.attributes,
        'status': s.status,
        'parent_span_id': s.parentSpanId,
      }).toList(),
    };
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Trace &&
          runtimeType == other.runtimeType &&
          traceId == other.traceId &&
          listEquals(spans, other.spans);

  @override
  int get hashCode => Object.hash(traceId, spans.length);
}
