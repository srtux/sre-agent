import 'package:autosre/features/agent_graph/domain/models.dart';
import 'package:autosre/features/agent_graph/presentation/agent_graph_details_panel.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _wrap(Widget child) {
  return MaterialApp(home: Scaffold(body: child));
}

void main() {
  group('AgentGraphDetailsPanel', () {
    testWidgets('renders nothing when selected is null', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(
        _wrap(const AgentGraphDetailsPanel(selected: null)),
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
            selected: SelectedGraphElement.node(node),
          ),
        ),
      );

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
            selected: SelectedGraphElement.node(node),
          ),
        ),
      );

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
            selected: SelectedGraphElement.node(node),
          ),
        ),
      );

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
            selected: SelectedGraphElement.node(node),
          ),
        ),
      );

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
              selected: SelectedGraphElement.edge(edge),
            ),
          ),
        );

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
            selected: SelectedGraphElement.edge(edge),
          ),
        ),
      );

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
  });
}
