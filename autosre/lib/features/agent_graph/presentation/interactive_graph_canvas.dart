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

  // Map to store the actual data associated with each node ID
  final Map<String, MultiTraceNode> _nodeDataMap = {};

  // Cache layout to avoid re-calculating on every build
  int _cachedHash = -1;

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
    _processGraphData();
  }

  @override
  void didUpdateWidget(InteractiveGraphCanvas oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.payload != oldWidget.payload) {
      _processGraphData();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
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
        ],
        onExecute: (ports, fields, state, forward, put) async {
          // No-op for visualization
        },
      ),
    );
  }

  void _processGraphData() {
    final payload = widget.payload;
    final hash = Object.hash(payload.nodes.length, payload.edges.length);
    if (_cachedHash == hash) return;
    _cachedHash = hash;

    // 1. Clear existing
    _controller.clear();
    _nodeDataMap.clear();

    if (payload.nodes.isEmpty) return;

    // 2. Map nodes for quick lookup
    final nodeMap = {for (var n in payload.nodes) n.id: n};
    _nodeDataMap.addAll(nodeMap);

    // 3. Run Sugiyama Layout
    _sugiyamaLayout(payload);

    // Debug: Print node positions
    for (var node in _controller.nodes.values) {
      debugPrint('NODE: ${node.id} at ${node.offset}');
    }
  }

  void _sugiyamaLayout(MultiTraceGraphPayload payload) {
    if (payload.nodes.isEmpty) return;

    final graph = gv.Graph()..isTree = false;
    final gvNodes = <String, gv.Node>{};

    // Create GraphView nodes and calculate max call count for edge scaling
    var maxCallCount = 1;
    for (var e in payload.edges) {
      if (e.callCount > maxCallCount) maxCallCount = e.callCount;
    }

    for (var n in payload.nodes) {
      final node = gv.Node.Id(n.id);
      gvNodes[n.id] = node;
      graph.addNode(node);
    }

    // Create GraphView edges
    for (var e in payload.edges) {
      if (gvNodes.containsKey(e.sourceId) && gvNodes.containsKey(e.targetId)) {
        graph.addEdge(gvNodes[e.sourceId]!, gvNodes[e.targetId]!);
      }
    }

    // Configure Sugiyama
    final builder = gv.SugiyamaConfiguration()
      ..orientation = gv.SugiyamaConfiguration.ORIENTATION_LEFT_RIGHT
      ..levelSeparation = 150
      ..nodeSeparation = 200;

    final algorithm = gv.SugiyamaAlgorithm(builder);
    algorithm.run(graph, 100, 100); // Shift X, Y

    // Add nodes to FL Editor with calculated positions
    for (var n in payload.nodes) {
      final gvNode = gvNodes[n.id];
      if (gvNode != null) {
        // Collect all outgoing edges from this node
        final outgoingEdges = payload.edges
            .where((e) => e.sourceId == n.id)
            .toList();

        // Find if any outgoing edge has errors to color the port/links
        final hasOutgoingError = outgoingEdges.any((e) => e.errorCount > 0);

        // Find max call count for the outgoing edges from this node specifically to scale the thickness
        var nodeMaxCallCount = 1;
        if (outgoingEdges.isNotEmpty) {
          nodeMaxCallCount = outgoingEdges
              .map((e) => e.callCount)
              .reduce((a, b) => a > b ? a : b);
        }

        var thickness = 2.0;
        if (maxCallCount > 1) {
          // Scale from 2.0 to 6.0 based on call count relative to global max
          thickness = 2.0 + (4.0 * (nodeMaxCallCount / maxCallCount));
        }

        final linkColor = hasOutgoingError
            ? AppColors.error
            : AppColors.primaryTeal.withValues(alpha: 0.6);

        _addFlNode(n.id, Offset(gvNode.x, gvNode.y), linkColor, thickness);
      }
    }

    // Add links
    for (var e in payload.edges) {
      if (_controller.isNodePresent(e.sourceId) &&
          _controller.isNodePresent(e.targetId)) {
        _controller.addLink(e.sourceId, 'out', e.targetId, 'in');
      }
    }

    // Auto-center graph
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_controller.nodes.isNotEmpty) {
        _controller.focusNodesById(
          _controller.nodes.keys.toSet(),
          animate: false,
        );
        // Deselect all after focusing
        _controller.clearSelection();
      }
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

    return FlNodeEditorWidget(
      controller: _controller,
      overlay: () => [], // No overlays for now
      nodeBuilder: (context, nodeData) {
        final multiTraceNode = _nodeDataMap[nodeData.id];
        if (multiTraceNode == null) return const SizedBox();

        return _buildCustomNode(context, multiTraceNode, nodeData);
      },
      // Hide default headers/fields since we use custom nodeBuilder
    );
  }

  Widget _buildCustomNode(
    BuildContext context,
    MultiTraceNode node,
    FlNodeDataModel nodeData,
  ) {
    final isSelected = nodeData.state.isSelected;
    final isAgent = node.type.toLowerCase() == 'agent';
    final color = _nodeColor(node.type);

    // Find ports
    final inputPort = nodeData.ports['in'];
    final outPort = nodeData.ports['out'];

    Widget content;
    if (isAgent || node.type.toLowerCase() == 'sub_agent') {
      // Pill shape for Agents
      content = Container(
        width: 160,
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: AppColors.backgroundCard,
          borderRadius: BorderRadius.circular(32),
          border: Border.all(
            color: isSelected
                ? AppColors.primaryTeal
                : (node.hasError
                      ? AppColors.error
                      : color.withValues(alpha: 0.5)),
            width: isSelected ? 2 : 1,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.2),
              blurRadius: 4,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircleAvatar(
              radius: 12,
              backgroundColor: color.withValues(alpha: 0.2),
              child: Icon(_nodeIcon(node.type), size: 14, color: color),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    node.id,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.bold,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                  Text(
                    '${_formatTokens(node.totalTokens)} toks',
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.6),
                      fontSize: 10,
                    ),
                  ),
                ],
              ),
            ),
            if (node.hasError) ...[
              const SizedBox(width: 4),
              const Icon(Icons.error, color: AppColors.error, size: 14),
            ],
          ],
        ),
      );
    } else if (node.type.toLowerCase() == 'llm' ||
        node.type.toLowerCase() == 'llm_model') {
      // Distinct Card for LLMs
      // Try to parse out the model name. Often IDs are like "generate_content gemini-2.5-flash"
      var displayId = node.id;
      final parts = node.id.split(' ');
      if (parts.length > 1 && parts.first.contains('generate_content')) {
        displayId = parts.sublist(1).join(' '); // e.g., "gemini-2.5-flash"
      }
      content = Container(
        width: 150,
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        decoration: BoxDecoration(
          color: AppColors.backgroundCard,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isSelected
                ? AppColors.secondaryPurple
                : (node.hasError
                      ? AppColors.error
                      : AppColors.secondaryPurple.withValues(alpha: 0.4)),
            width: isSelected ? 2 : 1,
          ),
          boxShadow: [
            if (isSelected)
              BoxShadow(
                color: AppColors.secondaryPurple.withValues(alpha: 0.2),
                blurRadius: 8,
                spreadRadius: 2,
              ),
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.2),
              blurRadius: 4,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(_nodeIcon(node.type), size: 14, color: color),
                const SizedBox(width: 6),
                const Text(
                  'LLM',
                  style: TextStyle(
                    color: Colors.white70,
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                if (node.hasError) ...[
                  const Spacer(),
                  const Icon(Icons.error, color: AppColors.error, size: 12),
                ],
              ],
            ),
            const SizedBox(height: 6),
            Text(
              displayId,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            if (node.totalTokens > 0) ...[
              const SizedBox(height: 4),
              Text(
                '${_formatTokens(node.totalTokens)} toks',
                style: TextStyle(
                  color: AppColors.secondaryPurple.withValues(alpha: 0.8),
                  fontSize: 10,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ]
          ],
        ),
      );
    } else {
      // Distinct Card for Tools
      content = Container(
        width: 140,
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: AppColors.backgroundCard,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isSelected
                ? AppColors.warning
                : (node.hasError ? AppColors.error : AppColors.surfaceBorder),
            width: isSelected ? 2 : 1,
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.2),
              blurRadius: 2,
              offset: const Offset(0, 1),
            ),
          ],
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(_nodeIcon(node.type), size: 14, color: color),
                if (node.hasError) ...[
                  const SizedBox(width: 4),
                  const Icon(Icons.error, color: AppColors.error, size: 12),
                ],
              ],
            ),
            const SizedBox(height: 6),
            Text(
              node.id,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 11,
                fontWeight: FontWeight.w500,
              ),
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            if (node.totalTokens > 0) ...[
              const SizedBox(height: 4),
              Text(
                '${_formatTokens(node.totalTokens)} toks',
                style: const TextStyle(color: Colors.white54, fontSize: 10),
              ),
            ]
          ],
        ),
      );
    }

    // Wrap content with ports (Left -> Right flow)
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
          // Input Port (Left)
          if (inputPort != null)
            Container(
              key: inputPort.key,
              width: 12,
              height: 12,
              margin: const EdgeInsets.only(right: 4),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.white12, // Subtle visible target
                border: Border.all(color: Colors.white24, width: 1),
              ),
            ),

          content,

          // Output Port (Right)
          if (outPort != null)
            Container(
              key: outPort.key,
              width: 12,
              height: 12,
              margin: const EdgeInsets.only(left: 4),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppColors.primaryTeal.withValues(alpha: 0.8),
                border: Border.all(color: Colors.white, width: 1.5),
              ),
            ),
        ],
      ),
    );
  }

  Color _nodeColor(String type) {
    switch (type.toLowerCase()) {
      case 'agent':
        return AppColors.primaryTeal;
      case 'tool':
        return AppColors.warning;
      case 'llm':
        return AppColors.secondaryPurple;
      case 'sub_agent':
        return AppColors.primaryCyan;
      default:
        return Colors.grey;
    }
  }

  IconData _nodeIcon(String type) {
    switch (type.toLowerCase()) {
      case 'agent':
      case 'sub_agent':
        return Icons.psychology;
      case 'tool':
        return Icons.build;
      case 'llm':
        return Icons.auto_awesome;
      default:
        return Icons.circle;
    }
  }

  String _formatTokens(int tokens) {
    if (tokens >= 1000000) return '${(tokens / 1000000).toStringAsFixed(1)}M';
    if (tokens >= 1000) return '${(tokens / 1000).toStringAsFixed(1)}K';
    return '$tokens';
  }
}
