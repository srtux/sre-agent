import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/models/adk_schema.dart';

/// Tests for type coercion, wrong-type handling, and bug fix verification.
void main() {
  // ===========================================================================
  // ToolLog — null safety fix for tool_name
  // ===========================================================================
  group('ToolLog fromJson null safety', () {
    test('handles missing tool_name without crash', () {
      final log = ToolLog.fromJson({'status': 'running', 'args': {}});
      expect(log.toolName, '');
      expect(log.status, 'running');
    });

    test('handles null tool_name', () {
      final log = ToolLog.fromJson({
        'tool_name': null,
        'args': {},
        'status': 'completed',
      });
      expect(log.toolName, '');
    });

    test('handles completely empty json', () {
      final log = ToolLog.fromJson(const {});
      expect(log.toolName, '');
      expect(log.status, 'unknown');
      expect(log.args, isEmpty);
      expect(log.result, isNull);
    });
  });

  // ===========================================================================
  // LogEntry — resource_labels type safety fix
  // ===========================================================================
  group('LogEntry fromJson resource_labels safety', () {
    test('handles non-string values in resource_labels', () {
      final entry = LogEntry.fromJson({
        'insert_id': 'id1',
        'timestamp': '2026-01-01T00:00:00Z',
        'severity': 'INFO',
        'payload': 'test',
        'resource_labels': {'project_id': 'proj', 'count': 42, 'flag': true},
        'resource_type': 'gce',
      });
      // Should not throw — converts non-strings to string
      expect(entry.resourceLabels['project_id'], 'proj');
      expect(entry.resourceLabels['count'], '42');
      expect(entry.resourceLabels['flag'], 'true');
    });

    test('handles null resource_labels', () {
      final entry = LogEntry.fromJson({
        'insert_id': 'id1',
        'timestamp': '2026-01-01T00:00:00Z',
        'severity': 'INFO',
        'payload': 'test',
        'resource_labels': null,
        'resource_type': 'gce',
      });
      expect(entry.resourceLabels, isEmpty);
    });

    test('handles non-Map http_request', () {
      final entry = LogEntry.fromJson({
        'insert_id': 'id1',
        'timestamp': '2026-01-01T00:00:00Z',
        'severity': 'INFO',
        'payload': 'test',
        'resource_labels': {},
        'resource_type': 'gce',
        'http_request': 'not a map',
      });
      expect(entry.httpRequest, isNull);
    });
  });

  // ===========================================================================
  // MetricsDashboardData — DateTime.parse try/catch fix
  // ===========================================================================
  group('MetricsDashboardData fromJson last_updated safety', () {
    test('handles invalid last_updated date', () {
      final data = MetricsDashboardData.fromJson({
        'title': 'Test',
        'metrics': [],
        'last_updated': 'not-a-date',
      });
      expect(data.lastUpdated, isNull);
    });

    test('handles numeric last_updated', () {
      final data = MetricsDashboardData.fromJson({
        'title': 'Test',
        'metrics': [],
        'last_updated': 12345,
      });
      // toString() of 12345 is not a valid date
      expect(data.lastUpdated, isNull);
    });

    test('handles valid last_updated', () {
      final data = MetricsDashboardData.fromJson({
        'title': 'Test',
        'metrics': [],
        'last_updated': '2026-01-01T10:00:00Z',
      });
      expect(data.lastUpdated, isNotNull);
      expect(data.lastUpdated!.year, 2026);
    });
  });

  // ===========================================================================
  // CouncilSynthesisData — rounds num-to-int coercion fix
  // ===========================================================================
  group('CouncilSynthesisData fromJson type coercion', () {
    test('handles rounds as double (JSON number coercion)', () {
      final data = CouncilSynthesisData.fromJson({
        'synthesis': 'test',
        'overall_severity': 'info',
        'overall_confidence': 0.5,
        'mode': 'standard',
        'rounds': 3.0,
        'panels': [],
      });
      expect(data.rounds, 3);
    });

    test('handles rounds as int', () {
      final data = CouncilSynthesisData.fromJson({
        'synthesis': 'test',
        'rounds': 2,
        'panels': [],
      });
      expect(data.rounds, 2);
    });

    test('handles missing rounds', () {
      final data = CouncilSynthesisData.fromJson({
        'synthesis': 'test',
        'panels': [],
      });
      expect(data.rounds, 1);
    });
  });

  // ===========================================================================
  // List parser type safety — non-Map items in lists
  // ===========================================================================
  group('List parser type safety', () {
    test('MetricSeries.fromJson skips non-Map items in points', () {
      final series = MetricSeries.fromJson({
        'metric_name': 'cpu',
        'points': [
          {'timestamp': '2026-01-01T00:00:00Z', 'value': 1.0},
          'not a map',
          42,
          null,
          {'timestamp': '2026-01-01T00:01:00Z', 'value': 2.0},
        ],
        'labels': {},
      });
      expect(series.points.length, 2);
      expect(series.points[0].value, 1.0);
      expect(series.points[1].value, 2.0);
    });

    test('RemediationPlan.fromJson skips non-Map items in steps', () {
      final plan = RemediationPlan.fromJson({
        'issue': 'test',
        'risk': 'low',
        'steps': [
          {'command': 'cmd1', 'description': 'desc1'},
          'invalid',
          null,
          {'command': 'cmd2', 'description': 'desc2'},
        ],
      });
      expect(plan.steps.length, 2);
    });

    test('LogEntriesData.fromJson skips non-Map entries', () {
      final data = LogEntriesData.fromJson({
        'entries': [
          {
            'insert_id': 'id1',
            'timestamp': '2026-01-01T00:00:00Z',
            'severity': 'INFO',
            'payload': 'test',
            'resource_labels': {},
            'resource_type': 'gce',
          },
          'not a map',
          42,
        ],
      });
      expect(data.entries.length, 1);
    });

    test('IncidentTimelineData.fromJson skips non-Map events', () {
      final data = IncidentTimelineData.fromJson({
        'incident_id': 'inc-1',
        'title': 'Test',
        'start_time': '2026-01-01T00:00:00Z',
        'status': 'ongoing',
        'events': [
          {
            'id': 'e1',
            'timestamp': '2026-01-01T00:00:00Z',
            'type': 'alert',
            'title': 'Alert',
          },
          null,
          'invalid',
        ],
      });
      expect(data.events.length, 1);
    });

    test('AgentTraceData.fromJson skips non-Map nodes', () {
      final data = AgentTraceData.fromJson({
        'trace_id': 't1',
        'nodes': [
          {'span_id': 's1', 'name': 'test', 'kind': 'tool_execution'},
          'invalid',
        ],
        'unique_agents': [],
        'unique_tools': [],
        'anti_patterns': [],
      });
      expect(data.nodes.length, 1);
    });

    test('AgentGraphData.fromJson skips non-Map nodes and edges', () {
      final data = AgentGraphData.fromJson({
        'nodes': [
          {'id': 'n1', 'label': 'Agent', 'type': 'agent'},
          42,
        ],
        'edges': [
          {
            'source_id': 'n1',
            'target_id': 'n2',
            'label': 'calls',
            'call_count': 1,
            'avg_duration_ms': 100.0,
          },
          'invalid',
        ],
      });
      expect(data.nodes.length, 1);
      expect(data.edges.length, 1);
    });

    test('DashboardMetric.fromJson skips non-Map history items', () {
      final metric = DashboardMetric.fromJson({
        'id': 'm1',
        'name': 'CPU',
        'unit': '%',
        'current_value': 50.0,
        'history': [
          {'timestamp': '2026-01-01T00:00:00Z', 'value': 50.0},
          'not a map',
          null,
        ],
      });
      expect(metric.history.length, 1);
    });

    test('MetricsDashboardData.fromJson skips non-Map metrics', () {
      final data = MetricsDashboardData.fromJson({
        'title': 'Test',
        'metrics': [
          {'id': 'm1', 'name': 'CPU', 'unit': '%', 'current_value': 50.0},
          null,
          'invalid',
        ],
      });
      expect(data.metrics.length, 1);
    });
  });

  // ===========================================================================
  // AgentNode — safe string conversion for connections
  // ===========================================================================
  group('AgentNode fromJson type safety', () {
    test('converts non-string connections to strings', () {
      final node = AgentNode.fromJson({
        'id': 'n1',
        'name': 'Agent',
        'type': 'agent',
        'status': 'active',
        'connections': [1, 2, true, 'n5'],
      });
      expect(node.connections, ['1', '2', 'true', 'n5']);
    });

    test('handles null connections', () {
      final node = AgentNode.fromJson({
        'id': 'n1',
        'name': 'Agent',
        'type': 'agent',
        'status': 'active',
        'connections': null,
      });
      expect(node.connections, isEmpty);
    });

    test('handles non-Map metadata', () {
      final node = AgentNode.fromJson({
        'id': 'n1',
        'name': 'Agent',
        'type': 'agent',
        'status': 'active',
        'metadata': 'not a map',
      });
      expect(node.metadata, isNull);
    });
  });

  // ===========================================================================
  // AgentActivityData — safe string conversion for completed_steps
  // ===========================================================================
  group('AgentActivityData fromJson type safety', () {
    test('converts non-string completed_steps to strings', () {
      final data = AgentActivityData.fromJson({
        'nodes': [],
        'current_phase': 'Testing',
        'completed_steps': [1, true, 'step3'],
      });
      expect(data.completedSteps, ['1', 'true', 'step3']);
    });

    test('handles null completed_steps', () {
      final data = AgentActivityData.fromJson({
        'nodes': [],
        'current_phase': 'Analyzing',
        'completed_steps': null,
      });
      expect(data.completedSteps, isEmpty);
    });

    test('skips non-Map nodes', () {
      final data = AgentActivityData.fromJson({
        'nodes': [
          {'id': 'n1', 'name': 'Agent', 'type': 'agent', 'status': 'active'},
          'invalid',
          null,
        ],
        'current_phase': 'Analyzing',
      });
      expect(data.nodes.length, 1);
    });
  });

  // ===========================================================================
  // TimelineEvent — metadata type check fix
  // ===========================================================================
  group('TimelineEvent fromJson metadata safety', () {
    test('handles non-Map metadata', () {
      final event = TimelineEvent.fromJson({
        'id': 'e1',
        'timestamp': '2026-01-01T00:00:00Z',
        'type': 'alert',
        'title': 'Alert',
        'metadata': 'not a map',
      });
      expect(event.metadata, isNull);
    });

    test('handles valid Map metadata', () {
      final event = TimelineEvent.fromJson({
        'id': 'e1',
        'timestamp': '2026-01-01T00:00:00Z',
        'type': 'alert',
        'title': 'Alert',
        'metadata': {'key': 'value'},
      });
      expect(event.metadata, isNotNull);
      expect(event.metadata!['key'], 'value');
    });

    test('handles null metadata', () {
      final event = TimelineEvent.fromJson({
        'id': 'e1',
        'timestamp': '2026-01-01T00:00:00Z',
        'type': 'alert',
        'title': 'Alert',
        'metadata': null,
      });
      expect(event.metadata, isNull);
    });
  });

  // ===========================================================================
  // LogPattern — severityCounts num-to-int coercion
  // ===========================================================================
  group('LogPattern fromJson type coercion', () {
    test('handles double values in severity_counts', () {
      final pattern = LogPattern.fromJson({
        'template': 'test',
        'count': 10.0,
        'severity_counts': {'ERROR': 5.0, 'WARNING': 3.0},
      });
      expect(pattern.count, 10);
      expect(pattern.severityCounts['ERROR'], 5);
      expect(pattern.severityCounts['WARNING'], 3);
    });

    test('handles null severity_counts', () {
      final pattern = LogPattern.fromJson({
        'template': 'test',
        'count': 5,
        'severity_counts': null,
      });
      expect(pattern.severityCounts, isEmpty);
    });
  });

  // ===========================================================================
  // Council models — list parser safety
  // ===========================================================================
  group('Council models list parser safety', () {
    test('CouncilAgentActivity.fromJson skips non-Map tool_calls', () {
      final activity = CouncilAgentActivity.fromJson({
        'agent_id': 'a1',
        'agent_name': 'panel',
        'agent_type': 'panel',
        'tool_calls': [
          {'call_id': 'c1', 'tool_name': 'fetch_trace'},
          'invalid',
          null,
        ],
        'llm_calls': [
          {'call_id': 'l1', 'model': 'gemini'},
          42,
        ],
      });
      expect(activity.toolCalls.length, 1);
      expect(activity.llmCalls.length, 1);
    });

    test('CouncilActivityGraph.fromJson skips non-Map agents', () {
      final graph = CouncilActivityGraph.fromJson({
        'investigation_id': 'inv-1',
        'mode': 'standard',
        'started_at': '2026-01-01T00:00:00Z',
        'agents': [
          {'agent_id': 'a1', 'agent_name': 'panel', 'agent_type': 'panel'},
          'invalid',
          null,
        ],
      });
      expect(graph.agents.length, 1);
    });

    test('CouncilSynthesisData.fromJson skips non-Map panels', () {
      final data = CouncilSynthesisData.fromJson({
        'synthesis': 'test',
        'panels': [
          {
            'panel': 'trace',
            'summary': 'ok',
            'severity': 'info',
            'confidence': 0.5,
          },
          'invalid',
          null,
        ],
      });
      expect(data.panels.length, 1);
    });
  });
}
