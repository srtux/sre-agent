import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import 'postmortem_action_items.dart';
import 'postmortem_data.dart';
import 'postmortem_lessons.dart';
import 'postmortem_timeline.dart';

// Re-export data models for backward compatibility.
export 'postmortem_data.dart';

/// Displays a generated postmortem report with Deep Space aesthetic.
class PostmortemCard extends StatefulWidget {
  final PostmortemData data;

  const PostmortemCard({super.key, required this.data});

  @override
  State<PostmortemCard> createState() => _PostmortemCardState();
}

class _PostmortemCardState extends State<PostmortemCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _animController;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      duration: const Duration(milliseconds: 800),
      vsync: this,
    );
    _animation = CurvedAnimation(
      parent: _animController,
      curve: Curves.easeOutCubic,
    );
    _animController.forward();
  }

  @override
  void dispose() {
    _animController.dispose();
    super.dispose();
  }

  Color _severityColor(String severity) {
    switch (severity.toLowerCase()) {
      case 'critical':
      case 'p0':
        return AppColors.error;
      case 'high':
      case 'p1':
        return AppColors.warning;
      case 'medium':
      case 'p2':
        return AppColors.info;
      case 'low':
        return AppColors.success;
      default:
        return AppColors.textMuted;
    }
  }

  @override
  Widget build(BuildContext context) {
    final data = widget.data;
    final sevColor = _severityColor(data.severity);

    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        return SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              _buildHeader(data, sevColor),
              const SizedBox(height: 16),

              // Impact summary
              if (data.impactSummary != null ||
                  data.errorBudgetConsumed != null ||
                  data.duration != null)
                _buildImpactSection(data),
              if (data.impactSummary != null ||
                  data.errorBudgetConsumed != null ||
                  data.duration != null)
                const SizedBox(height: 16),

              // Timeline
              if (data.timeline.isNotEmpty)
                PostmortemTimeline(timeline: data.timeline),
              if (data.timeline.isNotEmpty) const SizedBox(height: 16),

              // Root cause
              if (data.rootCause != null && data.rootCause!.isNotEmpty)
                _buildRootCauseSection(data.rootCause!),
              if (data.rootCause != null && data.rootCause!.isNotEmpty)
                const SizedBox(height: 16),

              // Action items
              if (data.actionItems.isNotEmpty)
                PostmortemActionItems(
                  items: data.actionItems,
                  animation: _animation,
                ),
              if (data.actionItems.isNotEmpty) const SizedBox(height: 16),

              // Lessons learned
              if (data.whatWentWell.isNotEmpty || data.whatWentPoorly.isNotEmpty)
                PostmortemLessons(
                  whatWentWell: data.whatWentWell,
                  whatWentPoorly: data.whatWentPoorly,
                ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildHeader(PostmortemData data, Color sevColor) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Icon
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                AppColors.secondaryPurple.withValues(alpha: 0.2),
                AppColors.secondaryPurple.withValues(alpha: 0.1),
              ],
            ),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: AppColors.secondaryPurple.withValues(alpha: 0.3),
            ),
          ),
          child: const Icon(
            Icons.assignment_rounded,
            size: 24,
            color: AppColors.secondaryPurple,
          ),
        ),
        const SizedBox(width: 14),

        // Title
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Postmortem Report',
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w500,
                  color: AppColors.textMuted,
                  letterSpacing: 0.5,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                data.title,
                style: const TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                  height: 1.3,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(width: 12),

        // Severity badge
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: sevColor.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: sevColor.withValues(alpha: 0.3)),
          ),
          child: Text(
            data.severity.toUpperCase(),
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: sevColor,
              letterSpacing: 0.5,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildImpactSection(PostmortemData data) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: GlassDecoration.card(borderRadius: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.bolt_rounded, size: 16, color: AppColors.warning),
              SizedBox(width: 8),
              Text(
                'Impact Summary',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Impact description
          if (data.impactSummary != null)
            Text(
              data.impactSummary!,
              style: const TextStyle(
                fontSize: 13,
                color: AppColors.textSecondary,
                height: 1.5,
              ),
            ),
          if (data.impactSummary != null) const SizedBox(height: 12),

          // Metrics row
          Row(
            children: [
              if (data.errorBudgetConsumed != null)
                _buildImpactChip(
                  Icons.data_usage_rounded,
                  'Budget Used',
                  data.errorBudgetConsumed!,
                  AppColors.error,
                ),
              if (data.errorBudgetConsumed != null) const SizedBox(width: 12),
              if (data.duration != null)
                _buildImpactChip(
                  Icons.timer_outlined,
                  'Duration',
                  data.duration!,
                  AppColors.warning,
                ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildImpactChip(
    IconData icon,
    String label,
    String value,
    Color color,
  ) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: color.withValues(alpha: 0.2)),
        ),
        child: Row(
          children: [
            Icon(icon, size: 14, color: color),
            const SizedBox(width: 6),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: const TextStyle(
                      fontSize: 10,
                      color: AppColors.textMuted,
                    ),
                  ),
                  Text(
                    value,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: color,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRootCauseSection(String rootCause) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: GlassDecoration.card(
        borderRadius: 12,
        borderColor: AppColors.error.withValues(alpha: 0.2),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.search_rounded, size: 16, color: AppColors.error),
              SizedBox(width: 8),
              Text(
                'Root Cause',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            rootCause,
            style: const TextStyle(
              fontSize: 13,
              color: AppColors.textSecondary,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }
}
