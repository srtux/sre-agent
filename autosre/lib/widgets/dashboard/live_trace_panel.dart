import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../services/dashboard_state.dart';
import '../../services/explorer_query_service.dart';
import '../../services/project_service.dart';
import '../../theme/app_theme.dart';
import '../common/error_banner.dart';
import '../common/explorer_empty_state.dart';
import '../common/shimmer_loading.dart';
import '../common/source_badge.dart';
import '../trace_waterfall.dart';
import 'manual_query_bar.dart';
import 'dashboard_card_wrapper.dart';
import 'query_helpers.dart';

/// Dashboard panel that displays all collected trace results.
///
/// Shows traces in a scrollable list with expandable waterfall views.
/// Each trace shows a summary header with span count and duration,
/// and can be expanded to reveal the full Syncfusion waterfall visualization.
///
/// Supports two query modes:
/// - **Trace ID**: Direct lookup by trace ID
/// - **Cloud Trace Filter**: Cloud Trace Query language filter expressions
/// - **Natural Language**: Describe what you want to find in plain English
class LiveTracePanel extends StatefulWidget {
  final List<DashboardItem> items;
  final DashboardState dashboardState;
  final Function(String)? onPromptRequest;
  const LiveTracePanel({
    super.key,
    required this.items,
    required this.dashboardState,
    this.onPromptRequest,
  });

  @override
  State<LiveTracePanel> createState() => _LiveTracePanelState();
}

class _LiveTracePanelState extends State<LiveTracePanel> {
  bool _helpDismissed = false;
  bool _helpDismissedLoaded = false;

  @override
  void initState() {
    super.initState();
    _loadHelpDismissed();

    // Auto-load slow traces when panel first appears with no data
    // and no load is already in progress.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (widget.items.isEmpty &&
          mounted &&
          !widget.dashboardState.isLoading(DashboardDataType.traces)) {
        _loadSlowTraces();
      }
    });
  }

  Future<void> _loadHelpDismissed() async {
    final prefs = await SharedPreferences.getInstance();
    if (mounted) {
      setState(() {
        _helpDismissed = prefs.getBool('traces_help_dismissed') ?? false;
        _helpDismissedLoaded = true;
      });
    }
  }

  Future<void> _dismissHelp() async {
    setState(() => _helpDismissed = true);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('traces_help_dismissed', true);
  }

  Future<void> _loadSlowTraces() async {
    if (!mounted) return;
    try {
      final explorer = context.read<ExplorerQueryService>();
      final projectId = context.read<ProjectService>().selectedProjectId;
      if (projectId == null) return;
      await explorer.loadSlowTraces(projectId: projectId);
    } catch (e) {
      debugPrint('LiveTracePanel auto-load error: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    final isLoading = widget.dashboardState.isLoading(DashboardDataType.traces);
    final error = widget.dashboardState.errorFor(DashboardDataType.traces);

    return Column(
      children: [
        // Query language header
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
          child: Column(
            children: [
              // Query bar changes based on mode
              ManualQueryBar(
                hintText: '+span:name:my_service  OR  trace=abc123def456789...',
                panelType: 'traces',
                dashboardState: widget.dashboardState,
                onRefresh: () {
                  final filter = widget.dashboardState.getLastQueryFilter(
                    DashboardDataType.traces,
                  );
                  if (filter != null && filter.isNotEmpty) {
                    final explorer = context.read<ExplorerQueryService>();
                    if (filter.startsWith('trace=')) {
                      explorer.queryTrace(traceId: filter.substring(6).trim());
                    } else {
                      explorer.queryTraceFilter(filter: filter);
                    }
                  }
                },
                languageLabel: 'TRACE',
                languageLabelColor: AppColors.primaryCyan,
                initialValue: widget.dashboardState.getLastQueryFilter(
                  DashboardDataType.traces,
                ),
                isLoading: isLoading,
                snippets: traceSnippets,
                templates: traceTemplates,
                enableNaturalLanguage: true,
                naturalLanguageHint:
                    'Show me the slowest API calls in the last hour...',
                naturalLanguageExamples: traceNaturalLanguageExamples,
                onSubmitWithMode: (query, isNl) {
                  widget.dashboardState.setLastQueryFilter(
                    DashboardDataType.traces,
                    query,
                  );
                  final explorer = context.read<ExplorerQueryService>();
                  if (isNl) {
                    if (widget.onPromptRequest != null) {
                      widget.onPromptRequest!(query);
                    }
                  } else {
                    if (query.startsWith('trace=')) {
                      explorer.queryTrace(traceId: query.substring(6).trim());
                    } else {
                      explorer.queryTraceFilter(filter: query);
                    }
                  }
                },
                onSubmit: (filter) {
                  widget.dashboardState.setLastQueryFilter(
                    DashboardDataType.traces,
                    filter,
                  );
                  final explorer = context.read<ExplorerQueryService>();
                  if (filter.startsWith('trace=')) {
                    explorer.queryTrace(traceId: filter.substring(6).trim());
                  } else {
                    explorer.queryTraceFilter(filter: filter);
                  }
                },
              ),
            ],
          ),
        ),
        // Syntax reference
        if (_helpDismissedLoaded && !_helpDismissed) _buildSyntaxHelp(),
        if (error != null)
          ErrorBanner(
            message: error,
            onDismiss: () =>
                widget.dashboardState.setError(DashboardDataType.traces, null),
          ),
        // Content
        Expanded(
          child: isLoading && widget.items.isEmpty
              ? const ShimmerLoading(showChart: true)
              : widget.items.isEmpty
              ? const ExplorerEmptyState(
                  icon: Icons.timeline_rounded,
                  title: 'No Traces Yet',
                  description:
                      'Enter a Cloud Trace filter expression or trace=ID to search\nfor traces, or switch to natural language mode.',
                  queryHint: 'e.g. trace=abc123def456789...',
                )
              : _buildTraceList(),
        ),
      ],
    );
  }

  Widget _buildSyntaxHelp() {
    return AnimatedSize(
      duration: const Duration(milliseconds: 200),
      curve: Curves.easeOut,
      child: Container(
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
            Icon(
              Icons.info_outline_rounded,
              size: 12,
              color: AppColors.textMuted.withValues(alpha: 0.7),
            ),
            const SizedBox(width: 6),
            Expanded(
              child: Text(
                'Tab to autocomplete  |  '
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

  Widget _buildTraceList() {
    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: widget.items.length,
      itemBuilder: (context, index) {
        final item = widget.items[widget.items.length - 1 - index];
        final trace = item.traceData;
        if (trace == null) return const SizedBox.shrink();

        final totalDuration = _calcTotalDuration(trace);

        return DashboardCardWrapper(
          initiallyExpanded: index == 0,
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
          child: SizedBox(
            height: MediaQuery.of(context).size.height * 0.85,
            child: Container(
              padding: const EdgeInsets.fromLTRB(8, 0, 8, 8),
              child: TraceWaterfall(trace: trace),
            ),
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
