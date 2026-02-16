import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:autosre/widgets/dashboard/bigquery_sidebar.dart';
import 'package:autosre/services/explorer_query_service.dart';
import 'package:autosre/services/dashboard_state.dart';

class MockExplorer extends ExplorerQueryService {
  MockExplorer(DashboardState state)
    : super(
        dashboardState: state,
        clientFactory: () async => throw Exception('unsupported'),
      );

  @override
  Future<List<String>> getDatasets({String? projectId}) async {
    return ['traces'];
  }

  @override
  Future<List<String>> getTables({
    required String datasetId,
    String? projectId,
  }) async {
    return ['_AllSpans'];
  }

  @override
  Future<List<Map<String, dynamic>>?> getTableSchema({
    required String datasetId,
    required String tableId,
    String? projectId,
  }) async {
    return [
      {
        'name': 'trace_id',
        'type': 'STRING',
        'mode': 'NULLABLE',
        'description': 'a',
        'fields': [],
      },
      {
        'name': 'events',
        'type': 'RECORD',
        'mode': 'REPEATED',
        'fields': [
          {'name': 'time', 'type': 'TIMESTAMP'},
        ],
      },
    ];
  }
}

void main() {
  testWidgets('BigQuerySidebar renders schema correctly', (
    WidgetTester tester,
  ) async {
    final state = DashboardState();
    final explorer = MockExplorer(state);

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider.value(value: state),
          Provider<ExplorerQueryService>.value(value: explorer),
        ],
        child: const MaterialApp(
          home: Scaffold(
            body: SizedBox(width: 280, height: 800, child: BigQuerySidebar()),
          ),
        ),
      ),
    );

    await tester.pumpAndSettle();

    // Verify datasets and tables loaded
    expect(find.text('_AllSpans'), findsOneWidget);

    // Expand the tile
    await tester.tap(find.text('_AllSpans'));
    await tester.pumpAndSettle();

    // Verify schema loaded
    expect(find.text('trace_id'), findsOneWidget);
    expect(find.text('events'), findsOneWidget);

    // Check if any exceptions were thrown
    if (tester.takeException() != null) {
      fail('Exception thrown during build: ${tester.takeException()}');
    }
  });
}
