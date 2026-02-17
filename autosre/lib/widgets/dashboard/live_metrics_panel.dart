import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

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
import 'query_helpers.dart';

/// Dashboard panel displaying all collected metric data.
///
/// Supports two query languages with a toggle plus natural language:
/// - **MQL Filter** (ListTimeSeries): Standard Cloud Monitoring filter syntax
/// - **PromQL**: Prometheus Query Language for metric queries
/// - **Natural Language**: Describe the metric you want to find
class LiveMetricsPanel extends StatefulWidget {
  final List<DashboardItem> items;
  final DashboardState dashboardState;
  final Function(String)? onPromptRequest;
  const LiveMetricsPanel({
    super.key,
    required this.items,
    required this.dashboardState,
    this.onPromptRequest,
  });

  @override
  State<LiveMetricsPanel> createState() => _LiveMetricsPanelState();
}

class _LiveMetricsPanelState extends State<LiveMetricsPanel> {

  static const _languages = ['MQL Filter', 'PromQL'];

  static const _hints = [
    'metric.type="compute.googleapis.com/instance/cpu/utilization"',
    'rate(compute_googleapis_com:instance_cpu_utilization[5m])',
  ];

  static const _syntaxExamples = [
    [
      ('metric.type="..."', 'Required metric type filter'),
      ('metric.labels.key="value"', 'Filter by metric label'),
      ('resource.type="gce_instance"', 'Filter by resource type'),
      ('resource.labels.zone="us-c1-a"', 'Filter by resource label'),
    ],
    [
      ('metric_name{label="val"}', 'Instant vector selector'),
      ('rate(metric[5m])', 'Per-second rate over 5 min'),
      ('sum by (label) (metric)', 'Aggregate by label'),
      ('histogram_quantile(0.95, ...)', '95th percentile'),
    ],
  ];

  bool _helpDismissed = false;
  bool _helpDismissedLoaded = false;

  @override
  void initState() {
    super.initState();
    _loadHelpDismissed();
  }

  Future<void> _loadHelpDismissed() async {
    final prefs = await SharedPreferences.getInstance();
    if (mounted) {
      setState(() {
        _helpDismissed = prefs.getBool('metrics_help_dismissed') ?? false;
        _helpDismissedLoaded = true;
      });
    }
  }

  Future<void> _dismissHelp() async {
    setState(() => _helpDismissed = true);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('metrics_help_dismissed', true);
  }

