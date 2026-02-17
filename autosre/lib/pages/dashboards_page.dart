import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../models/dashboard_models.dart';
import '../services/dashboard_service.dart';
import '../theme/app_theme.dart';
import 'dashboard_view_page.dart';

/// Dashboard listing page showing user-created and GCP project dashboards.
///
/// Features a responsive grid of dashboard cards with search/filter,
/// source badges (GCP/Local), and a FAB for creating new dashboards.
class DashboardsPage extends StatefulWidget {
  const DashboardsPage({super.key});

  @override
  State<DashboardsPage> createState() => _DashboardsPageState();
}

class _DashboardsPageState extends State<DashboardsPage> {
  final _searchController = TextEditingController();
  String _filter = 'all'; // all, local, cloud

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      context.read<DashboardApiService>().fetchDashboards();
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<DashboardSummary> _filteredDashboards(List<DashboardSummary> all) {
    var list = all;
    final query = _searchController.text.toLowerCase();
    if (query.isNotEmpty) {
      list = list
          .where((d) => d.displayName.toLowerCase().contains(query))
          .toList();
    }
    if (_filter == 'local') {
      list = list.where((d) => d.source == DashboardSource.local).toList();
    } else if (_filter == 'cloud') {
      list = list
          .where((d) => d.source == DashboardSource.cloudMonitoring)
          .toList();
    }
    return list;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.backgroundDark,
      appBar: AppBar(
        title: const Text('Dashboards'),
        backgroundColor: AppColors.backgroundCard,
        elevation: 0,
      ),
      body: Column(
        children: [
          _buildSearchBar(),
          _buildFilterChips(),
          Expanded(child: _buildDashboardGrid()),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showCreateDialog(context),
        backgroundColor: AppColors.primaryTeal,
        icon: const Icon(Icons.add),
        label: const Text('New Dashboard'),
      ),
    );
  }

