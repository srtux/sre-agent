import 'dart:math' as math;

import 'package:flutter/material.dart';
import '../../models/agent_models.dart';
import '../../theme/app_theme.dart';

/// Agent Activity Canvas - Real-time visualization of agent workflow
class AgentActivityCanvas extends StatefulWidget {
  final AgentActivityData data;

  const AgentActivityCanvas({super.key, required this.data});

  @override
  State<AgentActivityCanvas> createState() => _AgentActivityCanvasState();
}

class _AgentActivityCanvasState extends State<AgentActivityCanvas>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _flowController;
  late AnimationController _entranceController;
  late Animation<double> _pulseAnimation;
  late Animation<double> _flowAnimation;
  late Animation<double> _entranceAnimation;

  final Map<String, Offset> _nodePositions = {};

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    );

    _flowController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    );

    _entranceController = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    );

    _pulseAnimation = Tween<double>(begin: 0.8, end: 1.2).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _flowAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(parent: _flowController, curve: Curves.linear));

    _entranceAnimation = CurvedAnimation(
      parent: _entranceController,
      curve: Curves.easeOutCubic,
    );

    _entranceController.forward();
    _calculateNodePositions();
    _syncAnimations();
  }

  @override
  void didUpdateWidget(AgentActivityCanvas oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.data.nodes.length != widget.data.nodes.length) {
      _calculateNodePositions();
    }
    if (oldWidget.data.activeNodeId != widget.data.activeNodeId) {
      _syncAnimations();
    }
  }

  /// Only run pulse/flow animations when there is an active node.
  void _syncAnimations() {
    final hasActive = widget.data.activeNodeId != null;
    if (hasActive) {
      if (!_pulseController.isAnimating) _pulseController.repeat(reverse: true);
      if (!_flowController.isAnimating) _flowController.repeat();
    } else {
      _pulseController.stop();
      _pulseController.value = 0.0;
      _flowController.stop();
      _flowController.value = 0.0;
    }
  }

  void _calculateNodePositions() {
    // Calculate positions in a radial layout
    final nodes = widget.data.nodes;
    if (nodes.isEmpty) return;

    const centerX = 200.0;
    const centerY = 180.0;

    // Find coordinator node (center)
    final coordinatorIdx = nodes.indexWhere((n) => n.type == 'coordinator');

    if (coordinatorIdx >= 0) {
      _nodePositions[nodes[coordinatorIdx].id] = const Offset(centerX, centerY);

      // Position other nodes in a circle around coordinator
      final otherNodes = nodes.where((n) => n.type != 'coordinator').toList();
      final angleStep = (2 * math.pi) / otherNodes.length;
      const radius = 120.0;

      for (var i = 0; i < otherNodes.length; i++) {
        final angle = -math.pi / 2 + i * angleStep;
        _nodePositions[otherNodes[i].id] = Offset(
          centerX + radius * math.cos(angle),
          centerY + radius * math.sin(angle),
        );
      }
    } else {
      // Grid layout if no coordinator
      final cols = (math.sqrt(nodes.length)).ceil();
      for (var i = 0; i < nodes.length; i++) {
        final row = i ~/ cols;
        final col = i % cols;
        _nodePositions[nodes[i].id] = Offset(
          80.0 + col * 100.0,
          80.0 + row * 100.0,
        );
      }
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _flowController.dispose();
    _entranceController.dispose();
    super.dispose();
  }

  Color _getNodeColor(AgentNode node) {
    switch (node.type) {
      case 'coordinator':
        return AppColors.primaryTeal;
      case 'sub_agent':
        return AppColors.primaryCyan;
      case 'tool':
        return AppColors.warning;
      case 'data_source':
        return AppColors.info;
      default:
        return AppColors.textMuted;
    }
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'active':
        return AppColors.success;
      case 'completed':
        return AppColors.primaryTeal;
      case 'error':
        return AppColors.error;
      default:
        return AppColors.textMuted;
    }
  }

  IconData _getNodeIcon(AgentNode node) {
    switch (node.type) {
      case 'coordinator':
        return Icons.hub;
      case 'sub_agent':
        return Icons.smart_toy;
      case 'tool':
        return Icons.build;
      case 'data_source':
        return Icons.storage;
      default:
        return Icons.circle;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildHeader(),
        Expanded(
          child: AnimatedBuilder(
            animation: Listenable.merge([
              _pulseAnimation,
              _flowAnimation,
              _entranceAnimation,
            ]),
            builder: (context, child) {
              return LayoutBuilder(
                builder: (context, constraints) {
                  return ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Stack(
                      children: [
                        // Background grid
                        CustomPaint(
                          size: Size(
                            constraints.maxWidth,
                            constraints.maxHeight,
                          ),
                          painter: _GridPainter(),
                        ),
                        // Connections
                        CustomPaint(
                          size: Size(
                            constraints.maxWidth,
                            constraints.maxHeight,
                          ),
                          painter: _ConnectionsPainter(
                            nodes: widget.data.nodes,
                            positions: _nodePositions,
                            activeNodeId: widget.data.activeNodeId,
                            flowProgress: _flowAnimation.value,
                            entranceProgress: _entranceAnimation.value,
                          ),
                        ),
                        // Nodes
                        ...widget.data.nodes.map(
                          (node) => _buildNode(node, constraints),
                        ),
                      ],
                    ),
                  );
                },
              );
            },
          ),
        ),
        _buildLegend(),
        if (widget.data.message != null) _buildMessageBar(),
      ],
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppColors.primaryTeal.withValues(alpha: 0.2),
                  AppColors.primaryCyan.withValues(alpha: 0.15),
                ],
              ),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(
              Icons.account_tree,
              size: 18,
              color: AppColors.primaryTeal,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Agent Activity',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  widget.data.currentPhase,
                  style: const TextStyle(
                    fontSize: 11,
                    color: AppColors.textMuted,
                  ),
                ),
              ],
            ),
          ),
          _buildPhaseIndicator(),
        ],
      ),
    );
  }

  Widget _buildPhaseIndicator() {
    final isActive = widget.data.activeNodeId != null;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: (isActive ? AppColors.success : AppColors.textMuted).withValues(
          alpha: 0.15,
        ),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: (isActive ? AppColors.success : AppColors.textMuted)
              .withValues(alpha: 0.3),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (isActive)
            const SizedBox(
              width: 8,
              height: 8,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: AppColors.success,
              ),
            )
          else
            Container(
              width: 8,
              height: 8,
              decoration: const BoxDecoration(
                color: AppColors.textMuted,
                shape: BoxShape.circle,
              ),
            ),
          const SizedBox(width: 6),
          Text(
            isActive ? 'Processing' : 'Idle',
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w500,
              color: isActive ? AppColors.success : AppColors.textMuted,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildNode(AgentNode node, BoxConstraints constraints) {
    final position = _nodePositions[node.id];
    if (position == null) return const SizedBox.shrink();

    final isActive = node.id == widget.data.activeNodeId;
    final isCompleted = widget.data.completedSteps.contains(node.id);
    final color = _getNodeColor(node);
    final statusColor = _getStatusColor(node.status);
    final scale = isActive ? _pulseAnimation.value : 1.0;
    final opacity = _entranceAnimation.value;

    return Positioned(
      left: position.dx - 32,
      top: position.dy - 32,
      child: Opacity(
        opacity: opacity,
        child: MouseRegion(
          onEnter: (_) => setState(() {}),
          onExit: (_) => setState(() {}),
          child: Transform.scale(
            scale: scale,
            child: GestureDetector(
              onTap: () => _showNodeDetails(node),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                width: 64,
                height: 64,
                decoration: BoxDecoration(
                  gradient: RadialGradient(
                    colors: [
                      color.withValues(alpha: 0.3),
                      color.withValues(alpha: 0.1),
                    ],
                  ),
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: isActive
                        ? AppColors.success
                        : color.withValues(alpha: 0.5),
                    width: isActive ? 3 : 2,
                  ),
                  boxShadow: [
                    if (isActive)
                      BoxShadow(
                        color: AppColors.success.withValues(alpha: 0.4),
                        blurRadius: 16,
                        spreadRadius: 2,
                      ),
                    BoxShadow(
                      color: color.withValues(alpha: 0.2),
                      blurRadius: 8,
                      spreadRadius: 0,
                    ),
                  ],
                ),
                child: Stack(
                  children: [
                    Center(
                      child: Icon(_getNodeIcon(node), size: 24, color: color),
                    ),
                    // Status indicator
                    Positioned(
                      right: 4,
                      top: 4,
                      child: Container(
                        width: 12,
                        height: 12,
                        decoration: BoxDecoration(
                          color: statusColor,
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: AppColors.backgroundDark,
                            width: 2,
                          ),
                        ),
                      ),
                    ),
                    // Completed checkmark
                    if (isCompleted)
                      Positioned(
                        left: 4,
                        bottom: 4,
                        child: Container(
                          width: 16,
                          height: 16,
                          decoration: const BoxDecoration(
                            color: AppColors.success,
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(
                            Icons.check,
                            size: 10,
                            color: Colors.white,
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildLegend() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.03),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.surfaceBorder),
      ),
      child: Wrap(
        spacing: 16,
        runSpacing: 8,
        children: [
          _legendItem(Icons.hub, 'Coordinator', AppColors.primaryTeal),
          _legendItem(Icons.smart_toy, 'Sub-Agent', AppColors.primaryCyan),
          _legendItem(Icons.build, 'Tool', AppColors.warning),
          _legendItem(Icons.storage, 'Data Source', AppColors.info),
        ],
      ),
    );
  }

  Widget _legendItem(IconData icon, String label, Color color) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: color),
        const SizedBox(width: 4),
        Text(
          label,
          style: const TextStyle(fontSize: 10, color: AppColors.textMuted),
        ),
      ],
    );
  }

  Widget _buildMessageBar() {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.info.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.info.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          const Icon(Icons.info_outline, size: 14, color: AppColors.info),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              widget.data.message!,
              style: const TextStyle(fontSize: 11, color: AppColors.info),
            ),
          ),
        ],
      ),
    );
  }

  void _showNodeDetails(AgentNode node) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.backgroundCard,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            Icon(_getNodeIcon(node), color: _getNodeColor(node)),
            const SizedBox(width: 12),
            Text(
              node.name,
              style: const TextStyle(color: AppColors.textPrimary),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _detailRow('Type', node.type),
            _detailRow('Status', node.status),
            _detailRow('ID', node.id),
            if (node.connections.isNotEmpty)
              _detailRow('Connections', node.connections.length.toString()),
            if (node.metadata != null)
              ...node.metadata!.entries.map(
                (e) => _detailRow(e.key, e.value.toString()),
              ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  Widget _detailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Text(
            '$label: ',
            style: const TextStyle(color: AppColors.textMuted, fontSize: 12),
          ),
          Text(
            value,
            style: const TextStyle(
              color: AppColors.textSecondary,
              fontSize: 12,
              fontFamily: 'monospace',
            ),
          ),
        ],
      ),
    );
  }
}

