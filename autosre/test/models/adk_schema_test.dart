import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/models/adk_schema.dart';

void main() {
  // ===========================================================================
  // SpanInfo
  // ===========================================================================
  group('SpanInfo', () {
    test('fromJson parses valid data', () {
      final json = {
        'span_id': 'span-1',
        'trace_id': 'trace-1',
        'name': 'GET /api/users',
        'start_time': '2026-01-15T10:00:00Z',
        'end_time': '2026-01-15T10:00:01Z',
        'attributes': {'http.method': 'GET', 'http.status_code': 200},
        'status': 'OK',
        'parent_span_id': 'span-0',
      };
      final span = SpanInfo.fromJson(json);
      expect(span.spanId, 'span-1');
      expect(span.traceId, 'trace-1');
      expect(span.name, 'GET /api/users');
      expect(span.status, 'OK');
      expect(span.parentSpanId, 'span-0');
      expect(span.attributes['http.method'], 'GET');
    });

    test('fromJson provides defaults for missing fields', () {
      final span = SpanInfo.fromJson(const {});
      expect(span.spanId, '');
      expect(span.traceId, '');
      expect(span.name, '');
      expect(span.status, 'OK');
      expect(span.parentSpanId, isNull);
      expect(span.attributes, isEmpty);
    });

    test('fromJson handles invalid timestamps gracefully', () {
      final json = {
        'span_id': 's1',
        'start_time': 'not-a-date',
        'end_time': 'also-not-a-date',
      };
      final span = SpanInfo.fromJson(json);
      // Should not throw — falls back to DateTime.now()
      expect(span.startTime, isA<DateTime>());
      expect(span.endTime, isA<DateTime>());
    });

    test('fromJson handles null timestamps', () {
      final json = {'span_id': 's1', 'start_time': null, 'end_time': null};
      final span = SpanInfo.fromJson(json);
      expect(span.startTime, isA<DateTime>());
      expect(span.endTime, isA<DateTime>());
    });

    test('duration is computed correctly', () {
      final start = DateTime(2026, 1, 1, 10, 0, 0);
      final end = DateTime(2026, 1, 1, 10, 0, 2);
      final span = SpanInfo(
        spanId: 's1',
        traceId: 't1',
        name: 'test',
        startTime: start,
        endTime: end,
        attributes: {},
        status: 'OK',
      );
      expect(span.duration, const Duration(seconds: 2));
    });

    test('fromJson handles empty attributes', () {
      final json = {
        'span_id': 's1',
        'trace_id': 't1',
        'name': 'test',
        'start_time': '2026-01-01T00:00:00Z',
        'end_time': '2026-01-01T00:00:01Z',
        'attributes': null,
        'status': 'ERROR',
      };
      final span = SpanInfo.fromJson(json);
      expect(span.attributes, isEmpty);
      expect(span.status, 'ERROR');
    });
  });

  // ===========================================================================
  // Trace
  // ===========================================================================
  group('Trace', () {
    test('fromJson parses valid trace with spans', () {
      final json = {
        'trace_id': 'trace-abc',
        'spans': [
          {
            'span_id': 's1',
            'trace_id': 'trace-abc',
            'name': 'root',
            'start_time': '2026-01-01T00:00:00Z',
            'end_time': '2026-01-01T00:00:01Z',
            'attributes': <String, dynamic>{},
            'status': 'OK',
          },
          {
            'span_id': 's2',
            'trace_id': 'trace-abc',
            'name': 'child',
            'start_time': '2026-01-01T00:00:00Z',
            'end_time': '2026-01-01T00:00:00.500Z',
            'attributes': <String, dynamic>{},
            'status': 'OK',
            'parent_span_id': 's1',
          },
        ],
      };
      final trace = Trace.fromJson(json);
      expect(trace.traceId, 'trace-abc');
      expect(trace.spans.length, 2);
      expect(trace.spans[0].name, 'root');
      expect(trace.spans[1].parentSpanId, 's1');
    });

    test('fromJson handles null spans', () {
      final trace = Trace.fromJson({'trace_id': 'trace-1', 'spans': null});
      expect(trace.traceId, 'trace-1');
      expect(trace.spans, isEmpty);
    });

    test('fromJson handles missing spans key', () {
      final trace = Trace.fromJson({'trace_id': 'trace-1'});
      expect(trace.spans, isEmpty);
    });

    test('fromJson handles non-list spans', () {
      final trace = Trace.fromJson({'trace_id': 'trace-1', 'spans': 'invalid'});
      expect(trace.spans, isEmpty);
    });

    test('fromJson defaults trace_id when missing', () {
      final trace = Trace.fromJson(const {});
      expect(trace.traceId, 'unknown');
      expect(trace.spans, isEmpty);
    });

    test('fromJson skips malformed spans gracefully', () {
      final json = {
        'trace_id': 'trace-1',
        'spans': [
          {
            'span_id': 's1',
            'name': 'good-span',
            'start_time': '2026-01-01T00:00:00Z',
            'end_time': '2026-01-01T00:00:01Z',
          },
          'not-a-map',
          42,
          null,
        ],
      };
      final trace = Trace.fromJson(json);
      expect(trace.spans.length, 1);
      expect(trace.spans[0].name, 'good-span');
    });
  });

  // ===========================================================================
  // MetricPoint
  // ===========================================================================
  group('MetricPoint', () {
    test('fromJson parses valid data', () {
      final json = {
        'timestamp': '2026-01-01T10:00:00Z',
        'value': 42.5,
        'is_anomaly': true,
      };
      final point = MetricPoint.fromJson(json);
      expect(point.value, 42.5);
      expect(point.isAnomaly, isTrue);
      expect(point.timestamp.year, 2026);
    });

    test('fromJson handles integer value', () {
      final json = {'timestamp': '2026-01-01T10:00:00Z', 'value': 42};
      final point = MetricPoint.fromJson(json);
      expect(point.value, 42.0);
    });

    test('fromJson provides defaults for missing fields', () {
      final point = MetricPoint.fromJson(const {});
      expect(point.value, 0.0);
      expect(point.isAnomaly, isFalse);
      expect(point.timestamp, isA<DateTime>());
    });

    test('fromJson handles invalid timestamp', () {
      final point = MetricPoint.fromJson({'timestamp': 'bad', 'value': 1.0});
      expect(point.timestamp, isA<DateTime>());
      expect(point.value, 1.0);
    });

    test('fromJson handles null value', () {
      final point = MetricPoint.fromJson({
        'timestamp': '2026-01-01T10:00:00Z',
        'value': null,
      });
      expect(point.value, 0.0);
    });
  });

  // ===========================================================================
  // MetricSeries
  // ===========================================================================
  group('MetricSeries', () {
    test('fromJson parses valid series', () {
      final json = {
        'metric_name': 'cpu_utilization',
        'points': [
          {'timestamp': '2026-01-01T10:00:00Z', 'value': 45.0},
          {'timestamp': '2026-01-01T10:01:00Z', 'value': 55.0},
        ],
        'labels': {'instance': 'web-1', 'zone': 'us-central1-a'},
      };
      final series = MetricSeries.fromJson(json);
      expect(series.metricName, 'cpu_utilization');
      expect(series.points.length, 2);
      expect(series.points[0].value, 45.0);
      expect(series.labels['instance'], 'web-1');
    });

    test('fromJson handles empty points and labels', () {
      final series = MetricSeries.fromJson(const {});
      expect(series.metricName, '');
      expect(series.points, isEmpty);
      expect(series.labels, isEmpty);
    });

    test('fromJson handles null points', () {
      final json = {'metric_name': 'test', 'points': null, 'labels': null};
      final series = MetricSeries.fromJson(json);
      expect(series.points, isEmpty);
      expect(series.labels, isEmpty);
    });
  });

  // ===========================================================================
  // LogPattern
  // ===========================================================================
  group('LogPattern', () {
    test('fromJson parses valid data', () {
      final json = {
        'template': 'Connection refused to <*>',
        'count': 42,
        'severity_counts': {'ERROR': 30, 'WARNING': 12},
      };
      final pattern = LogPattern.fromJson(json);
      expect(pattern.template, 'Connection refused to <*>');
      expect(pattern.count, 42);
      expect(pattern.severityCounts['ERROR'], 30);
    });

    test('fromJson provides defaults', () {
      final pattern = LogPattern.fromJson(const {});
      expect(pattern.template, '');
      expect(pattern.count, 0);
      expect(pattern.severityCounts, isEmpty);
    });
  });


  // ===========================================================================
  // LogEntry
  // ===========================================================================
  group('LogEntry', () {
    test('fromJson parses valid entry', () {
      final json = {
        'insert_id': 'log-123',
        'timestamp': '2026-01-01T10:00:00Z',
        'severity': 'ERROR',
        'payload': 'Connection timed out',
        'resource_labels': {'project_id': 'test-project'},
        'resource_type': 'gce_instance',
        'trace_id': 'trace-1',
        'span_id': 'span-1',
        'http_request': {'method': 'GET', 'url': '/api/health'},
      };
      final entry = LogEntry.fromJson(json);
      expect(entry.insertId, 'log-123');
      expect(entry.severity, 'ERROR');
      expect(entry.payload, 'Connection timed out');
      expect(entry.resourceType, 'gce_instance');
      expect(entry.traceId, 'trace-1');
      expect(entry.spanId, 'span-1');
      expect(entry.httpRequest?['method'], 'GET');
    });

    test('fromJson provides defaults', () {
      final entry = LogEntry.fromJson(const {});
      expect(entry.insertId, '');
      expect(entry.severity, 'INFO');
      expect(entry.resourceType, 'unknown');
      expect(entry.traceId, isNull);
      expect(entry.spanId, isNull);
      expect(entry.httpRequest, isNull);
    });

    test('fromJson handles invalid timestamp', () {
      final entry = LogEntry.fromJson({'timestamp': 'invalid'});
      expect(entry.timestamp, isA<DateTime>());
    });

    test('isJsonPayload returns correct value', () {
      final textEntry = LogEntry(
        insertId: '1',
        timestamp: DateTime.now(),
        severity: 'INFO',
        payload: 'text message',
        resourceLabels: {},
        resourceType: 'test',
      );
      expect(textEntry.isJsonPayload, isFalse);

      final jsonEntry = LogEntry(
        insertId: '2',
        timestamp: DateTime.now(),
        severity: 'INFO',
        payload: {'message': 'structured log', 'level': 'info'},
        resourceLabels: {},
        resourceType: 'test',
      );
      expect(jsonEntry.isJsonPayload, isTrue);
    });

    test('payloadPreview handles string payload', () {
      final entry = LogEntry(
        insertId: '1',
        timestamp: DateTime.now(),
        severity: 'INFO',
        payload: 'Short message',
        resourceLabels: {},
        resourceType: 'test',
      );
      expect(entry.payloadPreview, 'Short message');
    });

    test('payloadPreview truncates long string payload', () {
      final longString = 'A' * 300;
      final entry = LogEntry(
        insertId: '1',
        timestamp: DateTime.now(),
        severity: 'INFO',
        payload: longString,
        resourceLabels: {},
        resourceType: 'test',
      );
      expect(entry.payloadPreview.length, 203); // 200 + '...'
      expect(entry.payloadPreview.endsWith('...'), isTrue);
    });

    test('payloadPreview extracts message from Map payload', () {
      final entry = LogEntry(
        insertId: '1',
        timestamp: DateTime.now(),
        severity: 'INFO',
        payload: {'message': 'Structured log message'},
        resourceLabels: {},
        resourceType: 'test',
      );
      expect(entry.payloadPreview, 'Structured log message');
    });

    test('payloadPreview uses msg key fallback', () {
      final entry = LogEntry(
        insertId: '1',
        timestamp: DateTime.now(),
        severity: 'INFO',
        payload: {'msg': 'Alternative msg key'},
        resourceLabels: {},
        resourceType: 'test',
      );
      expect(entry.payloadPreview, 'Alternative msg key');
    });

    test('payloadPreview handles null payload', () {
      final entry = LogEntry(
        insertId: '1',
        timestamp: DateTime.now(),
        severity: 'INFO',
        payload: null,
        resourceLabels: {},
        resourceType: 'test',
      );
      expect(entry.payloadPreview, '');
    });
  });

  // ===========================================================================
  // LogEntriesData
  // ===========================================================================
  group('LogEntriesData', () {
    test('fromJson parses valid data', () {
      final json = {
        'entries': [
          {
            'insert_id': 'id1',
            'timestamp': '2026-01-01T00:00:00Z',
            'severity': 'INFO',
            'payload': 'test',
            'resource_labels': <String, String>{},
            'resource_type': 'test',
          },
        ],
        'filter': 'severity="ERROR"',
        'project_id': 'my-project',
        'next_page_token': 'token123',
      };
      final data = LogEntriesData.fromJson(json);
      expect(data.entries.length, 1);
      expect(data.filter, 'severity="ERROR"');
      expect(data.projectId, 'my-project');
      expect(data.nextPageToken, 'token123');
    });

    test('fromJson handles empty entries', () {
      final data = LogEntriesData.fromJson(const {});
      expect(data.entries, isEmpty);
      expect(data.filter, isNull);
      expect(data.projectId, isNull);
      expect(data.nextPageToken, isNull);
    });
  });

  // ===========================================================================
  // ToolLog
  // ===========================================================================
  group('ToolLog', () {
    test('fromJson parses valid data', () {
      final json = {
        'tool_name': 'fetch_trace',
        'args': {'trace_id': 'abc123'},
        'status': 'completed',
        'result': 'Found 15 spans',
        'timestamp': '2026-01-01T10:00:00Z',
        'duration': '250ms',
      };
      final log = ToolLog.fromJson(json);
      expect(log.toolName, 'fetch_trace');
      expect(log.args['trace_id'], 'abc123');
      expect(log.status, 'completed');
      expect(log.result, 'Found 15 spans');
      expect(log.timestamp, '2026-01-01T10:00:00Z');
      expect(log.duration, '250ms');
    });

    test('fromJson handles missing optional fields', () {
      final json = {'tool_name': 'test_tool', 'args': {}, 'status': 'running'};
      final log = ToolLog.fromJson(json);
      expect(log.toolName, 'test_tool');
      expect(log.result, isNull);
      expect(log.timestamp, isNull);
      expect(log.duration, isNull);
    });

    test('fromJson stringifies complex result', () {
      final json = {
        'tool_name': 'test',
        'args': {},
        'status': 'completed',
        'result': {'key': 'value'},
      };
      final log = ToolLog.fromJson(json);
      expect(log.result, isA<String>());
      expect(log.result, contains('key'));
    });

    test('fromJson handles null args', () {
      final json = {'tool_name': 'test', 'args': null, 'status': 'error'};
      final log = ToolLog.fromJson(json);
      expect(log.args, isEmpty);
      expect(log.status, 'error');
    });
  });

  // ===========================================================================
  // DashboardMetric
  // ===========================================================================
  group('DashboardMetric', () {
    test('fromJson parses valid data', () {
      final json = {
        'id': 'm1',
        'name': 'CPU Utilization',
        'unit': '%',
        'current_value': 75.5,
        'previous_value': 60.0,
        'threshold': 90.0,
        'status': 'warning',
        'anomaly_description': 'Unusual spike detected',
        'history': [
          {'timestamp': '2026-01-01T10:00:00Z', 'value': 60.0},
          {'timestamp': '2026-01-01T10:01:00Z', 'value': 75.5},
        ],
      };
      final metric = DashboardMetric.fromJson(json);
      expect(metric.id, 'm1');
      expect(metric.name, 'CPU Utilization');
      expect(metric.unit, '%');
      expect(metric.currentValue, 75.5);
      expect(metric.previousValue, 60.0);
      expect(metric.threshold, 90.0);
      expect(metric.status, 'warning');
      expect(metric.anomalyDescription, 'Unusual spike detected');
      expect(metric.history.length, 2);
    });

    test('fromJson provides defaults', () {
      final metric = DashboardMetric.fromJson(const {});
      expect(metric.id, '');
      expect(metric.name, '');
      expect(metric.unit, '');
      expect(metric.currentValue, 0);
      expect(metric.previousValue, isNull);
      expect(metric.threshold, isNull);
      expect(metric.status, 'normal');
      expect(metric.anomalyDescription, isNull);
      expect(metric.history, isEmpty);
    });

    test('changePercent calculates correctly', () {
      final metric = DashboardMetric(
        id: 'm1',
        name: 'test',
        unit: '%',
        currentValue: 120,
        previousValue: 100,
      );
      expect(metric.changePercent, 20.0);
    });

    test('changePercent returns 0 when no previous value', () {
      final metric = DashboardMetric(
        id: 'm1',
        name: 'test',
        unit: '%',
        currentValue: 120,
      );
      expect(metric.changePercent, 0);
    });

    test('changePercent returns 0 when previous value is zero', () {
      final metric = DashboardMetric(
        id: 'm1',
        name: 'test',
        unit: '%',
        currentValue: 120,
        previousValue: 0,
      );
      expect(metric.changePercent, 0);
    });
  });

  // ===========================================================================
  // TimelineEvent
  // ===========================================================================
  group('TimelineEvent', () {
    test('fromJson parses valid data', () {
      final json = {
        'id': 'ev1',
        'timestamp': '2026-01-01T10:00:00Z',
        'type': 'alert',
        'title': 'High Error Rate',
        'description': 'Error rate exceeded 5%',
        'severity': 'critical',
        'metadata': {'alert_id': 'alert-123'},
        'is_correlated': true,
      };
      final event = TimelineEvent.fromJson(json);
      expect(event.id, 'ev1');
      expect(event.type, 'alert');
      expect(event.title, 'High Error Rate');
      expect(event.description, 'Error rate exceeded 5%');
      expect(event.severity, 'critical');
      expect(event.isCorrelatedToIncident, isTrue);
      expect(event.metadata?['alert_id'], 'alert-123');
    });

    test('fromJson provides defaults', () {
      final event = TimelineEvent.fromJson(const {});
      expect(event.id, '');
      expect(event.type, 'info');
      expect(event.title, '');
      expect(event.description, isNull);
      expect(event.severity, 'info');
      expect(event.isCorrelatedToIncident, isFalse);
    });

    test('fromJson handles invalid timestamp', () {
      final event = TimelineEvent.fromJson({'timestamp': 'bad-date'});
      expect(event.timestamp, isA<DateTime>());
    });
  });

  // ===========================================================================
  // IncidentTimelineData
  // ===========================================================================
  group('IncidentTimelineData', () {
    test('fromJson parses valid data', () {
      final json = {
        'incident_id': 'inc-1',
        'title': 'Production Outage',
        'start_time': '2026-01-01T09:00:00Z',
        'end_time': '2026-01-01T10:30:00Z',
        'status': 'resolved',
        'events': [
          {
            'id': 'e1',
            'timestamp': '2026-01-01T09:00:00Z',
            'type': 'alert',
            'title': 'Alert Fired',
            'severity': 'critical',
          },
        ],
        'root_cause': 'Database connection pool exhaustion',
        'ttd_seconds': 120,
        'ttm_seconds': 3600,
      };
      final data = IncidentTimelineData.fromJson(json);
      expect(data.incidentId, 'inc-1');
      expect(data.title, 'Production Outage');
      expect(data.status, 'resolved');
      expect(data.events.length, 1);
      expect(data.rootCause, 'Database connection pool exhaustion');
      expect(data.timeToDetect, const Duration(seconds: 120));
      expect(data.timeToMitigate, const Duration(seconds: 3600));
      expect(data.endTime, isNotNull);
    });

    test('fromJson provides defaults', () {
      final data = IncidentTimelineData.fromJson(const {});
      expect(data.incidentId, '');
      expect(data.title, 'Incident');
      expect(data.status, 'ongoing');
      expect(data.events, isEmpty);
      expect(data.rootCause, isNull);
      expect(data.timeToDetect, isNull);
      expect(data.timeToMitigate, isNull);
      expect(data.endTime, isNull);
    });

    test('fromJson handles invalid end_time', () {
      final json = {
        'start_time': '2026-01-01T09:00:00Z',
        'end_time': 'not-a-date',
      };
      final data = IncidentTimelineData.fromJson(json);
      expect(data.endTime, isNull);
    });
  });

  // ===========================================================================
  // VegaChartData
  // ===========================================================================
  group('VegaChartData', () {
    test('fromJson parses valid data', () {
      final json = {
        'question': 'What is the error rate?',
        'answer': 'The error rate is 5%',
        'agent_id': 'agent-1',
        'project_id': 'proj-1',
        'vega_lite_charts': [
          {'mark': 'bar', 'encoding': {}},
        ],
      };
      final data = VegaChartData.fromJson(json);
      expect(data.question, 'What is the error rate?');
      expect(data.answer, 'The error rate is 5%');
      expect(data.agentId, 'agent-1');
      expect(data.projectId, 'proj-1');
      expect(data.hasCharts, isTrue);
      expect(data.vegaLiteCharts.length, 1);
    });

    test('fromJson provides defaults', () {
      final data = VegaChartData.fromJson(const {});
      expect(data.question, '');
      expect(data.answer, '');
      expect(data.agentId, isNull);
      expect(data.hasCharts, isFalse);
    });
  });

  // ===========================================================================
  // AgentTraceNode
  // ===========================================================================
  group('AgentTraceNode', () {
    test('fromJson parses valid data', () {
      final json = {
        'span_id': 'span-1',
        'parent_span_id': 'span-0',
        'name': 'fetch_trace',
        'kind': 'tool_execution',
        'operation': 'execute_tool',
        'start_offset_ms': 100.0,
        'duration_ms': 250.0,
        'depth': 2,
        'input_tokens': 1500,
        'output_tokens': 500,
        'model_used': 'gemini-2.0-flash',
        'tool_name': 'fetch_trace',
        'agent_name': 'trace_panel',
        'has_error': false,
      };
      final node = AgentTraceNode.fromJson(json);
      expect(node.spanId, 'span-1');
      expect(node.parentSpanId, 'span-0');
      expect(node.kind, 'tool_execution');
      expect(node.startOffsetMs, 100.0);
      expect(node.durationMs, 250.0);
      expect(node.depth, 2);
      expect(node.inputTokens, 1500);
      expect(node.outputTokens, 500);
      expect(node.modelUsed, 'gemini-2.0-flash');
      expect(node.hasError, isFalse);
    });

    test('fromJson provides defaults', () {
      final node = AgentTraceNode.fromJson(const {});
      expect(node.spanId, '');
      expect(node.parentSpanId, isNull);
      expect(node.kind, 'unknown');
      expect(node.operation, 'unknown');
      expect(node.startOffsetMs, 0);
      expect(node.durationMs, 0);
      expect(node.depth, 0);
      expect(node.inputTokens, isNull);
      expect(node.outputTokens, isNull);
      expect(node.hasError, isFalse);
    });
  });

  // ===========================================================================
  // AgentTraceData
  // ===========================================================================
  group('AgentTraceData', () {
    test('fromJson parses valid data', () {
      final json = {
        'trace_id': 'trace-1',
        'root_agent_name': 'sre_agent',
        'nodes': [
          {'span_id': 's1', 'name': 'root', 'kind': 'agent_invocation'},
        ],
        'total_input_tokens': 5000,
        'total_output_tokens': 2000,
        'total_duration_ms': 3500.0,
        'llm_call_count': 3,
        'tool_call_count': 5,
        'unique_agents': ['sre_agent', 'trace_panel'],
        'unique_tools': ['fetch_trace', 'analyze_trace'],
        'anti_patterns': [
          {'name': 'excessive_tool_calls', 'severity': 'warning'},
        ],
      };
      final data = AgentTraceData.fromJson(json);
      expect(data.traceId, 'trace-1');
      expect(data.rootAgentName, 'sre_agent');
      expect(data.nodes.length, 1);
      expect(data.totalInputTokens, 5000);
      expect(data.totalOutputTokens, 2000);
      expect(data.totalDurationMs, 3500.0);
      expect(data.llmCallCount, 3);
      expect(data.toolCallCount, 5);
      expect(data.uniqueAgents.length, 2);
      expect(data.uniqueTools.length, 2);
      expect(data.antiPatterns.length, 1);
    });

    test('fromJson provides defaults', () {
      final data = AgentTraceData.fromJson(const {});
      expect(data.traceId, '');
      expect(data.rootAgentName, isNull);
      expect(data.nodes, isEmpty);
      expect(data.totalInputTokens, 0);
      expect(data.totalOutputTokens, 0);
      expect(data.totalDurationMs, 0);
      expect(data.llmCallCount, 0);
      expect(data.toolCallCount, 0);
      expect(data.uniqueAgents, isEmpty);
      expect(data.uniqueTools, isEmpty);
      expect(data.antiPatterns, isEmpty);
    });
  });

  // ===========================================================================
  // AgentGraphNode and AgentGraphEdge
  // ===========================================================================
  group('AgentGraphNode', () {
    test('fromJson parses valid data', () {
      final node = AgentGraphNode.fromJson({
        'id': 'n1',
        'label': 'SRE Agent',
        'type': 'agent',
        'total_tokens': 5000,
        'call_count': 3,
        'has_error': false,
      });
      expect(node.id, 'n1');
      expect(node.label, 'SRE Agent');
      expect(node.type, 'agent');
      expect(node.totalTokens, 5000);
      expect(node.callCount, 3);
      expect(node.hasError, isFalse);
    });

    test('fromJson provides defaults', () {
      final node = AgentGraphNode.fromJson(const {});
      expect(node.id, '');
      expect(node.label, '');
      expect(node.type, 'unknown');
      expect(node.totalTokens, isNull);
      expect(node.callCount, isNull);
      expect(node.hasError, isFalse);
    });
  });

  group('AgentGraphEdge', () {
    test('fromJson parses valid data', () {
      final edge = AgentGraphEdge.fromJson({
        'source_id': 'n1',
        'target_id': 'n2',
        'label': 'invokes',
        'call_count': 5,
        'avg_duration_ms': 150.0,
        'total_tokens': 3000,
        'has_error': true,
      });
      expect(edge.sourceId, 'n1');
      expect(edge.targetId, 'n2');
      expect(edge.label, 'invokes');
      expect(edge.callCount, 5);
      expect(edge.avgDurationMs, 150.0);
      expect(edge.totalTokens, 3000);
      expect(edge.hasError, isTrue);
    });

    test('fromJson provides defaults', () {
      final edge = AgentGraphEdge.fromJson(const {});
      expect(edge.sourceId, '');
      expect(edge.targetId, '');
      expect(edge.label, '');
      expect(edge.callCount, 0);
      expect(edge.avgDurationMs, 0);
      expect(edge.totalTokens, isNull);
      expect(edge.hasError, isFalse);
    });
  });

  // ===========================================================================
  // AgentGraphData
  // ===========================================================================
  group('AgentGraphData', () {
    test('fromJson parses valid data', () {
      final json = {
        'nodes': [
          {'id': 'n1', 'label': 'Agent', 'type': 'agent'},
        ],
        'edges': [
          {
            'source_id': 'n1',
            'target_id': 'n2',
            'label': 'calls',
            'call_count': 1,
            'avg_duration_ms': 100.0,
          },
        ],
        'root_agent_name': 'sre_agent',
      };
      final data = AgentGraphData.fromJson(json);
      expect(data.nodes.length, 1);
      expect(data.edges.length, 1);
      expect(data.rootAgentName, 'sre_agent');
    });

    test('fromJson provides defaults', () {
      final data = AgentGraphData.fromJson(const {});
      expect(data.nodes, isEmpty);
      expect(data.edges, isEmpty);
      expect(data.rootAgentName, isNull);
    });
  });

  // ===========================================================================
  // MetricsDashboardData
  // ===========================================================================
  group('MetricsDashboardData', () {
    test('fromJson parses valid data', () {
      final json = {
        'title': 'Service Health',
        'service_name': 'checkout-service',
        'metrics': [
          {
            'id': 'm1',
            'name': 'Latency',
            'unit': 'ms',
            'current_value': 150,
            'status': 'normal',
          },
        ],
        'last_updated': '2026-01-01T10:00:00Z',
      };
      final data = MetricsDashboardData.fromJson(json);
      expect(data.title, 'Service Health');
      expect(data.serviceName, 'checkout-service');
      expect(data.metrics.length, 1);
      expect(data.lastUpdated, isNotNull);
    });

    test('fromJson provides defaults', () {
      final data = MetricsDashboardData.fromJson(const {});
      expect(data.title, 'Metrics Dashboard');
      expect(data.serviceName, isNull);
      expect(data.metrics, isEmpty);
      expect(data.lastUpdated, isNull);
    });
  });

  // ===========================================================================
  // MetricDataPoint
  // ===========================================================================
  group('MetricDataPoint', () {
    test('fromJson parses valid data', () {
      final point = MetricDataPoint.fromJson({
        'timestamp': '2026-01-01T10:00:00Z',
        'value': 42.5,
      });
      expect(point.value, 42.5);
      expect(point.timestamp.year, 2026);
    });

    test('fromJson provides defaults', () {
      final point = MetricDataPoint.fromJson(const {});
      expect(point.value, 0);
      expect(point.timestamp, isA<DateTime>());
    });
  });
}
