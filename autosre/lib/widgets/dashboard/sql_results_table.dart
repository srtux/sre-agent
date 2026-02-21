import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../theme/app_theme.dart';
import '../../utils/isolate_helper.dart';
import 'json_payload_viewer.dart';

/// A sortable, scrollable data table for displaying BigQuery SQL query results.
///
/// Supports column sorting (with null-last semantics), row numbering,
/// tooltips for truncated/long values, number formatting, and CSV/JSON export.
class SqlResultsTable extends StatefulWidget {
  final List<String> columns;
  final List<Map<String, dynamic>> rows;

  const SqlResultsTable({super.key, required this.columns, required this.rows});

  @override
  State<SqlResultsTable> createState() => _SqlResultsTableState();
}

class _SqlResultsTableState extends State<SqlResultsTable> {
  String? _sortColumn;
  bool _sortDescending = false;
  int? _hoveredRow;
  final Set<int> _expandedRows = {};

  // Pagination
  int _currentPage = 0;
  int _pageSize = 100;

  // Column resizing
  late Map<String, double> _columnWidths;

  /// Column type cache — determined once from first non-null values.
  late Map<String, _ColumnType> _columnTypes;

  bool _isLoading = true;
  List<Map<String, dynamic>> _processedRows = [];

  @override
  void initState() {
    super.initState();
    _initColumnWidths();
    _processDataAsync();
  }

