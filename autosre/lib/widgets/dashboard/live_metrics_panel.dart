import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../services/dashboard_state.dart';
import '../../theme/app_theme.dart';
import '../metric_chart.dart';
import '../canvas/metrics_dashboard_canvas.dart';

/// Dashboard panel displaying all collected metric data.
///
/// Shows metrics in a responsive grid of charts, each rendered
/// with the MetricCorrelationChart widget. Dashboard-type metrics
/// use the MetricsDashboardCanvas.
class LiveMetricsPanel extends StatelessWidget {
  final List<DashboardItem> items;
  const LiveMetricsPanel({super.key, required this.items});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isWide = constraints.maxWidth > 500;
        return ListView.builder(
          padding: const EdgeInsets.all(12),
          itemCount: items.length,
          itemBuilder: (context, index) {
            final item = items[index];

            // Metrics dashboard canvas
            if (item.metricsDashboard != null) {
              return _buildDashboardCard(item, isWide);
            }

            // Single metric series chart
            if (item.metricSeries != null) {
              return _buildMetricCard(item, isWide);
            }

            return const SizedBox.shrink();
          },
        );
      },
    );
  }

  Widget _buildMetricCard(DashboardItem item, bool isWide) {
    final series = item.metricSeries!;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Container(
        height: isWide ? 280 : 220,
        decoration: BoxDecoration(
          color: AppColors.backgroundCard,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.surfaceBorder),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 10, 12, 0),
              child: Row(
                children: [
                  const Icon(Icons.show_chart_rounded,
                      size: 14, color: AppColors.warning),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      series.metricName,
                      style: GoogleFonts.jetBrainsMono(
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                        color: AppColors.textPrimary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Text(
                    '${series.points.length} pts',
                    style: const TextStyle(
                      fontSize: 10,
                      color: AppColors.textMuted,
                    ),
                  ),
                ],
              ),
            ),
            // Chart
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(8),
                child: MetricCorrelationChart(series: series),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildDashboardCard(DashboardItem item, bool isWide) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Container(
        height: 350,
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
                  const Icon(Icons.dashboard_rounded,
                      size: 14, color: AppColors.warning),
                  const SizedBox(width: 6),
                  Text(
                    'Golden Signals Dashboard',
                    style: GoogleFonts.inter(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  const Spacer(),
                  Text(
                    item.toolName,
                    style: const TextStyle(
                      fontSize: 10,
                      color: AppColors.textMuted,
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: MetricsDashboardCanvas(data: item.metricsDashboard!),
            ),
          ],
        ),
      ),
    );
  }
}
