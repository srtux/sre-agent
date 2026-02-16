import 'package:flutter/material.dart';
import '../models/adk_schema.dart';
import '../theme/app_theme.dart';
import '../theme/design_tokens.dart';
import 'log_entry_card.dart';

/// A Datadog-style log entries viewer with expandable JSON payloads.
class LogEntriesViewer extends StatefulWidget {
  final LogEntriesData data;

  const LogEntriesViewer({super.key, required this.data});

  @override
  State<LogEntriesViewer> createState() => _LogEntriesViewerState();
}

class _LogEntriesViewerState extends State<LogEntriesViewer>
    with SingleTickerProviderStateMixin {
  late AnimationController _animController;
  late Animation<double> _animation;
  String _searchQuery = '';
  String? _filterSeverity;
  final TextEditingController _searchController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _animController = AnimationController(
      duration: const Duration(milliseconds: 600),
      vsync: this,
    );
    _animation = CurvedAnimation(
      parent: _animController,
      curve: Curves.easeOutCubic,
    );
    _animController.forward();
  }

  @override
  void dispose() {
    _animController.dispose();
    _searchController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  List<LogEntry> get _filteredEntries {
    return widget.data.entries.where((entry) {
      // Filter by severity
      if (_filterSeverity != null && entry.severity != _filterSeverity) {
        return false;
      }
      // Filter by search query
      if (_searchQuery.isNotEmpty) {
        final query = _searchQuery.toLowerCase();
        final payloadStr = entry.payload?.toString().toLowerCase() ?? '';
        final resourceStr = entry.resourceLabels.toString().toLowerCase();
        if (!payloadStr.contains(query) && !resourceStr.contains(query)) {
          return false;
        }
      }
      return true;
    }).toList();
  }

  Map<String, int> get _severityCounts {
    final counts = <String, int>{};
    for (final entry in widget.data.entries) {
      counts[entry.severity] = (counts[entry.severity] ?? 0) + 1;
    }
    return counts;
  }

  Color _getSeverityColor(String severity) {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
      case 'EMERGENCY':
      case 'ALERT':
        return SeverityColors.critical;
      case 'ERROR':
        return AppColors.error;
      case 'WARNING':
        return AppColors.warning;
      case 'INFO':
      case 'NOTICE':
        return AppColors.info;
      case 'DEBUG':
        return AppColors.textMuted;
      default:
        return AppColors.textSecondary;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildHeader(),
        const SizedBox(height: 10),
        _buildSearchBar(),
        const SizedBox(height: 8),
        _buildSeverityFilterChips(),
        const SizedBox(height: 8),
        Expanded(
          child: AnimatedBuilder(
            animation: _animation,
            builder: (context, child) {
              final entries = _filteredEntries;
              if (entries.isEmpty) {
                return _buildEmptyState();
              }
              return ListView.builder(
                controller: _scrollController,
                padding: const EdgeInsets.symmetric(horizontal: 12),
                itemCount: entries.length,
                itemBuilder: (context, index) {
                  final staggerDelay = index / widget.data.entries.length;
                  final animValue =
                      ((_animation.value - staggerDelay * 0.3) / 0.7).clamp(
                        0.0,
                        1.0,
                      );
                  return LogEntryCard(
                    entry: entries[index],
                    animationValue: animValue,
                  );
                },
              );
            },
          ),
        ),
      ],
    );
  }

  Widget _buildHeader() {
    final errorCount = _severityCounts['ERROR'] ?? 0;
    final warningCount = _severityCounts['WARNING'] ?? 0;
    final criticalCount = _severityCounts['CRITICAL'] ?? 0;

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppColors.primaryBlue.withValues(alpha: 0.2),
                  AppColors.primaryCyan.withValues(alpha: 0.15),
                ],
              ),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(
              Icons.article_outlined,
              size: 18,
              color: AppColors.primaryBlue,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Text(
                      'Log Entries',
                      style: TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 6,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: AppColors.primaryTeal.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        '${widget.data.entries.length} entries',
                        style: const TextStyle(
                          fontSize: 10,
                          color: AppColors.primaryTeal,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
                if (widget.data.filter != null) ...[
                  const SizedBox(height: 2),
                  Text(
                    widget.data.filter!,
                    style: const TextStyle(
                      fontSize: 10,
                      color: AppColors.textMuted,
                      fontFamily: 'monospace',
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ],
            ),
          ),
          if (criticalCount > 0) ...[
            _buildStatChip(
              '$criticalCount critical',
              Icons.crisis_alert,
              SeverityColors.critical,
            ),
            const SizedBox(width: 6),
          ],
          if (errorCount > 0) ...[
            _buildStatChip(
              '$errorCount errors',
              Icons.error_outline,
              AppColors.error,
            ),
            const SizedBox(width: 6),
          ],
          if (warningCount > 0)
            _buildStatChip(
              '$warningCount warnings',
              Icons.warning_amber,
              AppColors.warning,
            ),
        ],
      ),
    );
  }

  Widget _buildStatChip(String text, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.25)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: color),
          const SizedBox(width: 4),
          Text(
            text,
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w500,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSearchBar() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Container(
        height: 40,
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: AppColors.surfaceBorder),
        ),
        child: Row(
          children: [
            const SizedBox(width: 12),
            const Icon(Icons.search, size: 18, color: AppColors.textMuted),
            const SizedBox(width: 8),
            Expanded(
              child: TextField(
                controller: _searchController,
                onChanged: (value) => setState(() => _searchQuery = value),
                style: const TextStyle(
                  fontSize: 13,
                  color: AppColors.textPrimary,
                ),
                decoration: const InputDecoration(
                  hintText: 'Search logs...',
                  hintStyle: TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 13,
                  ),
                  border: InputBorder.none,
                  contentPadding: EdgeInsets.zero,
                  isDense: true,
                ),
              ),
            ),
            if (_searchQuery.isNotEmpty)
              IconButton(
                icon: const Icon(
                  Icons.close,
                  size: 16,
                  color: AppColors.textMuted,
                ),
                onPressed: () {
                  _searchController.clear();
                  setState(() => _searchQuery = '');
                },
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
              ),
            const SizedBox(width: 12),
          ],
        ),
      ),
    );
  }

  Widget _buildSeverityFilterChips() {
    final severities = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG'];
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            const Text(
              'Filter:',
              style: TextStyle(fontSize: 10, color: AppColors.textMuted),
            ),
            const SizedBox(width: 8),
            _buildFilterChip('All', null, widget.data.entries.length),
            ...severities.map(
              (s) => Padding(
                padding: const EdgeInsets.only(left: 6),
                child: _buildFilterChip(s, s, _severityCounts[s] ?? 0),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildFilterChip(String label, String? severity, int count) {
    final isSelected = _filterSeverity == severity;
    final color = severity != null
        ? _getSeverityColor(severity)
        : AppColors.primaryTeal;

    return GestureDetector(
      onTap: () => setState(() => _filterSeverity = severity),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: isSelected ? color.withValues(alpha: 0.2) : Colors.transparent,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(
            color: isSelected ? color : AppColors.surfaceBorder,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              label,
              style: TextStyle(
                fontSize: 10,
                color: isSelected ? color : AppColors.textMuted,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
              ),
            ),
            const SizedBox(width: 4),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
              decoration: BoxDecoration(
                color: (isSelected ? color : AppColors.textMuted).withValues(
                  alpha: 0.2,
                ),
                borderRadius: BorderRadius.circular(3),
              ),
              child: Text(
                count.toString(),
                style: TextStyle(
                  fontSize: 9,
                  color: isSelected ? color : AppColors.textMuted,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.textMuted.withValues(alpha: 0.1),
              shape: BoxShape.circle,
            ),
            child: const Icon(
              Icons.search_off_outlined,
              size: 40,
              color: AppColors.textMuted,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            _searchQuery.isNotEmpty || _filterSeverity != null
                ? 'No logs match your filters'
                : 'No log entries',
            style: const TextStyle(color: AppColors.textMuted, fontSize: 14),
          ),
        ],
      ),
    );
  }
}
