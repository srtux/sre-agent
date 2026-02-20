import 'dart:async';

import 'package:fl_nodes/fl_nodes.dart';
import 'package:flutter/material.dart';

import 'package:graphview/GraphView.dart' as gv;
import '../../../theme/app_theme.dart';
import '../domain/models.dart';

/// A next-generation interactive graph canvas using fl_nodes.
///
/// Features:
/// - Drag-and-drop node editing
/// - Smooth bezier connections
/// - Custom node widgets
/// - Auto-layout using a custom tree layout algorithm on initial load
class InteractiveGraphCanvas extends StatefulWidget {
  final MultiTraceGraphPayload payload;
  final ValueChanged<MultiTraceNode>? onNodeSelected;
  final ValueChanged<MultiTraceEdge>? onEdgeSelected;
  final VoidCallback? onSelectionCleared;

  const InteractiveGraphCanvas({
    super.key,
    required this.payload,
    this.onNodeSelected,
    this.onEdgeSelected,
    this.onSelectionCleared,
  });

  @override
  State<InteractiveGraphCanvas> createState() => _InteractiveGraphCanvasState();
}

class _InteractiveGraphCanvasState extends State<InteractiveGraphCanvas> {
  late FlNodeEditorController _controller;
  // State for gradual disclosure
  final Set<String> _collapsedNodeIds = {};

  // Map to store the actual data associated with each node ID
  final Map<String, MultiTraceNode> _nodeDataMap = {};

  // Cache layout to avoid re-calculating on every build
  int _cachedHash = -1;

  Timer? _layoutTimer;

  @override
  void initState() {
    super.initState();
    _controller = FlNodeEditorController(
      config: const FlNodeEditorConfig(minZoom: 0.001, maxZoom: 10.0),
      style: const FlNodeEditorStyle(
        gridStyle: FlGridStyle(
          gridSpacingX: 48,
          gridSpacingY: 48,
          lineWidth: 0,
          lineColor: Colors.transparent,
          intersectionColor: Colors.transparent,
          intersectionRadius: 0,
          showGrid: false,
        ),
      ),
    );
    // Start significantly zoomed out (20x more than 1.0) for a bird's eye view
    _controller.viewportZoomNotifier.value = 0.05;
    _registerPrototypes();
    _initialCollapse();
    _processGraphData();
  }

  void _initialCollapse() {
    // Auto-collapse if graph > 25 nodes
    if (widget.payload.nodes.length > 25) {
      // Find root (node with 0 incoming edges or explicit isRoot)
      final incomingEdges = <String, int>{};
      for (var e in widget.payload.edges) {
        incomingEdges[e.targetId] = (incomingEdges[e.targetId] ?? 0) + 1;
      }

      // We want to keep depth 0 and 1 open, collapse depth 2+
      // Simple heuristic: Collapse all Agent/SubAgent nodes that are NOT the root
      // AND have children.
      // Actually, a BFS to determine depth is better.
      final roots = widget.payload.nodes.where((n) {
        return n.isRoot || !incomingEdges.containsKey(n.id);
      }).toList();

      if (roots.isEmpty && widget.payload.nodes.isNotEmpty) {
        // Cycle or just complex, pick first
        roots.add(widget.payload.nodes.first);
      }

      // BFS to assign depth
      final depthMap = <String, int>{};
      final queue = <String>[];
      for (var r in roots) {
        depthMap[r.id] = 0;
        queue.add(r.id);
      }

      final adj = <String, List<String>>{};
      for (var e in widget.payload.edges) {
        adj.putIfAbsent(e.sourceId, () => []).add(e.targetId);
      }

      while (queue.isNotEmpty) {
        final u = queue.removeAt(0);
        final d = depthMap[u]!;
        final children = adj[u] ?? [];
        for (var v in children) {
          if (!depthMap.containsKey(v)) {
            depthMap[v] = d + 1;
            queue.add(v);
          }
        }
      }

      // Collapse agents at depth >= 1 (so their children at depth >= 2 are hidden)
      for (var n in widget.payload.nodes) {
        final d = depthMap[n.id] ?? 0;
        if (d >= 1 && _isAgent(n)) {
          _collapsedNodeIds.add(n.id);
        }
      }
    }
  }

  bool _isAgent(MultiTraceNode node) {
    final t = node.type.toLowerCase();
    return t == 'agent' || t == 'sub_agent';
  }

