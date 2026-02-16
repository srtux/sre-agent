import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../services/dashboard_state.dart';
import '../../services/explorer_query_service.dart';
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
class LiveAlertsPanel extends StatelessWidget {
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
  Widget build(BuildContext context) {
    final isLoading = dashboardState.isLoading(DashboardDataType.alerts);
    final error = dashboardState.errorFor(DashboardDataType.alerts);

    return Column(
      children: [
        // Manual query bar
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
          child: ManualQueryBar(
            hintText: 'state="OPEN" AND severity="CRITICAL"',
            dashboardState: dashboardState,
            onRefresh: () {
              final filter = dashboardState.getLastQueryFilter(
                DashboardDataType.alerts,
              );
              if (filter != null && filter.isNotEmpty) {
                final explorer = context.read<ExplorerQueryService>();
                explorer.queryAlerts(filter: filter);
              }
            },
            initialValue: dashboardState.getLastQueryFilter(
              DashboardDataType.alerts,
            ),
            isLoading: isLoading,
            onSubmit: (filter) {
              dashboardState.setLastQueryFilter(
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
                dashboardState.setError(DashboardDataType.alerts, null),
          ),
        // Content
        Expanded(
          child: isLoading && items.isEmpty
              ? const ShimmerLoading()
              : items.isEmpty
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
        final itemHeight = items.length == 1
            ? (availableHeight - 32).clamp(600.0, 1500.0)
            : 600.0;

        return ListView.builder(
          padding: const EdgeInsets.all(12),
          itemCount: items.length,
          itemBuilder: (context, index) {
            final item = items[index];
            if (item.alertData == null) return const SizedBox.shrink();

            return DashboardCardWrapper(
              onClose: () => dashboardState.removeItem(item.id),
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
                  onPromptRequest: onPromptRequest,
                ),
              ),
            );
          },
        );
      },
    );
  }
}
