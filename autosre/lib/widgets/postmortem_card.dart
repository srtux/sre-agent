import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Priority level for postmortem action items.
enum ActionPriority { p0, p1, p2 }

/// A single event in the postmortem timeline.
class PostmortemTimelineEvent {
  final String timestamp;
  final String description;
  final String? actor;

  const PostmortemTimelineEvent({
    required this.timestamp,
    required this.description,
    this.actor,
  });

  factory PostmortemTimelineEvent.fromJson(Map<String, dynamic> json) {
    return PostmortemTimelineEvent(
      timestamp: json['timestamp'] as String? ?? '',
      description: json['description'] as String? ?? '',
      actor: json['actor'] as String?,
    );
  }
}

/// An action item from the postmortem.
class PostmortemActionItem {
  final String description;
  final ActionPriority priority;
  final String? owner;
  final bool completed;

  const PostmortemActionItem({
    required this.description,
    required this.priority,
    this.owner,
    this.completed = false,
  });

  factory PostmortemActionItem.fromJson(Map<String, dynamic> json) {
    final priorityStr =
        (json['priority'] as String? ?? 'p2').toLowerCase();
    final ActionPriority priority;
    switch (priorityStr) {
      case 'p0':
        priority = ActionPriority.p0;
      case 'p1':
        priority = ActionPriority.p1;
      default:
        priority = ActionPriority.p2;
    }

    return PostmortemActionItem(
      description: json['description'] as String? ?? '',
      priority: priority,
      owner: json['owner'] as String?,
      completed: json['completed'] as bool? ?? false,
    );
  }
}

/// Data model for a generated postmortem report.
class PostmortemData {
  final String title;
  final String severity;
  final String? impactSummary;
  final String? errorBudgetConsumed;
  final String? duration;
  final List<PostmortemTimelineEvent> timeline;
  final String? rootCause;
  final List<PostmortemActionItem> actionItems;
  final List<String> whatWentWell;
  final List<String> whatWentPoorly;

  const PostmortemData({
    required this.title,
    required this.severity,
    this.impactSummary,
    this.errorBudgetConsumed,
    this.duration,
    this.timeline = const [],
    this.rootCause,
    this.actionItems = const [],
    this.whatWentWell = const [],
    this.whatWentPoorly = const [],
  });

