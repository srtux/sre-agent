import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../theme/app_theme.dart';
import '../../application/dashboard_notifiers.dart';
import '../../domain/models.dart';

class DashboardViewPage extends ConsumerStatefulWidget {
  final String dashboardId;

  const DashboardViewPage({super.key, required this.dashboardId});

  @override
  ConsumerState<DashboardViewPage> createState() => _DashboardViewPageState();
}

class _DashboardViewPageState extends ConsumerState<DashboardViewPage> {
  bool _editMode = false;
  TimeRangePreset _selectedTimeRange = TimeRangePreset.oneHour;
  bool _showFilters = false;

  @override
  Widget build(BuildContext context) {
    final dashboardAsync = ref.watch(dashboardDetailProvider(widget.dashboardId));

    return Scaffold(
      backgroundColor: AppColors.backgroundDark,
      appBar: _buildAppBar(dashboardAsync),
      body: dashboardAsync.when(
        data: (dashboard) => _buildBody(dashboard),
        loading: () => const Center(
          child: CircularProgressIndicator(color: AppColors.primaryTeal),
        ),
        error: (err, stack) => _buildError(err),
      ),
    );
  }

  PreferredSizeWidget _buildAppBar(AsyncValue<Dashboard> dashboardAsync) {
    final dashboard = dashboardAsync.value;


    return AppBar(
      backgroundColor: AppColors.backgroundCard,
      elevation: 0,
      title: Text(
        dashboard?.displayName ?? 'Loading...',
        style: const TextStyle(fontSize: 18),
      ),
      actions: [
        PopupMenuButton<TimeRangePreset>(
          tooltip: 'Time range',
          icon: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.schedule, size: 18),
              const SizedBox(width: 4),
              Text(
                _selectedTimeRange.displayName,
                style: const TextStyle(fontSize: 13),
              ),
            ],
          ),
          onSelected: (preset) {
            setState(() => _selectedTimeRange = preset);
          },
          itemBuilder: (_) => TimeRangePreset.values
              .where((p) => p != TimeRangePreset.custom)
              .map((p) => PopupMenuItem(
                    value: p,
                    child: Text(p.displayName),
                  ))
              .toList(),
        ),
        IconButton(
          icon: Icon(
            Icons.filter_list,
            color: _showFilters ? AppColors.primaryCyan : null,
          ),
          tooltip: 'Toggle filters',
          onPressed: () => setState(() => _showFilters = !_showFilters),
        ),
        if (dashboard?.source == DashboardSource.local)
          IconButton(
            icon: Icon(
              _editMode ? Icons.check : Icons.edit,
              color: _editMode ? AppColors.primaryCyan : null,
            ),
            tooltip: _editMode ? 'Done editing' : 'Edit dashboard',
            onPressed: () => setState(() => _editMode = !_editMode),
          ),
        PopupMenuButton<String>(
          onSelected: (action) => _handleMenuAction(action, dashboard),
          itemBuilder: (_) => [
            const PopupMenuItem(value: 'refresh', child: Text('Refresh')),
            const PopupMenuItem(value: 'duplicate', child: Text('Duplicate')),
            if (dashboard?.source == DashboardSource.local)
              const PopupMenuItem(
                value: 'delete',
                child: Text('Delete', style: TextStyle(color: Colors.redAccent)),
              ),
          ],
        ),
      ],
    );
  }

  Widget _buildError(Object err) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.dashboard_outlined, size: 64, color: Colors.white24),
          const SizedBox(height: 16),
          Text(
            'Failed to load dashboard: $err',
            style: const TextStyle(color: Colors.white54, fontSize: 16),
          ),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: () => ref.invalidate(dashboardDetailProvider(widget.dashboardId)),
            child: const Text('Retry'),
          ),
        ],
      ),
    );
  }

  Widget _buildBody(Dashboard dashboard) {
    return Column(
      children: [
        if (_showFilters) _buildFilterBar(dashboard),
        Expanded(child: _buildGrid(dashboard)),
        if (_editMode) _buildEditToolbar(dashboard),
      ],
    );
  }

  Widget _buildFilterBar(Dashboard dashboard) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      color: AppColors.backgroundCard.withValues(alpha: 0.5),
      child: Row(
        children: [
          const Icon(Icons.filter_alt_outlined, size: 16, color: Colors.white54),
          const SizedBox(width: 8),
          if (dashboard.filters.isEmpty)
            const Text('No filters configured', style: TextStyle(color: Colors.white38, fontSize: 13))
          else
            ...dashboard.filters.map((f) => Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: Chip(
                    label: Text('${f.key} ${f.operator} ${f.value}',
                        style: const TextStyle(color: Colors.white70, fontSize: 12)),
                    backgroundColor: AppColors.backgroundDark,
                    side: BorderSide(color: Colors.white.withValues(alpha: 0.15)),
                  ),
                )),
          const Spacer(),
          if (dashboard.variables.isNotEmpty)
            ...dashboard.variables.map((v) => Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: Chip(
                    label: Text('\$${v.name}',
                        style: const TextStyle(color: AppColors.primaryCyan, fontSize: 12)),
                    backgroundColor: AppColors.primaryTeal.withValues(alpha: 0.15),
                    side: BorderSide(color: AppColors.primaryCyan.withValues(alpha: 0.3)),
                  ),
                )),
        ],
      ),
    );
  }

  Widget _buildGrid(Dashboard dashboard) {
    if (dashboard.panels.isEmpty) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.add_chart, size: 64, color: Colors.white.withValues(alpha: 0.2)),
            const SizedBox(height: 16),
            Text(
              'No panels yet',
              style: TextStyle(color: Colors.white.withValues(alpha: 0.4), fontSize: 16),
            ),
            if (_editMode) ...[
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: () => _showAddPanelDialog(context, dashboard),
                icon: const Icon(Icons.add),
                label: const Text('Add Panel'),
                style: FilledButton.styleFrom(backgroundColor: AppColors.primaryTeal),
              ),
            ],
          ],
        ),
      );
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        final gridWidth = constraints.maxWidth - 32;
        final cellWidth = gridWidth / dashboard.gridColumns;
        const cellHeight = 60.0;

        double maxBottom = 0;
        for (final panel in dashboard.panels) {
          final bottom = (panel.gridPosition.y + panel.gridPosition.height) * cellHeight;
          if (bottom > maxBottom) maxBottom = bottom;
        }

        return SingleChildScrollView(
          padding: const EdgeInsets.all(16),
          child: SizedBox(
            width: gridWidth,
            height: maxBottom + 80,
            child: CustomPaint(
              painter: _editMode ? _GridPainter(cellWidth, cellHeight) : null,
              child: Stack(
                children: dashboard.panels.map((panel) {
                  final left = panel.gridPosition.x * cellWidth;
                  final top = panel.gridPosition.y * cellHeight;
                  final width = panel.gridPosition.width * cellWidth;
                  final height = panel.gridPosition.height * cellHeight;

                  return Positioned(
                    left: left,
                    top: top,
                    width: width - 4,
                    height: height - 4,
                    child: _DashboardPanelCard(
                      panel: panel,
                      editMode: _editMode,
                      onDelete: () => _deletePanel(dashboard.id, panel.id),
                    ),
                  );
                }).toList(),
              ),
            ),
          ),
        );
      },
    );
  }

  Widget _buildEditToolbar(Dashboard dashboard) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: AppColors.backgroundCard,
        border: Border(top: BorderSide(color: Colors.white.withValues(alpha: 0.1))),
      ),
      child: Row(
        children: [
          FilledButton.icon(
            onPressed: () => _showAddPanelDialog(context, dashboard),
            icon: const Icon(Icons.add, size: 18),
            label: const Text('Add Panel'),
            style: FilledButton.styleFrom(backgroundColor: AppColors.primaryTeal),
          ),
          const Spacer(),
          Text(
            '${dashboard.panels.length} panels',
            style: const TextStyle(color: Colors.white38, fontSize: 13),
          ),
        ],
      ),
    );
  }

  void _deletePanel(String dashboardId, String panelId) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.backgroundCard,
        title: const Text('Remove Panel', style: TextStyle(color: Colors.white)),
        content: const Text('Are you sure you want to remove this panel?', style: TextStyle(color: Colors.white70)),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel', style: TextStyle(color: Colors.white54)),
          ),
          FilledButton(
            onPressed: () {
              Navigator.of(ctx).pop();
              ref.read(dashboardDetailProvider(dashboardId).notifier).removePanel(panelId);
            },
            style: FilledButton.styleFrom(backgroundColor: Colors.redAccent),
            child: const Text('Remove'),
          ),
        ],
      ),
    );
  }

  void _showAddPanelDialog(BuildContext context, Dashboard dashboard) {
    final titleController = TextEditingController();
    var selectedType = PanelType.timeSeries;

    showDialog(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDialogState) => AlertDialog(
          backgroundColor: AppColors.backgroundCard,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: const Text('Add Panel', style: TextStyle(color: Colors.white)),
          content: SizedBox(
            width: 400,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                TextField(
                  controller: titleController,
                  autofocus: true,
                  style: const TextStyle(color: Colors.white),
                  decoration: InputDecoration(
                    labelText: 'Panel Title',
                    labelStyle: TextStyle(color: Colors.white.withValues(alpha: 0.5)),
                    enabledBorder: OutlineInputBorder(
                      borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.2)),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderSide: const BorderSide(color: AppColors.primaryCyan),
                      borderRadius: BorderRadius.circular(8),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                const Text('Panel Type', style: TextStyle(color: Colors.white70, fontSize: 13)),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: PanelType.values.map((type) {
                    final isSelected = type == selectedType;
                    return ChoiceChip(
                      label: Text(type.displayName),
                      selected: isSelected,
                      onSelected: (_) {
                        setDialogState(() => selectedType = type);
                      },
                      selectedColor: AppColors.primaryTeal.withValues(alpha: 0.3),
                      labelStyle: TextStyle(
                        color: isSelected ? AppColors.primaryCyan : Colors.white70,
                        fontSize: 12,
                      ),
                      backgroundColor: AppColors.backgroundDark,
                      side: BorderSide(
                        color: isSelected ? AppColors.primaryCyan.withValues(alpha: 0.5) : Colors.white24,
                      ),
                    );
                  }).toList(),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Cancel', style: TextStyle(color: Colors.white54)),
            ),
            FilledButton(
              onPressed: () {
                if (titleController.text.trim().isEmpty) return;
                Navigator.of(ctx).pop();
                ref.read(dashboardDetailProvider(dashboard.id).notifier).addPanel({
                  'title': titleController.text.trim(),
                  'type': selectedType.name, // Fixed to use name for JSON
                });
              },
              style: FilledButton.styleFrom(backgroundColor: AppColors.primaryTeal),
              child: const Text('Add'),
            ),
          ],
        ),
      ),
    );
  }

  void _handleMenuAction(String action, Dashboard? dashboard) {
    if (dashboard == null) return;

    switch (action) {
      case 'refresh':
        ref.invalidate(dashboardDetailProvider(widget.dashboardId));
        break;
      case 'delete':
        showDialog(
          context: context,
          builder: (ctx) => AlertDialog(
            backgroundColor: AppColors.backgroundCard,
            title: const Text('Delete Dashboard', style: TextStyle(color: Colors.white)),
            content: Text(
              'Are you sure you want to delete "${dashboard.displayName}"?',
              style: const TextStyle(color: Colors.white70),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(ctx).pop(),
                child: const Text('Cancel', style: TextStyle(color: Colors.white54)),
              ),
              FilledButton(
                onPressed: () async {
                  Navigator.of(ctx).pop();
                  await ref.read(dashboardsProvider().notifier).deleteDashboard(dashboard.id);
                  if (!mounted) return;
                  Navigator.of(context).pop();
                },
                style: FilledButton.styleFrom(backgroundColor: Colors.redAccent),
                child: const Text('Delete'),
              ),
            ],
          ),
        );
        break;
    }
  }
}

