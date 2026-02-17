import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../services/dashboard_state.dart';
import '../../services/explorer_query_service.dart';
import '../../theme/app_theme.dart';
import '../common/error_banner.dart';
import '../common/explorer_empty_state.dart';
import '../common/shimmer_loading.dart';
import 'bigquery_sidebar.dart';
import 'bigquery_sql_syntax_controller.dart';
import 'dashboard_card_wrapper.dart';

import 'manual_query_bar.dart';
import 'query_helpers.dart';
import 'sql_results_table.dart';
import 'visual_data_explorer.dart';

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

  bool _showSidebar = true;
  double _sidebarWidth = 280.0;
  List<QuerySnippet> _schemaSnippets = [];

  late final BigQuerySqlSyntaxController _sqlController;

  bool _helpDismissed = false;
  bool _helpDismissedLoaded = false;

  @override
  void initState() {
    super.initState();
    _loadHelpDismissed();
    _sqlController = BigQuerySqlSyntaxController(
      text: widget.dashboardState.getLastQueryFilter(
        DashboardDataType.analytics,
      ),
    );
  }

  Future<void> _loadHelpDismissed() async {
    final prefs = await SharedPreferences.getInstance();
    if (mounted) {
      setState(() {
        _helpDismissed = prefs.getBool('charts_help_dismissed') ?? false;
        _helpDismissedLoaded = true;
      });
    }
  }

  Future<void> _dismissHelp() async {
    setState(() => _helpDismissed = true);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('charts_help_dismissed', true);
  }

  @override
  void dispose() {
    _sqlController.dispose();
    super.dispose();
  }

  void _insertAtCursor(String textToInsert, String separator) {
    final text = _sqlController.text;
    final selection = _sqlController.selection;

    // If there's no valid selection, append to the end
    if (!selection.isValid) {
      final prefix = text.isEmpty || text.endsWith(' ') || text.endsWith('\n')
          ? ''
          : separator;
      _sqlController.text = text + prefix + textToInsert;
      _sqlController.selection = TextSelection.collapsed(
        offset: _sqlController.text.length,
      );
      return;
    }

    final beforeCursor = text.substring(0, selection.baseOffset);
    final afterCursor = text.substring(selection.extentOffset);

    final prefix =
        beforeCursor.isEmpty ||
            beforeCursor.endsWith(' ') ||
            beforeCursor.endsWith('\n')
        ? ''
        : separator;

    final insertedText = prefix + textToInsert;
    _sqlController.text = beforeCursor + insertedText + afterCursor;
    _sqlController.selection = TextSelection.collapsed(
      offset: beforeCursor.length + insertedText.length,
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_viewMode == 0) return _buildSqlView();
    return _buildAgentChartsView();
  }

  // ===========================================================================
  // SQL Query View
  // ===========================================================================

  Widget _buildSqlView() {
    final isLoading = widget.dashboardState.isLoading(
      DashboardDataType.analytics,
    );
    final error = widget.dashboardState.errorFor(DashboardDataType.analytics);

    return Row(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Left sidebar for schemas
        if (_showSidebar) ...[
          SizedBox(
            width: _sidebarWidth,
            child: BigQuerySidebar(
              onClose: () => setState(() => _showSidebar = false),
              onInsertTable: (tableName) {
                _insertAtCursor(tableName, ' ');
                widget.dashboardState.setLastQueryFilter(
                  DashboardDataType.analytics,
                  _sqlController.text,
                );
              },
              onInsertColumn: (columnName) {
                _insertAtCursor(columnName, ', ');
                widget.dashboardState.setLastQueryFilter(
                  DashboardDataType.analytics,
                  _sqlController.text,
                );
              },
              onSchemaUpdated: (snippets) {
                setState(() {
                  _schemaSnippets = snippets;
                });
              },
            ),
          ),
          // Resizer handle
          GestureDetector(
            onHorizontalDragUpdate: (details) {
              setState(() {
                _sidebarWidth = (_sidebarWidth + details.delta.dx).clamp(
                  200.0,
                  600.0,
                );
              });
            },
            child: MouseRegion(
              cursor: SystemMouseCursors.resizeLeftRight,
              child: Container(
                width: 4,
                color: Colors.transparent,
                child: Center(
                  child: Container(
                    width: 1,
                    height: 40,
                    decoration: BoxDecoration(
                      color: AppColors.surfaceBorder.withValues(alpha: 0.3),
                      borderRadius: BorderRadius.circular(1),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
        // Main query and results area
        Expanded(
          child: ListenableBuilder(
            listenable: widget.dashboardState,
            builder: (context, _) {
              final sqlItems = widget.dashboardState
                  .itemsOfType(DashboardDataType.analytics)
                  .where((i) => i.sqlData != null)
                  .toList();
              final hasResults = sqlItems.isNotEmpty;

              return Column(
                children: [
                  // SQL editor
                  Padding(
                    padding: const EdgeInsets.fromLTRB(12, 4, 12, 4),
                    child: ManualQueryBar(
                      leading: IconButton(
                        icon: Icon(
                          _showSidebar
                              ? Icons.menu_open_rounded
                              : Icons.menu_rounded,
                          size: 18,
                        ),
                        color: _showSidebar
                            ? AppColors.primaryCyan
                            : AppColors.textMuted,
                        onPressed: () =>
                            setState(() => _showSidebar = !_showSidebar),
                        tooltip: _showSidebar ? 'Hide Schema' : 'Show Schema',
                      ),
                      controller: _sqlController,
                      hintText:
                          'SELECT column1, column2\nFROM `project.dataset.table`\nWHERE condition\nLIMIT 1000',
                      panelType: 'analytics',
                      dashboardState: widget.dashboardState,
                      onRefresh: () {
                        final sql = widget.dashboardState.getLastQueryFilter(
                          DashboardDataType.analytics,
                        );
                        if (sql != null && sql.isNotEmpty) {
                          final explorer = context.read<ExplorerQueryService>();
                          explorer.queryBigQuery(sql: sql);
                        }
                      },
                      languageLabelColor: AppColors.warning,
                      languages: const ['BigQuery SQL', 'Agent Charts'],
                      selectedLanguageIndex: 0,
                      onLanguageChanged: (i) => setState(() => _viewMode = i),
                      multiLine: true,
                      initialValue: widget.dashboardState.getLastQueryFilter(
                        DashboardDataType.analytics,
                      ),
                      isLoading: isLoading,
                      snippets: [
                        ...sqlSnippets,
                        ..._schemaSnippets,
                      ],
                      templates: sqlTemplates,
                      enableNaturalLanguage: true,
                      naturalLanguageHint:
                          'Show me the top 10 most expensive queries by slot usage...',
                      naturalLanguageExamples: sqlNaturalLanguageExamples,
                      onSubmitWithMode: (query, isNl) {
                        widget.dashboardState.setLastQueryFilter(
                          DashboardDataType.analytics,
                          query,
                        );
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
                        widget.dashboardState.setLastQueryFilter(
                          DashboardDataType.analytics,
                          sql,
                        );
                        final explorer = context.read<ExplorerQueryService>();
                        explorer.queryBigQuery(sql: sql);
                      },
                    ),
                  ),
                  // Syntax help
                  if (_helpDismissedLoaded && !_helpDismissed) _buildSqlSyntaxHelp(),
                  if (error != null)
                    ErrorBanner(
                      message: error,
                      onDismiss: () => widget.dashboardState.setError(
                        DashboardDataType.analytics,
                        null,
                      ),
                    ),
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
                    // Selection for which result to show in table vs visual explorer
                    // Actually, if we show cards, we can just show them all.
                    Expanded(
                      child: ListView.builder(
                        padding: const EdgeInsets.all(12),
                        itemCount: sqlItems.length,
                        itemBuilder: (context, index) {
                          // Show in reverse chronological order
                          final item = sqlItems[sqlItems.length - 1 - index];
                          if (item.sqlData == null) {
                            return const SizedBox.shrink();
                          }

                          return Padding(
                            padding: const EdgeInsets.only(bottom: 16),
                            child: _SqlResultCard(
                              item: item,
                              dashboardState: widget.dashboardState,
                            ),
                          );
                        },
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
                  Row(
                    children: [
                      Icon(
                        Icons.info_outline_rounded,
                        size: 11,
                        color: AppColors.textMuted.withValues(alpha: 0.6),
                      ),
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

  // ===========================================================================
  // Agent Charts View (original Vega-Lite charts)
  // ===========================================================================

  Widget _buildAgentChartsView() {
    final chartItems = widget.items.where((i) => i.chartData != null).toList();
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 4, 12, 4),
          child: ManualQueryBar(
            hintText: 'Search data answers...',
            panelType: 'analytics',
            dashboardState: widget.dashboardState,
            languages: const ['BigQuery SQL', 'Agent Charts'],
            selectedLanguageIndex: 1,
            onLanguageChanged: (i) => setState(() => _viewMode = i),
            languageLabelColor: AppColors.warning,
            initialValue: widget.dashboardState.getLastQueryFilter(
              DashboardDataType.analytics,
            ),
            isLoading: widget.dashboardState.isLoading(
              DashboardDataType.analytics,
            ),
            onSubmit: (query) {
              widget.dashboardState.setLastQueryFilter(
                DashboardDataType.analytics,
                query,
              );
            },
          ),
        ),
        Expanded(
          child: chartItems.isEmpty
              ? const ExplorerEmptyState(
                  icon: Icons.bar_chart_rounded,
                  title: 'No Charts Yet',
                  description:
                      'The analytics agent generates charts and data answers\nduring investigations.',
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: chartItems.length,
                  itemBuilder: (context, index) {
                    final item = chartItems[index];
                    if (item.chartData == null) return const SizedBox.shrink();
                    return DashboardCardWrapper(
                      onClose: () => widget.dashboardState.removeItem(item.id),
                      header: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(4),
                            decoration: BoxDecoration(
                              color: AppColors.warning.withValues(alpha: 0.15),
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
                        data: item.chartData!,
                        toolName: item.toolName,
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }
}

class _SqlResultCard extends StatefulWidget {
  final DashboardItem item;
  final DashboardState dashboardState;

  const _SqlResultCard({
    required this.item,
    required this.dashboardState,
  });

  @override
  State<_SqlResultCard> createState() => _SqlResultCardState();
}

class _SqlResultCardState extends State<_SqlResultCard> {
  bool _showVisualizer = false;

  @override
  Widget build(BuildContext context) {
    final sqlData = widget.item.sqlData!;

    return DashboardCardWrapper(
      onClose: () => widget.dashboardState.removeItem(widget.item.id),
      header: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
              color: AppColors.primaryCyan.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(6),
            ),
            child: const Icon(
              Icons.table_chart_rounded,
              size: 14,
              color: AppColors.primaryCyan,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              sqlData.query.replaceAll('\n', ' '),
              style: GoogleFonts.jetBrainsMono(
                fontSize: 10,
                fontWeight: FontWeight.w500,
                color: AppColors.textPrimary,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(width: 8),
          Text(
            '${sqlData.rows.length} rows',
            style: const TextStyle(
              fontSize: 9,
              color: AppColors.textMuted,
            ),
          ),
          const SizedBox(width: 12),
          // View Toggle
          Container(
            decoration: BoxDecoration(
              color: AppColors.backgroundDark,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(
                color: AppColors.surfaceBorder.withValues(alpha: 0.5),
              ),
            ),
            child: Row(
              children: [
                _buildToggleBtn(
                  icon: Icons.table_rows_rounded,
                  label: 'Table',
                  isActive: !_showVisualizer,
                  onTap: () => setState(() => _showVisualizer = false),
                ),
                _buildToggleBtn(
                  icon: Icons.bar_chart_rounded,
                  label: 'Visualize',
                  isActive: _showVisualizer,
                  onTap: () => setState(() => _showVisualizer = true),
                ),
              ],
            ),
          ),
        ],
      ),
      child: SizedBox(
        height: 600, // Larger fixed height for each result card
        child: _showVisualizer
            ? VisualDataExplorer(
                columns: sqlData.columns,
                rows: sqlData.rows,
              )
            : SqlResultsTable(
                columns: sqlData.columns,
                rows: sqlData.rows,
              ),
      ),
    );
  }

  Widget _buildToggleBtn({
    required IconData icon,
    required String label,
    required bool isActive,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(5),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: isActive
              ? AppColors.primaryCyan.withValues(alpha: 0.2)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(5),
        ),
        child: Row(
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
                fontWeight: isActive ? FontWeight.w600 : FontWeight.w500,
                color: isActive ? AppColors.primaryCyan : AppColors.textMuted,
              ),
            ),
          ],
        ),
      ),
    );
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
    final title =
        spec['title'] as String? ??
        spec['description'] as String? ??
        'Chart ${index + 1}';
    final mark = spec['mark'];
    final markType = mark is String
        ? mark
        : (mark is Map ? mark['type'] ?? 'unknown' : 'unknown');

    return Padding(
      padding: const EdgeInsets.only(top: 6),
      child: Container(
        decoration: BoxDecoration(
          color: AppColors.backgroundDark,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: AppColors.warning.withValues(alpha: 0.2)),
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
                      _showSpec ? Icons.code_off_rounded : Icons.code_rounded,
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
