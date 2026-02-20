import 'package:flutter/material.dart';

import '../../../theme/app_theme.dart';

/// A compact, reusable badge widget for displaying metrics inline on
/// agent graph nodes.
///
/// Use the named constructors for common metric types:
/// [MetricBadge.latency], [MetricBadge.cost], [MetricBadge.tokens],
/// [MetricBadge.errorRate], [MetricBadge.subcalls].
class MetricBadge extends StatelessWidget {
  /// Icon displayed before the value.
  final IconData icon;

  /// Formatted metric value string.
  final String value;

  /// Badge accent color.
  final Color color;

  /// Optional tooltip text shown on hover.
  final String? tooltip;

  const MetricBadge({
    super.key,
    required this.icon,
    required this.value,
    required this.color,
    this.tooltip,
  });

  /// Latency badge with a clock icon and formatted duration.
  factory MetricBadge.latency(double ms) {
    return MetricBadge(
      icon: Icons.schedule,
      value: _formatDuration(ms),
      color: AppColors.success,
      tooltip: '${ms.toStringAsFixed(1)} ms',
    );
  }

  /// Cost badge with a currency icon and dollar formatting.
  factory MetricBadge.cost(double dollars) {
    return MetricBadge(
      icon: Icons.monetization_on_outlined,
      value: '\$${dollars.toStringAsFixed(dollars < 0.01 ? 4 : 2)}',
      color: AppColors.warning,
      tooltip: 'Cost: \$${dollars.toStringAsFixed(4)}',
    );
  }

  /// Token count badge with a chip icon and compact formatting.
  factory MetricBadge.tokens(int count) {
    return MetricBadge(
      icon: Icons.memory,
      value: _formatCompact(count),
      color: AppColors.secondaryPurple,
      tooltip: '$count tokens',
    );
  }

  /// Error rate badge with a warning icon and percentage formatting.
  factory MetricBadge.errorRate(double pct) {
    return MetricBadge(
      icon: Icons.warning_amber_rounded,
      value: '${pct.toStringAsFixed(1)}%',
      color: AppColors.error,
      tooltip: 'Error rate: ${pct.toStringAsFixed(2)}%',
    );
  }

  /// Sub-calls badge showing tool and LLM call counts.
  factory MetricBadge.subcalls(int tools, int llms) {
    return MetricBadge(
      icon: Icons.call_split,
      value: '${tools}T ${llms}L',
      color: AppColors.textMuted,
      tooltip: '$tools tool calls, $llms LLM calls',
    );
  }

  static String _formatDuration(double ms) {
    if (ms < 1000) return '${ms.toStringAsFixed(0)}ms';
    if (ms < 60000) return '${(ms / 1000).toStringAsFixed(1)}s';
    return '${(ms / 60000).toStringAsFixed(1)}m';
  }

  static String _formatCompact(int value) {
    if (value < 1000) return '$value';
    if (value < 1000000) return '${(value / 1000).toStringAsFixed(1)}K';
    return '${(value / 1000000).toStringAsFixed(1)}M';
  }

  @override
  Widget build(BuildContext context) {
    final badge = Container(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 10, color: color),
          const SizedBox(width: 3),
          Text(
            value,
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w500,
              color: color,
              height: 1.2,
            ),
          ),
        ],
      ),
    );

    if (tooltip != null) {
      return Tooltip(message: tooltip!, child: badge);
    }
    return badge;
  }
}
