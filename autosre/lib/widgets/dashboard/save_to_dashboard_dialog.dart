import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../models/dashboard_models.dart';
import '../../services/dashboard_service.dart';
import '../../theme/app_theme.dart';

/// Dialog for saving explorer results as a dashboard panel.
///
/// Supports two modes:
/// - Create New: Creates a new dashboard with the panel
/// - Add to Existing: Adds the panel to an existing dashboard
///
/// Usage:
/// ```dart
/// SaveToDashboardDialog.show(
///   context: context,
///   panelTitle: 'CPU Usage',
///   panelType: PanelType.timeSeries,
///   panelData: {'queries': [...]},
/// );
/// ```
class SaveToDashboardDialog extends StatefulWidget {
  final String panelTitle;
  final PanelType panelType;
  final Map<String, dynamic> panelData;

  const SaveToDashboardDialog({
    super.key,
    required this.panelTitle,
    this.panelType = PanelType.timeSeries,
    this.panelData = const {},
  });

  /// Show the save to dashboard dialog.
  static Future<bool?> show({
    required BuildContext context,
    required String panelTitle,
    PanelType panelType = PanelType.timeSeries,
    Map<String, dynamic> panelData = const {},
  }) {
    return showDialog<bool>(
      context: context,
      builder: (_) => ChangeNotifierProvider.value(
        value: context.read<DashboardApiService>(),
        child: SaveToDashboardDialog(
          panelTitle: panelTitle,
          panelType: panelType,
          panelData: panelData,
        ),
      ),
    );
  }

  @override
  State<SaveToDashboardDialog> createState() => _SaveToDashboardDialogState();
}

