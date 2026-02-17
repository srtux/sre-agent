import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/adk_schema.dart';
import '../models/time_range.dart';
import 'dashboard_state.dart';
import 'service_config.dart';

/// Service for executing manual telemetry queries from the explorer UI.
///
/// Calls backend API endpoints directly and feeds results into [DashboardState]
/// with [DataSource.manual] tracking.
class ExplorerQueryService {
  final DashboardState _dashboardState;
  final Future<http.Client> Function() _clientFactory;
  final String _baseUrl;

  ExplorerQueryService({
    required DashboardState dashboardState,
    required Future<http.Client> Function() clientFactory,
    String? baseUrl,
  }) : _dashboardState = dashboardState,
       _clientFactory = clientFactory,
       _baseUrl = baseUrl ?? ServiceConfig.baseUrl;

  /// Query time-series metrics.
  Future<void> queryMetrics({
    required String filter,
    String? projectId,
    TimeRange? timeRange,
  }) async {
    final range = timeRange ?? _dashboardState.timeRange;
    _dashboardState.setLoading(DashboardDataType.metrics, true);
    try {
      final body = jsonEncode({
        'filter': filter,
        'project_id': projectId,
        'minutes_ago': range.minutesAgo,
      });
      final response = await _post('/api/tools/metrics/query', body);
      final data = await compute(jsonDecode, response.body) as Map<String, dynamic>;

      // Backend returns a single transformed MetricSeries dict
      // with metric_name, points, labels keys.
      final series = MetricSeries.fromJson(data);
      _dashboardState.addMetricSeries(
        series,
        'manual_query',
        data,
        source: DataSource.manual,
      );

      _dashboardState.openDashboard();
      _dashboardState.setActiveTab(DashboardDataType.metrics);
    } catch (e) {
      _dashboardState.setError(DashboardDataType.metrics, e.toString());
      debugPrint('ExplorerQueryService.queryMetrics error: $e');
    } finally {
      _dashboardState.setLoading(DashboardDataType.metrics, false);
    }
  }

  /// Fetch raw log entries.
  Future<void> queryLogs({
    required String filter,
    String? projectId,
    String? pageToken,
  }) async {
    _dashboardState.setLoading(DashboardDataType.logs, true);
    try {
      final payload = <String, dynamic>{
        'filter': filter,
        'project_id': projectId,
      };
      if (pageToken != null) {
        payload['page_token'] = pageToken;
      }
      final body = jsonEncode(payload);
      final response = await _post('/api/tools/logs/query', body);
      final data = await compute(jsonDecode, response.body) as Map<String, dynamic>;

      final logData = LogEntriesData.fromJson(data);
      if (pageToken != null) {
        _dashboardState.appendLogEntries(
          logData,
          'manual_query',
          data,
          source: DataSource.manual,
        );
      } else {
        _dashboardState.addLogEntries(
          logData,
          'manual_query',
          data,
          source: DataSource.manual,
        );
      }

      _dashboardState.openDashboard();
      _dashboardState.setActiveTab(DashboardDataType.logs);
    } catch (e) {
      _dashboardState.setError(DashboardDataType.logs, e.toString());
      debugPrint('ExplorerQueryService.queryLogs error: $e');
    } finally {
      _dashboardState.setLoading(DashboardDataType.logs, false);
    }
  }

  /// Fetch raw log entries for a specific trace span.
  Future<List<LogEntry>> fetchLogsForSpan({
    required String traceId,
    required String spanId,
    String? projectId,
  }) async {
    try {
      final filter = 'trace="projects/${projectId ?? 'summitt-gcp'}/traces/$traceId" AND spanId="$spanId"';
      final payload = <String, dynamic>{
        'filter': filter,
        'project_id': projectId,
      };

      final body = jsonEncode(payload);
      final response = await _post('/api/tools/logs/query', body);
      final data = await compute(jsonDecode, response.body) as Map<String, dynamic>;

      final logData = LogEntriesData.fromJson(data);
      return logData.entries;
    } catch (e) {
      debugPrint('ExplorerQueryService.fetchLogsForSpan error: $e');
      return [];
    }
  }

