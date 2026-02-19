import 'package:flutter/material.dart';
import '../../features/agent_graph/presentation/multi_trace_graph_page.dart';
import '../../features/dashboards/presentation/pages/dashboards_page.dart';
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

        return AnimatedContainer(
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeInOut,
          width: state.isRailExpanded ? 180 : 60,
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
            crossAxisAlignment: CrossAxisAlignment.stretch,
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
                isExpanded: state.isRailExpanded,
                onTap: state.toggleDashboard,
              ),
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                child: Divider(height: 1),
              ),
              // Dashboards Browser
              _RailItem(
                icon: Icons.dashboard_customize_outlined,
                label: 'Custom Dashboards',
                color: AppColors.primaryTeal,
                isActive: false,
                hasData: false,
                isExpanded: state.isRailExpanded,
                onTap: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (context) => const DashboardsPage(),
                    ),
                  );
                },
              ),
              // Agent Graph
              _RailItem(
                icon: Icons.account_tree_outlined,
                label: 'Agent Graph',
                color: AppColors.secondaryPurple,
                isActive: false,
                hasData: false,
                isExpanded: state.isRailExpanded,
                onTap: () {
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (context) => const MultiTraceGraphPage(),
                    ),
                  );
                },
              ),
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                child: Divider(height: 1),
              ),

              Expanded(
                child: ListView(
                  padding: EdgeInsets.zero,
                  children: DashboardDataType.values.map((type) {
                    final config = _tabIconConfig(type);
                    final count = counts[type] ?? 0;
                    final isCurrentTab =
                        state.isOpen && state.activeTab == type;

                    return _RailItem(
                      icon: config.icon,
                      label: config.label,
                      color: config.color,
                      isActive: isCurrentTab,
                      hasData: count > 0,
                      count: count,
                      isExpanded: state.isRailExpanded,
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

              // Expand/Collapse Toggle at bottom
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 8),
                child: InkWell(
                  onTap: state.toggleRail,
                  borderRadius: BorderRadius.circular(8),
                  child: Container(
                    height: 40,
                    width: double.infinity,
                    padding: state.isRailExpanded
                        ? const EdgeInsets.symmetric(horizontal: 10)
                        : EdgeInsets.zero,
                    child: Row(
                      mainAxisAlignment: state.isRailExpanded
                          ? MainAxisAlignment.start
                          : MainAxisAlignment.center,
                      children: [
                        Icon(
                          state.isRailExpanded
                              ? Icons.chevron_left_rounded
                              : Icons.chevron_right_rounded,
                          color: AppColors.textMuted,
                          size: 20,
                        ),
                        if (state.isRailExpanded) ...[
                          const SizedBox(width: 12),
                          const Text(
                            'Collapse',
                            style: TextStyle(
                              color: AppColors.textMuted,
                              fontSize: 13,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 8),
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
  final bool isExpanded;
  final VoidCallback onTap;

  const _RailItem({
    required this.icon,
    required this.label,
    required this.color,
    required this.isActive,
    required this.hasData,
    this.count = 0,
    this.isExpanded = false,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 8),
      child: Tooltip(
        message: isExpanded ? '' : label,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(8),
          child: Row(
            children: [
              Stack(
                alignment: Alignment.center,
                children: [
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: isActive
                          ? color.withValues(alpha: 0.15)
                          : hasData
                          ? color.withValues(alpha: 0.05)
                          : Colors.transparent,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: isActive
                            ? color.withValues(alpha: 0.4)
                            : hasData
                            ? color.withValues(alpha: 0.1)
                            : Colors.transparent,
                        width: 1,
                      ),
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
                      top: 6,
                      right: 6,
                      child: Container(
                        width: 6,
                        height: 6,
                        decoration: BoxDecoration(
                          color: color,
                          shape: BoxShape.circle,
                        ),
                      ),
                    ),
                ],
              ),
              if (isExpanded) ...[
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    label,
                    style: TextStyle(
                      color: isActive || hasData ? color : AppColors.textMuted,
                      fontSize: 13,
                      fontWeight: isActive
                          ? FontWeight.bold
                          : FontWeight.normal,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (count > 0) ...[
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 6,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: color.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(
                      '$count',
                      style: TextStyle(
                        color: color,
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  const SizedBox(width: 4),
                ],
              ],
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
        'Traces',
        Icons.alt_route_rounded,
        AppColors.primaryCyan,
      );
    case DashboardDataType.logs:
      return const _RailIconConfig(
        'Logs',
        Icons.article_outlined,
        AppColors.success,
      );
    case DashboardDataType.metrics:
      return const _RailIconConfig(
        'Metrics',
        Icons.show_chart_rounded,
        AppColors.warning,
      );
    case DashboardDataType.alerts:
      return const _RailIconConfig(
        'Alerts',
        Icons.notifications_active_outlined,
        AppColors.error,
      );
    case DashboardDataType.council:
      return const _RailIconConfig(
        'Council',
        Icons.groups_rounded,
        AppColors.primaryTeal,
      );
    case DashboardDataType.analytics:
      return const _RailIconConfig(
        'Analytics',
        Icons.insights_rounded,
        AppColors.primaryBlue,
      );
  }
}
