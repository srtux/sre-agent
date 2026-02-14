import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import '../../services/dashboard_state.dart';
import '../../services/explorer_query_service.dart';
import '../../theme/app_theme.dart';
import '../common/error_banner.dart';
import '../common/explorer_empty_state.dart';
import '../common/shimmer_loading.dart';
import '../common/source_badge.dart';
import '../syncfusion_metric_chart.dart';
import '../canvas/metrics_dashboard_canvas.dart';
import 'manual_query_bar.dart';
import 'dashboard_card_wrapper.dart';

/// Dashboard panel displaying all collected metric data.
///
/// Shows metrics in a responsive grid of charts, each rendered
/// with the SyncfusionMetricChart widget. Dashboard-type metrics
/// use the MetricsDashboardCanvas. Includes a manual query bar
/// for directly querying metrics.
class LiveMetricsPanel extends StatelessWidget {
  final List<DashboardItem> items;
  final DashboardState dashboardState;
  const LiveMetricsPanel({
    super.key,
    required this.items,
    required this.dashboardState,
  });

  @override
  Widget build(BuildContext context) {
    final isLoading = dashboardState.isLoading(DashboardDataType.metrics);
    final error = dashboardState.errorFor(DashboardDataType.metrics);

    return Column(
      children: [
        // Manual query bar
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
          child: ManualQueryBar(
            hintText: 'metric.type="compute.googleapis.com/..."',
            initialValue: dashboardState.getLastQueryFilter(DashboardDataType.metrics),
            isLoading: isLoading,
            onSubmit: (filter) {
              dashboardState.setLastQueryFilter(DashboardDataType.metrics, filter);
              final explorer = context.read<ExplorerQueryService>();
              explorer.queryMetrics(filter: filter);
            },
          ),
        ),
        if (error != null) ErrorBanner(message: error),
        // Content
        Expanded(
          child: isLoading && items.isEmpty
              ? const ShimmerLoading(showChart: true)
              : items.isEmpty
                  ? const ExplorerEmptyState(
                      icon: Icons.show_chart_rounded,
                      title: 'No Metrics Yet',
                      description:
                          'Query GCP Cloud Monitoring metrics by entering a\nmetric filter above, or wait for the agent to collect data.',
                      queryHint:
                          'metric.type="compute.googleapis.com/instance/cpu/utilization"',
                    )
                  : _buildMetricsList(context),
        ),
      ],
    );
  }

  Widget _buildMetricsList(BuildContext context) {
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
    return DashboardCardWrapper(
      onClose: () => dashboardState.removeItem(item.id),
      dataToCopy: const JsonEncoder.withIndent('  ').convert(item.rawData),
      header: Row(
        children: [
          const Icon(Icons.show_chart_rounded,
              size: 14, color: AppColors.warning),
          const SizedBox(width: 8),
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
          const SizedBox(width: 8),
          SourceBadge(source: item.source),
          const SizedBox(width: 8),
          Text(
            '${series.points.length} pts',
            style: const TextStyle(
              fontSize: 10,
              color: AppColors.textMuted,
            ),
          ),
        ],
      ),
      child: SizedBox(
        height: isWide ? 450 : 350,
        child: Padding(
          padding: const EdgeInsets.all(8),
          child: SyncfusionMetricChart(series: series),
        ),
      ),
    );
  }

  Widget _buildDashboardCard(DashboardItem item, bool isWide) {
    return DashboardCardWrapper(
      onClose: () => dashboardState.removeItem(item.id),
      header: Row(
        children: [
          const Icon(Icons.dashboard_rounded,
              size: 14, color: AppColors.warning),
          const SizedBox(width: 8),
          Text(
            'Golden Signals Dashboard',
            style: GoogleFonts.inter(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ),
          const Spacer(),
          SourceBadge(source: item.source),
          const SizedBox(width: 8),
          Text(
            item.toolName,
            style: const TextStyle(
              fontSize: 10,
              color: AppColors.textMuted,
            ),
          ),
        ],
      ),
      child: SizedBox(
        height: isWide ? 450 : 350,
        child: MetricsDashboardCanvas(data: item.metricsDashboard!),
      ),
    );
  }

}
