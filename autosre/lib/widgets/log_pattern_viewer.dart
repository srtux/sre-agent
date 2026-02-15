import 'package:flutter/material.dart';
import '../models/adk_schema.dart';
import '../theme/app_theme.dart';
import 'log_pattern_detail.dart';
import 'log_pattern_helpers.dart';
import 'log_pattern_row.dart';

class LogPatternViewer extends StatefulWidget {
  final List<LogPattern> patterns;

  const LogPatternViewer({super.key, required this.patterns});

  @override
  State<LogPatternViewer> createState() => _LogPatternViewerState();
}

class _LogPatternViewerState extends State<LogPatternViewer>
    with SingleTickerProviderStateMixin {
  late AnimationController _animController;
  late Animation<double> _animation;
  String _sortBy = 'count';
  bool _sortAsc = false;
  String? _selectedPattern;
  String _searchQuery = '';
  final TextEditingController _searchController = TextEditingController();
  String? _filterSeverity;

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
    super.dispose();
  }

  List<LogPattern> get _filteredAndSortedPatterns {
    var filtered = widget.patterns.where((p) {
      // Filter by search query
      if (_searchQuery.isNotEmpty &&
          !p.template.toLowerCase().contains(_searchQuery.toLowerCase())) {
        return false;
      }
      // Filter by severity
      if (_filterSeverity != null &&
          getDominantSeverity(p) != _filterSeverity) {
        return false;
      }
      return true;
    }).toList();

    filtered.sort((a, b) {
      int comparison;
      switch (_sortBy) {
        case 'count':
          comparison = a.count.compareTo(b.count);
          break;
        case 'severity':
          comparison = getSeverityPriority(
            getDominantSeverity(a),
          ).compareTo(getSeverityPriority(getDominantSeverity(b)));
          break;
        default:
          comparison = a.template.compareTo(b.template);
      }
      return _sortAsc ? comparison : -comparison;
    });
    return filtered;
  }

  @override
  Widget build(BuildContext context) {
    if (widget.patterns.isEmpty) {
      return _buildEmptyState();
    }

    final totalLogs = widget.patterns
        .map((p) => p.count)
        .reduce((a, b) => a + b);
    final errorCount = widget.patterns
        .where((p) => getDominantSeverity(p) == 'ERROR')
        .length;
    final warningCount = widget.patterns
        .where((p) => getDominantSeverity(p) == 'WARNING')
        .length;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildHeader(totalLogs, errorCount, warningCount),
        const SizedBox(height: 10),
        _buildSearchAndFilter(),
        const SizedBox(height: 8),
        _buildSeverityFilterChips(),
        const SizedBox(height: 8),
        _buildTableHeader(),
        Expanded(
          child: AnimatedBuilder(
            animation: _animation,
            builder: (context, child) {
              final patterns = _filteredAndSortedPatterns;
              if (patterns.isEmpty) {
                return const Center(
                  child: Text(
                    'No patterns match your filters',
                    style: TextStyle(color: AppColors.textMuted, fontSize: 13),
                  ),
                );
              }
              return ListView.builder(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                itemCount: patterns.length,
                itemBuilder: (context, index) {
                  return LogPatternRow(
                    pattern: patterns[index],
                    index: index,
                    total: patterns.length,
                    animation: _animation,
                    isSelected:
                        _selectedPattern == patterns[index].template,
                    onTap: () => setState(() {
                      _selectedPattern =
                          _selectedPattern == patterns[index].template
                              ? null
                              : patterns[index].template;
                    }),
                  );
                },
              );
            },
          ),
        ),
        if (_selectedPattern != null)
          LogPatternDetail(
            pattern: _filteredAndSortedPatterns.firstWhere(
              (p) => p.template == _selectedPattern,
              orElse: () => widget.patterns.first,
            ),
            onClose: () => setState(() => _selectedPattern = null),
          ),
      ],
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
              Icons.article_outlined,
              size: 40,
              color: AppColors.textMuted,
            ),
          ),
          const SizedBox(height: 16),
          const Text(
            'No log patterns detected',
            style: TextStyle(color: AppColors.textMuted, fontSize: 14),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader(int totalLogs, int errorCount, int warningCount) {
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
              Icons.analytics,
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
                      'Log Pattern Analysis',
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
                        '${widget.patterns.length} patterns',
                        style: const TextStyle(
                          fontSize: 10,
                          color: AppColors.primaryTeal,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 2),
                Text(
                  '$totalLogs total log entries analyzed',
                  style: const TextStyle(
                    fontSize: 10,
                    color: AppColors.textMuted,
                  ),
                ),
              ],
            ),
          ),
          if (errorCount > 0)
            _buildStatChip(
              '$errorCount errors',
              Icons.error_outline,
              AppColors.error,
            ),
          if (warningCount > 0) ...[
            const SizedBox(width: 6),
            _buildStatChip(
              '$warningCount warnings',
              Icons.warning_amber,
              AppColors.warning,
            ),
          ],
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

  Widget _buildSearchAndFilter() {
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
                  hintText: 'Search patterns...',
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
    final severities = ['ERROR', 'WARNING', 'INFO', 'DEBUG'];
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          const Text(
            'Filter:',
            style: TextStyle(fontSize: 10, color: AppColors.textMuted),
          ),
          const SizedBox(width: 8),
          _buildFilterChip('All', null),
          ...severities.map(
            (s) => Padding(
              padding: const EdgeInsets.only(left: 6),
              child: _buildFilterChip(s, s),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildFilterChip(String label, String? severity) {
    final isSelected = _filterSeverity == severity;
    final color = severity != null
        ? getLogSeverityColor(severity)
        : AppColors.primaryTeal;

    return GestureDetector(
      onTap: () => setState(() => _filterSeverity = severity),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color:
              isSelected ? color.withValues(alpha: 0.2) : Colors.transparent,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(
            color: isSelected ? color : AppColors.surfaceBorder,
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 10,
            color: isSelected ? color : AppColors.textMuted,
            fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
          ),
        ),
      ),
    );
  }

  Widget _buildTableHeader() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.03),
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(10),
          topRight: Radius.circular(10),
        ),
        border: Border.all(color: AppColors.surfaceBorder),
      ),
      child: Row(
        children: [
          _buildHeaderCell('Trend', null, 100),
          _buildHeaderCell('Count', 'count', 100),
          _buildHeaderCell('Severity', 'severity', 140),
          const SizedBox(width: 8),
          Expanded(child: _buildHeaderCell('Pattern', 'template', null)),
          const SizedBox(
            width: 80,
            child: Text(
              'Frequency',
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w600,
                color: AppColors.textMuted,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeaderCell(String label, String? sortKey, double? width) {
    final isActive = sortKey != null && _sortBy == sortKey;

    Widget content = sortKey != null
        ? InkWell(
            onTap: () {
              setState(() {
                if (_sortBy == sortKey) {
                  _sortAsc = !_sortAsc;
                } else {
                  _sortBy = sortKey;
                  _sortAsc = false;
                }
              });
            },
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  label,
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    color: isActive
                        ? AppColors.primaryTeal
                        : AppColors.textMuted,
                  ),
                ),
                const SizedBox(width: 2),
                Icon(
                  isActive
                      ? (_sortAsc
                          ? Icons.arrow_upward
                          : Icons.arrow_downward)
                      : Icons.unfold_more,
                  size: 12,
                  color:
                      isActive ? AppColors.primaryTeal : AppColors.textMuted,
                ),
              ],
            ),
          )
        : Text(
            label,
            style: const TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w600,
              color: AppColors.textMuted,
            ),
          );

    if (width != null) {
      return SizedBox(width: width, child: content);
    }
    return content;
  }
}
