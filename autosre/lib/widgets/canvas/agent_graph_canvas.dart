import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:graphview/GraphView.dart';
import '../../models/adk_schema.dart';
import '../../theme/app_theme.dart';

/// Agent dependency graph widget using graphview package.
///
/// Displays agents, tools, LLM models, and their relationships as a
/// directed graph with Sugiyama (hierarchical) or force-directed layout.
class AgentGraphCanvas extends StatefulWidget {
  final AgentGraphData data;

  const AgentGraphCanvas({super.key, required this.data});

  @override
  State<AgentGraphCanvas> createState() => _AgentGraphCanvasState();
}

class _AgentGraphCanvasState extends State<AgentGraphCanvas> {
  bool _useSugiyama = true;
  String? _selectedNodeId;

  // Cached graph and algorithm to avoid O(n²-n³) recomputation per frame.
  Graph? _cachedGraph;
  Algorithm? _cachedAlgorithm;
  bool _cachedUseSugiyama = true;
  int _cachedNodeCount = -1;
  int _cachedEdgeCount = -1;

  Color _nodeColor(String type) {
    switch (type) {
      case 'user':
        return Colors.white;
      case 'agent':
        return AppColors.primaryTeal;
      case 'sub_agent':
        return AppColors.primaryCyan;
      case 'tool':
        return AppColors.warning;
      case 'llm_model':
        return AppColors.secondaryPurple;
      default:
        return Colors.grey;
    }
  }

  IconData _nodeIcon(String type) {
    switch (type) {
      case 'user':
        return Icons.person;
      case 'agent':
        return Icons.smart_toy;
      case 'sub_agent':
        return Icons.smart_toy_outlined;
      case 'tool':
        return Icons.build;
      case 'llm_model':
        return Icons.auto_awesome;
      default:
        return Icons.circle;
    }
  }

  /// Rebuild the cached graph/algorithm only when data or layout mode changes.
  void _ensureGraphCached() {
    final data = widget.data;
    final needsRebuild = _cachedGraph == null ||
        _cachedNodeCount != data.nodes.length ||
        _cachedEdgeCount != data.edges.length ||
        _cachedUseSugiyama != _useSugiyama;
    if (!needsRebuild) return;

    _cachedGraph = _buildGraph(data);
    _cachedNodeCount = data.nodes.length;
    _cachedEdgeCount = data.edges.length;
    _cachedUseSugiyama = _useSugiyama;

    if (_useSugiyama) {
      final sugiyamaConfig = SugiyamaConfiguration()
        ..bendPointShape = CurvedBendPointShape(curveLength: 20)
        ..nodeSeparation = 40
        ..levelSeparation = 60
        ..orientation = SugiyamaConfiguration.ORIENTATION_TOP_BOTTOM;
      _cachedAlgorithm = SugiyamaAlgorithm(sugiyamaConfig);
    } else {
      _cachedAlgorithm = FruchtermanReingoldAlgorithm(
        FruchtermanReingoldConfiguration(),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final data = widget.data;
    if (data.nodes.isEmpty) {
      return const Center(
        child: Text('No graph data', style: TextStyle(color: Colors.white70)),
      );
    }

    _ensureGraphCached();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildToolbar(data),
        const SizedBox(height: 4),
        _buildLegend(),
        const SizedBox(height: 4),
        Expanded(
          child: InteractiveViewer(
            constrained: false,
            boundaryMargin: const EdgeInsets.all(100),
            minScale: 0.3,
            maxScale: 2.0,
            child: GraphView(
              graph: _cachedGraph!,
              algorithm: _cachedAlgorithm!,
              paint: Paint()
                ..color = Colors.white24
                ..strokeWidth = 1
                ..style = PaintingStyle.stroke,
              builder: (Node node) {
                final nodeId = node.key!.value as String;
                return _buildNodeWidget(data, nodeId);
              },
            ),
          ),
        ),
        if (_selectedNodeId != null) _buildNodeDetail(data),
      ],
    );
  }

  Graph _buildGraph(AgentGraphData data) {
    final graph = Graph()..isTree = false;
    final nodeMap = <String, Node>{};

    for (final gNode in data.nodes) {
      final node = Node.Id(gNode.id);
      nodeMap[gNode.id] = node;
      graph.addNode(node);
    }

    for (final edge in data.edges) {
      final source = nodeMap[edge.sourceId];
      final target = nodeMap[edge.targetId];
      if (source != null && target != null) {
        final paint = Paint()
          ..color = edge.hasError
              ? Colors.redAccent.withValues(alpha: 0.7)
              : Colors.white.withValues(alpha: 0.3)
          ..strokeWidth = math.min(edge.callCount.toDouble(), 4)
          ..style = PaintingStyle.stroke;
        graph.addEdge(source, target, paint: paint);
      }
    }

    return graph;
  }

