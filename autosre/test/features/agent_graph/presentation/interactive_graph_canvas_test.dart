import 'package:autosre/features/agent_graph/domain/models.dart';
import 'package:autosre/features/agent_graph/presentation/interactive_graph_canvas.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';


const _node1 = MultiTraceNode(
  id: 'agent_1',
  type: 'Agent',
  label: 'agent_1',
  executionCount: 10,
  avgDurationMs: 50.0,
  totalTokens: 1000,
  errorCount: 0,
  uniqueSessions: 5,
  isRoot: true,
  isLeaf: false,
);

const _node2 = MultiTraceNode(
  id: 'llm_1',
  type: 'LLM',
  label: 'tool_1',
  executionCount: 5,
  avgDurationMs: 200.0,
  totalTokens: 0,
  errorCount: 1,
  uniqueSessions: 3,
  isRoot: false,
  isLeaf: true,
);

const _edge1 = MultiTraceEdge(
  sourceId: 'agent_1',
  targetId: 'llm_1',
  callCount: 5,
  errorCount: 1,
  edgeTokens: 0,
  avgDurationMs: 200.0,
  uniqueSessions: 3,
  errorRatePct: 20.0,
);

void main() {
  group('InteractiveGraphCanvas', () {
    testWidgets('renders nodes in standard mode', skip: true, (tester) async {
       tester.view.physicalSize = const Size(1600, 900);
       tester.view.devicePixelRatio = 1.0;
       addTearDown(() => tester.view.resetPhysicalSize());

      const payload = MultiTraceGraphPayload(
         nodes: [_node1, _node2],
         edges: [_edge1],
       );

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(body: InteractiveGraphCanvas(payload: payload)),
        ),
      );
      // Wait enough for auto-fit timer (500ms)
      await tester.pump(const Duration(milliseconds: 600));
       await tester.pumpAndSettle();

      expect(find.text('agent_1'), findsOneWidget);
      expect(find.text('1.0K toks'), findsOneWidget);
    });

    testWidgets('renders empty graph', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: InteractiveGraphCanvas(
              payload: MultiTraceGraphPayload(nodes: [], edges: []),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('No Data'), findsOneWidget);
    });
  });
}
