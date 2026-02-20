import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:graphview/GraphView.dart';

import '../../../theme/app_theme.dart';
import '../domain/models.dart';

/// Visualizes an aggregated multi-trace agent graph using the graphview package.
///
/// Implements progressive disclosure:
/// - Default: Node label + type icon, edge color-coded by error rate.
/// - Hover: Tooltip with secondary metrics (tokens, duration).
/// - Click: Emits [onNodeSelected] / [onEdgeSelected] for detail panel.
class MultiTraceGraphCanvas extends StatefulWidget {
  final MultiTraceGraphPayload payload;
  final ValueChanged<MultiTraceNode>? onNodeSelected;
  final ValueChanged<MultiTraceEdge>? onEdgeSelected;
  final VoidCallback? onSelectionCleared;

  const MultiTraceGraphCanvas({
    super.key,
    required this.payload,
    this.onNodeSelected,
    this.onEdgeSelected,
    this.onSelectionCleared,
  });

  @override
  State<MultiTraceGraphCanvas> createState() => _MultiTraceGraphCanvasState();
}

class _MultiTraceGraphCanvasState extends State<MultiTraceGraphCanvas> {
  String? _selectedNodeId;
  bool _useSugiyama = true;
  bool _showListView = false;

  Graph? _cachedGraph;
  Algorithm? _cachedAlgorithm;
  bool _cachedLayout = true;
  int _cachedHash = -1;

  final TransformationController _transformationController =
      TransformationController();

  @override
  void dispose() {
    _transformationController.dispose();
    super.dispose();
  }

  // ---------------------------------------------------------------------------
  // Graph caching
  // ---------------------------------------------------------------------------

  void _ensureGraphCached() {
    final hash = Object.hash(
      widget.payload.nodes.length,
      widget.payload.edges.length,
      _useSugiyama,
    );
    if (_cachedGraph != null &&
        _cachedHash == hash &&
        _cachedLayout == _useSugiyama) {
      return;
    }
    _cachedHash = hash;
    _cachedLayout = _useSugiyama;

    _cachedGraph = _buildGraph();

    if (_useSugiyama) {
      final config = SugiyamaConfiguration()
        ..bendPointShape = CurvedBendPointShape(curveLength: 20)
        ..nodeSeparation = 100
        ..levelSeparation = 150
        ..orientation = SugiyamaConfiguration.ORIENTATION_LEFT_RIGHT;
      _cachedAlgorithm = SugiyamaAlgorithm(config);
    } else {
      _cachedAlgorithm = FruchtermanReingoldAlgorithm(
        FruchtermanReingoldConfiguration(),
      );
    }
  }

  Graph _buildGraph() {
    final graph = Graph()..isTree = false;
    final nodeMap = <String, Node>{};

    for (final n in widget.payload.nodes) {
      final node = Node.Id(n.id);
      nodeMap[n.id] = node;
      graph.addNode(node);
    }

    for (final e in widget.payload.edges) {
      final source = nodeMap[e.sourceId];
      final target = nodeMap[e.targetId];
      if (source == null || target == null) continue;

      // Edge thickness proportional to call count (traffic).
      final thickness = _edgeThickness(e.callCount);
      final color = _edgeColor(e.errorRatePct);

      final paint = Paint()
        ..color = color
        ..strokeWidth = thickness
        ..style = PaintingStyle.stroke;
      graph.addEdge(source, target, paint: paint);
    }

    return graph;
  }

  // ---------------------------------------------------------------------------
  // Visual mapping
  // ---------------------------------------------------------------------------

  Color _nodeColor(String type) {
    switch (type.toLowerCase()) {
      case 'agent':
        return AppColors.primaryTeal;
      case 'tool':
        return AppColors.warning;
      case 'llm':
      case 'llm_model':
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
      case 'llm_model':
        return Icons.auto_awesome;
      default:
        return Icons.circle;
    }
  }

  Color _edgeColor(double errorRatePct) {
    if (errorRatePct <= 0) return Colors.white.withValues(alpha: 0.25);
    if (errorRatePct < 10) return Colors.orange.withValues(alpha: 0.6);
    return AppColors.error.withValues(alpha: 0.8);
  }

  double _edgeThickness(int callCount) {
    if (callCount <= 0) return 1.0;
    // Log scale: 1-6px range based on calls.
    return math.min(1.0 + math.log(callCount + 1), 6.0);
  }

