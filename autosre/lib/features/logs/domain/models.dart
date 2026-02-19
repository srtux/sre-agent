import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:flutter/foundation.dart';

part 'models.freezed.dart';
part 'models.g.dart';

@freezed
abstract class LogPattern with _$LogPattern {
  const factory LogPattern({
    @Default('') String template,
    @Default(0) int count,
    @Default({}) @JsonKey(name: 'severity_counts') Map<String, int> severityCounts,
  }) = _LogPattern;

  factory LogPattern.fromJson(Map<String, dynamic> json) => _$LogPatternFromJson(json);
}

@freezed
abstract class LogEntry with _$LogEntry {
  const LogEntry._();

  const factory LogEntry({
    @JsonKey(name: 'insert_id') required String insertId,
    required DateTime timestamp,
    @Default('INFO') String severity, // 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
    required dynamic payload, // Can be String (text) or Map (JSON)
    @JsonKey(name: 'resource_labels') @Default({}) Map<String, String> resourceLabels,
    @JsonKey(name: 'resource_type') @Default('unknown') String resourceType,
    @JsonKey(name: 'trace_id') String? traceId,
    @JsonKey(name: 'span_id') String? spanId,
    @JsonKey(name: 'http_request') Map<String, dynamic>? httpRequest,
  }) = _LogEntry;

  factory LogEntry.fromJson(Map<String, dynamic> json) {
    final resourceLabels = <String, String>{};
    final labels = json['resource_labels'];
    if (labels is Map) {
      labels.forEach((k, v) {
        resourceLabels[k.toString()] = v.toString();
      });
    }

    Map<String, dynamic>? httpRequest;
    if (json['http_request'] is Map) {
      httpRequest = Map<String, dynamic>.from(json['http_request'] as Map);
    }

    return LogEntry(
      insertId: json['insert_id']?.toString() ?? '',
      timestamp: json['timestamp'] != null
          ? DateTime.tryParse(json['timestamp'].toString()) ?? DateTime.now()
          : DateTime.now(),
      severity: json['severity']?.toString() ?? 'INFO',
      payload: json['payload'],
      resourceLabels: resourceLabels,
      resourceType: json['resource_type']?.toString() ?? 'unknown',
      traceId: json['trace_id']?.toString(),
      spanId: json['span_id']?.toString(),
      httpRequest: httpRequest,
    );
  }

  bool get isJsonPayload => payload is Map;

  String get payloadPreview {
    if (payload is String) {
      final str = payload as String;
      return str.length > 200 ? '${str.substring(0, 200)}...' : str;
    }
    if (payload is Map) {
      final map = payload as Map;
      final message = map['message'] ?? map['msg'] ?? map['text'];
      if (message != null) return message.toString();
      final str = map.toString();
      return str.length > 200 ? '${str.substring(0, 200)}...' : str;
    }
    return payload?.toString() ?? '';
  }
}

@freezed
abstract class LogEntriesData with _$LogEntriesData {
  // ignore: unused_element
  const LogEntriesData._();

  const factory LogEntriesData({
    required List<LogEntry> entries,
    String? filter,
    @JsonKey(name: 'project_id') String? projectId,
    @JsonKey(name: 'next_page_token') String? nextPageToken,
    int? limit,
  }) = _LogEntriesData;

  factory LogEntriesData.fromJson(Map<String, dynamic> json) {
    return LogEntriesData(
      entries: (json['entries'] as List? ?? [])
          .whereType<Map>()
          .map((e) => LogEntry.fromJson(Map<String, dynamic>.from(e)))
          .toList(),
      filter: json['filter'] as String?,
      projectId: json['project_id'] as String?,
      nextPageToken: json['next_page_token'] as String?,
      limit: json['limit'] as int?,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'entries': entries.map((e) => {
        // LogEntry toJson doesn't exist either? We can just pass minimal representation or empty for dashboard cache.
        // Actually, logData.toJson() is just stored in the dashboard item as `raw`.
        'timestamp': e.timestamp.toIso8601String(),
        'severity': e.severity,
        'payload': e.payload,
        'insert_id': e.insertId,
        'resource_type': e.resourceType,
        'resource_labels': e.resourceLabels,
        'trace_id': e.traceId,
        'span_id': e.spanId,
        'http_request': e.httpRequest,
      }).toList(),
      'filter': filter,
      'project_id': projectId,
      'next_page_token': nextPageToken,
      'limit': limit,
    };
  }
}

/// A single time bucket from the backend histogram endpoint.
class LogHistogramBucket {
  final DateTime start;
  final DateTime end;
  final int debug;
  final int info;
  final int warning;
  final int error;
  final int critical;

  const LogHistogramBucket({
    required this.start,
    required this.end,
    this.debug = 0,
    this.info = 0,
    this.warning = 0,
    this.error = 0,
    this.critical = 0,
  });

  int get total => debug + info + warning + error + critical;

  factory LogHistogramBucket.fromJson(Map<String, dynamic> json) {
    return LogHistogramBucket(
      start: DateTime.parse(json['start'] as String),
      end: DateTime.parse(json['end'] as String),
      debug: (json['debug'] as num?)?.toInt() ?? 0,
      info: (json['info'] as num?)?.toInt() ?? 0,
      warning: (json['warning'] as num?)?.toInt() ?? 0,
      error: (json['error'] as num?)?.toInt() ?? 0,
      critical: (json['critical'] as num?)?.toInt() ?? 0,
    );
  }
}

/// Response from the /api/tools/logs/histogram endpoint.
class LogHistogramData {
  final List<LogHistogramBucket> buckets;
  final int totalCount;
  final int scannedEntries;

  const LogHistogramData({
    required this.buckets,
    this.totalCount = 0,
    this.scannedEntries = 0,
  });

  factory LogHistogramData.fromJson(Map<String, dynamic> json) {
    final bucketList = (json['buckets'] as List? ?? [])
        .whereType<Map>()
        .map((b) => LogHistogramBucket.fromJson(Map<String, dynamic>.from(b)))
        .toList();
    return LogHistogramData(
      buckets: bucketList,
      totalCount: (json['total_count'] as num?)?.toInt() ?? 0,
      scannedEntries: (json['scanned_entries'] as num?)?.toInt() ?? 0,
    );
  }
}