/// Paints the background grid
class _GridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = AppColors.surfaceBorder.withValues(alpha: 0.3)
      ..strokeWidth = 0.5;

    const gridSize = 30.0;

    // Vertical lines
    for (double x = 0; x < size.width; x += gridSize) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }

    // Horizontal lines
    for (double y = 0; y < size.height; y += gridSize) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

/// Paints the connections between nodes
class _ConnectionsPainter extends CustomPainter {
  final List<AgentNode> nodes;
  final Map<String, Offset> positions;
  final String? activeNodeId;
  final double flowProgress;
  final double entranceProgress;

  _ConnectionsPainter({
    required this.nodes,
    required this.positions,
    this.activeNodeId,
    required this.flowProgress,
    required this.entranceProgress,
  });

  @override
  void paint(Canvas canvas, Size size) {
    for (final node in nodes) {
      final fromPos = positions[node.id];
      if (fromPos == null) continue;

      for (final connectionId in node.connections) {
        final toPos = positions[connectionId];
        if (toPos == null) continue;

        final isActive =
            node.id == activeNodeId || connectionId == activeNodeId;
        final baseColor = isActive ? AppColors.success : AppColors.primaryTeal;

        // Draw the connection line
        final paint = Paint()
          ..color = baseColor.withValues(alpha: 0.3 * entranceProgress)
          ..strokeWidth = isActive ? 2.5 : 1.5
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round;

        final path = Path()
          ..moveTo(fromPos.dx, fromPos.dy)
          ..lineTo(toPos.dx, toPos.dy);

        canvas.drawPath(path, paint);

        // Draw animated flow particles for active connections
        if (isActive) {
          _drawFlowParticles(canvas, fromPos, toPos, baseColor);
        }

        // Draw arrow
        _drawArrow(
          canvas,
          fromPos,
          toPos,
          baseColor.withValues(alpha: entranceProgress),
        );
      }
    }
  }

