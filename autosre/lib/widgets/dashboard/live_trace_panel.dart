import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../services/dashboard_state.dart';
import '../../services/explorer_query_service.dart';
import '../../services/project_service.dart';
import '../../theme/app_theme.dart';
import '../common/error_banner.dart';
import '../common/explorer_empty_state.dart';
import '../common/shimmer_loading.dart';
import '../common/source_badge.dart';
import '../syncfusion_trace_waterfall.dart';
import 'manual_query_bar.dart';
import 'dashboard_card_wrapper.dart';
import 'query_language_badge.dart';

/// Dashboard panel that displays all collected trace results.
///
/// Shows traces in a scrollable list with expandable waterfall views.
/// Each trace shows a summary header with span count and duration,
/// and can be expanded to reveal the full Syncfusion waterfall visualization.
///
/// Supports two query modes:
/// - **Trace ID**: Direct lookup by trace ID
/// - **Cloud Trace Filter**: Cloud Trace Query language filter expressions
class LiveTracePanel extends StatefulWidget {
  final List<DashboardItem> items;
  final DashboardState dashboardState;
  const LiveTracePanel({
    super.key,
    required this.items,
    required this.dashboardState,
  });

  @override
  State<LiveTracePanel> createState() => _LiveTracePanelState();
}

class _LiveTracePanelState extends State<LiveTracePanel> {
  /// 0 = Cloud Trace Filter, 1 = Trace ID lookup
  int _queryMode = 0;