  @override
  Widget build(BuildContext context) {
    final isLoading = widget.dashboardState.isLoading(DashboardDataType.metrics);
    final error = widget.dashboardState.errorFor(DashboardDataType.metrics);

    return ListenableBuilder(
      listenable: widget.dashboardState,
      builder: (context, _) {
        final langIndex = widget.dashboardState.metricsQueryLanguage;

        return Column(
          children: [
            // Query language header + toggle
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
              child: Column(
                children: [
                  ManualQueryBar(
                    hintText: _hints[langIndex],
                    panelType: 'metrics',
                    dashboardState: widget.dashboardState,
                    onRefresh: () {
                      final filter = widget.dashboardState.getLastQueryFilter(
                        DashboardDataType.metrics,
                      );
                      if (filter != null && filter.isNotEmpty) {
                        final explorer = context.read<ExplorerQueryService>();
                        if (langIndex == 0) {
                          explorer.queryMetrics(filter: filter);
                        } else {
                          explorer.queryMetricsPromQL(query: filter);
                        }
                      }
                    },
                    languages: _languages,
                    selectedLanguageIndex: langIndex,
                    onLanguageChanged: (i) =>
                        widget.dashboardState.setMetricsQueryLanguage(i),
                    languageLabelColor: AppColors.warning,
                    initialValue: widget.dashboardState.getLastQueryFilter(
                      DashboardDataType.metrics,
                    ),
                    isLoading: isLoading,
                    snippets: langIndex == 0 ? mqlSnippets : promqlSnippets,
                    templates: langIndex == 0
                        ? metricsTemplates
                        : promqlTemplates,
                    enableNaturalLanguage: true,
                    naturalLanguageHint:
                        'What is the CPU utilization across all instances?',
                    naturalLanguageExamples: metricsNaturalLanguageExamples,
                    onSubmitWithMode: (query, isNl) {
                      widget.dashboardState.setLastQueryFilter(
                        DashboardDataType.metrics,
                        query,
                      );
                      final explorer = context.read<ExplorerQueryService>();
                      if (isNl) {
                        if (widget.onPromptRequest != null) {
                          widget.onPromptRequest!(query);
                        }
                      } else if (langIndex == 0) {
                        explorer.queryMetrics(filter: query);
                      } else {
                        explorer.queryMetricsPromQL(query: query);
                      }
                    },
                    onSubmit: (filter) {
                      widget.dashboardState.setLastQueryFilter(
                        DashboardDataType.metrics,
                        filter,
                      );
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
            // Syntax reference + inline help
            if (_helpDismissedLoaded && !_helpDismissed) _buildSyntaxHelp(langIndex),
            if (error != null)
              ErrorBanner(
                message: error,
                onDismiss: () =>
                    widget.dashboardState.setError(DashboardDataType.metrics, null),
              ),
            Expanded(
              child: isLoading && widget.items.isEmpty
                  ? const ShimmerLoading(showChart: true)
                  : widget.items.isEmpty
                  ? ExplorerEmptyState(
                      icon: Icons.show_chart_rounded,
                      title: 'No Metrics Yet',
                      description: langIndex == 0
                          ? 'Query metrics using ListTimeSeries filter syntax,\n'
                                'or switch to natural language mode.\n'
                                'Try the lightbulb for common metric templates.'
                          : 'Query metrics using PromQL expressions,\n'
                                'or switch to natural language mode.\n'
                                'Try the lightbulb for common PromQL templates.',
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
    return AnimatedSize(
      duration: const Duration(milliseconds: 200),
      curve: Curves.easeOut,
      child: Container(
        margin: const EdgeInsets.fromLTRB(12, 0, 12, 4),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: AppColors.warning.withValues(alpha: 0.04),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: AppColors.warning.withValues(alpha: 0.1)),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Inline help hint
                  Row(
                    children: [
                      Icon(
                        Icons.keyboard_rounded,
                        size: 11,
                        color: AppColors.textMuted.withValues(alpha: 0.6),
                      ),
                      const SizedBox(width: 5),
                      Text(
                        'Tab to autocomplete  |  '
                        'Lightbulb for templates  |  '
                        'NL toggle for natural language',
                        style: TextStyle(
                          fontSize: 9,
                          color: AppColors.textMuted.withValues(alpha: 0.7),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  // Syntax examples
                  ...examples.map(
                    (e) => Padding(
                      padding: const EdgeInsets.only(bottom: 2),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          SizedBox(
                            width: 220,
                            child: Text(
                              (e).$1,
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
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 4),
            SizedBox(
              width: 20,
              height: 20,
              child: IconButton(
                icon: const Icon(Icons.close, size: 12),
                padding: EdgeInsets.zero,
                color: AppColors.textMuted.withValues(alpha: 0.6),
                onPressed: _dismissHelp,
                style: IconButton.styleFrom(
                  minimumSize: const Size(20, 20),
                  backgroundColor: Colors.transparent,
                ),
                tooltip: 'Dismiss',
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildMetricsList(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final isWide = constraints.maxWidth > 500;
        return ListView.builder(
          padding: const EdgeInsets.all(12),
          itemCount: widget.items.length,
          itemBuilder: (context, index) {
            final item = widget.items[index];
            if (item.metricsDashboard != null) {
              return _buildDashboardCard(item, isWide);
            }
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
      onClose: () => widget.dashboardState.removeItem(item.id),
      dataToCopy: const JsonEncoder.withIndent('  ').convert(item.rawData),
      header: Row(
        children: [
          const Icon(
            Icons.show_chart_rounded,
            size: 14,
            color: AppColors.warning,
          ),
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
            style: const TextStyle(fontSize: 10, color: AppColors.textMuted),
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
      onClose: () => widget.dashboardState.removeItem(item.id),
      header: Row(
        children: [
          const Icon(
            Icons.dashboard_rounded,
            size: 14,
            color: AppColors.warning,
          ),
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
            style: const TextStyle(fontSize: 10, color: AppColors.textMuted),
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
