import 'package:autosre/features/agent_graph/domain/models.dart';
import 'package:autosre/features/agent_graph/presentation/graph_topology_helper.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('GraphTopologyHelper', () {
    group('analyze', () {
      test('simple DAG has no back-edges', () {
        // A → B → C
        const payload = MultiTraceGraphPayload(
          nodes: [
            MultiTraceNode(id: 'A', type: 'Agent', isRoot: true),
            MultiTraceNode(id: 'B', type: 'Tool'),
            MultiTraceNode(id: 'C', type: 'Tool'),
          ],
          edges: [
            MultiTraceEdge(sourceId: 'A', targetId: 'B'),
            MultiTraceEdge(sourceId: 'B', targetId: 'C'),
          ],
        );

        final helper = GraphTopologyHelper.analyze(payload);

        expect(helper.backEdgeKeys, isEmpty);
        expect(helper.dagEdges.length, 2);
        expect(helper.nodeDepths['A'], 0);
        expect(helper.nodeDepths['B'], 1);
        expect(helper.nodeDepths['C'], 2);
      });

      test('single cycle detected as back-edge', () {
        // A → B → C → A
        const payload = MultiTraceGraphPayload(
          nodes: [
            MultiTraceNode(id: 'A', type: 'Agent', isRoot: true),
            MultiTraceNode(id: 'B', type: 'Tool'),
            MultiTraceNode(id: 'C', type: 'Tool'),
          ],
          edges: [
            MultiTraceEdge(sourceId: 'A', targetId: 'B'),
            MultiTraceEdge(sourceId: 'B', targetId: 'C'),
            MultiTraceEdge(sourceId: 'C', targetId: 'A'),
          ],
        );

        final helper = GraphTopologyHelper.analyze(payload);

        expect(helper.backEdgeKeys, contains(('C', 'A')));
        expect(helper.backEdgeKeys.length, 1);
        expect(helper.dagEdges.length, 2);
      });

      test('multi-cycle graph detects all back-edges', () {
        // A → B → A (cycle 1)
        // A → C → D → A (cycle 2)
        const payload = MultiTraceGraphPayload(
          nodes: [
            MultiTraceNode(id: 'A', type: 'Agent', isRoot: true),
            MultiTraceNode(id: 'B', type: 'Tool'),
            MultiTraceNode(id: 'C', type: 'Tool'),
            MultiTraceNode(id: 'D', type: 'Tool'),
          ],
          edges: [
            MultiTraceEdge(sourceId: 'A', targetId: 'B'),
            MultiTraceEdge(sourceId: 'B', targetId: 'A'),
            MultiTraceEdge(sourceId: 'A', targetId: 'C'),
            MultiTraceEdge(sourceId: 'C', targetId: 'D'),
            MultiTraceEdge(sourceId: 'D', targetId: 'A'),
          ],
        );

        final helper = GraphTopologyHelper.analyze(payload);

        expect(helper.backEdgeKeys, contains(('B', 'A')));
        expect(helper.backEdgeKeys, contains(('D', 'A')));
        expect(helper.backEdgeKeys.length, 2);
        expect(helper.dagEdges.length, 3);
      });

      test('diamond DAG has no back-edges', () {
        // A → B, A → C, B → D, C → D
        const payload = MultiTraceGraphPayload(
          nodes: [
            MultiTraceNode(id: 'A', type: 'Agent', isRoot: true),
            MultiTraceNode(id: 'B', type: 'Tool'),
            MultiTraceNode(id: 'C', type: 'Tool'),
            MultiTraceNode(id: 'D', type: 'Tool'),
          ],
          edges: [
            MultiTraceEdge(sourceId: 'A', targetId: 'B'),
            MultiTraceEdge(sourceId: 'A', targetId: 'C'),
            MultiTraceEdge(sourceId: 'B', targetId: 'D'),
            MultiTraceEdge(sourceId: 'C', targetId: 'D'),
          ],
        );

        final helper = GraphTopologyHelper.analyze(payload);

        expect(helper.backEdgeKeys, isEmpty);
        expect(helper.dagEdges.length, 4);
      });

      test('self-loop detected as back-edge', () {
        // A → A
        const payload = MultiTraceGraphPayload(
          nodes: [
            MultiTraceNode(id: 'A', type: 'Agent', isRoot: true),
          ],
          edges: [
            MultiTraceEdge(sourceId: 'A', targetId: 'A'),
          ],
        );

        final helper = GraphTopologyHelper.analyze(payload);

        expect(helper.backEdgeKeys, contains(('A', 'A')));
        expect(helper.dagEdges, isEmpty);
      });

      test('disconnected components all analyzed', () {
        // Component 1: A → B
        // Component 2: C → D
        const payload = MultiTraceGraphPayload(
          nodes: [
            MultiTraceNode(id: 'A', type: 'Agent', isRoot: true),
            MultiTraceNode(id: 'B', type: 'Tool'),
            MultiTraceNode(id: 'C', type: 'Agent'),
            MultiTraceNode(id: 'D', type: 'Tool'),
          ],
          edges: [
            MultiTraceEdge(sourceId: 'A', targetId: 'B'),
            MultiTraceEdge(sourceId: 'C', targetId: 'D'),
          ],
        );

        final helper = GraphTopologyHelper.analyze(payload);

        expect(helper.backEdgeKeys, isEmpty);
        expect(helper.nodeDepths.length, 4);
        expect(helper.nodeDepths['A'], 0);
        expect(helper.nodeDepths['C'], 0);
      });

      test('empty payload produces empty results', () {
        const payload = MultiTraceGraphPayload(nodes: [], edges: []);

        final helper = GraphTopologyHelper.analyze(payload);

        expect(helper.backEdgeKeys, isEmpty);
        expect(helper.dagEdges, isEmpty);
        expect(helper.nodeDepths, isEmpty);
        expect(helper.rootIds, isEmpty);
      });

      test('pure cycle with no roots picks highest out-degree node', () {
        // A → B → C → A, no isRoot flags, all have in-degree > 0.
        const payload = MultiTraceGraphPayload(
          nodes: [
            MultiTraceNode(id: 'A', type: 'Agent'),
            MultiTraceNode(id: 'B', type: 'Tool'),
            MultiTraceNode(id: 'C', type: 'Tool'),
          ],
          edges: [
            MultiTraceEdge(sourceId: 'A', targetId: 'B'),
            MultiTraceEdge(sourceId: 'B', targetId: 'C'),
            MultiTraceEdge(sourceId: 'C', targetId: 'A'),
          ],
        );

        final helper = GraphTopologyHelper.analyze(payload);

        // All nodes have out-degree 1, so first node (A) is picked as root.
        expect(helper.rootIds, isNotEmpty);
        // Should detect exactly one back-edge.
        expect(helper.backEdgeKeys.length, 1);
        expect(helper.dagEdges.length, 2);
      });

      test('forward edges are not detected as back-edges', () {
        // A → B → C, A → C (forward edge, not a back-edge)
        const payload = MultiTraceGraphPayload(
          nodes: [
            MultiTraceNode(id: 'A', type: 'Agent', isRoot: true),
            MultiTraceNode(id: 'B', type: 'Tool'),
            MultiTraceNode(id: 'C', type: 'Tool'),
          ],
          edges: [
            MultiTraceEdge(sourceId: 'A', targetId: 'B'),
            MultiTraceEdge(sourceId: 'B', targetId: 'C'),
            MultiTraceEdge(sourceId: 'A', targetId: 'C'), // forward edge
          ],
        );

        final helper = GraphTopologyHelper.analyze(payload);

        // A→C is a forward edge (C is already visited/black when A
        // processes this edge), not a back-edge.
        expect(helper.backEdgeKeys, isEmpty);
        expect(helper.dagEdges.length, 3);
      });

      test('cross edges are not detected as back-edges', () {
        // A → B, A → C, B → D, C → D
        // If DFS visits B→D first, then C→D is a cross edge (D is black).
        const payload = MultiTraceGraphPayload(
          nodes: [
            MultiTraceNode(id: 'A', type: 'Agent', isRoot: true),
            MultiTraceNode(id: 'B', type: 'Tool'),
            MultiTraceNode(id: 'C', type: 'Tool'),
            MultiTraceNode(id: 'D', type: 'Tool'),
          ],
          edges: [
            MultiTraceEdge(sourceId: 'A', targetId: 'B'),
            MultiTraceEdge(sourceId: 'A', targetId: 'C'),
            MultiTraceEdge(sourceId: 'B', targetId: 'D'),
            MultiTraceEdge(sourceId: 'C', targetId: 'D'),
          ],
        );

        final helper = GraphTopologyHelper.analyze(payload);

        expect(helper.backEdgeKeys, isEmpty);
        expect(helper.dagEdges.length, 4);
      });

      test('uses isUserEntryPoint as root priority', () {
        const payload = MultiTraceGraphPayload(
          nodes: [
            MultiTraceNode(id: 'A', type: 'Agent', isRoot: true),
            MultiTraceNode(
              id: 'U',
              type: 'User',
              isUserEntryPoint: true,
            ),
            MultiTraceNode(id: 'B', type: 'Tool'),
          ],
          edges: [
            MultiTraceEdge(sourceId: 'U', targetId: 'A'),
            MultiTraceEdge(sourceId: 'A', targetId: 'B'),
          ],
        );

        final helper = GraphTopologyHelper.analyze(payload);
        expect(helper.rootIds, contains('U'));
        expect(helper.nodeDepths['U'], 0);
      });
    });

    group('getVisibleGraph', () {
      // A → B → C, A → D
      const payload = MultiTraceGraphPayload(
        nodes: [
          MultiTraceNode(id: 'A', type: 'Agent', isRoot: true),
          MultiTraceNode(id: 'B', type: 'Agent'),
          MultiTraceNode(id: 'C', type: 'Tool'),
          MultiTraceNode(id: 'D', type: 'Tool'),
        ],
        edges: [
          MultiTraceEdge(sourceId: 'A', targetId: 'B'),
          MultiTraceEdge(sourceId: 'B', targetId: 'C'),
          MultiTraceEdge(sourceId: 'A', targetId: 'D'),
        ],
      );

      test('all expanded shows all nodes', () {
        final helper = GraphTopologyHelper.analyze(payload);
        final visible = helper.getVisibleGraph({'A', 'B'});

        expect(visible.nodes.length, 4);
        expect(visible.dagEdges.length, 3);
      });

      test('collapsing A hides B, C, D', () {
        final helper = GraphTopologyHelper.analyze(payload);
        // A is NOT expanded → its children B and D are hidden.
        final visible = helper.getVisibleGraph(<String>{});

        expect(visible.nodes.length, 1);
        expect(visible.nodes.first.id, 'A');
        expect(visible.dagEdges, isEmpty);
      });

      test('expanding A but not B shows A, B, D but not C', () {
        final helper = GraphTopologyHelper.analyze(payload);
        final visible = helper.getVisibleGraph({'A'});

        final ids = visible.nodes.map((n) => n.id).toSet();
        expect(ids, containsAll(['A', 'B', 'D']));
        expect(ids, isNot(contains('C')));
        expect(visible.dagEdges.length, 2); // A→B, A→D
      });

      test('back-edges included only when both endpoints visible', () {
        // A → B → C → A (back-edge C→A)
        const cyclicPayload = MultiTraceGraphPayload(
          nodes: [
            MultiTraceNode(id: 'A', type: 'Agent', isRoot: true),
            MultiTraceNode(id: 'B', type: 'Agent'),
            MultiTraceNode(id: 'C', type: 'Tool'),
          ],
          edges: [
            MultiTraceEdge(sourceId: 'A', targetId: 'B'),
            MultiTraceEdge(sourceId: 'B', targetId: 'C'),
            MultiTraceEdge(sourceId: 'C', targetId: 'A'),
          ],
        );

        final helper = GraphTopologyHelper.analyze(cyclicPayload);

        // All expanded: back-edge C→A should be visible.
        final allVisible = helper.getVisibleGraph({'A', 'B'});
        expect(allVisible.backEdges.length, 1);
        expect(allVisible.backEdges.first.sourceId, 'C');

        // B collapsed: C not visible, so back-edge C→A excluded.
        final partialVisible = helper.getVisibleGraph({'A'});
        expect(partialVisible.backEdges, isEmpty);
      });
    });

    test('rootIds returns unmodifiable list', () {
      const payload = MultiTraceGraphPayload(
        nodes: [
          MultiTraceNode(id: 'A', type: 'Agent', isRoot: true),
          MultiTraceNode(id: 'B', type: 'Tool'),
        ],
        edges: [
          MultiTraceEdge(sourceId: 'A', targetId: 'B'),
        ],
      );

      final helper = GraphTopologyHelper.analyze(payload);
      expect(helper.rootIds, ['A']);
      expect(
        () => helper.rootIds.add('X'),
        throwsA(isA<UnsupportedError>()),
      );
    });

    group('buildChildToParent', () {
      test('maps children to first parent', () {
        const edges = [
          MultiTraceEdge(sourceId: 'A', targetId: 'B'),
          MultiTraceEdge(sourceId: 'A', targetId: 'C'),
          MultiTraceEdge(sourceId: 'B', targetId: 'D'),
        ];

        final map = GraphTopologyHelper.buildChildToParent(edges);
        expect(map['B'], 'A');
        expect(map['C'], 'A');
        expect(map['D'], 'B');
        expect(map.containsKey('A'), isFalse);
      });
    });
  });
}
