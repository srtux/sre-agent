import 'dart:math' as math;

import 'package:flutter/material.dart';
import '../../theme/app_theme.dart';
import '../../theme/design_tokens.dart';

/// Model for a service node in the topology
class ServiceNode {
  final String id;
  final String name;
  final String
  type; // 'frontend', 'backend', 'database', 'cache', 'queue', 'external'
  final String health; // 'healthy', 'degraded', 'unhealthy', 'unknown'
  final double latencyMs;
  final double errorRate;
  final int requestsPerSec;
  final List<ServiceConnection> connections;

  ServiceNode({
    required this.id,
    required this.name,
    required this.type,
    required this.health,
    this.latencyMs = 0,
    this.errorRate = 0,
    this.requestsPerSec = 0,
    this.connections = const [],
  });

  factory ServiceNode.fromJson(Map<String, dynamic> json) {
    return ServiceNode(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      type: json['type'] ?? 'backend',
      health: json['health'] ?? 'unknown',
      latencyMs: (json['latency_ms'] as num?)?.toDouble() ?? 0,
      errorRate: (json['error_rate'] as num?)?.toDouble() ?? 0,
      requestsPerSec: (json['requests_per_sec'] as num?)?.toInt() ?? 0,
      connections: (json['connections'] as List? ?? [])
          .map((c) => ServiceConnection.fromJson(Map<String, dynamic>.from(c)))
          .toList(),
    );
  }
}

/// Model for a connection between services
class ServiceConnection {
  final String targetId;
  final double trafficPercent;
  final double latencyMs;
  final double errorRate;

  ServiceConnection({
    required this.targetId,
    this.trafficPercent = 0,
    this.latencyMs = 0,
    this.errorRate = 0,
  });

  factory ServiceConnection.fromJson(Map<String, dynamic> json) {
    return ServiceConnection(
      targetId: json['target_id'] ?? '',
      trafficPercent: (json['traffic_percent'] as num?)?.toDouble() ?? 0,
      latencyMs: (json['latency_ms'] as num?)?.toDouble() ?? 0,
      errorRate: (json['error_rate'] as num?)?.toDouble() ?? 0,
    );
  }
}

/// Model for the service topology
class ServiceTopologyData {
  final List<ServiceNode> services;
  final String? highlightedServiceId;
  final String? incidentSourceId;
  final List<String> affectedPath;

  ServiceTopologyData({
    required this.services,
    this.highlightedServiceId,
    this.incidentSourceId,
    this.affectedPath = const [],
  });

  factory ServiceTopologyData.fromJson(Map<String, dynamic> json) {
    return ServiceTopologyData(
      services: (json['services'] as List? ?? [])
          .map((s) => ServiceNode.fromJson(Map<String, dynamic>.from(s)))
          .toList(),
      highlightedServiceId: json['highlighted_service_id'],
      incidentSourceId: json['incident_source_id'],
      affectedPath: List<String>.from(json['affected_path'] ?? []),
    );
  }
}

/// Service Topology Canvas - Interactive service dependency visualization
class ServiceTopologyCanvas extends StatefulWidget {
  final ServiceTopologyData data;

  const ServiceTopologyCanvas({super.key, required this.data});

  @override
  State<ServiceTopologyCanvas> createState() => _ServiceTopologyCanvasState();
}

