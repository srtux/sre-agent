import 'dart:async';

import 'package:fl_nodes/fl_nodes.dart';
import 'package:flutter/material.dart';

import 'package:graphview/GraphView.dart' as gv;
import '../../../theme/app_theme.dart';
import '../domain/graph_view_mode.dart';
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
  final GraphViewMode viewMode;
  final ValueChanged<MultiTraceNode>? onNodeSelected;
  final ValueChanged<MultiTraceEdge>? onEdgeSelected;
  final VoidCallback? onSelectionCleared;

  const InteractiveGraphCanvas({
    super.key,
    required this.payload,
    this.viewMode = GraphViewMode.standard,
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
      // Reset collapse state on new payload? Or try to preserve?
      // For now, reset to avoid stale IDs, or maybe re-run initial collapse
      _collapsedNodeIds.clear();
      _initialCollapse();
      _processGraphData();
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
          // Separate port for back-edges (cycles) rendered with dashed lines
          FlDataOutputPortPrototype(
            idName: 'back_out',
            displayName: (context) => 'Back',
            styleBuilder: (state) => FlPortStyle(
              shape: FlPortShape.circle,
              color: Colors.transparent,
              radius: 0,
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

  void _processGraphData() {
    final payload = widget.payload;
    // Hash includes collapsed state now
    final hash = Object.hash(
      payload.nodes.length,
      payload.edges.length,
      _collapsedNodeIds.length,
      _collapsedNodeIds.join(','),
    );
    if (_cachedHash == hash) return;
    _cachedHash = hash;

    // 1. Clear existing
    _controller.clear();
    _nodeDataMap.clear();

    if (payload.nodes.isEmpty) return;

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
      roots.add(payload.nodes.first); // Fallback
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

    final graph = gv.Graph()..isTree = false;
    final gvNodes = <String, gv.Node>{};

    // Calculate max call count for edge scaling
    var maxCallCount = 1;
    for (var e in edges) {
      if (e.callCount > maxCallCount) maxCallCount = e.callCount;
    }

    for (var n in nodes) {
      final node = gv.Node.Id(n.id);
      gvNodes[n.id] = node;
      graph.addNode(node);
    }

    for (var e in edges) {
      if (gvNodes.containsKey(e.sourceId) && gvNodes.containsKey(e.targetId)) {
        graph.addEdge(gvNodes[e.sourceId]!, gvNodes[e.targetId]!);
      }
    }

    final builder = gv.SugiyamaConfiguration()
      ..orientation = gv
          .SugiyamaConfiguration
          .ORIENTATION_TOP_BOTTOM // Use standard TB and rotate manually
      ..levelSeparation =
          150 // Vertical in TB -> Horizontal in LR
      ..nodeSeparation = 50; // Horizontal in TB -> Vertical in LR

    final algorithm = gv.SugiyamaAlgorithm(builder);
    algorithm.run(graph, 100, 100);

    // Debug: Check if nodes are spread out
    if (nodes.isNotEmpty) {
      final first = gvNodes[nodes.first.id]!;
      debugPrint(
        'LAYOUT DEBUG: First Node ${nodes.first.id} at ${first.x}, ${first.y}',
      );
      var allSame = true;
      for (var n in nodes) {
        final g = gvNodes[n.id]!;
        if (g.x != first.x || g.y != first.y) {
          allSame = false;
          break;
        }
      }
      if (allSame) {
        debugPrint(
          'LAYOUT ERROR: All nodes at same position! Algorithm failed.',
        );
        // Fallback to simple grid
        var i = 0;
        for (var n in nodes) {
          final row = i ~/ 5;
          final col = i % 5;
          gvNodes[n.id]!
            ..x = col * 300.0
            ..y = row * 150.0;
          i++;
        }
      }
    }

    // Build depth map from layout positions for back-edge detection.
    // In our LR layout (swapped from TB), the X position (gvNode.y * 1.5)
    // determines the "layer". Higher gvNode.y = further right = deeper layer.
    final depthMap = <String, double>{};
    for (var n in nodes) {
      final gvNode = gvNodes[n.id];
      if (gvNode != null) {
        depthMap[n.id] = gvNode.y;
      }
    }

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

        var thickness = 1.0; // Base thickness
        // User requested: "edges that have higher usage (more traces) ... slightly thicker"
        // "don't make lines too thick" -> Use range 1.0 to 3.0
        if (maxCallCount > 1) {
          // Linear scale: 1.0 to 3.0
          thickness = 1.0 + (2.0 * (nodeMaxCallCount / maxCallCount));
        }

        final linkColor = hasOutgoingError
            ? AppColors.error
            : AppColors.primaryTeal.withValues(alpha: 0.6);

        // Detect if this node has any back-edges (target at same or earlier layer)
        final hasBackEdge = outgoingEdges.any((e) {
          final srcDepth = depthMap[e.sourceId] ?? 0;
          final tgtDepth = depthMap[e.targetId] ?? 0;
          return tgtDepth <= srcDepth;
        });

        // SWAP X and Y for Left-to-Right layout since we used Top-Bottom algorithm
        // Also increase scaling if needed manually
        _addFlNode(
          n.id,
          Offset(gvNode.y * 1.5, gvNode.x * 1.2),
          linkColor,
          thickness,
          hasBackEdge: hasBackEdge,
        );
      }
    }

    // Add links — use 'back_out' port for back-edges (dashed) and 'out' for forward
    for (var e in edges) {
      if (_controller.isNodePresent(e.sourceId) &&
          _controller.isNodePresent(e.targetId)) {
        final srcDepth = depthMap[e.sourceId] ?? 0;
        final tgtDepth = depthMap[e.targetId] ?? 0;
        final isBackEdge = tgtDepth <= srcDepth;
        final outPort = isBackEdge ? 'back_out' : 'out';
        _controller.addLink(e.sourceId, outPort, e.targetId, 'in');
      }
    }

    _handleAutoFit();
  }

  void _handleAutoFit() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _layoutTimer?.cancel();
      _layoutTimer = Timer(const Duration(milliseconds: 300), () {
        if (!mounted) return;
        if (_controller.nodes.isNotEmpty) {
          _controller.focusNodesById(
            _controller.nodes.keys.toSet(),
            animate: true,
          );
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
    double linkThickness, {
    bool hasBackEdge = false,
  }) {
    if (_controller.isNodePresent(id)) return;

    final prototype = _controller.nodePrototypes['universal_node']!;

    final backEdgeColor = linkColor.withValues(alpha: 0.4);

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
                  curveType: FlLinkCurveType.bezier,
                ),
              ),
            ),
            state: FlPortState(),
          ),
          'back_out': FlPortDataModel(
            prototype: FlDataOutputPortPrototype(
              idName: 'back_out',
              displayName: (context) => 'Back',
              styleBuilder: (state) => FlPortStyle(
                shape: FlPortShape.circle,
                color: hasBackEdge ? backEdgeColor : Colors.transparent,
                radius: hasBackEdge ? 4 : 0,
                linkStyleBuilder: (state) => FlLinkStyle(
                  color: backEdgeColor,
                  lineWidth: linkThickness.clamp(1.0, 2.0),
                  drawMode: FlLineDrawMode.dashed,
                  curveType: FlLinkCurveType.bezier,
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

  int _getMaxTokens() {
    var max = 0;
    for (var n in widget.payload.nodes) {
      if (n.totalTokens > max) max = n.totalTokens;
    }
    return max > 0 ? max : 1;
  }

  Color _getTokenHeatmapColor(int tokens, int maxTokens) {
    if (tokens == 0) return Colors.grey.withValues(alpha: 0.3);
    final ratio = tokens / maxTokens;
    // Green -> Yellow -> Red gradient
    if (ratio < 0.5) {
      return Color.lerp(Colors.green, Colors.yellow, ratio * 2)!;
    } else {
      return Color.lerp(Colors.yellow, Colors.red, (ratio - 0.5) * 2)!;
    }
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
          bottom: 24,
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
                  () => _processGraphData(),
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
    if (node.isUserEntryPoint) {
      return _buildUserEntryNode(context, node, nodeData);
    }

    if (widget.viewMode != GraphViewMode.standard) {
      return _buildGenericNode(context, node, nodeData);
    }

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

  Widget _buildGenericNode(
    BuildContext context,
    MultiTraceNode node,
    FlNodeDataModel nodeData,
  ) {
    return _buildToolNode(
      context,
      node,
      nodeData,
      forceColor: _getNodeColorForMode(node),
    );
  }

  Widget _buildUserEntryNode(
    BuildContext context,
    MultiTraceNode node,
    FlNodeDataModel nodeData,
  ) {
    final isSelected = nodeData.state.isSelected;
    const color = AppColors.primaryBlue;

    final content = Container(
      width: 80,
      height: 80,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: const Color(0xFF1A2744),
        border: Border.all(
          color: isSelected ? AppColors.primaryCyan : color.withValues(alpha: 0.5),
          width: isSelected ? 2.5 : 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: color.withValues(alpha: isSelected ? 0.4 : 0.15),
            blurRadius: isSelected ? 16 : 8,
          ),
        ],
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(Icons.person, size: 28, color: color),
          const SizedBox(height: 2),
          Text(
            'User',
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.9),
              fontSize: 11,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
    return _wrapWithPorts(content, nodeData, color: color);
  }

  Color _getNodeColorForMode(MultiTraceNode node) {
    if (widget.viewMode == GraphViewMode.tokenHeatmap) {
      return _getTokenHeatmapColor(node.totalTokens, _getMaxTokens());
    }
    if (widget.viewMode == GraphViewMode.errorHeatmap) {
      return node.hasError
          ? AppColors.error
          : AppColors.primaryTeal.withValues(alpha: 0.3);
    }
    return _nodeColor(node.type);
  }

  Color _nodeColor(String type) {
    switch (type.toLowerCase()) {
      case 'agent':
      case 'sub_agent':
        return AppColors.primaryTeal;
      case 'tool':
        return AppColors.warning;
      case 'llm':
        return AppColors.secondaryPurple;
      default:
        return Colors.grey;
    }
  }

  Widget _wrapWithPorts(
    Widget content,
    FlNodeDataModel nodeData, {
    Color? color,
  }) {
    final inputPort = nodeData.ports['in'];
    final outPort = nodeData.ports['out'];
    final backOutPort = nodeData.ports['back_out'];
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
            Container(
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
          content,
          // Stack the forward and back-edge ports together
          Stack(
            alignment: Alignment.center,
            children: [
              if (outPort != null)
                Container(
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
              // Invisible anchor for back-edge links (co-located with out port)
              if (backOutPort != null)
                SizedBox(key: backOutPort.key, width: 0, height: 0),
            ],
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
    const color = AppColors.primaryTeal;
    final borderColor = isSelected
        ? AppColors.primaryCyan
        : node.isRoot
            ? AppColors.primaryCyan.withValues(alpha: 0.5)
            : Colors.white10;

    final content = Container(
      width: 260,
      decoration: BoxDecoration(
        color: const Color(0xFF181825),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: borderColor,
          width: isSelected ? 2 : 1,
        ),
        boxShadow: isSelected
            ? [
                BoxShadow(
                  color: AppColors.primaryCyan.withValues(alpha: 0.3),
                  blurRadius: 16,
                ),
              ]
            : [
                const BoxShadow(
                  color: Colors.black54,
                  blurRadius: 8,
                  offset: Offset(0, 4),
                ),
              ],
      ),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.1),
              borderRadius: const BorderRadius.vertical(
                top: Radius.circular(15),
              ),
            ),
            child: Row(
              children: [
                const Icon(Icons.smart_toy, size: 16, color: color),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    node.id.toUpperCase(),
                    style: const TextStyle(
                      color: color,
                      fontWeight: FontWeight.bold,
                      fontSize: 12,
                      letterSpacing: 1.0,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                // Expand/Collapse Button
                InkWell(
                  onTap: () => _toggleCollapse(node.id),
                  child: Container(
                    padding: const EdgeInsets.all(4),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.1),
                      shape: BoxShape.circle,
                    ),
                    child: Icon(
                      _collapsedNodeIds.contains(node.id)
                          ? Icons.add
                          : Icons.remove,
                      size: 14,
                      color: color,
                    ),
                  ),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (node.description != null) ...[
                  Text(
                    node.description!,
                    style: const TextStyle(
                      color: Colors.white70,
                      fontSize: 13,
                      height: 1.4,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 12),
                ],
                _buildMetricsRow(node, color),
                _buildOutgoingEdgeSummary(node),
              ],
            ),
          ),
        ],
      ),
    );
    return _wrapWithPorts(content, nodeData, color: color);
  }

  Widget _buildLLMNode(
    BuildContext context,
    MultiTraceNode node,
    FlNodeDataModel nodeData,
  ) {
    final isSelected = nodeData.state.isSelected;
    const color = AppColors.secondaryPurple;
    const secondaryPink = Color(0xFFF472B6); // Pink 400

    final content = Container(
      width: 240,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFF2A1E3E),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(
          color: isSelected ? secondaryPink : color.withValues(alpha: 0.3),
          width: isSelected ? 2 : 1,
        ),
        boxShadow: [
          BoxShadow(
            color: color.withValues(alpha: isSelected ? 0.4 : 0.1),
            blurRadius: 12,
            spreadRadius: isSelected ? 2 : 0,
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.auto_awesome, size: 18, color: secondaryPink),
              const SizedBox(width: 8),
              Flexible(
                child: Text(
                  _cleanId(node.id),
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                    fontSize: 14,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          _buildMetricsRow(node, secondaryPink, compact: true),
        ],
      ),
    );
    return _wrapWithPorts(content, nodeData, color: color);
  }

  Widget _buildToolNode(
    BuildContext context,
    MultiTraceNode node,
    FlNodeDataModel nodeData, {
    Color? forceColor,
  }) {
    final isSelected = nodeData.state.isSelected;
    final color = forceColor ?? AppColors.warning;

    final content = Container(
      width: 200,
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: const Color(0xFF252525),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isSelected ? color : Colors.white12,
          width: isSelected ? 2 : 1,
        ),
        boxShadow: isSelected
            ? [BoxShadow(color: color.withValues(alpha: 0.3), blurRadius: 8)]
            : [],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.build_circle_outlined, size: 14, color: color),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  _cleanId(node.id),
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.9),
                    fontSize: 12,
                    fontWeight: FontWeight.w500,
                    fontFamily: 'Roboto Mono',
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          if (node.hasError || node.avgDurationMs > 0) ...[
            const SizedBox(height: 6),
            _buildMetricsRow(node, color, compact: true),
          ],
        ],
      ),
    );
    return _wrapWithPorts(content, nodeData, color: color);
  }

  String _cleanId(String id) {
    if (id.contains('generate_content') && id.split(' ').length > 1) {
      return id.split(' ').sublist(1).join(' ');
    }
    return id;
  }

  Widget _buildMetricsRow(
    MultiTraceNode node,
    Color accentColor, {
    bool compact = false,
  }) {
    final isAgent = node.type.toLowerCase() == 'agent' ||
        node.type.toLowerCase() == 'sub_agent';
    final showCost = node.totalCost != null && node.totalCost! > 0;
    final showSubcalls =
        isAgent && (node.toolCallCount > 0 || node.llmCallCount > 0);

    return Wrap(
      spacing: 4,
      runSpacing: 4,
      children: [
        if (node.hasError) _buildErrorRateBadge(node.errorRatePct),
        if (node.avgDurationMs > 0)
          _buildLatencyBadge(node.avgDurationMs, accentColor),
        if (node.totalTokens > 0)
          _buildTokenBadge(node.totalTokens, accentColor),
        if (showCost)
          _buildCostBadge(node.totalCost!, const Color(0xFF00E676)),
        if (showSubcalls)
          _buildSubcallBadge(node.toolCallCount, node.llmCallCount),
      ],
    );
  }

  Widget _buildTokenBadge(int tokens, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        '${_formatTokens(tokens)} toks',
        style: TextStyle(
          color: color.withValues(alpha: 1.0),
          fontSize: 10,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }

  Widget _buildLatencyBadge(double latencyMs, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        '${latencyMs.toStringAsFixed(0)}ms',
        style: TextStyle(
          color: color.withValues(alpha: 1.0),
          fontSize: 10,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }

  Widget _buildErrorRateBadge(double errorRate) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
      decoration: BoxDecoration(
        color: AppColors.error.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.error, color: AppColors.error, size: 10),
          if (errorRate > 0) ...[
            const SizedBox(width: 2),
            Text(
              '${errorRate.toStringAsFixed(0)}%',
              style: const TextStyle(
                color: AppColors.error,
                fontSize: 10,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildCostBadge(double cost, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        '\$${_formatCost(cost)}',
        style: TextStyle(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }

  Widget _buildSubcallBadge(int toolCount, int llmCount) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        '${toolCount}T ${llmCount}L',
        style: TextStyle(
          color: Colors.white.withValues(alpha: 0.6),
          fontSize: 10,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }

  Widget _buildOutgoingEdgeSummary(MultiTraceNode node) {
    final outgoing = widget.payload.edges
        .where((e) => e.sourceId == node.id)
        .toList();
    if (outgoing.isEmpty) return const SizedBox.shrink();

    final totalCalls =
        outgoing.fold<int>(0, (sum, e) => sum + e.callCount);
    final avgDuration = outgoing
            .where((e) => e.avgDurationMs > 0)
            .fold<double>(0, (sum, e) => sum + e.avgDurationMs) /
        (outgoing.where((e) => e.avgDurationMs > 0).length.clamp(1, 9999));
    final totalCost = outgoing.fold<double>(
      0,
      (sum, e) => sum + (e.totalCost ?? 0),
    );

    final parts = <String>[
      '$totalCalls calls',
      if (avgDuration > 0) 'avg ${avgDuration.toStringAsFixed(1)}ms',
      if (totalCost > 0) '\$${_formatCost(totalCost)}',
    ];

    return Padding(
      padding: const EdgeInsets.only(top: 8),
      child: Row(
        children: [
          Icon(
            Icons.arrow_forward,
            size: 10,
            color: Colors.white.withValues(alpha: 0.3),
          ),
          const SizedBox(width: 4),
          Expanded(
            child: Text(
              parts.join(' | '),
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.35),
                fontSize: 10,
                fontStyle: FontStyle.italic,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }

  String _formatCost(double cost) {
    if (cost >= 1.0) return cost.toStringAsFixed(2);
    if (cost >= 0.01) return cost.toStringAsFixed(3);
    return cost.toStringAsFixed(4);
  }

  String _formatTokens(int tokens) {
    if (tokens >= 1000000) return '${(tokens / 1000000).toStringAsFixed(1)}M';
    if (tokens >= 1000) return '${(tokens / 1000).toStringAsFixed(1)}K';
    return '$tokens';
  }
}
