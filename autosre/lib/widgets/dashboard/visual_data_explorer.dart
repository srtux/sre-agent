import 'dart:math';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../theme/app_theme.dart';
import 'explorer_chart_painter.dart';

/// Aggregation functions available for measures.
enum AggregateFunction { sum, avg, count, min, max, countDistinct }

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
    if (aggregate != null) {
      return '${aggregate!.name.toUpperCase()}($column)';
    }
    return column;
  }
}

/// A Tableau-like visual data explorer that works with tabular BigQuery results.
///
/// Allows users to:
/// - Assign columns as dimensions or measures
/// - Select chart types (bar, line, scatter, pie, heatmap, etc.)
/// - Apply aggregation functions (SUM, AVG, COUNT, MIN, MAX)
/// - Group by and filter interactively
/// - View the transformed data as a chart or table
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
  int _limit = 100;

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
    // Auto-pick first categorical as dimension, first numeric as measure
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
  List<Map<String, dynamic>> get _aggregatedData {
    if (_dimensions.isEmpty && _measures.isEmpty) return widget.rows;

    // Apply filters first
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

    // Group by dimensions
    final groups = <String, List<Map<String, dynamic>>>{};
    for (final row in filteredRows) {
      final key = _dimensions
          .map((d) => row[d.column]?.toString() ?? '')
          .join('|');
      groups.putIfAbsent(key, () => []).add(row);
    }

    // Aggregate measures per group
    final result = <Map<String, dynamic>>[];
    for (final entry in groups.entries) {
      final groupRows = entry.value;
      final aggregatedRow = <String, dynamic>{};

      // Add dimension values from first row in group
      for (final dim in _dimensions) {
        aggregatedRow[dim.column] = groupRows.first[dim.column];
      }

      // Compute aggregations
      for (final measure in _measures) {
        final aggFn = measure.aggregate ?? AggregateFunction.sum;
        if (aggFn == AggregateFunction.count ||
            aggFn == AggregateFunction.countDistinct) {
          final values = groupRows
              .map((r) => r[measure.column])
              .where((v) => v != null && v.toString().isNotEmpty)
              .toList();
          aggregatedRow[measure.displayName] = aggFn == AggregateFunction.count
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

    // Sort
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

    return result.take(_limit).toList();
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
          // Limit control
          const Text(
            'Limit',
            style: TextStyle(fontSize: 10, color: AppColors.textMuted),
          ),
          const SizedBox(width: 4),
          SizedBox(
            width: 50,
            child: DropdownButton<int>(
              value: _limit,
              isDense: true,
              underline: const SizedBox.shrink(),
              dropdownColor: AppColors.backgroundCard,
              style: GoogleFonts.jetBrainsMono(
                fontSize: 10,
                color: AppColors.textPrimary,
              ),
              items: [10, 25, 50, 100, 500, 1000]
                  .map((v) => DropdownMenuItem(value: v, child: Text('$v')))
                  .toList(),
              onChanged: (v) => setState(() => _limit = v ?? 100),
            ),
          ),
          const SizedBox(width: 8),
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
    return Padding(
      padding: const EdgeInsets.only(right: 2),
      child: Tooltip(
        message: type.name,
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
            child: Icon(
              _chartTypeIcon(type),
              size: 14,
              color: isActive ? AppColors.primaryCyan : AppColors.textMuted,
            ),
          ),
        ),
      ),
    );
  }

  IconData _chartTypeIcon(ExplorerChartType type) {
    switch (type) {
      case ExplorerChartType.bar:
        return Icons.bar_chart_rounded;
      case ExplorerChartType.line:
        return Icons.show_chart_rounded;
      case ExplorerChartType.area:
        return Icons.area_chart_rounded;
      case ExplorerChartType.scatter:
        return Icons.scatter_plot_rounded;
      case ExplorerChartType.pie:
        return Icons.pie_chart_rounded;
      case ExplorerChartType.heatmap:
        return Icons.grid_on_rounded;
      case ExplorerChartType.table:
        return Icons.table_chart_rounded;
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
        children: [
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
              Text(
                label,
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  color: color,
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
    required VoidCallback onRemove,
    bool isMeasure = false,
    VoidCallback? onTapAggregate,
  }) {
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
          if (isMeasure && onTapAggregate != null)
            InkWell(
              onTap: onTapAggregate,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                margin: const EdgeInsets.only(right: 4),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(3),
                ),
                child: Text(
                  field.aggregate?.name.toUpperCase() ?? 'SUM',
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 8,
                    fontWeight: FontWeight.w700,
                    color: color,
                  ),
                ),
              ),
            ),
          Text(
            field.column,
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

  Widget _buildAddColumnButton(
    List<String> allColumns,
    Set<String> usedColumns,
    Color color,
    ValueChanged<String> onAdd,
  ) {
    final available = allColumns
        .where((c) => !usedColumns.contains(c))
        .toList();
    if (available.isEmpty) return const SizedBox.shrink();

    return PopupMenuButton<String>(
      onSelected: onAdd,
      tooltip: 'Add column',
      offset: const Offset(0, 24),
      color: AppColors.backgroundCard,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      itemBuilder: (_) => available.map((col) {
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
                fn.name.toUpperCase(),
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
              Text(
                'Filters',
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  color: AppColors.secondaryPurple,
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
                        color: AppColors.secondaryPurple.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(
                          color: AppColors.secondaryPurple.withValues(
                            alpha: 0.2,
                          ),
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
                            onTap: () =>
                                setState(() => _filters.removeAt(entry.key)),
                            child: Icon(
                              Icons.close_rounded,
                              size: 10,
                              color: AppColors.textMuted.withValues(alpha: 0.7),
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
            Icon(Icons.add_rounded, size: 12, color: AppColors.secondaryPurple),
            SizedBox(width: 2),
            Text(
              'Add',
              style: TextStyle(fontSize: 10, color: AppColors.secondaryPurple),
            ),
          ],
        ),
      ),
    );
  }

  void _showFilterDialog(String column) {
    final isNumeric = _numericColumns.contains(column);
    final operators = isNumeric
        ? ['=', '!=', '>', '<']
        : ['=', '!=', 'contains'];
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
                          onTap: () => setDialogState(() => selectedOp = op),
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 8,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: isSelected
                                  ? AppColors.secondaryPurple.withValues(
                                      alpha: 0.2,
                                    )
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
              'Add dimensions and measures to visualize data',
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

    final dimensionKey = _dimensions.first.column;
    final measureKey = _measures.first.displayName;

    // Build legend entries for multi-measure charts
    final legendEntries = _measures.map((m) => m.displayName).toList();

    return Column(
      children: [
        // Chart legend
        if (_measures.isNotEmpty) _buildLegend(legendEntries),
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
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: entries.asMap().entries.map((entry) {
          final color = colors[entry.key % colors.length];
          return Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8),
            child: Row(
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
            ),
          );
        }).toList(),
      ),
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
