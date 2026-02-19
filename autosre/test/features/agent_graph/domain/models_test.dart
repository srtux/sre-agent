import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/features/agent_graph/domain/models.dart';

void main() {
  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  Map<String, dynamic> fullNodeJson() => {
        'id': 'node-1',
        'type': 'agent',
        'description': 'Root agent',
        'total_tokens': 512,
        'has_error': true,
        'is_root': true,
        'is_leaf': false,
      };

  Map<String, dynamic> minimalNodeJson() => {
        'id': 'node-2',
        'type': 'tool',
      };

  Map<String, dynamic> fullEdgeJson() => {
        'source_id': 'a',
        'target_id': 'b',
        'source_type': 'agent',
        'target_type': 'tool',
        'call_count': 10,
        'error_count': 2,
        'error_rate_pct': 20.0,
        'sample_error': 'timeout',
        'edge_tokens': 1024,
        'avg_tokens_per_call': 102,
        'avg_duration_ms': 45.5,
        'p95_duration_ms': 120.3,
        'unique_sessions': 3,
      };

  Map<String, dynamic> minimalEdgeJson() => {
        'source_id': 'x',
        'target_id': 'y',
      };

  // ---------------------------------------------------------------------------
  // MultiTraceNode
  // ---------------------------------------------------------------------------

  group('MultiTraceNode', () {
    group('fromJson', () {
      test('parses all fields when present', () {
        final node = MultiTraceNode.fromJson(fullNodeJson());

        expect(node.id, 'node-1');
        expect(node.type, 'agent');
        expect(node.description, 'Root agent');
        expect(node.totalTokens, 512);
        expect(node.hasError, true);
        expect(node.isRoot, true);
        expect(node.isLeaf, false);
      });

      test('applies defaults for missing optional fields', () {
        final node = MultiTraceNode.fromJson(minimalNodeJson());

        expect(node.id, 'node-2');
        expect(node.type, 'tool');
        expect(node.description, isNull);
        expect(node.totalTokens, 0);
        expect(node.hasError, false);
        expect(node.isRoot, false);
        expect(node.isLeaf, false);
      });
    });

    group('toJson', () {
      test('round-trips through fromJson/toJson', () {
        final original = fullNodeJson();
        final node = MultiTraceNode.fromJson(original);
        final json = node.toJson();

        expect(json['id'], original['id']);
        expect(json['type'], original['type']);
        expect(json['description'], original['description']);
        expect(json['total_tokens'], original['total_tokens']);
        expect(json['has_error'], original['has_error']);
        expect(json['is_root'], original['is_root']);
        expect(json['is_leaf'], original['is_leaf']);
      });
    });

    group('equality', () {
      test('two identical nodes are equal', () {
        final a = MultiTraceNode.fromJson(fullNodeJson());
        final b = MultiTraceNode.fromJson(fullNodeJson());

        expect(a, equals(b));
        expect(a.hashCode, b.hashCode);
      });

      test('nodes with different ids are not equal', () {
        final a = MultiTraceNode.fromJson(fullNodeJson());
        final b = MultiTraceNode.fromJson({...fullNodeJson(), 'id': 'other'});

        expect(a, isNot(equals(b)));
      });

      test('nodes with different optional fields are not equal', () {
        final a = MultiTraceNode.fromJson(fullNodeJson());
        final b =
            MultiTraceNode.fromJson({...fullNodeJson(), 'has_error': false});

        expect(a, isNot(equals(b)));
      });
    });

    group('copyWith', () {
      test('returns a new instance with updated field', () {
        final node = MultiTraceNode.fromJson(fullNodeJson());
        final updated = node.copyWith(totalTokens: 999);

        expect(updated.totalTokens, 999);
        // Other fields remain unchanged.
        expect(updated.id, node.id);
        expect(updated.type, node.type);
        expect(updated.description, node.description);
        expect(updated.hasError, node.hasError);
        expect(updated.isRoot, node.isRoot);
        expect(updated.isLeaf, node.isLeaf);
      });

      test('can set description to null', () {
        final node = MultiTraceNode.fromJson(fullNodeJson());
        expect(node.description, isNotNull);

        final updated = node.copyWith(description: null);
        expect(updated.description, isNull);
      });

      test('can update multiple fields at once', () {
        final node = MultiTraceNode.fromJson(minimalNodeJson());
        final updated = node.copyWith(
          hasError: true,
          isRoot: true,
          totalTokens: 42,
        );

        expect(updated.hasError, true);
        expect(updated.isRoot, true);
        expect(updated.totalTokens, 42);
      });
    });
  });

  // ---------------------------------------------------------------------------
  // MultiTraceEdge
  // ---------------------------------------------------------------------------

  group('MultiTraceEdge', () {
    group('fromJson', () {
      test('parses all fields when present', () {
        final edge = MultiTraceEdge.fromJson(fullEdgeJson());

        expect(edge.sourceId, 'a');
        expect(edge.targetId, 'b');
        expect(edge.sourceType, 'agent');
        expect(edge.targetType, 'tool');
        expect(edge.callCount, 10);
        expect(edge.errorCount, 2);
        expect(edge.errorRatePct, 20.0);
        expect(edge.sampleError, 'timeout');
        expect(edge.edgeTokens, 1024);
        expect(edge.avgTokensPerCall, 102);
        expect(edge.avgDurationMs, 45.5);
        expect(edge.p95DurationMs, 120.3);
        expect(edge.uniqueSessions, 3);
      });

      test('applies defaults for missing optional fields', () {
        final edge = MultiTraceEdge.fromJson(minimalEdgeJson());

        expect(edge.sourceId, 'x');
        expect(edge.targetId, 'y');
        expect(edge.sourceType, '');
        expect(edge.targetType, '');
        expect(edge.callCount, 0);
        expect(edge.errorCount, 0);
        expect(edge.errorRatePct, 0.0);
        expect(edge.sampleError, isNull);
        expect(edge.edgeTokens, 0);
        expect(edge.avgTokensPerCall, 0);
        expect(edge.avgDurationMs, 0.0);
        expect(edge.p95DurationMs, 0.0);
        expect(edge.uniqueSessions, 0);
      });
    });

    group('toJson', () {
      test('round-trips through fromJson/toJson', () {
        final original = fullEdgeJson();
        final edge = MultiTraceEdge.fromJson(original);
        final json = edge.toJson();

        expect(json['source_id'], original['source_id']);
        expect(json['target_id'], original['target_id']);
        expect(json['source_type'], original['source_type']);
        expect(json['target_type'], original['target_type']);
        expect(json['call_count'], original['call_count']);
        expect(json['error_count'], original['error_count']);
        expect(json['error_rate_pct'], original['error_rate_pct']);
        expect(json['sample_error'], original['sample_error']);
        expect(json['edge_tokens'], original['edge_tokens']);
        expect(json['avg_tokens_per_call'], original['avg_tokens_per_call']);
        expect(json['avg_duration_ms'], original['avg_duration_ms']);
        expect(json['p95_duration_ms'], original['p95_duration_ms']);
        expect(json['unique_sessions'], original['unique_sessions']);
      });
    });

    group('equality', () {
      test('two identical edges are equal', () {
        final a = MultiTraceEdge.fromJson(fullEdgeJson());
        final b = MultiTraceEdge.fromJson(fullEdgeJson());

        expect(a, equals(b));
        expect(a.hashCode, b.hashCode);
      });

      test('edges with different source are not equal', () {
        final a = MultiTraceEdge.fromJson(fullEdgeJson());
        final b =
            MultiTraceEdge.fromJson({...fullEdgeJson(), 'source_id': 'z'});

        expect(a, isNot(equals(b)));
      });

      test('edges with different metrics are not equal', () {
        final a = MultiTraceEdge.fromJson(fullEdgeJson());
        final b =
            MultiTraceEdge.fromJson({...fullEdgeJson(), 'call_count': 999});

        expect(a, isNot(equals(b)));
      });
    });

    group('copyWith', () {
      test('returns a new instance with updated field', () {
        final edge = MultiTraceEdge.fromJson(fullEdgeJson());
        final updated = edge.copyWith(callCount: 42);

        expect(updated.callCount, 42);
        expect(updated.sourceId, edge.sourceId);
        expect(updated.targetId, edge.targetId);
      });
    });
  });

  // ---------------------------------------------------------------------------
  // MultiTraceGraphPayload
  // ---------------------------------------------------------------------------

  group('MultiTraceGraphPayload', () {
    group('fromJson', () {
      test('parses payload with both nodes and edges', () {
        final payload = MultiTraceGraphPayload.fromJson({
          'nodes': [fullNodeJson(), minimalNodeJson()],
          'edges': [fullEdgeJson()],
        });

        expect(payload.nodes, hasLength(2));
        expect(payload.edges, hasLength(1));
        expect(payload.nodes.first.id, 'node-1');
        expect(payload.nodes.last.id, 'node-2');
        expect(payload.edges.first.sourceId, 'a');
      });

      test('parses payload with empty lists', () {
        final payload = MultiTraceGraphPayload.fromJson({
          'nodes': <Map<String, dynamic>>[],
          'edges': <Map<String, dynamic>>[],
        });

        expect(payload.nodes, isEmpty);
        expect(payload.edges, isEmpty);
      });

      test('applies defaults when nodes and edges keys are missing', () {
        final payload = MultiTraceGraphPayload.fromJson({});

        expect(payload.nodes, isEmpty);
        expect(payload.edges, isEmpty);
      });
    });

    group('default constructor', () {
      test('has empty lists by default', () {
        const payload = MultiTraceGraphPayload();

        expect(payload.nodes, isEmpty);
        expect(payload.edges, isEmpty);
      });
    });

    group('toJson', () {
      test('round-trips through fromJson/toJson', () {
        final original = {
          'nodes': [fullNodeJson()],
          'edges': [fullEdgeJson()],
        };
        final payload = MultiTraceGraphPayload.fromJson(original);
        final json = payload.toJson();

        expect((json['nodes'] as List).length, 1);
        expect((json['edges'] as List).length, 1);
      });
    });

    group('equality', () {
      test('two identical payloads are equal', () {
        final json = {
          'nodes': [fullNodeJson()],
          'edges': [fullEdgeJson()],
        };
        final a = MultiTraceGraphPayload.fromJson(json);
        final b = MultiTraceGraphPayload.fromJson(json);

        expect(a, equals(b));
        expect(a.hashCode, b.hashCode);
      });

      test('payloads with different nodes are not equal', () {
        final a = MultiTraceGraphPayload.fromJson({
          'nodes': [fullNodeJson()],
          'edges': <Map<String, dynamic>>[],
        });
        final b = MultiTraceGraphPayload.fromJson({
          'nodes': [minimalNodeJson()],
          'edges': <Map<String, dynamic>>[],
        });

        expect(a, isNot(equals(b)));
      });
    });
  });

  // ---------------------------------------------------------------------------
  // SelectedGraphElement
  // ---------------------------------------------------------------------------

  group('SelectedGraphElement', () {
    final testNode = MultiTraceNode.fromJson(fullNodeJson());
    final testEdge = MultiTraceEdge.fromJson(fullEdgeJson());

    test('.node() constructor creates SelectedNode', () {
      final element = SelectedGraphElement.node(testNode);

      expect(element, isA<SelectedNode>());
      expect((element as SelectedNode).node, testNode);
    });

    test('.edge() constructor creates SelectedEdge', () {
      final element = SelectedGraphElement.edge(testEdge);

      expect(element, isA<SelectedEdge>());
      expect((element as SelectedEdge).edge, testEdge);
    });

    test('pattern matching works with switch/when on SelectedNode', () {
      final element = SelectedGraphElement.node(testNode);
      final result = switch (element) {
        SelectedNode(:final node) => 'node:${node.id}',
        SelectedEdge(:final edge) => 'edge:${edge.sourceId}',
      };

      expect(result, 'node:node-1');
    });

    test('pattern matching works with switch/when on SelectedEdge', () {
      final element = SelectedGraphElement.edge(testEdge);
      final result = switch (element) {
        SelectedNode(:final node) => 'node:${node.id}',
        SelectedEdge(:final edge) => 'edge:${edge.sourceId}',
      };

      expect(result, 'edge:a');
    });

    test('two SelectedNode with the same node are equal', () {
      final a = SelectedGraphElement.node(testNode);
      final b = SelectedGraphElement.node(testNode);

      expect(a, equals(b));
      expect(a.hashCode, b.hashCode);
    });

    test('SelectedNode and SelectedEdge are not equal', () {
      final nodeElement = SelectedGraphElement.node(testNode);
      final edgeElement = SelectedGraphElement.edge(testEdge);

      expect(nodeElement, isNot(equals(edgeElement)));
    });
  });
}
