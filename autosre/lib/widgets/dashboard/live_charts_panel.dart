import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../services/dashboard_state.dart';
import '../../services/explorer_query_service.dart';
import '../../theme/app_theme.dart';
import '../common/error_banner.dart';
import '../common/explorer_empty_state.dart';
import '../common/shimmer_loading.dart';
import 'manual_query_bar.dart';
import 'dashboard_card_wrapper.dart';
import 'query_language_badge.dart';
import 'query_helpers.dart';
import 'sql_results_table.dart';
import 'visual_data_explorer.dart';
import 'bigquery_sidebar.dart';

/// Dashboard panel showing BigQuery SQL results and Vega-Lite charts.
///
/// Provides:
/// - **SQL Editor**: Multi-line BigQuery SQL query input
/// - **Tabular Results**: Sortable, exportable data table for SQL results
/// - **Visual Data Explorer**: Tableau-like interactive visualization builder
/// - **Agent Charts**: Vega-Lite chart specs from the CA Data Agent
class LiveChartsPanel extends StatefulWidget {
  final List<DashboardItem> items;
  final DashboardState dashboardState;
  final Function(String)? onPromptRequest;
  const LiveChartsPanel({
    super.key,
    required this.items,
    required this.dashboardState,
    this.onPromptRequest,
  });

  @override
  State<LiveChartsPanel> createState() => _LiveChartsPanelState();
}

class _LiveChartsPanelState extends State<LiveChartsPanel> {
  /// 0 = SQL Query, 1 = Agent Charts
  int _viewMode = 0;

  /// 0 = Table view, 1 = Visual Explorer
  int _resultsView = 0;

  late final TextEditingController _sqlController;

  @override
  void initState() {
    super.initState();
    _sqlController = TextEditingController(
      text: widget.dashboardState.getLastQueryFilter(DashboardDataType.charts),
    );
  }

