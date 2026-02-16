import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/models/adk_schema.dart';

void main() {
  // ===========================================================================
  // SpanInfo equality
  // ===========================================================================
  group('SpanInfo equality', () {
    final start = DateTime.utc(2026, 1, 1, 10, 0, 0);
    final end = DateTime.utc(2026, 1, 1, 10, 0, 1);

    SpanInfo makeSpan({String spanId = 's1'}) => SpanInfo(
      spanId: spanId,
      traceId: 't1',
      name: 'GET /api',
      startTime: start,
      endTime: end,
      attributes: {'key': 'value'},
      status: 'OK',
      parentSpanId: 'p1',
    );

    test('identical instances are equal', () {
      final a = makeSpan();
      expect(a == a, isTrue);
    });

    test('equal fields produce equality', () {
      final a = makeSpan();
      final b = makeSpan();
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('different spanId breaks equality', () {
      final a = makeSpan(spanId: 's1');
      final b = makeSpan(spanId: 's2');
      expect(a == b, isFalse);
    });

    test('different types are not equal', () {
      final a = makeSpan();
      // ignore: unrelated_type_equality_checks
      expect(a == 'not a span', isFalse);
    });
  });

  // ===========================================================================
  // Trace equality
  // ===========================================================================
  group('Trace equality', () {
    test('equal traces are equal', () {
      final a = Trace(traceId: 't1', spans: []);
      final b = Trace(traceId: 't1', spans: []);
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('different traceId breaks equality', () {
      final a = Trace(traceId: 't1', spans: []);
      final b = Trace(traceId: 't2', spans: []);
      expect(a == b, isFalse);
    });

    test('different span lists break equality', () {
      final span = SpanInfo(
        spanId: 's1',
        traceId: 't1',
        name: 'test',
        startTime: DateTime.utc(2026),
        endTime: DateTime.utc(2026),
        attributes: {},
        status: 'OK',
      );
      final a = Trace(traceId: 't1', spans: [span]);
      final b = Trace(traceId: 't1', spans: []);
      expect(a == b, isFalse);
    });
  });

  // ===========================================================================
  // MetricPoint equality
  // ===========================================================================
  group('MetricPoint equality', () {
    test('equal points are equal', () {
      final ts = DateTime.utc(2026, 1, 1);
      final a = MetricPoint(timestamp: ts, value: 42.0);
      final b = MetricPoint(timestamp: ts, value: 42.0);
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('different value breaks equality', () {
      final ts = DateTime.utc(2026, 1, 1);
      final a = MetricPoint(timestamp: ts, value: 42.0);
      final b = MetricPoint(timestamp: ts, value: 43.0);
      expect(a == b, isFalse);
    });

    test('different isAnomaly breaks equality', () {
      final ts = DateTime.utc(2026, 1, 1);
      final a = MetricPoint(timestamp: ts, value: 42.0, isAnomaly: false);
      final b = MetricPoint(timestamp: ts, value: 42.0, isAnomaly: true);
      expect(a == b, isFalse);
    });
  });

  // ===========================================================================
  // MetricSeries equality
  // ===========================================================================
  group('MetricSeries equality', () {
    test('equal series are equal', () {
      final a = MetricSeries(metricName: 'cpu', points: [], labels: {'k': 'v'});
      final b = MetricSeries(metricName: 'cpu', points: [], labels: {'k': 'v'});
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('different labels break equality', () {
      final a = MetricSeries(
        metricName: 'cpu',
        points: [],
        labels: {'k': 'v1'},
      );
      final b = MetricSeries(
        metricName: 'cpu',
        points: [],
        labels: {'k': 'v2'},
      );
      expect(a == b, isFalse);
    });
  });

  // ===========================================================================
  // RemediationStep / RemediationPlan equality
  // ===========================================================================
  group('RemediationStep equality', () {
    test('equal steps are equal', () {
      final a = RemediationStep(command: 'cmd', description: 'desc');
      final b = RemediationStep(command: 'cmd', description: 'desc');
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });
  });

  group('RemediationPlan equality', () {
    test('equal plans are equal', () {
      final step = RemediationStep(command: 'cmd', description: 'desc');
      final a = RemediationPlan(issue: 'bug', risk: 'low', steps: [step]);
      final b = RemediationPlan(issue: 'bug', risk: 'low', steps: [step]);
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });
  });

  // ===========================================================================
  // LogPattern equality
  // ===========================================================================
  group('LogPattern equality', () {
    test('equal patterns are equal', () {
      final a = LogPattern(
        template: 'tmpl',
        count: 5,
        severityCounts: {'ERROR': 3},
      );
      final b = LogPattern(
        template: 'tmpl',
        count: 5,
        severityCounts: {'ERROR': 3},
      );
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });
  });

  // ===========================================================================
  // LogEntry equality
  // ===========================================================================
  group('LogEntry equality', () {
    test('equal entries are equal', () {
      final ts = DateTime.utc(2026, 1, 1);
      final a = LogEntry(
        insertId: 'id1',
        timestamp: ts,
        severity: 'INFO',
        payload: 'test',
        resourceLabels: {},
        resourceType: 'gce',
      );
      final b = LogEntry(
        insertId: 'id1',
        timestamp: ts,
        severity: 'INFO',
        payload: 'test',
        resourceLabels: {},
        resourceType: 'gce',
      );
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });
  });

  // ===========================================================================
  // ToolLog equality
  // ===========================================================================
  group('ToolLog equality', () {
    test('equal logs are equal', () {
      final a = ToolLog(
        toolName: 'fetch_trace',
        args: {'id': '123'},
        status: 'completed',
        result: 'ok',
        timestamp: '2026-01-01T00:00:00Z',
        duration: '100ms',
      );
      final b = ToolLog(
        toolName: 'fetch_trace',
        args: {'id': '123'},
        status: 'completed',
        result: 'ok',
        timestamp: '2026-01-01T00:00:00Z',
        duration: '100ms',
      );
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('different status breaks equality', () {
      final a = ToolLog(toolName: 't', args: {}, status: 'running');
      final b = ToolLog(toolName: 't', args: {}, status: 'completed');
      expect(a == b, isFalse);
    });
  });

  // ===========================================================================
  // TimelineEvent equality
  // ===========================================================================
  group('TimelineEvent equality', () {
    test('equal events are equal', () {
      final ts = DateTime.utc(2026, 1, 1);
      final a = TimelineEvent(
        id: 'e1',
        timestamp: ts,
        type: 'alert',
        title: 'Alert',
      );
      final b = TimelineEvent(
        id: 'e1',
        timestamp: ts,
        type: 'alert',
        title: 'Alert',
      );
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });
  });

  // ===========================================================================
  // AgentNode equality
  // ===========================================================================
  group('AgentNode equality', () {
    test('equal nodes are equal', () {
      final a = AgentNode(
        id: 'n1',
        name: 'Agent',
        type: 'agent',
        status: 'active',
      );
      final b = AgentNode(
        id: 'n1',
        name: 'Agent',
        type: 'agent',
        status: 'active',
      );
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('different connections break equality', () {
      final a = AgentNode(
        id: 'n1',
        name: 'Agent',
        type: 'agent',
        status: 'active',
        connections: ['n2'],
      );
      final b = AgentNode(
        id: 'n1',
        name: 'Agent',
        type: 'agent',
        status: 'active',
        connections: ['n3'],
      );
      expect(a == b, isFalse);
    });
  });

  // ===========================================================================
  // AgentGraphNode / AgentGraphEdge equality
  // ===========================================================================
  group('AgentGraphNode equality', () {
    test('equal nodes are equal', () {
      final a = AgentGraphNode(
        id: 'n1',
        label: 'Agent',
        type: 'agent',
        hasError: false,
      );
      final b = AgentGraphNode(
        id: 'n1',
        label: 'Agent',
        type: 'agent',
        hasError: false,
      );
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });
  });

  group('AgentGraphEdge equality', () {
    test('equal edges are equal', () {
      final a = AgentGraphEdge(
        sourceId: 'n1',
        targetId: 'n2',
        label: 'calls',
        callCount: 1,
        avgDurationMs: 100.0,
        hasError: false,
      );
      final b = AgentGraphEdge(
        sourceId: 'n1',
        targetId: 'n2',
        label: 'calls',
        callCount: 1,
        avgDurationMs: 100.0,
        hasError: false,
      );
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });
  });

  // ===========================================================================
  // PanelFinding equality
  // ===========================================================================
  group('PanelFinding equality', () {
    test('equal findings are equal', () {
      final a = PanelFinding(
        panel: 'trace',
        summary: 'High latency',
        severity: 'warning',
        confidence: 0.85,
        evidence: ['e1'],
        recommendedActions: ['scale up'],
      );
      final b = PanelFinding(
        panel: 'trace',
        summary: 'High latency',
        severity: 'warning',
        confidence: 0.85,
        evidence: ['e1'],
        recommendedActions: ['scale up'],
      );
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('different evidence breaks equality', () {
      final a = PanelFinding(
        panel: 'trace',
        summary: 's',
        severity: 'info',
        confidence: 0.5,
        evidence: ['e1'],
        recommendedActions: [],
      );
      final b = PanelFinding(
        panel: 'trace',
        summary: 's',
        severity: 'info',
        confidence: 0.5,
        evidence: ['e2'],
        recommendedActions: [],
      );
      expect(a == b, isFalse);
    });
  });

  // ===========================================================================
  // CriticReport equality
  // ===========================================================================
  group('CriticReport equality', () {
    test('equal reports are equal', () {
      final a = CriticReport(
        agreements: ['a1'],
        contradictions: [],
        gaps: [],
        revisedConfidence: 0.9,
      );
      final b = CriticReport(
        agreements: ['a1'],
        contradictions: [],
        gaps: [],
        revisedConfidence: 0.9,
      );
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });
  });

  // ===========================================================================
  // ToolCallRecord / LLMCallRecord equality
  // ===========================================================================
  group('ToolCallRecord equality', () {
    test('equal records are equal', () {
      final a = ToolCallRecord(callId: 'c1', toolName: 'fetch_trace');
      final b = ToolCallRecord(callId: 'c1', toolName: 'fetch_trace');
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });
  });

  group('LLMCallRecord equality', () {
    test('equal records are equal', () {
      final a = LLMCallRecord(callId: 'c1', model: 'gemini-2.0-flash');
      final b = LLMCallRecord(callId: 'c1', model: 'gemini-2.0-flash');
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });

    test('totalTokens computed correctly', () {
      final r = LLMCallRecord(
        callId: 'c1',
        model: 'gemini',
        inputTokens: 100,
        outputTokens: 50,
      );
      expect(r.totalTokens, 150);
    });
  });
}
