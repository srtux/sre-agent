import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../data/dashboard_repository.dart';
import '../domain/models.dart';

part 'dashboard_notifiers.g.dart';

@riverpod
class Dashboards extends _$Dashboards {
  @override
  Future<List<DashboardSummary>> build({
    String? projectId,
    bool includeCloud = true,
  }) async {
    return ref
        .watch(dashboardRepositoryProvider)
        .listDashboards(projectId: projectId, includeCloud: includeCloud);
  }

  Future<void> refresh() async {
    ref.invalidateSelf();
    await future;
  }

  Future<void> createDashboard({
    required String displayName,
    String description = '',
    List<Map<String, dynamic>>? panels,
    String? projectId,
  }) async {
    await ref
        .read(dashboardRepositoryProvider)
        .createDashboard(
          displayName: displayName,
          description: description,
          panels: panels,
          projectId: projectId,
        );
    ref.invalidateSelf();
  }

  Future<void> deleteDashboard(String dashboardId) async {
    final success = await ref
        .read(dashboardRepositoryProvider)
        .deleteDashboard(dashboardId);
    if (success) {
      ref.invalidateSelf();
    }
  }
}

@riverpod
class DashboardDetail extends _$DashboardDetail {
  @override
  Future<Dashboard> build(String dashboardId) async {
    final dashboard = await ref
        .watch(dashboardRepositoryProvider)
        .getDashboard(dashboardId);
    if (dashboard == null) {
      throw Exception('Dashboard not found');
    }
    return dashboard;
  }

  Future<void> updateDashboard(Map<String, dynamic> updates) async {
    final updated = await ref
        .read(dashboardRepositoryProvider)
        .updateDashboard(dashboardId, updates);
    state = AsyncValue.data(updated);
    // Also invalidate the list as names/summaries might have changed
    ref.invalidate(dashboardsProvider);
  }

  Future<void> addPanel(Map<String, dynamic> panelData) async {
    final updated = await ref
        .read(dashboardRepositoryProvider)
        .addPanel(dashboardId, panelData);
    state = AsyncValue.data(updated);
  }

  Future<void> removePanel(String panelId) async {
    final updated = await ref
        .read(dashboardRepositoryProvider)
        .removePanel(dashboardId, panelId);
    state = AsyncValue.data(updated);
  }

  Future<void> updatePanelPosition(
    String panelId,
    GridPosition position,
  ) async {
    final updated = await ref
        .read(dashboardRepositoryProvider)
        .updatePanelPosition(dashboardId, panelId, position);
    state = AsyncValue.data(updated);
  }
}
