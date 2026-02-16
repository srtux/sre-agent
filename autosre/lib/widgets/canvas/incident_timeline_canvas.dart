import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../models/adk_schema.dart';
import '../../theme/app_theme.dart';
import '../../theme/design_tokens.dart';

/// Incident Timeline Canvas - Visual timeline of incident progression
class IncidentTimelineCanvas extends StatefulWidget {
  final IncidentTimelineData data;

  const IncidentTimelineCanvas({super.key, required this.data});

  @override
  State<IncidentTimelineCanvas> createState() => _IncidentTimelineCanvasState();
}

class _IncidentTimelineCanvasState extends State<IncidentTimelineCanvas>
    with TickerProviderStateMixin {
  late AnimationController _entranceController;
  late AnimationController _pulseController;
  late Animation<double> _entranceAnimation;
  late Animation<double> _pulseAnimation;

  String? _selectedEventId;
  String? _hoveredEventId;
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _entranceController = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    );
    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    )..repeat(reverse: true);

    _entranceAnimation = CurvedAnimation(
      parent: _entranceController,
      curve: Curves.easeOutCubic,
    );
    _pulseAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _entranceController.forward();
  }

  @override
  void dispose() {
    _entranceController.dispose();
    _pulseController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Color _getSeverityColor(String severity) {
    switch (severity) {
      case 'critical':
        return AppColors.error;
      case 'high':
        return SeverityColors.high;
      case 'medium':
        return AppColors.warning;
      case 'low':
        return AppColors.info;
      default:
        return AppColors.textMuted;
    }
  }

  Color _getTypeColor(String type) {
    switch (type) {
      case 'alert':
        return AppColors.error;
      case 'deployment':
        return AppColors.primaryCyan;
      case 'config_change':
        return AppColors.warning;
      case 'scaling':
        return AppColors.info;
      case 'incident':
        return AppColors.error;
      case 'recovery':
        return AppColors.success;
      case 'agent_action':
        return AppColors.primaryTeal;
      default:
        return AppColors.textMuted;
    }
  }

  IconData _getTypeIcon(String type) {
    switch (type) {
      case 'alert':
        return Icons.notification_important;
      case 'deployment':
        return Icons.rocket_launch;
      case 'config_change':
        return Icons.settings;
      case 'scaling':
        return Icons.speed;
      case 'incident':
        return Icons.error;
      case 'recovery':
        return Icons.check_circle;
      case 'agent_action':
        return Icons.smart_toy;
      default:
        return Icons.circle;
    }
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'ongoing':
        return AppColors.error;
      case 'mitigated':
        return AppColors.warning;
      case 'resolved':
        return AppColors.success;
      default:
        return AppColors.textMuted;
    }
  }

  @override
  Widget build(BuildContext context) {
    final sortedEvents = List<TimelineEvent>.from(widget.data.events)
      ..sort((a, b) => a.timestamp.compareTo(b.timestamp));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildHeader(),
        _buildIncidentStats(),
        Expanded(
          child: AnimatedBuilder(
            animation: Listenable.merge([_entranceAnimation, _pulseAnimation]),
            builder: (context, child) {
              return Container(
                margin: const EdgeInsets.symmetric(horizontal: 16),
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppColors.surfaceBorder),
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Stack(
                    children: [
                      // Background
                      CustomPaint(
                        size: Size.infinite,
                        painter: _TimelineBackgroundPainter(
                          entranceProgress: _entranceAnimation.value,
                        ),
                      ),
                      // Timeline content
                      SingleChildScrollView(
                        controller: _scrollController,
                        scrollDirection: Axis.horizontal,
                        padding: const EdgeInsets.all(20),
                        child: SizedBox(
                          width: math.max(600.0, sortedEvents.length * 150.0),
                          child: Stack(
                            children: [
                              // Timeline line
                              Positioned(
                                left: 0,
                                right: 0,
                                top: 100,
                                child: _buildTimelineLine(sortedEvents),
                              ),
                              // Events
                              ...sortedEvents.asMap().entries.map((entry) {
                                final index = entry.key;
                                final event = entry.value;
                                return _buildEventNode(
                                  event,
                                  index,
                                  sortedEvents.length,
                                );
                              }),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              );
            },
          ),
        ),
        if (_selectedEventId != null) _buildEventDetails(),
        if (widget.data.rootCause != null) _buildRootCause(),
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
                  _getStatusColor(widget.data.status).withValues(alpha: 0.2),
                  _getStatusColor(widget.data.status).withValues(alpha: 0.1),
                ],
              ),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(
              widget.data.status == 'resolved'
                  ? Icons.check_circle
                  : widget.data.status == 'mitigated'
                  ? Icons.warning_amber
                  : Icons.error,
              size: 18,
              color: _getStatusColor(widget.data.status),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Incident Timeline',
                  style: TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  widget.data.title,
                  style: const TextStyle(
                    fontSize: 11,
                    color: AppColors.textMuted,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
          _buildStatusBadge(),
        ],
      ),
    );
  }

  Widget _buildStatusBadge() {
    final color = _getStatusColor(widget.data.status);
    final isOngoing = widget.data.status == 'ongoing';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (isOngoing)
            SizedBox(
              width: 8,
              height: 8,
              child: CircularProgressIndicator(strokeWidth: 2, color: color),
            )
          else
            Container(
              width: 8,
              height: 8,
              decoration: BoxDecoration(color: color, shape: BoxShape.circle),
            ),
          const SizedBox(width: 6),
          Text(
            widget.data.status.toUpperCase(),
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildIncidentStats() {
    final duration = (widget.data.endTime ?? DateTime.now()).difference(
      widget.data.startTime,
    );

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.03),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: AppColors.surfaceBorder),
      ),
      child: Row(
        children: [
          _buildStatItem(
            'Started',
            DateFormat('MMM d, HH:mm').format(widget.data.startTime),
            Icons.play_arrow,
          ),
          _buildStatItem('Duration', _formatDuration(duration), Icons.timer),
          if (widget.data.timeToDetect != null)
            _buildStatItem(
              'TTD',
              _formatDuration(widget.data.timeToDetect!),
              Icons.visibility,
            ),
          if (widget.data.timeToMitigate != null)
            _buildStatItem(
              'TTM',
              _formatDuration(widget.data.timeToMitigate!),
              Icons.healing,
            ),
          _buildStatItem(
            'Events',
            '${widget.data.events.length}',
            Icons.event_note,
          ),
        ],
      ),
    );
  }

  Widget _buildStatItem(String label, String value, IconData icon) {
    return Expanded(
      child: Row(
        children: [
          Icon(icon, size: 12, color: AppColors.textMuted),
          const SizedBox(width: 4),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: const TextStyle(fontSize: 9, color: AppColors.textMuted),
              ),
              Text(
                value,
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _formatDuration(Duration duration) {
    if (duration.inDays > 0) {
      return '${duration.inDays}d ${duration.inHours % 24}h';
    } else if (duration.inHours > 0) {
      return '${duration.inHours}h ${duration.inMinutes % 60}m';
    } else if (duration.inMinutes > 0) {
      return '${duration.inMinutes}m ${duration.inSeconds % 60}s';
    }
    return '${duration.inSeconds}s';
  }

  Widget _buildTimelineLine(List<TimelineEvent> events) {
    return CustomPaint(
      size: const Size(double.infinity, 4),
      painter: _TimelineLinePainter(
        entranceProgress: _entranceAnimation.value,
        pulseProgress: _pulseAnimation.value,
        isOngoing: widget.data.status == 'ongoing',
      ),
    );
  }

  Widget _buildEventNode(TimelineEvent event, int index, int total) {
    final isSelected = event.id == _selectedEventId;
    final isHovered = event.id == _hoveredEventId;
    final color = _getTypeColor(event.type);
    final severityColor = _getSeverityColor(event.severity);
    final xPos = 50.0 + index * 140.0;
    final isAbove = index % 2 == 0;

    return Positioned(
      left: xPos - 30,
      top: isAbove ? 20 : 120,
      child: Opacity(
        opacity: _entranceAnimation.value,
        child: Transform.translate(
          offset: Offset(
            0,
            isAbove
                ? 30 * (1 - _entranceAnimation.value)
                : -30 * (1 - _entranceAnimation.value),
          ),
          child: MouseRegion(
            onEnter: (_) => setState(() => _hoveredEventId = event.id),
            onExit: (_) => setState(() => _hoveredEventId = null),
            child: GestureDetector(
              onTap: () => setState(
                () => _selectedEventId = _selectedEventId == event.id
                    ? null
                    : event.id,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (!isAbove) _buildEventConnector(color, isSelected),
                  // Event card
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    width: 120,
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: (isSelected || isHovered)
                          ? color.withValues(alpha: 0.2)
                          : AppColors.backgroundCard,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: isSelected ? color : AppColors.surfaceBorder,
                        width: isSelected ? 2 : 1,
                      ),
                      boxShadow: [
                        if (isSelected)
                          BoxShadow(
                            color: color.withValues(alpha: 0.3),
                            blurRadius: 12,
                            spreadRadius: 1,
                          ),
                        if (event.isCorrelatedToIncident)
                          BoxShadow(
                            color: AppColors.error.withValues(alpha: 0.2),
                            blurRadius: 8,
                            spreadRadius: 1,
                          ),
                      ],
                    ),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        // Icon and severity
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(4),
                              decoration: BoxDecoration(
                                color: color.withValues(alpha: 0.15),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Icon(
                                _getTypeIcon(event.type),
                                size: 14,
                                color: color,
                              ),
                            ),
                            const Spacer(),
                            Container(
                              width: 8,
                              height: 8,
                              decoration: BoxDecoration(
                                color: severityColor,
                                shape: BoxShape.circle,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        // Title
                        Text(
                          event.title,
                          style: const TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w500,
                            color: AppColors.textPrimary,
                          ),
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 4),
                        // Timestamp
                        Text(
                          DateFormat('HH:mm:ss').format(event.timestamp),
                          style: const TextStyle(
                            fontSize: 9,
                            color: AppColors.textMuted,
                            fontFamily: 'monospace',
                          ),
                        ),
                        // Correlation indicator
                        if (event.isCorrelatedToIncident) ...[
                          const SizedBox(height: 4),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 4,
                              vertical: 2,
                            ),
                            decoration: BoxDecoration(
                              color: AppColors.error.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: const Text(
                              'CORRELATED',
                              style: TextStyle(
                                fontSize: 7,
                                fontWeight: FontWeight.w600,
                                color: AppColors.error,
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  if (isAbove) _buildEventConnector(color, isSelected),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildEventConnector(Color color, bool isSelected) {
    return Container(
      width: 2,
      height: 20,
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            color.withValues(alpha: isSelected ? 0.8 : 0.3),
            color.withValues(alpha: isSelected ? 0.4 : 0.1),
          ],
        ),
      ),
    );
  }

  Widget _buildEventDetails() {
    final event = widget.data.events.firstWhere(
      (e) => e.id == _selectedEventId,
      orElse: () => widget.data.events.first,
    );

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: _getTypeColor(event.type).withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: _getTypeColor(event.type).withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                _getTypeIcon(event.type),
                size: 16,
                color: _getTypeColor(event.type),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  event.title,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: _getSeverityColor(
                    event.severity,
                  ).withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  event.severity.toUpperCase(),
                  style: TextStyle(
                    fontSize: 9,
                    fontWeight: FontWeight.w600,
                    color: _getSeverityColor(event.severity),
                  ),
                ),
              ),
            ],
          ),
          if (event.description != null) ...[
            const SizedBox(height: 8),
            Text(
              event.description!,
              style: const TextStyle(
                fontSize: 11,
                color: AppColors.textSecondary,
              ),
            ),
          ],
          if (event.metadata != null && event.metadata!.isNotEmpty) ...[
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: event.metadata!.entries.take(4).map((e) {
                return Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 6,
                    vertical: 3,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(4),
                  ),
                  child: Text(
                    '${e.key}: ${e.value}',
                    style: const TextStyle(
                      fontSize: 9,
                      color: AppColors.textMuted,
                      fontFamily: 'monospace',
                    ),
                  ),
                );
              }).toList(),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildRootCause() {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.warning.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: AppColors.warning.withValues(alpha: 0.3)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: AppColors.warning.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(
              Icons.lightbulb,
              size: 16,
              color: AppColors.warning,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Root Cause Analysis',
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: AppColors.warning,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  widget.data.rootCause!,
                  style: const TextStyle(
                    fontSize: 12,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Background painter for the timeline
class _TimelineBackgroundPainter extends CustomPainter {
  final double entranceProgress;

  _TimelineBackgroundPainter({required this.entranceProgress});

  @override
  void paint(Canvas canvas, Size size) {
    // Draw subtle grid pattern
    final paint = Paint()
      ..color = AppColors.surfaceBorder.withValues(
        alpha: 0.15 * entranceProgress,
      )
      ..strokeWidth = 0.5;

    const spacing = 30.0;
    for (double x = 0; x < size.width; x += spacing) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }
  }

  @override
  bool shouldRepaint(covariant _TimelineBackgroundPainter oldDelegate) {
    return oldDelegate.entranceProgress != entranceProgress;
  }
}

/// Painter for the main timeline line
class _TimelineLinePainter extends CustomPainter {
  final double entranceProgress;
  final double pulseProgress;
  final bool isOngoing;

  _TimelineLinePainter({
    required this.entranceProgress,
    required this.pulseProgress,
    required this.isOngoing,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final lineWidth = size.width * entranceProgress;

    // Draw main line
    final linePaint = Paint()
      ..shader = LinearGradient(
        colors: [
          AppColors.primaryTeal.withValues(alpha: 0.6),
          isOngoing
              ? AppColors.error.withValues(alpha: 0.6)
              : AppColors.success.withValues(alpha: 0.6),
        ],
      ).createShader(Rect.fromLTWH(0, 0, lineWidth, 4))
      ..strokeWidth = 3
      ..strokeCap = StrokeCap.round;

    canvas.drawLine(const Offset(0, 2), Offset(lineWidth, 2), linePaint);

    // Draw glow effect for ongoing incidents
    if (isOngoing) {
      final glowPaint = Paint()
        ..color = AppColors.error.withValues(alpha: 0.3 * pulseProgress)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 8);

      canvas.drawCircle(Offset(lineWidth, 2), 8 + 4 * pulseProgress, glowPaint);

      // Draw pulsing dot at the end
      final dotPaint = Paint()..color = AppColors.error;
      canvas.drawCircle(Offset(lineWidth, 2), 4 + 2 * pulseProgress, dotPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _TimelineLinePainter oldDelegate) {
    return oldDelegate.entranceProgress != entranceProgress ||
        oldDelegate.pulseProgress != pulseProgress;
  }
}
