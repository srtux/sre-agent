import 'package:flutter_test/flutter_test.dart';
import 'package:dio/dio.dart';
import 'package:autosre/features/logs/data/log_repository.dart';

class MockDio extends Fake implements Dio {
  int getCount = 0;
  String? lastPath;
  Map<String, dynamic>? lastParams;
  bool shouldThrowError = false;

  @override
  Future<Response<T>> post<T>(
    String path, {
    Object? data,
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
    void Function(int, int)? onSendProgress,
    void Function(int, int)? onReceiveProgress,
  }) async {
    getCount++;
    lastPath = path;
    if (data is Map<String, dynamic>) {
      lastParams = data;
    }

    if (shouldThrowError) {
      throw DioException(
        requestOptions: RequestOptions(path: path),
        response: Response(
          statusCode: 500,
          requestOptions: RequestOptions(path: path),
          data: 'Internal Server Error',
        ),
        type: DioExceptionType.badResponse,
      );
    }

    return Response<T>(
      data: {
        'entries': [
          {
            'insert_id': '1',
            'timestamp': '2026-02-16T00:00:00Z',
            'severity': 'INFO',
            'payload': 'Test log',
          }
        ],
        'next_page_token': 'token123',
      } as T,
      statusCode: 200,
      requestOptions: RequestOptions(path: path),
    );
  }
}

void main() {
  late LogRepository repository;
  late MockDio mockDio;

  setUp(() {
    mockDio = MockDio();
    repository = LogRepository(mockDio);
  });

  group('LogRepository', () {
    test('queryLogs calls correct endpoint and parses results', () async {
      final result = await repository.queryLogs(
        filter: 'severity=ERROR',
        projectId: 'test-project',
      );

      expect(mockDio.getCount, 1);
      expect(mockDio.lastPath, '/api/tools/logs/query');
      expect(mockDio.lastParams?['filter'], 'severity=ERROR');
      expect(mockDio.lastParams?['project_id'], 'test-project');
      // No page_token or cursor fields sent for a plain query
      expect(mockDio.lastParams?.containsKey('page_token'), false);
      expect(mockDio.lastParams?.containsKey('cursor_timestamp'), false);

      expect(result.entries.length, 1);
      expect(result.entries.first.payload, 'Test log');
    });

    test('queryLogs sends cursor_timestamp when provided', () async {
      final cursor = DateTime.utc(2026, 2, 16, 12, 0, 0);
      await repository.queryLogs(
        filter: 'severity=ERROR',
        projectId: 'test-project',
        cursorTimestamp: cursor,
        cursorInsertId: 'abc123',
      );

      expect(
        mockDio.lastParams?['cursor_timestamp'],
        '2026-02-16T12:00:00.000Z',
      );
      expect(mockDio.lastParams?['cursor_insert_id'], 'abc123');
      // minutes_ago must NOT be sent when cursor is provided
      expect(mockDio.lastParams?.containsKey('minutes_ago'), false);
    });

    test('queryLogs sends minutes_ago when no cursor provided', () async {
      await repository.queryLogs(
        filter: 'severity=ERROR',
        minutesAgo: 30,
      );

      expect(mockDio.lastParams?['minutes_ago'], 30);
      expect(mockDio.lastParams?.containsKey('cursor_timestamp'), false);
    });

    test('queryLogs throws exception on 500 error', () async {
      mockDio.shouldThrowError = true;
      expect(() => repository.queryLogs(filter: 'test'), throwsException);
    });
  });
}
