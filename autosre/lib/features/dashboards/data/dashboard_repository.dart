import 'package:dio/dio.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../../shared/data/dio_provider.dart';
import '../domain/models.dart';

part 'dashboard_repository.g.dart';

class DashboardRepository {
  final Dio _dio;

  DashboardRepository(this._dio);

  Future<List<DashboardSummary>> listDashboards({
    String? projectId,
    bool includeCloud = true,
  }) async {
    final response = await _dio.get(
      '/api/dashboards',
      queryParameters: {
        'project_id': ?projectId,
        'include_cloud': includeCloud.toString(),
      },
    );

    final dynamic rawData = response.data;
    if (rawData is! Map<String, dynamic>) {
      throw Exception(
          'Expected JSON Map from /api/dashboards, but got ${rawData.runtimeType}. '
          'This often happens if the request falls back to the frontend index.html due to an incorrect baseUrl.');
    }
    final data = rawData;
    final list = data['dashboards'] as List<dynamic>? ?? [];
    return list
        .map((d) => DashboardSummary.fromJson(d as Map<String, dynamic>))
        .toList();
  }

  Future<Dashboard?> getDashboard(String dashboardId) async {
    final response = await _dio.get('/api/dashboards/$dashboardId');
    return Dashboard.fromJson(response.data as Map<String, dynamic>);
  }

  Future<Dashboard> createDashboard({
    required String displayName,
    String description = '',
    List<Map<String, dynamic>>? panels,
    String? projectId,
  }) async {
    final response = await _dio.post(
      '/api/dashboards',
      data: {
        'display_name': displayName,
        'description': description,
        'panels': ?panels,
        'project_id': ?projectId,
      },
    );
    return Dashboard.fromJson(response.data as Map<String, dynamic>);
  }

  Future<Dashboard> updateDashboard(
    String dashboardId,
    Map<String, dynamic> updates,
  ) async {
    final response = await _dio.patch(
      '/api/dashboards/$dashboardId',
      data: updates,
    );
    return Dashboard.fromJson(response.data as Map<String, dynamic>);
  }

  Future<bool> deleteDashboard(String dashboardId) async {
    final response = await _dio.delete('/api/dashboards/$dashboardId');
    return response.statusCode == 204;
  }

  Future<Dashboard> addPanel(
    String dashboardId,
    Map<String, dynamic> panelData,
  ) async {
    final response = await _dio.post(
      '/api/dashboards/$dashboardId/panels',
      data: panelData,
    );
    return Dashboard.fromJson(response.data as Map<String, dynamic>);
  }

  Future<Dashboard> removePanel(
    String dashboardId,
    String panelId,
  ) async {
    final response = await _dio.delete(
      '/api/dashboards/$dashboardId/panels/$panelId',
    );
    return Dashboard.fromJson(response.data as Map<String, dynamic>);
  }

  Future<Dashboard> updatePanelPosition(
    String dashboardId,
    String panelId,
    GridPosition position,
  ) async {
    final response = await _dio.patch(
      '/api/dashboards/$dashboardId/panels/$panelId/position',
      data: position.toJson(),
    );
    return Dashboard.fromJson(response.data as Map<String, dynamic>);
  }
}

@riverpod
DashboardRepository dashboardRepository(Ref ref) {

  return DashboardRepository(ref.watch(dioProvider));
}
