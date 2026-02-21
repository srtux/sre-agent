import 'package:dio/dio.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../shared/data/dio_provider.dart';
import '../domain/models.dart';

part 'log_repository.g.dart';

@riverpod
LogRepository logRepository(Ref ref) {
  return LogRepository(ref.watch(dioProvider));
}

class LogRepository {
  final Dio _dio;

  LogRepository(this._dio);

  Future<LogEntriesData> queryLogs({
    required String filter,
    String? projectId,
    DateTime? cursorTimestamp,
    String? cursorInsertId,
    int? limit,
    int? minutesAgo,
  }) async {
    final data = <String, dynamic>{
      'filter': filter,
      'project_id': projectId,
      'limit': limit,
    };

    if (cursorTimestamp != null) {
      data['cursor_timestamp'] = cursorTimestamp.toUtc().toIso8601String();
      if (cursorInsertId != null) {
        data['cursor_insert_id'] = cursorInsertId;
      }
    } else if (minutesAgo != null) {
      data['minutes_ago'] = minutesAgo;
    }

    final response = await _dio.post('/api/tools/logs/query', data: data);
    return LogEntriesData.fromJson(response.data);
  }

  Future<List<LogEntry>> fetchLogsForSpan({
    required String traceId,
    required String spanId,
    String? projectId,
  }) async {
    if (projectId == null || projectId.isEmpty) {
      throw Exception('Project ID is required. Please select a project first.');
    }
    final filter =
        'trace="projects/$projectId/traces/$traceId" AND spanId="$spanId"';
    final data = await queryLogs(filter: filter, projectId: projectId);
    return data.entries;
  }
}
