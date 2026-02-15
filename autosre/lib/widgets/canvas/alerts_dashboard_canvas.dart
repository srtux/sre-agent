import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../../models/adk_schema.dart';
import '../../theme/app_theme.dart';
import '../../theme/design_tokens.dart';

/// Alerts Dashboard Canvas - A premium, list-based view of active alerts.
class AlertsDashboardCanvas extends StatefulWidget {
  final IncidentTimelineData data;
  final Function(String)? onPromptRequest;

  const AlertsDashboardCanvas({
    super.key,
    required this.data,
    this.onPromptRequest,
  });

  @override
  State<AlertsDashboardCanvas> createState() => _AlertsDashboardCanvasState();
}

class _AlertsDashboardCanvasState extends State<AlertsDashboardCanvas> {
  @override
  Widget build(BuildContext context) {
    // Sort events by severity (critical first) and then timestamp (newest first)
    final sortedEvents = List<TimelineEvent>.from(widget.data.events)
      ..sort((a, b) {
        final sevMap = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3, 'info': 4};
        final aSev = sevMap[a.severity] ?? 5;
        final bSev = sevMap[b.severity] ?? 5;
        if (aSev != bSev) return aSev.compareTo(bSev);
        return b.timestamp.compareTo(a.timestamp);
      });

    final criticalCount = widget.data.events.where((e) => e.severity == 'critical').length;
    final highCount = widget.data.events.where((e) => e.severity == 'high').length;
    final warningCount = widget.data.events.where((e) => e.severity == 'medium').length;

