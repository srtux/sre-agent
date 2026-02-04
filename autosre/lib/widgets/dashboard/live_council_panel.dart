import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../services/dashboard_state.dart';
import '../../theme/app_theme.dart';

/// Dashboard panel showing council investigation synthesis results.
///
/// Displays the council's unified assessment including:
/// - Investigation mode and round count
/// - Overall severity and confidence
/// - Synthesized narrative
class LiveCouncilPanel extends StatelessWidget {
  final List<DashboardItem> items;
  const LiveCouncilPanel({super.key, required this.items});

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: items.length,
      itemBuilder: (context, index) {
        final item = items[index];
        final council = item.councilData;
        if (council == null) return const SizedBox.shrink();

        return Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Container(
            decoration: BoxDecoration(
              color: AppColors.backgroundCard,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.surfaceBorder),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildHeader(council),
                _buildMetrics(council),
                _buildSynthesis(council),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildHeader(dynamic council) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 0),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
              color: AppColors.primaryTeal.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(6),
            ),
            child: const Icon(
              Icons.groups_rounded,
              size: 14,
              color: AppColors.primaryTeal,
            ),
          ),
          const SizedBox(width: 8),
          Text(
            'Council Investigation',
            style: GoogleFonts.inter(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ),
          const Spacer(),
          _buildModeBadge(council.mode as String),
          const SizedBox(width: 6),
          _buildSeverityBadge(council.overallSeverity as String),
        ],
      ),
    );
  }

  Widget _buildMetrics(dynamic council) {
    final confidence = council.overallConfidence as double;
    final rounds = council.rounds as int;
    final mode = council.mode as String;

    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 0),
      child: Row(
        children: [
          _buildMetricChip(
            Icons.speed_rounded,
            'Confidence',
            '${(confidence * 100).toStringAsFixed(0)}%',
            confidence >= 0.85
                ? AppColors.success
                : confidence >= 0.5
                    ? AppColors.warning
                    : AppColors.error,
          ),
          const SizedBox(width: 8),
          if (mode == 'debate') ...[
            _buildMetricChip(
              Icons.loop_rounded,
              'Rounds',
              '$rounds',
              AppColors.primaryCyan,
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildMetricChip(
      IconData icon, String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.2)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 4),
          Text(
            '$label: ',
            style: TextStyle(
              fontSize: 10,
              color: color.withValues(alpha: 0.8),
            ),
          ),
          Text(
            value,
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

  Widget _buildSynthesis(dynamic council) {
    final synthesis = council.synthesis as String;
    if (synthesis.isEmpty) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.all(12),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: AppColors.backgroundDark.withValues(alpha: 0.5),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: AppColors.surfaceBorder.withValues(alpha: 0.3),
          ),
        ),
        child: Text(
          synthesis,
          style: const TextStyle(
            fontSize: 12,
            color: AppColors.textSecondary,
            height: 1.5,
          ),
        ),
      ),
    );
  }

  Widget _buildModeBadge(String mode) {
    Color color;
    IconData icon;
    switch (mode.toLowerCase()) {
      case 'fast':
        color = AppColors.success;
        icon = Icons.flash_on_rounded;
        break;
      case 'debate':
        color = AppColors.error;
        icon = Icons.forum_rounded;
        break;
      default: // standard
        color = AppColors.primaryCyan;
        icon = Icons.auto_awesome_rounded;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 10, color: color),
          const SizedBox(width: 3),
          Text(
            mode.toUpperCase(),
            style: TextStyle(
              fontSize: 9,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSeverityBadge(String severity) {
    Color color;
    switch (severity.toLowerCase()) {
      case 'critical':
        color = AppColors.error;
        break;
      case 'warning':
        color = AppColors.warning;
        break;
      case 'healthy':
        color = AppColors.success;
        break;
      default: // info
        color = AppColors.primaryCyan;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        severity.toUpperCase(),
        style: TextStyle(
          fontSize: 9,
          fontWeight: FontWeight.w600,
          color: color,
        ),
      ),
    );
  }
}
