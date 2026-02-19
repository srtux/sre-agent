import 'dart:math';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../theme/app_theme.dart';
import 'explorer_chart_painter.dart';

/// Aggregation functions available for measures.
enum AggregateFunction {
  sum,
  avg,

  /// COUNT(col) — counts non-null, non-empty values of the column per group.
  count,

  min,
  max,

  /// COUNT(DISTINCT col) — counts unique non-null values per group.
  countDistinct,

  /// COUNT(*) — counts all rows in the group regardless of column value.
  countStar,
}

/// Configuration for a single dimension or measure field.
class FieldConfig {
  final String column;
  final AggregateFunction? aggregate; // null = dimension
  final bool descending;

  const FieldConfig({
    required this.column,
    this.aggregate,
    this.descending = false,
  });

  String get displayName {
    switch (aggregate) {
      case AggregateFunction.countStar:
        return 'COUNT(*)';
      case null:
        return column;
      default:
        return '${aggregate!.name.toUpperCase()}($column)';
    }
  }
}

/// A Tableau-like visual data explorer that works with tabular BigQuery results.
///
/// Allows users to:
/// - Assign columns as dimensions or measures
/// - Select chart types (bar, horizontal bar, stacked bar, grouped bar, line,
///   area, scatter, pie, heatmap, table)
/// - Apply aggregation functions (SUM, AVG, COUNT, COUNT(*), MIN, MAX,
///   COUNT DISTINCT)
/// - Use multiple dimensions: the **first dimension** maps to the X axis;
///   for [ExplorerChartType.stackedBar] and [ExplorerChartType.groupedBar] a
///   **second dimension** maps to the colour series.
/// - Apply row filters and sort interactively
/// - View all data points loaded from the SQL query — no extra row cap is
///   applied in the visualisation layer
class VisualDataExplorer extends StatefulWidget {
  final List<String> columns;
  final List<Map<String, dynamic>> rows;

  const VisualDataExplorer({
    super.key,
    required this.columns,
    required this.rows,
  });

  @override
  State<VisualDataExplorer> createState() => _VisualDataExplorerState();
}

class _VisualDataExplorerState extends State<VisualDataExplorer> {
  // Explorer configuration
  final List<FieldConfig> _dimensions = [];
  final List<FieldConfig> _measures = [];
  final List<_FilterEntry> _filters = [];
  ExplorerChartType _chartType = ExplorerChartType.bar;
  String? _sortColumn;
  bool _sortDescending = false;

  /// Columns detected as numeric.
  late final Set<String> _numericColumns;

  /// Columns detected as non-numeric (categorical/text/date).
  late final Set<String> _categoricalColumns;

  @override
  void initState() {
    super.initState();
    _detectColumnTypes();
    _autoConfigureDefaults();
  }

  void _detectColumnTypes() {
    _numericColumns = {};
    _categoricalColumns = {};

    for (final col in widget.columns) {
      var isNumeric = false;
      // Check first few non-null values
      for (final row in widget.rows.take(20)) {
        final val = row[col];
        if (val != null) {
          if (val is num || double.tryParse(val.toString()) != null) {
            isNumeric = true;
          }
          break;
        }
      }
      if (isNumeric) {
        _numericColumns.add(col);
      } else {
        _categoricalColumns.add(col);
      }
    }
  }

  void _autoConfigureDefaults() {
    // Auto-pick first categorical as dimension, first numeric as measure.
    if (_categoricalColumns.isNotEmpty) {
      _dimensions.add(FieldConfig(column: _categoricalColumns.first));
    }
    if (_numericColumns.isNotEmpty) {
      _measures.add(
        FieldConfig(
          column: _numericColumns.first,
          aggregate: AggregateFunction.sum,
        ),
      );
    }
  }

