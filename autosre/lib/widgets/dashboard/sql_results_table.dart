import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../theme/app_theme.dart';

/// A sortable, scrollable data table for displaying BigQuery SQL query results.
///
/// Supports column sorting (with null-last semantics), row numbering,
/// tooltips for truncated/long values, number formatting, and CSV/JSON export.
class SqlResultsTable extends StatefulWidget {
  final List<String> columns;
  final List<Map<String, dynamic>> rows;

  const SqlResultsTable({
    super.key,
    required this.columns,
    required this.rows,
  });

  @override
  State<SqlResultsTable> createState() => _SqlResultsTableState();
}

class _SqlResultsTableState extends State<SqlResultsTable> {
  String? _sortColumn;
  bool _sortDescending = false;
  int? _hoveredRow;
  final Set<int> _expandedRows = {};

  /// Column type cache — determined once from first non-null values.
  late Map<String, _ColumnType> _columnTypes;

  @override
  void initState() {
    super.initState();
    _columnTypes = _detectColumnTypes();
  }

  @override
  void didUpdateWidget(SqlResultsTable oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.columns != widget.columns || oldWidget.rows != widget.rows) {
      _columnTypes = _detectColumnTypes();
      _expandedRows.clear();
    }
  }

  Map<String, _ColumnType> _detectColumnTypes() {
    final types = <String, _ColumnType>{};
    for (final col in widget.columns) {
      var detected = _ColumnType.string;
      for (final row in widget.rows.take(30)) {
        final val = row[col];
        if (val == null) continue;
        if (val is Map || val is List) {
          detected = _ColumnType.json;
        } else if (val is num) {
          detected = _ColumnType.number;
        } else if (val is bool) {
          detected = _ColumnType.boolean;
        } else {
          final s = val.toString();
          if (double.tryParse(s) != null) {
            detected = _ColumnType.number;
          } else if (_looksLikeTimestamp(s)) {
            detected = _ColumnType.timestamp;
          } else if (_looksLikeJson(s)) {
            detected = _ColumnType.json;
          } else {
            detected = _ColumnType.string;
          }
        }
        break; // use first non-null value
      }
      types[col] = detected;
    }
    return types;
  }

  static bool _looksLikeTimestamp(String s) {
    return RegExp(r'^\d{4}-\d{2}-\d{2}[T ]').hasMatch(s);
  }

  static bool _looksLikeJson(String s) {
    final trimmed = s.trim();
    return (trimmed.startsWith('{') && trimmed.endsWith('}')) ||
        (trimmed.startsWith('[') && trimmed.endsWith(']'));
  }

  List<Map<String, dynamic>> get _sortedRows {
    if (_sortColumn == null) return widget.rows;
    final sorted = List<Map<String, dynamic>>.from(widget.rows);
    sorted.sort((a, b) {
      final aVal = a[_sortColumn];
      final bVal = b[_sortColumn];
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      int cmp;
      if (aVal is num && bVal is num) {
        cmp = aVal.compareTo(bVal);
      } else {
        cmp = aVal.toString().compareTo(bVal.toString());
      }
      return _sortDescending ? -cmp : cmp;
    });
    return sorted;
  }

  @override
  Widget build(BuildContext context) {
    if (widget.columns.isEmpty) {
      return const Center(
        child: Text(
          'No results',
          style: TextStyle(fontSize: 12, color: AppColors.textMuted),
        ),
      );
    }

    final rows = _sortedRows;
    final allColumns = ['#', ...widget.columns];

    return Column(
      children: [
        _buildSummaryBar(),
        Expanded(
          child: Scrollbar(
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: SizedBox(
                width: allColumns.length * 150.0, // Base width for columns
                child: Column(
                  children: [
                    _buildHeader(allColumns),
                    Expanded(
                      child: ListView.builder(
                        itemCount: rows.length,
                        itemBuilder: (context, index) {
                          return _buildRow(rows[index], index, allColumns);
                        },
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildSummaryBar() {
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
          const Icon(Icons.table_rows_rounded, size: 12, color: AppColors.textMuted),
          const SizedBox(width: 6),
          Text(
            '${widget.rows.length} rows, ${widget.columns.length} columns',
            style: const TextStyle(fontSize: 10, color: AppColors.textMuted),
          ),
          const Spacer(),
          _buildExportButton(
            icon: Icons.content_copy_rounded,
            label: 'CSV',
            onTap: _copyAsCsv,
          ),
          const SizedBox(width: 6),
          _buildExportButton(
            icon: Icons.data_object_rounded,
            label: 'JSON',
            onTap: _copyAsJson,
          ),
        ],
      ),
    );
  }

  Widget _buildExportButton({
    required IconData icon,
    required String label,
    required VoidCallback onTap,
  }) {
    return InkWell(
      borderRadius: BorderRadius.circular(4),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(4),
          border: Border.all(
            color: AppColors.surfaceBorder.withValues(alpha: 0.3),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 11, color: AppColors.textMuted),
            const SizedBox(width: 4),
            Text(
              label,
              style: const TextStyle(fontSize: 9, color: AppColors.textMuted),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader(List<String> columns) {
    return Container(
      height: 36,
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        border: const Border(
          bottom: BorderSide(color: AppColors.surfaceBorder, width: 1),
        ),
      ),
      child: Row(
        children: columns.map((col) {
          final isIndex = col == '#';
          final colType = isIndex ? _ColumnType.string : (_columnTypes[col] ?? _ColumnType.string);
          final isSorted = _sortColumn == col;

          return Expanded(
            flex: isIndex ? 0 : 1,
            child: SizedBox(
              width: isIndex ? 50 : 150,
              child: InkWell(
                onTap: isIndex
                    ? null
                    : () => setState(() {
                          if (_sortColumn == col) {
                            _sortDescending = !_sortDescending;
                          } else {
                            _sortColumn = col;
                            _sortDescending = false;
                          }
                        }),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  child: Row(
                    children: [
                      if (!isIndex)
                        Icon(
                          _iconForColumnType(colType),
                          size: 10,
                          color: isSorted ? AppColors.primaryCyan : AppColors.textMuted,
                        ),
                      if (!isIndex) const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          col,
                          style: GoogleFonts.jetBrainsMono(
                            fontSize: 10,
                            fontWeight: FontWeight.w600,
                            color: isSorted ? AppColors.primaryCyan : AppColors.textPrimary,
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      if (isSorted)
                        Icon(
                          _sortDescending ? Icons.arrow_drop_down : Icons.arrow_drop_up,
                          size: 14,
                          color: AppColors.primaryCyan,
                        ),
                    ],
                  ),
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildRow(Map<String, dynamic> row, int index, List<String> columns) {
    final isExpanded = _expandedRows.contains(index);
    final hasJson = _columnTypes.values.any((t) => t == _ColumnType.json);

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        InkWell(
          onTap: hasJson ? () => setState(() {
            if (isExpanded) {
              _expandedRows.remove(index);
            } else {
              _expandedRows.add(index);
            }
          }) : null,
          onHover: (hovering) => setState(() => _hoveredRow = hovering ? index : null),
          child: Container(
            height: 32,
            decoration: BoxDecoration(
              color: _hoveredRow == index ? Colors.white.withValues(alpha: 0.05) : Colors.transparent,
              border: const Border(
                bottom: BorderSide(color: AppColors.surfaceBorder, width: 0.5),
              ),
            ),
            child: Row(
              children: columns.map((col) {
                final isIndex = col == '#';
                final val = isIndex ? (index + 1) : row[col];
                final colType = isIndex ? _ColumnType.number : (_columnTypes[col] ?? _ColumnType.string);
                final display = _formatValue(val, colType, compact: true);

                return Expanded(
                  flex: isIndex ? 0 : 1,
                  child: SizedBox(
                    width: isIndex ? 50 : 150,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 12),
                      child: Row(
                        children: [
                          if (isIndex && hasJson)
                            Icon(
                              isExpanded ? Icons.keyboard_arrow_down : Icons.keyboard_arrow_right,
                              size: 12,
                              color: AppColors.textMuted,
                            ),
                          if (isIndex && hasJson) const SizedBox(width: 4),
                          Expanded(
                            child: Text(
                              display,
                              style: GoogleFonts.jetBrainsMono(
                                fontSize: 10,
                                color: val == null
                                    ? AppColors.textMuted.withValues(alpha: 0.5)
                                    : colType == _ColumnType.json
                                        ? AppColors.primaryTeal
                                        : AppColors.textSecondary,
                                fontStyle: val == null ? FontStyle.italic : FontStyle.normal,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
          ),
        ),
        if (isExpanded) _buildExpandedArea(row),
      ],
    );
  }

  Widget _buildExpandedArea(Map<String, dynamic> row) {
    final jsonCols = widget.columns.where((c) => _columnTypes[c] == _ColumnType.json).toList();

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.2),
        border: const Border(
          bottom: BorderSide(color: AppColors.surfaceBorder, width: 1),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: jsonCols.map((col) {
          final val = row[col];
          return Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.data_object, size: 12, color: AppColors.primaryTeal),
                    const SizedBox(width: 6),
                    Text(
                      col,
                      style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        color: AppColors.primaryTeal,
                      ),
                    ),
                    const Spacer(),
                    IconButton(
                      icon: const Icon(Icons.copy, size: 12),
                      onPressed: () => Clipboard.setData(ClipboardData(text: _formatValue(val, _ColumnType.json, compact: false))),
                      padding: EdgeInsets.zero,
                      constraints: const BoxConstraints(),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.backgroundDark,
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(color: AppColors.surfaceBorder),
                  ),
                  child: SelectableText(
                    _formatValue(val, _ColumnType.json, compact: false),
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 11,
                      color: AppColors.textSecondary,
                      height: 1.5,
                    ),
                  ),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }

  String _formatValue(dynamic val, _ColumnType colType, {bool compact = true}) {
    if (val == null) return 'NULL';
    if (val is double) {
      if (val == val.roundToDouble() && val.abs() < 1e15) return _formatNumber(val.toInt());
      return val.toStringAsFixed(4);
    }
    if (val is int) return _formatNumber(val);

    if (colType == _ColumnType.json) {
      try {
        final dynamic decoded = val is String ? jsonDecode(val) : val;
        final encoder = compact ? const JsonEncoder() : const JsonEncoder.withIndent('  ');
        final s = encoder.convert(decoded);
        if (compact && s.length > 50) return '${s.substring(0, 50)}...';
        return s;
      } catch (_) {
        return val.toString();
      }
    }

    final s = val.toString();
    if (compact && s.length > 50) return '${s.substring(0, 50)}...';
    return s;
  }

  String _formatNumber(int value) {
    if (value.abs() < 1000) return value.toString();
    final neg = value < 0;
    final abs = value.abs().toString();
    final buffer = StringBuffer();
    final remainder = abs.length % 3;
    if (remainder > 0) buffer.write(abs.substring(0, remainder));
    for (var i = remainder; i < abs.length; i += 3) {
      if (buffer.isNotEmpty) buffer.write(',');
      buffer.write(abs.substring(i, i + 3));
    }
    return neg ? '-$buffer' : buffer.toString();
  }

  IconData _iconForColumnType(_ColumnType type) {
    switch (type) {
      case _ColumnType.number: return Icons.tag_rounded;
      case _ColumnType.boolean: return Icons.toggle_on_rounded;
      case _ColumnType.timestamp: return Icons.schedule_rounded;
      case _ColumnType.json: return Icons.data_object_rounded;
      case _ColumnType.string: return Icons.text_fields_rounded;
    }
  }

  void _copyAsCsv() {
    final buffer = StringBuffer();
    buffer.writeln(widget.columns.join(','));
    for (final row in _sortedRows) {
      final values = widget.columns.map((c) => _escapeCsv(row[c]?.toString() ?? '')).join(',');
      buffer.writeln(values);
    }
    Clipboard.setData(ClipboardData(text: buffer.toString()));
  }

  void _copyAsJson() {
    final json = const JsonEncoder.withIndent('  ').convert(_sortedRows);
    Clipboard.setData(ClipboardData(text: json));
  }

  String _escapeCsv(String value) {
    if (value.contains(',') || value.contains('"') || value.contains('\n')) {
      return '"${value.replaceAll('"', '""')}"';
    }
    return value;
  }
}

enum _ColumnType { string, number, boolean, timestamp, json }
