import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../services/dashboard_state.dart';
import '../../theme/app_theme.dart';

/// Dashboard panel showing Vega-Lite charts from the CA Data Agent.
///
/// Each item displays the question asked, the text answer, and any
/// Vega-Lite chart specs returned. Charts are shown as JSON specs
/// that can be copied for external rendering (full Vega-Lite rendering
/// can be added via a WebView or JS interop in a future iteration).
import 'manual_query_bar.dart';
import 'dashboard_card_wrapper.dart';
import '../common/explorer_empty_state.dart';

/// Dashboard panel showing Vega-Lite charts from the CA Data Agent.
class LiveChartsPanel extends StatelessWidget {
  final List<DashboardItem> items;
  final DashboardState dashboardState;
  const LiveChartsPanel({
    super.key,
    required this.items,
    required this.dashboardState,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
          child: ManualQueryBar(
            hintText: 'Search data answers...',
            initialValue: dashboardState.getLastQueryFilter(DashboardDataType.charts),
            isLoading: dashboardState.isLoading(DashboardDataType.charts),
            onSubmit: (query) {
              dashboardState.setLastQueryFilter(DashboardDataType.charts, query);
            },
          ),
        ),
        Expanded(
          child: items.isEmpty
              ? const ExplorerEmptyState(
                  icon: Icons.bar_chart_rounded,
                  title: 'No Charts Yet',
                  description:
                      'The analytics agent generates charts and data answers\nduring investigations.',
                )
              : ListView.builder(
                  padding: const EdgeInsets.all(12),
                  itemCount: items.length,
                  itemBuilder: (context, index) {
                    final item = items[index];
                    if (item.chartData == null) return const SizedBox.shrink();
                    return DashboardCardWrapper(
                      onClose: () => dashboardState.removeItem(item.id),
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
                      child: _ChartCard(data: item.chartData!, toolName: item.toolName),
                    );
                  },
                ),
        ),
      ],
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
        // Header info from CardWrapper is enough for the title row
        // Question text
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
          // Chart placeholders
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
        // Question text
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
