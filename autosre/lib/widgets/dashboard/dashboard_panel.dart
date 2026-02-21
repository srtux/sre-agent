import 'package:flutter/material.dart';

import '../../services/dashboard_state.dart';
import '../../theme/app_theme.dart';
import 'live_logs_explorer.dart';
import 'live_metrics_panel.dart';
import 'live_trace_panel.dart';
import 'live_alerts_panel.dart';
import 'live_council_panel.dart';
import 'live_charts_panel.dart';
import 'agent_graph_iframe_panel.dart';
import 'sre_toolbar.dart';

/// The main investigation dashboard panel.
///
/// Displays a tabbed interface that collects and organizes all tool call
/// results into interactive data views: Traces, Logs, Metrics, Alerts,
/// and Remediation plans.
class DashboardPanel extends StatefulWidget {
  final DashboardState state;
  final VoidCallback onClose;
  final VoidCallback? onToggleMaximize;
  final bool isMaximized;
  final Function(String)? onPromptRequest;

  const DashboardPanel({
    super.key,
    required this.state,
    required this.onClose,
    this.onToggleMaximize,
    this.isMaximized = false,
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
          offset: Offset(_slideAnimation.value * -400, 0),
          child: Opacity(opacity: _fadeAnimation.value, child: child),
        );
      },
      child: Material(
        color: Colors.transparent,
        child: Container(
          decoration: BoxDecoration(
            color: AppColors.backgroundDark,
            border: Border(
              right: BorderSide(
                color: AppColors.surfaceBorder.withValues(alpha: 0.8),
                width: 1,
              ),
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.4),
                blurRadius: 20,
                offset: const Offset(4, 0),
              ),
            ],
          ),
          child: Column(
            children: [
              SreToolbar(
                dashboardState: widget.state,
                isMaximized: widget.isMaximized,
                onToggleMaximize: widget.onToggleMaximize,
                onClose: widget.onClose,
              ),
              Expanded(child: SelectionArea(child: _buildContent())),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildContent() {
    return ListenableBuilder(
      listenable: widget.state,
      builder: (context, _) {
        final items = widget.state.itemsOfType(widget.state.activeTab);

        switch (widget.state.activeTab) {
          case DashboardDataType.traces:
            return LiveTracePanel(
              items: items,
              dashboardState: widget.state,
              onPromptRequest: widget.onPromptRequest,
            );
          case DashboardDataType.logs:
            return LiveLogsExplorer(
              items: items,
              dashboardState: widget.state,
              onPromptRequest: widget.onPromptRequest,
            );
          case DashboardDataType.metrics:
            return LiveMetricsPanel(
              items: items,
              dashboardState: widget.state,
              onPromptRequest: widget.onPromptRequest,
            );
          case DashboardDataType.alerts:
            return LiveAlertsPanel(
              items: items,
              dashboardState: widget.state,
              onPromptRequest: widget.onPromptRequest,
            );
          case DashboardDataType.council:
            return LiveCouncilPanel(items: items, dashboardState: widget.state);
          case DashboardDataType.analytics:
            return LiveChartsPanel(
              items: items,
              dashboardState: widget.state,
              onPromptRequest: widget.onPromptRequest,
            );
          case DashboardDataType.agentGraph:
            return const AgentGraphIframePanel();
        }
      },
    );
  }
}
