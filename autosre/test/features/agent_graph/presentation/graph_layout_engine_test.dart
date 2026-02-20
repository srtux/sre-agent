import 'package:autosre/features/agent_graph/domain/models.dart';
import 'package:autosre/features/agent_graph/presentation/graph_layout_engine.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('GraphLayoutEngine', () {
    test('empty nodes returns empty map', () {
      final positions = GraphLayoutEngine.computePositions(
        nodes: [],
        dagEdges: [],
      );
      expect(positions, isEmpty);
    });

    test('single node returns position at origin', () {
      const nodes = [
        MultiTraceNode(id: 'A', type: 'Agent'),
      ];

      final positions = GraphLayoutEngine.computePositions(
        nodes: nodes,
        dagEdges: [],
      );

      expect(positions.length, 1);
      expect(positions.containsKey('A'), isTrue);
      // Single node centered at origin.
      expect(positions['A']!.dx, 0.0);
      expect(positions['A']!.dy, 0.0);
    });

    test('position map contains all nodes', () {
      const nodes = [
        MultiTraceNode(id: 'A', type: 'Agent', isRoot: true),
        MultiTraceNode(id: 'B', type: 'Tool'),
        MultiTraceNode(id: 'C', type: 'LLM'),
      ];
      const edges = [
        MultiTraceEdge(sourceId: 'A', targetId: 'B'),
        MultiTraceEdge(sourceId: 'A', targetId: 'C'),
      ];

      final positions = GraphLayoutEngine.computePositions(
        nodes: nodes,
        dagEdges: edges,
      );

      expect(positions.length, 3);
      expect(positions.containsKey('A'), isTrue);
      expect(positions.containsKey('B'), isTrue);
      expect(positions.containsKey('C'), isTrue);
    });

    test('nodes at different layers have different positions', () {
      const nodes = [
        MultiTraceNode(id: 'A', type: 'Agent', isRoot: true),
        MultiTraceNode(id: 'B', type: 'Tool'),
      ];
      const edges = [
        MultiTraceEdge(sourceId: 'A', targetId: 'B'),
      ];

      final positions = GraphLayoutEngine.computePositions(
        nodes: nodes,
        dagEdges: edges,
      );

      expect(positions['A'], isNot(equals(positions['B'])));
    });

    test('edges referencing non-existent nodes are skipped', () {
      const nodes = [
        MultiTraceNode(id: 'A', type: 'Agent'),
        MultiTraceNode(id: 'B', type: 'Tool'),
      ];
      const edges = [
        MultiTraceEdge(sourceId: 'A', targetId: 'B'),
        MultiTraceEdge(sourceId: 'A', targetId: 'Z'), // Z not in nodes
        MultiTraceEdge(sourceId: 'X', targetId: 'B'), // X not in nodes
      ];

      final positions = GraphLayoutEngine.computePositions(
        nodes: nodes,
        dagEdges: edges,
      );

      // Should not crash; only A and B have positions.
      expect(positions.length, 2);
      expect(positions.containsKey('A'), isTrue);
      expect(positions.containsKey('B'), isTrue);
    });

    test('agent and llm nodes get different sizes', () {
      const nodes = [
        MultiTraceNode(id: 'A', type: 'Agent', isRoot: true),
        MultiTraceNode(id: 'B', type: 'LLM'),
        MultiTraceNode(id: 'C', type: 'Tool'),
      ];
      const edges = [
        MultiTraceEdge(sourceId: 'A', targetId: 'B'),
        MultiTraceEdge(sourceId: 'A', targetId: 'C'),
      ];

      final positions = GraphLayoutEngine.computePositions(
        nodes: nodes,
        dagEdges: edges,
      );

      // All three nodes should have positions.
      expect(positions.length, 3);
      // B and C should be at different positions since they're children of A
      // with different sizes.
      expect(positions['B'], isNot(equals(positions['C'])));
    });

    test('duplicate node IDs handled gracefully', () {
      const nodes = [
        MultiTraceNode(id: 'A', type: 'Agent'),
        MultiTraceNode(id: 'A', type: 'Agent'), // duplicate
      ];

      final positions = GraphLayoutEngine.computePositions(
        nodes: nodes,
        dagEdges: [],
      );

      // Should not crash, and should produce position for 'A'.
      expect(positions.containsKey('A'), isTrue);
    });
  });
}