  /// Fetch a distributed trace by ID.
  Future<void> queryTrace({required String traceId, String? projectId}) async {
    _dashboardState.setLoading(DashboardDataType.traces, true);
    try {
      var url = '$_baseUrl/api/tools/trace/${Uri.encodeComponent(traceId)}';
      if (projectId != null) {
        url += '?project_id=${Uri.encodeComponent(projectId)}';
      }

      final client = await _clientFactory();
      try {
        final response = await client
            .get(Uri.parse(url))
            .timeout(const Duration(seconds: 30));

        if (response.statusCode != 200) {
          throw Exception('Trace fetch failed: ${response.statusCode}');
        }

        final data = await compute(jsonDecode, response.body) as Map<String, dynamic>;
        final trace = Trace.fromJson(data);

        if (trace.spans.isNotEmpty) {
          _dashboardState.addTrace(
            trace,
            'manual_query',
            data,
            source: DataSource.manual,
          );
          _dashboardState.openDashboard();
          _dashboardState.setActiveTab(DashboardDataType.traces);
        }
      } finally {
        client.close();
      }
    } catch (e) {
      _dashboardState.setError(DashboardDataType.traces, e.toString());
      debugPrint('ExplorerQueryService.queryTrace error: $e');
    } finally {
      _dashboardState.setLoading(DashboardDataType.traces, false);
    }
  }

  /// Query traces using Cloud Trace filter syntax.
  ///
  /// Accepts Cloud Trace Query language filters such as:
  /// `+span:name:my_span`, `RootSpan:/api/v1`, `MinDuration:500ms`.
  Future<void> queryTraceFilter({
    required String filter,
    String? projectId,
    TimeRange? timeRange,
  }) async {
    final range = timeRange ?? _dashboardState.timeRange;
    _dashboardState.setLoading(DashboardDataType.traces, true);
    try {
      final body = jsonEncode({
        'filter': filter,
        'project_id': projectId,
        'minutes_ago': range.minutesAgo,
      });
      final response = await _post('/api/tools/traces/query', body);
      final listData = await compute(jsonDecode, response.body) as List<dynamic>;

      for (var item in listData) {
        final data = item as Map<String, dynamic>;
        final trace = Trace.fromJson(data);
        if (trace.spans.isNotEmpty) {
          _dashboardState.addTrace(
            trace,
            'manual_query',
            data,
            source: DataSource.manual,
          );
        }
      }

      _dashboardState.openDashboard();
      _dashboardState.setActiveTab(DashboardDataType.traces);
    } catch (e) {
      _dashboardState.setError(DashboardDataType.traces, e.toString());
      debugPrint('ExplorerQueryService.queryTraceFilter error: $e');
    } finally {
      _dashboardState.setLoading(DashboardDataType.traces, false);
    }
  }

  /// Query metrics using PromQL.
  Future<void> queryMetricsPromQL({
    required String query,
    String? projectId,
    TimeRange? timeRange,
  }) async {
    final range = timeRange ?? _dashboardState.timeRange;
    _dashboardState.setLoading(DashboardDataType.metrics, true);
    try {
      final body = jsonEncode({
        'query': query,
        'project_id': projectId,
        'minutes_ago': range.minutesAgo,
      });
      final response = await _post('/api/tools/metrics/promql', body);
      final data = await compute(jsonDecode, response.body) as Map<String, dynamic>;

      final series = MetricSeries.fromJson(data);
      _dashboardState.addMetricSeries(
        series,
        'manual_query_promql',
        data,
        source: DataSource.manual,
      );

      _dashboardState.openDashboard();
      _dashboardState.setActiveTab(DashboardDataType.metrics);
    } catch (e) {
      _dashboardState.setError(DashboardDataType.metrics, e.toString());
      debugPrint('ExplorerQueryService.queryMetricsPromQL error: $e');
    } finally {
      _dashboardState.setLoading(DashboardDataType.metrics, false);
    }
  }

  /// Execute a BigQuery SQL query and return tabular results.
  Future<void> queryBigQuery({required String sql, String? projectId}) async {
    _dashboardState.setLoading(DashboardDataType.analytics, true);
    try {
      final body = jsonEncode({'sql': sql, 'project_id': projectId});
      final response = await _post('/api/tools/bigquery/query', body);
      final data = await compute(jsonDecode, response.body) as Map<String, dynamic>;

      // Parse column names and row data from response
      final columns =
          (data['columns'] as List?)?.map((c) => c.toString()).toList() ?? [];
      final rows =
          (data['rows'] as List?)
              ?.map((r) => Map<String, dynamic>.from(r as Map))
              .toList() ??
          [];

      _dashboardState.addSqlResults(
        sql,
        columns,
        rows,
        'bigquery_sql_explorer',
        source: DataSource.manual,
      );
      _dashboardState.openDashboard();
      _dashboardState.setActiveTab(DashboardDataType.analytics);
    } catch (e) {
      _dashboardState.setError(DashboardDataType.analytics, e.toString());
      debugPrint('ExplorerQueryService.queryBigQuery error: $e');
    } finally {
      _dashboardState.setLoading(DashboardDataType.analytics, false);
    }
  }

