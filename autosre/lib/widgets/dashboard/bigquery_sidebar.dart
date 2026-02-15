import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';

import '../../services/explorer_query_service.dart';
import '../../theme/app_theme.dart';
import '../common/shimmer_loading.dart';

class BigQuerySidebar extends StatefulWidget {
  final Function(String)? onInsertTable;
  final Function(String)? onInsertColumn;

  const BigQuerySidebar({
    super.key,
    this.onInsertTable,
    this.onInsertColumn,
  });

  @override
  State<BigQuerySidebar> createState() => _BigQuerySidebarState();
}

class _BigQuerySidebarState extends State<BigQuerySidebar> {
  bool _loadingDatasets = true;
  List<String> _datasets = [];
  String? _selectedDataset;

  bool _loadingTables = false;
  List<String> _tables = [];

  // Cache for schemas — keyed by "datasetId.tableId" to avoid cross-dataset collisions
  final Map<String, List<Map<String, dynamic>>> _tableSchemas = {};
  final Set<String> _fetchingSchemas = {};

  String _schemaCacheKey(String tableId) => '${_selectedDataset ?? ""}.$tableId';

  @override
  void initState() {
    super.initState();
    _fetchDatasets();
  }

  Future<void> _fetchDatasets() async {
    setState(() {
      _loadingDatasets = true;
    });
    final explorer = context.read<ExplorerQueryService>();
    final datasets = await explorer.getDatasets();
    if (mounted) {
      setState(() {
        _datasets = datasets;
        _loadingDatasets = false;
        if (datasets.isNotEmpty) {
          _selectedDataset = datasets.first;
          _fetchTables(_selectedDataset!);
        }
      });
    }
  }

  Future<void> _fetchTables(String datasetId) async {
    setState(() {
      _loadingTables = true;
      _tables = [];
    });
    final explorer = context.read<ExplorerQueryService>();
    final tables = await explorer.getTables(datasetId: datasetId);
    if (mounted && _selectedDataset == datasetId) {
      setState(() {
        _tables = tables;
        _loadingTables = false;
      });
    }
  }

