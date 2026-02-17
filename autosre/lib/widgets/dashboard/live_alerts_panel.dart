import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../services/dashboard_state.dart';
import '../../services/explorer_query_service.dart';
import '../../services/project_service.dart';
import '../../theme/app_theme.dart';
import '../canvas/alerts_dashboard_canvas.dart';
import '../common/error_banner.dart';
import '../common/explorer_empty_state.dart';
import '../common/shimmer_loading.dart';
import '../common/source_badge.dart';
import 'manual_query_bar.dart';
import 'dashboard_card_wrapper.dart';

/// Dashboard panel showing all collected alert/incident dashboard data.
///
/// Includes a manual query bar for searching alerts directly.
/// Auto-loads recent alerts (past 7 days) when first displayed with no data.
class LiveAlertsPanel extends StatefulWidget {
  final List<DashboardItem> items;
  final DashboardState dashboardState;
  final Function(String)? onPromptRequest;

  const LiveAlertsPanel({
    super.key,
    required this.items,
    required this.dashboardState,
    this.onPromptRequest,
  });

  @override
  State<LiveAlertsPanel> createState() => _LiveAlertsPanelState();
}

class _LiveAlertsPanelState extends State<LiveAlertsPanel> {
  @override
  void initState() {
    super.initState();

    // Auto-load recent alerts when panel first appears with no data
    // and no load is already in progress.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (widget.items.isEmpty &&
          mounted &&
          !widget.dashboardState.isLoading(DashboardDataType.alerts)) {
        _loadRecentAlerts();
      }
    });
  }

  Future<void> _loadRecentAlerts() async {
    if (!mounted) return;
    try {
      final explorer = context.read<ExplorerQueryService>();
      final projectId = context.read<ProjectService>().selectedProjectId;
      if (projectId == null) return;
      await explorer.loadRecentAlerts(projectId: projectId);
    } catch (e) {
      debugPrint('LiveAlertsPanel auto-load error: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final isLoading = widget.dashboardState.isLoading(DashboardDataType.alerts);
    final error = widget.dashboardState.errorFor(DashboardDataType.alerts);

    return Column(
      children: [
        // Manual query bar
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
          child: ManualQueryBar(
            hintText: 'state="OPEN" AND severity="CRITICAL"',
            panelType: 'alerts',
            dashboardState: widget.dashboardState,
            onRefresh: () {
              final filter = widget.dashboardState.getLastQueryFilter(
                DashboardDataType.alerts,
              );
              if (filter != null && filter.isNotEmpty) {
                final explorer = context.read<ExplorerQueryService>();
                explorer.queryAlerts(filter: filter);
              }
            },
            initialValue: widget.dashboardState.getLastQueryFilter(
              DashboardDataType.alerts,
            ),
            isLoading: isLoading,
            onSubmit: (filter) {
              widget.dashboardState.setLastQueryFilter(
                DashboardDataType.alerts,
                filter,
              );
              final explorer = context.read<ExplorerQueryService>();
              explorer.queryAlerts(filter: filter);
            },
          ),
        ),
        if (error != null)
          ErrorBanner(
            message: error,
            onDismiss: () =>
                widget.dashboardState.setError(DashboardDataType.alerts, null),
          ),
        // Content
        Expanded(
          child: isLoading && widget.items.isEmpty
              ? const ShimmerLoading()
              : widget.items.isEmpty
              ? const ExplorerEmptyState(
                  icon: Icons.notifications_active_outlined,
                  title: 'No Alerts Yet',
                  description:
                      'Query active alerts and incidents by entering\na filter expression above, or wait for the agent to find them.',
                  queryHint: 'state="OPEN" AND severity="CRITICAL"',
                )
              : _buildAlertContent(),
        ),
      ],
    );
  }

  Widget _buildAlertContent() {
    return LayoutBuilder(
      builder: (context, constraints) {
        final availableHeight = constraints.maxHeight;
        // If there's only one item, let it take up most of the screen
        // If multiple, use a standard tall height
        final itemHeight = widget.items.length == 1
            ? (availableHeight - 32).clamp(600.0, 1500.0)
            : 600.0;

        return ListView.builder(
          padding: const EdgeInsets.all(12),
          itemCount: widget.items.length,
          itemBuilder: (context, index) {
            final item = widget.items[index];
            if (item.alertData == null) return const SizedBox.shrink();

            return DashboardCardWrapper(
              onClose: () => widget.dashboardState.removeItem(item.id),
              header: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(4),
                    decoration: BoxDecoration(
                      color: AppColors.error.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: const Icon(
                      Icons.notifications_active_outlined,
                      size: 14,
                      color: AppColors.error,
                    ),
                  ),
                  const SizedBox(width: 8),
                  const Text(
                    'Active Alerts Dashboard',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const Spacer(),
                  SourceBadge(source: item.source),
                ],
              ),
              child: SizedBox(
                height: itemHeight,
                child: AlertsDashboardCanvas(
                  data: item.alertData!,
                  onPromptRequest: widget.onPromptRequest,
                ),
              ),
            );
          },
        );
      },
    );
  }
}