  /// Compute aggregated data from current configuration.
  ///
  /// All rows that survive the filter and grouping are returned — no extra
  /// row cap is applied here. The SQL query controls data volume.
  List<Map<String, dynamic>> get _aggregatedData {
    if (_dimensions.isEmpty && _measures.isEmpty) return widget.rows;

    // Apply filters first.
    var filteredRows = widget.rows;
    for (final filter in _filters) {
      filteredRows = filteredRows.where((row) {
        final val = row[filter.column]?.toString() ?? '';
        switch (filter.operator) {
          case '=':
            return val == filter.value;
          case '!=':
            return val != filter.value;
          case 'contains':
            return val.toLowerCase().contains(filter.value.toLowerCase());
          case '>':
            final a = double.tryParse(val);
            final b = double.tryParse(filter.value);
            return a != null && b != null && a > b;
          case '<':
            final a = double.tryParse(val);
            final b = double.tryParse(filter.value);
            return a != null && b != null && a < b;
          default:
            return true;
        }
      }).toList();
    }

    // Group by dimensions.
    final groups = <String, List<Map<String, dynamic>>>{};
    for (final row in filteredRows) {
      final key = _dimensions
          .map((d) => row[d.column]?.toString() ?? '')
          .join('|');
      groups.putIfAbsent(key, () => []).add(row);
    }

    // Aggregate measures per group.
    final result = <Map<String, dynamic>>[];
    for (final entry in groups.entries) {
      final groupRows = entry.value;
      final aggregatedRow = <String, dynamic>{};

      // Add dimension values from first row in group.
      for (final dim in _dimensions) {
        aggregatedRow[dim.column] = groupRows.first[dim.column];
      }

      // Compute aggregations.
      for (final measure in _measures) {
        final aggFn = measure.aggregate ?? AggregateFunction.sum;

        if (aggFn == AggregateFunction.countStar) {
          // COUNT(*): total rows in the group, column is irrelevant.
          aggregatedRow[measure.displayName] = groupRows.length.toDouble();
        } else if (aggFn == AggregateFunction.count ||
            aggFn == AggregateFunction.countDistinct) {
          final values = groupRows
              .map((r) => r[measure.column])
              .where((v) => v != null && v.toString().isNotEmpty)
              .toList();
          aggregatedRow[measure.displayName] =
              aggFn == AggregateFunction.count
                  ? values.length.toDouble()
                  : values.toSet().length.toDouble();
        } else {
          final values = groupRows
              .map((r) => _toDouble(r[measure.column]))
              .where((v) => v != null)
              .cast<double>()
              .toList();

          aggregatedRow[measure.displayName] = _aggregate(values, aggFn);
        }
      }

      result.add(aggregatedRow);
    }

    // Sort.
    if (_sortColumn != null) {
      result.sort((a, b) {
        final aVal = a[_sortColumn] ?? '';
        final bVal = b[_sortColumn] ?? '';
        int cmp;
        if (aVal is num && bVal is num) {
          cmp = aVal.compareTo(bVal);
        } else {
          cmp = aVal.toString().compareTo(bVal.toString());
        }
        return _sortDescending ? -cmp : cmp;
      });
    }

    return result;
  }

  double? _toDouble(dynamic val) {
    if (val == null) return null;
    if (val is num) return val.toDouble();
    if (val is bool) return val ? 1.0 : 0.0;
    if (val is String) return double.tryParse(val);
    return double.tryParse(val.toString());
  }