  @override
  void dispose() {
    _sqlController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Header with view mode toggle
        _buildHeader(),
        // Content based on view mode
        Expanded(
          child: _viewMode == 0 ? _buildSqlView() : _buildAgentChartsView(),
        ),
      ],
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
      child: Row(
        children: [
          QueryLanguageBadge(
            language: _viewMode == 0 ? 'BigQuery SQL' : 'Agent Charts',
            icon: _viewMode == 0
                ? Icons.storage_rounded
                : Icons.bar_chart_rounded,
            color: AppColors.warning,
            onHelpTap: _viewMode == 0 ? () => _openDocs() : null,
          ),
          const Spacer(),
          // View mode toggle
          Container(
            padding: const EdgeInsets.all(2),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.05),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: AppColors.surfaceBorder.withValues(alpha: 0.3),
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildViewModeChip('SQL Query', Icons.code_rounded, 0),
                _buildViewModeChip(
                    'Agent Charts', Icons.auto_awesome_rounded, 1),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildViewModeChip(String label, IconData icon, int index) {
    final isActive = _viewMode == index;
    return GestureDetector(
      onTap: () => setState(() => _viewMode = index),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: isActive
              ? AppColors.warning.withValues(alpha: 0.15)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: isActive
                ? AppColors.warning.withValues(alpha: 0.3)
                : Colors.transparent,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 12,
              color: isActive ? AppColors.warning : AppColors.textMuted,
            ),
            const SizedBox(width: 4),
            Text(
              label,
              style: TextStyle(
                fontSize: 10,
                fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
                color: isActive ? AppColors.warning : AppColors.textMuted,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ===========================================================================
  // SQL Query View
  // ===========================================================================

  Widget _buildSqlView() {
    final isLoading =
        widget.dashboardState.isLoading(DashboardDataType.charts);
    final error = widget.dashboardState.errorFor(DashboardDataType.charts);

    return Row(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Left sidebar for schemas
        BigQuerySidebar(
          onInsertTable: (tableName) {
            final current = _sqlController.text;
            final prefix = current.isEmpty || current.endsWith(' ') || current.endsWith('\n') ? '' : ' ';
            _sqlController.text = current + prefix + tableName;
            widget.dashboardState.setLastQueryFilter(DashboardDataType.charts, _sqlController.text);
          },
          onInsertColumn: (columnName) {
            final current = _sqlController.text;
            final prefix = current.isEmpty || current.endsWith(' ') || current.endsWith('\n') ? '' : ', ';
            _sqlController.text = current + prefix + columnName;
            widget.dashboardState.setLastQueryFilter(DashboardDataType.charts, _sqlController.text);
          },
        ),
        // Main query and results area
        Expanded(
          child: ListenableBuilder(
            listenable: widget.dashboardState,
            builder: (context, _) {
              final hasResults = widget.dashboardState.bigQueryColumns.isNotEmpty;

              return Column(
                children: [
                  // SQL editor
                  Padding(
                    padding: const EdgeInsets.fromLTRB(12, 4, 12, 4),
                    child: ManualQueryBar(
                      controller: _sqlController,
                      hintText:
                          'SELECT column1, column2\nFROM `project.dataset.table`\nWHERE condition\nLIMIT 1000',
                      languageLabel: 'SQL',
                      languageLabelColor: AppColors.warning,
                      multiLine: true,
                      initialValue: widget.dashboardState
                          .getLastQueryFilter(DashboardDataType.charts),
                isLoading: isLoading,
                snippets: sqlSnippets,
                templates: sqlTemplates,
                enableNaturalLanguage: true,
                naturalLanguageHint:
                    'Show me the top 10 most expensive queries by slot usage...',
                naturalLanguageExamples: sqlNaturalLanguageExamples,
                onSubmitWithMode: (query, isNl) {
                  widget.dashboardState
                      .setLastQueryFilter(DashboardDataType.charts, query);
                  final explorer = context.read<ExplorerQueryService>();
                  if (isNl) {
                    if (widget.onPromptRequest != null) {
                      widget.onPromptRequest!(query);
                    }
                  } else {
                    explorer.queryBigQuery(sql: query);
                  }
                },
                onSubmit: (sql) {
                  widget.dashboardState
                      .setLastQueryFilter(DashboardDataType.charts, sql);
                  final explorer = context.read<ExplorerQueryService>();
                  explorer.queryBigQuery(sql: sql);
                },
                    ),
                  ),
                  // Syntax help
                  _buildSqlSyntaxHelp(),
                  if (error != null) ErrorBanner(message: error),
                  // Results area
                  if (isLoading && !hasResults)
                    const Expanded(child: ShimmerLoading())
                  else if (!hasResults)
                    const Expanded(
                      child: ExplorerEmptyState(
                        icon: Icons.storage_rounded,
                        title: 'BigQuery SQL Explorer',
                        description:
                            'Write a BigQuery SQL query above to explore data,\n'
                            'or switch to natural language mode.\n'
                            'Try the lightbulb for common SQL templates.',
                        queryHint:
                            'SELECT * FROM `project.dataset.table` LIMIT 100',
                      ),
                    )
                  else ...[
                    // Results view toggle (Table vs Visual Explorer)
                    _buildResultsViewToggle(),
                    // Results content
                    Expanded(
                      child: _resultsView == 0
                          ? SqlResultsTable(
                              columns: widget.dashboardState.bigQueryColumns,
                              rows: widget.dashboardState.bigQueryResults,
                            )
                          : VisualDataExplorer(
                              columns: widget.dashboardState.bigQueryColumns,
                              rows: widget.dashboardState.bigQueryResults,
                            ),
                    ),
                  ],
                ],
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _buildSqlSyntaxHelp() {
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
          Row(
            children: [
              Icon(Icons.keyboard_rounded,
                  size: 11,
                  color: AppColors.textMuted.withValues(alpha: 0.6)),
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
          Row(
            children: [
              Icon(Icons.info_outline_rounded,
                  size: 11,
                  color: AppColors.textMuted.withValues(alpha: 0.6)),
              const SizedBox(width: 5),
              Expanded(
                child: Text(
                  'BigQuery Standard SQL  |  Ctrl+Enter to run  |  '
                  'Tables: OTel spans, logs, metrics',
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 9,
                    color: AppColors.textMuted.withValues(alpha: 0.8),
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildResultsViewToggle() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.backgroundCard.withValues(alpha: 0.5),
        border: Border(
          bottom: BorderSide(
            color: AppColors.surfaceBorder.withValues(alpha: 0.3),
          ),
        ),
      ),
      child: Row(
        children: [
          _buildResultsViewChip('Table', Icons.table_chart_rounded, 0),
          const SizedBox(width: 4),
          _buildResultsViewChip('Visual Explorer', Icons.analytics_rounded, 1),
          const Spacer(),
          // Row count
          ListenableBuilder(
            listenable: widget.dashboardState,
            builder: (context, _) {
              return Text(
                '${widget.dashboardState.bigQueryResults.length} rows',
                style: TextStyle(
                  fontSize: 10,
                  color: AppColors.textMuted.withValues(alpha: 0.7),
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildResultsViewChip(String label, IconData icon, int index) {
    final isActive = _resultsView == index;
    return GestureDetector(
      onTap: () => setState(() => _resultsView = index),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: isActive
              ? AppColors.primaryCyan.withValues(alpha: 0.15)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: isActive
                ? AppColors.primaryCyan.withValues(alpha: 0.3)
                : AppColors.surfaceBorder.withValues(alpha: 0.2),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 12,
              color: isActive ? AppColors.primaryCyan : AppColors.textMuted,
            ),
            const SizedBox(width: 4),
            Text(
              label,
              style: TextStyle(
                fontSize: 10,
                fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
                color: isActive ? AppColors.primaryCyan : AppColors.textMuted,
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ===========================================================================
  // Agent Charts View (original Vega-Lite charts)
  // ===========================================================================

  Widget _buildAgentChartsView() {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 4, 12, 4),
          child: ManualQueryBar(
            hintText: 'Search data answers...',
            initialValue: widget.dashboardState
                .getLastQueryFilter(DashboardDataType.charts),
            isLoading:
                widget.dashboardState.isLoading(DashboardDataType.charts),
            onSubmit: (query) {
              widget.dashboardState
                  .setLastQueryFilter(DashboardDataType.charts, query);
            },
          ),
        ),
        Expanded(
          child: widget.items.isEmpty
              ? const ExplorerEmptyState(
                  icon: Icons.bar_chart_rounded,
                  title: 'No Charts Yet',
                  description:
                      'The analytics agent generates charts and data answers\nduring investigations.',
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: widget.items.length,
                  itemBuilder: (context, index) {
                    final item = widget.items[index];
                    if (item.chartData == null) return const SizedBox.shrink();
                    return DashboardCardWrapper(
                      onClose: () =>
                          widget.dashboardState.removeItem(item.id),
                      header: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(4),
                            decoration: BoxDecoration(
                              color:
                                  AppColors.warning.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: const Icon(
                              Icons.bar_chart_rounded,
                              size: 14,
                              color: AppColors.warning,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              item.chartData?.question ?? 'Data Analysis',
                              style: const TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                                color: AppColors.textPrimary,
                              ),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                      child: _ChartCard(
                          data: item.chartData!, toolName: item.toolName),
                    );
                  },
                ),
        ),
      ],
    );
  }

  Future<void> _openDocs() async {
    final url = Uri.parse(
      'https://cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax',
    );
    if (await canLaunchUrl(url)) {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    }
  }
}

class _ChartCard extends StatefulWidget {
  final dynamic data;
  final String toolName;
  const _ChartCard({required this.data, required this.toolName});

  @override
  State<_ChartCard> createState() => _ChartCardState();
}

class _ChartCardState extends State<_ChartCard> {
  bool _showSpec = false;

  @override
  Widget build(BuildContext context) {
    final data = widget.data;
    final answer = data.answer as String? ?? '';
    final hasCharts = data.hasCharts as bool? ?? false;
    final charts = hasCharts ? data.vegaLiteCharts as List : [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Answer text
        if (answer.isNotEmpty)
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
            child: Text(
              answer,
              style: const TextStyle(
                fontSize: 12,
                color: AppColors.textSecondary,
                height: 1.5,
              ),
              maxLines: 10,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        // Chart previews
        if (charts.isNotEmpty)
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 4, 12, 8),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                for (var i = 0; i < charts.length; i++)
                  _buildChartPreview(charts[i] as Map<String, dynamic>, i),
              ],
            ),
          ),
      ],
    );
  }

  Widget _buildChartPreview(Map<String, dynamic> spec, int index) {
    final title = spec['title'] as String? ??
        spec['description'] as String? ??
        'Chart ${index + 1}';
    final mark = spec['mark'];
    final markType =
        mark is String ? mark : (mark is Map ? mark['type'] ?? 'unknown' : 'unknown');

    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.backgroundDark,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: AppColors.warning.withValues(alpha: 0.2),
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Chart info bar
            Padding(
              padding: const EdgeInsets.fromLTRB(10, 8, 10, 6),
              child: Row(
                children: [
                  Icon(
                    _iconForMark(markType.toString()),
                    size: 14,
                    color: AppColors.warning,
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      title.toString(),
                      style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w500,
                        color: AppColors.textPrimary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Text(
                    markType.toString(),
                    style: const TextStyle(
                      fontSize: 10,
                      color: AppColors.textMuted,
                    ),
                  ),
                  const SizedBox(width: 8),
                  InkWell(
                    onTap: () => _copySpec(spec),
                    child: const Icon(
                      Icons.copy_rounded,
                      size: 14,
                      color: AppColors.textMuted,
                    ),
                  ),
                  const SizedBox(width: 6),
                  InkWell(
                    onTap: () => setState(() => _showSpec = !_showSpec),
                    child: Icon(
                      _showSpec
                          ? Icons.code_off_rounded
                          : Icons.code_rounded,
                      size: 14,
                      color: AppColors.textMuted,
                    ),
                  ),
                ],
              ),
            ),
            // Expandable spec view
            if (_showSpec)
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppColors.backgroundCard.withValues(alpha: 0.5),
                  borderRadius: const BorderRadius.only(
                    bottomLeft: Radius.circular(8),
                    bottomRight: Radius.circular(8),
                  ),
                ),
                child: SelectableText(
                  const JsonEncoder.withIndent('  ').convert(spec),
                  style: const TextStyle(
                    fontSize: 10,
                    fontFamily: 'monospace',
                    color: AppColors.textSecondary,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  IconData _iconForMark(String markType) {
    switch (markType.toLowerCase()) {
      case 'bar':
        return Icons.bar_chart_rounded;
      case 'line':
        return Icons.show_chart_rounded;
      case 'area':
        return Icons.area_chart_rounded;
      case 'point':
      case 'circle':
        return Icons.scatter_plot_rounded;
      case 'arc':
        return Icons.pie_chart_rounded;
      default:
        return Icons.insert_chart_rounded;
    }
  }

  void _copySpec(Map<String, dynamic> spec) {
    final jsonStr = const JsonEncoder.withIndent('  ').convert(spec);
    Clipboard.setData(ClipboardData(text: jsonStr));
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Vega-Lite spec copied to clipboard'),
          duration: Duration(seconds: 2),
        ),
      );
    }
  }
}
