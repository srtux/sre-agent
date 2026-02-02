import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../models/adk_schema.dart';
import '../../services/dashboard_state.dart';
import '../../theme/app_theme.dart';
import '../../utils/ansi_parser.dart';

/// Dashboard panel for exploring all collected log data.
///
/// Provides a mini logs explorer with:
/// - Severity filter chips with counts
/// - Search across all collected log entries
/// - Expandable JSON payload viewer
/// - Aggregated view across multiple tool calls
class LiveLogsExplorer extends StatefulWidget {
  final List<DashboardItem> items;
  const LiveLogsExplorer({super.key, required this.items});

  @override
  State<LiveLogsExplorer> createState() => _LiveLogsExplorerState();
}

class _LiveLogsExplorerState extends State<LiveLogsExplorer> {
  String _searchQuery = '';
  String? _severityFilter;
  int? _expandedEntry;

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

  List<LogEntry> get _filteredEntries {
    var entries = _allEntries;
    if (_severityFilter != null) {
      entries =
          entries.where((e) => e.severity == _severityFilter).toList();
    }
    if (_searchQuery.isNotEmpty) {
      final q = _searchQuery.toLowerCase();
      entries = entries
          .where((e) => e.payloadPreview.toLowerCase().contains(q))
          .toList();
    }
    return entries;
  }

  Map<String, int> get _severityCounts {
    final counts = <String, int>{};
    for (final entry in _allEntries) {
      counts[entry.severity] = (counts[entry.severity] ?? 0) + 1;
    }
    return counts;
  }

  @override
  Widget build(BuildContext context) {
    final hasPatterns =
        widget.items.any((i) => i.logPatterns != null && i.logPatterns!.isNotEmpty);

    return Column(
      children: [
        // Search and filters
        _buildFilterBar(),
        // Pattern summary (if any)
        if (hasPatterns) _buildPatternSummary(),
        // Log entries list
        Expanded(child: _buildLogList()),
      ],
    );
  }

  Widget _buildFilterBar() {
    final counts = _severityCounts;
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppColors.backgroundCard.withValues(alpha: 0.5),
        border: Border(
          bottom: BorderSide(
            color: AppColors.surfaceBorder.withValues(alpha: 0.3),
          ),
        ),
      ),
      child: Column(
        children: [
          // Search
          SizedBox(
            height: 34,
            child: TextField(
              style: const TextStyle(fontSize: 12, color: AppColors.textPrimary),
              decoration: InputDecoration(
                hintText: 'Search logs...',
                hintStyle:
                    const TextStyle(fontSize: 12, color: AppColors.textMuted),
                prefixIcon:
                    const Icon(Icons.search, size: 16, color: AppColors.textMuted),
                filled: true,
                fillColor: Colors.white.withValues(alpha: 0.05),
                contentPadding: const EdgeInsets.symmetric(horizontal: 12),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: BorderSide.none,
                ),
              ),
              onChanged: (v) => setState(() => _searchQuery = v),
            ),
          ),
          const SizedBox(height: 8),
          // Severity chips
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                _buildSeverityChip('ALL', null, _allEntries.length),
                ...counts.entries.map((e) =>
                    _buildSeverityChip(e.key, e.key, e.value)),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSeverityChip(String label, String? value, int count) {
    final isActive = _severityFilter == value;
    final color = _severityColor(label);
    return Padding(
      padding: const EdgeInsets.only(right: 6),
      child: FilterChip(
        label: Text(
          '$label ($count)',
          style: TextStyle(
            fontSize: 10,
            fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
            color: isActive ? color : AppColors.textMuted,
          ),
        ),
        selected: isActive,
        onSelected: (_) => setState(() => _severityFilter = value),
        backgroundColor: Colors.white.withValues(alpha: 0.05),
        selectedColor: color.withValues(alpha: 0.15),
        side: BorderSide(
          color: isActive ? color.withValues(alpha: 0.4) : Colors.transparent,
        ),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
        padding: const EdgeInsets.symmetric(horizontal: 4),
        visualDensity: VisualDensity.compact,
      ),
    );
  }

  Widget _buildPatternSummary() {
    final patterns = <LogPattern>[];
    for (final item in widget.items) {
      if (item.logPatterns != null) patterns.addAll(item.logPatterns!);
    }
    if (patterns.isEmpty) return const SizedBox.shrink();

    // Show top 3 patterns
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
          ...top.map((p) => Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 2),
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
              )),
        ],
      ),
    );
  }

  Widget _buildLogList() {
    final entries = _filteredEntries;
    if (entries.isEmpty) {
      return const Center(
        child: Text(
          'No matching log entries',
          style: TextStyle(fontSize: 13, color: AppColors.textMuted),
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(8),
      itemCount: entries.length,
      itemBuilder: (context, index) {
        final entry = entries[index];
        final isExpanded = _expandedEntry == index;
        final sevColor = _severityColor(entry.severity);

        return Padding(
          padding: const EdgeInsets.only(bottom: 2),
          child: InkWell(
            onTap: entry.isJsonPayload
                ? () => setState(() {
                      _expandedEntry = isExpanded ? null : index;
                    })
                : null,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
              decoration: BoxDecoration(
                color: isExpanded
                    ? Colors.white.withValues(alpha: 0.03)
                    : Colors.transparent,
                borderRadius: BorderRadius.circular(4),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Severity badge
                      Container(
                        width: 50,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 4, vertical: 1),
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
                          '${entry.timestamp.hour.toString().padLeft(2, '0')}:${entry.timestamp.minute.toString().padLeft(2, '0')}:${entry.timestamp.second.toString().padLeft(2, '0')}',
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
                  // Expanded payload
                  if (isExpanded && entry.isJsonPayload)
                    Container(
                      margin: const EdgeInsets.only(top: 6, left: 56),
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: const Color(0xFF0F172A),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(
                          color: Colors.white.withValues(alpha: 0.08),
                        ),
                      ),
                      child: SelectableText(
                        entry.payload.toString(),
                        style: GoogleFonts.jetBrainsMono(
                          fontSize: 10,
                          color: AppColors.primaryCyan,
                          height: 1.4,
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Color _severityColor(String severity) {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
      case 'EMERGENCY':
      case 'ALERT':
        return const Color(0xFFFF1744);
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