  double _aggregate(List<double> values, AggregateFunction fn) {
    if (values.isEmpty) return 0;
    switch (fn) {
      case AggregateFunction.sum:
        return values.fold(0.0, (a, b) => a + b);
      case AggregateFunction.avg:
        return values.fold(0.0, (a, b) => a + b) / values.length;
      case AggregateFunction.count:
        return values.length.toDouble();
      case AggregateFunction.min:
        return values.reduce(min);
      case AggregateFunction.max:
        return values.reduce(max);
      case AggregateFunction.countDistinct:
        return values.toSet().length.toDouble();
      case AggregateFunction.countStar:
        return values.length.toDouble();
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        // Configuration toolbar
        _buildConfigBar(),
        // Field shelves (dimensions + measures + filters)
        _buildFieldShelves(),
        // Chart / table content
        Expanded(child: _buildVisualization()),
      ],
    );
  }

  Widget _buildConfigBar() {
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
          // Chart type selector
          const Text(
            'Chart',
            style: TextStyle(fontSize: 10, color: AppColors.textMuted),
          ),
          const SizedBox(width: 6),
          ...ExplorerChartType.values.map(_buildChartTypeChip),
          const Spacer(),
          // Sort toggle
          InkWell(
            borderRadius: BorderRadius.circular(4),
            onTap: () => setState(() => _sortDescending = !_sortDescending),
            child: Padding(
              padding: const EdgeInsets.all(4),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    _sortDescending
                        ? Icons.arrow_downward_rounded
                        : Icons.arrow_upward_rounded,
                    size: 12,
                    color: AppColors.textMuted,
                  ),
                  const SizedBox(width: 2),
                  const Text(
                    'Sort',
                    style: TextStyle(fontSize: 10, color: AppColors.textMuted),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildChartTypeChip(ExplorerChartType type) {
    final isActive = _chartType == type;
    final icon = _chartTypeIcon(type);
    final label = _chartTypeLabel(type);

    return Padding(
      padding: const EdgeInsets.only(right: 2),
      child: Tooltip(
        message: label,
        child: InkWell(
          borderRadius: BorderRadius.circular(4),
          onTap: () => setState(() => _chartType = type),
          child: Container(
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
              color: isActive
                  ? AppColors.primaryCyan.withValues(alpha: 0.15)
                  : Colors.transparent,
              borderRadius: BorderRadius.circular(4),
              border: Border.all(
                color: isActive
                    ? AppColors.primaryCyan.withValues(alpha: 0.3)
                    : Colors.transparent,
              ),
            ),
            child: icon,
          ),
        ),
      ),
    );
  }

  /// Returns the icon widget for [type]. Horizontal bar is a rotated bar icon.
  Widget _chartTypeIcon(ExplorerChartType type) {
    final isActive = _chartType == type;
    final color = isActive ? AppColors.primaryCyan : AppColors.textMuted;

    switch (type) {
      case ExplorerChartType.bar:
        return Icon(Icons.bar_chart_rounded, size: 14, color: color);
      case ExplorerChartType.horizontalBar:
        return Transform.rotate(
          angle: -1.5708, // -90°
          child: Icon(Icons.bar_chart_rounded, size: 14, color: color),
        );
      case ExplorerChartType.stackedBar:
        return Icon(Icons.stacked_bar_chart_rounded, size: 14, color: color);
      case ExplorerChartType.groupedBar:
        return Icon(Icons.view_column_rounded, size: 14, color: color);
      case ExplorerChartType.line:
        return Icon(Icons.show_chart_rounded, size: 14, color: color);
      case ExplorerChartType.area:
        return Icon(Icons.area_chart_rounded, size: 14, color: color);
      case ExplorerChartType.scatter:
        return Icon(Icons.scatter_plot_rounded, size: 14, color: color);
      case ExplorerChartType.pie:
        return Icon(Icons.pie_chart_rounded, size: 14, color: color);
      case ExplorerChartType.heatmap:
        return Icon(Icons.grid_on_rounded, size: 14, color: color);
      case ExplorerChartType.table:
        return Icon(Icons.table_chart_rounded, size: 14, color: color);
    }
  }

  String _chartTypeLabel(ExplorerChartType type) {
    switch (type) {
      case ExplorerChartType.bar:
        return 'Bar';
      case ExplorerChartType.horizontalBar:
        return 'Horizontal Bar';
      case ExplorerChartType.stackedBar:
        return 'Stacked Bar (2 dims)';
      case ExplorerChartType.groupedBar:
        return 'Grouped Bar (2 dims)';
      case ExplorerChartType.line:
        return 'Line';
      case ExplorerChartType.area:
        return 'Area';
      case ExplorerChartType.scatter:
        return 'Scatter';
      case ExplorerChartType.pie:
        return 'Pie';
      case ExplorerChartType.heatmap:
        return 'Heatmap';
      case ExplorerChartType.table:
        return 'Table';
    }
  }

  Widget _buildFieldShelves() {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.02),
        border: Border(
          bottom: BorderSide(
            color: AppColors.surfaceBorder.withValues(alpha: 0.3),
          ),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Dimension hint for multi-series chart types.
          if (_chartType == ExplorerChartType.stackedBar ||
              _chartType == ExplorerChartType.groupedBar)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                children: [
                  Icon(
                    Icons.info_outline_rounded,
                    size: 11,
                    color: AppColors.primaryCyan.withValues(alpha: 0.6),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '1st dimension = X axis  ·  2nd dimension = colour series',
                    style: TextStyle(
                      fontSize: 9,
                      color: AppColors.primaryCyan.withValues(alpha: 0.6),
                    ),
                  ),
                ],
              ),
            ),
          // Dimensions row
          _buildShelfRow(
            label: 'Dimensions',
            icon: Icons.category_rounded,
            color: AppColors.primaryCyan,
            fields: _dimensions,
            availableColumns: widget.columns,
            onAdd: (col) => setState(() {
              _dimensions.add(FieldConfig(column: col));
            }),
            onRemove: (index) => setState(() {
              _dimensions.removeAt(index);
            }),
          ),
          const SizedBox(height: 6),
          // Measures row
          _buildShelfRow(
            label: 'Measures',
            icon: Icons.functions_rounded,
            color: AppColors.warning,
            fields: _measures,
            availableColumns: widget.columns,
            isMeasure: true,
            onAdd: (col) => setState(() {
              _measures.add(
                FieldConfig(column: col, aggregate: AggregateFunction.sum),
              );
            }),
            onRemove: (index) => setState(() {
              _measures.removeAt(index);
            }),
            onUpdateAggregate: (index, fn) => setState(() {
              final old = _measures[index];
              _measures[index] = FieldConfig(
                column: old.column,
                aggregate: fn,
                descending: old.descending,
              );
            }),
          ),
          const SizedBox(height: 6),
          // Filters row
          _buildFiltersRow(),
        ],
      ),
    );
  }

  Widget _buildShelfRow({
    required String label,
    required IconData icon,
    required Color color,
    required List<FieldConfig> fields,
    required List<String> availableColumns,
    required ValueChanged<String> onAdd,
    required ValueChanged<int> onRemove,
    bool isMeasure = false,
    Function(int, AggregateFunction)? onUpdateAggregate,
  }) {
    return Row(
      children: [
        SizedBox(
          width: 80,
          child: Row(
            children: [
              Icon(icon, size: 12, color: color),
              const SizedBox(width: 4),
              Expanded(
                child: Text(
                  label,
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    color: color,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
        ),
        // Field chips
        Expanded(
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                ...List.generate(fields.length, (i) {
                  final field = fields[i];
                  return Padding(
                    padding: const EdgeInsets.only(right: 4),
                    child: _buildFieldChip(
                      field,
                      color,
                      index: i,
                      onRemove: () => onRemove(i),
                      isMeasure: isMeasure,
                      onTapAggregate: isMeasure && onUpdateAggregate != null
                          ? () => _showAggregateMenu(i, onUpdateAggregate)
                          : null,
                    ),
                  );
                }),
                // Add column button
                _buildAddColumnButton(
                  availableColumns,
                  fields.map((f) => f.column).toSet(),
                  color,
                  onAdd,
                  isMeasure: isMeasure,
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildFieldChip(
    FieldConfig field,
    Color color, {
    required int index,
    required VoidCallback onRemove,
    bool isMeasure = false,
    VoidCallback? onTapAggregate,
  }) {
    // Dim index badge: show [1], [2] … for dimensions to indicate role.
    final dimBadge = !isMeasure ? '[${index + 1}]' : null;

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.2)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Dim index badge
          if (dimBadge != null)
            Padding(
              padding: const EdgeInsets.only(right: 3),
              child: Text(
                dimBadge,
                style: TextStyle(
                  fontSize: 8,
                  fontWeight: FontWeight.w700,
                  color: color.withValues(alpha: 0.7),
                ),
              ),
            ),
          if (isMeasure && onTapAggregate != null)
            InkWell(
              onTap: onTapAggregate,
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                margin: const EdgeInsets.only(right: 4),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(3),
                ),
                child: Text(
                  _aggregateBadgeLabel(field.aggregate),
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 8,
                    fontWeight: FontWeight.w700,
                    color: color,
                  ),
                ),
              ),
            ),
          Text(
            field.aggregate == AggregateFunction.countStar
                ? field.column // column shown dimly for context
                : field.column,
            style: GoogleFonts.jetBrainsMono(
              fontSize: 10,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(width: 4),
          InkWell(
            onTap: onRemove,
            child: Icon(
              Icons.close_rounded,
              size: 10,
              color: AppColors.textMuted.withValues(alpha: 0.7),
            ),
          ),
        ],
      ),
    );
  }

  /// Short label used in the aggregate badge chip, e.g. "SUM", "AVG", "CNT*".
  String _aggregateBadgeLabel(AggregateFunction? fn) {
    switch (fn) {
      case AggregateFunction.countStar:
        return 'CNT*';
      case AggregateFunction.countDistinct:
        return 'CNTD';
      case null:
        return 'SUM';
      default:
        return fn.name.toUpperCase();
    }
  }

  Widget _buildAddColumnButton(
    List<String> allColumns,
    Set<String> usedColumns,
    Color color,
    ValueChanged<String> onAdd, {
    bool isMeasure = false,
  }) {
    final available = allColumns
        .where((c) => !usedColumns.contains(c))
        .toList();

    // Measures also offer a COUNT(*) virtual field that doesn't need a column.
    final canAddCountStar =
        isMeasure && !_measures.any((m) => m.aggregate == AggregateFunction.countStar);

    if (available.isEmpty && !canAddCountStar) return const SizedBox.shrink();

    return PopupMenuButton<String>(
      onSelected: (val) {
        if (val == '__count_star__') {
          // Add a COUNT(*) measure — use the first available column as a
          // placeholder (the column value is ignored during aggregation).
          final placeholder = widget.columns.isNotEmpty
              ? widget.columns.first
              : '';
          setState(() {
            _measures.add(
              FieldConfig(
                column: placeholder,
                aggregate: AggregateFunction.countStar,
              ),
            );
          });
        } else {
          onAdd(val);
        }
      },
      tooltip: 'Add column',
      offset: const Offset(0, 24),
      color: AppColors.backgroundCard,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      itemBuilder: (_) => [
        // COUNT(*) virtual option for measures
        if (canAddCountStar)
          PopupMenuItem(
            value: '__count_star__',
            height: 32,
            child: Row(
              children: [
                const Icon(
                  Icons.tag_rounded,
                  size: 12,
                  color: AppColors.warning,
                ),
                const SizedBox(width: 6),
                Text(
                  'COUNT(*)',
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 11,
                    color: AppColors.warning,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ),
        // Regular column entries
        ...available.map((col) {
          final isNumeric = _numericColumns.contains(col);
          return PopupMenuItem(
            value: col,
            height: 32,
            child: Row(
              children: [
                Icon(
                  isNumeric
                      ? Icons.tag_rounded
                      : Icons.text_fields_rounded,
                  size: 12,
                  color: isNumeric
                      ? AppColors.warning
                      : AppColors.primaryCyan,
                ),
                const SizedBox(width: 6),
                Text(
                  col,
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 11,
                    color: AppColors.textPrimary,
                  ),
                ),
              ],
            ),
          );
        }),
      ],
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: color.withValues(alpha: 0.2),
            style: BorderStyle.solid,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.add_rounded, size: 12, color: color),
            const SizedBox(width: 2),
            Text('Add', style: TextStyle(fontSize: 10, color: color)),
          ],
        ),
      ),
    );
  }

  void _showAggregateMenu(
    int index,
    Function(int, AggregateFunction) onUpdate,
  ) {
    final box = context.findRenderObject() as RenderBox;
    final position = box.localToGlobal(Offset.zero);

    showMenu<AggregateFunction>(
      context: context,
      position: RelativeRect.fromLTRB(
        position.dx + 100,
        position.dy + 100,
        position.dx + 200,
        0,
      ),
      color: AppColors.backgroundCard,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      items: AggregateFunction.values
          .map(
            (fn) => PopupMenuItem(
              value: fn,
              height: 32,
              child: Text(
                _aggregateMenuLabel(fn),
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 11,
                  color: AppColors.textPrimary,
                ),
              ),
            ),
          )
          .toList(),
    ).then((fn) {
      if (fn != null) onUpdate(index, fn);
    });
  }

  /// Full label for the aggregate picker menu.
  String _aggregateMenuLabel(AggregateFunction fn) {
    switch (fn) {
      case AggregateFunction.sum:
        return 'SUM';
      case AggregateFunction.avg:
        return 'AVG';
      case AggregateFunction.count:
        return 'COUNT(col)';
      case AggregateFunction.min:
        return 'MIN';
      case AggregateFunction.max:
        return 'MAX';
      case AggregateFunction.countDistinct:
        return 'COUNT DISTINCT';
      case AggregateFunction.countStar:
        return 'COUNT(*)';
    }
  }

  Widget _buildFiltersRow() {
    return Row(
      children: [
        const SizedBox(
          width: 80,
          child: Row(
            children: [
              Icon(
                Icons.filter_alt_rounded,
                size: 12,
                color: AppColors.secondaryPurple,
              ),
              SizedBox(width: 4),
              Expanded(
                child: Text(
                  'Filters',
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    color: AppColors.secondaryPurple,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
        ),
        Expanded(
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                ..._filters.asMap().entries.map((entry) {
                  final filter = entry.value;
                  return Padding(
                    padding: const EdgeInsets.only(right: 4),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 6,
                        vertical: 3,
                      ),
                      decoration: BoxDecoration(
                        color:
                            AppColors.secondaryPurple.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(
                          color: AppColors.secondaryPurple
                              .withValues(alpha: 0.2),
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            '${filter.column} ${filter.operator} ${filter.value}',
                            style: GoogleFonts.jetBrainsMono(
                              fontSize: 9,
                              color: AppColors.textPrimary,
                            ),
                          ),
                          const SizedBox(width: 4),
                          InkWell(
                            onTap: () => setState(
                                () => _filters.removeAt(entry.key)),
                            child: Icon(
                              Icons.close_rounded,
                              size: 10,
                              color:
                                  AppColors.textMuted.withValues(alpha: 0.7),
                            ),
                          ),
                        ],
                      ),
                    ),
                  );
                }),
                // Add filter button
                _buildAddFilterButton(),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildAddFilterButton() {
    if (widget.columns.isEmpty) return const SizedBox.shrink();

    return PopupMenuButton<String>(
      onSelected: (col) => _showFilterDialog(col),
      tooltip: 'Add filter',
      offset: const Offset(0, 24),
      color: AppColors.backgroundCard,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      itemBuilder: (_) => widget.columns.map((col) {
        final isNumeric = _numericColumns.contains(col);
        return PopupMenuItem(
          value: col,
          height: 32,
          child: Row(
            children: [
              Icon(
                isNumeric ? Icons.tag_rounded : Icons.text_fields_rounded,
                size: 12,
                color: isNumeric ? AppColors.warning : AppColors.primaryCyan,
              ),
              const SizedBox(width: 6),
              Text(
                col,
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 11,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
        );
      }).toList(),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: AppColors.secondaryPurple.withValues(alpha: 0.2),
          ),
        ),
        child: const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.add_rounded,
              size: 12,
              color: AppColors.secondaryPurple,
            ),
            SizedBox(width: 2),
            Text(
              'Add',
              style: TextStyle(
                  fontSize: 10, color: AppColors.secondaryPurple),
            ),
          ],
        ),
      ),
    );
  }

  void _showFilterDialog(String column) {
    final isNumeric = _numericColumns.contains(column);
    final operators =
        isNumeric ? ['=', '!=', '>', '<'] : ['=', '!=', 'contains'];
    var selectedOp = operators.first;
    final valueController = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setDialogState) {
            return AlertDialog(
              backgroundColor: AppColors.backgroundCard,
              title: Text(
                'Filter: $column',
                style: const TextStyle(
                  fontSize: 14,
                  color: AppColors.textPrimary,
                ),
              ),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Operator selector
                  Row(
                    children: operators.map((op) {
                      final isSelected = op == selectedOp;
                      return Padding(
                        padding: const EdgeInsets.only(right: 4),
                        child: InkWell(
                          onTap: () =>
                              setDialogState(() => selectedOp = op),
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: isSelected
                                  ? AppColors.secondaryPurple
                                      .withValues(alpha: 0.2)
                                  : Colors.transparent,
                              borderRadius: BorderRadius.circular(4),
                              border: Border.all(
                                color: isSelected
                                    ? AppColors.secondaryPurple
                                    : AppColors.surfaceBorder,
                              ),
                            ),
                            child: Text(
                              op,
                              style: GoogleFonts.jetBrainsMono(
                                fontSize: 12,
                                color: isSelected
                                    ? AppColors.secondaryPurple
                                    : AppColors.textMuted,
                              ),
                            ),
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                  const SizedBox(height: 12),
                  // Value input
                  TextField(
                    controller: valueController,
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 12,
                      color: AppColors.textPrimary,
                    ),
                    decoration: InputDecoration(
                      hintText: 'Filter value...',
                      hintStyle: TextStyle(
                        fontSize: 12,
                        color: AppColors.textMuted.withValues(alpha: 0.5),
                      ),
                      filled: true,
                      fillColor: AppColors.backgroundDark,
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(6),
                        borderSide: const BorderSide(
                          color: AppColors.surfaceBorder,
                        ),
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 8,
                      ),
                    ),
                    autofocus: true,
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(ctx).pop(),
                  child: const Text(
                    'Cancel',
                    style: TextStyle(color: AppColors.textMuted),
                  ),
                ),
                TextButton(
                  onPressed: () {
                    if (valueController.text.isNotEmpty) {
                      setState(() {
                        _filters.add(
                          _FilterEntry(
                            column: column,
                            operator: selectedOp,
                            value: valueController.text,
                          ),
                        );
                      });
                      Navigator.of(ctx).pop();
                    }
                  },
                  child: const Text(
                    'Apply',
                    style: TextStyle(color: AppColors.primaryCyan),
                  ),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Widget _buildVisualization() {
    final data = _aggregatedData;

    if (data.isEmpty || (_dimensions.isEmpty && _measures.isEmpty)) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.analytics_rounded,
              size: 40,
              color: AppColors.textMuted.withValues(alpha: 0.3),
            ),
            const SizedBox(height: 12),
            const Text(
              'Add dimensions and measures to visualise data',
              style: TextStyle(fontSize: 12, color: AppColors.textMuted),
            ),
            const SizedBox(height: 4),
            Text(
              '${widget.rows.length} rows, ${widget.columns.length} columns available',
              style: TextStyle(
                fontSize: 10,
                color: AppColors.textMuted.withValues(alpha: 0.6),
              ),
            ),
          ],
        ),
      );
    }

    if (_chartType == ExplorerChartType.table) {
      return _buildDataTable(data);
    }

    return _buildChart(data);
  }

  Widget _buildDataTable(List<Map<String, dynamic>> data) {
    if (data.isEmpty) return const SizedBox.shrink();

    final cols = data.first.keys.toList();

    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: SingleChildScrollView(
        child: DataTable(
          columnSpacing: 20,
          headingRowHeight: 36,
          dataRowMinHeight: 30,
          dataRowMaxHeight: 30,
          columns: cols.map((col) {
            final isNumeric =
                _numericColumns.contains(col) || col.contains('(');
            return DataColumn(
              label: InkWell(
                onTap: () => setState(() {
                  if (_sortColumn == col) {
                    _sortDescending = !_sortDescending;
                  } else {
                    _sortColumn = col;
                    _sortDescending = false;
                  }
                }),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(
                      col,
                      style: GoogleFonts.jetBrainsMono(
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    if (_sortColumn == col)
                      Icon(
                        _sortDescending
                            ? Icons.arrow_drop_down_rounded
                            : Icons.arrow_drop_up_rounded,
                        size: 14,
                        color: AppColors.primaryCyan,
                      ),
                  ],
                ),
              ),
              numeric: isNumeric,
            );
          }).toList(),
          rows: data.map((row) {
            return DataRow(
              cells: cols.map((col) {
                final val = row[col];
                String display;
                if (val is double) {
                  display = val == val.roundToDouble()
                      ? val.toInt().toString()
                      : val.toStringAsFixed(2);
                } else {
                  display = val?.toString() ?? '';
                }
                return DataCell(
                  Text(
                    display,
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 10,
                      color: AppColors.textSecondary,
                    ),
                  ),
                );
              }).toList(),
            );
          }).toList(),
        ),
      ),
    );
  }

  Widget _buildChart(List<Map<String, dynamic>> data) {
    if (_dimensions.isEmpty || _measures.isEmpty) {
      return const Center(
        child: Text(
          'Add at least one dimension and one measure',
          style: TextStyle(fontSize: 12, color: AppColors.textMuted),
        ),
      );
    }

    // Stacked / grouped bar charts need a 2nd dimension for series colouring.
    final needsSecondDim =
        _chartType == ExplorerChartType.stackedBar ||
        _chartType == ExplorerChartType.groupedBar;
    final hasSecondDim = _dimensions.length >= 2;

    if (needsSecondDim && !hasSecondDim) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.layers_rounded,
              size: 36,
              color: AppColors.primaryCyan.withValues(alpha: 0.4),
            ),
            const SizedBox(height: 10),
            Text(
              'Add a 2nd dimension to use ${_chartTypeLabel(_chartType)}',
              style: const TextStyle(
                  fontSize: 12, color: AppColors.textMuted),
            ),
            const SizedBox(height: 4),
            const Text(
              '1st dimension → X axis  ·  2nd dimension → colour series',
              style: TextStyle(
                  fontSize: 10, color: AppColors.textMuted),
            ),
          ],
        ),
      );
    }

    final dimensionKey = _dimensions.first.column;
    final seriesKey =
        (needsSecondDim && hasSecondDim) ? _dimensions[1].column : null;
    final measureKey = _measures.first.displayName;

    // Legend entries: series values for stacked/grouped, measure names otherwise.
    List<String> legendEntries;
    if (needsSecondDim && hasSecondDim) {
      // seriesKey is non-null here because hasSecondDim is true.
      legendEntries = data
          .map((r) => r[seriesKey!]?.toString() ?? '')
          .toSet()
          .toList();
    } else {
      legendEntries = _measures.map((m) => m.displayName).toList();
    }

    // Row count annotation
    final rowLabel = '${data.length} data points';

    return Column(
      children: [
        // Legend + row count
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
          child: Row(
            children: [
              Expanded(child: _buildLegend(legendEntries)),
              Text(
                rowLabel,
                style: TextStyle(
                  fontSize: 9,
                  color: AppColors.textMuted.withValues(alpha: 0.5),
                ),
              ),
            ],
          ),
        ),
        // Chart area
        Expanded(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: CustomPaint(
              painter: ExplorerChartPainter(
                data: data,
                dimensionKey: dimensionKey,
                measureKey: measureKey,
                measures: _measures.map((m) => m.displayName).toList(),
                chartType: _chartType,
                color: AppColors.primaryCyan,
                textColor: AppColors.textMuted,
                gridColor: AppColors.surfaceBorder,
                seriesKey: seriesKey,
              ),
              child: const SizedBox.expand(),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildLegend(List<String> entries) {
    const colors = explorerChartColors;
    return Wrap(
      spacing: 12,
      runSpacing: 4,
      children: entries.asMap().entries.map((entry) {
        final color = colors[entry.key % colors.length];
        return Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 10,
              height: 10,
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.7),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            const SizedBox(width: 4),
            Text(
              entry.value,
              style: GoogleFonts.jetBrainsMono(
                fontSize: 9,
                color: AppColors.textMuted,
              ),
            ),
          ],
        );
      }).toList(),
    );
  }
}

/// Filter entry for the visual explorer.
class _FilterEntry {
  final String column;
  final String operator;
  final String value;

  const _FilterEntry({
    required this.column,
    required this.operator,
    required this.value,
  });
}
