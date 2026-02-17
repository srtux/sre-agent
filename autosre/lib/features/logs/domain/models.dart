import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:flutter/foundation.dart';

part 'models.freezed.dart';
part 'models.g.dart';

@freezed
class LogPattern with _$LogPattern {
  const factory LogPattern({
    @Default('') String template,
    @Default(0) int count,
    @Default({}) @JsonKey(name: 'severity_counts') Map<String, int> severityCounts,
  }) = _LogPattern;

  factory LogPattern.fromJson(Map<String, dynamic> json) => _$LogPatternFromJson(json);
}

@freezed
class LogEntry with _$LogEntry {
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

  factory LogEntry.fromJson(Map<String, dynamic> json) => _$LogEntryFromJson(json);

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
class LogEntriesData with _$LogEntriesData {
  const factory LogEntriesData({
    required List<LogEntry> entries,
    String? filter,
    @JsonKey(name: 'project_id') String? projectId,
    @JsonKey(name: 'next_page_token') String? nextPageToken,
  }) = _LogEntriesData;

  factory LogEntriesData.fromJson(Map<String, dynamic> json) => _$LogEntriesDataFromJson(json);
}