  factory PostmortemData.fromJson(Map<String, dynamic> json) {
    final timelineRaw = json['timeline'] as List<dynamic>? ?? [];
    final actionsRaw = json['action_items'] as List<dynamic>? ?? [];
    final wellRaw = json['what_went_well'] as List<dynamic>? ?? [];
    final poorlyRaw = json['what_went_poorly'] as List<dynamic>? ?? [];

    return PostmortemData(
      title: json['title'] as String? ?? 'Postmortem Report',
      severity: json['severity'] as String? ?? 'unknown',
      impactSummary: json['impact_summary'] as String?,
      errorBudgetConsumed: json['error_budget_consumed'] as String?,
      duration: json['duration'] as String?,
      timeline: timelineRaw
          .map((e) =>
              PostmortemTimelineEvent.fromJson(Map<String, dynamic>.from(e)))
          .toList(),
      rootCause: json['root_cause'] as String?,
      actionItems: actionsRaw
          .map((e) =>
              PostmortemActionItem.fromJson(Map<String, dynamic>.from(e)))
          .toList(),
      whatWentWell: wellRaw.map((e) => e.toString()).toList(),
      whatWentPoorly: poorlyRaw.map((e) => e.toString()).toList(),
    );
  }
}

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
  bool _timelineExpanded = false;
  final Set<int> _checkedActions = {};

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

    // Pre-populate checked actions from data
    for (int i = 0; i < widget.data.actionItems.length; i++) {
      if (widget.data.actionItems[i].completed) {
        _checkedActions.add(i);
      }
    }
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

  Color _priorityColor(ActionPriority priority) {
    switch (priority) {
      case ActionPriority.p0:
        return AppColors.error;
      case ActionPriority.p1:
        return AppColors.warning;
      case ActionPriority.p2:
        return AppColors.info;
    }
  }

  String _priorityLabel(ActionPriority priority) {
    switch (priority) {
      case ActionPriority.p0:
        return 'P0';
      case ActionPriority.p1:
        return 'P1';
      case ActionPriority.p2:
        return 'P2';
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
              if (data.timeline.isNotEmpty) _buildTimelineSection(data.timeline),
              if (data.timeline.isNotEmpty) const SizedBox(height: 16),

              // Root cause
              if (data.rootCause != null && data.rootCause!.isNotEmpty)
                _buildRootCauseSection(data.rootCause!),
              if (data.rootCause != null && data.rootCause!.isNotEmpty)
                const SizedBox(height: 16),

              // Action items
              if (data.actionItems.isNotEmpty)
                _buildActionItemsSection(data.actionItems),
              if (data.actionItems.isNotEmpty) const SizedBox(height: 16),

              // Lessons learned
              if (data.whatWentWell.isNotEmpty || data.whatWentPoorly.isNotEmpty)
                _buildLessonsSection(data.whatWentWell, data.whatWentPoorly),
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
              Icon(Icons.impact_rounded, size: 16, color: AppColors.warning),
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

  Widget _buildTimelineSection(List<PostmortemTimelineEvent> timeline) {
    return Container(
      decoration: GlassDecoration.card(borderRadius: 12),
      child: Column(
        children: [
          // Timeline header (tappable to expand/collapse)
          InkWell(
            onTap: () {
              setState(() {
                _timelineExpanded = !_timelineExpanded;
              });
            },
            borderRadius: BorderRadius.circular(12),
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Row(
                children: [
                  const Icon(
                    Icons.timeline_rounded,
                    size: 16,
                    color: AppColors.primaryCyan,
                  ),
                  const SizedBox(width: 8),
                  const Text(
                    'Timeline of Events',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(
                      color: AppColors.primaryCyan.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      '${timeline.length}',
                      style: const TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                        color: AppColors.primaryCyan,
                      ),
                    ),
                  ),
                  const Spacer(),
                  AnimatedRotation(
                    duration: const Duration(milliseconds: 200),
                    turns: _timelineExpanded ? 0.5 : 0,
                    child: const Icon(
                      Icons.expand_more,
                      color: AppColors.textMuted,
                    ),
                  ),
                ],
              ),
            ),
          ),

          // Timeline events
          AnimatedCrossFade(
            duration: const Duration(milliseconds: 200),
            firstChild: Padding(
              padding: const EdgeInsets.fromLTRB(14, 0, 14, 14),
              child: Column(
                children: List.generate(timeline.length, (index) {
                  final event = timeline[index];
                  final isLast = index == timeline.length - 1;
                  return _buildTimelineEvent(event, isLast);
                }),
              ),
            ),
            secondChild: const SizedBox.shrink(),
            crossFadeState: _timelineExpanded
                ? CrossFadeState.showFirst
                : CrossFadeState.showSecond,
          ),
        ],
      ),
    );
  }

  Widget _buildTimelineEvent(PostmortemTimelineEvent event, bool isLast) {
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Dot + Line
          SizedBox(
            width: 24,
            child: Column(
              children: [
                const SizedBox(height: 4),
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: AppColors.primaryCyan,
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: AppColors.primaryCyan.withValues(alpha: 0.4),
                        blurRadius: 4,
                      ),
                    ],
                  ),
                ),
                if (!isLast)
                  Expanded(
                    child: Container(
                      width: 1,
                      color: AppColors.surfaceBorder,
                    ),
                  ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          // Content
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(
                        event.timestamp,
                        style: const TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          fontFamily: 'monospace',
                          color: AppColors.primaryCyan,
                        ),
                      ),
                      if (event.actor != null) ...[
                        const SizedBox(width: 8),
                        Text(
                          event.actor!,
                          style: const TextStyle(
                            fontSize: 11,
                            color: AppColors.textMuted,
                          ),
                        ),
                      ],
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    event.description,
                    style: const TextStyle(
                      fontSize: 13,
                      color: AppColors.textSecondary,
                      height: 1.4,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
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

  Widget _buildActionItemsSection(List<PostmortemActionItem> items) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          children: [
            Icon(Icons.checklist_rounded, size: 16, color: AppColors.primaryTeal),
            SizedBox(width: 8),
            Text(
              'Action Items',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        ...List.generate(items.length, (index) {
          final item = items[index];
          final isChecked = _checkedActions.contains(index);
          final pColor = _priorityColor(item.priority);
          final pLabel = _priorityLabel(item.priority);

          final staggerDelay = index / items.length;
          final animValue =
              ((_animation.value - staggerDelay * 0.3) / 0.7).clamp(0.0, 1.0);

          return AnimatedOpacity(
            duration: const Duration(milliseconds: 200),
            opacity: animValue,
            child: AnimatedSlide(
              duration: const Duration(milliseconds: 300),
              offset: Offset(0, (1 - animValue) * 0.1),
              child: Container(
                margin: const EdgeInsets.only(bottom: 8),
                decoration: GlassDecoration.card(
                  borderRadius: 10,
                  borderColor: isChecked
                      ? AppColors.success.withValues(alpha: 0.3)
                      : null,
                ),
                child: InkWell(
                  onTap: () {
                    setState(() {
                      if (_checkedActions.contains(index)) {
                        _checkedActions.remove(index);
                      } else {
                        _checkedActions.add(index);
                      }
                    });
                  },
                  borderRadius: BorderRadius.circular(10),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Row(
                      children: [
                        // Checkbox
                        AnimatedContainer(
                          duration: const Duration(milliseconds: 200),
                          width: 22,
                          height: 22,
                          decoration: BoxDecoration(
                            gradient: isChecked
                                ? LinearGradient(
                                    colors: [
                                      AppColors.success,
                                      AppColors.success.withValues(alpha: 0.8),
                                    ],
                                  )
                                : null,
                            color: isChecked
                                ? null
                                : Colors.white.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(
                              color: isChecked
                                  ? AppColors.success
                                  : AppColors.surfaceBorder,
                            ),
                          ),
                          child: isChecked
                              ? const Icon(
                                  Icons.check,
                                  size: 14,
                                  color: Colors.white,
                                )
                              : null,
                        ),
                        const SizedBox(width: 10),

                        // Priority badge
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 6,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: pColor.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(
                              color: pColor.withValues(alpha: 0.3),
                            ),
                          ),
                          child: Text(
                            pLabel,
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                              color: pColor,
                              letterSpacing: 0.5,
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),

                        // Description
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                item.description,
                                style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w500,
                                  color: isChecked
                                      ? AppColors.textMuted
                                      : AppColors.textPrimary,
                                  decoration: isChecked
                                      ? TextDecoration.lineThrough
                                      : null,
                                ),
                              ),
                              if (item.owner != null) ...[
                                const SizedBox(height: 2),
                                Text(
                                  'Owner: ${item.owner}',
                                  style: const TextStyle(
                                    fontSize: 11,
                                    color: AppColors.textMuted,
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          );
        }),
      ],
    );
  }

  Widget _buildLessonsSection(
    List<String> wentWell,
    List<String> wentPoorly,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          children: [
            Icon(Icons.school_rounded, size: 16, color: AppColors.secondaryPurple),
            SizedBox(width: 8),
            Text(
              'Lessons Learned',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),

        // What went well
        if (wentWell.isNotEmpty)
          _buildLessonsList(
            title: 'What Went Well',
            items: wentWell,
            icon: Icons.thumb_up_alt_rounded,
            color: AppColors.success,
          ),
        if (wentWell.isNotEmpty && wentPoorly.isNotEmpty)
          const SizedBox(height: 10),

        // What went poorly
        if (wentPoorly.isNotEmpty)
          _buildLessonsList(
            title: 'What Went Poorly',
            items: wentPoorly,
            icon: Icons.thumb_down_alt_rounded,
            color: AppColors.error,
          ),
      ],
    );
  }

  Widget _buildLessonsList({
    required String title,
    required List<String> items,
    required IconData icon,
    required Color color,
  }) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: GlassDecoration.card(
        borderRadius: 10,
        borderColor: color.withValues(alpha: 0.2),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 14, color: color),
              const SizedBox(width: 6),
              Text(
                title,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: color,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ...items.map((item) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Container(
                      width: 4,
                      height: 4,
                      decoration: BoxDecoration(
                        color: color.withValues(alpha: 0.6),
                        shape: BoxShape.circle,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      item,
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppColors.textSecondary,
                        height: 1.5,
                      ),
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }
}
