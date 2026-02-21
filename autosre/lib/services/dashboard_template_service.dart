import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../utils/isolate_helper.dart';
import 'service_config.dart';

Map<String, dynamic> _parseJsonMap(String json) =>
    jsonDecode(json) as Map<String, dynamic>;

/// Summary of an OOTB dashboard template.
class DashboardTemplateSummary {
  final String id;
  final String displayName;
  final String description;
  final String service;
  final int panelCount;
  final Map<String, String> labels;

  DashboardTemplateSummary({
    required this.id,
    required this.displayName,
    required this.description,
    required this.service,
    required this.panelCount,
    required this.labels,
  });

  factory DashboardTemplateSummary.fromJson(Map<String, dynamic> json) {
    return DashboardTemplateSummary(
      id: json['id'] as String? ?? '',
      displayName: json['display_name'] as String? ?? '',
      description: json['description'] as String? ?? '',
      service: json['service'] as String? ?? '',
      panelCount: json['panel_count'] as int? ?? 0,
      labels:
          (json['labels'] as Map<String, dynamic>?)?.map(
            (k, v) => MapEntry(k, v.toString()),
          ) ??
          {},
    );
  }
}

/// Summary of a provisioned or custom dashboard.
class DashboardSummary {
  final String id;
  final String displayName;
  final String description;
  final String source;
  final int panelCount;
  final Map<String, String> labels;

  DashboardSummary({
    required this.id,
    required this.displayName,
    required this.description,
    required this.source,
    required this.panelCount,
    required this.labels,
  });

  factory DashboardSummary.fromJson(Map<String, dynamic> json) {
    return DashboardSummary(
      id: json['id'] as String? ?? '',
      displayName: json['display_name'] as String? ?? '',
      description: json['description'] as String? ?? '',
      source: json['source'] as String? ?? 'local',
      panelCount: json['panel_count'] as int? ?? 0,
      labels:
          (json['labels'] as Map<String, dynamic>?)?.map(
            (k, v) => MapEntry(k, v.toString()),
          ) ??
          {},
    );
  }
}

/// Service for managing dashboard templates and custom dashboards.
///
/// Communicates with the backend `/api/dashboards` endpoints for:
/// - Listing OOTB templates
/// - Provisioning templates as dashboards
/// - Creating custom dashboards
/// - Adding metric, log, and trace panels
class DashboardTemplateService extends ChangeNotifier {
  final http.Client _client;

  List<DashboardTemplateSummary> _templates = [];
  List<DashboardTemplateSummary> get templates => List.unmodifiable(_templates);

  List<DashboardSummary> _dashboards = [];
  List<DashboardSummary> get dashboards => List.unmodifiable(_dashboards);

  bool _isLoading = false;
  bool get isLoading => _isLoading;

  String? _error;
  String? get error => _error;

  /// Currently selected dashboard ID for adding custom panels.
  String? _selectedDashboardId;
  String? get selectedDashboardId => _selectedDashboardId;

  DashboardTemplateService({http.Client? client})
    : _client = client ?? http.Client();

  String get _baseUrl => '${ServiceConfig.baseUrl}/api/dashboards';

  // -----------------------------------------------------------------------
  // Template operations
  // -----------------------------------------------------------------------

  /// Fetch available OOTB templates from the backend.
  Future<void> fetchTemplates() async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final response = await _client
          .get(Uri.parse('$_baseUrl/templates/list'))
          .timeout(ServiceConfig.defaultTimeout);

