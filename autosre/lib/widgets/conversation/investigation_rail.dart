import 'package:flutter/material.dart';
import '../../services/dashboard_state.dart';
import '../../theme/app_theme.dart';

/// A vertical rail on the left side providing quick access to dashboard categories.
class InvestigationRail extends StatelessWidget {
  final DashboardState state;

  const InvestigationRail({super.key, required this.state});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: state,
      builder: (context, _) {
        final hasData = state.hasData;
        final counts = state.typeCounts;

        return Container(
          width: 56,
          decoration: BoxDecoration(
            color: AppColors.backgroundCard.withValues(alpha: 0.8),
            border: Border(
              left: BorderSide(
                color: AppColors.surfaceBorder.withValues(alpha: 0.5),
                width: 1,
              ),
            ),
          ),
          child: Column(
            children: [
              const SizedBox(height: 12),
              // Main Toggle
              _RailItem(
                icon: state.isOpen
                    ? Icons.dashboard_rounded
                    : Icons.dashboard_outlined,
                label: 'Dashboard',
                color: AppColors.primaryCyan,
                isActive: state.isOpen,
                hasData: hasData,
                onTap: state.toggleDashboard,
              ),
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                child: Divider(height: 1),
              ),
              // Category Items
              Expanded(
                child: ListView(
                  padding: EdgeInsets.zero,
                  children: DashboardDataType.values.map((type) {
                    final config = _tabIconConfig(type);
                    final count = counts[type] ?? 0;
                    final isCurrentTab = state.isOpen && state.activeTab == type;

                    return _RailItem(
                      icon: config.icon,
                      label: config.label,
                      color: config.color,
                      isActive: isCurrentTab,
                      hasData: count > 0,
                      count: count,
                      onTap: () {
                        if (!state.isOpen) {
                          state.openDashboard();
                        }
                        state.setActiveTab(type);
                      },
                    );
                  }).toList(),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _RailItem extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final bool isActive;
  final bool hasData;
  final int count;
  final VoidCallback onTap;

  const _RailItem({
    required this.icon,
    required this.label,
    required this.color,
    required this.isActive,
    required this.hasData,
    this.count = 0,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Tooltip(
        message: label,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(8),
          child: Stack(
            alignment: Alignment.center,
            children: [
              AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: isActive
                      ? color.withValues(alpha: 0.15)
                      : hasData
                          ? color.withValues(alpha: 0.05)
                          : Colors.transparent,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: isActive
                        ? color.withValues(alpha: 0.4)
                        : hasData
                            ? color.withValues(alpha: 0.1)
                            : Colors.transparent,
                    width: 1,
                  ),
                  boxShadow: [
                    if (isActive || (hasData && !isActive))
                      BoxShadow(
                        color: color.withValues(alpha: 0.1),
                        blurRadius: 8,
                        spreadRadius: -2,
                      ),
                  ],
                ),
                child: Icon(
                  icon,
                  size: 20,
                  color: isActive || hasData ? color : AppColors.textMuted,
                ),
              ),
              // Activity Indicator Glow
              if (hasData && !isActive)
                Positioned(
                  top: 8,
                  right: 8,
                  child: Container(
                    width: 6,
                    height: 6,
                    decoration: BoxDecoration(
                      color: color,
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: color.withValues(alpha: 0.6),
                          blurRadius: 4,
                          spreadRadius: 1,
                        ),
                      ],
                    ),
                  ),
                ),
              // Badge count
              if (count > 0 && isActive)
                Positioned(
                  bottom: 4,
                  right: 4,
                  child: Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                    decoration: BoxDecoration(
                      color: color,
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      '$count',
                      style: const TextStyle(
                        fontSize: 8,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _RailIconConfig {
  final String label;
  final IconData icon;
  final Color color;
  const _RailIconConfig(this.label, this.icon, this.color);
}

_RailIconConfig _tabIconConfig(DashboardDataType type) {
  switch (type) {
    case DashboardDataType.traces:
      return const _RailIconConfig(
          'Traces', Icons.alt_route_rounded, AppColors.primaryCyan);
    case DashboardDataType.logs:
      return const _RailIconConfig(
          'Logs', Icons.article_outlined, AppColors.success);
    case DashboardDataType.metrics:
      return const _RailIconConfig(
          'Metrics', Icons.show_chart_rounded, AppColors.warning);
    case DashboardDataType.alerts:
      return const _RailIconConfig('Alerts',
          Icons.notifications_active_outlined, AppColors.error);
    case DashboardDataType.remediation:
      return const _RailIconConfig('Remediation',
          Icons.build_circle_outlined, AppColors.secondaryPurple);
    case DashboardDataType.council:
      return const _RailIconConfig(
          'Council', Icons.groups_rounded, AppColors.primaryTeal);
    case DashboardDataType.analytics:
      return const _RailIconConfig(
          'Analytics', Icons.insights_rounded, AppColors.primaryBlue);
  }
}
