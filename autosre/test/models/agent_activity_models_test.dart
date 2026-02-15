import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/models/adk_schema.dart';

void main() {
  // ===========================================================================
  // AgentNode
  // ===========================================================================
  group('AgentNode', () {
    test('fromJson parses valid data', () {
      final node = AgentNode.fromJson({
        'id': 'n1',
        'name': 'SRE Coordinator',
        'type': 'coordinator',
        'status': 'active',
        'connections': ['n2', 'n3'],
        'metadata': {'role': 'root'},
      });
      expect(node.id, 'n1');
      expect(node.name, 'SRE Coordinator');
      expect(node.type, 'coordinator');
      expect(node.status, 'active');
      expect(node.connections, ['n2', 'n3']);
      expect(node.metadata?['role'], 'root');
    });

    test('fromJson provides defaults', () {
      final node = AgentNode.fromJson(const {});
      expect(node.id, '');
      expect(node.name, '');
      expect(node.type, 'tool');
      expect(node.status, 'idle');
      expect(node.connections, isEmpty);
      expect(node.metadata, isNull);
    });

    test('fromJson handles null connections', () {
      final node = AgentNode.fromJson({
        'id': 'n1', 'name': 'test', 'type': 'tool', 'status': 'idle',
        'connections': null,
      });
      expect(node.connections, isEmpty);
    });

    test('fromJson handles empty connections', () {
      final node = AgentNode.fromJson({
        'id': 'n1', 'name': 'test', 'type': 'tool', 'status': 'idle',
        'connections': [],
      });
      expect(node.connections, isEmpty);
    });
  });

  // ===========================================================================
  // AgentActivityData
  // ===========================================================================
  group('AgentActivityData', () {
    test('fromJson parses valid data', () {
      final data = AgentActivityData.fromJson({
        'nodes': [
          {
            'id': 'n1', 'name': 'Coordinator', 'type': 'coordinator',
            'status': 'active', 'connections': ['n2'],
          },
          {
            'id': 'n2', 'name': 'Trace Tool', 'type': 'tool',
            'status': 'completed',
          },
        ],
        'current_phase': 'Investigating',
        'active_node_id': 'n1',
        'completed_steps': ['fetch_trace', 'analyze_metrics'],
        'message': 'Analyzing trace data...',
      });
      expect(data.nodes.length, 2);
      expect(data.currentPhase, 'Investigating');
      expect(data.activeNodeId, 'n1');
      expect(data.completedSteps, ['fetch_trace', 'analyze_metrics']);
      expect(data.message, 'Analyzing trace data...');
    });

    test('fromJson provides defaults', () {
      final data = AgentActivityData.fromJson(const {});
      expect(data.nodes, isEmpty);
      expect(data.currentPhase, 'Analyzing');
      expect(data.activeNodeId, isNull);
      expect(data.completedSteps, isEmpty);
      expect(data.message, isNull);
    });

    test('fromJson handles null nodes', () {
      final data = AgentActivityData.fromJson({
        'nodes': null,
        'current_phase': 'Idle',
      });
      expect(data.nodes, isEmpty);
      expect(data.currentPhase, 'Idle');
    });

    test('fromJson handles empty data gracefully', () {
      final data = AgentActivityData.fromJson({
        'nodes': [],
        'current_phase': null,
        'active_node_id': null,
        'completed_steps': null,
        'message': null,
      });
      expect(data.nodes, isEmpty);
      expect(data.currentPhase, 'Analyzing');
      expect(data.activeNodeId, isNull);
      expect(data.completedSteps, isEmpty);
      expect(data.message, isNull);
    });
  });

  // ===========================================================================
  // Integration: AgentNode accessible via barrel import
  // ===========================================================================
  group('Barrel import integration', () {
    test('AgentNode and AgentActivityData are accessible from adk_schema barrel', () {
      // This test validates that the barrel file properly re-exports
      // the models moved from agent_activity_canvas.dart
      final node = AgentNode(
        id: 'n1', name: 'test', type: 'tool', status: 'idle',
      );
      final data = AgentActivityData(
        nodes: [node], currentPhase: 'Testing',
      );
      expect(data.nodes.length, 1);
      expect(data.nodes[0].id, 'n1');
    });
  });
}