  @override
  Widget build(BuildContext context) {
    final isLoading =
        widget.dashboardState.isLoading(DashboardDataType.traces);
    final error = widget.dashboardState.errorFor(DashboardDataType.traces);

    return Column(
      children: [
        // Query language header
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
          child: Column(
            children: [
              // Language selector row
              Row(
                children: [
                  QueryLanguageBadge(
                    language: 'Cloud Trace',
                    icon: Icons.timeline_rounded,
                    color: AppColors.primaryCyan,
                    onHelpTap: () => _openDocs(),
                  ),
                  const Spacer(),
                  _buildModeToggle(),
                ],
              ),
              const SizedBox(height: 6),
              // Query bar changes based on mode
              if (_queryMode == 0)
                ManualQueryBar(
                  hintText:
                      '+span:name:my_service RootSpan:/api/v1 MinDuration:100ms',
                  languageLabel: 'FILTER',
                  languageLabelColor: AppColors.primaryCyan,
                  initialValue: widget.dashboardState
                      .getLastQueryFilter(DashboardDataType.traces),
                  isLoading: isLoading,
                  onSubmit: (filter) {
                    widget.dashboardState
                        .setLastQueryFilter(DashboardDataType.traces, filter);
                    final explorer = context.read<ExplorerQueryService>();
                    explorer.queryTraceFilter(filter: filter);
                  },
                )
              else
                ManualQueryBar(
                  hintText: 'Enter Trace ID (e.g. abc123def456789...)',
                  initialValue: widget.dashboardState
                      .getLastQueryFilter(DashboardDataType.traces),
                  isLoading: isLoading,
                  onSubmit: (traceId) {
                    widget.dashboardState
                        .setLastQueryFilter(DashboardDataType.traces, traceId);
                    final explorer = context.read<ExplorerQueryService>();
                    explorer.queryTrace(traceId: traceId);
                  },
                ),
            ],
          ),
        ),
        // Syntax reference (collapsed by default)
        _buildSyntaxHelp(),
        if (error != null) ErrorBanner(message: error),
        // Content
        Expanded(
          child: isLoading && widget.items.isEmpty
              ? const ShimmerLoading(showChart: true)
              : widget.items.isEmpty
                  ? ExplorerEmptyState(
                      icon: Icons.timeline_rounded,
                      title: 'No Traces Yet',
                      description: _queryMode == 0
                          ? 'Enter a Cloud Trace filter expression above to search\nfor traces, or wait for the agent to find traces.'
                          : 'Enter a Cloud Trace ID above to visualize\nthe distributed trace waterfall, or wait for the agent to find traces.',
                      queryHint: _queryMode == 0
                          ? 'e.g. +span:name:my_service MinDuration:100ms'
                          : 'e.g. abc123def456789...',
                    )
                  : _buildTraceList(),
        ),
      ],
    );
  }

  Widget _buildModeToggle() {
    return Container(
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
          _buildModeChip('Filter', 0),
          _buildModeChip('Trace ID', 1),
        ],
      ),
    );
  }

  Widget _buildModeChip(String label, int index) {
    final isActive = _queryMode == index;
    return GestureDetector(
      onTap: () => setState(() => _queryMode = index),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: isActive
              ? AppColors.primaryCyan.withValues(alpha: 0.15)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: isActive
                ? AppColors.primaryCyan.withValues(alpha: 0.3)
                : Colors.transparent,
          ),
        ),
        child: Text(
          label,
          style: GoogleFonts.jetBrainsMono(
            fontSize: 10,
            fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
            color: isActive ? AppColors.primaryCyan : AppColors.textMuted,
          ),
        ),
      ),
    );
  }

  Widget _buildSyntaxHelp() {
    if (_queryMode != 0) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 0, 12, 4),
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.primaryCyan.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: AppColors.primaryCyan.withValues(alpha: 0.1),
        ),
      ),
      child: Row(
        children: [
          Icon(Icons.info_outline_rounded,
              size: 12,
              color: AppColors.textMuted.withValues(alpha: 0.7)),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              'Syntax: +span:name:<value>  RootSpan:<path>  '
              'MinDuration:<dur>  HasLabel:<key>:<value>',
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
    );
  }

  Widget _buildTraceList() {
    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: widget.items.length,
      itemBuilder: (context, index) {
        final item = widget.items[index];
        final trace = item.traceData;
        if (trace == null) return const SizedBox.shrink();

        final totalDuration = _calcTotalDuration(trace);

        return DashboardCardWrapper(
          initiallyExpanded: index == 0, // Expand first one by default
          onClose: () => widget.dashboardState.removeItem(item.id),
          dataToCopy: const JsonEncoder.withIndent('  ').convert(item.rawData),
          header: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: AppColors.primaryCyan.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Icon(
                  Icons.timeline_rounded,
                  size: 14,
                  color: AppColors.primaryCyan,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      trace.traceId.length > 16
                          ? '${trace.traceId.substring(0, 16)}...'
                          : trace.traceId,
                      style: GoogleFonts.jetBrainsMono(
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Row(
                      children: [
                        Text(
                          '${trace.spans.length} spans  |  ${totalDuration}ms  |  ${item.toolName}',
                          style: const TextStyle(
                            fontSize: 11,
                            color: AppColors.textMuted,
                          ),
                        ),
                        const SizedBox(width: 6),
                        SourceBadge(source: item.source),
                      ],
                    ),
                  ],
                ),
              ),
              _buildCloudTraceButton(trace.traceId),
            ],
          ),
          child: Container(
            padding: const EdgeInsets.fromLTRB(8, 0, 8, 8),
            child: SyncfusionTraceWaterfall(trace: trace),
          ),
        );
      },
    );
  }

  Widget _buildCloudTraceButton(String traceId) {
    return Tooltip(
      message: 'Open in Cloud Trace',
      child: InkWell(
        borderRadius: BorderRadius.circular(4),
        onTap: () async {
          final projectId =
              ProjectService.instance.selectedProject.value?.projectId;
          if (projectId == null) return;
          final url = Uri.parse(
            'https://console.cloud.google.com/traces/list'
            '?tid=$traceId&project=$projectId',
          );
          if (await canLaunchUrl(url)) {
            await launchUrl(url, mode: LaunchMode.externalApplication);
          }
        },
        child: Padding(
          padding: const EdgeInsets.all(4),
          child: Icon(
            Icons.open_in_new_rounded,
            size: 14,
            color: AppColors.primaryCyan.withValues(alpha: 0.7),
          ),
        ),
      ),
    );
  }

  Future<void> _openDocs() async {
    final url = Uri.parse(
      'https://cloud.google.com/trace/docs/trace-filters',
    );
    if (await canLaunchUrl(url)) {
      await launchUrl(url, mode: LaunchMode.externalApplication);
    }
  }

  String _calcTotalDuration(dynamic trace) {
    if (trace.spans.isEmpty) return '0';
    try {
      DateTime? earliest;
      DateTime? latest;
      for (final span in trace.spans) {
        if (earliest == null || span.startTime.isBefore(earliest)) {
          earliest = span.startTime;
        }
        if (latest == null || span.endTime.isAfter(latest)) {
          latest = span.endTime;
        }
      }
      if (earliest != null && latest != null) {
        return latest.difference(earliest).inMilliseconds.toString();
      }
    } catch (_) {}
    return '?';
  }
}