      if (response.statusCode == 200) {
        final data = await AppIsolate.run(_parseJsonMap, response.body);
        final rawList = data['templates'] as List<dynamic>? ?? [];
        _templates = rawList
            .whereType<Map<String, dynamic>>()
            .map((item) => DashboardTemplateSummary.fromJson(item))
            .toList();
      } else {
        _error = 'Failed to fetch templates: ${response.statusCode}';
      }
    } catch (e) {
      _error = 'Failed to fetch templates: $e';
      debugPrint('DashboardTemplateService.fetchTemplates error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Provision an OOTB template as a new dashboard.
  Future<Map<String, dynamic>?> provisionTemplate(
    String templateId, {
    String? projectId,
  }) async {
    try {
      final body = <String, dynamic>{};
      if (projectId != null) body['project_id'] = projectId;

      final response = await _client
          .post(
            Uri.parse('$_baseUrl/templates/$templateId/provision'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(body),
          )
          .timeout(ServiceConfig.defaultTimeout);

      if (response.statusCode == 201) {
        final dashboard = await AppIsolate.run(_parseJsonMap, response.body);
        // Refresh dashboard list
        await fetchDashboards();
        return dashboard;
      } else {
        debugPrint(
          'Provision template failed: ${response.statusCode} ${response.body}',
        );
        return null;
      }
    } catch (e) {
      debugPrint('DashboardTemplateService.provisionTemplate error: $e');
      return null;
    }
  }

  // -----------------------------------------------------------------------
  // Dashboard operations
  // -----------------------------------------------------------------------

  /// Fetch all dashboards from the backend.
  Future<void> fetchDashboards({bool includeCloud = false}) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final uri = Uri.parse(
        _baseUrl,
      ).replace(queryParameters: {'include_cloud': includeCloud.toString()});
      final response = await _client
          .get(uri)
          .timeout(ServiceConfig.defaultTimeout);

      if (response.statusCode == 200) {
        final data = await AppIsolate.run(_parseJsonMap, response.body);
        final rawList = data['dashboards'] as List<dynamic>? ?? [];
        _dashboards = rawList
            .whereType<Map<String, dynamic>>()
            .map((item) => DashboardSummary.fromJson(item))
            .toList();
      } else {
        _error = 'Failed to fetch dashboards: ${response.statusCode}';
      }
    } catch (e) {
      _error = 'Failed to fetch dashboards: $e';
      debugPrint('DashboardTemplateService.fetchDashboards error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Create a new empty custom dashboard.
  Future<Map<String, dynamic>?> createDashboard({
    required String displayName,
    String description = '',
    String? projectId,
  }) async {
    try {
      final body = <String, dynamic>{
        'display_name': displayName,
        'description': description,
      };
      if (projectId != null) body['project_id'] = projectId;

      final response = await _client
          .post(
            Uri.parse(_baseUrl),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(body),
          )
          .timeout(ServiceConfig.defaultTimeout);

      if (response.statusCode == 201) {
        final dashboard = await AppIsolate.run(_parseJsonMap, response.body);
        await fetchDashboards();
        return dashboard;
      } else {
        debugPrint(
          'Create dashboard failed: ${response.statusCode} ${response.body}',
        );
        return null;
      }
    } catch (e) {
      debugPrint('DashboardTemplateService.createDashboard error: $e');
      return null;
    }
  }

  /// Delete a dashboard.
  Future<bool> deleteDashboard(String dashboardId) async {
    try {
      final response = await _client
          .delete(Uri.parse('$_baseUrl/$dashboardId'))
          .timeout(ServiceConfig.defaultTimeout);

      if (response.statusCode == 204) {
        if (_selectedDashboardId == dashboardId) {
          _selectedDashboardId = null;
        }
        await fetchDashboards();
        return true;
      }
      return false;
    } catch (e) {
      debugPrint('DashboardTemplateService.deleteDashboard error: $e');
      return false;
    }
  }

  /// Select a dashboard for adding panels.
  void selectDashboard(String? dashboardId) {
    if (_selectedDashboardId != dashboardId) {
      _selectedDashboardId = dashboardId;
      notifyListeners();
    }
  }

  // -----------------------------------------------------------------------
  // Custom panel operations
  // -----------------------------------------------------------------------

  /// Add a metric chart panel to the selected dashboard.
  Future<Map<String, dynamic>?> addMetricPanel({
    required String dashboardId,
    required String title,
    required String metricType,
    String? resourceType,
    String aggregation = 'ALIGN_MEAN',
    List<String>? groupBy,
    String description = '',
    String? unit,
    String panelType = 'time_series',
  }) async {
    try {
      final body = <String, dynamic>{
        'title': title,
        'metric_type': metricType,
        'aggregation': aggregation,
        'description': description,
        'panel_type': panelType,
      };
      if (resourceType != null) body['resource_type'] = resourceType;
      if (groupBy != null) body['group_by'] = groupBy;
      if (unit != null) body['unit'] = unit;

      final response = await _client
          .post(
            Uri.parse('$_baseUrl/$dashboardId/panels/metric'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(body),
          )
          .timeout(ServiceConfig.defaultTimeout);

      if (response.statusCode == 200) {
        return await AppIsolate.run(_parseJsonMap, response.body);
      }
      debugPrint(
        'Add metric panel failed: ${response.statusCode} ${response.body}',
      );
      return null;
    } catch (e) {
      debugPrint('DashboardTemplateService.addMetricPanel error: $e');
      return null;
    }
  }

  /// Add a log viewer panel to a dashboard.
  Future<Map<String, dynamic>?> addLogPanel({
    required String dashboardId,
    required String title,
    required String logFilter,
    String? resourceType,
    List<String>? severityLevels,
    String description = '',
  }) async {
    try {
      final body = <String, dynamic>{
        'title': title,
        'log_filter': logFilter,
        'description': description,
      };
      if (resourceType != null) body['resource_type'] = resourceType;
      if (severityLevels != null) body['severity_levels'] = severityLevels;

      final response = await _client
          .post(
            Uri.parse('$_baseUrl/$dashboardId/panels/log'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(body),
          )
          .timeout(ServiceConfig.defaultTimeout);

      if (response.statusCode == 200) {
        return await AppIsolate.run(_parseJsonMap, response.body);
      }
      debugPrint(
        'Add log panel failed: ${response.statusCode} ${response.body}',
      );
      return null;
    } catch (e) {
      debugPrint('DashboardTemplateService.addLogPanel error: $e');
      return null;
    }
  }

  /// Add a trace list panel to a dashboard.
  Future<Map<String, dynamic>?> addTracePanel({
    required String dashboardId,
    required String title,
    required String traceFilter,
    String description = '',
  }) async {
    try {
      final body = <String, dynamic>{
        'title': title,
        'trace_filter': traceFilter,
        'description': description,
      };

      final response = await _client
          .post(
            Uri.parse('$_baseUrl/$dashboardId/panels/trace'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode(body),
          )
          .timeout(ServiceConfig.defaultTimeout);

      if (response.statusCode == 200) {
        return await AppIsolate.run(_parseJsonMap, response.body);
      }
      debugPrint(
        'Add trace panel failed: ${response.statusCode} ${response.body}',
      );
      return null;
    } catch (e) {
      debugPrint('DashboardTemplateService.addTracePanel error: $e');
      return null;
    }
  }

  @override
  void dispose() {
    _client.close();
    super.dispose();
  }
}
