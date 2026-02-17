import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../services/dashboard_template_service.dart';
import '../../theme/app_theme.dart';

/// Panel for browsing OOTB dashboard templates, provisioning dashboards,
/// and adding custom metric/log/trace panels to a selected dashboard.
class CustomDashboardPanel extends StatefulWidget {
  final DashboardTemplateService templateService;
  final VoidCallback? onClose;

  const CustomDashboardPanel({
    super.key,
    required this.templateService,
    this.onClose,
  });

  @override
  State<CustomDashboardPanel> createState() => _CustomDashboardPanelState();
}

class _CustomDashboardPanelState extends State<CustomDashboardPanel>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;

  // Add panel form state
  final _panelTitleController = TextEditingController();
  final _metricTypeController = TextEditingController();
  final _resourceTypeController = TextEditingController();
  final _logFilterController = TextEditingController();
  final _traceFilterController = TextEditingController();
  final _descriptionController = TextEditingController();
  String _panelType = 'metric'; // metric, log, trace

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
    // Load templates and dashboards on init
    widget.templateService.fetchTemplates();
    widget.templateService.fetchDashboards();
  }

  @override
  void dispose() {
    _tabController.dispose();
    _panelTitleController.dispose();
    _metricTypeController.dispose();
    _resourceTypeController.dispose();
    _logFilterController.dispose();
    _traceFilterController.dispose();
    _descriptionController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: widget.templateService,
      builder: (context, _) {
        return Container(
          decoration: BoxDecoration(
            color: AppColors.backgroundDark,
            border: Border(
              right: BorderSide(
                color: AppColors.surfaceBorder.withValues(alpha: 0.8),
                width: 1,
              ),
            ),
          ),
          child: Column(
            children: [
              _buildHeader(),
              _buildTabBar(),
              Expanded(
                child: TabBarView(
                  controller: _tabController,
                  children: [
                    _buildTemplatesTab(),
                    _buildDashboardsTab(),
                    _buildAddPanelTab(),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _buildHeader() {
    return Container(
      height: 44,
      decoration: BoxDecoration(
        color: AppColors.backgroundCard,
        border: Border(
          bottom: BorderSide(
            color: AppColors.surfaceBorder.withValues(alpha: 0.5),
            width: 1,
          ),
        ),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 12),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppColors.primaryCyan.withValues(alpha: 0.2),
                  AppColors.primaryCyan.withValues(alpha: 0.1),
                ],
              ),
              borderRadius: BorderRadius.circular(6),
            ),
            child: const Icon(
              Icons.dashboard_customize_rounded,
              size: 14,
              color: AppColors.primaryCyan,
            ),
          ),
          const SizedBox(width: 8),
          Text(
            'Dashboards',
            style: GoogleFonts.inter(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
              letterSpacing: -0.2,
            ),
          ),
          const Spacer(),
          if (widget.onClose != null)
            IconButton(
              icon: const Icon(Icons.close, size: 18),
              color: AppColors.textMuted,
              onPressed: widget.onClose,
              tooltip: 'Close',
              style: IconButton.styleFrom(
                padding: const EdgeInsets.all(4),
                minimumSize: const Size(28, 28),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildTabBar() {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.backgroundCard,
        border: Border(
          bottom: BorderSide(
            color: AppColors.surfaceBorder.withValues(alpha: 0.3),
            width: 1,
          ),
        ),
      ),
      child: TabBar(
        controller: _tabController,
        isScrollable: false,
        labelColor: AppColors.primaryCyan,
        unselectedLabelColor: AppColors.textMuted,
        indicatorColor: AppColors.primaryCyan,
        indicatorSize: TabBarIndicatorSize.tab,
        labelStyle: GoogleFonts.inter(
          fontSize: 11,
          fontWeight: FontWeight.w600,
        ),
        unselectedLabelStyle: GoogleFonts.inter(
          fontSize: 11,
          fontWeight: FontWeight.w500,
        ),
        tabs: const [
          Tab(text: 'Templates', height: 36),
          Tab(text: 'My Dashboards', height: 36),
          Tab(text: 'Add Panel', height: 36),
        ],
      ),
    );
  }

  // -------------------------------------------------------------------------
  // Templates Tab
  // -------------------------------------------------------------------------

  Widget _buildTemplatesTab() {
    if (widget.templateService.isLoading) {
      return const Center(
        child: CircularProgressIndicator(color: AppColors.primaryCyan),
      );
    }

    final templates = widget.templateService.templates;
    if (templates.isEmpty) {
      return Center(
        child: Text(
          'No templates available',
          style: GoogleFonts.inter(color: AppColors.textMuted, fontSize: 13),
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: templates.length,
      itemBuilder: (context, index) {
        final template = templates[index];
        return _buildTemplateCard(template);
      },
    );
  }

  Widget _buildTemplateCard(DashboardTemplateSummary template) {
    final serviceIcons = {
      'gke': Icons.cloud_circle_outlined,
      'cloud_run': Icons.play_circle_outline_rounded,
      'bigquery': Icons.analytics_outlined,
      'vertex_agent_engine': Icons.smart_toy_outlined,
    };
    final serviceColors = {
      'gke': AppColors.primaryBlue,
      'cloud_run': AppColors.success,
      'bigquery': AppColors.warning,
      'vertex_agent_engine': AppColors.secondaryPurple,
    };

    final icon = serviceIcons[template.service] ?? Icons.dashboard;
    final color = serviceColors[template.service] ?? AppColors.primaryCyan;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: AppColors.backgroundCard,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: AppColors.surfaceBorder.withValues(alpha: 0.4),
        ),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: () => _provisionTemplate(template),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(icon, color: color, size: 20),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      template.displayName,
                      style: GoogleFonts.inter(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      template.description,
                      style: GoogleFonts.inter(
                        fontSize: 11,
                        color: AppColors.textMuted,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${template.panelCount} panels',
                      style: GoogleFonts.inter(
                        fontSize: 10,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: AppColors.primaryCyan.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  'Deploy',
                  style: GoogleFonts.inter(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: AppColors.primaryCyan,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _provisionTemplate(DashboardTemplateSummary template) async {
    final result =
        await widget.templateService.provisionTemplate(template.id);
    if (result != null && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Dashboard "${template.displayName}" created'),
          backgroundColor: AppColors.success.withValues(alpha: 0.9),
        ),
      );
      // Switch to dashboards tab
      _tabController.animateTo(1);
    }
  }

  // -------------------------------------------------------------------------
  // Dashboards Tab
  // -------------------------------------------------------------------------

  Widget _buildDashboardsTab() {
    if (widget.templateService.isLoading) {
      return const Center(
        child: CircularProgressIndicator(color: AppColors.primaryCyan),
      );
    }

    final dashboards = widget.templateService.dashboards;

    return Column(
      children: [
        // Create new dashboard button
        Padding(
          padding: const EdgeInsets.all(12),
          child: SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: _showCreateDashboardDialog,
              icon: const Icon(Icons.add, size: 16),
              label: Text(
                'New Dashboard',
                style: GoogleFonts.inter(fontSize: 12),
              ),
              style: OutlinedButton.styleFrom(
                foregroundColor: AppColors.primaryCyan,
                side: BorderSide(
                  color: AppColors.primaryCyan.withValues(alpha: 0.5),
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              ),
            ),
          ),
        ),
        Expanded(
          child: dashboards.isEmpty
              ? Center(
                  child: Text(
                    'No dashboards yet.\nProvision a template or create a new one.',
                    textAlign: TextAlign.center,
                    style: GoogleFonts.inter(
                      color: AppColors.textMuted,
                      fontSize: 12,
                    ),
                  ),
                )
              : ListView.builder(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 12),
                  itemCount: dashboards.length,
                  itemBuilder: (context, index) {
                    final dash = dashboards[index];
                    final isSelected =
                        dash.id == widget.templateService.selectedDashboardId;
                    return _buildDashboardCard(dash, isSelected);
                  },
                ),
        ),
      ],
    );
  }

  Widget _buildDashboardCard(DashboardSummary dashboard, bool isSelected) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: isSelected
            ? AppColors.primaryCyan.withValues(alpha: 0.08)
            : AppColors.backgroundCard,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: isSelected
              ? AppColors.primaryCyan.withValues(alpha: 0.5)
              : AppColors.surfaceBorder.withValues(alpha: 0.4),
          width: isSelected ? 1.5 : 1,
        ),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: () {
          widget.templateService.selectDashboard(dashboard.id);
          // Switch to Add Panel tab so user can add panels
          _tabController.animateTo(2);
        },
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      dashboard.displayName,
                      style: GoogleFonts.inter(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    if (dashboard.description.isNotEmpty) ...[
                      const SizedBox(height: 2),
                      Text(
                        dashboard.description,
                        style: GoogleFonts.inter(
                          fontSize: 11,
                          color: AppColors.textMuted,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        _buildBadge(dashboard.source, AppColors.textSecondary),
                        const SizedBox(width: 6),
                        _buildBadge(
                          '${dashboard.panelCount} panels',
                          AppColors.textSecondary,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              if (isSelected)
                const Icon(
                  Icons.check_circle,
                  color: AppColors.primaryCyan,
                  size: 18,
                ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBadge(String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        text,
        style: GoogleFonts.inter(fontSize: 10, color: color),
      ),
    );
  }

  Future<void> _showCreateDashboardDialog() async {
    final nameController = TextEditingController();
    final descController = TextEditingController();

    final result = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: AppColors.backgroundCard,
        title: Text(
          'New Dashboard',
          style: GoogleFonts.inter(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w600,
          ),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameController,
              style: const TextStyle(color: AppColors.textPrimary),
              decoration: const InputDecoration(
                labelText: 'Name',
                labelStyle: TextStyle(color: AppColors.textMuted),
                enabledBorder: UnderlineInputBorder(
                  borderSide: BorderSide(color: AppColors.textMuted),
                ),
                focusedBorder: UnderlineInputBorder(
                  borderSide: BorderSide(color: AppColors.primaryCyan),
                ),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: descController,
              style: const TextStyle(color: AppColors.textPrimary),
              decoration: const InputDecoration(
                labelText: 'Description (optional)',
                labelStyle: TextStyle(color: AppColors.textMuted),
                enabledBorder: UnderlineInputBorder(
                  borderSide: BorderSide(color: AppColors.textMuted),
                ),
                focusedBorder: UnderlineInputBorder(
                  borderSide: BorderSide(color: AppColors.primaryCyan),
                ),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.primaryCyan,
            ),
            child: const Text('Create'),
          ),
        ],
      ),
    );

    if (result == true && nameController.text.isNotEmpty) {
      await widget.templateService.createDashboard(
        displayName: nameController.text,
        description: descController.text,
      );
    }

    nameController.dispose();
    descController.dispose();
  }

  // -------------------------------------------------------------------------
  // Add Panel Tab
  // -------------------------------------------------------------------------

  Widget _buildAddPanelTab() {
    final selectedId = widget.templateService.selectedDashboardId;

    if (selectedId == null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.dashboard_outlined,
                size: 48,
                color: AppColors.textMuted,
              ),
              const SizedBox(height: 12),
              Text(
                'Select a dashboard first',
                style: GoogleFonts.inter(
                  fontSize: 14,
                  color: AppColors.textMuted,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Go to the "My Dashboards" tab and select\n'
                'a dashboard to add panels to.',
                textAlign: TextAlign.center,
                style: GoogleFonts.inter(
                  fontSize: 12,
                  color: AppColors.textMuted,
                ),
              ),
            ],
          ),
        ),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Panel type selector
          _buildSectionHeader('Panel Type'),
          const SizedBox(height: 8),
          _buildPanelTypeSelector(),
          const SizedBox(height: 16),

          // Panel form
          _buildSectionHeader('Panel Configuration'),
          const SizedBox(height: 8),
          _buildFormField('Title', _panelTitleController, 'My Custom Panel'),
          _buildFormField('Description', _descriptionController,
              'Optional description'),
          const SizedBox(height: 8),
          if (_panelType == 'metric') ..._buildMetricFields(),
          if (_panelType == 'log') ..._buildLogFields(),
          if (_panelType == 'trace') ..._buildTraceFields(),

          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              onPressed: _addPanel,
              icon: const Icon(Icons.add, size: 16),
              label: Text(
                'Add Panel',
                style: GoogleFonts.inter(fontSize: 12),
              ),
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.primaryCyan,
                padding:
                    const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSectionHeader(String title) {
    return Text(
      title,
      style: GoogleFonts.inter(
        fontSize: 11,
        fontWeight: FontWeight.w600,
        color: AppColors.textSecondary,
        letterSpacing: 0.5,
      ),
    );
  }

  Widget _buildPanelTypeSelector() {
    return Row(
      children: [
        _buildTypeChip('Metric', 'metric', Icons.show_chart_rounded,
            AppColors.warning),
        const SizedBox(width: 6),
        _buildTypeChip(
            'Log', 'log', Icons.article_outlined, AppColors.success),
        const SizedBox(width: 6),
        _buildTypeChip(
            'Trace', 'trace', Icons.alt_route_rounded, AppColors.primaryCyan),
      ],
    );
  }

  Widget _buildTypeChip(
    String label,
    String value,
    IconData icon,
    Color color,
  ) {
    final isSelected = _panelType == value;
    return Expanded(
      child: InkWell(
        onTap: () => setState(() => _panelType = value),
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: isSelected
                ? color.withValues(alpha: 0.15)
                : AppColors.backgroundCard,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: isSelected
                  ? color.withValues(alpha: 0.5)
                  : AppColors.surfaceBorder.withValues(alpha: 0.3),
            ),
          ),
          child: Column(
            children: [
              Icon(icon, color: isSelected ? color : AppColors.textMuted,
                  size: 18),
              const SizedBox(height: 4),
              Text(
                label,
                style: GoogleFonts.inter(
                  fontSize: 11,
                  fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                  color: isSelected ? color : AppColors.textMuted,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildFormField(
    String label,
    TextEditingController controller,
    String hint,
  ) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: TextField(
        controller: controller,
        style: GoogleFonts.inter(
          fontSize: 12,
          color: AppColors.textPrimary,
        ),
        decoration: InputDecoration(
          labelText: label,
          hintText: hint,
          labelStyle:
              GoogleFonts.inter(fontSize: 11, color: AppColors.textMuted),
          hintStyle:
              GoogleFonts.inter(fontSize: 11, color: AppColors.textMuted),
          isDense: true,
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(6),
            borderSide: BorderSide(
                color: AppColors.surfaceBorder.withValues(alpha: 0.4)),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(6),
            borderSide: const BorderSide(color: AppColors.primaryCyan),
          ),
          filled: true,
          fillColor: AppColors.backgroundCard,
        ),
      ),
    );
  }

  List<Widget> _buildMetricFields() {
    return [
      _buildFormField(
        'Metric Type',
        _metricTypeController,
        'e.g. compute.googleapis.com/instance/cpu/utilization',
      ),
      _buildFormField(
        'Resource Type (optional)',
        _resourceTypeController,
        'e.g. gce_instance, k8s_container',
      ),
    ];
  }

  List<Widget> _buildLogFields() {
    return [
      _buildFormField(
        'Log Filter',
        _logFilterController,
        'e.g. resource.type="k8s_container"',
      ),
      _buildFormField(
        'Resource Type (optional)',
        _resourceTypeController,
        'e.g. k8s_container, cloud_run_revision',
      ),
    ];
  }

  List<Widget> _buildTraceFields() {
    return [
      _buildFormField(
        'Trace Filter',
        _traceFilterController,
        'e.g. +resource.type:"cloud_run_revision"',
      ),
    ];
  }

  Future<void> _addPanel() async {
    final dashboardId = widget.templateService.selectedDashboardId;
    if (dashboardId == null) return;

    final title = _panelTitleController.text.isEmpty
        ? 'Untitled Panel'
        : _panelTitleController.text;

    Map<String, dynamic>? result;

    switch (_panelType) {
      case 'metric':
        if (_metricTypeController.text.isEmpty) {
          _showError('Metric type is required');
          return;
        }
        result = await widget.templateService.addMetricPanel(
          dashboardId: dashboardId,
          title: title,
          metricType: _metricTypeController.text,
          resourceType: _resourceTypeController.text.isNotEmpty
              ? _resourceTypeController.text
              : null,
          description: _descriptionController.text,
        );

      case 'log':
        if (_logFilterController.text.isEmpty) {
          _showError('Log filter is required');
          return;
        }
        result = await widget.templateService.addLogPanel(
          dashboardId: dashboardId,
          title: title,
          logFilter: _logFilterController.text,
          resourceType: _resourceTypeController.text.isNotEmpty
              ? _resourceTypeController.text
              : null,
          description: _descriptionController.text,
        );

      case 'trace':
        if (_traceFilterController.text.isEmpty) {
          _showError('Trace filter is required');
          return;
        }
        result = await widget.templateService.addTracePanel(
          dashboardId: dashboardId,
          title: title,
          traceFilter: _traceFilterController.text,
          description: _descriptionController.text,
        );
    }

    if (result != null && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Panel "$title" added'),
          backgroundColor: AppColors.success.withValues(alpha: 0.9),
        ),
      );
      // Clear form
      _panelTitleController.clear();
      _metricTypeController.clear();
      _resourceTypeController.clear();
      _logFilterController.clear();
      _traceFilterController.clear();
      _descriptionController.clear();
      // Refresh dashboard list
      await widget.templateService.fetchDashboards();
    } else if (mounted) {
      _showError('Failed to add panel');
    }
  }

  void _showError(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: AppColors.error.withValues(alpha: 0.9),
      ),
    );
  }
}
