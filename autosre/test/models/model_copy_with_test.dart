import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/models/adk_schema.dart';

void main() {
  // ===========================================================================
  // Trace.copyWith
  // ===========================================================================
  group('Trace.copyWith', () {
    final original = Trace(
      traceId: 'trace-1',
      spans: [
        SpanInfo(
          spanId: 's1',
          traceId: 'trace-1',
          name: 'root',
          startTime: DateTime.utc(2026),
          endTime: DateTime.utc(2026),
          attributes: {},
          status: 'OK',
        ),
      ],
    );

    test('returns copy with no changes when no args', () {
      final copy = original.copyWith();
      expect(copy.traceId, original.traceId);
      expect(copy.spans.length, original.spans.length);
      expect(copy, equals(original));
    });

    test('updates traceId only', () {
      final copy = original.copyWith(traceId: 'trace-2');
      expect(copy.traceId, 'trace-2');
      expect(copy.spans.length, original.spans.length);
    });

    test('updates spans only', () {
      final copy = original.copyWith(spans: []);
      expect(copy.traceId, original.traceId);
      expect(copy.spans, isEmpty);
    });

    test('does not mutate original', () {
      original.copyWith(traceId: 'modified');
      expect(original.traceId, 'trace-1');
    });
  });

  // ===========================================================================
  // MetricSeries.copyWith
  // ===========================================================================
  group('MetricSeries.copyWith', () {
    final original = MetricSeries(
      metricName: 'cpu_util',
      points: [MetricPoint(timestamp: DateTime.utc(2026), value: 45.0)],
      labels: {'zone': 'us-central1-a'},
    );

    test('returns copy with no changes when no args', () {
      final copy = original.copyWith();
      expect(copy, equals(original));
    });

    test('updates metricName only', () {
      final copy = original.copyWith(metricName: 'memory_util');
      expect(copy.metricName, 'memory_util');
      expect(copy.points.length, original.points.length);
      expect(copy.labels, original.labels);
    });

    test('updates labels only', () {
      final copy = original.copyWith(labels: {'zone': 'eu-west1-b'});
      expect(copy.metricName, original.metricName);
      expect(copy.labels['zone'], 'eu-west1-b');
    });

    test('updates points only', () {
      final copy = original.copyWith(points: []);
      expect(copy.points, isEmpty);
      expect(copy.metricName, original.metricName);
    });
  });

  // ===========================================================================
  // LogEntriesData.copyWith
  // ===========================================================================
  group('LogEntriesData.copyWith', () {
    final original = LogEntriesData(
      entries: [
        LogEntry(
          insertId: 'id1',
          timestamp: DateTime.utc(2026),
          severity: 'ERROR',
          payload: 'test',
          resourceLabels: {},
          resourceType: 'gce',
        ),
      ],
      filter: 'severity="ERROR"',
      projectId: 'my-project',
      nextPageToken: 'token1',
    );

    test('returns copy with no changes when no args', () {
      final copy = original.copyWith();
      expect(copy, equals(original));
    });

    test('updates filter only', () {
      final copy = original.copyWith(filter: 'severity="WARNING"');
      expect(copy.filter, 'severity="WARNING"');
      expect(copy.entries.length, original.entries.length);
      expect(copy.projectId, original.projectId);
    });

    test('updates nextPageToken only', () {
      final copy = original.copyWith(nextPageToken: 'token2');
      expect(copy.nextPageToken, 'token2');
      expect(copy.filter, original.filter);
    });

    test('updates entries only', () {
      final copy = original.copyWith(entries: []);
      expect(copy.entries, isEmpty);
      expect(copy.filter, original.filter);
    });
  });

  // ===========================================================================
  // IncidentTimelineData.copyWith
  // ===========================================================================
  group('IncidentTimelineData.copyWith', () {
    final original = IncidentTimelineData(
      incidentId: 'inc-1',
      title: 'Outage',
      startTime: DateTime.utc(2026, 1, 1, 9),
      endTime: DateTime.utc(2026, 1, 1, 10),
      status: 'resolved',
      events: [
        TimelineEvent(
          id: 'e1',
          timestamp: DateTime.utc(2026, 1, 1, 9),
          type: 'alert',
          title: 'Alert',
        ),
      ],
      rootCause: 'DB issue',
      timeToDetect: const Duration(minutes: 5),
      timeToMitigate: const Duration(hours: 1),
    );

    test('returns copy with no changes when no args', () {
      final copy = original.copyWith();
      expect(copy, equals(original));
    });

    test('updates status only', () {
      final copy = original.copyWith(status: 'mitigated');
      expect(copy.status, 'mitigated');
      expect(copy.incidentId, original.incidentId);
      expect(copy.events.length, original.events.length);
    });

    test('updates events only', () {
      final copy = original.copyWith(events: []);
      expect(copy.events, isEmpty);
      expect(copy.status, original.status);
    });

    test('updates rootCause only', () {
      final copy = original.copyWith(rootCause: 'Network partition');
      expect(copy.rootCause, 'Network partition');
      expect(copy.title, original.title);
    });
  });

  // ===========================================================================
  // CouncilSynthesisData.copyWith
  // ===========================================================================
  group('CouncilSynthesisData.copyWith', () {
    final original = CouncilSynthesisData(
      synthesis: 'Redis pool exhaustion causing latency.',
      overallSeverity: 'warning',
      overallConfidence: 0.87,
      mode: 'standard',
      rounds: 1,
      panels: [
        PanelFinding(
          panel: 'trace',
          summary: 'High latency',
          severity: 'warning',
          confidence: 0.85,
          evidence: [],
          recommendedActions: [],
        ),
      ],
      rawData: const {},
    );

    test('returns copy with no changes when no args', () {
      final copy = original.copyWith();
      expect(copy, equals(original));
    });

    test('updates activityGraph only (dashboard_state pattern)', () {
      final graph = CouncilActivityGraph(
        investigationId: 'inv-1',
        mode: 'standard',
        startedAt: 'now',
      );
      final copy = original.copyWith(activityGraph: graph);
      expect(copy.activityGraph, isNotNull);
      expect(copy.activityGraph!.investigationId, 'inv-1');
      expect(copy.synthesis, original.synthesis);
      expect(copy.panels.length, original.panels.length);
    });

    test('updates overallSeverity only', () {
      final copy = original.copyWith(overallSeverity: 'critical');
      expect(copy.overallSeverity, 'critical');
      expect(copy.synthesis, original.synthesis);
    });

    test('updates rounds only', () {
      final copy = original.copyWith(rounds: 3);
      expect(copy.rounds, 3);
      expect(copy.mode, original.mode);
    });

    test('does not mutate original', () {
      original.copyWith(synthesis: 'modified');
      expect(original.synthesis, 'Redis pool exhaustion causing latency.');
    });
  });
}