  /// Query alerts/incidents.
  Future<void> queryAlerts({
    String? filter,
    String? projectId,
    TimeRange? timeRange,
  }) async {
    final range = timeRange ?? _dashboardState.timeRange;
    _dashboardState.setLoading(DashboardDataType.alerts, true);
    try {
      final body = jsonEncode({
        'filter': filter,
        'project_id': projectId,
        'minutes_ago': range.minutesAgo,
      });
      final response = await _post('/api/tools/alerts/query', body);
      final data = await compute(jsonDecode, response.body) as Map<String, dynamic>;

      final alertData = IncidentTimelineData.fromJson(data);
      _dashboardState.addAlerts(
        alertData,
        'manual_query',
        data,
        source: DataSource.manual,
      );

      _dashboardState.openDashboard();
      _dashboardState.setActiveTab(DashboardDataType.alerts);
    } catch (e) {
      _dashboardState.setError(DashboardDataType.alerts, e.toString());
      debugPrint('ExplorerQueryService.queryAlerts error: $e');
    } finally {
      _dashboardState.setLoading(DashboardDataType.alerts, false);
    }
  }

  Future<http.Response> _post(String path, String body) async {
    final client = await _clientFactory();
    try {
      final response = await client
          .post(
            Uri.parse('$_baseUrl$path'),
            headers: {'Content-Type': 'application/json'},
            body: body,
          )
          .timeout(ServiceConfig.defaultTimeout);
      if (response.statusCode != 200) {
        throw Exception('API error ${response.statusCode}: ${response.body}');
      }
      return response;
    } finally {
      client.close();
    }
  }

  Future<http.Response> _get(String path, {String? projectId}) async {
    final client = await _clientFactory();
    try {
      var url = '$_baseUrl$path';
      if (projectId != null) {
        final sep = url.contains('?') ? '&' : '?';
        url = '$url${sep}project_id=${Uri.encodeComponent(projectId)}';
      }
      final response = await client
          .get(Uri.parse(url))
          .timeout(ServiceConfig.defaultTimeout);
      if (response.statusCode != 200) {
        throw Exception('API error ${response.statusCode}: ${response.body}');
      }
      return response;
    } finally {
      client.close();
    }
  }

  /// Fetch datasets for the project.
  Future<List<String>> getDatasets({String? projectId}) async {
    try {
      final response = await _get(
        '/api/tools/bigquery/datasets',
        projectId: projectId,
      );
      final data = await compute(jsonDecode, response.body) as Map<String, dynamic>;
      final items = data['datasets'] as List?;
      return items?.map((e) => e.toString()).toList() ?? [];
    } catch (e) {
      debugPrint('ExplorerQueryService.getDatasets error: $e');
      return [];
    }
  }

  /// Fetch list of log names for the project.
  Future<List<String>> getLogNames({String? projectId}) async {
    try {
      final response = await _get(
        '/api/tools/logs/names',
        projectId: projectId,
      );
      final data = await compute(jsonDecode, response.body) as Map<String, dynamic>;
      final listData = data['logs'] as List<dynamic>? ?? [];
      return listData.map((e) => e.toString()).toList();
    } catch (e) {
      debugPrint('ExplorerQueryService.getLogNames error: $e');
      return [];
    }
  }

  /// Fetch list of monitored resource descriptors.
  Future<List<Map<String, dynamic>>> getResourceKeys({
    String? projectId,
  }) async {
    try {
      final response = await _get(
        '/api/tools/logs/resource_keys',
        projectId: projectId,
      );
      final data = await compute(jsonDecode, response.body) as Map<String, dynamic>;
      final listData = data['resource_keys'] as List<dynamic>? ?? [];
      return listData.map((e) => Map<String, dynamic>.from(e as Map)).toList();
    } catch (e) {
      debugPrint('ExplorerQueryService.getResourceKeys error: $e');
      return [];
    }
  }

  /// Fetch tables in a dataset.
  Future<List<String>> getTables({
    required String datasetId,
    String? projectId,
  }) async {
    try {
      final response = await _get(
        '/api/tools/bigquery/datasets/${Uri.encodeComponent(datasetId)}/tables',
        projectId: projectId,
      );
      final data = await compute(jsonDecode, response.body) as Map<String, dynamic>;
      final items = data['tables'] as List?;
      return items?.map((e) => e.toString()).toList() ?? [];
    } catch (e) {
      debugPrint('ExplorerQueryService.getTables error: $e');
      return [];
    }
  }

  Future<List<Map<String, dynamic>>?> getTableSchema({
    required String datasetId,
    required String tableId,
    String? projectId,
  }) async {
    try {
      final response = await _get(
        '/api/tools/bigquery/datasets/${Uri.encodeComponent(datasetId)}/tables/${Uri.encodeComponent(tableId)}/schema',
        projectId: projectId,
      );
      final data = await compute(jsonDecode, response.body) as Map<String, dynamic>;
      final items = data['schema'] as List?;
      return items?.map((e) => Map<String, dynamic>.from(e as Map)).toList() ??
          [];
    } catch (e) {
      debugPrint('ExplorerQueryService.getTableSchema error: $e');
      return null;
    }
  }