  // ignore: unused_element
  void _toggleCollapse(String nodeId) {
    setState(() {
      if (_collapsedNodeIds.contains(nodeId)) {
        _collapsedNodeIds.remove(nodeId);
      } else {
        _collapsedNodeIds.add(nodeId);
      }
      _processGraphData();
    });
  }

  @override
  void didUpdateWidget(InteractiveGraphCanvas oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.payload != oldWidget.payload) {
      // Sync processing to ensure data is ready, but also use microtask to avoid
      // modifying controller during the same build/layout pass that triggered this.
      scheduleMicrotask(() {
        if (!mounted) return;
        _collapsedNodeIds.clear();
        _initialCollapse();
        _processGraphData();
        setState(() {}); // Ensure build is called after controller modification
      });
    }
  }

  // ... (dispose and registerPrototypes stay same)

  void _registerPrototypes() {
    // Register a universal node prototype that acts as a container for all our node types.
    // We differentiate visually based on the data we attach.
    _controller.registerNodePrototype(
      FlNodePrototype(
        idName: 'universal_node',
        displayName: (context) => 'Universal Node',
        description: (context) => 'A generic node for agents and tools',
        ports: [
          FlDataInputPortPrototype(
            idName: 'in',
            displayName: (context) => 'In',
          ),
          FlDataOutputPortPrototype(
            idName: 'out',
            displayName: (context) => 'Out',
            styleBuilder: (state) => FlPortStyle(
              shape: FlPortShape.circle,
              color: AppColors.primaryTeal,
              radius: 6,
              linkStyleBuilder: (state) => const FlLinkStyle.basic(),
            ),
          ),
        ],
        onExecute: (ports, fields, state, forward, put) async {
          // No-op for visualization
        },
      ),
    );
  }

  void _processGraphData({bool force = false}) {
    final payload = widget.payload;
    // Hash includes collapsed state and node contents to detect changes better
    final nodeHash = payload.nodes.fold(
      0,
      (acc, n) => acc ^ n.id.hashCode ^ n.hasError.hashCode ^ n.executionCount,
    );
    final hash = Object.hash(
      payload.nodes.length,
      payload.edges.length,
      _collapsedNodeIds.length,
      _collapsedNodeIds.join(','),
      nodeHash,
    );

    if (!force && _cachedHash == hash) return;
    _cachedHash = hash;

    // 1. Clear existing
    _controller.clear();
    _nodeDataMap.clear();

    if (payload.nodes.isEmpty) {
      if (mounted && _cachedHash != -1) setState(() {});
      return;
    }

    // 2. Filter Graph based on Collapsed State (Refined Visibility)
    final visibleNodes = <String, MultiTraceNode>{};
    final visibleEdges = <MultiTraceEdge>[];

    // BFS from Roots to determine visibility
    // A node is visible if it is reachable from a Root through visible paths.
    // If a node is Collapsed, its OUTGOING edges are NOT traversed (children hidden),
    // UNLESS the child is also reachable via another non-collapsed path?
    // "Gradual Disclosure" usually implies strict tree-like hiding.
    // Let's assume strict hiding for simplicity: filtered out.

    final incomingEdges = <String, int>{};
    for (var e in payload.edges) {
      incomingEdges[e.targetId] = (incomingEdges[e.targetId] ?? 0) + 1;
    }

    final roots = payload.nodes.where((n) {
      return n.isRoot || !incomingEdges.containsKey(n.id);
    }).toList();
    if (roots.isEmpty && payload.nodes.isNotEmpty) {
      // Fallback: Cycle detected or complex graph.
      // Pick the node with the highest number of outgoing edges (Hub/Orchestrator).
      final nodeOutDegree = <String, int>{};
      for (var e in payload.edges) {
        nodeOutDegree[e.sourceId] = (nodeOutDegree[e.sourceId] ?? 0) + 1;
      }

      var bestNode = payload.nodes.first;
      var maxOut = -1;

      for (var n in payload.nodes) {
        final out = nodeOutDegree[n.id] ?? 0;
        if (out > maxOut) {
          maxOut = out;
          bestNode = n;
        } else if (out == maxOut) {
          // Tie-break: prefer 'Agent' type or 'sre_agent' ID
          if (n.id.contains('sre_agent') &&
              !bestNode.id.contains('sre_agent')) {
            bestNode = n;
          }
        }
      }
      roots.add(bestNode);
    }

    final queue = <String>[];
    final visited = <String>{};

    for (var r in roots) {
      queue.add(r.id);
      visited.add(r.id);
      visibleNodes[r.id] = r;
    }

    final adjMap = <String, List<MultiTraceEdge>>{};
    for (var e in payload.edges) {
      adjMap.putIfAbsent(e.sourceId, () => []).add(e);
    }

    while (queue.isNotEmpty) {
      final uId = queue.removeAt(0);

      // If u is open (not collapsed), we traverse its children
      if (!_collapsedNodeIds.contains(uId)) {
        final edges = adjMap[uId] ?? [];
        for (var e in edges) {
          visibleEdges.add(e);
          if (!visited.contains(e.targetId)) {
            visited.add(e.targetId);
            queue.add(e.targetId);
            // Add node to visible map
            final targetNode = payload.nodes.firstWhere(
              (n) => n.id == e.targetId,
              orElse: () => MultiTraceNode(id: e.targetId, type: 'Unknown'),
            );
            visibleNodes[e.targetId] = targetNode;
          }
        }
      }
    }

    _nodeDataMap.addAll(visibleNodes);

    // 3. Run Sugiyama Layout on Visible Graph
    if (visibleNodes.isNotEmpty) {
      _sugiyamaLayout(visibleNodes.values.toList(), visibleEdges);
    }
  }

  void _sugiyamaLayout(List<MultiTraceNode> nodes, List<MultiTraceEdge> edges) {
    if (nodes.isEmpty) return;

    // Calculate max call count for edge scaling
    var maxCallCount = 1;
    for (var e in edges) {
      if (e.callCount > maxCallCount) maxCallCount = e.callCount;
    }

    // 3. Build GraphView Graph
    final graph = gv.Graph()..isTree = false;
    final gvNodes = <String, gv.Node>{};
    final uniqueIds = <String>{};

    for (var n in nodes) {
      if (uniqueIds.contains(n.id)) continue;
      uniqueIds.add(n.id);

      final node = gv.Node.Id(n.id);

      // Set node size for Sugiyama algorithm to prevent overlap
      // Width/Height estimates based on _build*Node widgets
      final type = n.type.toLowerCase();
      if (type == 'agent' || type == 'sub_agent') {
        node.size = const Size(260, 150);
      } else if (type == 'llm') {
        node.size = const Size(240, 100);
      } else {
        node.size = const Size(200, 80); // Tool
      }

      gvNodes[n.id] = node;
      graph.addNode(node);
    }

    for (var e in edges) {
      if (gvNodes.containsKey(e.sourceId) && gvNodes.containsKey(e.targetId)) {
        graph.addEdge(gvNodes[e.sourceId]!, gvNodes[e.targetId]!);
      }
    }

    // 4. Run Sugiyama Layout
    final builder = gv.SugiyamaConfiguration()
      ..orientation = gv.SugiyamaConfiguration.ORIENTATION_LEFT_RIGHT
      ..levelSeparation = 120
      ..nodeSeparation = 60;

    final algorithm = gv.SugiyamaAlgorithm(builder);
    algorithm.run(graph, 100, 100);

    // 5. Calculate Center to Normalize
    var minX = double.infinity;
    var minY = double.infinity;
    var maxX = double.negativeInfinity;
    var maxY = double.negativeInfinity;

    for (var gvNode in gvNodes.values) {
      if (gvNode.x < minX) minX = gvNode.x;
      if (gvNode.y < minY) minY = gvNode.y;
      if (gvNode.x > maxX) maxX = gvNode.x;
      if (gvNode.y > maxY) maxY = gvNode.y;
    }

    final centerX = (minX + maxX) / 2;
    final centerY = (minY + maxY) / 2;

    for (var n in nodes) {
      final gvNode = gvNodes[n.id];
      if (gvNode != null) {
        final outgoingEdges = edges.where((e) => e.sourceId == n.id).toList();
        final hasOutgoingError = outgoingEdges.any((e) => e.errorCount > 0);

        // Edge thickness based on max call count of outgoing edges
        var nodeMaxCallCount = 1;
        if (outgoingEdges.isNotEmpty) {
          nodeMaxCallCount = outgoingEdges
              .map((e) => e.callCount)
              .reduce((a, b) => a > b ? a : b);
        }

        var thickness = 1.0;
        if (maxCallCount > 1) {
          thickness = 1.0 + (2.0 * (nodeMaxCallCount / maxCallCount));
        }

        final linkColor = hasOutgoingError
            ? AppColors.error
            : AppColors.primaryTeal.withValues(alpha: 0.6);

        _addFlNode(
          n.id,
          // Center the graph at (0,0) so "Center View" works correctly
          Offset(gvNode.x - centerX, gvNode.y - centerY),
          linkColor,
          thickness,
        );
      }
    }

    // Add links
    for (var e in edges) {
      if (_controller.isNodePresent(e.sourceId) &&
          _controller.isNodePresent(e.targetId)) {
        _controller.addLink(e.sourceId, 'out', e.targetId, 'in');
      }
    }

    _handleAutoFit();
  }

  void _handleAutoFit() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _layoutTimer?.cancel();
      _layoutTimer = Timer(const Duration(milliseconds: 500), () {
        if (!mounted) return;
        if (_controller.nodes.isNotEmpty) {
          _controller.focusNodesById(
            _controller.nodes.keys.toSet(),
            animate: true,
          );
          // After fitting, zoom out significantly more as requested
          _controller.setViewportZoom(0.05, absolute: true, animate: true);
          // Deselect all after focusing
          _controller.clearSelection();
        }
      });
    });
  }

  void _addFlNode(
    String id,
    Offset offset,
    Color linkColor,
    double linkThickness,
  ) {
    if (_controller.isNodePresent(id)) return;

    final prototype = _controller.nodePrototypes['universal_node']!;

    _controller.addNodeFromExisting(
      FlNodeDataModel(
        id: id,
        prototype: prototype,
        ports: {
          'in': FlPortDataModel(
            prototype: prototype.ports.firstWhere((p) => p.idName == 'in'),
            state: FlPortState(),
          ),
          'out': FlPortDataModel(
            prototype: FlDataOutputPortPrototype(
              idName: 'out',
              displayName: (context) => 'Out',
              styleBuilder: (state) => FlPortStyle(
                shape: FlPortShape.circle,
                color: linkColor,
                radius: 6,
                linkStyleBuilder: (state) => FlLinkStyle(
                  color: linkColor,
                  lineWidth: linkThickness,
                  drawMode: FlLineDrawMode.solid,
                  curveType: FlLinkCurveType
                      .bezier, // User requested "start from right edge" -> bezier Tangent
                ),
              ),
            ),
            state: FlPortState(),
          ),
        },
        fields: {},
        state: FlNodeState(),
        offset: offset,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (widget.payload.nodes.isEmpty) {
      return const Center(
        child: Text('No Data', style: TextStyle(color: Colors.white54)),
      );
    }

    // We use a Key based on the graph hash to force the editor to rebuild fully
    // when the graph structure changes. This prevents "NodeEditorRenderBox child count"
    // exceptions caused by the fl_nodes package losing sync with the controller.
    final graphKey = ValueKey(_cachedHash);

    return Stack(
      children: [
        FlNodeEditorWidget(
          key: graphKey,
          controller: _controller,
          overlay: () => [], // No overlays for now
          nodeBuilder: (context, nodeData) {
            final multiTraceNode = _nodeDataMap[nodeData.id];
            if (multiTraceNode == null) return const SizedBox();

            return _buildCustomNode(context, multiTraceNode, nodeData);
          },
          // Hide default headers/fields since we use custom nodeBuilder
        ),
        Positioned(
          top: 24,
          right: 24,
          child: Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: const Color(0xFF1E1E2E).withValues(alpha: 0.9),
              borderRadius: BorderRadius.circular(12),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.3),
                  blurRadius: 8,
                  offset: const Offset(0, 4),
                ),
              ],
              border: Border.all(color: Colors.white10),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildIconButton(
                  Icons.refresh,
                  'Auto Layout',
                  () {
                  _processGraphData(force: true);
                  setState(() {});
                },
                ),
                const SizedBox(width: 8),
                Container(width: 1, height: 24, color: Colors.white10),
                const SizedBox(width: 8),
                _buildIconButton(
                  Icons.crop_free,
                  'Fit to Screen',
                  _handleAutoFit,
                ),
                // Zoom buttons omitted if API is unclear, Fit is usually sufficient for "Reset"
                // User asked for limit sampling too, which is in the notifier/repo now (logic-wise).
                // UI for sampling is not yet in the canvas, maybe in the toolbar?
                // Let's keep canvas just for graph controls.
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildIconButton(IconData icon, String tooltip, VoidCallback onTap) {
    return Tooltip(
      message: tooltip,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(8),
          child: Padding(
            padding: const EdgeInsets.all(8),
            child: Icon(icon, color: Colors.white70, size: 20),
          ),
        ),
      ),
    );
  }

  Widget _buildCustomNode(
    BuildContext context,
    MultiTraceNode node,
    FlNodeDataModel nodeData,
  ) {
    switch (node.type.toLowerCase()) {
      case 'agent':
      case 'sub_agent':
        return _buildAgentNode(context, node, nodeData);
      case 'llm':
        return _buildLLMNode(context, node, nodeData);
      case 'tool':
      default:
        return _buildToolNode(context, node, nodeData);
    }
  }

  Widget _wrapWithPorts(
    Widget content,
    FlNodeDataModel nodeData, {
    Color? color,
  }) {
    final inputPort = nodeData.ports['in'];
    final outPort = nodeData.ports['out'];
    final effectiveColor = color ?? Colors.grey;

    return GestureDetector(
      behavior: HitTestBehavior.translucent,
      onTapDown: (_) {
        if (!nodeData.state.isSelected) {
          _controller.selectNodesById({nodeData.id});
        }
      },
      onPanUpdate: (details) {
        if (!nodeData.state.isSelected) {
          _controller.selectNodesById({nodeData.id});
        }
        _controller.dragSelection(details.delta);
      },
      child: Row(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          if (inputPort != null)
            IgnorePointer(
              child: Container(
                key: inputPort.key,
                width: 10,
                height: 10,
                margin: const EdgeInsets.only(right: 2),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: Colors.white24,
                  border: Border.all(color: Colors.white54, width: 1),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.3),
                      blurRadius: 2,
                    ),
                  ],
                ),
              ),
            ),
          content,
          if (outPort != null)
            IgnorePointer(
              child: Container(
                key: outPort.key,
                width: 10,
                height: 10,
                margin: const EdgeInsets.only(left: 2),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: effectiveColor,
                  border: Border.all(color: Colors.white24, width: 1.5),
                  boxShadow: [
                    BoxShadow(
                      color: effectiveColor.withValues(alpha: 0.4),
                      blurRadius: 4,
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildAgentNode(
    BuildContext context,
    MultiTraceNode node,
    FlNodeDataModel nodeData,
  ) {
    final isSelected = nodeData.state.isSelected;
    final hasError = node.hasError;
    final Color borderColor;
    if (isSelected) {
      borderColor = const Color(0xFF64B5F6); // Lighter blue for selection
    } else {
      borderColor = hasError
          ? const Color(0xFFE53935)
          : const Color(0xFF1565C0);
    }
    // Robot icon for Agents
    const iconData = Icons.smart_toy;

    final content = Container(
      width: 280,
      constraints: const BoxConstraints(maxHeight: 140),
      decoration: BoxDecoration(
        color: const Color(0xFF0D1B2A), // Darker background
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: borderColor,
          width: hasError ? 2 : 1, // Thicker if error
        ),
        boxShadow: [
          BoxShadow(
            color: borderColor.withValues(alpha: hasError ? 0.6 : 0.3),
            blurRadius: 12,
            spreadRadius: 2,
          ),
        ],
      ),
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1565C0).withValues(alpha: 0.2),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(
                        iconData,
                        color: Color(0xFF42A5F5),
                        size: 18,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        node.label ?? node.id,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                // Stats Row
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    _buildStatBadge(
                      Icons.timer,
                      _formatDuration(node.avgDurationMs),
                      Colors.grey,
                    ),
                    if (node.errorRatePct > 0)
                      _buildStatBadge(
                        Icons.warning,
                        '${node.errorRatePct.toStringAsFixed(1)}%',
                        const Color(0xFFEF5350),
                      ),
                  ],
                ),
              ],
            ),
          ),
          // Execution Count Badge
          Positioned(
            top: -6,
            right: -6,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: const Color(0xFF1565C0),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFF0D1B2A), width: 2),
              ),
              child: Text(
                '${node.executionCount}',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 10,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
        ],
      ),
    );
    return _wrapWithPorts(content, nodeData, color: borderColor);
  }

  Widget _buildLLMNode(
    BuildContext context,
    MultiTraceNode node,
    FlNodeDataModel nodeData,
  ) {
    final isSelected = nodeData.state.isSelected;
    final hasError = node.hasError;
    final Color borderColor;
    if (isSelected) {
      borderColor = const Color(0xFFD1C4E9); // Lighter purple for selection
    } else {
      borderColor = hasError
          ? const Color(0xFFE53935)
          : const Color(0xFF673AB7);
    }
    // Sparkles for LLM
    const iconData = Icons.auto_awesome;

    final content = Container(
      width: 240,
      constraints: const BoxConstraints(maxHeight: 110),
      decoration: BoxDecoration(
        color: const Color(0xFF1A1025), // Dark purple tint
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: borderColor, width: hasError ? 2 : 1,
        ),
        boxShadow: [
          BoxShadow(
            color: borderColor.withValues(alpha: hasError ? 0.6 : 0.2),
            blurRadius: 10,
          ),
        ],
      ),
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Padding(
            padding: const EdgeInsets.all(10),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(iconData, color: Color(0xFF9575CD), size: 16),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        node.label?.replaceAll('generate_content ', '') ??
                            node.id,
                        style: const TextStyle(
                          color: Color(0xFFD1C4E9),
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Text(
                      _formatDuration(node.avgDurationMs),
                      style: const TextStyle(color: Colors.grey, fontSize: 11),
                    ),
                    const Spacer(),
                    if (node.totalTokens > 0)
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 6,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: const Color(0xFF673AB7).withValues(alpha: 0.2),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          '${(node.totalTokens / 1000).toStringAsFixed(1)}k',
                          style: const TextStyle(
                            color: Color(0xFFB39DDB),
                            fontSize: 10,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                  ],
                ),
              ],
            ),
          ),
          Positioned(
            top: -6,
            right: -6,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: const Color(0xFF512DA8),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFF1A1025), width: 2),
              ),
              child: Text(
                '${node.executionCount}',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 9,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
        ],
      ),
    );
    return _wrapWithPorts(content, nodeData, color: borderColor);
  }





  Widget _buildToolNode(
    BuildContext context,
    MultiTraceNode node,
    FlNodeDataModel nodeData, {
    Color? forceColor,
  }) {
    final isSelected = nodeData.state.isSelected;
    final hasError = node.hasError;

    Color borderColor;
    if (isSelected) {
      borderColor = Colors
          .white; // Explicit white for selection across all tool/generic modes
    } else if (forceColor != null) {
      borderColor = forceColor;
    } else {
      borderColor = hasError
          ? const Color(0xFFE53935)
          : const Color(0xFF546E7A);
    }
    // Wrench for Tool
    const iconData = Icons.build;

    final content = Container(
      width: 200,
      constraints: const BoxConstraints(maxHeight: 90),
      decoration: BoxDecoration(
        color: const Color(0xFF181C1F), // Dark grey
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: borderColor, width: hasError ? 2 : 1,
        ),
      ),
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Padding(
            padding: const EdgeInsets.all(8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Row(
                  children: [
                    const Icon(iconData, color: Color(0xFF90A4AE), size: 14),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        node.label ?? node.id,
                        style: const TextStyle(
                          color: Color(0xFFCFD8DC),
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  _formatDuration(node.avgDurationMs),
                  style: const TextStyle(color: Colors.grey, fontSize: 10),
                ),
              ],
            ),
          ),
          if (node.executionCount > 1)
            Positioned(
              top: -4,
              right: -4,
              child: Container(
                width: 18,
                height: 18,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: const Color(0xFF455A64),
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: const Color(0xFF181C1F),
                    width: 1.5,
                  ),
                ),
                child: Text(
                  '${node.executionCount}',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 8,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
    return _wrapWithPorts(content, nodeData, color: borderColor);
  }

  Widget _buildStatBadge(IconData icon, String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 10, color: color),
          const SizedBox(width: 4),
          Text(
            text,
            style: TextStyle(
              color: color,
              fontSize: 10,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  String _formatDuration(double ms) {
    if (ms < 1) return '<1ms';
    if (ms < 1000) return '${ms.round()}ms';
    return '${(ms / 1000).toStringAsFixed(1)}s';
  }
}
