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
            initialValue: dashboardState.getLastQueryFilter(DashboardDataType.alerts),
            isLoading: isLoading,
            onSubmit: (filter) {
              dashboardState.setLastQueryFilter(DashboardDataType.alerts, filter);
              final explorer = context.read<ExplorerQueryService>();
              explorer.queryAlerts(filter: filter);
            },
          ),
        ),
        if (error != null) ErrorBanner(message: error),
        // Content
        Expanded(
          child: isLoading && items.isEmpty
              ? const ShimmerLoading()
              : items.isEmpty
                  ? const ExplorerEmptyState(
                      icon: Icons.notifications_active_outlined,
                      title: 'Alerts Explorer',
                      description:
                          'Query active alerts and incidents by entering\na filter expression above.',
                      queryHint: 'state="OPEN" AND severity="CRITICAL"',
                    )
                  : _buildAlertContent(),
        ),
      ],
    );
  }

  Widget _buildAlertContent() {
    // If there is only one item, allow it to expand to fill the available space.
    if (items.length == 1) {
      final item = items.first;
      if (item.alertData == null) return const SizedBox.shrink();

      return Padding(
        padding: const EdgeInsets.all(12),
        child: Container(
          decoration: BoxDecoration(
            color: AppColors.backgroundCard,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.surfaceBorder),
          ),
          clipBehavior: Clip.antiAlias,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildHeader(item),
              Expanded(
                child: AlertsDashboardCanvas(
                  data: item.alertData!,
                  onPromptRequest: onPromptRequest,
                ),
              ),
            ],
          ),
        ),
      );
    }

    // For multiple items, keep the list view with fixed height
    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: items.length,
      itemBuilder: (context, index) {
        final item = items[index];
        if (item.alertData == null) return const SizedBox.shrink();

        return Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Container(
            height: 450,
            decoration: BoxDecoration(
              color: AppColors.backgroundCard,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.surfaceBorder),
            ),
            clipBehavior: Clip.antiAlias,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildHeader(item),
                Expanded(
                  child: AlertsDashboardCanvas(
                    data: item.alertData!,
                    onPromptRequest: onPromptRequest,
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildHeader(DashboardItem item) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 0),
      child: Row(
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
          Padding(
              padding: const EdgeInsets.only(right: 6),
              child: SourceBadge(source: item.source),
            ),
          Text(
            '${item.alertData!.events.length} alerts',
            style: const TextStyle(
              fontSize: 10,
              color: AppColors.textMuted,
            ),
          ),
        ],
      ),
    );
  }
}