  /// Infer JSON keys for a specific column.
  Future<List<String>> getJsonKeys({
    required String datasetId,
    required String tableId,
    required String columnName,
    String? projectId,
  }) async {
    try {
      final response = await _get(
        '/api/tools/bigquery/datasets/${Uri.encodeComponent(datasetId)}/tables/${Uri.encodeComponent(tableId)}/columns/${Uri.encodeComponent(columnName)}/json-keys',
        projectId: projectId,
      );
      final data = await compute(jsonDecode, response.body) as Map<String, dynamic>;
      final listData = data['keys'] as List<dynamic>? ?? [];
      return listData.map((e) => e.toString()).toList();
    } catch (e) {
      debugPrint('ExplorerQueryService.getJsonKeys error: $e');
      return [];
    }
  }

  // =========================================================================
  // Default Data Loading (Auto-load on dashboard open)
  // =========================================================================

  /// Auto-load recent logs (past 15 minutes, all severities).
  ///
  /// Called when the logs panel is first displayed to provide an immediate
  /// overview of recent log activity in the selected project.
  Future<void> loadDefaultLogs({String? projectId}) async {
    _dashboardState.setLoading(DashboardDataType.logs, true);
    try {
      final payload = <String, dynamic>{
        'filter': '',
        'project_id': projectId,
        'minutes_ago': 15,
        'limit': 100,
      };
      final body = jsonEncode(payload);
      final response = await _post('/api/tools/logs/query', body);
      final data = await compute(jsonDecode, response.body) as Map<String, dynamic>;

      final logData = LogEntriesData.fromJson(data);
      _dashboardState.addLogEntries(
        logData,
        'auto_load',
        data,
        source: DataSource.manual,
      );

      _dashboardState.setLastQueryFilter(DashboardDataType.logs, '');
    } catch (e) {
      _dashboardState.setError(DashboardDataType.logs, e.toString());
      debugPrint('ExplorerQueryService.loadDefaultLogs error: $e');
    } finally {
      _dashboardState.setLoading(DashboardDataType.logs, false);
    }
  }

  /// Auto-load slow traces (latency > 3s, past 1 hour, up to 20 traces).
  ///
  /// Uses the Cloud Trace `MinDuration` filter to find only traces that
  /// exceed the 3-second threshold, providing an immediate view of
  /// performance bottlenecks.
  Future<void> loadSlowTraces({String? projectId}) async {
    _dashboardState.setLoading(DashboardDataType.traces, true);
    try {
      final body = jsonEncode({
        'filter': 'MinDuration:3s',
        'project_id': projectId,
        'minutes_ago': 60,
        'limit': 20,
      });
      final response = await _post('/api/tools/traces/query', body);
      final listData = await compute(jsonDecode, response.body) as List<dynamic>;

      for (var item in listData) {
        final data = item as Map<String, dynamic>;
        final trace = Trace.fromJson(data);
        if (trace.spans.isNotEmpty) {
          _dashboardState.addTrace(
            trace,
            'auto_load',
            data,
            source: DataSource.manual,
          );
        }
      }

      // Data loaded; the caller is responsible for tab/dashboard state.
    } catch (e) {
      _dashboardState.setError(DashboardDataType.traces, e.toString());
      debugPrint('ExplorerQueryService.loadSlowTraces error: $e');
    } finally {
      _dashboardState.setLoading(DashboardDataType.traces, false);
    }
  }

  /// Auto-load recent alerts (past 7 days).
  ///
  /// Provides an immediate overview of recent alerting activity
  /// when the alerts panel is first opened.
  Future<void> loadRecentAlerts({String? projectId}) async {
    _dashboardState.setLoading(DashboardDataType.alerts, true);
    try {
      /// 7 days = 10080 minutes.
      const sevenDaysInMinutes = 10080;
      final body = jsonEncode({
        'filter': '',
        'project_id': projectId,
        'minutes_ago': sevenDaysInMinutes,
      });
      final response = await _post('/api/tools/alerts/query', body);
      final data = await compute(jsonDecode, response.body) as Map<String, dynamic>;

      final alertData = IncidentTimelineData.fromJson(data);
      _dashboardState.addAlerts(
        alertData,
        'auto_load',
        data,
        source: DataSource.manual,
      );

      // Data loaded; the caller is responsible for tab/dashboard state.
    } catch (e) {
      _dashboardState.setError(DashboardDataType.alerts, e.toString());
      debugPrint('ExplorerQueryService.loadRecentAlerts error: $e');
    } finally {
      _dashboardState.setLoading(DashboardDataType.alerts, false);
    }
  }
}
