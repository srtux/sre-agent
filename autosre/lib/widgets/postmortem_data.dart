// Data models for postmortem reports.
//
// Extracted from PostmortemCard to reduce file size and improve reusability.

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
