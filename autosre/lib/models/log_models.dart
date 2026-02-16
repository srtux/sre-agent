import 'package:flutter/foundation.dart';

/// A log pattern extracted from clustering analysis.
class LogPattern {
  final String template;
  final int count;
  final Map<String, int> severityCounts;

  LogPattern({
    required this.template,
    required this.count,
    required this.severityCounts,
  });

  factory LogPattern.fromJson(Map<String, dynamic> json) {
    return LogPattern(
      template: json['template'] as String? ?? '',
      count: (json['count'] as num?)?.toInt() ?? 0,
      severityCounts:
          (json['severity_counts'] as Map?)?.map(
            (key, value) =>
                MapEntry(key.toString(), (value as num?)?.toInt() ?? 0),
          ) ??
          {},
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is LogPattern &&
          runtimeType == other.runtimeType &&
          template == other.template &&
          count == other.count &&
          mapEquals(severityCounts, other.severityCounts);

  @override
  int get hashCode => Object.hash(template, count, severityCounts.length);
}

/// Individual log entry with full payload for expandable JSON view.
class LogEntry {
  final String insertId;
  final DateTime timestamp;
  final String severity; // 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
  final dynamic payload; // Can be String (text) or Map (JSON)
  final Map<String, String> resourceLabels;
  final String resourceType;
  final String? traceId;
  final String? spanId;
  final Map<String, dynamic>? httpRequest;

  LogEntry({
    required this.insertId,
    required this.timestamp,
    required this.severity,
    required this.payload,
    required this.resourceLabels,
    required this.resourceType,
    this.traceId,
    this.spanId,
    this.httpRequest,
  });

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

  factory LogEntry.fromJson(Map<String, dynamic> json) {
    DateTime ts;
    try {
      ts = DateTime.parse(json['timestamp']?.toString() ?? '');
    } catch (_) {
      ts = DateTime.now();
    }

    // Safely convert resource_labels to Map<String, String>
    final rawLabels = json['resource_labels'];
    final Map<String, String> labels;
    if (rawLabels is Map) {
      labels = rawLabels.map(
        (key, value) => MapEntry(key.toString(), value.toString()),
      );
    } else {
      labels = {};
    }

    return LogEntry(
      insertId: json['insert_id'] as String? ?? '',
      timestamp: ts,
      severity: json['severity'] as String? ?? 'INFO',
      payload: json['payload'],
      resourceLabels: labels,
      resourceType: json['resource_type'] as String? ?? 'unknown',
      traceId: json['trace_id'] as String?,
      spanId: json['span_id'] as String?,
      httpRequest: json['http_request'] != null && json['http_request'] is Map
          ? Map<String, dynamic>.from(json['http_request'] as Map)
          : null,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is LogEntry &&
          runtimeType == other.runtimeType &&
          insertId == other.insertId &&
          timestamp == other.timestamp &&
          severity == other.severity &&
          resourceType == other.resourceType &&
          traceId == other.traceId &&
          spanId == other.spanId;

  @override
  int get hashCode =>
      Object.hash(insertId, timestamp, severity, resourceType, traceId, spanId);
}

/// Container for log entries viewer.
class LogEntriesData {
  final List<LogEntry> entries;
  final String? filter;
  final String? projectId;
  final String? nextPageToken;

  LogEntriesData({
    required this.entries,
    this.filter,
    this.projectId,
    this.nextPageToken,
  });

  factory LogEntriesData.fromJson(Map<String, dynamic> json) {
    final entriesList = (json['entries'] as List? ?? [])
        .whereType<Map>()
        .map((e) => LogEntry.fromJson(Map<String, dynamic>.from(e)))
        .toList();
    return LogEntriesData(
      entries: entriesList,
      filter: json['filter'] as String?,
      projectId: json['project_id'] as String?,
      nextPageToken: json['next_page_token'] as String?,
    );
  }

  LogEntriesData copyWith({
    List<LogEntry>? entries,
    String? filter,
    String? projectId,
    String? nextPageToken,
  }) {
    return LogEntriesData(
      entries: entries ?? this.entries,
      filter: filter ?? this.filter,
      projectId: projectId ?? this.projectId,
      nextPageToken: nextPageToken ?? this.nextPageToken,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is LogEntriesData &&
          runtimeType == other.runtimeType &&
          listEquals(entries, other.entries) &&
          filter == other.filter &&
          projectId == other.projectId &&
          nextPageToken == other.nextPageToken;

  @override
  int get hashCode =>
      Object.hash(entries.length, filter, projectId, nextPageToken);
}
