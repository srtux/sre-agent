import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../utils/isolate_helper.dart';

import '../models/adk_schema.dart';
import '../models/time_range.dart';
import 'dashboard_state.dart';
import 'service_config.dart';

// --- Background Isolate Parsers ---
// These top-level functions execute in a separate isolate to prevent
// heavy JSON parsing and model formatting from blocking the UI thread.

MetricSeries _parseMetrics(String body) {
  final data = jsonDecode(body) as Map<String, dynamic>;
  return MetricSeries.fromJson(data);
}

LogEntriesData _parseLogEntries(String body) {
  final data = jsonDecode(body) as Map<String, dynamic>;
  return LogEntriesData.fromJson(data);
}

Trace _parseTrace(String body) {
  final data = jsonDecode(body) as Map<String, dynamic>;
  return Trace.fromJson(data);
}

List<Trace> _parseTraceList(String body) {
  final listData = jsonDecode(body) as List<dynamic>;
  final traces = <Trace>[];
  for (final item in listData) {
    traces.add(Trace.fromJson(item as Map<String, dynamic>));
  }
  return traces;
}

Map<String, dynamic> _parseBigQueryResults(String body) {
  return jsonDecode(body) as Map<String, dynamic>;
}

IncidentTimelineData _parseAlerts(String body) {
  final data = jsonDecode(body) as Map<String, dynamic>;
  return IncidentTimelineData.fromJson(data);
}

List<String> _parseStringList(Map<String, dynamic> args) {
  final body = args['body'] as String;
  final key = args['key'] as String;
  final data = jsonDecode(body) as Map<String, dynamic>;
  final items = data[key] as List?;
  return items?.map((e) => e.toString()).toList() ?? [];
}

List<Map<String, dynamic>> _parseResourceKeys(String body) {
  final data = jsonDecode(body) as Map<String, dynamic>;
  final listData = data['resource_keys'] as List<dynamic>? ?? [];
  return listData.map((e) => Map<String, dynamic>.from(e as Map)).toList();
}

List<Map<String, dynamic>> _parseTableSchema(String body) {
  final data = jsonDecode(body) as Map<String, dynamic>;
  final items = data['schema'] as List?;
  return items?.map((e) => Map<String, dynamic>.from(e as Map)).toList() ?? [];
}


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

      // Decode JSON and map to MetricSeries on a background thread
      final series = await compute(_parseMetrics, response.body);

      _dashboardState.addMetricSeries(
        series,
        'manual_query',
        series.toJson(), // The original mapped json dict structure
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

  Future<void> queryLogs({
    required String filter,
    String? projectId,
    String? pageToken,
    int? limit,
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
      if (limit != null) {
        payload['limit'] = limit;
      }
      final body = jsonEncode(payload);
      final response = await _post('/api/tools/logs/query', body);

      // Run background parsing
      final logData = await AppIsolate.run(_parseLogEntries, response.body);

      if (pageToken != null) {
        _dashboardState.appendLogEntries(
          logData,
          'manual_query',
          logData.toJson(),
          source: DataSource.manual,
        );
      } else {
        _dashboardState.addLogEntries(
          logData,
          'manual_query',
          logData.toJson(),
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
      final logData = await AppIsolate.run(_parseLogEntries, response.body);

      return logData.entries;
    } catch (e) {
      debugPrint('ExplorerQueryService.fetchLogsForSpan error: $e');
      return [];
    }
  }

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

        final trace = await AppIsolate.run(_parseTrace, response.body);

        if (trace.spans.isNotEmpty) {
          _dashboardState.addTrace(
            trace,
            'manual_query',
            trace.toJson(),
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
      final traces = await AppIsolate.run(_parseTraceList, response.body);

      for (var trace in traces) {
        if (trace.spans.isNotEmpty) {
          _dashboardState.addTrace(
            trace,
            'manual_query',
            trace.toJson(),
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

      final series = await AppIsolate.run(_parseMetrics, response.body);

      _dashboardState.addMetricSeries(
        series,
        'manual_query_promql',
        series.toJson(),
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

  Future<void> queryBigQuery({required String sql, String? projectId}) async {
    _dashboardState.setLoading(DashboardDataType.analytics, true);
    try {
      final body = jsonEncode({'sql': sql, 'project_id': projectId});
      final response = await _post('/api/tools/bigquery/query', body);

      final data = await AppIsolate.run(_parseBigQueryResults, response.body);

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

      final alertData = await AppIsolate.run(_parseAlerts, response.body);

      _dashboardState.addAlerts(
        alertData,
        'manual_query',
        alertData.toJson(),
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

  Future<List<String>> getDatasets({String? projectId}) async {
    try {
      final response = await _get(
        '/api/tools/bigquery/datasets',
        projectId: projectId,
      );
      return await AppIsolate.run(_parseStringList, {'body': response.body, 'key': 'datasets'});
    } catch (e) {
      debugPrint('ExplorerQueryService.getDatasets error: $e');
      return [];
    }
  }

  Future<List<String>> getLogNames({String? projectId}) async {
    try {
      final response = await _get(
        '/api/tools/logs/names',
        projectId: projectId,
      );
      return await AppIsolate.run(_parseStringList, {'body': response.body, 'key': 'logs'});
    } catch (e) {
      debugPrint('ExplorerQueryService.getLogNames error: $e');
      return [];
    }
  }

  Future<List<Map<String, dynamic>>> getResourceKeys({
    String? projectId,
  }) async {
    try {
      final response = await _get(
        '/api/tools/logs/resource_keys',
        projectId: projectId,
      );
      return await AppIsolate.run(_parseResourceKeys, response.body);
    } catch (e) {
      debugPrint('ExplorerQueryService.getResourceKeys error: $e');
      return [];
    }
  }

  Future<List<String>> getTables({
    required String datasetId,
    String? projectId,
  }) async {
    try {
      final response = await _get(
        '/api/tools/bigquery/datasets/${Uri.encodeComponent(datasetId)}/tables',
        projectId: projectId,
      );
      return await AppIsolate.run(_parseStringList, {'body': response.body, 'key': 'tables'});
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
      return await AppIsolate.run(_parseTableSchema, response.body);
    } catch (e) {
      debugPrint('ExplorerQueryService.getTableSchema error: $e');
      return null;
    }
  }

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
      return await AppIsolate.run(_parseStringList, {'body': response.body, 'key': 'keys'});
    } catch (e) {
      debugPrint('ExplorerQueryService.getJsonKeys error: $e');
      return [];
    }
  }

  // =========================================================================
  // Default Data Loading (Auto-load on dashboard open)
  // =========================================================================

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

      final logData = await AppIsolate.run(_parseLogEntries, response.body);

      _dashboardState.addLogEntries(
        logData,
        'auto_load',
        logData.toJson(),
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

      final traces = await AppIsolate.run(_parseTraceList, response.body);

      for (var trace in traces) {
        if (trace.spans.isNotEmpty) {
          _dashboardState.addTrace(
            trace,
            'auto_load',
            trace.toJson(),
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

      final alertData = await AppIsolate.run(_parseAlerts, response.body);

      _dashboardState.addAlerts(
        alertData,
        'auto_load',
        alertData.toJson(),
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
