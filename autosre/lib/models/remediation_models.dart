import 'package:flutter/foundation.dart';

/// A single step in a remediation plan.
class RemediationStep {
  final String command;
  final String description;

  RemediationStep({required this.command, required this.description});

  factory RemediationStep.fromJson(Map<String, dynamic> json) {
    return RemediationStep(
      command: json['command'] as String? ?? '',
      description: json['description'] as String? ?? '',
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is RemediationStep &&
          runtimeType == other.runtimeType &&
          command == other.command &&
          description == other.description;

  @override
  int get hashCode => Object.hash(command, description);
}

/// A remediation plan with risk assessment and ordered steps.
class RemediationPlan {
  final String issue;
  final String risk; // 'low', 'medium', 'high'
  final List<RemediationStep> steps;

  RemediationPlan({
    required this.issue,
    required this.risk,
    required this.steps,
  });

  factory RemediationPlan.fromJson(Map<String, dynamic> json) {
    final stepsList = (json['steps'] as List? ?? [])
        .whereType<Map>()
        .map((i) => RemediationStep.fromJson(Map<String, dynamic>.from(i)))
        .toList();
    return RemediationPlan(
      issue: json['issue'] as String? ?? '',
      risk: json['risk'] as String? ?? 'low',
      steps: stepsList,
    );
  }

  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is RemediationPlan &&
          runtimeType == other.runtimeType &&
          issue == other.issue &&
          risk == other.risk &&
          listEquals(steps, other.steps);

  @override
  int get hashCode => Object.hash(issue, risk, steps.length);
}
