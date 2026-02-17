import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../models/adk_schema.dart';
import '../../services/dashboard_state.dart';
import '../../services/explorer_query_service.dart';
import '../../services/project_service.dart';
import '../../theme/app_theme.dart';
import '../../theme/design_tokens.dart' as tokens;
import '../../utils/ansi_parser.dart';
import '../common/error_banner.dart';
import '../common/explorer_empty_state.dart';
import '../common/shimmer_loading.dart';
import 'json_payload_viewer.dart';
import 'log_field_facets.dart';
import 'log_timeline_histogram.dart';
import 'manual_query_bar.dart';
import 'query_helpers.dart';

/// Key used in SharedPreferences to persist help banner dismissal.
const _helpDismissedKey = 'logs_help_dismissed';

/// Dashboard panel for exploring all collected log data.
///
/// Provides a professional, facet-driven diagnostic tool aligned with
/// Google Cloud Logging standards:
/// - Cloud Logging query language support with autocomplete & templates
/// - Natural language mode for plain-English queries
/// - Left-pane faceted navigation (Severity, Resource Type, Log Name, Project)
/// - Timeline histogram showing log frequency by severity
/// - Dismissible help banner with persistent state
/// - Expandable JSON payload detail view with Copy JSON
/// - Aggregated view across multiple tool calls
class LiveLogsExplorer extends StatefulWidget {
  final List<DashboardItem> items;
  final DashboardState dashboardState;
  final Function(String)? onPromptRequest;
  const LiveLogsExplorer({
    super.key,
    required this.items,
    required this.dashboardState,
    this.onPromptRequest,
  });

  @override
  State<LiveLogsExplorer> createState() => _LiveLogsExplorerState();
}

class _LiveLogsExplorerState extends State<LiveLogsExplorer> {
  int? _expandedEntry;
  bool _helpDismissed = false;
  bool _helpDismissedLoaded = false;

  /// Cached lists for quick filters
  List<String> _logNames = [];

  /// Active facet filters: field name -> set of selected values.
  final Map<String, Set<String>> _facetFilters = {};

  final ScrollController _scrollController = ScrollController();
  bool _isLoadingMore = false;

  @override
  void initState() {
    super.initState();
    _loadHelpDismissed();

    _scrollController.addListener(_onScroll);

    WidgetsBinding.instance.addPostFrameCallback((_) {
      _fetchMetadata();
      // Auto-load recent logs when panel first appears with no data
      // and no load is already in progress (avoids duplicate with
      // conversation_page._onProjectChanged which also triggers a load).
      if (widget.items.isEmpty &&
          mounted &&
          !widget.dashboardState.isLoading(DashboardDataType.logs)) {
        _loadDefaultLogs();
      }
    });
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  String? get _latestPageToken {
    // Find the most recent manual logs item with a page token
    for (final item in widget.items.reversed) {
      if (item.type == DashboardDataType.logs &&
          item.source == DataSource.manual &&
          item.logData?.nextPageToken != null) {
        return item.logData!.nextPageToken;
      }
    }
    return null;
  }

  Future<void> _onScroll() async {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 400) {
      await _loadMoreLogs();
    }
  }

  Future<void> _loadMoreLogs() async {
    if (_isLoadingMore) return;

    final pageToken = _latestPageToken;
    if (pageToken == null) return;

    final filter = widget.dashboardState.getLastQueryFilter(
      DashboardDataType.logs,
    );
    if (filter == null || filter.isEmpty) return;

    setState(() => _isLoadingMore = true);

    try {
      final explorer = context.read<ExplorerQueryService>();
      await explorer.queryLogs(filter: filter, pageToken: pageToken);
    } finally {
      if (mounted) {
        setState(() => _isLoadingMore = false);
      }
    }
  }

  Future<void> _fetchMetadata() async {
    final explorer = context.read<ExplorerQueryService>();
    final logs = await explorer.getLogNames();
    if (mounted) {
      setState(() {
        _logNames = logs;
      });
    }
  }