    return Container(
      color: AppColors.backgroundDark,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildSummaryHeader(criticalCount, highCount, warningCount),
          Expanded(
            child: ListView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              itemCount: sortedEvents.length,
              itemBuilder: (context, index) {
                return _AlertCard(
                  event: sortedEvents[index],
                  onPromptRequest: widget.onPromptRequest,
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryHeader(int critical, int high, int warning) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
      decoration: BoxDecoration(
        color: AppColors.backgroundCard.withValues(alpha: 0.5),
        border: const Border(
          bottom: BorderSide(color: AppColors.surfaceBorder, width: 1),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Text(
                'Active Alerts',
                style: TextStyle(
                  fontSize: 18,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                  letterSpacing: -0.5,
                ),
              ),
              const Spacer(),
              _buildStatusIndicator(widget.data.status),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              _buildStatChip('Critical', critical, AppColors.error),
              const SizedBox(width: 8),
              _buildStatChip('High', high, SeverityColors.high),
              const SizedBox(width: 8),
              _buildStatChip('Warning', warning, AppColors.warning),
              const Spacer(),
              Text(
                'Total: ${widget.data.events.length}',
                style: const TextStyle(
                  fontSize: 12,
                  color: AppColors.textMuted,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildStatChip(String label, int count, Color color) {
    if (count == 0) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: color.withValues(alpha: 0.2), width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle),
          ),
          const SizedBox(width: 8),
          Text(
            '$count $label',
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatusIndicator(String status) {
    final color = status == 'ongoing'
        ? AppColors.error
        : (status == 'resolved' ? AppColors.success : AppColors.warning);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (status == 'ongoing')
            const SizedBox(
              width: 10,
              height: 10,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: AppColors.error,
              ),
            )
          else
            Icon(Icons.check_circle, size: 12, color: color),
          const SizedBox(width: 6),
          Text(
            status.toUpperCase(),
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              color: color,
              letterSpacing: 0.5,
            ),
          ),
        ],
      ),
    );
  }
}

class _AlertCard extends StatefulWidget {
  final TimelineEvent event;
  final Function(String)? onPromptRequest;

  const _AlertCard({
    required this.event,
    this.onPromptRequest,
  });

  @override
  State<_AlertCard> createState() => _AlertCardState();
}

class _AlertCardState extends State<_AlertCard> {
  bool _expanded = false;

  Color _getSeverityColor(String severity) {
    switch (severity.toLowerCase()) {
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

  @override
  Widget build(BuildContext context) {
    final event = widget.event;
    final color = _getSeverityColor(event.severity);
    final metadata = event.metadata ?? {};
    final serviceName = metadata['service_name'] ?? 'unknown_service';
    final resourceType = metadata['resource_type'] ?? 'unknown_resource';
    final state = metadata['state'] ?? 'UNKNOWN';
    final metricType = metadata['metric_type'] ?? '';

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: AppColors.backgroundCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.surfaceBorder, width: 1),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.1),
            blurRadius: 8,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () {
            setState(() {
              _expanded = !_expanded;
            });
          },
          child: IntrinsicHeight(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Severity Color Pillar
                Container(width: 4, color: color),
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: color.withValues(alpha: 0.15),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                event.severity.toUpperCase(),
                                style: TextStyle(
                                  fontSize: 9,
                                  fontWeight: FontWeight.w700,
                                  color: color,
                                  letterSpacing: 0.5,
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              DateFormat('HH:mm:ss').format(event.timestamp),
                              style: const TextStyle(
                                fontSize: 11,
                                color: AppColors.textMuted,
                                fontFamily: 'monospace',
                              ),
                            ),
                            const Spacer(),
                            if (state == 'OPEN')
                              _buildPulseIndicator()
                            else
                              Text(
                                state,
                                style: TextStyle(
                                  fontSize: 10,
                                  fontWeight: FontWeight.w600,
                                  color: state == 'CLOSED'
                                      ? AppColors.success
                                      : AppColors.textMuted,
                                ),
                              ),
                          ],
                        ),
                        const SizedBox(height: 10),
                        Text(
                          event.title,
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textPrimary,
                            height: 1.2,
                          ),
                        ),
                        const SizedBox(height: 12),
                        // Resource & Metric Info
                        Row(
                          children: [
                            _buildInfoItem(Icons.cloud_outlined, serviceName),
                            const SizedBox(width: 16),
                            _buildInfoItem(
                                Icons.category_outlined, resourceType),
                          ],
                        ),
                        if (metricType.isNotEmpty) ...[
                          const SizedBox(height: 8),
                          _buildInfoItem(Icons.show_chart_rounded, metricType),
                        ],
                        if (_expanded) _buildExpandedContent(event),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildExpandedContent(TimelineEvent event) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (event.description != null && event.description!.isNotEmpty) ...[
          const SizedBox(height: 16),
          const Divider(height: 1, color: AppColors.surfaceBorder),
          const SizedBox(height: 12),
          Text(
            event.description!,
            style: const TextStyle(
              fontSize: 13,
              color: AppColors.textSecondary,
              height: 1.4,
            ),
          ),
        ],
        if (event.metadata != null && event.metadata!.isNotEmpty) ...[
          const SizedBox(height: 12),
          const Divider(height: 1, color: AppColors.surfaceBorder),
          const SizedBox(height: 12),
          ...event.metadata!.entries.where((e) {
            final k = e.key;
            return k != 'service_name' &&
                k != 'resource_type' &&
                k != 'state' &&
                k != 'metric_type';
          }).map((e) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 6.0),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${e.key}: ',
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 12,
                      color: AppColors.textSecondary,
                    ),
                  ),
                  Expanded(
                    child: Text(
                      e.value.toString(),
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppColors.textMuted,
                        fontFamily: 'monospace',
                      ),
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
        // Remediation Action Button
        const SizedBox(height: 16),
        const Divider(height: 1, color: AppColors.surfaceBorder),
        const SizedBox(height: 12),
        SizedBox(
          width: double.infinity,
          child: ElevatedButton.icon(
            onPressed: () {
              if (widget.onPromptRequest != null) {
                widget.onPromptRequest!(
                    'Generate remediation suggestions for alert: ${event.title}');
              }
            },
            style: ElevatedButton.styleFrom(
              backgroundColor: AppColors.secondaryPurple.withValues(alpha: 0.1),
              foregroundColor: AppColors.secondaryPurple,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
                side: BorderSide(
                    color: AppColors.secondaryPurple.withValues(alpha: 0.3)),
              ),
              padding: const EdgeInsets.symmetric(vertical: 12),
              elevation: 0,
            ),
            icon: const Icon(Icons.build_circle_outlined, size: 16),
            label: const Text(
              'Generate Remediation Plan',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildInfoItem(IconData icon, String text) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 12, color: AppColors.textMuted),
        const SizedBox(width: 6),
        Flexible(
          child: Text(
            text,
            style: const TextStyle(
              fontSize: 11,
              color: AppColors.textSecondary,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildPulseIndicator() {
    return Container(
      width: 8,
      height: 8,
      decoration: const BoxDecoration(
        color: AppColors.error,
        shape: BoxShape.circle,
        boxShadow: [
          BoxShadow(
            color: AppColors.error,
            blurRadius: 4,
            spreadRadius: 1,
          ),
        ],
      ),
    );
  }
}
