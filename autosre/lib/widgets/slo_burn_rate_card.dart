import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

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
      targetPercentage:
          (json['target_percentage'] as num?)?.toDouble() ?? 99.9,
      severity: severity,
      errorBudgetRemainingFraction:
          (json['error_budget_remaining_fraction'] as num?)?.toDouble() ?? 1.0,
      hoursToExhaustion:
          (json['hours_to_exhaustion'] as num?)?.toDouble(),
      windows: windowsList
          .map((w) => BurnRateWindow.fromJson(Map<String, dynamic>.from(w)))
          .toList(),
      summary: json['summary'] as String?,
    );
  }
}

/// Displays SLO multi-window burn rate analysis with a Deep Space aesthetic.
class SloBurnRateCard extends StatefulWidget {
  final SloBurnRateData data;

  const SloBurnRateCard({super.key, required this.data});

  @override
  State<SloBurnRateCard> createState() => _SloBurnRateCardState();
}

class _SloBurnRateCardState extends State<SloBurnRateCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _animController;
  late Animation<double> _animation;
  final Set<int> _expandedWindows = {};

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

  Color _severityColor(BurnRateSeverity severity) {
    switch (severity) {
      case BurnRateSeverity.critical:
        return AppColors.error;
      case BurnRateSeverity.warning:
        return AppColors.warning;
      case BurnRateSeverity.ok:
        return AppColors.success;
    }
  }

  IconData _severityIcon(BurnRateSeverity severity) {
    switch (severity) {
      case BurnRateSeverity.critical:
        return Icons.error_rounded;
      case BurnRateSeverity.warning:
        return Icons.warning_rounded;
      case BurnRateSeverity.ok:
        return Icons.check_circle_rounded;
    }
  }

  String _severityLabel(BurnRateSeverity severity) {
    switch (severity) {
      case BurnRateSeverity.critical:
        return 'CRITICAL';
      case BurnRateSeverity.warning:
        return 'WARNING';
      case BurnRateSeverity.ok:
        return 'OK';
    }
  }

  String _formatDuration(Duration d) {
    if (d.inHours >= 24) {
      final days = d.inDays;
      return '${days}d';
    } else if (d.inHours > 0) {
      return '${d.inHours}h';
    }
    return '${d.inMinutes}m';
  }

  @override
  Widget build(BuildContext context) {
    final data = widget.data;
    final color = _severityColor(data.severity);

    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        return Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              // Header row
              _buildHeader(data, color),
              const SizedBox(height: 16),

              // SLO target + Error budget gauge
              _buildBudgetSection(data, color),
              const SizedBox(height: 16),

              // Exhaustion projection
              if (data.hoursToExhaustion != null)
                _buildExhaustionProjection(data.hoursToExhaustion!, color),
              if (data.hoursToExhaustion != null) const SizedBox(height: 16),

              // Summary
              if (data.summary != null && data.summary!.isNotEmpty)
                _buildSummary(data.summary!),
              if (data.summary != null && data.summary!.isNotEmpty)
                const SizedBox(height: 16),

              // Window analysis breakdown
              if (data.windows.isNotEmpty)
                const Text(
                  'Window Analysis',
                  style: TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
              if (data.windows.isNotEmpty) const SizedBox(height: 10),

              // Window list
              ...List.generate(data.windows.length, (index) {
                final staggerDelay = index / data.windows.length;
                final animValue =
                    ((_animation.value - staggerDelay * 0.3) / 0.7)
                        .clamp(0.0, 1.0);
                return AnimatedOpacity(
                  duration: const Duration(milliseconds: 200),
                  opacity: animValue,
                  child: AnimatedSlide(
                    duration: const Duration(milliseconds: 300),
                    offset: Offset(0, (1 - animValue) * 0.1),
                    child: _buildWindowRow(data.windows[index], index),
                  ),
                );
              }),
            ],
          ),
        );
      },
    );
  }

  Widget _buildHeader(SloBurnRateData data, Color color) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Icon
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                color.withValues(alpha: 0.2),
                color.withValues(alpha: 0.1),
              ],
            ),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: color.withValues(alpha: 0.3)),
          ),
          child: Icon(Icons.speed_rounded, size: 24, color: color),
        ),
        const SizedBox(width: 14),

        // Title
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'SLO Burn Rate',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                data.sloName,
                style: const TextStyle(
                  fontSize: 13,
                  color: AppColors.textSecondary,
                  height: 1.4,
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
            color: color.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: color.withValues(alpha: 0.3)),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(_severityIcon(data.severity), size: 16, color: color),
              const SizedBox(width: 6),
              Text(
                _severityLabel(data.severity),
                style: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: color,
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildBudgetSection(SloBurnRateData data, Color color) {
    final remaining = data.errorBudgetRemainingFraction.clamp(0.0, 1.0);
    final remainingPercent = (remaining * 100).toStringAsFixed(1);

    // Choose gauge color based on remaining budget
    final Color gaugeColor;
    if (remaining > 0.5) {
      gaugeColor = AppColors.success;
    } else if (remaining > 0.2) {
      gaugeColor = AppColors.warning;
    } else {
      gaugeColor = AppColors.error;
    }

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: GlassDecoration.card(borderRadius: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              // SLO Target
              Row(
                children: [
                  const Icon(
                    Icons.flag_rounded,
                    size: 16,
                    color: AppColors.textMuted,
                  ),
                  const SizedBox(width: 6),
                  const Text(
                    'SLO Target',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                      color: AppColors.textMuted,
                    ),
                  ),
                  const SizedBox(width: 8),
                  Text(
                    '${data.targetPercentage}%',
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      color: AppColors.primaryCyan,
                    ),
                  ),
                ],
              ),
              // Budget remaining label
              Text(
                '$remainingPercent% budget remaining',
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w500,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Error budget gauge
          Stack(
            children: [
              // Background
              Container(
                height: 10,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(5),
                ),
              ),
              // Filled portion
              LayoutBuilder(
                builder: (context, constraints) {
                  return AnimatedContainer(
                    duration: const Duration(milliseconds: 600),
                    curve: Curves.easeOutCubic,
                    height: 10,
                    width: constraints.maxWidth * remaining * _animation.value,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        colors: [
                          gaugeColor,
                          gaugeColor.withValues(alpha: 0.7),
                        ],
                      ),
                      borderRadius: BorderRadius.circular(5),
                      boxShadow: [
                        BoxShadow(
                          color: gaugeColor.withValues(alpha: 0.4),
                          blurRadius: 8,
                          offset: const Offset(0, 2),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildExhaustionProjection(double hours, Color color) {
    final String timeLabel;
    if (hours >= 168) {
      timeLabel = '${(hours / 168).toStringAsFixed(1)} weeks';
    } else if (hours >= 24) {
      timeLabel = '${(hours / 24).toStringAsFixed(1)} days';
    } else {
      timeLabel = '${hours.toStringAsFixed(1)} hours';
    }

    final isCritical = hours < 24;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: GlassDecoration.card(
        borderRadius: 10,
        borderColor: isCritical
            ? AppColors.error.withValues(alpha: 0.3)
            : null,
      ),
      child: Row(
        children: [
          Icon(
            Icons.timer_outlined,
            size: 18,
            color: isCritical ? AppColors.error : AppColors.textMuted,
          ),
          const SizedBox(width: 10),
          const Text(
            'Budget Exhaustion in',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w500,
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(width: 8),
          Text(
            timeLabel,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w700,
              color: isCritical ? AppColors.error : AppColors.primaryCyan,
            ),
          ),
          if (isCritical) ...[
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: AppColors.error.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(4),
              ),
              child: const Text(
                'URGENT',
                style: TextStyle(
                  fontSize: 9,
                  fontWeight: FontWeight.w700,
                  color: AppColors.error,
                  letterSpacing: 0.5,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildSummary(String summary) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: GlassDecoration.card(borderRadius: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(
            Icons.info_outline_rounded,
            size: 16,
            color: AppColors.info,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              summary,
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
  }

  Widget _buildWindowRow(BurnRateWindow window, int index) {
    final isExpanded = _expandedWindows.contains(index);
    final isTriggered = window.alertTriggered;
    final burnRatio = (window.burnRate / window.threshold).clamp(0.0, 2.0);

    final Color windowColor;
    if (isTriggered) {
      windowColor = AppColors.error;
    } else if (burnRatio > 0.7) {
      windowColor = AppColors.warning;
    } else {
      windowColor = AppColors.success;
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: GlassDecoration.card(
        borderRadius: 10,
        borderColor:
            isTriggered ? AppColors.error.withValues(alpha: 0.3) : null,
      ),
      child: Column(
        children: [
          InkWell(
            onTap: () {
              setState(() {
                if (_expandedWindows.contains(index)) {
                  _expandedWindows.remove(index);
                } else {
                  _expandedWindows.add(index);
                }
              });
            },
            borderRadius: BorderRadius.circular(10),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                children: [
                  // Alert status indicator
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: windowColor,
                      shape: BoxShape.circle,
                      boxShadow: [
                        if (isTriggered)
                          BoxShadow(
                            color: windowColor.withValues(alpha: 0.6),
                            blurRadius: 6,
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 10),

                  // Window label
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          window.label,
                          style: const TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w500,
                            color: AppColors.textPrimary,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          _formatDuration(window.windowDuration),
                          style: const TextStyle(
                            fontSize: 11,
                            color: AppColors.textMuted,
                          ),
                        ),
                      ],
                    ),
                  ),

                  // Burn rate value
                  Text(
                    '${window.burnRate.toStringAsFixed(2)}x',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      fontFamily: 'monospace',
                      color: windowColor,
                    ),
                  ),
                  const SizedBox(width: 8),

                  // Alert triggered badge
                  if (isTriggered)
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 6,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: AppColors.error.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(
                          color: AppColors.error.withValues(alpha: 0.3),
                        ),
                      ),
                      child: const Text(
                        'ALERT',
                        style: TextStyle(
                          fontSize: 9,
                          fontWeight: FontWeight.w700,
                          color: AppColors.error,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ),

                  const SizedBox(width: 6),

                  // Expand chevron
                  AnimatedRotation(
                    duration: const Duration(milliseconds: 200),
                    turns: isExpanded ? 0.5 : 0,
                    child: const Icon(
                      Icons.expand_more,
                      size: 18,
                      color: AppColors.textMuted,
                    ),
                  ),
                ],
              ),
            ),
          ),

          // Expanded details
          AnimatedCrossFade(
            duration: const Duration(milliseconds: 200),
            firstChild: Padding(
              padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Burn rate bar
                  Row(
                    children: [
                      const Text(
                        'Burn Rate',
                        style: TextStyle(
                          fontSize: 11,
                          color: AppColors.textMuted,
                        ),
                      ),
                      const Spacer(),
                      Text(
                        'Threshold: ${window.threshold.toStringAsFixed(1)}x',
                        style: const TextStyle(
                          fontSize: 11,
                          color: AppColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Stack(
                    children: [
                      Container(
                        height: 6,
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(3),
                        ),
                      ),
                      LayoutBuilder(
                        builder: (context, constraints) {
                          final barWidth = constraints.maxWidth *
                              (burnRatio / 2.0).clamp(0.0, 1.0);
                          return Container(
                            height: 6,
                            width: barWidth,
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                colors: [
                                  windowColor,
                                  windowColor.withValues(alpha: 0.7),
                                ],
                              ),
                              borderRadius: BorderRadius.circular(3),
                            ),
                          );
                        },
                      ),
                      // Threshold marker
                      LayoutBuilder(
                        builder: (context, constraints) {
                          final markerPos = constraints.maxWidth *
                              (window.threshold / (window.threshold * 2.0))
                                  .clamp(0.0, 1.0);
                          return Positioned(
                            left: markerPos,
                            child: Container(
                              width: 2,
                              height: 6,
                              color: AppColors.textSecondary,
                            ),
                          );
                        },
                      ),
                    ],
                  ),
                ],
              ),
            ),
            secondChild: const SizedBox.shrink(),
            crossFadeState: isExpanded
                ? CrossFadeState.showFirst
                : CrossFadeState.showSecond,
          ),
        ],
      ),
    );
  }
}
