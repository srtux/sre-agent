import 'package:autosre/features/agent_graph/domain/models.dart';
import 'package:autosre/features/agent_graph/presentation/agent_graph_details_panel.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:autosre/features/agent_graph/data/agent_graph_repository.dart';

class FakeAgentGraphRepository implements AgentGraphRepository {
  @override
  Future<Map<String, dynamic>> fetchNodeDetails({
    required String dataset,
    required String nodeId,
    required int timeRangeHours,
    String? projectId,
  }) async => {
    'latency': {'p50': 100, 'p90': 200, 'p99': 300, 'max_val': 400},
    'top_errors': [],
  };

  @override
  Future<Map<String, dynamic>> fetchEdgeDetails({
    required String dataset,
    required String sourceId,
    required String targetId,
    required int timeRangeHours,
    String? projectId,
  }) async => {
    'latency': {'p50': 100, 'p90': 200, 'p99': 300, 'max_val': 400},
    'top_errors': [],
  };

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

Widget _wrap(Widget child) {
  return ProviderScope(
    overrides: [
      agentGraphRepositoryProvider.overrideWithValue(
        FakeAgentGraphRepository(),
      ),
    ],
    child: MaterialApp(home: Scaffold(body: child)),
  );
}

void main() {
  const testPayload = MultiTraceGraphPayload(
    nodes: [
      MultiTraceNode(id: 'root-agent', type: 'agent', totalTokens: 100),
      MultiTraceNode(id: 'tool-1', type: 'tool', totalTokens: 300),
    ],
    edges: [],
  );

  group('AgentGraphDetailsPanel', () {
    testWidgets('renders nothing when selected is null', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(
        _wrap(
          const AgentGraphDetailsPanel(payload: testPayload, selected: null),
        ),
      );

      // SizedBox.shrink has zero dimensions and no children.
      expect(find.byType(SizedBox), findsOneWidget);
      // The container with width 320 should not be present.
      expect(find.byType(SingleChildScrollView), findsNothing);
    });

    testWidgets('shows node type and id when a SelectedNode is provided', (
      WidgetTester tester,
    ) async {
      const node = MultiTraceNode(id: 'orchestrator', type: 'agent');

      await tester.pumpWidget(
        _wrap(
          const AgentGraphDetailsPanel(
            payload: testPayload,
            selected: SelectedGraphElement.node(node),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // The header displays the node id as title text.
      expect(find.text('orchestrator'), findsOneWidget);
      // The detail section shows the type in a metric card.
      expect(find.text('agent'), findsOneWidget);
    });

    testWidgets('shows description text when node has a description', (
      WidgetTester tester,
    ) async {
      const node = MultiTraceNode(
        id: 'trace-analyzer',
        type: 'tool',
        description: 'Analyzes distributed traces',
      );

      await tester.pumpWidget(
        _wrap(
          const AgentGraphDetailsPanel(
            payload: testPayload,
            selected: SelectedGraphElement.node(node),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Description'), findsOneWidget);
      expect(find.text('Analyzes distributed traces'), findsOneWidget);
    });

    testWidgets('shows "Has Errors" badge when node.hasError is true', (
      WidgetTester tester,
    ) async {
      const node = MultiTraceNode(
        id: 'failing-tool',
        type: 'tool',
        hasError: true,
      );

      await tester.pumpWidget(
        _wrap(
          const AgentGraphDetailsPanel(
            payload: testPayload,
            selected: SelectedGraphElement.node(node),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Has Errors'), findsOneWidget);
    });

    testWidgets('shows "Root" badge when node.isRoot is true', (
      WidgetTester tester,
    ) async {
      const node = MultiTraceNode(
        id: 'root-agent',
        type: 'agent',
        isRoot: true,
      );

      await tester.pumpWidget(
        _wrap(
          const AgentGraphDetailsPanel(
            payload: testPayload,
            selected: SelectedGraphElement.node(node),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Root'), findsOneWidget);
    });

    testWidgets(
      'shows call count and unique sessions when a SelectedEdge is provided',
      (WidgetTester tester) async {
        const edge = MultiTraceEdge(
          sourceId: 'agent_1',
          targetId: 'tool_1',
          callCount: 42,
          uniqueSessions: 7,
        );

        await tester.pumpWidget(
          _wrap(
            const AgentGraphDetailsPanel(
              payload: testPayload,
              selected: SelectedGraphElement.edge(edge),
            ),
          ),
        );
        await tester.pumpAndSettle();

        // Header shows source -> target.
        expect(find.textContaining('agent_1'), findsOneWidget);
        expect(find.textContaining('tool_1'), findsOneWidget);

        // Metric rows show the values.
        expect(find.text('Call Count'), findsOneWidget);
        expect(find.text('42'), findsOneWidget);
        expect(find.text('Unique Sessions'), findsOneWidget);
        expect(find.text('7'), findsOneWidget);
      },
    );

    testWidgets('shows sample error text when edge has sampleError', (
      WidgetTester tester,
    ) async {
      const edge = MultiTraceEdge(
        sourceId: 'a',
        targetId: 'b',
        errorCount: 3,
        sampleError: 'Connection refused',
      );

      await tester.pumpWidget(
        _wrap(
          const AgentGraphDetailsPanel(
            payload: testPayload,
            selected: SelectedGraphElement.edge(edge),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('Sample Error'), findsOneWidget);
      expect(find.text('Connection refused'), findsOneWidget);
    });

    testWidgets('calls onClose when close button is tapped', (
      WidgetTester tester,
    ) async {
      var closeCalled = false;

      const node = MultiTraceNode(id: 'n1', type: 'agent');

      await tester.pumpWidget(
        _wrap(
          AgentGraphDetailsPanel(
            payload: testPayload,
            selected: const SelectedGraphElement.node(node),
            onClose: () => closeCalled = true,
          ),
        ),
      );

      // The close button uses Icons.close.
      await tester.tap(find.byIcon(Icons.close));
      await tester.pumpAndSettle();

      expect(closeCalled, isTrue);
    });

    testWidgets('shows token percentage relative to total graph tokens', (
      WidgetTester tester,
    ) async {
      // testPayload has 400 tokens total (100 + 300).
      // We'll select 'tool-1' which has 300 tokens (75%).
      final node = testPayload.nodes.firstWhere((n) => n.id == 'tool-1');

      await tester.pumpWidget(
        _wrap(
          AgentGraphDetailsPanel(
            payload: testPayload,
            selected: SelectedGraphElement.node(node),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Check for "75.0% of total"
      expect(find.text('75.0% of total'), findsOneWidget);
    });

    testWidgets('shows Latency and Error Rate rows when present', (
      WidgetTester tester,
    ) async {
      const node = MultiTraceNode(
        id: 'perf-node',
        type: 'agent',
        avgDurationMs: 123.4,
        hasError: true,
        errorRatePct: 5.6,
      );

      await tester.pumpWidget(
        _wrap(
          const AgentGraphDetailsPanel(
            payload: testPayload,
            selected: SelectedGraphElement.node(node),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Latency
      expect(find.text('Avg Latency'), findsOneWidget);
      expect(find.text('123.4 ms'), findsOneWidget);

      // Error Rate (shown as metric card + metric bar label)
      expect(find.text('Error Rate'), findsAtLeast(1));
      expect(find.text('5.6%'), findsOneWidget);
    });
  });
}