  Future<void> _processDataAsync() async {
    setState(() => _isLoading = true);

    try {
      _ProcessRowsResult result;
      final args = _ProcessRowsArgs(columns: widget.columns, rows: widget.rows);

      // Avoid isolate overhead for small datasets (also bypasses compute in widget tests)
      if (widget.rows.length < 500) {
        result = _ProcessRowsTask.process(args);
      } else {
        result = await AppIsolate.run(_ProcessRowsTask.process, args);
      }

      if (!mounted) return;

      setState(() {
        _columnTypes = result.columnTypes;
        _processedRows = result.processedRows;
        _cachedSortedRows = null; // Invalidate sort cache
        _isLoading = false;
      });
    } catch (e, stack) {
      debugPrint('Error processing rows: $e\n$stack');
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _columnTypes = {};
        _processedRows = [];
      });
    }
  }

  void _initColumnWidths() {
    _columnWidths = {};
    _columnWidths['#'] = 50.0;
    for (final col in widget.columns) {
      _columnWidths[col] = 150.0;
    }
  }

  @override
  void didUpdateWidget(SqlResultsTable oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.columns != widget.columns || oldWidget.rows != widget.rows) {
      _initColumnWidths();
      _expandedRows.clear();
      _currentPage = 0;
      _processDataAsync();
    }
  }

  static bool _looksLikeTimestamp(String s) {
    return RegExp(r'^\d{4}-\d{2}-\d{2}[T ]').hasMatch(s);
  }

  static bool _looksLikeJson(String s) {
    final trimmed = s.trim();
    return (trimmed.startsWith('{') && trimmed.endsWith('}')) ||
        (trimmed.startsWith('[') && trimmed.endsWith(']'));
  }

  // Cached sort state to avoid re-sorting on every build.
  List<Map<String, dynamic>>? _cachedSortedRows;
  String? _cachedSortColumn;
  bool _cachedSortDescending = false;

  List<Map<String, dynamic>> get _sortedRows {
    if (_sortColumn == null) return _processedRows;
    // Return cache if sort parameters haven't changed.
    if (_cachedSortedRows != null &&
        _cachedSortColumn == _sortColumn &&
        _cachedSortDescending == _sortDescending) {
      return _cachedSortedRows!;
    }
    final sorted = List<Map<String, dynamic>>.from(_processedRows);
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
    _cachedSortedRows = sorted;
    _cachedSortColumn = _sortColumn;
    _cachedSortDescending = _sortDescending;
    return sorted;
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            SizedBox(
              width: 24,
              height: 24,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
            SizedBox(height: 12),
            Text(
              'Processing data...',
              style: TextStyle(fontSize: 12, color: AppColors.textMuted),
            ),
          ],
        ),
      );
    }

    if (widget.columns.isEmpty) {
      return const Center(
        child: Text(
          'No results',
          style: TextStyle(fontSize: 12, color: AppColors.textMuted),
        ),
      );
    }

    final rows = _sortedRows;
    final startIndex = _currentPage * _pageSize;
    final endIndex = (startIndex + _pageSize).clamp(0, rows.length);
    final pagedRows = rows.sublist(startIndex, endIndex);

    final allColumns = ['#', ...widget.columns];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildSummaryBar(),
        Expanded(
          child: Align(
            alignment: Alignment.topLeft,
            child: Scrollbar(
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: SizedBox(
                  width: allColumns.fold(
                    0.0,
                    (sum, col) =>
                        (sum as double) + (_columnWidths[col] ?? 150.0),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildHeader(allColumns),
                      Expanded(
                        child: ListView.builder(
                          itemCount: pagedRows.length,
                          itemBuilder: (context, index) {
                            final actualIndex =
                                _currentPage * _pageSize + index;
                            return _buildRow(
                              pagedRows[index],
                              actualIndex,
                              allColumns,
                            );
                          },
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
        _buildPaginationFooter(rows.length),
      ],
    );
  }

  Widget _buildPaginationFooter(int totalRows) {
    final totalPages = (totalRows / _pageSize).ceil();
    final startItem = totalRows == 0 ? 0 : (_currentPage * _pageSize) + 1;
    final endItem = (startItem + _pageSize - 1).clamp(0, totalRows);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.backgroundCard.withValues(alpha: 0.5),
        border: Border(
          top: BorderSide(
            color: AppColors.surfaceBorder.withValues(alpha: 0.3),
          ),
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.end,
        children: [
          const Text(
            'Rows per page:',
            style: TextStyle(fontSize: 10, color: AppColors.textMuted),
          ),
          const SizedBox(width: 8),
          DropdownButton<int>(
            value: _pageSize,
            isDense: true,
            underline: const SizedBox.shrink(),
            style: GoogleFonts.jetBrainsMono(
              fontSize: 10,
              color: AppColors.textPrimary,
            ),
            dropdownColor: AppColors.backgroundCard,
            items: [50, 100, 200, 1000]
                .map((s) => DropdownMenuItem(value: s, child: Text('$s')))
                .toList(),
            onChanged: (val) {
              if (val != null) {
                setState(() {
                  _pageSize = val;
                  _currentPage = 0;
                });
              }
            },
          ),
          const SizedBox(width: 16),
          Text(
            '$startItem-$endItem of $totalRows',
            style: const TextStyle(fontSize: 10, color: AppColors.textMuted),
          ),
          const SizedBox(width: 16),
          IconButton(
            icon: const Icon(Icons.chevron_left, size: 16),
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
            color: _currentPage > 0
                ? AppColors.textPrimary
                : AppColors.textMuted,
            onPressed: _currentPage > 0
                ? () => setState(() => _currentPage--)
                : null,
          ),
          const SizedBox(width: 16),
          IconButton(
            icon: const Icon(Icons.chevron_right, size: 16),
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
            color: _currentPage < totalPages - 1
                ? AppColors.textPrimary
                : AppColors.textMuted,
            onPressed: _currentPage < totalPages - 1
                ? () => setState(() => _currentPage++)
                : null,
          ),
        ],
      ),
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
          const Icon(
            Icons.table_rows_rounded,
            size: 12,
            color: AppColors.textMuted,
          ),
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
          final colType = isIndex
              ? _ColumnType.string
              : (_columnTypes[col] ?? _ColumnType.string);
          final isSorted = _sortColumn == col;
          final width = _columnWidths[col] ?? 150.0;

          return SizedBox(
            width: width,
            child: Row(
              children: [
                Expanded(
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
                              color: isSorted
                                  ? AppColors.primaryCyan
                                  : AppColors.textMuted,
                            ),
                          if (!isIndex) const SizedBox(width: 6),
                          Expanded(
                            child: Text(
                              col,
                              style: GoogleFonts.jetBrainsMono(
                                fontSize: 10,
                                fontWeight: FontWeight.w600,
                                color: isSorted
                                    ? AppColors.primaryCyan
                                    : AppColors.textPrimary,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                          if (isSorted)
                            Icon(
                              _sortDescending
                                  ? Icons.arrow_drop_down
                                  : Icons.arrow_drop_up,
                              size: 14,
                              color: AppColors.primaryCyan,
                            ),
                        ],
                      ),
                    ),
                  ),
                ),
                // Resizer handle
                MouseRegion(
                  cursor: SystemMouseCursors.resizeColumn,
                  child: GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onHorizontalDragUpdate: (details) {
                      setState(() {
                        final newWidth = width + details.delta.dx;
                        _columnWidths[col] = newWidth.clamp(30.0, 800.0);
                      });
                    },
                    child: Container(width: 4, color: Colors.transparent),
                  ),
                ),
              ],
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
          onTap: hasJson
              ? () => setState(() {
                  if (isExpanded) {
                    _expandedRows.remove(index);
                  } else {
                    _expandedRows.add(index);
                  }
                })
              : null,
          onHover: (hovering) =>
              setState(() => _hoveredRow = hovering ? index : null),
          child: Container(
            height: 32,
            decoration: BoxDecoration(
              color: _hoveredRow == index
                  ? Colors.white.withValues(alpha: 0.05)
                  : Colors.transparent,
              border: const Border(
                bottom: BorderSide(color: AppColors.surfaceBorder, width: 0.5),
              ),
            ),
            child: Row(
              children: columns.map((col) {
                final isIndex = col == '#';
                final val = isIndex ? (index + 1) : row[col];
                final colType = isIndex
                    ? _ColumnType.number
                    : (_columnTypes[col] ?? _ColumnType.string);
                final display = _formatValue(val, colType, compact: true);

                final width = _columnWidths[col] ?? 150.0;

                return SizedBox(
                  width: width,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    child: Row(
                      children: [
                        if (isIndex && hasJson)
                          Icon(
                            isExpanded
                                ? Icons.keyboard_arrow_down
                                : Icons.keyboard_arrow_right,
                            size: 12,
                            color: AppColors.textMuted,
                          ),
                        if (isIndex && hasJson) const SizedBox(width: 4),
                        Expanded(
                          child: Align(
                            alignment: Alignment.centerLeft,
                            child: Text(
                              display,
                              textAlign: TextAlign.left,
                              style: GoogleFonts.jetBrainsMono(
                                fontSize: 10,
                                color: val == null
                                    ? AppColors.textMuted.withValues(alpha: 0.5)
                                    : colType == _ColumnType.json
                                    ? AppColors.primaryTeal
                                    : AppColors.textSecondary,
                                fontStyle: val == null
                                    ? FontStyle.italic
                                    : FontStyle.normal,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ),
                      ],
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
    final jsonCols = widget.columns
        .where((c) => _columnTypes[c] == _ColumnType.json)
        .toList();

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
                    const Icon(
                      Icons.data_object,
                      size: 12,
                      color: AppColors.primaryTeal,
                    ),
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
                      onPressed: () => Clipboard.setData(
                        ClipboardData(
                          text: _formatValue(
                            val,
                            _ColumnType.json,
                            compact: false,
                          ),
                        ),
                      ),
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
                  child: _buildJsonExplorer(val),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildJsonExplorer(dynamic val) {
    if (val == null) {
      return const Text('NULL', style: TextStyle(color: AppColors.textMuted));
    }
    try {
      // Data is already pre-decoded by isolate
      final map = val is Map<String, dynamic> ? val : {'data': val};

      return JsonPayloadViewer(
        json: map,
        onValueTap: (path, disp) {
          Clipboard.setData(ClipboardData(text: disp));
        },
      );
    } catch (_) {
      return SelectableText(
        _formatValue(val, _ColumnType.json, compact: false),
        style: GoogleFonts.jetBrainsMono(
          fontSize: 11,
          color: AppColors.textSecondary,
          height: 1.5,
        ),
      );
    }
  }

  String _formatValue(dynamic val, _ColumnType colType, {bool compact = true}) {
    if (val == null) return 'NULL';

    if (colType == _ColumnType.timestamp) {
      DateTime? dt;
      final numVal = val is num
          ? val.toDouble()
          : double.tryParse(val.toString());

      if (numVal != null) {
        // Auto-detect precision based on magnitude
        if (numVal > 1e16) {
          // nanoseconds
          dt = DateTime.fromMillisecondsSinceEpoch(numVal ~/ 1e6);
        } else if (numVal > 1e14) {
          // microseconds
          dt = DateTime.fromMillisecondsSinceEpoch(numVal ~/ 1e3);
        } else if (numVal > 1e11) {
          // milliseconds
          dt = DateTime.fromMillisecondsSinceEpoch(numVal.toInt());
        } else {
          // seconds
          dt = DateTime.fromMillisecondsSinceEpoch((numVal * 1000).toInt());
        }
      } else {
        dt = DateTime.tryParse(val.toString());
      }
      if (dt != null) {
        final loc = dt.toLocal();
        return '${loc.year}-${loc.month.toString().padLeft(2, '0')}-${loc.day.toString().padLeft(2, '0')} '
            '${loc.hour.toString().padLeft(2, '0')}:${loc.minute.toString().padLeft(2, '0')}:${loc.second.toString().padLeft(2, '0')}';
      }
    }

    if (val is double) {
      if (val == val.roundToDouble() && val.abs() < 1e15) {
        return _formatNumber(val.toInt());
      }
      return val.toStringAsFixed(4);
    }
    if (val is int) return _formatNumber(val);

    if (colType == _ColumnType.json) {
      try {
        final encoder = compact
            ? const JsonEncoder()
            : const JsonEncoder.withIndent('  ');
        final s = encoder.convert(val);
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

// Isolate workflow for processing SQL rows
class _ProcessRowsArgs {
  final List<String> columns;
  final List<Map<String, dynamic>> rows;
  const _ProcessRowsArgs({required this.columns, required this.rows});
}

class _ProcessRowsResult {
  final Map<String, _ColumnType> columnTypes;
  final List<Map<String, dynamic>> processedRows;
  const _ProcessRowsResult({
    required this.columnTypes,
    required this.processedRows,
  });
}

class _ProcessRowsTask {
  static _ProcessRowsResult process(_ProcessRowsArgs args) {
    final types = <String, _ColumnType>{};

    // 1. Detect Types
    for (final col in args.columns) {
      var detected = _ColumnType.string;
      for (final row in args.rows.take(30)) {
        final val = row[col];
        if (val == null) continue;
        if (val is Map || val is List) {
          detected = _ColumnType.json;
        } else if (val is num) {
          final colLower = col.toLowerCase();
          if ((colLower.contains('time') || colLower.contains('date')) &&
              val > 1000000000) {
            detected = _ColumnType.timestamp;
          } else {
            detected = _ColumnType.number;
          }
        } else if (val is bool) {
          detected = _ColumnType.boolean;
        } else {
          final s = val.toString();
          final parsedDouble = double.tryParse(s);
          if (parsedDouble != null) {
            final colLower = col.toLowerCase();
            if ((colLower.contains('time') ||
                    colLower.contains('date') ||
                    colLower.contains('timestamp')) &&
                parsedDouble > 1000000000) {
              detected = _ColumnType.timestamp;
            } else {
              detected = _ColumnType.number;
            }
          } else if (_SqlResultsTableState._looksLikeTimestamp(s)) {
            detected = _ColumnType.timestamp;
          } else if (_SqlResultsTableState._looksLikeJson(s)) {
            detected = _ColumnType.json;
          } else {
            detected = _ColumnType.string;
          }
        }
        break; // use first non-null value
      }
      types[col] = detected;
    }

    // 2. Pre-process JSON rows
    final processedRows = <Map<String, dynamic>>[];
    for (var i = 0; i < args.rows.length; i++) {
      final rawRow = args.rows[i];
      final processedRow = Map<String, dynamic>.from(rawRow); // Clone to mutate

      for (final col in args.columns) {
        if (types[col] == _ColumnType.json) {
          final val = rawRow[col];
          if (val is String) {
            try {
              // Pre-decode JSON strings so the UI thread doesn't have to
              processedRow[col] = jsonDecode(val);
            } catch (_) {
              // If decode fails, leave it as string
            }
          }
        }
      }
      processedRows.add(processedRow);
    }

    return _ProcessRowsResult(columnTypes: types, processedRows: processedRows);
  }
}
