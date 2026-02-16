// Data models for SLO burn rate analysis.
//
// Extracted from SloBurnRateCard to reduce file size and improve reusability.

/// Severity levels for SLO burn rate analysis.
enum BurnRateSeverity { ok, warning, critical }

/// A single burn-rate analysis window.
class BurnRateWindow {
  final String name;
  final String label;
  final double burnRate;
  final double threshold;
  final bool alertTriggered;
  final Duration windowDuration;

  const BurnRateWindow({
    required this.name,
    required this.label,
    required this.burnRate,
    required this.threshold,
    required this.alertTriggered,
    required this.windowDuration,
  });

  factory BurnRateWindow.fromJson(Map<String, dynamic> json) {
    return BurnRateWindow(
      name: json['name'] as String? ?? 'unknown',
      label: json['label'] as String? ?? 'Unknown Window',
      burnRate: (json['burn_rate'] as num?)?.toDouble() ?? 0.0,
      threshold: (json['threshold'] as num?)?.toDouble() ?? 1.0,
      alertTriggered: json['alert_triggered'] as bool? ?? false,
      windowDuration: Duration(
        minutes: (json['window_minutes'] as num?)?.toInt() ?? 60,
      ),
    );
  }
}

/// Data model for SLO burn rate analysis.
class SloBurnRateData {
  final String sloName;
  final double targetPercentage;
  final BurnRateSeverity severity;
  final double errorBudgetRemainingFraction;
  final double? hoursToExhaustion;
  final List<BurnRateWindow> windows;
  final String? summary;

  const SloBurnRateData({
    required this.sloName,
    required this.targetPercentage,
    required this.severity,
    required this.errorBudgetRemainingFraction,
    this.hoursToExhaustion,
    required this.windows,
    this.summary,
  });

  factory SloBurnRateData.fromJson(Map<String, dynamic> json) {
    final severityStr = (json['severity'] as String? ?? 'ok').toLowerCase();
    final BurnRateSeverity severity;
    switch (severityStr) {
      case 'critical':
        severity = BurnRateSeverity.critical;
      case 'warning':
        severity = BurnRateSeverity.warning;
      default:
        severity = BurnRateSeverity.ok;
    }

    final windowsList = json['windows'] as List<dynamic>? ?? [];

    return SloBurnRateData(
      sloName: json['slo_name'] as String? ?? 'SLO',
      targetPercentage: (json['target_percentage'] as num?)?.toDouble() ?? 99.9,
      severity: severity,
      errorBudgetRemainingFraction:
          (json['error_budget_remaining_fraction'] as num?)?.toDouble() ?? 1.0,
      hoursToExhaustion: (json['hours_to_exhaustion'] as num?)?.toDouble(),
      windows: windowsList
          .map((w) => BurnRateWindow.fromJson(Map<String, dynamic>.from(w)))
          .toList(),
      summary: json['summary'] as String?,
    );
  }
}
