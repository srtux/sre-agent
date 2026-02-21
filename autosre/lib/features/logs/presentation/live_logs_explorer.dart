import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pluto_grid/pluto_grid.dart';
import 'package:intl/intl.dart';
import '../application/log_notifier.dart';
import '../domain/models.dart';
import '../../../theme/app_theme.dart';

class LiveLogsExplorer extends ConsumerStatefulWidget {
  const LiveLogsExplorer({super.key});

  @override
  ConsumerState<LiveLogsExplorer> createState() => _LiveLogsExplorerState();
}

class _LiveLogsExplorerState extends ConsumerState<LiveLogsExplorer> {
  PlutoGridStateManager? stateManager;
  List<PlutoRow> _cachedRows = [];
  int _lastEntryCount = -1;

  final List<PlutoColumn> columns = [
    PlutoColumn(
      title: 'Timestamp',
      field: 'timestamp',
      type: PlutoColumnType.text(),
      width: 180,
      enableEditingMode: false,
    ),
    PlutoColumn(
      title: 'Severity',
      field: 'severity',
      type: PlutoColumnType.text(),
      width: 100,
      enableEditingMode: false,
      renderer: (rendererContext) {
        final severity = rendererContext.cell.value.toString();
        final color = _getSeverityColor(severity);
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(4),
          ),
          child: Text(
            severity,
            style: TextStyle(
              color: color,
              fontWeight: FontWeight.bold,
              fontSize: 12,
            ),
          ),
        );
      },
    ),
    PlutoColumn(
      title: 'Message',
      field: 'message',
      type: PlutoColumnType.text(),
      width: 500,
      enableEditingMode: false,
    ),
    PlutoColumn(
      title: 'Resource',
      field: 'resource',
      type: PlutoColumnType.text(),
      width: 150,
      enableEditingMode: false,
    ),
  ];

  static Color _getSeverityColor(String severity) {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
        return Colors.purple;
      case 'ERROR':
        return AppColors.error;
      case 'WARNING':
        return AppColors.warning;
      case 'INFO':
        return AppColors.info;
      case 'DEBUG':
        return AppColors.textMuted;
      default:
        return AppColors.textSecondary;
    }
  }

  List<PlutoRow> _buildRows(List<LogEntry> entries) {
    return entries.map((entry) {
      return PlutoRow(
        cells: {
          'timestamp': PlutoCell(
            value: DateFormat(
              'yyyy-MM-dd HH:mm:ss.SSS',
            ).format(entry.timestamp),
          ),
          'severity': PlutoCell(value: entry.severity),
          'message': PlutoCell(value: entry.payloadPreview),
          'resource': PlutoCell(value: entry.resourceType),
        },
      );
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    // Only rebuild when loading state or entry count changes, not on every
    // state notification (e.g. selected entry changes).
    final isLoading = ref.watch(logProvider.select((s) => s.isLoading));
    final entries = ref.watch(logProvider.select((s) => s.entries));

    // Cache rows — only rebuild the list when entry count actually changes.
    if (entries.length != _lastEntryCount) {
      _cachedRows = _buildRows(entries);
      _lastEntryCount = entries.length;
    }

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: Column(
        children: [
          _buildToolbar(),
          Expanded(
            child: isLoading && entries.isEmpty
                ? const Center(child: CircularProgressIndicator())
                : PlutoGrid(
                    columns: columns,
                    rows: _cachedRows,
                    onLoaded: (PlutoGridOnLoadedEvent event) {
                      stateManager = event.stateManager;
                      stateManager?.setShowColumnFilter(true);
                    },
                    configuration: const PlutoGridConfiguration(
                      style: PlutoGridStyleConfig(
                        gridBackgroundColor: Colors.transparent,
                        rowColor: Colors.transparent,
                        columnTextStyle: TextStyle(
                          color: AppColors.textPrimary,
                          fontWeight: FontWeight.bold,
                        ),
                        cellTextStyle: TextStyle(
                          color: AppColors.textPrimary,
                          fontSize: 13,
                        ),
                        gridBorderColor: AppColors.surfaceBorder,
                      ),
                    ),
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildToolbar() {
    return Padding(
      padding: const EdgeInsets.all(8.0),
      child: Row(
        children: [
          const Icon(Icons.article_outlined, color: AppColors.primaryBlue),
          const SizedBox(width: 8),
          const Text(
            'Live Logs',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          const Spacer(),
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => ref.read(logProvider.notifier).fetchLogs(),
          ),
        ],
      ),
    );
  }
}
