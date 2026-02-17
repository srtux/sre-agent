import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/dashboard_models.dart';
import 'auth_service.dart';

/// Service for managing dashboards via the backend API.
///
/// Provides CRUD operations for dashboards, panel management,
/// and state management for the dashboard UI.
class DashboardApiService extends ChangeNotifier {
  List<DashboardSummary> _dashboards = [];
  DashboardModel? _currentDashboard;
  bool _isLoading = false;
  String? _error;

  List<DashboardSummary> get dashboards => _dashboards;
  DashboardModel? get currentDashboard => _currentDashboard;
  bool get isLoading => _isLoading;
  String? get error => _error;

  String get _baseUrl {
    const configuredUrl = String.fromEnvironment('API_BASE_URL');
    if (configuredUrl.isNotEmpty) return configuredUrl;
    if (kIsWeb) {
      final uri = Uri.base;
      return '${uri.scheme}://${uri.host}:${uri.port}';
    }
    return 'http://localhost:8001';
  }

  Future<http.Client> _getClient() async {
    return AuthService.instance.getAuthenticatedClient();
  }

  /// Fetch all dashboards.
  Future<void> fetchDashboards({
    String? projectId,
    bool includeCloud = true,
  }) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final client = await _getClient();
      final queryParams = <String, String>{};
      if (projectId != null) queryParams['project_id'] = projectId;
      if (!includeCloud) queryParams['include_cloud'] = 'false';

      final uri = Uri.parse('$_baseUrl/api/dashboards')
          .replace(queryParameters: queryParams.isNotEmpty ? queryParams : null);

      final response = await client.get(uri);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        final list = data['dashboards'] as List<dynamic>? ?? [];
        _dashboards = list
            .map((d) =>
                DashboardSummary.fromJson(d as Map<String, dynamic>))
            .toList();
        _error = null;
      } else {
        _error = 'Failed to fetch dashboards: ${response.statusCode}';
      }
    } catch (e) {
      _error = 'Failed to fetch dashboards: $e';
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Fetch a specific dashboard by ID.
  Future<DashboardModel?> fetchDashboard(String dashboardId) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final client = await _getClient();
      final uri = Uri.parse('$_baseUrl/api/dashboards/$dashboardId');
      final response = await client.get(uri);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        _currentDashboard = DashboardModel.fromJson(data);
        _error = null;
        notifyListeners();
        return _currentDashboard;
      } else {
        _error = 'Failed to fetch dashboard: ${response.statusCode}';
        notifyListeners();
        return null;
      }
    } catch (e) {
      _error = 'Failed to fetch dashboard: $e';
      notifyListeners();
      return null;
    } finally {
      _isLoading = false;
    }
  }

  /// Create a new dashboard.
  Future<DashboardModel?> createDashboard({
    required String displayName,
    String description = '',
    List<Map<String, dynamic>>? panels,
    String? projectId,
  }) async {
    try {
      final client = await _getClient();
      final uri = Uri.parse('$_baseUrl/api/dashboards');
      final body = <String, dynamic>{
        'display_name': displayName,
        'description': description,
      };
      if (panels != null) body['panels'] = panels;
      if (projectId != null) body['project_id'] = projectId;

      final response = await client.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(body),
      );

      if (response.statusCode == 201) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        final dashboard = DashboardModel.fromJson(data);
        await fetchDashboards();
        return dashboard;
      } else {
        _error = 'Failed to create dashboard: ${response.statusCode}';
        notifyListeners();
        return null;
      }
    } catch (e) {
      _error = 'Failed to create dashboard: $e';
      notifyListeners();
      return null;
    }
  }

  /// Update a dashboard.
  Future<DashboardModel?> updateDashboard(
    String dashboardId,
    Map<String, dynamic> updates,
  ) async {
    try {
      final client = await _getClient();
      final uri = Uri.parse('$_baseUrl/api/dashboards/$dashboardId');

      final response = await client.patch(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(updates),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        _currentDashboard = DashboardModel.fromJson(data);
        notifyListeners();
        return _currentDashboard;
      } else {
        _error = 'Failed to update dashboard: ${response.statusCode}';
        notifyListeners();
        return null;
      }
    } catch (e) {
      _error = 'Failed to update dashboard: $e';
      notifyListeners();
      return null;
    }
  }

  /// Delete a dashboard.
  Future<bool> deleteDashboard(String dashboardId) async {
    try {
      final client = await _getClient();
      final uri = Uri.parse('$_baseUrl/api/dashboards/$dashboardId');
      final response = await client.delete(uri);

      if (response.statusCode == 204) {
        _dashboards.removeWhere((d) => d.id == dashboardId);
        if (_currentDashboard?.id == dashboardId) {
          _currentDashboard = null;
        }
        notifyListeners();
        return true;
      }
      return false;
    } catch (e) {
      _error = 'Failed to delete dashboard: $e';
      notifyListeners();
      return false;
    }
  }

  /// Add a panel to a dashboard.
  Future<DashboardModel?> addPanel(
    String dashboardId,
    Map<String, dynamic> panelData,
  ) async {
    try {
      final client = await _getClient();
      final uri = Uri.parse('$_baseUrl/api/dashboards/$dashboardId/panels');

      final response = await client.post(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(panelData),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        _currentDashboard = DashboardModel.fromJson(data);
        notifyListeners();
        return _currentDashboard;
      }
      return null;
    } catch (e) {
      _error = 'Failed to add panel: $e';
      notifyListeners();
      return null;
    }
  }

  /// Remove a panel from a dashboard.
  Future<DashboardModel?> removePanel(
    String dashboardId,
    String panelId,
  ) async {
    try {
      final client = await _getClient();
      final uri = Uri.parse(
          '$_baseUrl/api/dashboards/$dashboardId/panels/$panelId');
      final response = await client.delete(uri);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        _currentDashboard = DashboardModel.fromJson(data);
        notifyListeners();
        return _currentDashboard;
      }
      return null;
    } catch (e) {
      _error = 'Failed to remove panel: $e';
      notifyListeners();
      return null;
    }
  }

  /// Update a panel's position.
  Future<DashboardModel?> updatePanelPosition(
    String dashboardId,
    String panelId,
    GridPosition position,
  ) async {
    try {
      final client = await _getClient();
      final uri = Uri.parse(
          '$_baseUrl/api/dashboards/$dashboardId/panels/$panelId/position');

      final response = await client.patch(
        uri,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode(position.toJson()),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        _currentDashboard = DashboardModel.fromJson(data);
        notifyListeners();
        return _currentDashboard;
      }
      return null;
    } catch (e) {
      _error = 'Failed to update panel position: $e';
      notifyListeners();
      return null;
    }
  }
}
