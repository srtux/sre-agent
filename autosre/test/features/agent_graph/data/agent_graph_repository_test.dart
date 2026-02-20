import 'package:autosre/features/agent_graph/data/agent_graph_repository.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

const _mockGraphJson = '{"nodes":[{"id":"agent_1","type":"Agent",'
    '"total_tokens":1000,"has_error":false,"avg_duration_ms":100.5,'
    '"error_rate_pct":0.0,"is_root":true,"is_leaf":false}],'
    '"edges":[{"source_id":"agent_1","target_id":"tool_1",'
    '"source_type":"Agent","target_type":"Tool","call_count":5,'
    '"error_count":1,"error_rate_pct":20.0,"total_tokens":500,'
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
    group('buildGraphSql (live GRAPH_TABLE)', () {
      test('produces SQL with correct dataset and time range substituted', () {
        final sql = repository.buildGraphSql(
          dataset: 'my-project.my_dataset',
          timeRangeHours: 12,
        );

        expect(sql, contains('`my-project.my_dataset.agent_topology_nodes`'));
        expect(sql, contains('INTERVAL 12 HOUR'));
        expect(sql, contains('flutter_graph_payload'));
        expect(sql, contains('agent_topology_edges'));
      });
    });

    group('buildPrecomputedGraphSql', () {
      test('produces SQL against agent_graph_hourly table', () {
        final sql = repository.buildPrecomputedGraphSql(
          dataset: 'my-project.my_dataset',
          timeRangeHours: 6,
        );

        expect(sql, contains('`my-project.my_dataset.agent_graph_hourly`'));
        expect(sql, contains('INTERVAL 6 HOUR'));
        expect(sql, contains('flutter_graph_payload'));
        // Must NOT use GRAPH_TABLE — that's the whole point.
        expect(sql, isNot(contains('GRAPH_TABLE')));
      });

      test('includes edge limit when sampleLimit is provided', () {
        final sql = repository.buildPrecomputedGraphSql(
          dataset: 'my-project.my_dataset',
          timeRangeHours: 24,
          sampleLimit: 50,
        );

        expect(sql, contains('LIMIT 50'));
      });

      test('omits edge limit when sampleLimit is null', () {
        final sql = repository.buildPrecomputedGraphSql(
          dataset: 'my-project.my_dataset',
          timeRangeHours: 24,
        );

        expect(sql, isNot(contains('LIMIT')));
      });
    });

    group('fetchGraph', () {
      test('calls correct endpoint /api/tools/bigquery/query', () async {
        await repository.fetchGraph();

        expect(mockDio.postCount, 1);
        expect(mockDio.lastPath, '/api/tools/bigquery/query');
        expect(mockDio.lastData?['sql'], isA<String>());
      });

      test('uses precomputed query for timeRangeHours >= 1', () async {
        await repository.fetchGraph(timeRangeHours: 6);

        final sql = mockDio.lastData?['sql'] as String;
        expect(sql, contains('agent_graph_hourly'));
        expect(sql, isNot(contains('GRAPH_TABLE')));
      });

      test('uses precomputed query for timeRangeHours == 1', () async {
        await repository.fetchGraph(timeRangeHours: 1);

        final sql = mockDio.lastData?['sql'] as String;
        expect(sql, contains('agent_graph_hourly'));
      });

      test('uses live topology query for sub-hour ranges', () async {
        // timeRangeHours < kPrecomputedMinHours should fall back to live query.
        // The UI passes fractional hours as 0 for sub-hour presets (5m, 15m, 30m).
        await repository.fetchGraph(timeRangeHours: 0);

        final sql = mockDio.lastData?['sql'] as String;
        expect(sql, contains('agent_topology_nodes'));
        expect(sql, isNot(contains('agent_graph_hourly')));
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
