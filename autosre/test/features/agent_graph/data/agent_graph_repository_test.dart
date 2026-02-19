import 'package:autosre/features/agent_graph/data/agent_graph_repository.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

const _mockGraphJson = '{"nodes":[{"id":"agent_1","type":"Agent",'
    '"total_tokens":1000,"has_error":false,"is_root":true,"is_leaf":false}],'
    '"edges":[{"source_id":"agent_1","target_id":"tool_1",'
    '"source_type":"Agent","target_type":"Tool","call_count":5,'
    '"error_count":1,"error_rate_pct":20.0,"edge_tokens":500,'
    '"avg_tokens_per_call":100,"avg_duration_ms":150.5,'
    '"p95_duration_ms":300.0,"unique_sessions":3}]}';

class MockDio extends Fake implements Dio {
  int postCount = 0;
  String? lastPath;
  Map<String, dynamic>? lastData;
  bool shouldThrowError = false;
  Map<String, dynamic> mockResponseData = {
    'rows': [
      {'flutter_graph_payload': _mockGraphJson},
    ],
    'columns': ['flutter_graph_payload'],
  };

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
    postCount++;
    lastPath = path;
    if (data is Map<String, dynamic>) {
      lastData = data;
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
      data: mockResponseData as T,
      statusCode: 200,
      requestOptions: RequestOptions(path: path),
    );
  }
}

void main() {
  late AgentGraphRepository repository;
  late MockDio mockDio;

  setUp(() {
    mockDio = MockDio();
    repository = AgentGraphRepository(mockDio);
  });

  group('AgentGraphRepository', () {
    group('buildGraphSql', () {
      test('produces SQL with correct dataset and time range substituted', () {
        final sql = repository.buildGraphSql(
          dataset: 'my-project.my_dataset',
          timeRangeHours: 12,
        );

        expect(sql, contains('`my-project.my_dataset.agent_trace_graph`'));
        expect(sql, contains('INTERVAL 12 HOUR'));
        expect(sql, contains('flutter_graph_payload'));
      });
    });

    group('fetchGraph', () {
      test('calls correct endpoint /api/tools/bigquery/query', () async {
        await repository.fetchGraph();

        expect(mockDio.postCount, 1);
        expect(mockDio.lastPath, '/api/tools/bigquery/query');
        expect(mockDio.lastData?['sql'], isA<String>());
      });

      test('parses response into MultiTraceGraphPayload with correct nodes '
          'and edges', () async {
        final result = await repository.fetchGraph();

        // Verify nodes.
        expect(result.nodes, hasLength(1));
        final node = result.nodes.first;
        expect(node.id, 'agent_1');
        expect(node.type, 'Agent');
        expect(node.totalTokens, 1000);
        expect(node.hasError, isFalse);
        expect(node.isRoot, isTrue);
        expect(node.isLeaf, isFalse);

        // Verify edges.
        expect(result.edges, hasLength(1));
        final edge = result.edges.first;
        expect(edge.sourceId, 'agent_1');
        expect(edge.targetId, 'tool_1');
        expect(edge.sourceType, 'Agent');
        expect(edge.targetType, 'Tool');
        expect(edge.callCount, 5);
        expect(edge.errorCount, 1);
        expect(edge.errorRatePct, 20.0);
        expect(edge.edgeTokens, 500);
        expect(edge.avgTokensPerCall, 100);
        expect(edge.avgDurationMs, 150.5);
        expect(edge.p95DurationMs, 300.0);
        expect(edge.uniqueSessions, 3);
      });

      test('returns empty payload when no rows', () async {
        mockDio.mockResponseData = {
          'rows': <Map<String, dynamic>>[],
          'columns': ['flutter_graph_payload'],
        };

        final result = await repository.fetchGraph();

        expect(result.nodes, isEmpty);
        expect(result.edges, isEmpty);
      });

      test('throws on DioException', () async {
        mockDio.shouldThrowError = true;

        expect(
          () => repository.fetchGraph(),
          throwsA(isA<DioException>()),
        );
      });
    });
  });
}