class _DashboardPanelCard extends StatelessWidget {
  final DashboardPanel panel;
  final bool editMode;
  final VoidCallback onDelete;

  const _DashboardPanelCard({
    required this.panel,
    required this.editMode,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.backgroundCard,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: editMode
              ? AppColors.primaryCyan.withValues(alpha: 0.3)
              : Colors.white.withValues(alpha: 0.08),
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.2),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
              border: Border(bottom: BorderSide(color: Colors.white.withValues(alpha: 0.06))),
            ),
            child: Row(
              children: [
                Icon(_getPanelIcon(), size: 14, color: AppColors.primaryCyan),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    panel.title,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                if (editMode)
                  InkWell(
                    onTap: onDelete,
                    child: const Icon(Icons.close, size: 16, color: Colors.white38),
                  ),
              ],
            ),
          ),
          Expanded(child: Center(child: _buildPanelContent())),
        ],
      ),
    );
  }

  IconData _getPanelIcon() {
    switch (panel.type) {
      case PanelType.timeSeries: return Icons.show_chart;
      case PanelType.gauge: return Icons.speed;
      case PanelType.stat: return Icons.numbers;
      case PanelType.table: return Icons.table_chart;
      case PanelType.logs: return Icons.subject;
      case PanelType.traces: return Icons.timeline;
      case PanelType.pie: return Icons.pie_chart;
      case PanelType.heatmap: return Icons.grid_on;
      case PanelType.bar: return Icons.bar_chart;
      case PanelType.text: return Icons.text_fields;
      case PanelType.alertChart: return Icons.warning_amber;
      case PanelType.scorecard: return Icons.score;
      case PanelType.scatter: return Icons.scatter_plot;
      case PanelType.treemap: return Icons.account_tree;
      case PanelType.errorReporting: return Icons.error_outline;
      case PanelType.incidentList: return Icons.list_alt;
    }
  }

  Widget _buildPanelContent() {
    if (panel.type == PanelType.text && panel.textContent != null) {
      return Padding(
        padding: const EdgeInsets.all(12),
        child: Text(
          panel.textContent!['content'] as String? ?? '',
          style: const TextStyle(color: Colors.white70, fontSize: 13),
        ),
      );
    }

    if (panel.type == PanelType.stat) {
      return Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Text(
            '--',
            style: TextStyle(
              color: AppColors.primaryCyan,
              fontSize: 32,
              fontWeight: FontWeight.bold,
            ),
          ),
          if (panel.unit != null)
            Text(
              panel.unit!,
              style: const TextStyle(color: Colors.white38, fontSize: 12),
            ),
        ],
      );
    }

    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(_getPanelIcon(), size: 28, color: Colors.white.withValues(alpha: 0.15)),
        const SizedBox(height: 4),
        Text(
          panel.type.displayName,
          style: TextStyle(color: Colors.white.withValues(alpha: 0.25), fontSize: 11),
        ),
        if (panel.queries.isEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(
              'No data source configured',
              style: TextStyle(color: Colors.white.withValues(alpha: 0.15), fontSize: 10),
            ),
          ),
      ],
    );
  }
}

class _GridPainter extends CustomPainter {
  final double cellWidth;
  final double cellHeight;

  _GridPainter(this.cellWidth, this.cellHeight);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white.withValues(alpha: 0.04)
      ..strokeWidth = 0.5;

    for (double x = 0; x <= size.width; x += cellWidth) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }

    for (double y = 0; y <= size.height; y += cellHeight) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }
  }

  @override
  bool shouldRepaint(covariant _GridPainter oldDelegate) =>
      cellWidth != oldDelegate.cellWidth || cellHeight != oldDelegate.cellHeight;
}