class _SaveToDashboardDialogState extends State<SaveToDashboardDialog> {
  bool _createNew = true;
  final _titleController = TextEditingController();
  final _dashboardNameController = TextEditingController();
  final _searchController = TextEditingController();
  String? _selectedDashboardId;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _titleController.text = widget.panelTitle;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<DashboardApiService>().fetchDashboards();
    });
  }

  @override
  void dispose() {
    _titleController.dispose();
    _dashboardNameController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: AppColors.backgroundCard,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      title: Row(
        children: [
          const Icon(Icons.dashboard_customize,
              color: AppColors.primaryCyan, size: 22),
          const SizedBox(width: 8),
          const Text('Save to Dashboard',
              style: TextStyle(color: Colors.white, fontSize: 18)),
        ],
      ),
      content: SizedBox(
        width: 480,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Panel info
              _buildPanelInfo(),
              const SizedBox(height: 16),

              // Panel title
              TextField(
                controller: _titleController,
                style: const TextStyle(color: Colors.white),
                decoration: _inputDecoration('Panel Title'),
              ),
              const SizedBox(height: 20),

              // Mode toggle
              _buildModeToggle(),
              const SizedBox(height: 16),

              // Mode-specific content
              if (_createNew)
                _buildCreateNewSection()
              else
                _buildExistingSection(),
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _saving ? null : () => Navigator.of(context).pop(false),
          child:
              const Text('Cancel', style: TextStyle(color: Colors.white54)),
        ),
        FilledButton(
          onPressed: _saving ? null : _save,
          style:
              FilledButton.styleFrom(backgroundColor: AppColors.primaryTeal),
          child: _saving
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: Colors.white,
                  ),
                )
              : const Text('Save'),
        ),
      ],
    );
  }

  Widget _buildPanelInfo() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.backgroundDark,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: AppColors.primaryTeal.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(
              _getPanelIcon(widget.panelType),
              color: AppColors.primaryCyan,
              size: 20,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  widget.panelType.displayName,
                  style: const TextStyle(
                    color: AppColors.primaryCyan,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  widget.panelTitle,
                  style: const TextStyle(color: Colors.white70, fontSize: 13),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildModeToggle() {
    return Row(
      children: [
        Expanded(
          child: _buildToggleOption(
            'Create New',
            Icons.add_circle_outline,
            _createNew,
            () => setState(() => _createNew = true),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _buildToggleOption(
            'Add to Existing',
            Icons.dashboard,
            !_createNew,
            () => setState(() => _createNew = false),
          ),
        ),
      ],
    );
  }

  Widget _buildToggleOption(
      String label, IconData icon, bool selected, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 12),
        decoration: BoxDecoration(
          color: selected
              ? AppColors.primaryTeal.withValues(alpha: 0.15)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: selected
                ? AppColors.primaryCyan.withValues(alpha: 0.5)
                : Colors.white.withValues(alpha: 0.15),
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon,
                size: 18,
                color: selected ? AppColors.primaryCyan : Colors.white38),
            const SizedBox(width: 8),
            Text(
              label,
              style: TextStyle(
                color: selected ? AppColors.primaryCyan : Colors.white54,
                fontSize: 13,
                fontWeight: selected ? FontWeight.w600 : FontWeight.normal,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCreateNewSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Dashboard Name',
            style: TextStyle(color: Colors.white70, fontSize: 13)),
        const SizedBox(height: 8),
        TextField(
          controller: _dashboardNameController,
          style: const TextStyle(color: Colors.white),
          decoration: _inputDecoration('Enter dashboard name'),
        ),
      ],
    );
  }

  Widget _buildExistingSection() {
    return Consumer<DashboardApiService>(
      builder: (context, service, _) {
        final dashboards = service.dashboards
            .where((d) => d.source == DashboardSource.local)
            .where((d) {
          final query = _searchController.text.toLowerCase();
          return query.isEmpty ||
              d.displayName.toLowerCase().contains(query);
        }).toList();

        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: _searchController,
              onChanged: (_) => setState(() {}),
              style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(
                hintText: 'Search dashboards...',
                hintStyle:
                    TextStyle(color: Colors.white.withValues(alpha: 0.3)),
                prefixIcon: Icon(Icons.search,
                    size: 18, color: Colors.white.withValues(alpha: 0.3)),
                filled: true,
                fillColor: AppColors.backgroundDark,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: BorderSide.none,
                ),
                contentPadding: const EdgeInsets.symmetric(vertical: 10),
              ),
            ),
            const SizedBox(height: 12),
            if (service.isLoading)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: CircularProgressIndicator(
                      color: AppColors.primaryTeal, strokeWidth: 2),
                ),
              )
            else if (dashboards.isEmpty)
              Padding(
                padding: const EdgeInsets.all(16),
                child: Center(
                  child: Text(
                    'No local dashboards found',
                    style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.4),
                        fontSize: 13),
                  ),
                ),
              )
            else
              ConstrainedBox(
                constraints: const BoxConstraints(maxHeight: 200),
                child: ListView.builder(
                  shrinkWrap: true,
                  itemCount: dashboards.length,
                  itemBuilder: (context, index) {
                    final d = dashboards[index];
                    final selected = _selectedDashboardId == d.id;
                    return ListTile(
                      dense: true,
                      selected: selected,
                      selectedTileColor:
                          AppColors.primaryTeal.withValues(alpha: 0.15),
                      shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8)),
                      leading: Icon(
                        Icons.dashboard,
                        size: 18,
                        color: selected
                            ? AppColors.primaryCyan
                            : Colors.white38,
                      ),
                      title: Text(
                        d.displayName,
                        style: TextStyle(
                          color:
                              selected ? AppColors.primaryCyan : Colors.white,
                          fontSize: 14,
                        ),
                      ),
                      subtitle: Text(
                        '${d.panelCount} panels',
                        style: const TextStyle(
                            color: Colors.white38, fontSize: 12),
                      ),
                      trailing: selected
                          ? const Icon(Icons.check_circle,
                              color: AppColors.primaryCyan, size: 18)
                          : null,
                      onTap: () {
                        setState(() => _selectedDashboardId = d.id);
                      },
                    );
                  },
                ),
              ),
          ],
        );
      },
    );
  }

  InputDecoration _inputDecoration(String label) {
    return InputDecoration(
      labelText: label,
      labelStyle: TextStyle(color: Colors.white.withValues(alpha: 0.5)),
      enabledBorder: OutlineInputBorder(
        borderSide:
            BorderSide(color: Colors.white.withValues(alpha: 0.2)),
        borderRadius: BorderRadius.circular(8),
      ),
      focusedBorder: OutlineInputBorder(
        borderSide: const BorderSide(color: AppColors.primaryCyan),
        borderRadius: BorderRadius.circular(8),
      ),
    );
  }

  IconData _getPanelIcon(PanelType type) {
    switch (type) {
      case PanelType.timeSeries:
        return Icons.show_chart;
      case PanelType.gauge:
        return Icons.speed;
      case PanelType.stat:
        return Icons.numbers;
      case PanelType.table:
        return Icons.table_chart;
      case PanelType.logs:
        return Icons.subject;
      case PanelType.traces:
        return Icons.timeline;
      case PanelType.pie:
        return Icons.pie_chart;
      case PanelType.heatmap:
        return Icons.grid_on;
      case PanelType.bar:
        return Icons.bar_chart;
      case PanelType.text:
        return Icons.text_fields;
      case PanelType.alertChart:
        return Icons.warning_amber;
      case PanelType.scorecard:
        return Icons.score;
      case PanelType.scatter:
        return Icons.scatter_plot;
      case PanelType.treemap:
        return Icons.account_tree;
      case PanelType.errorReporting:
        return Icons.error_outline;
      case PanelType.incidentList:
        return Icons.list_alt;
    }
  }

  Future<void> _save() async {
    final title = _titleController.text.trim();
    if (title.isEmpty) return;

    setState(() => _saving = true);

    final service = context.read<DashboardApiService>();
    final panelData = {
      ...widget.panelData,
      'title': title,
      'type': widget.panelType.value,
    };

    try {
      if (_createNew) {
        final dashName = _dashboardNameController.text.trim();
        if (dashName.isEmpty) {
          setState(() => _saving = false);
          return;
        }
        final dashboard = await service.createDashboard(
          displayName: dashName,
          panels: [panelData],
        );
        if (dashboard != null && mounted) {
          Navigator.of(context).pop(true);
        }
      } else {
        if (_selectedDashboardId == null) {
          setState(() => _saving = false);
          return;
        }
        final result =
            await service.addPanel(_selectedDashboardId!, panelData);
        if (result != null && mounted) {
          Navigator.of(context).pop(true);
        }
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }
}