  Widget _buildToolbar(AgentGraphData data) {
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
          Text(
            data.rootAgentName ?? 'Agent Graph',
            style: const TextStyle(
              color: Colors.white,
              fontSize: 15,
              fontWeight: FontWeight.w600,
            ),
          ),
          const Spacer(),
          _layoutToggle(),
        ],
      ),
    );
  }

  Widget _layoutToggle() {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _toggleButton(
            'Hierarchical',
            _useSugiyama,
            () => setState(() => _useSugiyama = true),
          ),
          _toggleButton(
            'Force',
            !_useSugiyama,
            () => setState(() => _useSugiyama = false),
          ),
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
      ('User', 'user'),
      ('Agent', 'agent'),
      ('Tool', 'tool'),
      ('LLM', 'llm_model'),
    ];
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: types.map((t) {
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
        }).toList(),
      ),
    );
  }

  Widget _buildNodeWidget(AgentGraphData data, String nodeId) {
    final gNode = data.nodes.firstWhere(
      (n) => n.id == nodeId,
      orElse: () => AgentGraphNode(
        id: nodeId,
        label: nodeId,
        type: 'unknown',
        hasError: false,
      ),
    );
    final isSelected = _selectedNodeId == nodeId;
    final color = _nodeColor(gNode.type);

    return GestureDetector(
      onTap: () => setState(() => _selectedNodeId = isSelected ? null : nodeId),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isSelected ? color : color.withValues(alpha: 0.4),
            width: isSelected ? 2 : 1,
          ),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(_nodeIcon(gNode.type), color: color, size: 20),
            const SizedBox(height: 4),
            Text(
              gNode.label,
              style: TextStyle(
                color: gNode.hasError ? Colors.redAccent : Colors.white,
                fontSize: 11,
                fontWeight: FontWeight.w500,
              ),
            ),
            if (gNode.callCount != null && gNode.callCount! > 0)
              Text(
                '${gNode.callCount}x',
                style: const TextStyle(color: Colors.white38, fontSize: 9),
              ),
            if (gNode.totalTokens != null && gNode.totalTokens! > 0)
              Text(
                _formatTokens(gNode.totalTokens!),
                style: TextStyle(
                  color: color.withValues(alpha: 0.8),
                  fontSize: 9,
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildNodeDetail(AgentGraphData data) {
    final gNode = data.nodes.firstWhere(
      (n) => n.id == _selectedNodeId,
      orElse: () => AgentGraphNode(
        id: _selectedNodeId!,
        label: _selectedNodeId!,
        type: 'unknown',
        hasError: false,
      ),
    );

    final relatedEdges = data.edges
        .where(
          (e) => e.sourceId == _selectedNodeId || e.targetId == _selectedNodeId,
        )
        .toList();

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.all(8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.black26,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: _nodeColor(gNode.type).withValues(alpha: 0.4),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Icon(
                _nodeIcon(gNode.type),
                color: _nodeColor(gNode.type),
                size: 16,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  gNode.label,
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                  ),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.close, size: 16, color: Colors.white54),
                onPressed: () => setState(() => _selectedNodeId = null),
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            'Type: ${gNode.type}',
            style: const TextStyle(color: Colors.white54, fontSize: 11),
          ),
          if (gNode.callCount != null)
            Text(
              'Calls: ${gNode.callCount}',
              style: const TextStyle(color: Colors.white54, fontSize: 11),
            ),
          if (gNode.totalTokens != null)
            Text(
              'Tokens: ${_formatTokens(gNode.totalTokens!)}',
              style: const TextStyle(color: Colors.white54, fontSize: 11),
            ),
          if (relatedEdges.isNotEmpty) ...[
            const SizedBox(height: 6),
            const Text(
              'Connections:',
              style: TextStyle(color: Colors.white38, fontSize: 10),
            ),
            ...relatedEdges
                .take(5)
                .map(
                  (e) => Text(
                    '  ${e.sourceId} -[${e.label}]-> ${e.targetId} (${e.callCount}x, ${e.avgDurationMs.toStringAsFixed(0)}ms)',
                    style: const TextStyle(color: Colors.white30, fontSize: 10),
                  ),
                ),
          ],
        ],
      ),
    );
  }

  String _formatTokens(int tokens) {
    if (tokens >= 1000000) {
      return '${(tokens / 1000000).toStringAsFixed(1)}M tok';
    }
    if (tokens >= 1000) return '${(tokens / 1000).toStringAsFixed(1)}K tok';
    return '$tokens tok';
  }
}
