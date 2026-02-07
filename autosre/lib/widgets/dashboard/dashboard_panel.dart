import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../services/dashboard_state.dart';
import '../../theme/app_theme.dart';
import '../common/explorer_empty_state.dart';
import 'live_logs_explorer.dart';
import 'live_metrics_panel.dart';
import 'live_trace_panel.dart';
import 'live_alerts_panel.dart';
import 'live_remediation_panel.dart';
import 'live_council_panel.dart';
import 'live_charts_panel.dart';
import 'sre_toolbar.dart';

/// The main investigation dashboard panel.
///
/// Displays a tabbed interface that collects and organizes all tool call
/// results into interactive data views: Traces, Logs, Metrics, Alerts,
/// and Remediation plans.
class DashboardPanel extends StatefulWidget {
  final DashboardState state;
  final VoidCallback onClose;
  final Function(String)? onPromptRequest;

  const DashboardPanel({
    super.key,
    required this.state,
    required this.onClose,
    this.onPromptRequest,
  });

  @override
  State<DashboardPanel> createState() => _DashboardPanelState();
}

class _DashboardPanelState extends State<DashboardPanel>
    with SingleTickerProviderStateMixin {
  late AnimationController _entranceController;
  late Animation<double> _slideAnimation;
  late Animation<double> _fadeAnimation;

  @override
  void initState() {
    super.initState();
    _entranceController = AnimationController(
      duration: const Duration(milliseconds: 300),
      vsync: this,
    );
    _slideAnimation = Tween<double>(begin: 1.0, end: 0.0).animate(
      CurvedAnimation(parent: _entranceController, curve: Curves.easeOutCubic),
    );
    _fadeAnimation = CurvedAnimation(
      parent: _entranceController,
      curve: Curves.easeOut,
    );
    _entranceController.forward();
  }

  @override
  void dispose() {
    _entranceController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _entranceController,
      builder: (context, child) {
        return Transform.translate(
          offset: Offset(_slideAnimation.value * 400, 0),
          child: Opacity(
            opacity: _fadeAnimation.value,
            child: child,
          ),
        );
      },
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.backgroundDark,
          border: Border(
            left: BorderSide(
              color: AppColors.surfaceBorder.withValues(alpha: 0.5),
              width: 1,
            ),
          ),
        ),
        child: Column(
          children: [
            _buildHeader(),
            SreToolbar(
              dashboardState: widget.state,
              onRefresh: () {},
            ),
            _buildTabBar(),
            Expanded(child: _buildContent()),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.backgroundCard,
        border: Border(
          bottom: BorderSide(
            color: AppColors.surfaceBorder.withValues(alpha: 0.5),
            width: 1,
          ),
        ),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppColors.primaryCyan.withValues(alpha: 0.2),
                  AppColors.primaryTeal.withValues(alpha: 0.2),
                ],
              ),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(
              Icons.dashboard_rounded,
              size: 16,
              color: AppColors.primaryCyan,
            ),
          ),
          const SizedBox(width: 10),
          Text(
            'Investigation Dashboard',
            style: GoogleFonts.inter(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
              letterSpacing: -0.2,
            ),
          ),
          const Spacer(),
          _buildItemCount(),
          const SizedBox(width: 8),
          IconButton(
            icon: const Icon(Icons.close, size: 18),
            color: AppColors.textMuted,
            onPressed: widget.onClose,
            style: IconButton.styleFrom(
              padding: const EdgeInsets.all(4),
              minimumSize: const Size(28, 28),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildItemCount() {
    return ListenableBuilder(
      listenable: widget.state,
      builder: (context, _) {
        final count = widget.state.items.length;
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
      },
    );
  }

  Widget _buildTabBar() {
    return ListenableBuilder(
      listenable: widget.state,
      builder: (context, _) {
        final counts = widget.state.typeCounts;
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
          decoration: BoxDecoration(
            color: AppColors.backgroundCard.withValues(alpha: 0.5),
            border: Border(
              bottom: BorderSide(
                color: AppColors.surfaceBorder.withValues(alpha: 0.3),
                width: 1,
              ),
            ),
          ),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: DashboardDataType.values.map((type) {
                return _DashboardTab(
                  type: type,
                  isActive: widget.state.activeTab == type,
                  count: counts[type] ?? 0,
                  onTap: () => widget.state.setActiveTab(type),
                );
              }).toList(),
            ),
          ),
        );
      },
    );
  }

  Widget _buildContent() {
    return ListenableBuilder(
      listenable: widget.state,
      builder: (context, _) {
        if (!widget.state.hasData) {
          return _buildEmptyState();
        }

        final items = widget.state.itemsOfType(widget.state.activeTab);
        if (items.isEmpty) {
          return _buildEmptyTabState(widget.state.activeTab);
        }

        switch (widget.state.activeTab) {
          case DashboardDataType.traces:
            return LiveTracePanel(
              items: items,
              dashboardState: widget.state,
            );
          case DashboardDataType.logs:
            return LiveLogsExplorer(
              items: items,
              dashboardState: widget.state,
            );
          case DashboardDataType.metrics:
            return LiveMetricsPanel(
              items: items,
              dashboardState: widget.state,
            );
          case DashboardDataType.alerts:
            return LiveAlertsPanel(
              items: items,
              dashboardState: widget.state,
              onPromptRequest: widget.onPromptRequest,
            );
          case DashboardDataType.remediation:
            return LiveRemediationPanel(items: items);
          case DashboardDataType.council:
            return LiveCouncilPanel(items: items);
          case DashboardDataType.charts:
            return LiveChartsPanel(items: items);
        }
      },
    );
  }

  Widget _buildEmptyState() {
    return const ExplorerEmptyState(
      icon: Icons.analytics_outlined,
      title: 'Observability Explorer',
      description: 'Use the query bars above each panel to explore telemetry data,\nor start an agent investigation to auto-populate results.',
      queryHint: 'metric.type="compute.googleapis.com/instance/cpu/utilization"',
    );
  }

  Widget _buildEmptyTabState(DashboardDataType type) {
    final config = _tabConfig(type);
    return ExplorerEmptyState(
      icon: config.icon,
      title: 'No ${config.label} Yet',
      description: 'Use the query bar to search for ${config.label.toLowerCase()},\nor wait for the agent to collect data.',
    );
  }
}

class _DashboardTab extends StatelessWidget {
  final DashboardDataType type;
  final bool isActive;
  final int count;
  final VoidCallback onTap;

  const _DashboardTab({
    required this.type,
    required this.isActive,
    required this.count,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final config = _tabConfig(type);
    final color = isActive ? config.color : AppColors.textMuted;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 2),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(8),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(
              color: isActive
                  ? config.color.withValues(alpha: 0.12)
                  : Colors.transparent,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: isActive
                    ? config.color.withValues(alpha: 0.3)
                    : Colors.transparent,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(config.icon, size: 14, color: color),
                const SizedBox(width: 6),
                Text(
                  config.label,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
                    color: color,
                  ),
                ),
                if (count > 0) ...[
                  const SizedBox(width: 6),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                    decoration: BoxDecoration(
                      color: config.color.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(
                      '$count',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                        color: config.color,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
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
  }
}
