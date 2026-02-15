import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../models/adk_schema.dart';
import '../../theme/app_theme.dart';
import '../../theme/design_tokens.dart' as tokens;

/// A sidebar widget that displays log field facets with counts and filtering.
///
/// Similar to Google Cloud Logging's "Log fields" pane, this widget computes
/// facet counts from a list of [LogEntry] objects and allows toggling filters
/// on individual values.
class LogFieldFacets extends StatefulWidget {
  /// All log entries to compute facets from.
  final List<LogEntry> entries;

  /// Currently active filters (field name → set of selected values).
  final Map<String, Set<String>> activeFilters;

  /// Called when a facet value is clicked (toggle behavior).
  final void Function(String field, String value) onFilterToggle;

  const LogFieldFacets({
    super.key,
    required this.entries,
    required this.activeFilters,
    required this.onFilterToggle,
  });

  @override
  State<LogFieldFacets> createState() => _LogFieldFacetsState();
}

class _LogFieldFacetsState extends State<LogFieldFacets> {
  /// Tracks which sections are collapsed.
  final Map<String, bool> _collapsedSections = {};

  /// Cached facet data: field name → sorted list of (value, count) pairs.
  Map<String, List<MapEntry<String, int>>> _facets = {};

  /// Length of entries list when facets were last computed.
  int _lastEntriesLength = -1;

  static const double _width = 220;
  static const int _logNameLimit = 10;
  static const int _projectIdLimit = 5;

  static const _severityOrder = [
    'CRITICAL',
    'ERROR',
    'WARNING',
    'INFO',
    'DEBUG',
  ];

  @override
  void didUpdateWidget(LogFieldFacets oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.entries.length != _lastEntriesLength ||
        !identical(widget.entries, oldWidget.entries)) {
      _recomputeFacets();
    }
  }

  @override
  void initState() {
    super.initState();
    _recomputeFacets();
  }

  void _recomputeFacets() {
    _facets = _computeFacets();
    _lastEntriesLength = widget.entries.length;
  }

  Map<String, List<MapEntry<String, int>>> _computeFacets() {
    if (widget.entries.isEmpty) return {};

    final severityCounts = <String, int>{};
    final resourceTypeCounts = <String, int>{};
    final logNameCounts = <String, int>{};
    final projectIdCounts = <String, int>{};

    for (final entry in widget.entries) {
      // Severity
      severityCounts[entry.severity] =
          (severityCounts[entry.severity] ?? 0) + 1;

      // Resource type
      resourceTypeCounts[entry.resourceType] =
          (resourceTypeCounts[entry.resourceType] ?? 0) + 1;

      // Log name
      final logName = entry.resourceLabels['log_name'] ?? 'unknown';
      logNameCounts[logName] = (logNameCounts[logName] ?? 0) + 1;

      // Project ID
      final projectId = entry.resourceLabels['project_id'];
      if (projectId != null) {
        projectIdCounts[projectId] = (projectIdCounts[projectId] ?? 0) + 1;
      }
    }

    // Sort severity by predefined order
    final sortedSeverity = <MapEntry<String, int>>[];
    for (final sev in _severityOrder) {
      final count = severityCounts[sev];
      if (count != null) {
        sortedSeverity.add(MapEntry(sev, count));
      }
    }
    // Add any severities not in the predefined order
    for (final entry in severityCounts.entries) {
      if (!_severityOrder.contains(entry.key)) {
        sortedSeverity.add(entry);
      }
    }

    return {
      'Severity': sortedSeverity,
      'Resource Type': _sortedByCount(resourceTypeCounts),
      'Log Name': _sortedByCount(logNameCounts, limit: _logNameLimit),
      'Project ID': _sortedByCount(projectIdCounts, limit: _projectIdLimit),
    };
  }

  /// Returns entries sorted by count descending, limited to [limit] if given.
  List<MapEntry<String, int>> _sortedByCount(
    Map<String, int> counts, {
    int? limit,
  }) {
    final sorted = counts.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    if (limit != null && sorted.length > limit) {
      return sorted.sublist(0, limit);
    }
    return sorted;
  }

  Color _severityDotColor(String severity) {
    switch (severity) {
      case 'CRITICAL':
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
        return AppColors.textMuted;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: _width,
      decoration: BoxDecoration(
        color: AppColors.backgroundCard.withValues(alpha: 0.5),
        border: Border(
          right: BorderSide(
            color: AppColors.surfaceBorder.withValues(alpha: 0.3),
            width: 1,
          ),
        ),
      ),
      child: widget.entries.isEmpty
          ? Center(
              child: Text(
                'No log data',
                style: GoogleFonts.robotoMono(
                  fontSize: 11,
                  color: AppColors.textMuted,
                ),
              ),
            )
          : SingleChildScrollView(
              padding: tokens.Spacing.paddingSm,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: _buildSections(),
              ),
            ),
    );
  }

  List<Widget> _buildSections() {
    final sections = <Widget>[];
    final fieldNames = _facets.keys.toList();

    for (var i = 0; i < fieldNames.length; i++) {
      final fieldName = fieldNames[i];
      final values = _facets[fieldName]!;
      if (values.isEmpty) continue;

      sections.add(
        _FacetSection(
          fieldName: fieldName,
          values: values,
          isCollapsed: _collapsedSections[fieldName] ?? false,
          activeValues: widget.activeFilters[fieldName] ?? const {},
          isSeverity: fieldName == 'Severity',
          severityDotColor: _severityDotColor,
          onToggleCollapse: () {
            setState(() {
              _collapsedSections[fieldName] =
                  !(_collapsedSections[fieldName] ?? false);
            });
          },
          onFilterToggle: (value) => widget.onFilterToggle(fieldName, value),
        ),
      );

      // Divider between sections (not after the last one)
      if (i < fieldNames.length - 1) {
        sections.add(
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Divider(
              height: 1,
              thickness: 1,
              color: AppColors.surfaceBorder.withValues(alpha: 0.2),
            ),
          ),
        );
      }
    }

    return sections;
  }
}

