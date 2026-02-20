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
  final ValueChanged<MultiTraceNode>? onNodeSelected;
  final ValueChanged<MultiTraceEdge>? onEdgeSelected;
  final VoidCallback? onSelectionCleared;
  final GraphViewMode viewMode;

  const InteractiveGraphCanvas({
    super.key,
    required this.payload,
    this.onNodeSelected,
    this.onEdgeSelected,
    this.onSelectionCleared,
    this.viewMode = GraphViewMode.standard,
  });

  @override
  State<InteractiveGraphCanvas> createState() => _InteractiveGraphCanvasState();
}

class _InteractiveGraphCanvasState extends State<InteractiveGraphCanvas>
    with TickerProviderStateMixin {
  late FlNodeEditorController _controller;
  // State for gradual disclosure
  final Set<String> _collapsedNodeIds = {};

  // Map to store the actual data associated with each node ID
  final Map<String, MultiTraceNode> _nodeDataMap = {};

  // Cache layout to avoid re-calculating on every build
  int _cachedHash = -1;

  Timer? _layoutTimer;

  // Animation for expand/collapse transitions
  late final AnimationController _layoutAnimController;
  late final Animation<double> _layoutAnimation;
  Map<String, Offset> _previousPositions = {};
  Map<String, Offset> _targetPositions = {};

  // Path highlighting state
  Set<String> _highlightedPath = {};
  String? _lockedSelectionId;

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
    _layoutAnimController = AnimationController(
      duration: const Duration(milliseconds: 400),
      vsync: this,
    );
    _layoutAnimation = CurvedAnimation(
      parent: _layoutAnimController,
      curve: Curves.easeInOut,
    );
    _layoutAnimation.addListener(_onLayoutAnimationTick);
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

  bool _hasChildren(String nodeId) {
    return widget.payload.edges.any((e) => e.sourceId == nodeId);
  }

  void _toggleCollapse(String nodeId) {
    // Save current positions before reprocessing
    _previousPositions = {};
    for (final entry in _controller.nodes.entries) {
      _previousPositions[entry.key] = entry.value.offset;
    }

    // Toggle collapsed state
    if (_collapsedNodeIds.contains(nodeId)) {
      _collapsedNodeIds.remove(nodeId);
    } else {
      _collapsedNodeIds.add(nodeId);
    }

    // Reprocess to compute new layout
    _processGraphData();

    // Save target positions and reset to previous for animation
    _targetPositions = {};
    for (final entry in _controller.nodes.entries) {
      _targetPositions[entry.key] = entry.value.offset;
      // Start from previous position if available, otherwise stay at target
      entry.value.offset = _previousPositions[entry.key] ?? entry.value.offset;
    }

    // Animate from previous to target positions
    _layoutAnimController.forward(from: 0.0);
    setState(() {});
  }

  void _onLayoutAnimationTick() {
    final t = _layoutAnimation.value;
    for (final entry in _controller.nodes.entries) {
      final prev = _previousPositions[entry.key];
      final target = _targetPositions[entry.key];
      if (prev != null && target != null) {
        entry.value.offset = Offset.lerp(prev, target, t)!;
      }
    }
    if (mounted) setState(() {});
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

  @override
  void dispose() {
    _layoutTimer?.cancel();
    _layoutAnimController.dispose();
    super.dispose();
  }

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
          // Center the graph at (0,0) so "Center View" works correctly
          Offset(gvNode.x - centerX, gvNode.y - centerY),
          linkColor,
          thickness,
          hasBackEdge: hasBackEdge,
        );
      }
    }

    // Add links -- use 'back_out' port for back-edges (dashed) and 'out' for forward
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
                  curveType: FlLinkCurveType
                      .bezier, // User requested "start from right edge" -> bezier Tangent
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
                _buildIconButton(Icons.refresh, 'Auto Layout', () {
                  _processGraphData(force: true);
                  setState(() {});
                }),
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
    if (node.isUserNode || node.isUserEntryPoint) {
      return RepaintBoundary(
        child: _buildUserEntryNode(context, node, nodeData),
      );
    }

    if (widget.viewMode != GraphViewMode.standard) {
      return RepaintBoundary(
        child: _buildGenericNode(context, node, nodeData),
      );
    }

    Widget content;
    switch (node.type.toLowerCase()) {
      case 'agent':
      case 'sub_agent':
        content = _buildAgentNode(context, node, nodeData);
      case 'llm':
        content = _buildLLMNode(context, node, nodeData);
      case 'tool':
      default:
        content = _buildToolNode(context, node, nodeData);
    }
    return RepaintBoundary(child: content);
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
          color: isSelected
              ? AppColors.primaryCyan
              : color.withValues(alpha: 0.5),
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
    if (widget.viewMode == GraphViewMode.costHeatmap) {
      final maxCost = widget.payload.nodes
          .map((n) => n.totalCost ?? 0)
          .fold<double>(0, (a, b) => a > b ? a : b);
      if (maxCost <= 0) return Colors.grey;
      final ratio = ((node.totalCost ?? 0) / maxCost).clamp(0.0, 1.0);
      return _getTokenHeatmapColor((ratio * 1000).toInt(), 1000);
    }
    return _nodeColor(node.type);
  }

  int _getMaxTokens() {
    var maxTokens = 1;
    for (var n in widget.payload.nodes) {
      if (n.totalTokens > maxTokens) maxTokens = n.totalTokens;
    }
    return maxTokens;
  }

  Color _getTokenHeatmapColor(int tokens, int maxTokens) {
    if (maxTokens <= 0) return Colors.grey;
    final ratio = (tokens / maxTokens).clamp(0.0, 1.0);
    // Gradient from cool (low tokens) to hot (high tokens)
    if (ratio < 0.25) {
      return Color.lerp(Colors.blue.shade900, Colors.blue, ratio * 4)!;
    } else if (ratio < 0.5) {
      return Color.lerp(Colors.blue, Colors.green, (ratio - 0.25) * 4)!;
    } else if (ratio < 0.75) {
      return Color.lerp(Colors.green, Colors.orange, (ratio - 0.5) * 4)!;
    } else {
      return Color.lerp(Colors.orange, Colors.red, (ratio - 0.75) * 4)!;
    }
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
    final isDimmed =
        _highlightedPath.isNotEmpty && !_highlightedPath.contains(nodeData.id);

    return GestureDetector(
      behavior: HitTestBehavior.translucent,
      onTapDown: (_) {
        final nodeId = nodeData.id;
        if (_lockedSelectionId == nodeId) {
          // Deselect
          setState(() {
            _lockedSelectionId = null;
            _highlightedPath.clear();
          });
          _controller.clearSelection();
          widget.onSelectionCleared?.call();
        } else {
          setState(() {
            _lockedSelectionId = nodeId;
            _highlightedPath = _computePath(nodeId);
          });
          _controller.selectNodesById({nodeId});
          final node = _nodeDataMap[nodeId];
          if (node != null) {
            widget.onNodeSelected?.call(node);
          }
        }
      },
      onPanUpdate: (details) {
        if (!nodeData.state.isSelected) {
          _controller.selectNodesById({nodeData.id});
        }
        _controller.dragSelection(details.delta);
      },
      child: Opacity(
        opacity: isDimmed ? 0.2 : 1.0,
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
      ),
    );
  }

  Set<String> _computePath(String nodeId) {
    final path = <String>{nodeId};
    final adjForward = <String, List<String>>{};
    final adjReverse = <String, List<String>>{};
    for (final e in widget.payload.edges) {
      adjForward.putIfAbsent(e.sourceId, () => []).add(e.targetId);
      adjReverse.putIfAbsent(e.targetId, () => []).add(e.sourceId);
    }
    // BFS downstream
    final queue = [nodeId];
    while (queue.isNotEmpty) {
      final u = queue.removeAt(0);
      for (final v in (adjForward[u] ?? [])) {
        if (path.add(v)) queue.add(v);
      }
    }
    // BFS upstream
    queue.add(nodeId);
    final visited = <String>{nodeId};
    while (queue.isNotEmpty) {
      final u = queue.removeAt(0);
      for (final v in (adjReverse[u] ?? [])) {
        if (visited.add(v)) {
          path.add(v);
          queue.add(v);
        }
      }
    }
    return path;
  }

  Widget _buildAgentNode(
    BuildContext context,
    MultiTraceNode node,
    FlNodeDataModel nodeData,
  ) {
    final isSelected = nodeData.state.isSelected;
    final hasError = node.hasError;
    const color = AppColors.primaryTeal;
    // Robot icon for Agents
    const iconData = Icons.smart_toy;

    final Color borderColor;
    if (isSelected) {
      borderColor = AppColors.primaryCyan;
    } else if (hasError) {
      borderColor = const Color(0xFFE53935);
    } else if (node.isRoot) {
      borderColor = AppColors.primaryCyan.withValues(alpha: 0.5);
    } else {
      borderColor = const Color(0xFF1565C0);
    }

    final content = Container(
      width: 280,
      constraints: const BoxConstraints(maxHeight: 140),
      decoration: BoxDecoration(
        color: const Color(0xFF0D1B2A), // Darker background
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: borderColor,
          width: (isSelected || hasError) ? 2 : 1,
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
                    // Expand/collapse toggle for agent nodes with children
                    if (_hasChildren(node.id))
                      GestureDetector(
                        onTap: () => _toggleCollapse(node.id),
                        child: Icon(
                          _collapsedNodeIds.contains(node.id)
                              ? Icons.expand_more
                              : Icons.expand_less,
                          color: Colors.white54,
                          size: 18,
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 8),
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
                  const SizedBox(height: 8),
                ],
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
                const SizedBox(height: 4),
                _buildMetricsRow(node, color),
                _buildOutgoingEdgeSummary(node),
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
          // Expand/Collapse toggle (only if node has children)
          if (widget.payload.edges.any((e) => e.sourceId == node.id))
            Positioned(
              bottom: -12,
              left: 0,
              right: 0,
              child: Center(
                child: GestureDetector(
                  onTap: () => _toggleCollapse(node.id),
                  child: Container(
                    width: 24,
                    height: 24,
                    decoration: BoxDecoration(
                      color: const Color(0xFF0D1B2A),
                      shape: BoxShape.circle,
                      border: Border.all(color: borderColor, width: 1.5),
                    ),
                    child: Icon(
                      _collapsedNodeIds.contains(node.id)
                          ? Icons.chevron_right
                          : Icons.expand_more,
                      color: Colors.white70,
                      size: 16,
                    ),
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
        border: Border.all(color: borderColor, width: hasError ? 2 : 1),
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
        border: Border.all(color: borderColor, width: hasError ? 2 : 1),
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

  // ignore: unused_element
  String _cleanId(String id) {
    if (id.contains('generate_content') && id.split(' ').length > 1) {
      return id.split(' ').sublist(1).join(' ');
    }
    return id;
  }

  Widget _buildMetricsRow(
    MultiTraceNode node,
    Color accentColor,
  ) {
    final isAgent =
        node.type.toLowerCase() == 'agent' ||
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
        if (showCost) _buildCostBadge(node.totalCost!, const Color(0xFF00E676)),
        if (showSubcalls)
          _buildSubcallBadge(node.toolCallCount, node.llmCallCount),
      ],
    );
  }

  Widget _buildErrorRateBadge(double errorRatePct) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
      decoration: BoxDecoration(
        color: AppColors.error.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.error_outline, size: 10, color: AppColors.error),
          const SizedBox(width: 2),
          Text(
            '${errorRatePct.toStringAsFixed(1)}%',
            style: const TextStyle(
              color: AppColors.error,
              fontSize: 10,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLatencyBadge(double durationMs, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.timer, size: 10, color: color),
          const SizedBox(width: 2),
          Text(
            _formatDuration(durationMs),
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

  Widget _buildTokenBadge(int tokens, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.token, size: 10, color: color),
          const SizedBox(width: 2),
          Text(
            _formatTokens(tokens),
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

    final totalCalls = outgoing.fold<int>(0, (sum, e) => sum + e.callCount);
    final avgDuration =
        outgoing
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

  String _formatDuration(double ms) {
    if (ms < 1) return '<1ms';
    if (ms < 1000) return '${ms.round()}ms';
    return '${(ms / 1000).toStringAsFixed(1)}s';
  }
}