  String _formatTokens(int tokens) {
    if (tokens >= 1000000) return '${(tokens / 1000000).toStringAsFixed(1)}M';
    if (tokens >= 1000) return '${(tokens / 1000).toStringAsFixed(1)}K';
    return '$tokens';
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final payload = widget.payload;
    if (payload.nodes.isEmpty) {
      return const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.account_tree_outlined, color: Colors.white24, size: 48),
            SizedBox(height: 12),
            Text(
              'No graph data.\nRun a query to visualize agent traces.',
              textAlign: TextAlign.center,
              style: TextStyle(color: Colors.white38, fontSize: 13),
            ),
          ],
        ),
      );
    }

    _ensureGraphCached();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildToolbar(),
        const SizedBox(height: 4),
        _buildLegend(),
        const SizedBox(height: 4),
        Expanded(
          child: _showListView ? _buildEdgeListView() : _buildGraphView(),
        ),
      ],
    );
  }

  Widget _buildGraphView() {
    return Stack(
      children: [
        Positioned.fill(
          child: InteractiveViewer(
            transformationController: _transformationController,
            constrained: false,
            boundaryMargin: const EdgeInsets.all(120),
            minScale: 0.2,
            maxScale: 3.0,
            child: GraphView(
              graph: _cachedGraph!,
              algorithm: _cachedAlgorithm!,
              paint: Paint()
                ..color = Colors.white24
                ..strokeWidth = 1
                ..style = PaintingStyle.stroke,
              builder: (Node node) {
                final nodeId = node.key!.value as String;
                return _buildNodeWidget(nodeId);
              },
            ),
          ),
        ),
        Positioned(bottom: 16, right: 16, child: _buildZoomControls()),
      ],
    );
  }

  Widget _buildEdgeListView() {
    final edges = widget.payload.edges.toList()
      ..sort((a, b) => b.callCount.compareTo(a.callCount));

    if (edges.isEmpty) {
      return const Center(
        child: Text(
          'No edges to display.',
          style: TextStyle(color: Colors.white38),
        ),
      );
    }

    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: edges.length,
      separatorBuilder: (context, index) => const SizedBox(height: 8),
      itemBuilder: (context, index) {
        final edge = edges[index];
        return InkWell(
          onTap: () => widget.onEdgeSelected?.call(edge),
          borderRadius: BorderRadius.circular(8),
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.04),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: edge.errorRatePct > 0
                    ? AppColors.error.withValues(alpha: 0.3)
                    : AppColors.surfaceBorder,
              ),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            edge.sourceId,
                            style: const TextStyle(
                              color: Colors.white70,
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const Padding(
                            padding: EdgeInsets.symmetric(horizontal: 6),
                            child: Icon(
                              Icons.arrow_forward,
                              size: 12,
                              color: Colors.white38,
                            ),
                          ),
                          Text(
                            edge.targetId,
                            style: const TextStyle(
                              color: Colors.white70,
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${edge.callCount} calls · ${edge.uniqueSessions} sessions · ${_formatTokens(edge.edgeTokens)} tokens',
                        style: const TextStyle(
                          color: Colors.white38,
                          fontSize: 10,
                        ),
                      ),
                    ],
                  ),
                ),
                if (edge.errorRatePct > 0)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 6,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.error.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      '${edge.errorRatePct.toStringAsFixed(1)}% err',
                      style: const TextStyle(
                        color: AppColors.error,
                        fontSize: 10,
                      ),
                    ),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }

  // ---------------------------------------------------------------------------
  // Toolbar, Legend, & Controls
  // ---------------------------------------------------------------------------

  Widget _buildZoomControls() {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.backgroundCard.withValues(alpha: 0.9),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.surfaceBorder),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.2),
            blurRadius: 8,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            icon: const Icon(Icons.add, size: 20, color: Colors.white70),
            onPressed: () => _zoom(1.2),
            tooltip: 'Zoom In',
          ),
          const Divider(height: 1, color: AppColors.surfaceBorder),
          IconButton(
            icon: const Icon(Icons.remove, size: 20, color: Colors.white70),
            onPressed: () => _zoom(0.8),
            tooltip: 'Zoom Out',
          ),
          const Divider(height: 1, color: AppColors.surfaceBorder),
          IconButton(
            icon: const Icon(Icons.crop_free, size: 20, color: Colors.white70),
            onPressed: () {
              _transformationController.value = Matrix4.identity();
            },
            tooltip: 'Reset View',
          ),
        ],
      ),
    );
  }

  void _zoom(double factor) {
    // Current scale is determined by the matrix.
    // Ensure we don't go past minScale (0.2) or maxScale (3.0).
    final currentScale = _transformationController.value.getMaxScaleOnAxis();
    if (factor > 1.0 && currentScale * factor > 3.0) {
      factor = 3.0 / currentScale;
    }
    if (factor < 1.0 && currentScale * factor < 0.2) {
      factor = 0.2 / currentScale;
    }

    final matrix = _transformationController.value.clone();
    matrix.scaleByDouble(factor, factor, 1.0, 1.0);
    _transformationController.value = matrix;
  }

  Widget _buildToolbar() {
    final nodeCount = widget.payload.nodes.length;
    final edgeCount = widget.payload.edges.length;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        children: [
          const Icon(
            Icons.account_tree,
            color: AppColors.primaryCyan,
            size: 18,
          ),
          const SizedBox(width: 8),
          const Text(
            'Multi-Trace Agent Graph',
            style: TextStyle(
              color: Colors.white,
              fontSize: 15,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Text(
              '$nodeCount nodes · $edgeCount edges',
              style: const TextStyle(color: Colors.white38, fontSize: 10),
            ),
          ),
          const Spacer(),
          _buildViewToggle(),
          const SizedBox(width: 12),
          _buildLayoutToggle(),
        ],
      ),
    );
  }

  Widget _buildViewToggle() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _toggleIconButton(Icons.account_tree_outlined, !_showListView, () {
            setState(() => _showListView = false);
          }, 'Graph View'),
          _toggleIconButton(Icons.list, _showListView, () {
            setState(() => _showListView = true);
          }, 'Edge List'),
        ],
      ),
    );
  }

  Widget _toggleIconButton(
    IconData icon,
    bool active,
    VoidCallback onTap,
    String tooltip,
  ) {
    return InkWell(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: active
              ? AppColors.primaryTeal.withValues(alpha: 0.3)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(4),
        ),
        child: Icon(
          icon,
          size: 16,
          color: active ? Colors.white : Colors.white38,
        ),
      ),
    );
  }

  Widget _buildLayoutToggle() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _toggleButton('Hierarchical', _useSugiyama, () {
            setState(() => _useSugiyama = true);
          }),
          _toggleButton('Force', !_useSugiyama, () {
            setState(() => _useSugiyama = false);
          }),
        ],
      ),
    );
  }

  Widget _toggleButton(String label, bool active, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: active
              ? AppColors.primaryTeal.withValues(alpha: 0.3)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: active ? Colors.white : Colors.white38,
            fontSize: 11,
          ),
        ),
      ),
    );
  }

  Widget _buildLegend() {
    const types = [
      ('Agent', 'agent'),
      ('Sub-agent', 'sub_agent'),
      ('Tool', 'tool'),
      ('LLM', 'llm'),
    ];
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          ...types.map((t) {
            return Padding(
              padding: const EdgeInsets.only(right: 14),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(_nodeIcon(t.$2), color: _nodeColor(t.$2), size: 12),
                  const SizedBox(width: 3),
                  Text(
                    t.$1,
                    style: const TextStyle(color: Colors.white54, fontSize: 10),
                  ),
                ],
              ),
            );
          }),
          const SizedBox(width: 12),
          Container(width: 16, height: 2, color: Colors.white24),
          const SizedBox(width: 4),
          const Text(
            'OK',
            style: TextStyle(color: Colors.white38, fontSize: 9),
          ),
          const SizedBox(width: 8),
          Container(
            width: 16,
            height: 2,
            color: AppColors.error.withValues(alpha: 0.8),
          ),
          const SizedBox(width: 4),
          const Text(
            'Errors',
            style: TextStyle(color: Colors.white38, fontSize: 9),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Node widget
  // ---------------------------------------------------------------------------

  Widget _buildNodeWidget(String nodeId) {
    final node = widget.payload.nodes.firstWhere(
      (n) => n.id == nodeId,
      orElse: () => MultiTraceNode(id: nodeId, type: 'unknown'),
    );
    final isSelected = _selectedNodeId == nodeId;
    final color = _nodeColor(node.type);

    // Scale node width based on execution count
    // Base 80, max 200. Log scale.
    final count = node.executionCount > 0 ? node.executionCount : 1;
    final widthScale = math.min(1.0 + math.log(count) * 0.3, 2.5);
    final width = 80.0 * widthScale;

    return Tooltip(
      message:
          '${node.label ?? node.id}\n'
          'Type: ${node.type}\n'
          'Calls: ${node.executionCount}\n'
          'Errors: ${node.errorCount}\n'
          'Tokens: ${_formatTokens(node.totalTokens)}',
      waitDuration: const Duration(milliseconds: 400),
      child: GestureDetector(
        onTap: () {
          setState(() {
            if (_selectedNodeId == nodeId) {
              _selectedNodeId = null;
              widget.onSelectionCleared?.call();
            } else {
              _selectedNodeId = nodeId;
              widget.onNodeSelected?.call(node);
            }
          });
        },
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          constraints: BoxConstraints(minWidth: width, maxWidth: width * 2),
          decoration: BoxDecoration(
            color: color.withValues(alpha: isSelected ? 0.25 : 0.12),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(
              color: node.hasError
                  ? AppColors.error
                  : isSelected
                  ? color
                  : color.withValues(alpha: 0.4),
              width: node.hasError || isSelected ? 2 : 1,
            ),
            boxShadow: isSelected
                ? [
                    BoxShadow(
                      color: color.withValues(alpha: 0.3),
                      blurRadius: 12,
                      spreadRadius: 1,
                    ),
                  ]
                : null,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(_nodeIcon(node.type), color: color, size: 20),
              const SizedBox(height: 4),
              Text(
                node.label ?? node.id,
                style: TextStyle(
                  color: node.hasError ? AppColors.error : Colors.white,
                  fontSize: 11,
                  fontWeight: FontWeight.w500,
                ),
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              if (node.isRoot)
                Container(
                  margin: const EdgeInsets.only(top: 3),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 4,
                    vertical: 1,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.primaryCyan.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: const Text(
                    'ROOT',
                    style: TextStyle(
                      color: AppColors.primaryCyan,
                      fontSize: 8,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
