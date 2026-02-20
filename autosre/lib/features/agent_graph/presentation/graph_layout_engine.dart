import 'dart:ui';

import 'package:graphview/GraphView.dart' as gv;

import '../domain/models.dart';

/// Stateless wrapper around `graphview`'s SugiyamaAlgorithm that computes
/// node positions from a visible sub-graph.
///
/// Only DAG edges are fed to the algorithm — back-edges are excluded to avoid
/// confusing the layered layout.
class GraphLayoutEngine {
  /// Compute positions for [nodes] using the Sugiyama hierarchical layout.
  ///
  /// Returns a map of nodeId → center [Offset]. Positions are normalized
  /// so the graph center is at (0, 0).
  static Map<String, Offset> computePositions({
    required List<MultiTraceNode> nodes,
    required List<MultiTraceEdge> dagEdges,
    double nodeWidth = 200,
    double nodeHeight = 100,
  }) {
    if (nodes.isEmpty) return {};

    final graph = gv.Graph()..isTree = false;
    final gvNodes = <String, gv.Node>{};
    final uniqueIds = <String>{};

    for (final n in nodes) {
      if (!uniqueIds.add(n.id)) continue;
      final node = gv.Node.Id(n.id);

      // Size estimates based on node type widgets.
      final type = n.type.toLowerCase();
      if (type == 'agent' || type == 'sub_agent') {
        node.size = const Size(260, 150);
      } else if (type == 'llm') {
        node.size = const Size(240, 100);
      } else {
        node.size = Size(nodeWidth, nodeHeight);
      }

      gvNodes[n.id] = node;
      graph.addNode(node);
    }

    for (final e in dagEdges) {
      final src = gvNodes[e.sourceId];
      final tgt = gvNodes[e.targetId];
      if (src != null && tgt != null) {
        graph.addEdge(src, tgt);
      }
    }

    // Run Sugiyama layout.
    final config = gv.SugiyamaConfiguration()
      ..orientation = gv.SugiyamaConfiguration.ORIENTATION_LEFT_RIGHT
      ..levelSeparation = 120
      ..nodeSeparation = 60;

    final algorithm = gv.SugiyamaAlgorithm(config);
    algorithm.run(graph, 100, 100);

    // Compute bounding box for centering.
    var minX = double.infinity;
    var minY = double.infinity;
    var maxX = double.negativeInfinity;
    var maxY = double.negativeInfinity;

    for (final gvNode in gvNodes.values) {
      if (gvNode.x < minX) minX = gvNode.x;
      if (gvNode.y < minY) minY = gvNode.y;
      if (gvNode.x > maxX) maxX = gvNode.x;
      if (gvNode.y > maxY) maxY = gvNode.y;
    }

    final centerX = (minX + maxX) / 2;
    final centerY = (minY + maxY) / 2;

    // Build position map centered at origin.
    final positions = <String, Offset>{};
    for (final n in nodes) {
      final gvNode = gvNodes[n.id];
      if (gvNode != null) {
        positions[n.id] = Offset(gvNode.x - centerX, gvNode.y - centerY);
      }
    }

    return positions;
  }
}
