import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../services/dashboard_state.dart';
import '../../theme/app_theme.dart';

/// Unified Dashboard Header
///
/// Layout: [Dynamic Tab icon+label] | ...spacer... | [Count] [Maximize] [Close]
class SreToolbar extends StatelessWidget {
  final DashboardState dashboardState;
  final bool isMaximized;
  final VoidCallback? onToggleMaximize;
  final VoidCallback onClose;

  const SreToolbar({
    super.key,
    required this.dashboardState,
    this.isMaximized = false,
    this.onToggleMaximize,
    required this.onClose,
  });

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: dashboardState,
      builder: (context, _) {
        return Container(
          height: 44,
          decoration: BoxDecoration(
            color: AppColors.backgroundCard,
            border: Border(
              bottom: BorderSide(
                color: AppColors.surfaceBorder.withValues(alpha: 0.5),
                width: 1,
              ),
            ),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: Row(
            children: [
              _buildBrandLabel(),
              const Spacer(),
              _buildItemCount(),
              const SizedBox(width: 8),
              if (onToggleMaximize != null)
                IconButton(
                  icon: Icon(
                    isMaximized ? Icons.fullscreen_exit : Icons.fullscreen,
                    size: 20,
                  ),
                  color: AppColors.textMuted,
                  onPressed: onToggleMaximize,
                  tooltip: isMaximized ? 'Restore' : 'Maximize',
                  style: IconButton.styleFrom(
                    padding: const EdgeInsets.all(4),
                    minimumSize: const Size(28, 28),
                  ),
                ),
              IconButton(
                icon: const Icon(Icons.close, size: 18),
                color: AppColors.textMuted,
                onPressed: onClose,
                tooltip: 'Close Dashboard',
                style: IconButton.styleFrom(
                  padding: const EdgeInsets.all(4),
                  minimumSize: const Size(28, 28),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildBrandLabel() {
    final config = _tabConfig(dashboardState.activeTab);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          padding: const EdgeInsets.all(4),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                config.color.withValues(alpha: 0.2),
                config.color.withValues(alpha: 0.1),
              ],
            ),
            borderRadius: BorderRadius.circular(6),
          ),
          child: Icon(
            config.icon,
            size: 14,
            color: config.color,
          ),
        ),
        const SizedBox(width: 8),
        Text(
          config.label,
          style: GoogleFonts.inter(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: AppColors.textPrimary,
            letterSpacing: -0.2,
          ),
        ),
      ],
    );
  }

  Widget _buildItemCount() {
    final count = dashboardState.items.length;
    if (count == 0) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: AppColors.primaryCyan.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Text(
        '$count items',
        style: const TextStyle(
          fontSize: 11,
          color: AppColors.primaryCyan,
          fontWeight: FontWeight.w500,
        ),
      ),
    );
  }
}

class _TabConfig {
  final String label;
  final IconData icon;
  final Color color;
  const _TabConfig(this.label, this.icon, this.color);
}

_TabConfig _tabConfig(DashboardDataType type) {
  switch (type) {
    case DashboardDataType.traces:
      return const _TabConfig('Traces', Icons.timeline_rounded, AppColors.primaryCyan);
    case DashboardDataType.logs:
      return const _TabConfig('Logs', Icons.article_outlined, AppColors.success);
    case DashboardDataType.metrics:
      return const _TabConfig('Metrics', Icons.show_chart_rounded, AppColors.warning);
    case DashboardDataType.alerts:
      return const _TabConfig('Alerts', Icons.notifications_active_outlined, AppColors.error);
    case DashboardDataType.remediation:
      return const _TabConfig('Remediation', Icons.build_circle_outlined, AppColors.secondaryPurple);
    case DashboardDataType.council:
      return const _TabConfig('Council', Icons.groups_rounded, AppColors.primaryTeal);
    case DashboardDataType.charts:
      return const _TabConfig('Charts', Icons.bar_chart_rounded, AppColors.warning);
    case DashboardDataType.sql:
      return const _TabConfig('SQL', Icons.storage_rounded, AppColors.warning);
  }
}
