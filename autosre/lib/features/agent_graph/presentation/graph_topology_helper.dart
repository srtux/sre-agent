import '../domain/models.dart';

/// Result of [GraphTopologyHelper.getVisibleGraph].
class VisibleGraph {
  final List<MultiTraceNode> nodes;
  final List<MultiTraceEdge> dagEdges;
  final List<MultiTraceEdge> backEdges;

  const VisibleGraph({
    required this.nodes,
    required this.dagEdges,
    required this.backEdges,
  });
}

/// Analyses graph topology using iterative DFS with three-set coloring to
/// detect true back-edges (cycles) and extract a DAG.
class GraphTopologyHelper {
  /// (sourceId, targetId) pairs identified as back-edges.
  final Set<(String, String)> backEdgeKeys;

  /// Edges with back-edges removed.
  final List<MultiTraceEdge> dagEdges;

  /// DFS discovery depth for each node.
  final Map<String, int> nodeDepths;

  /// All nodes in the payload, indexed by id.
  final Map<String, MultiTraceNode> _nodeMap;

  /// Adjacency list from payload edges (all edges, including back-edges).
  final Map<String, List<MultiTraceEdge>> _adjAll;

  /// Adjacency list from DAG edges only.
  final Map<String, List<MultiTraceEdge>> _adjDag;

  /// Root node ids (DFS start points).
  final List<String> _rootIds;

  GraphTopologyHelper._({
    required this.backEdgeKeys,
    required this.dagEdges,
    required this.nodeDepths,
    required Map<String, MultiTraceNode> nodeMap,
    required Map<String, List<MultiTraceEdge>> adjAll,
    required Map<String, List<MultiTraceEdge>> adjDag,
    required List<String> rootIds,
  })  : _nodeMap = nodeMap,
        _adjAll = adjAll,
        _adjDag = adjDag,
        _rootIds = rootIds;

  /// Analyse a [MultiTraceGraphPayload] and return a [GraphTopologyHelper]
  /// with back-edge detection results.
  factory GraphTopologyHelper.analyze(MultiTraceGraphPayload payload) {
    // Build node map and adjacency list.
    final nodeMap = <String, MultiTraceNode>{};
    for (final n in payload.nodes) {
      nodeMap[n.id] = n;
    }

    final adjAll = <String, List<MultiTraceEdge>>{};
    final inDegree = <String, int>{};
    for (final e in payload.edges) {
      adjAll.putIfAbsent(e.sourceId, () => []).add(e);
      inDegree[e.targetId] = (inDegree[e.targetId] ?? 0) + 1;
    }

    // Determine root nodes:
    // 1. Nodes with isUserEntryPoint == true
    // 2. Nodes with isRoot == true
    // 3. Nodes with zero in-degree
    final rootIds = <String>[];
    final userEntryPoints = payload.nodes
        .where((n) => n.isUserEntryPoint)
        .map((n) => n.id)
        .toList();
    if (userEntryPoints.isNotEmpty) {
      rootIds.addAll(userEntryPoints);
    } else {
      final roots = payload.nodes
          .where((n) => n.isRoot)
          .map((n) => n.id)
          .toList();
      if (roots.isNotEmpty) {
        rootIds.addAll(roots);
      } else {
        // Fall back to zero in-degree nodes.
        for (final n in payload.nodes) {
          if (!inDegree.containsKey(n.id) || inDegree[n.id] == 0) {
            rootIds.add(n.id);
          }
        }
      }
    }

    // If still no roots (pure cycle), pick the node with highest out-degree.
    if (rootIds.isEmpty && payload.nodes.isNotEmpty) {
      final outDegree = <String, int>{};
      for (final e in payload.edges) {
        outDegree[e.sourceId] = (outDegree[e.sourceId] ?? 0) + 1;
      }
      var bestId = payload.nodes.first.id;
      var bestOut = outDegree[bestId] ?? 0;
      for (final n in payload.nodes) {
        final out = outDegree[n.id] ?? 0;
        if (out > bestOut) {
          bestOut = out;
          bestId = n.id;
        }
      }
      rootIds.add(bestId);
    }

    // --- Iterative DFS with three-set coloring ---
    // white = not yet visited, gray = in recursion stack, black = fully explored.
    const white = 0;
    const gray = 1;
    const black = 2;

    final color = <String, int>{};
    for (final n in payload.nodes) {
      color[n.id] = white;
    }

    final backEdgeKeys = <(String, String)>{};
    final nodeDepths = <String, int>{};

    // Stack entries: (nodeId, edgeIndex, depth).
    // edgeIndex tracks which child edge we process next.
    for (final rootId in rootIds) {
      if (color[rootId] != white) continue;

      final stack = <(String, int, int)>[];
      stack.add((rootId, 0, 0));
      color[rootId] = gray;
      nodeDepths[rootId] = 0;

      while (stack.isNotEmpty) {
        final (nodeId, edgeIdx, depth) = stack.last;
        final children = adjAll[nodeId] ?? const [];

        if (edgeIdx < children.length) {
          // Advance edge index for current stack frame.
          stack[stack.length - 1] = (nodeId, edgeIdx + 1, depth);

          final edge = children[edgeIdx];
          final childId = edge.targetId;
          final childColor = color[childId] ?? white;

          if (childColor == gray) {
            // Back-edge: child is on the current recursion stack.
            backEdgeKeys.add((edge.sourceId, edge.targetId));
          } else if (childColor == white) {
            // Tree edge: descend.
            color[childId] = gray;
            nodeDepths[childId] = depth + 1;
            stack.add((childId, 0, depth + 1));
          }
          // If black, it's a cross/forward edge — ignore.
        } else {
          // All children processed — mark black.
          color[nodeId] = black;
          stack.removeLast();
        }
      }
    }

    // Handle nodes not reachable from any root (disconnected components).
    for (final n in payload.nodes) {
      if (color[n.id] == white) {
        nodeDepths[n.id] = 0;
        // Run DFS from this node too.
        final stack = <(String, int, int)>[];
        stack.add((n.id, 0, 0));
        color[n.id] = gray;

        while (stack.isNotEmpty) {
          final (nodeId, edgeIdx, depth) = stack.last;
          final children = adjAll[nodeId] ?? const [];

          if (edgeIdx < children.length) {
            stack[stack.length - 1] = (nodeId, edgeIdx + 1, depth);

            final edge = children[edgeIdx];
            final childId = edge.targetId;
            final childColor = color[childId] ?? white;

            if (childColor == gray) {
              backEdgeKeys.add((edge.sourceId, edge.targetId));
            } else if (childColor == white) {
              color[childId] = gray;
              nodeDepths[childId] = depth + 1;
              stack.add((childId, 0, depth + 1));
            }
          } else {
            color[nodeId] = black;
            stack.removeLast();
          }
        }
      }
    }

    // Build DAG edges (all edges minus back-edges).
    final dagEdges = payload.edges
        .where((e) => !backEdgeKeys.contains((e.sourceId, e.targetId)))
        .toList();

    // Build DAG adjacency list.
    final adjDag = <String, List<MultiTraceEdge>>{};
    for (final e in dagEdges) {
      adjDag.putIfAbsent(e.sourceId, () => []).add(e);
    }

    return GraphTopologyHelper._(
      backEdgeKeys: backEdgeKeys,
      dagEdges: dagEdges,
      nodeDepths: nodeDepths,
      nodeMap: nodeMap,
      adjAll: adjAll,
      adjDag: adjDag,
      rootIds: rootIds,
    );
  }

