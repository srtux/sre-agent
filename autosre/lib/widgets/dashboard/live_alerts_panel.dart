import 'package:flutter/material.dart';

import '../../services/dashboard_state.dart';
import '../../theme/app_theme.dart';
import '../canvas/incident_timeline_canvas.dart';

/// Dashboard panel showing all collected alert/incident timeline data.
class LiveAlertsPanel extends StatelessWidget {
  final List<DashboardItem> items;
  const LiveAlertsPanel({super.key, required this.items});

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: items.length,
      itemBuilder: (context, index) {
        final item = items[index];
        if (item.alertData == null) return const SizedBox.shrink();

        return Padding(
          padding: const EdgeInsets.only(bottom: 10),
          child: Container(
            height: 380,
            decoration: BoxDecoration(
              color: AppColors.backgroundCard,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.surfaceBorder),
            ),
            clipBehavior: Clip.antiAlias,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
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
                      Text(
                        'Alert Timeline',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w600,
                          color: AppColors.textPrimary,
                        ),
                      ),
                      const Spacer(),
                      Text(
                        '${item.alertData!.events.length} events',
                        style: const TextStyle(
                          fontSize: 10,
                          color: AppColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: IncidentTimelineCanvas(data: item.alertData!),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
