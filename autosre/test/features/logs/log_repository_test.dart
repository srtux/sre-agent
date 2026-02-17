import 'package:flutter_test/flutter_test.dart';
import 'package:dio/dio.dart';
import 'package:autosre/features/logs/data/log_repository.dart';
import 'package:autosre/features/logs/domain/models.dart';

class MockDio extends Fake implements Dio {
  int getCount = 0;
  String? lastPath;
  Map<String, dynamic>? lastParams;
  bool shouldThrowError = false;

  @override
  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
    Options? options,
    CancelToken? cancelToken,
    void Function(int, int)? onReceiveProgress,
  }) async {
    getCount++;
    lastPath = path;
    lastParams = queryParameters;

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

      expect(result.entries.length, 1);
      expect(result.entries.first.payload, 'Test log');
      expect(result.nextPageToken, 'token123');
    });

    test('queryLogs throws exception on 500 error', () async {
      mockDio.shouldThrowError = true;
      expect(() => repository.queryLogs(filter: 'test'), throwsException);
    });
  });
}