  /// Returns the visible sub-graph given the current set of expanded node IDs.
  ///
  /// Traverses from roots through DAG edges only. If a node is NOT in
  /// [expandedNodeIds], the node itself is included but its children are not
  /// traversed. Back-edges are included only if both endpoints are visible.
  VisibleGraph getVisibleGraph(Set<String> expandedNodeIds) {
    final visibleIds = <String>{};
    final visibleDagEdges = <MultiTraceEdge>[];

    // BFS from roots through DAG edges.
    final queue = <String>[..._rootIds];
    final visited = <String>{..._rootIds};
    visibleIds.addAll(_rootIds);

    while (queue.isNotEmpty) {
      final nodeId = queue.removeAt(0);

      // Only traverse children if node is expanded.
      if (!expandedNodeIds.contains(nodeId)) continue;

      final edges = _adjDag[nodeId] ?? const [];
      for (final edge in edges) {
        visibleDagEdges.add(edge);
        if (visited.add(edge.targetId)) {
          visibleIds.add(edge.targetId);
          queue.add(edge.targetId);
        }
      }
    }

    // Collect visible nodes in order.
    final visibleNodes = <MultiTraceNode>[];
    for (final id in visibleIds) {
      final node = _nodeMap[id];
      if (node != null) {
        visibleNodes.add(node);
      }
    }

    // Include back-edges where both endpoints are visible.
    final visibleBackEdges = <MultiTraceEdge>[];
    for (final key in backEdgeKeys) {
      if (visibleIds.contains(key.$1) && visibleIds.contains(key.$2)) {
        // Find the original edge.
        final edges = _adjAll[key.$1] ?? const [];
        for (final e in edges) {
          if (e.targetId == key.$2) {
            visibleBackEdges.add(e);
            break;
          }
        }
      }
    }

    return VisibleGraph(
      nodes: visibleNodes,
      dagEdges: visibleDagEdges,
      backEdges: visibleBackEdges,
    );
  }

  /// Returns the set of root node IDs.
  List<String> get rootIds => List.unmodifiable(_rootIds);

  /// Build a child→parent map from the given DAG edges.
  /// If a child has multiple parents, the first encountered wins.
  static Map<String, String> buildChildToParent(List<MultiTraceEdge> dagEdges) {
    final map = <String, String>{};
    for (final e in dagEdges) {
      map.putIfAbsent(e.targetId, () => e.sourceId);
    }
    return map;
  }
}
