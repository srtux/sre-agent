import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/models/adk_schema.dart';
import 'package:autosre/models/time_range.dart';

/// Tests for Dart 3 modernization changes:
/// - Enhanced enums with member properties
/// - Switch expressions (behavioral equivalence)
/// - if-case pattern matching (behavioral equivalence)
/// - final class modifiers (compile-time, no runtime test needed)
/// - DateTime.tryParse replacement
void main() {
  // ===========================================================================
  // Enhanced CouncilAgentType enum — iconName member property
  // ===========================================================================
  group('CouncilAgentType enhanced enum', () {
    test('each variant has displayName', () {
      expect(CouncilAgentType.root.displayName, 'Root Agent');
      expect(CouncilAgentType.orchestrator.displayName, 'Orchestrator');
      expect(CouncilAgentType.panel.displayName, 'Expert Panel');
      expect(CouncilAgentType.critic.displayName, 'Critic');
      expect(CouncilAgentType.synthesizer.displayName, 'Synthesizer');
      expect(CouncilAgentType.subAgent.displayName, 'Sub-Agent');
    });

    test('each variant has iconName', () {
      expect(CouncilAgentType.root.iconName, 'account_tree');
      expect(CouncilAgentType.orchestrator.iconName, 'hub');
      expect(CouncilAgentType.panel.iconName, 'psychology');
      expect(CouncilAgentType.critic.iconName, 'forum');
      expect(CouncilAgentType.synthesizer.iconName, 'summarize');
      expect(CouncilAgentType.subAgent.iconName, 'smart_toy');
    });

    test('fromString still works with switch expression', () {
      expect(CouncilAgentType.fromString('root'), CouncilAgentType.root);
      expect(
        CouncilAgentType.fromString('orchestrator'),
        CouncilAgentType.orchestrator,
      );
      expect(CouncilAgentType.fromString('panel'), CouncilAgentType.panel);
      expect(CouncilAgentType.fromString('critic'), CouncilAgentType.critic);
      expect(
        CouncilAgentType.fromString('synthesizer'),
        CouncilAgentType.synthesizer,
      );
      expect(
        CouncilAgentType.fromString('sub_agent'),
        CouncilAgentType.subAgent,
      );
      expect(
        CouncilAgentType.fromString('subagent'),
        CouncilAgentType.subAgent,
      );
      expect(CouncilAgentType.fromString('unknown'), CouncilAgentType.subAgent);
    });

    test('fromString is case-insensitive', () {
      expect(CouncilAgentType.fromString('ROOT'), CouncilAgentType.root);
      expect(CouncilAgentType.fromString('Panel'), CouncilAgentType.panel);
      expect(
        CouncilAgentType.fromString('SYNTHESIZER'),
        CouncilAgentType.synthesizer,
      );
    });

    test('CouncilAgentActivity.iconName delegates to enum', () {
      final activity = CouncilAgentActivity(
        agentId: 'a1',
        agentName: 'test',
        agentType: CouncilAgentType.panel,
      );
      expect(activity.iconName, CouncilAgentType.panel.iconName);
      expect(activity.iconName, 'psychology');
    });
  });

  // ===========================================================================
  // Enhanced TimeRangePreset enum — duration & label members
  // ===========================================================================
  group('TimeRangePreset enhanced enum', () {
    test('each preset has correct duration', () {
      expect(TimeRangePreset.fiveMinutes.duration, const Duration(minutes: 5));
      expect(
        TimeRangePreset.fifteenMinutes.duration,
        const Duration(minutes: 15),
      );
      expect(
        TimeRangePreset.thirtyMinutes.duration,
        const Duration(minutes: 30),
      );
      expect(TimeRangePreset.oneHour.duration, const Duration(hours: 1));
      expect(TimeRangePreset.threeHours.duration, const Duration(hours: 3));
      expect(TimeRangePreset.sixHours.duration, const Duration(hours: 6));
      expect(TimeRangePreset.twelveHours.duration, const Duration(hours: 12));
      expect(TimeRangePreset.oneDay.duration, const Duration(days: 1));
      expect(TimeRangePreset.twoDays.duration, const Duration(days: 2));
      expect(TimeRangePreset.oneWeek.duration, const Duration(days: 7));
      expect(TimeRangePreset.fourteenDays.duration, const Duration(days: 14));
      expect(TimeRangePreset.thirtyDays.duration, const Duration(days: 30));
    });

    test('each preset has correct label', () {
      expect(TimeRangePreset.fiveMinutes.label, 'Last 5 minutes');
      expect(TimeRangePreset.fifteenMinutes.label, 'Last 15 minutes');
      expect(TimeRangePreset.thirtyMinutes.label, 'Last 30 minutes');
      expect(TimeRangePreset.oneHour.label, 'Last 1 hour');
      expect(TimeRangePreset.threeHours.label, 'Last 3 hours');
      expect(TimeRangePreset.sixHours.label, 'Last 6 hours');
      expect(TimeRangePreset.twelveHours.label, 'Last 12 hours');
      expect(TimeRangePreset.oneDay.label, 'Last 1 day');
      expect(TimeRangePreset.twoDays.label, 'Last 2 days');
      expect(TimeRangePreset.oneWeek.label, 'Last 7 days');
      expect(TimeRangePreset.fourteenDays.label, 'Last 14 days');
      expect(TimeRangePreset.thirtyDays.label, 'Last 30 days');
    });

    test('custom preset has null label', () {
      expect(TimeRangePreset.custom.label, isNull);
    });

    test('custom preset has default 1h duration', () {
      expect(TimeRangePreset.custom.duration, const Duration(hours: 1));
    });
  });

  // ===========================================================================
  // TimeRange — displayLabel uses if-case pattern matching
  // ===========================================================================
  group('TimeRange displayLabel', () {
    test('returns preset label for standard presets', () {
      final range = TimeRange.fromPreset(TimeRangePreset.oneHour);
      expect(range.displayLabel, 'Last 1 hour');
    });

    test('returns formatted range for custom preset', () {
      final range = TimeRange(
        start: DateTime(2026, 1, 15, 10, 0),
        end: DateTime(2026, 1, 15, 14, 0),
        preset: TimeRangePreset.custom,
      );
      expect(range.displayLabel, contains('Jan 15'));
      expect(range.displayLabel, contains('-'));
    });

    test('fromPreset creates correct time range', () {
      final range = TimeRange.fromPreset(TimeRangePreset.fiveMinutes);
      const expectedDuration = Duration(minutes: 5);
      // Allow 1 second tolerance for test execution time
      expect(range.duration.inSeconds, closeTo(expectedDuration.inSeconds, 1));
    });

    test('refresh recalculates from now for standard presets', () {
      final old = TimeRange.fromPreset(TimeRangePreset.oneHour);
      final refreshed = old.refresh();
      expect(refreshed.preset, TimeRangePreset.oneHour);
      expect(refreshed.duration.inMinutes, closeTo(60, 1));
    });

    test('refresh preserves duration for custom preset', () {
      final old = TimeRange(
        start: DateTime(2026, 1, 1, 10, 0),
        end: DateTime(2026, 1, 1, 12, 0),
        preset: TimeRangePreset.custom,
      );
      final refreshed = old.refresh();
      expect(refreshed.preset, TimeRangePreset.custom);
      expect(refreshed.duration.inHours, 2);
    });
  });

  // ===========================================================================
  // PanelFinding — switch expression for displayName/iconName
  // ===========================================================================
  group('PanelFinding switch expressions', () {
    PanelFinding makeFinding(String panel) => PanelFinding(
      panel: panel,
      summary: '',
      severity: 'info',
      confidence: 0.5,
      evidence: [],
      recommendedActions: [],
    );

    test('displayName maps all known panels', () {
      expect(makeFinding('trace').displayName, 'Trace Analysis');
      expect(makeFinding('metrics').displayName, 'Metrics Analysis');
      expect(makeFinding('logs').displayName, 'Logs Analysis');
      expect(makeFinding('alerts').displayName, 'Alerts Analysis');
    });

    test('displayName falls through to raw name for unknown', () {
      expect(makeFinding('custom_panel').displayName, 'custom_panel');
    });

    test('displayName is case-insensitive', () {
      expect(makeFinding('TRACE').displayName, 'Trace Analysis');
      expect(makeFinding('Metrics').displayName, 'Metrics Analysis');
    });

    test('iconName maps all known panels', () {
      expect(makeFinding('trace').iconName, 'timeline');
      expect(makeFinding('metrics').iconName, 'analytics');
      expect(makeFinding('logs').iconName, 'description');
      expect(makeFinding('alerts').iconName, 'notifications_active');
    });

    test('iconName falls through to help for unknown', () {
      expect(makeFinding('unknown').iconName, 'help');
    });
  });

  // ===========================================================================
  // CouncilSynthesisData — if-case pattern parsing
  // ===========================================================================
  group('CouncilSynthesisData if-case patterns', () {
    test('parses panels from List via switch pattern', () {
      final data = CouncilSynthesisData.fromJson({
        'synthesis': 'test',
        'panels': [
          {
            'panel': 'trace',
            'summary': 's',
            'severity': 'info',
            'confidence': 0.5,
          },
          {
            'panel': 'logs',
            'summary': 's',
            'severity': 'info',
            'confidence': 0.5,
          },
        ],
      });
      expect(data.panels.length, 2);
      expect(data.panels[0].panel, 'trace');
      expect(data.panels[1].panel, 'logs');
    });

    test('returns empty panels when panels is null', () {
      final data = CouncilSynthesisData.fromJson({
        'synthesis': 'test',
        'panels': null,
      });
      expect(data.panels, isEmpty);
    });

    test('returns empty panels when panels is not a list', () {
      final data = CouncilSynthesisData.fromJson({
        'synthesis': 'test',
        'panels': 'not a list',
      });
      expect(data.panels, isEmpty);
    });

    test('parses critic_report from Map via switch pattern', () {
      final data = CouncilSynthesisData.fromJson({
        'synthesis': 'test',
        'critic_report': {
          'agreements': ['ok'],
          'contradictions': [],
          'gaps': [],
          'revised_confidence': 0.8,
        },
      });
      expect(data.criticReport, isNotNull);
      expect(data.criticReport!.agreements.length, 1);
    });

    test('returns null critic_report when not a Map', () {
      final data = CouncilSynthesisData.fromJson({
        'synthesis': 'test',
        'critic_report': 'not a map',
      });
      expect(data.criticReport, isNull);
    });

    test('parses activity_graph from Map via switch pattern', () {
      final data = CouncilSynthesisData.fromJson({
        'synthesis': 'test',
        'activity_graph': {
          'investigation_id': 'inv-1',
          'mode': 'standard',
          'started_at': 'now',
          'agents': [],
        },
      });
      expect(data.activityGraph, isNotNull);
      expect(data.activityGraph!.investigationId, 'inv-1');
    });

    test('returns null activity_graph when not a Map', () {
      final data = CouncilSynthesisData.fromJson({
        'synthesis': 'test',
        'activity_graph': 42,
      });
      expect(data.activityGraph, isNull);
    });
  });

  // ===========================================================================
  // DateTime.tryParse modernization
  // ===========================================================================
  group('DateTime.tryParse modernization', () {
    test('TimelineEvent parses valid timestamp', () {
      final event = TimelineEvent.fromJson({
        'id': 'e1',
        'timestamp': '2026-03-15T10:30:00Z',
        'type': 'alert',
        'title': 'Test',
      });
      expect(event.timestamp.year, 2026);
      expect(event.timestamp.month, 3);
      expect(event.timestamp.day, 15);
    });

    test('TimelineEvent defaults to now for invalid timestamp', () {
      final before = DateTime.now();
      final event = TimelineEvent.fromJson({
        'id': 'e1',
        'timestamp': 'not-a-date',
        'type': 'alert',
        'title': 'Test',
      });
      final after = DateTime.now();
      expect(
        event.timestamp.isAfter(before.subtract(const Duration(seconds: 1))),
        isTrue,
      );
      expect(
        event.timestamp.isBefore(after.add(const Duration(seconds: 1))),
        isTrue,
      );
    });

    test('IncidentTimelineData parses end_time with tryParse', () {
      final data = IncidentTimelineData.fromJson({
        'incident_id': 'inc-1',
        'title': 'Test',
        'start_time': '2026-01-01T00:00:00Z',
        'end_time': '2026-01-01T01:00:00Z',
        'status': 'resolved',
        'events': [],
      });
      expect(data.endTime, isNotNull);
      expect(data.endTime!.hour, 1);
    });

    test('IncidentTimelineData returns null for invalid end_time', () {
      final data = IncidentTimelineData.fromJson({
        'incident_id': 'inc-1',
        'title': 'Test',
        'start_time': '2026-01-01T00:00:00Z',
        'end_time': 'invalid',
        'status': 'ongoing',
        'events': [],
      });
      expect(data.endTime, isNull);
    });

    test('IncidentTimelineData returns null for missing end_time', () {
      final data = IncidentTimelineData.fromJson({
        'incident_id': 'inc-1',
        'title': 'Test',
        'start_time': '2026-01-01T00:00:00Z',
        'status': 'ongoing',
        'events': [],
      });
      expect(data.endTime, isNull);
    });

    test('MetricPoint parses valid timestamp with tryParse', () {
      final point = MetricPoint.fromJson({
        'timestamp': '2026-06-01T12:00:00Z',
        'value': 42.0,
      });
      expect(point.timestamp.year, 2026);
      expect(point.timestamp.month, 6);
    });

    test('MetricPoint defaults to now for invalid timestamp', () {
      final point = MetricPoint.fromJson({'timestamp': 'bad', 'value': 42.0});
      expect(point.timestamp.year, DateTime.now().year);
    });

    test('MetricsDashboardData parses last_updated with tryParse', () {
      final data = MetricsDashboardData.fromJson({
        'title': 'Test',
        'metrics': [],
        'last_updated': '2026-01-01T10:00:00Z',
      });
      expect(data.lastUpdated, isNotNull);
      expect(data.lastUpdated!.year, 2026);
    });

    test('MetricsDashboardData returns null for invalid last_updated', () {
      final data = MetricsDashboardData.fromJson({
        'title': 'Test',
        'metrics': [],
        'last_updated': 'not-a-date',
      });
      expect(data.lastUpdated, isNull);
    });
  });

  // ===========================================================================
  // Null-safe lookups (replace try-catch firstWhere)
  // ===========================================================================
  group('Null-safe lookups', () {
    test('CouncilActivityGraph.getAgentById returns null for missing', () {
      final graph = CouncilActivityGraph(
        investigationId: 'inv-1',
        mode: 'standard',
        startedAt: 'now',
        agents: [
          CouncilAgentActivity(
            agentId: 'a1',
            agentName: 'test',
            agentType: CouncilAgentType.panel,
          ),
        ],
      );
      expect(graph.getAgentById('a1'), isNotNull);
      expect(graph.getAgentById('nonexistent'), isNull);
    });

    test('CouncilActivityGraph.criticAgent returns null when none', () {
      final graph = CouncilActivityGraph(
        investigationId: 'inv-1',
        mode: 'standard',
        startedAt: 'now',
        agents: [
          CouncilAgentActivity(
            agentId: 'a1',
            agentName: 'panel',
            agentType: CouncilAgentType.panel,
          ),
        ],
      );
      expect(graph.criticAgent, isNull);
    });

    test('CouncilSynthesisData.getPanelByType returns null for missing', () {
      final data = CouncilSynthesisData(
        synthesis: 'test',
        overallSeverity: 'info',
        overallConfidence: 0.5,
        mode: 'standard',
        rounds: 1,
        panels: [
          PanelFinding(
            panel: 'trace',
            summary: 's',
            severity: 'info',
            confidence: 0.5,
            evidence: [],
            recommendedActions: [],
          ),
        ],
        rawData: const {},
      );
      expect(data.getPanelByType('trace'), isNotNull);
      expect(data.getPanelByType('TRACE'), isNotNull);
      expect(data.getPanelByType('nonexistent'), isNull);
    });
  });
}
