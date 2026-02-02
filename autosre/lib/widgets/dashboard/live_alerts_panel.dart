import 'package:flutter/material.dart';

import '../../services/dashboard_state.dart';
import '../../theme/app_theme.dart';
import '../canvas/alerts_dashboard_canvas.dart';

/// Dashboard panel showing all collected alert/incident dashboard data.
class LiveAlertsPanel extends StatelessWidget {
  final List<DashboardItem> items;
  final Function(String)? onPromptRequest;

  const LiveAlertsPanel({
    super.key,
    required this.items,
    this.onPromptRequest,
  });

  @override
  Widget build(BuildContext context) {
    // If there is only one item, allow it to expand to fill the available space.
    if (items.length == 1) {
      final item = items.first;
      if (item.alertData == null) return const SizedBox.shrink();

      return Padding(
        padding: const EdgeInsets.all(12),
        child: Container(
          // No fixed height, fills parent
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

    // For multiple items, keep the list view with fixed height for now
    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: items.length,
      itemBuilder: (context, index) {
        final item = items[index];
        if (item.alertData == null) return const SizedBox.shrink();

        return Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Container(
            height: 450, // Fixed height for list items
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