  Future<void> _fetchSchema(String tableId) async {
    final cacheKey = _schemaCacheKey(tableId);
    if (_selectedDataset == null ||
        _tableSchemas.containsKey(cacheKey) ||
        _fetchingSchemas.contains(cacheKey)) {
      return;
    }
    setState(() {
      _fetchingSchemas.add(cacheKey);
    });
    final explorer = context.read<ExplorerQueryService>();
    final schema = await explorer.getTableSchema(
      datasetId: _selectedDataset!,
      tableId: tableId,
    );
    if (mounted) {
      setState(() {
        _tableSchemas[cacheKey] = schema;
        _fetchingSchemas.remove(cacheKey);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 280,
      decoration: BoxDecoration(
        color: AppColors.backgroundCard.withValues(alpha: 0.3),
        border: Border(
          right: BorderSide(
            color: AppColors.surfaceBorder.withValues(alpha: 0.3),
          ),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _buildHeader(),
          _buildDatasetSelector(),
          const Divider(height: 1, color: AppColors.surfaceBorder),
          Expanded(
            child: _buildTablesList(),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: Row(
        children: [
          const Icon(Icons.storage_rounded, size: 16, color: AppColors.warning),
          const SizedBox(width: 8),
          const Text(
            'Data Explorer',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ),
          const Spacer(),
          IconButton(
            icon: const Icon(Icons.refresh_rounded, size: 14),
            color: AppColors.textMuted,
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
            onPressed: _fetchDatasets,
            tooltip: 'Refresh Datasets',
          ),
        ],
      ),
    );
  }

  Widget _buildDatasetSelector() {
    if (_loadingDatasets) {
      return const Padding(
        padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: SizedBox(height: 32, child: ShimmerLoading()),
      );
    }
    if (_datasets.isEmpty) {
      return const Padding(
        padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: Text(
          'No datasets found in project.',
          style: TextStyle(fontSize: 11, color: AppColors.textMuted),
        ),
      );
    }

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      child: Container(
        height: 32,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        decoration: BoxDecoration(
          color: AppColors.backgroundDark,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: AppColors.surfaceBorder),
        ),
        child: DropdownButtonHideUnderline(
          child: DropdownButton<String>(
            value: _selectedDataset,
            isExpanded: true,
            icon: const Icon(Icons.arrow_drop_down, color: AppColors.textMuted),
            dropdownColor: AppColors.backgroundDark,
            style: const TextStyle(
              fontSize: 12,
              color: AppColors.textPrimary,
            ),
            items: _datasets.map((dataset) {
              return DropdownMenuItem(
                value: dataset,
                child: Text(dataset, maxLines: 1, overflow: TextOverflow.ellipsis),
              );
            }).toList(),
            onChanged: (value) {
              if (value != null && value != _selectedDataset) {
                setState(() {
                  _selectedDataset = value;
                });
                _fetchTables(value);
              }
            },
          ),
        ),
      ),
    );
  }

  Widget _buildTablesList() {
    if (_loadingDatasets) return const SizedBox.shrink();
    if (_loadingTables) {
      return ListView.builder(
        padding: const EdgeInsets.symmetric(vertical: 8),
        itemCount: 5,
        itemBuilder: (context, index) => const Padding(
          padding: EdgeInsets.symmetric(horizontal: 16, vertical: 6),
          child: SizedBox(height: 24, child: ShimmerLoading()),
        ),
      );
    }
    if (_tables.isEmpty) {
      return Center(
        child: Text(
          _selectedDataset == null ? 'Select a dataset' : 'No tables found.',
          style: const TextStyle(fontSize: 11, color: AppColors.textMuted),
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.symmetric(vertical: 4),
      itemCount: _tables.length,
      itemBuilder: (context, index) {
        final tableId = _tables[index];
        return Theme(
          data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
          child: ExpansionTile(
            key: PageStorageKey('bq_sidebar_schema_${_selectedDataset}_$tableId'),
            tilePadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 0),
            childrenPadding: EdgeInsets.zero,
            minTileHeight: 36.0,
            onExpansionChanged: (expanded) {
              if (expanded) {
                _fetchSchema(tableId);
              }
            },
            leading: const Icon(Icons.table_chart_rounded, size: 14, color: AppColors.primaryCyan),
            title: Row(
              children: [
                Expanded(
                  child: Text(
                    tableId,
                    style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (widget.onInsertTable != null)
                  IconButton(
                    icon: const Icon(Icons.input_rounded, size: 14),
                    color: AppColors.textMuted,
                    padding: EdgeInsets.zero,
                    constraints: const BoxConstraints(),
                    tooltip: 'Insert table name',
                    onPressed: () => widget.onInsertTable!('`$_selectedDataset.$tableId`'),
                  ),
              ],
            ),
            children: [
              _buildSchemaView(tableId),
            ],
          ),
        );
      },
    );
  }

  Widget _buildSchemaView(String tableId) {
    final cacheKey = _schemaCacheKey(tableId);
    if (_fetchingSchemas.contains(cacheKey)) {
      return const Padding(
        padding: EdgeInsets.all(16),
        child: Center(child: SizedBox(height: 20, child: ShimmerLoading())),
      );
    }
    final schema = _tableSchemas[cacheKey];
    if (schema == null) {
      return const Padding(
        padding: EdgeInsets.all(16),
        child: Center(
          child: Text(
            'Schema unavailable',
            style: TextStyle(fontSize: 11, color: AppColors.textMuted),
          ),
        ),
      );
    }
    if (schema.isEmpty) {
      return const Padding(
        padding: EdgeInsets.all(16),
        child: Center(
          child: Text(
            'No columns',
            style: TextStyle(fontSize: 11, color: AppColors.textMuted),
          ),
        ),
      );
    }

    return Container(
      color: AppColors.backgroundDark.withValues(alpha: 0.5),
      child: _buildFieldList(schema, depth: 0),
    );
  }

  /// Recursively builds the field list, supporting nested RECORD fields.
  Widget _buildFieldList(List<Map<String, dynamic>> fields, {required int depth}) {
    return ListView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: fields.length,
      itemBuilder: (context, index) {
        final column = fields[index];
        return _buildFieldItem(column, depth: depth);
      },
    );
  }

  Widget _buildFieldItem(Map<String, dynamic> column, {required int depth}) {
    final name = column['name']?.toString() ?? 'Unknown';
    final type = column['type']?.toString() ?? 'UNKNOWN';
    final mode = column['mode']?.toString() ?? 'NULLABLE';
    final description = column['description']?.toString() ?? '';
    final nestedFields = column['fields'] as List? ?? [];
    final isRecord = type == 'RECORD' || type == 'STRUCT';
    final leftPadding = 24.0 + (depth * 16.0);

    if (isRecord && nestedFields.isNotEmpty) {
      // RECORD fields are expandable to show nested fields
      return Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          tilePadding: EdgeInsets.only(left: leftPadding, right: 16),
          childrenPadding: EdgeInsets.zero,
          minTileHeight: 32.0,
          leading: Icon(
            _iconForType(type),
            size: 12,
            color: _colorForType(type),
          ),
          title: _buildFieldTitle(name, type, mode, description),
          children: [
            _buildFieldList(
              nestedFields.map((f) => Map<String, dynamic>.from(f as Map)).toList(),
              depth: depth + 1,
            ),
          ],
        ),
      );
    }

    // Leaf fields
    return InkWell(
      onTap: widget.onInsertColumn != null
          ? () => widget.onInsertColumn!(name)
          : null,
      child: Tooltip(
        message: description.isNotEmpty ? description : '$name ($type)',
        waitDuration: const Duration(milliseconds: 500),
        child: Padding(
          padding: EdgeInsets.only(left: leftPadding, right: 16, top: 5, bottom: 5),
          child: Row(
            children: [
              Icon(
                _iconForType(type),
                size: 12,
                color: _colorForType(type),
              ),
              const SizedBox(width: 6),
              Expanded(
                child: _buildFieldTitle(name, type, mode, description),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildFieldTitle(String name, String type, String mode, String description) {
    return Row(
      children: [
        Expanded(
          child: Text(
            name,
            style: GoogleFonts.jetBrainsMono(
              fontSize: 11,
              color: AppColors.textSecondary,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
        const SizedBox(width: 4),
        // Mode badge for REQUIRED or REPEATED fields
        if (mode == 'REQUIRED')
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 3, vertical: 1),
            margin: const EdgeInsets.only(right: 4),
            decoration: BoxDecoration(
              color: AppColors.error.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(3),
            ),
            child: Text(
              'REQ',
              style: GoogleFonts.jetBrainsMono(
                fontSize: 7,
                fontWeight: FontWeight.w700,
                color: AppColors.error.withValues(alpha: 0.8),
              ),
            ),
          ),
        if (mode == 'REPEATED')
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 3, vertical: 1),
            margin: const EdgeInsets.only(right: 4),
            decoration: BoxDecoration(
              color: AppColors.secondaryPurple.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(3),
            ),
            child: Text(
              '[ ]',
              style: GoogleFonts.jetBrainsMono(
                fontSize: 7,
                fontWeight: FontWeight.w700,
                color: AppColors.secondaryPurple.withValues(alpha: 0.8),
              ),
            ),
          ),
        Text(
          _abbreviateType(type),
          style: GoogleFonts.jetBrainsMono(
            fontSize: 9,
            color: _colorForType(type).withValues(alpha: 0.7),
          ),
        ),
      ],
    );
  }

  /// Returns a type-specific icon for BigQuery schema field types.
  IconData _iconForType(String type) {
    switch (type.toUpperCase()) {
      case 'STRING':
      case 'BYTES':
        return Icons.text_fields_rounded;
      case 'INTEGER':
      case 'INT64':
      case 'NUMERIC':
      case 'BIGNUMERIC':
        return Icons.tag_rounded;
      case 'FLOAT':
      case 'FLOAT64':
        return Icons.tag_rounded;
      case 'BOOLEAN':
      case 'BOOL':
        return Icons.toggle_on_rounded;
      case 'TIMESTAMP':
      case 'DATE':
      case 'TIME':
      case 'DATETIME':
        return Icons.schedule_rounded;
      case 'RECORD':
      case 'STRUCT':
        return Icons.account_tree_rounded;
      case 'GEOGRAPHY':
        return Icons.map_rounded;
      case 'JSON':
        return Icons.data_object_rounded;
      default:
        return Icons.help_outline_rounded;
    }
  }

  /// Returns a type-specific color for BigQuery schema field types.
  Color _colorForType(String type) {
    switch (type.toUpperCase()) {
      case 'STRING':
      case 'BYTES':
        return AppColors.primaryCyan;
      case 'INTEGER':
      case 'INT64':
      case 'NUMERIC':
      case 'BIGNUMERIC':
      case 'FLOAT':
      case 'FLOAT64':
        return AppColors.warning;
      case 'BOOLEAN':
      case 'BOOL':
        return AppColors.success;
      case 'TIMESTAMP':
      case 'DATE':
      case 'TIME':
      case 'DATETIME':
        return AppColors.secondaryPurple;
      case 'RECORD':
      case 'STRUCT':
        return AppColors.info;
      case 'JSON':
        return AppColors.primaryTeal;
      default:
        return AppColors.textMuted;
    }
  }

  /// Abbreviates long BigQuery type names for compact display.
  String _abbreviateType(String type) {
    switch (type.toUpperCase()) {
      case 'BIGNUMERIC':
        return 'BIGNUM';
      case 'TIMESTAMP':
        return 'TSTAMP';
      case 'DATETIME':
        return 'DTIME';
      case 'GEOGRAPHY':
        return 'GEO';
      case 'FLOAT64':
        return 'FLOAT';
      case 'INT64':
        return 'INT';
      case 'BOOLEAN':
        return 'BOOL';
      default:
        return type;
    }
  }
}
