import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../theme/app_theme.dart';

/// A sortable, scrollable data table for displaying BigQuery SQL query results.
///
/// Supports column sorting, row selection, and CSV/JSON export via clipboard.
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

  List<Map<String, dynamic>> get _sortedRows {
    if (_sortColumn == null) return widget.rows;
    final sorted = List<Map<String, dynamic>>.from(widget.rows);
    sorted.sort((a, b) {
      final aVal = a[_sortColumn];
      final bVal = b[_sortColumn];
      int cmp;
      if (aVal is num && bVal is num) {
        cmp = aVal.compareTo(bVal);
      } else {
        cmp = (aVal?.toString() ?? '').compareTo(bVal?.toString() ?? '');
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

    return DataTable(
      columnSpacing: 24,
      headingRowHeight: 36,
      dataRowMinHeight: 32,
      dataRowMaxHeight: 32,
      headingRowColor: WidgetStateProperty.all(
        Colors.white.withValues(alpha: 0.03),
      ),
      columns: widget.columns.map((col) {
        final isSorted = _sortColumn == col;
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
          cells: widget.columns.map((col) {
            final val = row[col];
            String display;
            if (val is double) {
              display = val == val.roundToDouble()
                  ? val.toInt().toString()
                  : val.toStringAsFixed(4);
            } else if (val == null) {
              display = 'NULL';
            } else {
              display = val.toString();
            }
            return DataCell(
              MouseRegion(
                onEnter: (_) => setState(() => _hoveredRow = index),
                onExit: (_) => setState(() => _hoveredRow = null),
                child: Text(
                  display.length > 50
                      ? '${display.substring(0, 50)}...'
                      : display,
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 10,
                    color: val == null
                        ? AppColors.textMuted.withValues(alpha: 0.5)
                        : AppColors.textSecondary,
                    fontStyle:
                        val == null ? FontStyle.italic : FontStyle.normal,
                  ),
                ),
              ),
            );
          }).toList(),
        );
      }),
    );
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
