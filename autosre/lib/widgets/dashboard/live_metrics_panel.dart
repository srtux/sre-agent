import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

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
import 'query_language_badge.dart';
import 'query_language_toggle.dart';

/// Dashboard panel displaying all collected metric data.
///
/// Shows metrics in a responsive grid of charts, each rendered
/// with the SyncfusionMetricChart widget. Dashboard-type metrics
/// use the MetricsDashboardCanvas.
///
/// Supports two query languages with a toggle:
/// - **ListTimeSeries** (MQL filter): Standard Cloud Monitoring filter syntax
/// - **PromQL**: Prometheus Query Language for metric queries
class LiveMetricsPanel extends StatelessWidget {
  final List<DashboardItem> items;
  final DashboardState dashboardState;
  const LiveMetricsPanel({
    super.key,
    required this.items,
    required this.dashboardState,
  });

  static const _languages = ['MQL Filter', 'PromQL'];

  static const _hints = [
    'metric.type="compute.googleapis.com/instance/cpu/utilization"',
    'rate(compute_googleapis_com:instance_cpu_utilization[5m])',
  ];

  static const _syntaxExamples = [
    // MQL / ListTimeSeries filter examples
    [
      ('metric.type="..."', 'Required metric type filter'),
      ('metric.labels.key="value"', 'Filter by metric label'),
      ('resource.type="gce_instance"', 'Filter by resource type'),
      ('resource.labels.zone="us-c1-a"', 'Filter by resource label'),
    ],
    // PromQL examples
    [
      ('metric_name{label="val"}', 'Instant vector selector'),
      ('rate(metric[5m])', 'Per-second rate over 5 min'),
      ('sum by (label) (metric)', 'Aggregate by label'),
      ('histogram_quantile(0.95, ...)', '95th percentile'),
    ],
  ];

  @override
  Widget build(BuildContext context) {
    final isLoading = dashboardState.isLoading(DashboardDataType.metrics);
    final error = dashboardState.errorFor(DashboardDataType.metrics);

    return ListenableBuilder(
      listenable: dashboardState,
      builder: (context, _) {
        final langIndex = dashboardState.metricsQueryLanguage;

        return Column(
          children: [
            // Query language header + toggle
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
              child: Column(
                children: [
                  // Language badge + toggle row
                  Row(
                    children: [
                      QueryLanguageBadge(
                        language: _languages[langIndex],
                        icon: Icons.show_chart_rounded,
                        color: AppColors.warning,
                        onHelpTap: () => _openDocs(langIndex),
                      ),
                      const SizedBox(width: 8),
                      QueryLanguageToggle(
                        languages: _languages,
                        selectedIndex: langIndex,
                        onChanged: (i) =>
                            dashboardState.setMetricsQueryLanguage(i),
                        activeColor: AppColors.warning,
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  // Query bar
                  ManualQueryBar(
                    hintText: _hints[langIndex],
                    languageLabel: langIndex == 0 ? 'MQL' : 'PromQL',
                    languageLabelColor: AppColors.warning,
                    initialValue: dashboardState
                        .getLastQueryFilter(DashboardDataType.metrics),
                    isLoading: isLoading,
                    onSubmit: (filter) {
                      dashboardState.setLastQueryFilter(
                          DashboardDataType.metrics, filter);
                      final explorer = context.read<ExplorerQueryService>();
                      if (langIndex == 0) {
                        explorer.queryMetrics(filter: filter);
                      } else {
                        explorer.queryMetricsPromQL(query: filter);
                      }
                    },
                  ),
                ],
              ),
            ),
            // Syntax reference
            _buildSyntaxHelp(langIndex),
            if (error != null) ErrorBanner(message: error),
            // Content
            Expanded(
              child: isLoading && items.isEmpty
                  ? const ShimmerLoading(showChart: true)
                  : items.isEmpty
                      ? ExplorerEmptyState(
                          icon: Icons.show_chart_rounded,
                          title: 'No Metrics Yet',
                          description: langIndex == 0
                              ? 'Query Cloud Monitoring metrics using ListTimeSeries\nfilter syntax, or wait for the agent to collect data.'
                              : 'Query Cloud Monitoring metrics using PromQL\nexpressions, or wait for the agent to collect data.',
                          queryHint: _hints[langIndex],
                        )
                      : _buildMetricsList(context),
            ),
          ],
        );
      },
    );
  }

  Widget _buildSyntaxHelp(int langIndex) {
    final examples = _syntaxExamples[langIndex];
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 0, 12, 4),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.warning.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: AppColors.warning.withValues(alpha: 0.1),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ...examples.map((e) => Padding(
                padding: const EdgeInsets.only(bottom: 2),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(
                      width: 220,
                      child: Text(
                        (e as (String, String)).$1,
                        style: GoogleFonts.jetBrainsMono(
                          fontSize: 9,
                          color: AppColors.warning.withValues(alpha: 0.9),
                        ),
                      ),
                    ),
                    Expanded(
                      child: Text(
                        e.$2,
                        style: TextStyle(
                          fontSize: 9,
                          color: AppColors.textMuted.withValues(alpha: 0.8),
                        ),
                      ),
                    ),
                  ],
                ),
              )),
        ],
      ),
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

  Future<void> _openDocs(int langIndex) async {
    final urls = [
      'https://cloud.google.com/monitoring/api/v3/filters',
      'https://cloud.google.com/monitoring/promql',
    ];
    final url = Uri.parse(urls[langIndex]);
    if (await canLaunchUrl(url)) {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    }
  }
}