class _ServiceTopologyCanvasState extends State<ServiceTopologyCanvas>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _entranceController;
  late Animation<double> _pulseAnimation;
  late Animation<double> _entranceAnimation;

  final Map<String, Offset> _nodePositions = {};
  String? _selectedServiceId;
  String? _hoveredServiceId;
  double _scale = 1.0;
  Offset _offset = Offset.zero;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    );

    _entranceController = AnimationController(
      duration: const Duration(milliseconds: 1000),
      vsync: this,
    );

    _pulseAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _entranceAnimation = CurvedAnimation(
      parent: _entranceController,
      curve: Curves.easeOutCubic,
    );

    _entranceController.forward();
    _calculateNodePositions();
    _syncAnimations();
  }

  @override
  void didUpdateWidget(ServiceTopologyCanvas oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.data.services.length != widget.data.services.length) {
      _calculateNodePositions();
    }
    if (oldWidget.data.affectedPath != widget.data.affectedPath ||
        oldWidget.data.incidentSourceId != widget.data.incidentSourceId) {
      _syncAnimations();
    }
  }

  /// Only run pulse animation when there is an active incident or affected path.
  void _syncAnimations() {
    final needsAnimation = widget.data.affectedPath.isNotEmpty ||
        widget.data.incidentSourceId != null;
    if (needsAnimation) {
      if (!_pulseController.isAnimating) {
        _pulseController.repeat(reverse: true);
      }
    } else {
      _pulseController.stop();
    }
  }

  void _calculateNodePositions() {
    final services = widget.data.services;
    if (services.isEmpty) return;

    // Layer-based layout (left to right flow)
    final layers = _organizeIntoLayers(services);
    const layerSpacing = 160.0;
    const nodeSpacing = 100.0;

    var currentX = 80.0;
    for (var layerIdx = 0; layerIdx < layers.length; layerIdx++) {
      final layer = layers[layerIdx];
      final totalHeight = layer.length * nodeSpacing;
      var startY = (400 - totalHeight) / 2 + nodeSpacing / 2;

      for (var nodeIdx = 0; nodeIdx < layer.length; nodeIdx++) {
        _nodePositions[layer[nodeIdx].id] = Offset(
          currentX,
          startY + nodeIdx * nodeSpacing,
        );
      }
      currentX += layerSpacing;
    }
  }

  List<List<ServiceNode>> _organizeIntoLayers(List<ServiceNode> services) {
    // Simple layering: frontends first, then backends, then databases/external
    final typeOrder = [
      'frontend',
      'backend',
      'cache',
      'queue',
      'database',
      'external',
    ];
    final layers = <List<ServiceNode>>[];

    for (final type in typeOrder) {
      final layerNodes = services.where((s) => s.type == type).toList();
      if (layerNodes.isNotEmpty) {
        layers.add(layerNodes);
      }
    }

    // Add any remaining nodes not in typeOrder
    final unassigned = services
        .where((s) => !typeOrder.contains(s.type))
        .toList();
    if (unassigned.isNotEmpty) {
      layers.add(unassigned);
    }

    return layers;
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _entranceController.dispose();
    super.dispose();
  }

  Color _getHealthColor(String health) {
    switch (health) {
      case 'healthy':
        return AppColors.success;
      case 'degraded':
        return AppColors.warning;
      case 'unhealthy':
        return AppColors.error;
      default:
        return AppColors.textMuted;
    }
  }

  Color _getTypeColor(String type) {
    switch (type) {
      case 'frontend':
        return AppColors.primaryCyan;
      case 'backend':
        return AppColors.primaryTeal;
      case 'database':
        return AppColors.info;
      case 'cache':
        return AppColors.warning;
      case 'queue':
        return SeverityColors.queue;
      case 'external':
        return AppColors.textMuted;
      default:
        return AppColors.primaryTeal;
    }
  }

  IconData _getTypeIcon(String type) {
    switch (type) {
      case 'frontend':
        return Icons.web;
      case 'backend':
        return Icons.dns;
      case 'database':
        return Icons.storage;
      case 'cache':
        return Icons.memory;
      case 'queue':
        return Icons.queue;
      case 'external':
        return Icons.cloud;
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
        _buildToolbar(),
        Expanded(
          child: AnimatedBuilder(
            animation: Listenable.merge([_pulseAnimation, _entranceAnimation]),
            builder: (context, child) {
              return GestureDetector(
                onScaleUpdate: (details) {
                  setState(() {
                    _scale = (_scale * details.scale).clamp(0.5, 2.0);
                    _offset += details.focalPointDelta;
                  });
                },
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Container(
                    margin: const EdgeInsets.symmetric(horizontal: 16),
                    decoration: BoxDecoration(
                      color: Colors.black.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: AppColors.surfaceBorder),
                    ),
                    child: LayoutBuilder(
                      builder: (context, constraints) {
                        return Transform(
                          transform: Matrix4.identity()
                            ..translateByDouble(
                              _offset.dx,
                              _offset.dy,
                              0.0,
                              1.0,
                            )
                            ..scaleByDouble(_scale, _scale, 1.0, 1.0),
                          child: Stack(
                            children: [
                              // Background pattern
                              CustomPaint(
                                size: Size(
                                  constraints.maxWidth,
                                  constraints.maxHeight,
                                ),
                                painter: _TopologyBackgroundPainter(),
                              ),
                              // Connections
                              CustomPaint(
                                size: Size(
                                  constraints.maxWidth,
                                  constraints.maxHeight,
                                ),
                                painter: _TopologyConnectionsPainter(
                                  services: widget.data.services,
                                  positions: _nodePositions,
                                  highlightedId:
                                      _selectedServiceId ?? _hoveredServiceId,
                                  incidentSourceId:
                                      widget.data.incidentSourceId,
                                  affectedPath: widget.data.affectedPath,
                                  entranceProgress: _entranceAnimation.value,
                                  pulseProgress: _pulseAnimation.value,
                                ),
                              ),
                              // Service nodes
                              ...widget.data.services.map(
                                (service) => _buildServiceNode(service),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
                  ),
                ),
              );
            },
          ),
        ),
        _buildHealthSummary(),
        _buildLegend(),
      ],
    );
  }

  Widget _buildHeader() {
    final unhealthyCount = widget.data.services
        .where((s) => s.health == 'unhealthy')
        .length;
    final degradedCount = widget.data.services
        .where((s) => s.health == 'degraded')
        .length;

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppColors.primaryBlue.withValues(alpha: 0.2),
                  AppColors.primaryCyan.withValues(alpha: 0.15),
                ],
              ),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(
              Icons.hub,
              size: 18,
              color: AppColors.primaryBlue,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Service Topology',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  '${widget.data.services.length} services',
                  style: const TextStyle(
                    fontSize: 11,
                    color: AppColors.textMuted,
                  ),
                ),
              ],
            ),
          ),
          if (unhealthyCount > 0)
            _buildStatusBadge(unhealthyCount, 'unhealthy', AppColors.error),
          const SizedBox(width: 8),
          if (degradedCount > 0)
            _buildStatusBadge(degradedCount, 'degraded', AppColors.warning),
        ],
      ),
    );
  }

  Widget _buildStatusBadge(int count, String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.warning_amber, size: 12, color: color),
          const SizedBox(width: 4),
          Text(
            '$count $label',
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w500,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildToolbar() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Row(
        children: [
          _buildToolButton(Icons.zoom_in, 'Zoom In', () {
            setState(() => _scale = (_scale * 1.2).clamp(0.5, 2.0));
          }),
          _buildToolButton(Icons.zoom_out, 'Zoom Out', () {
            setState(() => _scale = (_scale / 1.2).clamp(0.5, 2.0));
          }),
          _buildToolButton(Icons.center_focus_strong, 'Reset View', () {
            setState(() {
              _scale = 1.0;
              _offset = Offset.zero;
            });
          }),
          const Spacer(),
          if (_selectedServiceId != null)
            TextButton.icon(
              onPressed: () => setState(() => _selectedServiceId = null),
              icon: const Icon(Icons.clear, size: 14),
              label: const Text('Clear Selection'),
              style: TextButton.styleFrom(
                foregroundColor: AppColors.textMuted,
                textStyle: const TextStyle(fontSize: 11),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildToolButton(IconData icon, String tooltip, VoidCallback onTap) {
    return Tooltip(
      message: tooltip,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(6),
        child: Container(
          padding: const EdgeInsets.all(6),
          margin: const EdgeInsets.only(right: 4),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.05),
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: AppColors.surfaceBorder),
          ),
          child: Icon(icon, size: 16, color: AppColors.textMuted),
        ),
      ),
    );
  }

  Widget _buildServiceNode(ServiceNode service) {
    final position = _nodePositions[service.id];
    if (position == null) return const SizedBox.shrink();

    final isSelected = service.id == _selectedServiceId;
    final isHovered = service.id == _hoveredServiceId;
    final isAffected = widget.data.affectedPath.contains(service.id);
    final isIncidentSource = service.id == widget.data.incidentSourceId;
    final healthColor = _getHealthColor(service.health);
    final typeColor = _getTypeColor(service.type);
    final opacity = _entranceAnimation.value;

    return Positioned(
      left: position.dx - 40,
      top: position.dy - 40,
      child: Opacity(
        opacity: opacity,
        child: MouseRegion(
          onEnter: (_) => setState(() => _hoveredServiceId = service.id),
          onExit: (_) => setState(() => _hoveredServiceId = null),
          child: GestureDetector(
            onTap: () => setState(
              () => _selectedServiceId = _selectedServiceId == service.id
                  ? null
                  : service.id,
            ),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: 80,
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: (isSelected || isHovered)
                    ? typeColor.withValues(alpha: 0.2)
                    : AppColors.backgroundCard,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: isIncidentSource
                      ? AppColors.error
                      : isAffected
                      ? AppColors.warning
                      : isSelected
                      ? typeColor
                      : AppColors.surfaceBorder,
                  width: (isSelected || isIncidentSource) ? 2 : 1,
                ),
                boxShadow: [
                  if (isSelected || isIncidentSource)
                    BoxShadow(
                      color: (isIncidentSource ? AppColors.error : typeColor)
                          .withValues(alpha: 0.3),
                      blurRadius: 12,
                      spreadRadius: 2,
                    ),
                ],
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Icon with health indicator
                  Stack(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: typeColor.withValues(alpha: 0.15),
                          shape: BoxShape.circle,
                        ),
                        child: Icon(
                          _getTypeIcon(service.type),
                          size: 20,
                          color: typeColor,
                        ),
                      ),
                      Positioned(
                        right: 0,
                        top: 0,
                        child: Container(
                          width: 10,
                          height: 10,
                          decoration: BoxDecoration(
                            color: healthColor,
                            shape: BoxShape.circle,
                            border: Border.all(
                              color: AppColors.backgroundCard,
                              width: 2,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  // Service name
                  Text(
                    service.name,
                    style: const TextStyle(
                      fontSize: 9,
                      fontWeight: FontWeight.w500,
                      color: AppColors.textPrimary,
                    ),
                    textAlign: TextAlign.center,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  // Metrics preview
                  if (isSelected || isHovered) ...[
                    const SizedBox(height: 4),
                    _buildMetricChip(
                      '${service.latencyMs.toStringAsFixed(0)}ms',
                      service.latencyMs > 500
                          ? AppColors.warning
                          : AppColors.textMuted,
                    ),
                    const SizedBox(height: 2),
                    _buildMetricChip(
                      '${(service.errorRate * 100).toStringAsFixed(1)}% err',
                      service.errorRate > 0.01
                          ? AppColors.error
                          : AppColors.textMuted,
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildMetricChip(String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        text,
        style: TextStyle(fontSize: 8, color: color, fontFamily: 'monospace'),
      ),
    );
  }

  Widget _buildHealthSummary() {
    final selected = _selectedServiceId != null
        ? widget.data.services.firstWhere(
            (s) => s.id == _selectedServiceId,
            orElse: () => widget.data.services.first,
          )
        : null;

    if (selected == null) return const SizedBox.shrink();

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.surfaceBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                _getTypeIcon(selected.type),
                size: 16,
                color: _getTypeColor(selected.type),
              ),
              const SizedBox(width: 8),
              Text(
                selected.name,
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: _getHealthColor(
                    selected.health,
                  ).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  selected.health.toUpperCase(),
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    color: _getHealthColor(selected.health),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              _buildStat(
                'Latency',
                '${selected.latencyMs.toStringAsFixed(1)}ms',
              ),
              _buildStat(
                'Error Rate',
                '${(selected.errorRate * 100).toStringAsFixed(2)}%',
              ),
              _buildStat('RPS', '${selected.requestsPerSec}'),
              _buildStat('Connections', '${selected.connections.length}'),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStat(String label, String value) {
    return Expanded(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: const TextStyle(fontSize: 9, color: AppColors.textMuted),
          ),
          Text(
            value,
            style: const TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: AppColors.textSecondary,
              fontFamily: 'monospace',
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLegend() {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.03),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.surfaceBorder),
      ),
      child: Row(
        children: [
          _legendItem(Icons.web, 'Frontend', _getTypeColor('frontend')),
          _legendItem(Icons.dns, 'Backend', _getTypeColor('backend')),
          _legendItem(Icons.storage, 'Database', _getTypeColor('database')),
          _legendItem(Icons.memory, 'Cache', _getTypeColor('cache')),
          const Spacer(),
          _healthLegend('Healthy', AppColors.success),
          _healthLegend('Degraded', AppColors.warning),
          _healthLegend('Unhealthy', AppColors.error),
        ],
      ),
    );
  }

  Widget _legendItem(IconData icon, String label, Color color) {
    return Padding(
      padding: const EdgeInsets.only(right: 16),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 4),
          Text(
            label,
            style: const TextStyle(fontSize: 9, color: AppColors.textMuted),
          ),
        ],
      ),
    );
  }

  Widget _healthLegend(String label, Color color) {
    return Padding(
      padding: const EdgeInsets.only(left: 12),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          const SizedBox(width: 4),
          Text(
            label,
            style: const TextStyle(fontSize: 9, color: AppColors.textMuted),
          ),
        ],
      ),
    );
  }
}

/// Background painter for topology
class _TopologyBackgroundPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    // Draw dots grid
    const spacing = 25.0;
    final dotPaint = Paint()
      ..color = AppColors.surfaceBorder.withValues(alpha: 0.4)
      ..style = PaintingStyle.fill;

    for (double x = 0; x < size.width; x += spacing) {
      for (double y = 0; y < size.height; y += spacing) {
        canvas.drawCircle(Offset(x, y), 1, dotPaint);
      }
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

/// Connections painter for topology
class _TopologyConnectionsPainter extends CustomPainter {
  final List<ServiceNode> services;
  final Map<String, Offset> positions;
  final String? highlightedId;
  final String? incidentSourceId;
  final List<String> affectedPath;
  final double entranceProgress;
  final double pulseProgress;

  _TopologyConnectionsPainter({
    required this.services,
    required this.positions,
    this.highlightedId,
    this.incidentSourceId,
    required this.affectedPath,
    required this.entranceProgress,
    required this.pulseProgress,
  });

  @override
  void paint(Canvas canvas, Size size) {
    for (final service in services) {
      final fromPos = positions[service.id];
      if (fromPos == null) continue;

      for (final connection in service.connections) {
        final toPos = positions[connection.targetId];
        if (toPos == null) continue;

        final isHighlighted =
            highlightedId == service.id || highlightedId == connection.targetId;
        final isAffectedConnection =
            affectedPath.contains(service.id) &&
            affectedPath.contains(connection.targetId);
        final isIncidentPath = incidentSourceId == service.id;

        // Determine colors
        Color lineColor;
        double strokeWidth;

        if (isIncidentPath || isAffectedConnection) {
          lineColor = AppColors.error;
          strokeWidth = 3;
        } else if (isHighlighted) {
          lineColor = AppColors.primaryTeal;
          strokeWidth = 2.5;
        } else {
          lineColor = AppColors.surfaceBorder;
          strokeWidth = 1.5;
        }

        // Draw connection
        final paint = Paint()
          ..color = lineColor.withValues(alpha: entranceProgress * 0.6)
          ..strokeWidth = strokeWidth
          ..style = PaintingStyle.stroke
          ..strokeCap = StrokeCap.round;

        // Calculate control point for curved line
        final midX = (fromPos.dx + toPos.dx) / 2;
        final midY = (fromPos.dy + toPos.dy) / 2;
        final controlOffset = (fromPos.dy - toPos.dy).abs() < 50 ? 20.0 : 0.0;

        final path = Path()
          ..moveTo(fromPos.dx, fromPos.dy)
          ..quadraticBezierTo(midX, midY - controlOffset, toPos.dx, toPos.dy);

        canvas.drawPath(path, paint);

        // Draw traffic flow animation for affected paths
        if (isAffectedConnection || isIncidentPath) {
          _drawTrafficFlow(canvas, fromPos, toPos, lineColor);
        }

        // Draw arrow at midpoint
        _drawArrowHead(
          canvas,
          fromPos,
          toPos,
          lineColor.withValues(alpha: entranceProgress),
        );
      }
    }
  }

  void _drawTrafficFlow(Canvas canvas, Offset from, Offset to, Color color) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.fill;

    // Calculate position along the path
    for (var i = 0; i < 3; i++) {
      final t = (pulseProgress + i * 0.33) % 1.0;
      final x = from.dx + (to.dx - from.dx) * t;
      final y = from.dy + (to.dy - from.dy) * t;
      canvas.drawCircle(Offset(x, y), 3, paint);
    }
  }

  void _drawArrowHead(Canvas canvas, Offset from, Offset to, Color color) {
    final angle = math.atan2(to.dy - from.dy, to.dx - from.dx);
    final midX = (from.dx + to.dx) / 2;
    final midY = (from.dy + to.dy) / 2;
    const arrowLength = 8.0;
    const arrowAngle = math.pi / 6;

    final paint = Paint()
      ..color = color.withValues(alpha: 0.8)
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

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant _TopologyConnectionsPainter oldDelegate) {
    return oldDelegate.highlightedId != highlightedId ||
        oldDelegate.entranceProgress != entranceProgress ||
        oldDelegate.pulseProgress != pulseProgress;
  }
}
