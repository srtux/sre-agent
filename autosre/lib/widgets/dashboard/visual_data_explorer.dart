import 'dart:math';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../theme/app_theme.dart';

/// Aggregation functions available for measures.
enum AggregateFunction { sum, avg, count, min, max, countDistinct }

/// Chart types for visualization.
enum ExplorerChartType { bar, line, area, scatter, pie, heatmap, table }

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
      _measures.add(FieldConfig(
        column: _numericColumns.first,
        aggregate: AggregateFunction.sum,
      ));
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
      final key = _dimensions.map((d) => row[d.column]?.toString() ?? '').join('|');
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
        final values = groupRows
            .map((r) => _toDouble(r[measure.column]))
            .where((v) => v != null)
            .cast<double>()
            .toList();

        aggregatedRow[measure.displayName] =
            _aggregate(values, measure.aggregate ?? AggregateFunction.sum);
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
                  .map((v) => DropdownMenuItem(
                        value: v,
                        child: Text('$v'),
                      ))
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
              _measures.add(FieldConfig(
                column: col,
                aggregate: AggregateFunction.sum,
              ));
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
    final available = allColumns.where((c) => !usedColumns.contains(c)).toList();
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
            Text(
              'Add',
              style: TextStyle(fontSize: 10, color: color),
            ),
          ],
        ),
      ),
    );
  }

  void _showAggregateMenu(
      int index, Function(int, AggregateFunction) onUpdate) {
    final box = context.findRenderObject() as RenderBox;
    final position = box.localToGlobal(Offset.zero);

    showMenu<AggregateFunction>(
      context: context,
      position: RelativeRect.fromLTRB(
          position.dx + 100, position.dy + 100, position.dx + 200, 0),
      color: AppColors.backgroundCard,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      items: AggregateFunction.values
          .map((fn) => PopupMenuItem(
                value: fn,
                height: 32,
                child: Text(
                  fn.name.toUpperCase(),
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 11,
                    color: AppColors.textPrimary,
                  ),
                ),
              ))
          .toList(),
    ).then((fn) {
      if (fn != null) onUpdate(index, fn);
    });
  }

  Widget _buildFiltersRow() {
    return Row(
      children: [
        SizedBox(
          width: 80,
          child: Row(
            children: [
              const Icon(Icons.filter_alt_rounded,
                  size: 12, color: AppColors.secondaryPurple),
              const SizedBox(width: 4),
              const Text(
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
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
                      decoration: BoxDecoration(
                        color: AppColors.secondaryPurple.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(
                          color: AppColors.secondaryPurple.withValues(alpha: 0.2),
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
                            onTap: () => setState(() => _filters.removeAt(entry.key)),
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
    final operators = isNumeric ? ['=', '!=', '>', '<'] : ['=', '!=', 'contains'];
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
                                horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: isSelected
                                  ? AppColors.secondaryPurple.withValues(alpha: 0.2)
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
                        borderSide: const BorderSide(color: AppColors.surfaceBorder),
                      ),
                      contentPadding: const EdgeInsets.symmetric(
                          horizontal: 10, vertical: 8),
                    ),
                    autofocus: true,
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.of(ctx).pop(),
                  child: const Text('Cancel',
                      style: TextStyle(color: AppColors.textMuted)),
                ),
                TextButton(
                  onPressed: () {
                    if (valueController.text.isNotEmpty) {
                      setState(() {
                        _filters.add(_FilterEntry(
                          column: column,
                          operator: selectedOp,
                          value: valueController.text,
                        ));
                      });
                      Navigator.of(ctx).pop();
                    }
                  },
                  child: const Text('Apply',
                      style: TextStyle(color: AppColors.primaryCyan)),
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
            Icon(Icons.analytics_rounded,
                size: 40,
                color: AppColors.textMuted.withValues(alpha: 0.3)),
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
        if (_measures.isNotEmpty)
          _buildLegend(legendEntries),
        // Chart area
        Expanded(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: CustomPaint(
              painter: _ExplorerChartPainter(
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
    final colors = _chartColors;
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

  static List<Color> get _chartColors => [
    AppColors.primaryCyan,
    AppColors.warning,
    AppColors.success,
    AppColors.error,
    AppColors.secondaryPurple,
    AppColors.primaryBlue,
    AppColors.info,
    AppColors.primaryTeal,
  ];
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

/// Custom painter for rendering explorer charts.
class _ExplorerChartPainter extends CustomPainter {
  final List<Map<String, dynamic>> data;
  final String dimensionKey;
  final String measureKey;
  final List<String> measures;
  final ExplorerChartType chartType;
  final Color color;
  final Color textColor;
  final Color gridColor;

  static const _chartColors = [
    AppColors.primaryCyan,
    AppColors.warning,
    AppColors.success,
    AppColors.error,
    AppColors.secondaryPurple,
    AppColors.primaryBlue,
    AppColors.info,
    AppColors.primaryTeal,
  ];

  _ExplorerChartPainter({
    required this.data,
    required this.dimensionKey,
    required this.measureKey,
    required this.measures,
    required this.chartType,
    required this.color,
    required this.textColor,
    required this.gridColor,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (data.isEmpty) return;

    final values = data.map((row) {
      final v = row[measureKey];
      if (v is num) return v.toDouble();
      return double.tryParse(v?.toString() ?? '') ?? 0.0;
    }).toList();

    final labels = data.map((row) => row[dimensionKey]?.toString() ?? '').toList();

    if (values.isEmpty) return;

    final maxVal = values.reduce(max);
    final minVal = values.reduce(min);
    final range = maxVal - minVal;

    final chartArea = Rect.fromLTRB(60, 20, size.width - 20, size.height - 40);

    switch (chartType) {
      case ExplorerChartType.bar:
        _drawGrid(canvas, chartArea, maxVal, minVal);
        _drawBarChart(canvas, chartArea, values, labels, maxVal, range);
        _drawAxisLabels(canvas, chartArea, labels);
        break;
      case ExplorerChartType.line:
      case ExplorerChartType.area:
        _drawGrid(canvas, chartArea, maxVal, minVal);
        _drawLineChart(canvas, chartArea, values, labels, minVal, maxVal, range,
            fill: chartType == ExplorerChartType.area);
        _drawAxisLabels(canvas, chartArea, labels);
        break;
      case ExplorerChartType.scatter:
        _drawGrid(canvas, chartArea, maxVal, minVal);
        _drawScatterChart(canvas, chartArea, values, labels, minVal, range);
        _drawAxisLabels(canvas, chartArea, labels);
        break;
      case ExplorerChartType.pie:
        _drawPieChart(canvas, size, values, labels);
        break;
      case ExplorerChartType.heatmap:
        _drawHeatmap(canvas, chartArea, values, labels, minVal, maxVal);
        _drawAxisLabels(canvas, chartArea, labels);
        break;
      case ExplorerChartType.table:
        // Handled by widget, not painter
        break;
    }
  }

  void _drawGrid(Canvas canvas, Rect area, double maxVal, double minVal) {
    final paint = Paint()
      ..color = gridColor.withValues(alpha: 0.15)
      ..strokeWidth = 0.5;

    const gridLines = 5;
    for (var i = 0; i <= gridLines; i++) {
      final y = area.top + (area.height * i / gridLines);
      canvas.drawLine(Offset(area.left, y), Offset(area.right, y), paint);

      // Y-axis labels
      final val = maxVal - (maxVal - minVal) * i / gridLines;
      final tp = TextPainter(
        text: TextSpan(
          text: _formatAxisValue(val),
          style: TextStyle(fontSize: 9, color: textColor.withValues(alpha: 0.6)),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      tp.paint(canvas, Offset(area.left - tp.width - 6, y - tp.height / 2));
    }
  }

  String _formatAxisValue(double val) {
    if (val.abs() >= 1e9) return '${(val / 1e9).toStringAsFixed(1)}B';
    if (val.abs() >= 1e6) return '${(val / 1e6).toStringAsFixed(1)}M';
    if (val.abs() >= 1e3) return '${(val / 1e3).toStringAsFixed(1)}K';
    return val == val.roundToDouble()
        ? val.toInt().toString()
        : val.toStringAsFixed(1);
  }

  void _drawBarChart(Canvas canvas, Rect area, List<double> values,
      List<String> labels, double maxVal, double range) {
    if (maxVal == 0) return;
    final barWidth = (area.width / values.length) * 0.7;
    final gap = (area.width / values.length) * 0.15;

    for (var i = 0; i < values.length; i++) {
      final x = area.left + (area.width * i / values.length) + gap;
      final barHeight = (values[i] / maxVal) * area.height;
      final y = area.bottom - barHeight;

      final paint = Paint()
        ..color = color.withValues(alpha: 0.7)
        ..style = PaintingStyle.fill;

      canvas.drawRRect(
        RRect.fromRectAndCorners(
          Rect.fromLTWH(x, y, barWidth, barHeight),
          topLeft: const Radius.circular(3),
          topRight: const Radius.circular(3),
        ),
        paint,
      );

      // Value label on top of bar
      if (values.length <= 20) {
        final tp = TextPainter(
          text: TextSpan(
            text: _formatAxisValue(values[i]),
            style: TextStyle(
              fontSize: 8,
              color: textColor.withValues(alpha: 0.7),
            ),
          ),
          textDirection: TextDirection.ltr,
        )..layout();
        tp.paint(canvas,
            Offset(x + barWidth / 2 - tp.width / 2, y - tp.height - 2));
      }
    }
  }

  void _drawLineChart(Canvas canvas, Rect area, List<double> values,
      List<String> labels, double minVal, double maxVal, double range,
      {bool fill = false}) {
    if (values.length < 2) return;

    // Handle constant values (range == 0) — draw a horizontal line at midpoint
    final effectiveRange = range == 0 ? 1.0 : range;
    final effectiveMin = range == 0 ? minVal - 0.5 : minVal;

    final points = <Offset>[];
    for (var i = 0; i < values.length; i++) {
      final x = area.left + (area.width * i / (values.length - 1));
      final normalized = (values[i] - effectiveMin) / effectiveRange;
      final y = area.bottom - (normalized * area.height);
      points.add(Offset(x, y));
    }

    // Fill area
    if (fill && points.isNotEmpty) {
      final path = Path()
        ..moveTo(points.first.dx, area.bottom)
        ..lineTo(points.first.dx, points.first.dy);
      for (final p in points.skip(1)) {
        path.lineTo(p.dx, p.dy);
      }
      path.lineTo(points.last.dx, area.bottom);
      path.close();

      canvas.drawPath(
        path,
        Paint()
          ..color = color.withValues(alpha: 0.15)
          ..style = PaintingStyle.fill,
      );
    }

    // Draw line
    final linePaint = Paint()
      ..color = color
      ..strokeWidth = 2
      ..style = PaintingStyle.stroke;

    final linePath = Path()..moveTo(points.first.dx, points.first.dy);
    for (final p in points.skip(1)) {
      linePath.lineTo(p.dx, p.dy);
    }
    canvas.drawPath(linePath, linePaint);

    // Draw dots
    for (final p in points) {
      canvas.drawCircle(p, 3, Paint()..color = color);
      canvas.drawCircle(
          p,
          2,
          Paint()
            ..color = const Color(0xFF0F172A)
            ..style = PaintingStyle.fill);
    }
  }

  void _drawScatterChart(Canvas canvas, Rect area, List<double> values,
      List<String> labels, double minVal, double range) {
    // Handle constant values gracefully
    final effectiveRange = range == 0 ? 1.0 : range;
    final effectiveMin = range == 0 ? minVal - 0.5 : minVal;

    for (var i = 0; i < values.length; i++) {
      final x = area.left + (area.width * i / values.length) + (area.width / values.length / 2);
      final normalized = (values[i] - effectiveMin) / effectiveRange;
      final y = area.bottom - (normalized * area.height);
      canvas.drawCircle(
          Offset(x, y), 4, Paint()..color = color.withValues(alpha: 0.7));
    }
  }

  void _drawPieChart(
      Canvas canvas, Size size, List<double> values, List<String> labels) {
    final total = values.fold(0.0, (a, b) => a + b.abs());
    if (total == 0) return;

    final center = Offset(size.width * 0.4, size.height / 2);
    final radius = min(size.width * 0.35, size.height / 2.5);
    var startAngle = -pi / 2;

    // Draw slices
    for (var i = 0; i < values.length; i++) {
      final sweep = (values[i].abs() / total) * 2 * pi;
      final paint = Paint()
        ..color = _chartColors[i % _chartColors.length].withValues(alpha: 0.7)
        ..style = PaintingStyle.fill;

      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        startAngle,
        sweep,
        true,
        paint,
      );

      // Slice border for separation
      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        startAngle,
        sweep,
        true,
        Paint()
          ..color = const Color(0xFF0F172A)
          ..strokeWidth = 1.5
          ..style = PaintingStyle.stroke,
      );

      startAngle += sweep;
    }

    // Draw legend on the right side
    final legendX = size.width * 0.7;
    var legendY = max(20.0, (size.height - values.length * 18) / 2);
    for (var i = 0; i < values.length && i < 15; i++) {
      final color = _chartColors[i % _chartColors.length];
      final label = labels[i].length > 18
          ? '${labels[i].substring(0, 18)}...'
          : labels[i];
      final pct = (values[i].abs() / total * 100).toStringAsFixed(1);

      // Color swatch
      canvas.drawRRect(
        RRect.fromRectAndRadius(
          Rect.fromLTWH(legendX, legendY, 8, 8),
          const Radius.circular(2),
        ),
        Paint()..color = color.withValues(alpha: 0.7),
      );

      // Label
      final tp = TextPainter(
        text: TextSpan(
          text: '$label ($pct%)',
          style: TextStyle(
            fontSize: 9,
            color: textColor.withValues(alpha: 0.8),
          ),
        ),
        textDirection: TextDirection.ltr,
      )..layout(maxWidth: size.width - legendX - 12);
      tp.paint(canvas, Offset(legendX + 12, legendY - 1));

      legendY += 18;
    }
  }

  void _drawHeatmap(Canvas canvas, Rect area, List<double> values,
      List<String> labels, double minVal, double maxVal) {
    if (values.isEmpty) return;

    final range = maxVal - minVal;
    final cellWidth = area.width / values.length;
    final cellHeight = area.height;

    for (var i = 0; i < values.length; i++) {
      // Normalize to 0..1 for color intensity
      final normalized = range == 0 ? 0.5 : (values[i] - minVal) / range;

      // Interpolate from cool (low) to hot (high)
      final cellColor = Color.lerp(
        AppColors.primaryCyan.withValues(alpha: 0.1),
        AppColors.error.withValues(alpha: 0.8),
        normalized,
      )!;

      final x = area.left + cellWidth * i;
      canvas.drawRect(
        Rect.fromLTWH(x, area.top, cellWidth - 1, cellHeight),
        Paint()..color = cellColor,
      );

      // Value label inside cell
      if (values.length <= 30) {
        final tp = TextPainter(
          text: TextSpan(
            text: _formatAxisValue(values[i]),
            style: TextStyle(
              fontSize: 9,
              color: normalized > 0.5
                  ? Colors.white.withValues(alpha: 0.9)
                  : textColor.withValues(alpha: 0.7),
              fontWeight: FontWeight.w500,
            ),
          ),
          textDirection: TextDirection.ltr,
        )..layout();
        tp.paint(
          canvas,
          Offset(
            x + cellWidth / 2 - tp.width / 2,
            area.top + cellHeight / 2 - tp.height / 2,
          ),
        );
      }
    }

    // Color scale legend at top-right
    final scaleWidth = 80.0;
    final scaleHeight = 8.0;
    final scaleX = area.right - scaleWidth;
    final scaleY = area.top - 16;
    for (var i = 0; i < scaleWidth.toInt(); i++) {
      final t = i / scaleWidth;
      final c = Color.lerp(
        AppColors.primaryCyan.withValues(alpha: 0.1),
        AppColors.error.withValues(alpha: 0.8),
        t,
      )!;
      canvas.drawRect(
        Rect.fromLTWH(scaleX + i, scaleY, 1, scaleHeight),
        Paint()..color = c,
      );
    }
    // Scale labels
    final lowTp = TextPainter(
      text: TextSpan(
        text: _formatAxisValue(minVal),
        style: TextStyle(fontSize: 7, color: textColor.withValues(alpha: 0.5)),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    lowTp.paint(canvas, Offset(scaleX, scaleY - lowTp.height - 1));

    final highTp = TextPainter(
      text: TextSpan(
        text: _formatAxisValue(maxVal),
        style: TextStyle(fontSize: 7, color: textColor.withValues(alpha: 0.5)),
      ),
      textDirection: TextDirection.ltr,
    )..layout();
    highTp.paint(
        canvas, Offset(scaleX + scaleWidth - highTp.width, scaleY - highTp.height - 1));
  }

  void _drawAxisLabels(Canvas canvas, Rect area, List<String> labels) {
    // Determine max label length based on available space
    final labelWidth = area.width / labels.length;
    final maxChars = max(4, min(20, (labelWidth / 6).floor()));

    for (var i = 0; i < labels.length; i++) {
      final x = area.left + (area.width * i / labels.length) + (area.width / labels.length / 2);
      final label = labels[i].length > maxChars
          ? '${labels[i].substring(0, maxChars)}..'
          : labels[i];
      final tp = TextPainter(
        text: TextSpan(
          text: label,
          style: TextStyle(fontSize: 8, color: textColor.withValues(alpha: 0.6)),
        ),
        textDirection: TextDirection.ltr,
      )..layout();

      // Rotate labels if many items
      if (labels.length > 8) {
        canvas.save();
        canvas.translate(x, area.bottom + 4);
        canvas.rotate(0.5); // ~30 degrees
        tp.paint(canvas, Offset.zero);
        canvas.restore();
      } else {
        tp.paint(canvas, Offset(x - tp.width / 2, area.bottom + 4));
      }
    }
  }

  @override
  bool shouldRepaint(covariant _ExplorerChartPainter oldDelegate) =>
      data != oldDelegate.data ||
      dimensionKey != oldDelegate.dimensionKey ||
      measureKey != oldDelegate.measureKey ||
      chartType != oldDelegate.chartType ||
      measures != oldDelegate.measures;
}