  Widget _buildSearchBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: TextField(
        controller: _searchController,
        onChanged: (_) => setState(() {}),
        style: const TextStyle(color: Colors.white),
        decoration: InputDecoration(
          hintText: 'Search dashboards...',
          hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.5)),
          prefixIcon:
              Icon(Icons.search, color: Colors.white.withValues(alpha: 0.5)),
          filled: true,
          fillColor: AppColors.backgroundCard,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide.none,
          ),
          contentPadding: const EdgeInsets.symmetric(vertical: 12),
        ),
      ),
    );
  }

  Widget _buildFilterChips() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      child: Row(
        children: [
          _buildChip('All', 'all'),
          const SizedBox(width: 8),
          _buildChip('Local', 'local'),
          const SizedBox(width: 8),
          _buildChip('Cloud', 'cloud'),
        ],
      ),
    );
  }

  Widget _buildChip(String label, String value) {
    final selected = _filter == value;
    return FilterChip(
      label: Text(label),
      selected: selected,
      onSelected: (_) => setState(() => _filter = value),
      selectedColor: AppColors.primaryTeal.withValues(alpha: 0.3),
      checkmarkColor: AppColors.primaryCyan,
      labelStyle: TextStyle(
        color: selected ? AppColors.primaryCyan : Colors.white70,
      ),
      backgroundColor: AppColors.backgroundCard,
      side: BorderSide(
        color: selected
            ? AppColors.primaryCyan.withValues(alpha: 0.5)
            : Colors.white24,
      ),
    );
  }

  Widget _buildDashboardGrid() {
    return Consumer<DashboardApiService>(
      builder: (context, service, _) {
        if (service.isLoading) {
          return const Center(
            child: CircularProgressIndicator(color: AppColors.primaryTeal),
          );
        }
        if (service.error != null) {
          return Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(Icons.error_outline,
                    color: Colors.redAccent.withValues(alpha: 0.7), size: 48),
                const SizedBox(height: 16),
                Text(service.error!,
                    style: const TextStyle(color: Colors.white70)),
                const SizedBox(height: 16),
                ElevatedButton(
                  onPressed: () => service.fetchDashboards(),
                  child: const Text('Retry'),
                ),
              ],
            ),
          );
        }

        final filtered = _filteredDashboards(service.dashboards);
        if (filtered.isEmpty) {
          return _buildEmptyState();
        }

        return LayoutBuilder(
          builder: (context, constraints) {
            final crossAxisCount = constraints.maxWidth > 1200
                ? 4
                : constraints.maxWidth > 800
                    ? 3
                    : constraints.maxWidth > 500
                        ? 2
                        : 1;
            return GridView.builder(
              padding: const EdgeInsets.all(16),
              gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: crossAxisCount,
                childAspectRatio: 1.6,
                crossAxisSpacing: 16,
                mainAxisSpacing: 16,
              ),
              itemCount: filtered.length,
              itemBuilder: (context, index) =>
                  _buildDashboardCard(filtered[index]),
            );
          },
        );
      },
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.dashboard_outlined,
              size: 64, color: Colors.white.withValues(alpha: 0.3)),
          const SizedBox(height: 16),
          Text(
            _searchController.text.isNotEmpty
                ? 'No dashboards match your search'
                : 'No dashboards yet',
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.5),
              fontSize: 18,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Create a dashboard to get started',
            style: TextStyle(
                color: Colors.white.withValues(alpha: 0.3), fontSize: 14),
          ),
        ],
      ),
    );
  }

  Widget _buildDashboardCard(DashboardSummary dashboard) {
    final isCloud = dashboard.source == DashboardSource.cloudMonitoring;
    return Card(
      color: AppColors.backgroundCard,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: Colors.white.withValues(alpha: 0.1)),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () {
          Navigator.of(context).push(
            MaterialPageRoute(
              builder: (_) =>
                  DashboardViewPage(dashboardId: dashboard.id),
            ),
          );
        },
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      dashboard.displayName,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  _buildSourceBadge(isCloud),
                ],
              ),
              const SizedBox(height: 8),
              if (dashboard.description.isNotEmpty)
                Expanded(
                  child: Text(
                    dashboard.description,
                    style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.5), fontSize: 13),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              const Spacer(),
              Row(
                children: [
                  Icon(Icons.widgets_outlined,
                      size: 14,
                      color: Colors.white.withValues(alpha: 0.4)),
                  const SizedBox(width: 4),
                  Text(
                    '${dashboard.panelCount} panels',
                    style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.4),
                        fontSize: 12),
                  ),
                  const Spacer(),
                  if (dashboard.metadata?.starred == true)
                    Icon(Icons.star,
                        size: 16, color: Colors.amber.withValues(alpha: 0.7)),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSourceBadge(bool isCloud) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: isCloud
            ? Colors.blue.withValues(alpha: 0.2)
            : AppColors.primaryTeal.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: isCloud
              ? Colors.blue.withValues(alpha: 0.4)
              : AppColors.primaryTeal.withValues(alpha: 0.4),
        ),
      ),
      child: Text(
        isCloud ? 'GCP' : 'Local',
        style: TextStyle(
          color: isCloud ? Colors.blue[200] : AppColors.primaryCyan,
          fontSize: 11,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }

  void _showCreateDialog(BuildContext context) {
    final nameController = TextEditingController();
    final descController = TextEditingController();

    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.backgroundCard,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: const Text('New Dashboard',
            style: TextStyle(color: Colors.white)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TextField(
              controller: nameController,
              autofocus: true,
              style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(
                labelText: 'Name',
                labelStyle:
                    TextStyle(color: Colors.white.withValues(alpha: 0.5)),
                enabledBorder: OutlineInputBorder(
                  borderSide: BorderSide(
                      color: Colors.white.withValues(alpha: 0.2)),
                  borderRadius: BorderRadius.circular(8),
                ),
                focusedBorder: OutlineInputBorder(
                  borderSide:
                      const BorderSide(color: AppColors.primaryCyan),
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: descController,
              style: const TextStyle(color: Colors.white),
              maxLines: 2,
              decoration: InputDecoration(
                labelText: 'Description (optional)',
                labelStyle:
                    TextStyle(color: Colors.white.withValues(alpha: 0.5)),
                enabledBorder: OutlineInputBorder(
                  borderSide: BorderSide(
                      color: Colors.white.withValues(alpha: 0.2)),
                  borderRadius: BorderRadius.circular(8),
                ),
                focusedBorder: OutlineInputBorder(
                  borderSide:
                      const BorderSide(color: AppColors.primaryCyan),
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Cancel',
                style: TextStyle(color: Colors.white54)),
          ),
          FilledButton(
            onPressed: () async {
              if (nameController.text.trim().isEmpty) return;
              Navigator.of(ctx).pop();
              final service = context.read<DashboardApiService>();
              final dashboard = await service.createDashboard(
                displayName: nameController.text.trim(),
                description: descController.text.trim(),
              );
              if (dashboard != null && context.mounted) {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) =>
                        DashboardViewPage(dashboardId: dashboard.id),
                  ),
                );
              }
            },
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.primaryTeal,
            ),
            child: const Text('Create'),
          ),
        ],
      ),
    );
  }
}
