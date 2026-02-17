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
    String? pageToken,
    int? limit,
  }) async {
    final response = await _dio.post(
      '/api/tools/logs/query',
      data: {
        'filter': filter,
        'project_id': projectId,
        'page_token': pageToken,
        'limit': limit,
      },
    );

    return LogEntriesData.fromJson(response.data);
  }

  Future<List<LogEntry>> fetchLogsForSpan({
    required String traceId,
    required String spanId,
    String? projectId,
  }) async {
    final filter = 'trace="projects/${projectId ?? 'summitt-gcp'}/traces/$traceId" AND spanId="$spanId"';
    final data = await queryLogs(filter: filter, projectId: projectId);
    return data.entries;
  }
}
