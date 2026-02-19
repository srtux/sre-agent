import 'package:autosre/features/agent_graph/domain/models.dart';
import 'package:autosre/features/agent_graph/presentation/multi_trace_graph_canvas.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Widget _wrap(Widget child) {
  return MaterialApp(
    home: Scaffold(body: child),
  );
}

const _singleNode = MultiTraceNode(
  id: 'root_agent',
  type: 'agent',
  isRoot: true,
  totalTokens: 5000,
);

const _secondNode = MultiTraceNode(
  id: 'trace_tool',
  type: 'tool',
  totalTokens: 1200,
);

const _thirdNode = MultiTraceNode(
  id: 'gemini_flash',
  type: 'llm',
  totalTokens: 8000,
);

const _edge = MultiTraceEdge(
  sourceId: 'root_agent',
  targetId: 'trace_tool',
  callCount: 10,
  uniqueSessions: 3,
);

const _edge2 = MultiTraceEdge(
  sourceId: 'root_agent',
  targetId: 'gemini_flash',
  callCount: 5,
  uniqueSessions: 2,
);

void main() {
  group('MultiTraceGraphCanvas', () {
    testWidgets('shows empty state text when payload has no nodes', (
      WidgetTester tester,
    ) async {
      const emptyPayload = MultiTraceGraphPayload();

      await tester.pumpWidget(
        _wrap(
          const MultiTraceGraphCanvas(payload: emptyPayload),
        ),
      );

      expect(
        find.text('No graph data.\nRun a query to visualize agent traces.'),
        findsOneWidget,
      );
      expect(
        find.byIcon(Icons.account_tree_outlined),
        findsOneWidget,
      );
    });

    testWidgets('shows header text when nodes are present', (
      WidgetTester tester,
    ) async {
      // Use a wide surface to avoid toolbar overflow.
      tester.view.physicalSize = const Size(1600, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      const payload = MultiTraceGraphPayload(
        nodes: [_singleNode, _secondNode],
        edges: [_edge],
      );

      await tester.pumpWidget(
        _wrap(const MultiTraceGraphCanvas(payload: payload)),
      );
      await tester.pumpAndSettle();

      expect(find.text('Multi-Trace Agent Graph'), findsOneWidget);
    });

    testWidgets('shows node count and edge count in the toolbar', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1600, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      const payload = MultiTraceGraphPayload(
        nodes: [_singleNode, _secondNode, _thirdNode],
        edges: [_edge, _edge2],
      );

      await tester.pumpWidget(
        _wrap(const MultiTraceGraphCanvas(payload: payload)),
      );
      await tester.pumpAndSettle();

      expect(find.text('3 nodes \u00b7 2 edges'), findsOneWidget);
    });

    testWidgets('shows legend items (Agent, Tool, LLM)', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1600, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      const payload = MultiTraceGraphPayload(
        nodes: [_singleNode, _secondNode],
        edges: [_edge],
      );

      await tester.pumpWidget(
        _wrap(const MultiTraceGraphCanvas(payload: payload)),
      );
      await tester.pumpAndSettle();

      expect(find.text('Agent'), findsOneWidget);
      expect(find.text('Tool'), findsOneWidget);
      expect(find.text('LLM'), findsOneWidget);
    });

    testWidgets('calls onNodeSelected when a node is tapped', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1600, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      MultiTraceNode? selectedNode;

      const payload = MultiTraceGraphPayload(
        nodes: [_singleNode, _secondNode],
        edges: [_edge],
      );

      await tester.pumpWidget(
        _wrap(
          MultiTraceGraphCanvas(
            payload: payload,
            onNodeSelected: (node) => selectedNode = node,
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Tap the node labeled 'root_agent'.
      await tester.tap(find.text('root_agent'));
      await tester.pumpAndSettle();

      expect(selectedNode, isNotNull);
      expect(selectedNode!.id, 'root_agent');
    });

    testWidgets('renders both layout toggle buttons', (
      WidgetTester tester,
    ) async {
      tester.view.physicalSize = const Size(1600, 900);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(() => tester.view.resetPhysicalSize());

      const payload = MultiTraceGraphPayload(
        nodes: [_singleNode, _secondNode],
        edges: [_edge],
      );

      await tester.pumpWidget(
        _wrap(const MultiTraceGraphCanvas(payload: payload)),
      );
      await tester.pumpAndSettle();

      expect(find.text('Hierarchical'), findsOneWidget);
      expect(find.text('Force'), findsOneWidget);
    });
  });
}
