import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:graphview/GraphView.dart';
import '../../models/adk_schema.dart';
import '../../theme/app_theme.dart';

/// Agent dependency graph with **progressive disclosure**.
///
/// Initially only the user node and root agents are shown. Expanding an agent
/// reveals its scoped children (tools, LLM models, sub-agents). Sub-agents can
/// be expanded further to reveal their own scope.
///
/// Visual hints — a chevron icon and a children-count badge — indicate
/// expandable nodes. Animated transitions smooth the graph rebuilds.
class AgentGraphCanvas extends StatefulWidget {
  final AgentGraphData data;

  const AgentGraphCanvas({super.key, required this.data});

  @override
  State<AgentGraphCanvas> createState() => _AgentGraphCanvasState();
}

class _AgentGraphCanvasState extends State<AgentGraphCanvas>
    with SingleTickerProviderStateMixin {
  bool _useSugiyama = true;
  String? _selectedNodeId;

  /// Set of agent node IDs whose children are currently visible.
  final Set<String> _expandedAgentIds = {};

  // Cached graph and algorithm to avoid O(n²-n³) recomputation per frame.
  Graph? _cachedGraph;
  Algorithm? _cachedAlgorithm;
  bool _cachedUseSugiyama = true;
  int _cachedNodeCount = -1;
  int _cachedEdgeCount = -1;
  int _cachedExpandedHash = -1;

  late AnimationController _animController;
  late Animation<double> _fadeAnim;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
    );
    _fadeAnim = CurvedAnimation(
      parent: _animController,
      curve: Curves.easeInOut,
    );
    _animController.value = 1.0;

    // Auto-expand the root agent when there is exactly one.
    _autoExpandSingleRoot();
  }

  @override
  void didUpdateWidget(AgentGraphCanvas oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.data != widget.data) {
      _expandedAgentIds.clear();
      _autoExpandSingleRoot();
    }
  }

  @override
  void dispose() {
    _animController.dispose();
    super.dispose();
  }

  /// If there is exactly one root agent, expand it by default so the user
  /// immediately sees the first level of detail.
  void _autoExpandSingleRoot() {
    final roots = widget.data.nodes.where(
      (n) =>
          n.type == 'agent' &&
          n.parentAgentId == null &&
          n.id != 'user' &&
          n.expandable,
    );
    if (roots.length == 1) {
      _expandedAgentIds.add(roots.first.id);
    }
  }

  // ---------------------------------------------------------------------------
  // Visibility filtering
  // ---------------------------------------------------------------------------

  /// A node is visible when:
  /// - it has no parent agent (user or root agents), **or**
  /// - its parent agent is currently expanded.
  bool _isNodeVisible(AgentGraphNode n) {
    if (n.parentAgentId == null) return true;
    return _expandedAgentIds.contains(n.parentAgentId);
  }

  List<AgentGraphNode> _visibleNodes() {
    return widget.data.nodes.where(_isNodeVisible).toList();
  }

  /// An edge is visible when both its source and target nodes are visible.
  List<AgentGraphEdge> _visibleEdges(Set<String> visibleIds) {
    return widget.data.edges.where((e) {
      return visibleIds.contains(e.sourceId) && visibleIds.contains(e.targetId);
    }).toList();
  }

  // ---------------------------------------------------------------------------
  // Graph colours / icons
  // ---------------------------------------------------------------------------

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

  // ---------------------------------------------------------------------------
  // Graph caching
  // ---------------------------------------------------------------------------

  /// Rebuild the cached graph/algorithm only when data, layout mode, or
  /// expansion state changes.
  void _ensureGraphCached(
    List<AgentGraphNode> nodes,
    List<AgentGraphEdge> edges,
  ) {
    final expandedHash = Object.hashAll(_expandedAgentIds);
    final needsRebuild =
        _cachedGraph == null ||
        _cachedNodeCount != nodes.length ||
        _cachedEdgeCount != edges.length ||
        _cachedUseSugiyama != _useSugiyama ||
        _cachedExpandedHash != expandedHash;
    if (!needsRebuild) return;

    _cachedGraph = _buildGraph(nodes, edges);
    _cachedNodeCount = nodes.length;
    _cachedEdgeCount = edges.length;
    _cachedUseSugiyama = _useSugiyama;
    _cachedExpandedHash = expandedHash;

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

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final data = widget.data;
    if (data.nodes.isEmpty) {
      return const Center(
        child: Text('No graph data', style: TextStyle(color: Colors.white70)),
      );
    }

    final nodes = _visibleNodes();
    final visibleIds = nodes.map((n) => n.id).toSet();
    final edges = _visibleEdges(visibleIds);

    _ensureGraphCached(nodes, edges);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildToolbar(data),
        const SizedBox(height: 4),
        _buildLegend(),
        const SizedBox(height: 4),
        Expanded(
          child: FadeTransition(
            opacity: _fadeAnim,
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
        ),
        if (_selectedNodeId != null) _buildNodeDetail(data),
      ],
    );
  }

  Graph _buildGraph(List<AgentGraphNode> nodes, List<AgentGraphEdge> edges) {
    final graph = Graph()..isTree = false;
    final nodeMap = <String, Node>{};

    for (final gNode in nodes) {
      final node = Node.Id(gNode.id);
      nodeMap[gNode.id] = node;
      graph.addNode(node);
    }

    for (final edge in edges) {
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

  // ---------------------------------------------------------------------------
  // Toolbar & legend
  // ---------------------------------------------------------------------------

  Widget _buildToolbar(AgentGraphData data) {
    // Count how many nodes are hidden behind collapsed agents.
    final totalNodes = data.nodes.length;
    final visibleCount = _visibleNodes().length;
    final hiddenCount = totalNodes - visibleCount;

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
          if (hiddenCount > 0) ...[
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                '+$hiddenCount hidden',
                style: const TextStyle(color: Colors.white38, fontSize: 10),
              ),
            ),
          ],
          const Spacer(),
          if (_expandedAgentIds.isNotEmpty)
            _actionButton(
              'Collapse all',
              Icons.unfold_less,
              () => setState(() {
                _expandedAgentIds.clear();
                _autoExpandSingleRoot();
                _playTransition();
              }),
            ),
          const SizedBox(width: 8),
          _actionButton(
            'Expand all',
            Icons.unfold_more,
            () => setState(() {
              for (final n in widget.data.nodes) {
                if (n.expandable) _expandedAgentIds.add(n.id);
              }
              _playTransition();
            }),
          ),
          const SizedBox(width: 12),
          _layoutToggle(),
        ],
      ),
    );
  }

  Widget _actionButton(String label, IconData icon, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(4),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, color: Colors.white38, size: 14),
            const SizedBox(width: 4),
            Text(
              label,
              style: const TextStyle(color: Colors.white54, fontSize: 10),
            ),
          ],
        ),
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
      ('Sub-agent', 'sub_agent'),
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

  // ---------------------------------------------------------------------------
  // Node widget
  // ---------------------------------------------------------------------------

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
    final isExpanded = _expandedAgentIds.contains(nodeId);

    return GestureDetector(
      onTap: () => setState(() {
        _selectedNodeId = isSelected ? null : nodeId;
      }),
      onDoubleTap: gNode.expandable ? () => _toggleExpansion(nodeId) : null,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        constraints: const BoxConstraints(minWidth: 80),
        decoration: BoxDecoration(
          color: color.withValues(alpha: isExpanded ? 0.25 : 0.15),
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
              textAlign: TextAlign.center,
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
            // --- Progressive disclosure hint ---
            if (gNode.expandable) ...[
              const SizedBox(height: 4),
              _buildExpandHint(gNode, isExpanded, color),
            ],
          ],
        ),
      ),
    );
  }

  /// A compact expand/collapse control showing the children count and a chevron.
  Widget _buildExpandHint(AgentGraphNode gNode, bool isExpanded, Color color) {
    return GestureDetector(
      onTap: () => _toggleExpansion(gNode.id),
      behavior: HitTestBehavior.opaque,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: color.withValues(alpha: 0.3)),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              isExpanded ? Icons.expand_less : Icons.expand_more,
              color: color,
              size: 14,
            ),
            const SizedBox(width: 2),
            Text(
              '${gNode.childrenCount}',
              style: TextStyle(color: color, fontSize: 10),
            ),
          ],
        ),
      ),
    );
  }

  void _toggleExpansion(String nodeId) {
    setState(() {
      if (_expandedAgentIds.contains(nodeId)) {
        // Collapse: also collapse any descendants
        _collapseWithDescendants(nodeId);
      } else {
        _expandedAgentIds.add(nodeId);
      }
      _playTransition();
    });
  }

  /// When collapsing an agent, also collapse any sub-agents that were expanded
  /// under it so the user doesn't see orphaned expanded states.
  void _collapseWithDescendants(String agentId) {
    _expandedAgentIds.remove(agentId);
    // Find child agents of this agent and collapse them recursively.
    final childAgents = widget.data.nodes.where(
      (n) => n.parentAgentId == agentId && n.expandable,
    );
    for (final child in childAgents) {
      _collapseWithDescendants(child.id);
    }
  }

  void _playTransition() {
    _animController.forward(from: 0.0);
  }

  // ---------------------------------------------------------------------------
  // Node detail panel
  // ---------------------------------------------------------------------------

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

    final color = _nodeColor(gNode.type);

    return Container(
      width: double.infinity,
      margin: const EdgeInsets.all(8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.black26,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Icon(_nodeIcon(gNode.type), color: color, size: 16),
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
              if (gNode.expandable)
                GestureDetector(
                  onTap: () => _toggleExpansion(gNode.id),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 3,
                    ),
                    decoration: BoxDecoration(
                      color: color.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      _expandedAgentIds.contains(gNode.id)
                          ? 'Collapse'
                          : 'Expand (${gNode.childrenCount})',
                      style: TextStyle(color: color, fontSize: 10),
                    ),
                  ),
                ),
              const SizedBox(width: 8),
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
          if (gNode.depth > 0)
            Text(
              'Depth: ${gNode.depth}',
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
          if (gNode.childrenCount > 0)
            Text(
              'Children: ${gNode.childrenCount}',
              style: const TextStyle(color: Colors.white54, fontSize: 11),
            ),
          if (relatedEdges.isNotEmpty) ...[
            const SizedBox(height: 6),
            const Text(
              'Connections:',
              style: TextStyle(color: Colors.white38, fontSize: 10),
            ),
            ...relatedEdges
                .take(8)
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
