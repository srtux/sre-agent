import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import 'burn_rate_window_row.dart';
import 'slo_burn_rate_data.dart';

// Re-export data models for backward compatibility.
export 'slo_burn_rate_data.dart';

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
                    ((_animation.value - staggerDelay * 0.3) / 0.7).clamp(
                      0.0,
                      1.0,
                    );
                return AnimatedOpacity(
                  duration: const Duration(milliseconds: 200),
                  opacity: animValue,
                  child: AnimatedSlide(
                    duration: const Duration(milliseconds: 300),
                    offset: Offset(0, (1 - animValue) * 0.1),
                    child: BurnRateWindowRow(window: data.windows[index]),
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
                        colors: [gaugeColor, gaugeColor.withValues(alpha: 0.7)],
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
        borderColor: isCritical ? AppColors.error.withValues(alpha: 0.3) : null,
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
}
