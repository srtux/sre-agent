import 'package:flutter/material.dart';
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

  // Cache for schemas to avoid multiple fetches for the same table
  final Map<String, List<Map<String, dynamic>>> _tableSchemas = {};
  final Set<String> _fetchingSchemas = {};

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
    if (_selectedDataset == null || _tableSchemas.containsKey(tableId) || _fetchingSchemas.contains(tableId)) {
      return;
    }
    setState(() {
      _fetchingSchemas.add(tableId);
    });
    final explorer = context.read<ExplorerQueryService>();
    final schema = await explorer.getTableSchema(
      datasetId: _selectedDataset!,
      tableId: tableId,
    );
    if (mounted) {
      setState(() {
        _tableSchemas[tableId] = schema;
        _fetchingSchemas.remove(tableId);
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
            key: PageStorageKey('table_$tableId'),
            tilePadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 0),
            childrenPadding: EdgeInsets.zero,
            minTileHeight: 36,
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
    if (_fetchingSchemas.contains(tableId)) {
      return const Padding(
        padding: EdgeInsets.all(16),
        child: Center(child: SizedBox(height: 20, child: ShimmerLoading())),
      );
    }
    final schema = _tableSchemas[tableId];
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
      child: ListView.builder(
        shrinkWrap: true,
        physics: const NeverScrollableScrollPhysics(),
        itemCount: schema.length,
        itemBuilder: (context, index) {
          final column = schema[index];
          final name = column['name'] as String? ?? 'Unknown';
          final type = column['type'] as String? ?? 'UNKNOWN';
          return InkWell(
            onTap: widget.onInsertColumn != null
                ? () => widget.onInsertColumn!(name)
                : null,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 6),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      name,
                      style: const TextStyle(fontSize: 11, color: AppColors.textSecondary, fontFamily: 'monospace'),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  Text(
                    type,
                    style: const TextStyle(fontSize: 10, color: AppColors.textMuted, fontFamily: 'monospace'),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }
}