  void _drawFlowParticles(Canvas canvas, Offset from, Offset to, Color color) {
    final particlePaint = Paint()
      ..color = color
      ..style = PaintingStyle.fill;

    final dx = to.dx - from.dx;
    final dy = to.dy - from.dy;

    // Draw multiple particles along the path
    for (var i = 0; i < 3; i++) {
      final progress = (flowProgress + i * 0.33) % 1.0;
      final particlePos = Offset(
        from.dx + dx * progress,
        from.dy + dy * progress,
      );
      canvas.drawCircle(particlePos, 3, particlePaint);
    }
  }

  void _drawArrow(Canvas canvas, Offset from, Offset to, Color color) {
    final angle = math.atan2(to.dy - from.dy, to.dx - from.dx);
    const arrowLength = 8.0;
    const arrowAngle = math.pi / 6;

    // Calculate midpoint for arrow
    final midX = (from.dx + to.dx) / 2;
    final midY = (from.dy + to.dy) / 2;

    final arrowPaint = Paint()
      ..color = color.withValues(alpha: 0.6)
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final path = Path()
      ..moveTo(
        midX - arrowLength * math.cos(angle - arrowAngle),
        midY - arrowLength * math.sin(angle - arrowAngle),
      )
      ..lineTo(midX, midY)
      ..lineTo(
        midX - arrowLength * math.cos(angle + arrowAngle),
        midY - arrowLength * math.sin(angle + arrowAngle),
      );

    canvas.drawPath(path, arrowPaint);
  }

  @override
  bool shouldRepaint(covariant _ConnectionsPainter oldDelegate) {
    return oldDelegate.activeNodeId != activeNodeId ||
        oldDelegate.flowProgress != flowProgress ||
        oldDelegate.entranceProgress != entranceProgress;
  }
}