/// A single facet section with a collapsible header and value rows.
class _FacetSection extends StatelessWidget {
  final String fieldName;
  final List<MapEntry<String, int>> values;
  final bool isCollapsed;
  final Set<String> activeValues;
  final bool isSeverity;
  final Color Function(String) severityDotColor;
  final VoidCallback onToggleCollapse;
  final void Function(String value) onFilterToggle;

  const _FacetSection({
    required this.fieldName,
    required this.values,
    required this.isCollapsed,
    required this.activeValues,
    required this.isSeverity,
    required this.severityDotColor,
    required this.onToggleCollapse,
    required this.onFilterToggle,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Section header
        GestureDetector(
          onTap: onToggleCollapse,
          behavior: HitTestBehavior.opaque,
          child: Padding(
            padding: const EdgeInsets.only(bottom: tokens.Spacing.xs),
            child: Row(
              children: [
                AnimatedRotation(
                  turns: isCollapsed ? -0.25 : 0,
                  duration: tokens.Durations.fast,
                  child: const Icon(
                    Icons.expand_more,
                    size: 12,
                    color: AppColors.textMuted,
                  ),
                ),
                const SizedBox(width: tokens.Spacing.xs),
                Expanded(
                  child: Text(
                    fieldName.toUpperCase(),
                    style: GoogleFonts.robotoMono(
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      color: AppColors.textMuted,
                      letterSpacing: 0.5,
                    ),
                  ),
                ),
                Text(
                  '${values.length}',
                  style: GoogleFonts.robotoMono(
                    fontSize: 10,
                    color: AppColors.textMuted,
                  ),
                ),
              ],
            ),
          ),
        ),

        // Collapsible value rows
        AnimatedSize(
          duration: tokens.Durations.normal,
          curve: Curves.easeInOut,
          alignment: Alignment.topCenter,
          child: isCollapsed
              ? const SizedBox.shrink()
              : Column(
                  children: values
                      .map((entry) => _FacetValueRow(
                            value: entry.key,
                            count: entry.value,
                            isActive: activeValues.contains(entry.key),
                            isSeverity: isSeverity,
                            dotColor:
                                isSeverity ? severityDotColor(entry.key) : null,
                            onTap: () => onFilterToggle(entry.key),
                          ))
                      .toList(),
                ),
        ),
      ],
    );
  }
}

/// A single value row within a facet section.
class _FacetValueRow extends StatefulWidget {
  final String value;
  final int count;
  final bool isActive;
  final bool isSeverity;
  final Color? dotColor;
  final VoidCallback onTap;

  const _FacetValueRow({
    required this.value,
    required this.count,
    required this.isActive,
    required this.isSeverity,
    required this.dotColor,
    required this.onTap,
  });

  @override
  State<_FacetValueRow> createState() => _FacetValueRowState();
}

class _FacetValueRowState extends State<_FacetValueRow> {
  bool _hovering = false;

  @override
  Widget build(BuildContext context) {
    final isActive = widget.isActive;

    final Color backgroundColor;
    if (isActive) {
      backgroundColor = AppColors.primaryCyan.withValues(alpha: 0.1);
    } else if (_hovering) {
      backgroundColor = Colors.white.withValues(alpha: 0.05);
    } else {
      backgroundColor = Colors.transparent;
    }

    final textColor =
        isActive ? AppColors.primaryCyan : AppColors.textSecondary;
    final countColor = isActive ? AppColors.primaryCyan : AppColors.textMuted;

    return MouseRegion(
      cursor: SystemMouseCursors.click,
      onEnter: (_) => setState(() => _hovering = true),
      onExit: (_) => setState(() => _hovering = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedContainer(
          duration: tokens.Durations.instant,
          height: 26,
          padding: const EdgeInsets.symmetric(
            horizontal: tokens.Spacing.sm,
            vertical: 2,
          ),
          decoration: BoxDecoration(
            color: backgroundColor,
            borderRadius: tokens.Radii.borderXs,
            border: isActive
                ? Border.all(
                    color: AppColors.primaryCyan.withValues(alpha: 0.3),
                    width: 1,
                  )
                : null,
          ),
          child: Row(
            children: [
              // Severity color dot or spacer
              if (widget.isSeverity && widget.dotColor != null) ...[
                Container(
                  width: 6,
                  height: 6,
                  decoration: BoxDecoration(
                    color: widget.dotColor,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: tokens.Spacing.xs),
              ],

              // Value label
              Expanded(
                child: Text(
                  widget.value,
                  overflow: TextOverflow.ellipsis,
                  style: GoogleFonts.robotoMono(
                    fontSize: 11,
                    color: textColor,
                  ),
                ),
              ),

              // Count badge
              Text(
                '${widget.count}',
                style: GoogleFonts.robotoMono(
                  fontSize: 10,
                  color: countColor,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