  Future<void> _loadDefaultLogs() async {
    if (!mounted) return;
    try {
      final explorer = context.read<ExplorerQueryService>();
      final projectId = context.read<ProjectService>().selectedProjectId;
      if (projectId == null) return;
      await explorer.loadDefaultLogs(projectId: projectId);
    } catch (e) {
      debugPrint('LiveLogsExplorer auto-load error: $e');
    }
  }

  Future<void> _loadHelpDismissed() async {
    final prefs = await SharedPreferences.getInstance();
    if (mounted) {
      setState(() {
        _helpDismissed = prefs.getBool(_helpDismissedKey) ?? false;
        _helpDismissedLoaded = true;
      });
    }
  }

  Future<void> _dismissHelp() async {
    setState(() => _helpDismissed = true);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_helpDismissedKey, true);
  }

  /// Aggregate all log entries across all tool calls.
  List<LogEntry> get _allEntries {
    final entries = <LogEntry>[];
    for (final item in widget.items) {
      if (item.logData != null) {
        entries.addAll(item.logData!.entries);
      }
    }
    // Sort by timestamp descending (newest first)
    entries.sort((a, b) => b.timestamp.compareTo(a.timestamp));
    return entries;
  }

  /// Entries filtered by active facet filters.
  List<LogEntry> get _filteredEntries {
    var entries = _allEntries;

    // Apply facet filters
    for (final facetEntry in _facetFilters.entries) {
      final field = facetEntry.key;
      final values = facetEntry.value;
      if (values.isEmpty) continue;

      entries = entries.where((e) {
        switch (field) {
          case 'Severity':
            return values.contains(e.severity);
          case 'Resource Type':
            return values.contains(e.resourceType);
          case 'Log Name':
            final logName = e.resourceLabels['log_name'] ?? 'unknown';
            return values.contains(logName);
          case 'Project ID':
            final projectId = e.resourceLabels['project_id'];
            return projectId != null && values.contains(projectId);
          default:
            return true;
        }
      }).toList();
    }

    return entries;
  }

  void _onFacetFilterToggle(String field, String value) {
    setState(() {
      final values = _facetFilters.putIfAbsent(field, () => {});
      if (values.contains(value)) {
        values.remove(value);
        if (values.isEmpty) _facetFilters.remove(field);
      } else {
        values.add(value);
      }
      // Reset expanded entry when filters change
      _expandedEntry = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final isLoading = widget.dashboardState.isLoading(DashboardDataType.logs);
    final error = widget.dashboardState.errorFor(DashboardDataType.logs);
    final hasPatterns = widget.items.any(
      (i) => i.logPatterns != null && i.logPatterns!.isNotEmpty,
    );
    final allEntries = _allEntries;
    final hasData = allEntries.isNotEmpty || hasPatterns;

    return Column(
      children: [
        // Query bar (primary filter - all filtering goes through here)
        Padding(
          padding: const EdgeInsets.fromLTRB(
            tokens.Spacing.md,
            tokens.Spacing.sm,
            tokens.Spacing.md,
            tokens.Spacing.xs,
          ),
          child: ManualQueryBar(
            hintText: 'severity>=ERROR AND resource.type="gce_instance"',
            dashboardState: widget.dashboardState,
            onRefresh: () {
              final filter = widget.dashboardState.getLastQueryFilter(
                DashboardDataType.logs,
              );
              if (filter != null && filter.isNotEmpty) {
                final explorer = context.read<ExplorerQueryService>();
                explorer.queryLogs(filter: filter);
              }
            },
            languageLabel: 'LOG FILTER',
            languageLabelColor: AppColors.success,
            initialValue: widget.dashboardState.getLastQueryFilter(
              DashboardDataType.logs,
            ),
            isLoading: isLoading,
            snippets: loggingSnippets,
            templates: loggingTemplates,
            enableNaturalLanguage: true,
            naturalLanguageHint:
                'Show me all errors from the payment service...',
            naturalLanguageExamples: loggingNaturalLanguageExamples,
            onSubmitWithMode: (query, isNl) {
              widget.dashboardState.setLastQueryFilter(
                DashboardDataType.logs,
                query,
              );
              final explorer = context.read<ExplorerQueryService>();
              if (isNl) {
                widget.onPromptRequest?.call(query);
              } else {
                explorer.queryLogs(filter: query);
              }
            },
            onSubmit: (filter) {
              widget.dashboardState.setLastQueryFilter(
                DashboardDataType.logs,
                filter,
              );
              final explorer = context.read<ExplorerQueryService>();
              explorer.queryLogs(filter: filter);
            },
          ),
        ),

        // Metadata dropdown selectors
        _buildMetadataSelectors(),

        // Collapsible help banner
        if (_helpDismissedLoaded && !_helpDismissed) _buildDismissibleHelp(),

        // Error banner
        if (error != null)
          ErrorBanner(
            message: error,
            onDismiss: () =>
                widget.dashboardState.setError(DashboardDataType.logs, null),
          ),

        // Content area
        if (isLoading && !hasData)
          const Expanded(child: ShimmerLoading())
        else if (!hasData)
          const Expanded(
            child: ExplorerEmptyState(
              icon: Icons.article_outlined,
              title: 'Logs Explorer',
              description:
                  'Query Cloud Logging entries using the query language,\n'
                  'or switch to natural language mode.\n'
                  'Try the lightbulb button for pre-built templates.',
              queryHint: 'severity>=ERROR AND resource.type="gce_instance"',
            ),
          )
        else ...[
          // Timeline histogram
          LogTimelineHistogram(
            entries: allEntries,
            timeRange: widget.dashboardState.timeRange,
          ),

          // Pattern summary (if available)
          if (hasPatterns) _buildPatternSummary(),

          // Main content: Facets sidebar + Log list
          Expanded(
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Left-pane faceted navigation
                LogFieldFacets(
                  entries: allEntries,
                  activeFilters: _facetFilters,
                  onFilterToggle: _onFacetFilterToggle,
                ),

                // Log results list
                Expanded(child: _buildLogList()),
              ],
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildMetadataSelectors() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        tokens.Spacing.md,
        0,
        tokens.Spacing.md,
        tokens.Spacing.sm,
      ),
      child: Row(
        children: [
          _buildDropdown('All log names', _logNames, (val) {
            if (val != null) _appendFilter('logName="$val"');
          }),
          const SizedBox(width: tokens.Spacing.sm),
          _buildDropdown(
            'All severities',
            const [
              'DEFAULT',
              'DEBUG',
              'INFO',
              'NOTICE',
              'WARNING',
              'ERROR',
              'CRITICAL',
              'ALERT',
              'EMERGENCY',
            ],
            (val) {
              if (val != null) _appendFilter('severity="$val"');
            },
          ),
        ],
      ),
    );
  }

  Widget _buildDropdown(
    String hint,
    List<String> items,
    ValueChanged<String?> onChanged,
  ) {
    return Container(
      height: 28,
      padding: const EdgeInsets.symmetric(horizontal: 8),
      decoration: BoxDecoration(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(4),
      ),
      child: DropdownButtonHideUnderline(
        child: DropdownButton<String>(
          isDense: true,
          hint: Text(
            hint,
            style: const TextStyle(
              fontSize: 12,
              color: AppColors.textPrimary,
              fontWeight: FontWeight.w500,
            ),
          ),
          icon: const Icon(
            Icons.arrow_drop_down,
            size: 18,
            color: AppColors.textPrimary,
          ),
          style: const TextStyle(fontSize: 12, color: AppColors.textPrimary),
          dropdownColor: AppColors.backgroundElevated,
          focusColor: Colors.transparent,
          items: items.map((i) {
            var display = i;
            if (i.contains('/logs/')) {
              final parts = i.split('/logs/');
              if (parts.length > 1) {
                display = Uri.decodeComponent(parts.last);
              }
            }
            return DropdownMenuItem(
              value: i,
              child: SizedBox(
                width: display.length > 30 ? 200 : null,
                child: Text(display, overflow: TextOverflow.ellipsis),
              ),
            );
          }).toList(),
          onChanged: onChanged,
        ),
      ),
    );
  }

  void _appendFilter(String addition) {
    var current =
        widget.dashboardState.getLastQueryFilter(DashboardDataType.logs) ?? '';
    if (current.isEmpty) {
      current = addition;
    } else if (!current.contains(addition)) {
      current = '$current AND $addition';
    }
    widget.dashboardState.setLastQueryFilter(DashboardDataType.logs, current);

    final explorer = context.read<ExplorerQueryService>();
    explorer.queryLogs(filter: current);
  }

  /// Dismissible help banner with 'X' button and persistent state.
  Widget _buildDismissibleHelp() {
    return AnimatedSize(
      duration: tokens.Durations.fast,
      curve: Curves.easeOut,
      child: Container(
        margin: const EdgeInsets.fromLTRB(
          tokens.Spacing.md,
          0,
          tokens.Spacing.md,
          tokens.Spacing.xs,
        ),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        decoration: BoxDecoration(
          color: AppColors.success.withValues(alpha: 0.04),
          borderRadius: tokens.Radii.borderMd,
          border: Border.all(color: AppColors.success.withValues(alpha: 0.1)),
        ),
        child: Row(
          children: [
            Icon(
              Icons.keyboard_rounded,
              size: 11,
              color: AppColors.textMuted.withValues(alpha: 0.6),
            ),
            const SizedBox(width: 6),
            Expanded(
              child: Text(
                'Tab to autocomplete  |  '
                'Click lightbulb for templates  |  '
                'Toggle NL for natural language',
                style: TextStyle(
                  fontSize: 9,
                  color: AppColors.textMuted.withValues(alpha: 0.7),
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

  Widget _buildPatternSummary() {
    final patterns = <LogPattern>[];
    for (final item in widget.items) {
      if (item.logPatterns != null) patterns.addAll(item.logPatterns!);
    }
    if (patterns.isEmpty) return const SizedBox.shrink();

    patterns.sort((a, b) => b.count.compareTo(a.count));
    final top = patterns.take(3).toList();

    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppColors.success.withValues(alpha: 0.05),
        border: Border(
          bottom: BorderSide(
            color: AppColors.surfaceBorder.withValues(alpha: 0.3),
          ),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.pattern, size: 14, color: AppColors.success),
              const SizedBox(width: 6),
              Text(
                'Top Patterns (${patterns.length} total)',
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: AppColors.success,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          ...top.map(
            (p) => Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 6,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.success.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      '${p.count}x',
                      style: const TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                        color: AppColors.success,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      p.template,
                      style: GoogleFonts.jetBrainsMono(
                        fontSize: 10,
                        color: AppColors.textSecondary,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLogList() {
    final entries = _filteredEntries;
    if (entries.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.filter_list_off_rounded,
              size: 32,
              color: AppColors.textMuted.withValues(alpha: 0.4),
            ),
            const SizedBox(height: tokens.Spacing.sm),
            const Text(
              'No matching log entries',
              style: TextStyle(fontSize: 13, color: AppColors.textMuted),
            ),
            if (_facetFilters.isNotEmpty) ...[
              const SizedBox(height: tokens.Spacing.xs),
              TextButton(
                onPressed: () => setState(() {
                  _facetFilters.clear();
                  _expandedEntry = null;
                }),
                child: const Text(
                  'Clear all filters',
                  style: TextStyle(fontSize: 11, color: AppColors.primaryCyan),
                ),
              ),
            ],
          ],
        ),
      );
    }

    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.all(tokens.Spacing.sm),
      itemCount: entries.length + (_isLoadingMore ? 1 : 0),
      itemBuilder: (context, index) {
        if (index == entries.length) {
          return const Padding(
            padding: EdgeInsets.symmetric(vertical: tokens.Spacing.md),
            child: Center(
              child: SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: AppColors.primaryCyan,
                ),
              ),
            ),
          );
        }
        return _buildLogRow(entries[index], index);
      },
    );
  }

  Widget _buildLogRow(LogEntry entry, int index) {
    final isExpanded = _expandedEntry == index;
    final sevColor = _severityColor(entry.severity);

    return Padding(
      padding: const EdgeInsets.only(bottom: 1),
      child: InkWell(
        onTap: () => setState(() {
          _expandedEntry = isExpanded ? null : index;
        }),
        borderRadius: tokens.Radii.borderXs,
        child: AnimatedContainer(
          duration: tokens.Durations.instant,
          padding: const EdgeInsets.symmetric(
            horizontal: tokens.Spacing.sm,
            vertical: 5,
          ),
          decoration: BoxDecoration(
            color: isExpanded
                ? Colors.white.withValues(alpha: 0.03)
                : Colors.transparent,
            borderRadius: tokens.Radii.borderXs,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Log entry header row
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Expand chevron
                  AnimatedRotation(
                    turns: isExpanded ? 0.25 : 0,
                    duration: tokens.Durations.instant,
                    child: Icon(
                      Icons.chevron_right,
                      size: 14,
                      color: AppColors.textMuted.withValues(alpha: 0.5),
                    ),
                  ),
                  const SizedBox(width: 2),

                  // Severity badge
                  Container(
                    width: 50,
                    padding: const EdgeInsets.symmetric(
                      horizontal: 4,
                      vertical: 1,
                    ),
                    decoration: BoxDecoration(
                      color: sevColor.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(3),
                    ),
                    child: Text(
                      entry.severity.length > 5
                          ? entry.severity.substring(0, 5)
                          : entry.severity,
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 9,
                        fontWeight: FontWeight.w600,
                        color: sevColor,
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),

                  // Timestamp
                  SizedBox(
                    width: 70,
                    child: Text(
                      '${entry.timestamp.hour.toString().padLeft(2, '0')}:'
                      '${entry.timestamp.minute.toString().padLeft(2, '0')}:'
                      '${entry.timestamp.second.toString().padLeft(2, '0')}',
                      style: GoogleFonts.jetBrainsMono(
                        fontSize: 10,
                        color: AppColors.textMuted,
                      ),
                    ),
                  ),

                  // Payload preview
                  Expanded(
                    child: RichText(
                      text: AnsiParser.parse(
                        entry.payloadPreview,
                        baseStyle: GoogleFonts.jetBrainsMono(
                          fontSize: 11,
                          color: AppColors.textSecondary,
                        ),
                      ),
                      maxLines: isExpanded ? null : 1,
                      overflow: isExpanded
                          ? TextOverflow.visible
                          : TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),

              // Expanded JSON detail view
              if (isExpanded) _buildExpandedDetail(entry),
            ],
          ),
        ),
      ),
    );
  }

  /// Full JSON detail view shown when a log row is expanded.
  Widget _buildExpandedDetail(LogEntry entry) {
    // Build a comprehensive JSON map of the full LogEntry
    final fullJson = <String, dynamic>{};

    // Payload
    if (entry.isJsonPayload) {
      fullJson['jsonPayload'] = entry.payload;
    } else {
      fullJson['textPayload'] = entry.payload?.toString() ?? '';
    }

    // Resource
    fullJson['resource'] = {
      'type': entry.resourceType,
      'labels': entry.resourceLabels,
    };

    // Metadata
    fullJson['severity'] = entry.severity;
    fullJson['timestamp'] = entry.timestamp.toIso8601String();
    fullJson['insertId'] = entry.insertId;

    // Optional fields
    if (entry.traceId != null) fullJson['trace'] = entry.traceId;
    if (entry.spanId != null) fullJson['spanId'] = entry.spanId;
    if (entry.httpRequest != null) fullJson['httpRequest'] = entry.httpRequest;

    final prettyJson = const JsonEncoder.withIndent('  ').convert(fullJson);

    return Container(
      margin: const EdgeInsets.only(top: 6, left: 16),
      decoration: BoxDecoration(
        color: AppColors.backgroundDark,
        borderRadius: tokens.Radii.borderSm,
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header with resource type badge and copy button
          Container(
            padding: const EdgeInsets.symmetric(
              horizontal: tokens.Spacing.sm,
              vertical: tokens.Spacing.xs,
            ),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.03),
              borderRadius: const BorderRadius.only(
                topLeft: Radius.circular(tokens.Radii.sm),
                topRight: Radius.circular(tokens.Radii.sm),
              ),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 6,
                    vertical: 2,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.primaryCyan.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(
                      color: AppColors.primaryCyan.withValues(alpha: 0.2),
                    ),
                  ),
                  child: Text(
                    entry.resourceType,
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 9,
                      color: AppColors.primaryCyan,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
                if (entry.traceId != null) ...[
                  const SizedBox(width: tokens.Spacing.sm),
                  Icon(
                    Icons.timeline_rounded,
                    size: 11,
                    color: AppColors.textMuted.withValues(alpha: 0.6),
                  ),
                  const SizedBox(width: 2),
                  Text(
                    entry.traceId!.length > 16
                        ? '${entry.traceId!.substring(0, 16)}...'
                        : entry.traceId!,
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 9,
                      color: AppColors.textMuted,
                    ),
                  ),
                ],
                const Spacer(),
                SizedBox(
                  height: 24,
                  child: TextButton.icon(
                    onPressed: () {
                      Clipboard.setData(ClipboardData(text: prettyJson));
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('JSON copied to clipboard'),
                          duration: Duration(seconds: 2),
                        ),
                      );
                    },
                    icon: const Icon(Icons.copy_rounded, size: 12),
                    label: const Text('Copy JSON'),
                    style: TextButton.styleFrom(
                      foregroundColor: AppColors.textMuted,
                      padding: const EdgeInsets.symmetric(horizontal: 8),
                      textStyle: const TextStyle(fontSize: 10),
                      minimumSize: Size.zero,
                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    ),
                  ),
                ),
              ],
            ),
          ),

          // JSON content
          Padding(
            padding: const EdgeInsets.all(tokens.Spacing.sm),
            child: JsonPayloadViewer(
              json: fullJson,
              onValueTap: (path, displayVal) {
                final filterAddition = '$path=$displayVal';
                final currentFilter =
                    widget.dashboardState.getLastQueryFilter(
                      DashboardDataType.logs,
                    ) ??
                    '';
                final newFilter = currentFilter.isEmpty
                    ? filterAddition
                    : '$currentFilter AND $filterAddition';

                widget.dashboardState.setLastQueryFilter(
                  DashboardDataType.logs,
                  newFilter,
                );

                final explorer = context.read<ExplorerQueryService>();
                explorer.queryLogs(filter: newFilter);
              },
            ),
          ),
        ],
      ),
    );
  }

  Color _severityColor(String severity) {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
      case 'EMERGENCY':
      case 'ALERT':
        return tokens.SeverityColors.critical;
      case 'ERROR':
        return AppColors.error;
      case 'WARNING':
        return AppColors.warning;
      case 'INFO':
        return AppColors.info;
      case 'DEBUG':
        return AppColors.textMuted;
      default:
        return AppColors.textSecondary;
    }
  }
}
