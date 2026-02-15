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

  /// Column type cache — determined once from first non-null values.
  late final Map<String, _ColumnType> _columnTypes;

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
    // ISO 8601 or common timestamp patterns
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
      // Null-last sorting: nulls always sort to the end regardless of direction
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

    return Column(
      children: [
        // Results summary bar
        _buildSummaryBar(),
        // Scrollable data table
        Expanded(
          child: SelectionArea(
            child: Scrollbar(
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: SingleChildScrollView(
                  child: _buildTable(),
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
          Icon(Icons.table_rows_rounded,
              size: 12,
              color: AppColors.textMuted.withValues(alpha: 0.7)),
          const SizedBox(width: 6),
          Text(
            '${widget.rows.length} rows, ${widget.columns.length} columns',
            style: const TextStyle(
              fontSize: 10,
              color: AppColors.textMuted,
            ),
          ),
          const Spacer(),
          // Export buttons
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

  Widget _buildTable() {
    final rows = _sortedRows;

    // Prepend a row-number column
    final allColumns = ['#', ...widget.columns];

    return DataTable(
      columnSpacing: 24,
      headingRowHeight: 36,
      dataRowMinHeight: 32,
      dataRowMaxHeight: 32,
      headingRowColor: WidgetStateProperty.all(
        Colors.white.withValues(alpha: 0.03),
      ),
      columns: allColumns.map((col) {
        if (col == '#') {
          // Row number column header
          return DataColumn(
            label: Text(
              '#',
              style: GoogleFonts.jetBrainsMono(
                fontSize: 10,
                fontWeight: FontWeight.w600,
                color: AppColors.textMuted.withValues(alpha: 0.5),
              ),
            ),
            numeric: true,
          );
        }
        final isSorted = _sortColumn == col;
        final colType = _columnTypes[col] ?? _ColumnType.string;
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
                // Type indicator icon
                Padding(
                  padding: const EdgeInsets.only(right: 4),
                  child: Icon(
                    _iconForColumnType(colType),
                    size: 10,
                    color: isSorted
                        ? AppColors.primaryCyan.withValues(alpha: 0.7)
                        : AppColors.textMuted.withValues(alpha: 0.4),
                  ),
                ),
                Text(
                  col,
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                    color: isSorted ? AppColors.primaryCyan : AppColors.textPrimary,
                  ),
                ),
                if (isSorted) ...[
                  const SizedBox(width: 2),
                  Icon(
                    _sortDescending
                        ? Icons.arrow_drop_down_rounded
                        : Icons.arrow_drop_up_rounded,
                    size: 16,
                    color: AppColors.primaryCyan,
                  ),
                ],
              ],
            ),
          ),
        );
      }).toList(),
      rows: List.generate(rows.length, (index) {
        final row = rows[index];
        final isHovered = _hoveredRow == index;
        return DataRow(
          color: WidgetStateProperty.all(
            isHovered
                ? Colors.white.withValues(alpha: 0.05)
                : Colors.transparent,
          ),
          cells: allColumns.map((col) {
            if (col == '#') {
              // Row number cell
              return DataCell(
                MouseRegion(
                  onEnter: (_) => setState(() => _hoveredRow = index),
                  onExit: (_) => setState(() => _hoveredRow = null),
                  child: Text(
                    '${index + 1}',
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 9,
                      color: AppColors.textMuted.withValues(alpha: 0.4),
                    ),
                  ),
                ),
              );
            }
            final val = row[col];
            final colType = _columnTypes[col] ?? _ColumnType.string;
            final display = _formatValue(val, colType);
            final fullText = val?.toString() ?? 'NULL';
            final isTruncated = display != fullText && val != null;

            return DataCell(
              MouseRegion(
                onEnter: (_) => setState(() => _hoveredRow = index),
                onExit: (_) => setState(() => _hoveredRow = null),
                child: Tooltip(
                  message: isTruncated || (fullText.length > 30)
                      ? fullText
                      : '',
                  waitDuration: const Duration(milliseconds: 400),
                  child: InkWell(
                    onLongPress: val != null
                        ? () {
                            Clipboard.setData(ClipboardData(text: fullText));
                            if (mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                const SnackBar(
                                  content: Text('Cell value copied'),
                                  duration: Duration(seconds: 1),
                                ),
                              );
                            }
                          }
                        : null,
                    child: Text(
                      display,
                      style: GoogleFonts.jetBrainsMono(
                        fontSize: 10,
                        color: val == null
                            ? AppColors.textMuted.withValues(alpha: 0.5)
                            : colType == _ColumnType.number
                                ? AppColors.warning.withValues(alpha: 0.9)
                                : colType == _ColumnType.timestamp
                                    ? AppColors.secondaryPurple.withValues(alpha: 0.8)
                                    : colType == _ColumnType.boolean
                                        ? AppColors.success.withValues(alpha: 0.8)
                                        : colType == _ColumnType.json
                                            ? AppColors.primaryTeal.withValues(alpha: 0.8)
                                            : AppColors.textSecondary,
                        fontStyle:
                            val == null ? FontStyle.italic : FontStyle.normal,
                      ),
                    ),
                  ),
                ),
              ),
            );
          }).toList(),
        );
      }),
    );
  }

  /// Format a cell value with type-aware formatting.
  String _formatValue(dynamic val, _ColumnType colType) {
    if (val == null) return 'NULL';

    if (val is double) {
      if (val == val.roundToDouble() && val.abs() < 1e15) {
        return _formatNumber(val.toInt());
      }
      return val.toStringAsFixed(4);
    }

    if (val is int) {
      return _formatNumber(val);
    }

    // JSON objects/arrays — compact display
    if (val is Map || val is List) {
      final s = const JsonEncoder().convert(val);
      if (s.length > 80) {
        return '${s.substring(0, 80)}...';
      }
      return s;
    }

    final s = val.toString();
    if (s.length > 80) {
      return '${s.substring(0, 80)}...';
    }
    return s;
  }

  /// Format integers/large numbers with thousands separators.
  String _formatNumber(int value) {
    if (value.abs() < 1000) return value.toString();
    final neg = value < 0;
    final abs = value.abs().toString();
    final buffer = StringBuffer();
    final remainder = abs.length % 3;
    if (remainder > 0) {
      buffer.write(abs.substring(0, remainder));
    }
    for (var i = remainder; i < abs.length; i += 3) {
      if (buffer.isNotEmpty) buffer.write(',');
      buffer.write(abs.substring(i, i + 3));
    }
    return neg ? '-$buffer' : buffer.toString();
  }

  IconData _iconForColumnType(_ColumnType type) {
    switch (type) {
      case _ColumnType.number:
        return Icons.tag_rounded;
      case _ColumnType.boolean:
        return Icons.toggle_on_rounded;
      case _ColumnType.timestamp:
        return Icons.schedule_rounded;
      case _ColumnType.json:
        return Icons.data_object_rounded;
      case _ColumnType.string:
        return Icons.text_fields_rounded;
    }
  }

  void _copyAsCsv() {
    final buffer = StringBuffer();
    buffer.writeln(widget.columns.join(','));
    for (final row in _sortedRows) {
      final values = widget.columns
          .map((c) => _escapeCsv(row[c]?.toString() ?? ''))
          .join(',');
      buffer.writeln(values);
    }
    Clipboard.setData(ClipboardData(text: buffer.toString()));
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Copied as CSV'),
          duration: Duration(seconds: 2),
        ),
      );
    }
  }

  void _copyAsJson() {
    final json = const JsonEncoder.withIndent('  ').convert(_sortedRows);
    Clipboard.setData(ClipboardData(text: json));
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Copied as JSON'),
          duration: Duration(seconds: 2),
        ),
      );
    }
  }

  String _escapeCsv(String value) {
    if (value.contains(',') || value.contains('"') || value.contains('\n')) {
      return '"${value.replaceAll('"', '""')}"';
    }
    return value;
  }
}

/// Internal column type classification for formatting.
enum _ColumnType { string, number, boolean, timestamp, json }
