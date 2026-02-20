import 'dart:async';

import 'package:fl_nodes/fl_nodes.dart';
import 'package:flutter/material.dart';

import '../../../theme/app_theme.dart';
import '../domain/graph_view_mode.dart';
import '../domain/models.dart';
import 'back_edge_painter.dart';
import 'graph_animation_controller.dart';
import 'graph_layout_engine.dart';
import 'graph_topology_helper.dart';

/// Interactive graph canvas using fl_nodes, with modular layout, topology
/// analysis, and animation.
///
/// Delegates to:
/// - [GraphTopologyHelper] for DFS cycle detection and visible-graph filtering
/// - [GraphLayoutEngine] for Sugiyama position computation
/// - [GraphTransitionState] for sprouting/collapsing animation interpolation
/// - [BackEdgePainter] for sweeping bezier arc back-edges
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

  // --- Topology ---
  late GraphTopologyHelper _topology;

  // --- Expand/Collapse state (positive semantics: expanded = children visible) ---
  Set<String> _expandedNodeIds = {};

  // --- Visible graph cache ---
  late VisibleGraph _visibleGraph;
  final Map<String, MultiTraceNode> _nodeDataMap = {};
  List<BackEdgePath> _backEdgePaths = [];

  // Cache layout to avoid re-calculating on every build
  int _cachedHash = -1;
  Timer? _layoutTimer;

  // --- Layout transition animation (400ms easeOutCubic) ---
  late final AnimationController _layoutAnimController;
  late final Animation<double> _layoutAnimation;
  GraphTransitionState _transition = GraphTransitionState.empty;
  Map<String, Offset> _currentPositions = {};

  // --- Back-edge marching ants animation (5s repeating) ---
  late final AnimationController _marchingAntsController;

  // --- Path highlighting ---
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
    _controller.viewportZoomNotifier.value = 0.05;

    _layoutAnimController = AnimationController(
      duration: const Duration(milliseconds: 400),
      vsync: this,
    );
    _layoutAnimation = CurvedAnimation(
      parent: _layoutAnimController,
      curve: Curves.easeOutCubic,
    );
    _layoutAnimation.addListener(_onLayoutAnimationTick);

    _marchingAntsController = AnimationController(
      duration: const Duration(seconds: 5),
      vsync: this,
    );

    _registerPrototypes();
    _analyzeAndLayout();
  }

  /// Analyse topology, determine initial expand state, compute layout.
  void _analyzeAndLayout() {
    _topology = GraphTopologyHelper.analyze(widget.payload);
    _initializeExpandState();
    _processGraphData();
  }

  /// Compute initial expand state: for small graphs expand everything,
  /// for large graphs expand only roots and depth-0 agents.
  void _initializeExpandState() {
    _expandedNodeIds = {};

    if (widget.payload.nodes.length <= 25) {
      // Small graph: expand everything.
      for (final n in widget.payload.nodes) {
        if (_hasChildren(n.id)) {
          _expandedNodeIds.add(n.id);
        }
      }
    } else {
      // Large graph: only expand roots (depth 0).
      for (final rootId in _topology.rootIds) {
        _expandedNodeIds.add(rootId);
      }
    }
  }

  bool _hasChildren(String nodeId) {
    return widget.payload.edges.any((e) => e.sourceId == nodeId);
  }

  void _handleNodeExpand(String nodeId) {
    // Capture old state for animation.
    final oldPositions = Map<String, Offset>.from(_currentPositions);
    final oldVisibleIds = _visibleGraph.nodes.map((n) => n.id).toSet();

    // Toggle expand/collapse.
    if (_expandedNodeIds.contains(nodeId)) {
      _expandedNodeIds.remove(nodeId);
      // Also collapse all descendants to match "collapse subtree" semantics.
      _collapseDescendants(nodeId);
    } else {
      _expandedNodeIds.add(nodeId);
    }

    // Recompute layout.
    _processGraphData();

    // Compute animation transition.
    final newVisibleIds = _visibleGraph.nodes.map((n) => n.id).toSet();
    final childToParent =
        GraphTopologyHelper.buildChildToParent(_visibleGraph.dagEdges);
    // Also include old DAG edges for collapsing nodes' parent lookup.
    final allDagEdges = _topology.dagEdges;
    for (final e in allDagEdges) {
      childToParent.putIfAbsent(e.targetId, () => e.sourceId);
    }

    _transition = GraphTransitionState.compute(
      oldPositions: oldPositions,
      newPositions: _currentPositions,
      oldVisibleIds: oldVisibleIds,
      newVisibleIds: newVisibleIds,
      childToParent: childToParent,
    );

    // Apply start positions for animation.
    for (final entry in _controller.nodes.entries) {
      entry.value.offset = _transition.positionAt(entry.key, 0.0);
    }

    _layoutAnimController.forward(from: 0.0);
    setState(() {});
  }

  /// Remove all descendants of [nodeId] from _expandedNodeIds.
  void _collapseDescendants(String nodeId) {
    final queue = <String>[nodeId];
    final adj = <String, List<String>>{};
    for (final e in _topology.dagEdges) {
      adj.putIfAbsent(e.sourceId, () => []).add(e.targetId);
    }
    while (queue.isNotEmpty) {
      final current = queue.removeAt(0);
      for (final child in (adj[current] ?? [])) {
        _expandedNodeIds.remove(child);
        queue.add(child);
      }
    }
  }

  void _onLayoutAnimationTick() {
    final t = _layoutAnimation.value;
    for (final entry in _controller.nodes.entries) {
      entry.value.offset = _transition.positionAt(entry.key, t);
    }
    if (mounted) setState(() {});
  }

  @override
  void didUpdateWidget(InteractiveGraphCanvas oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.payload != oldWidget.payload) {
      scheduleMicrotask(() {
        if (!mounted) return;
        _analyzeAndLayout();
        setState(() {});
      });
    }
  }

  @override
  void dispose() {
    _layoutTimer?.cancel();
    _layoutAnimController.dispose();
    _marchingAntsController.dispose();
    super.dispose();
  }

  void _registerPrototypes() {
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
        onExecute: (ports, fields, state, forward, put) async {},
      ),
    );
  }

  void _processGraphData({bool force = false}) {
    final payload = widget.payload;
    final nodeHash = payload.nodes.fold(
      0,
      (acc, n) => acc ^ n.id.hashCode ^ n.hasError.hashCode ^ n.executionCount,
    );
    final hash = Object.hash(
      payload.nodes.length,
      payload.edges.length,
      _expandedNodeIds.length,
      _expandedNodeIds.join(','),
      nodeHash,
    );

    if (!force && _cachedHash == hash) return;
    _cachedHash = hash;

    _controller.clear();
    _nodeDataMap.clear();

    if (payload.nodes.isEmpty) {
      _visibleGraph = const VisibleGraph(nodes: [], dagEdges: [], backEdges: []);
      _backEdgePaths = [];
      if (mounted && _cachedHash != -1) setState(() {});
      return;
    }

    // 1. Get visible graph from topology helper.
    _visibleGraph = _topology.getVisibleGraph(_expandedNodeIds);

    for (final n in _visibleGraph.nodes) {
      _nodeDataMap[n.id] = n;
    }

    if (_visibleGraph.nodes.isEmpty) return;

    // 2. Compute positions via layout engine (DAG edges only).
    _currentPositions = GraphLayoutEngine.computePositions(
      nodes: _visibleGraph.nodes,
      dagEdges: _visibleGraph.dagEdges,
    );

    // 3. Calculate edge styling and add fl_nodes.
    _addFlNodes(_visibleGraph.nodes, _visibleGraph.dagEdges);

    // 4. Build back-edge paths for the painter.
    _backEdgePaths = _buildBackEdgePaths(_visibleGraph.backEdges);

    // Start/stop marching ants animation based on whether back-edges exist.
    if (_backEdgePaths.isNotEmpty && !_marchingAntsController.isAnimating) {
      _marchingAntsController.repeat();
    } else if (_backEdgePaths.isEmpty && _marchingAntsController.isAnimating) {
      _marchingAntsController.stop();
    }

    _handleAutoFit();
  }

  void _addFlNodes(List<MultiTraceNode> nodes, List<MultiTraceEdge> dagEdges) {
    var maxCallCount = 1;
    for (final e in dagEdges) {
      if (e.callCount > maxCallCount) maxCallCount = e.callCount;
    }

    for (final n in nodes) {
      final position = _currentPositions[n.id];
      if (position == null) continue;

      final outgoingEdges = dagEdges.where((e) => e.sourceId == n.id).toList();
      final hasOutgoingError = outgoingEdges.any((e) => e.errorCount > 0);

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

      _addFlNode(n.id, position, linkColor, thickness);
    }

    // Add DAG links.
    for (final e in dagEdges) {
      if (_controller.isNodePresent(e.sourceId) &&
          _controller.isNodePresent(e.targetId)) {
        _controller.addLink(e.sourceId, 'out', e.targetId, 'in');
      }
    }
  }

  List<BackEdgePath> _buildBackEdgePaths(List<MultiTraceEdge> backEdges) {
    final paths = <BackEdgePath>[];
    for (var i = 0; i < backEdges.length; i++) {
      final e = backEdges[i];
      final start = _currentPositions[e.sourceId];
      final end = _currentPositions[e.targetId];
      if (start == null || end == null) continue;

      final hasError = e.errorCount > 0;
      paths.add(BackEdgePath(
        start: start,
        end: end,
        color: hasError
            ? AppColors.error.withValues(alpha: 0.6)
            : AppColors.primaryTeal.withValues(alpha: 0.4),
        thickness: 1.5,
        sourceId: e.sourceId,
        targetId: e.targetId,
        edgeIndex: i,
      ));
    }
    return paths;
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
          _controller.setViewportZoom(0.05, absolute: true, animate: true);
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

    final graphKey = ValueKey(_cachedHash);

    return Stack(
      children: [
        // Layer 1: Back-edge painter (BEHIND nodes)
        if (_backEdgePaths.isNotEmpty)
          Positioned.fill(
            child: AnimatedBuilder(
              animation: _marchingAntsController,
              builder: (context, _) => CustomPaint(
                painter: BackEdgePainter(
                  edges: _backEdgePaths,
                  marchingAntsPhase: _marchingAntsController.value,
                  highlightedPath: _highlightedPath,
                ),
              ),
            ),
          ),
        // Layer 2: FlNodeEditorWidget (nodes + DAG edges)
        FlNodeEditorWidget(
          key: graphKey,
          controller: _controller,
          overlay: () => [],
          nodeBuilder: (context, nodeData) {
            final multiTraceNode = _nodeDataMap[nodeData.id];
            if (multiTraceNode == null) return const SizedBox();
            return _buildCustomNode(context, multiTraceNode, nodeData);
          },
        ),
        // Layer 3: Controls overlay
        _buildControls(),
      ],
    );
  }

  Widget _buildControls() {
    return Positioned(
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
          ],
        ),
      ),
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
    for (final n in widget.payload.nodes) {
      if (n.totalTokens > maxTokens) maxTokens = n.totalTokens;
    }
    return maxTokens;
  }

  Color _getTokenHeatmapColor(int tokens, int maxTokens) {
    if (maxTokens <= 0) return Colors.grey;
    final ratio = (tokens / maxTokens).clamp(0.0, 1.0);
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
    final effectiveColor = color ?? Colors.grey;
    final isDimmed =
        _highlightedPath.isNotEmpty && !_highlightedPath.contains(nodeData.id);

    return GestureDetector(
      behavior: HitTestBehavior.translucent,
      onTapDown: (_) {
        final nodeId = nodeData.id;
        if (_lockedSelectionId == nodeId) {
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

    final isExpanded = _expandedNodeIds.contains(node.id);

    final content = Container(
      width: 280,
      constraints: const BoxConstraints(minHeight: 140),
      decoration: BoxDecoration(
        color: const Color(0xFF0D1B2A),
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
                    if (_hasChildren(node.id))
                      GestureDetector(
                        onTap: () => _handleNodeExpand(node.id),
                        child: Icon(
                          isExpanded ? Icons.expand_less : Icons.expand_more,
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
          if (_hasChildren(node.id))
            Positioned(
              bottom: -12,
              left: 0,
              right: 0,
              child: Center(
                child: GestureDetector(
                  onTap: () => _handleNodeExpand(node.id),
                  child: Container(
                    width: 24,
                    height: 24,
                    decoration: BoxDecoration(
                      color: const Color(0xFF0D1B2A),
                      shape: BoxShape.circle,
                      border: Border.all(color: borderColor, width: 1.5),
                    ),
                    child: Icon(
                      isExpanded ? Icons.expand_more : Icons.chevron_right,
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
      borderColor = const Color(0xFFD1C4E9);
    } else {
      borderColor = hasError
          ? const Color(0xFFE53935)
          : const Color(0xFF673AB7);
    }
    const iconData = Icons.auto_awesome;

    final content = Container(
      width: 240,
      constraints: const BoxConstraints(minHeight: 110),
      decoration: BoxDecoration(
        color: const Color(0xFF1A1025),
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
      borderColor = Colors.white;
    } else if (forceColor != null) {
      borderColor = forceColor;
    } else {
      borderColor = hasError
          ? const Color(0xFFE53935)
          : const Color(0xFF546E7A);
    }
    const iconData = Icons.build;

    final content = Container(
      width: 200,
      constraints: const BoxConstraints(minHeight: 90),
      decoration: BoxDecoration(
        color: const Color(0xFF181C1F),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: borderColor, width: hasError ? 2 : 1),
      ),
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Padding(
            padding: const EdgeInsets.all(8),
            child: Column(
              mainAxisSize: MainAxisSize.min,
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

  Widget _buildMetricsRow(MultiTraceNode node, Color accentColor) {
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
