import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/models/adk_schema.dart';
import 'package:autosre/services/dashboard_state.dart';

void main() {
  late DashboardState state;

  setUp(() {
    state = DashboardState();
  });

  // ===========================================================================
  // Basic state management
  // ===========================================================================
  group('DashboardState basic operations', () {
    test('initial state is correct', () {
      expect(state.isOpen, isFalse);
      expect(state.activeTab, DashboardDataType.logs);
      expect(state.hasData, isFalse);
      expect(state.items, isEmpty);
      expect(state.autoRefresh, isFalse);
      expect(state.metricsQueryLanguage, 0);
    });

    test('toggleDashboard toggles isOpen', () {
      expect(state.isOpen, isFalse);
      state.toggleDashboard();
      expect(state.isOpen, isTrue);
      state.toggleDashboard();
      expect(state.isOpen, isFalse);
    });

    test('openDashboard sets isOpen to true', () {
      state.openDashboard();
      expect(state.isOpen, isTrue);
      // Opening again should not re-notify
      state.openDashboard();
      expect(state.isOpen, isTrue);
    });

    test('closeDashboard sets isOpen to false', () {
      state.openDashboard();
      state.closeDashboard();
      expect(state.isOpen, isFalse);
      // Closing again should not re-notify
      state.closeDashboard();
      expect(state.isOpen, isFalse);
    });

    test('setActiveTab changes the active tab', () {
      state.setActiveTab(DashboardDataType.logs);
      expect(state.activeTab, DashboardDataType.logs);
      state.setActiveTab(DashboardDataType.metrics);
      expect(state.activeTab, DashboardDataType.metrics);
    });

    test('setActiveTab does not notify when tab is same', () {
      var notifyCount = 0;
      state.addListener(() => notifyCount++);
      // Change to a different tab first to verify it notifies on change
      state.setActiveTab(DashboardDataType.metrics);
      expect(notifyCount, 1);
      // Change to the SAME tab, should NOT notify
      state.setActiveTab(DashboardDataType.metrics);
      expect(notifyCount, 1);
    });

    test('setMetricsQueryLanguage changes index', () {
      state.setMetricsQueryLanguage(1);
      expect(state.metricsQueryLanguage, 1);
    });

    test('setMetricsQueryLanguage does not notify when same', () {
      var notifyCount = 0;
      state.addListener(() => notifyCount++);
      state.setMetricsQueryLanguage(1);
      expect(notifyCount, 1);
      state.setMetricsQueryLanguage(1);
      expect(notifyCount, 1);
    });
  });

  // ===========================================================================
  // Adding items
  // ===========================================================================
  group('DashboardState adding items', () {
    test('addTrace adds a trace item', () {
      final trace = Trace(traceId: 'trace-1', spans: []);
      state.addTrace(trace, 'fetch_trace', {});

      expect(state.items.length, 1);
      expect(state.items.first.type, DashboardDataType.traces);
      expect(state.items.first.traceData, trace);
      expect(state.items.first.source, DataSource.agent);
    });

    test('addTrace with manual source', () {
      final trace = Trace(traceId: 'trace-2', spans: []);
      state.addTrace(trace, 'fetch_trace', {}, source: DataSource.manual);

      expect(state.items.first.source, DataSource.manual);
    });

    test('addLogEntries adds a log item', () {
      const logData = LogEntriesData(entries: []);
      state.addLogEntries(logData, 'fetch_logs', {});

      expect(state.items.length, 1);
      expect(state.items.first.type, DashboardDataType.logs);
      expect(state.items.first.logData, logData);
    });

    test('addLogPatterns adds a log patterns item', () {
      final patterns = [
        const LogPattern(template: 'Error <*>', count: 5, severityCounts: {}),
      ];
      state.addLogPatterns(patterns, 'analyze_logs', {});

      expect(state.items.length, 1);
      expect(state.items.first.type, DashboardDataType.logs);
      expect(state.items.first.logPatterns, patterns);
    });

    test('addMetricSeries adds a metric item', () {
      final series = MetricSeries(metricName: 'cpu', points: [], labels: {});
      state.addMetricSeries(series, 'fetch_metrics', {});

      expect(state.items.length, 1);
      expect(state.items.first.type, DashboardDataType.metrics);
      expect(state.items.first.metricSeries, series);
    });

    test('addMetricsDashboard adds a metrics dashboard item', () {
      final data = MetricsDashboardData(title: 'Health', metrics: []);
      state.addMetricsDashboard(data, 'get_dashboard', {});

      expect(state.items.length, 1);
      expect(state.items.first.type, DashboardDataType.metrics);
      expect(state.items.first.metricsDashboard, data);
    });

    test('addAlerts adds an alert item', () {
      final data = IncidentTimelineData(
        incidentId: 'inc-1',
        title: 'Outage',
        startTime: DateTime.now(),
        status: 'ongoing',
        events: [],
      );
      state.addAlerts(data, 'get_alerts', {});

      expect(state.items.length, 1);
      expect(state.items.first.type, DashboardDataType.alerts);
      expect(state.items.first.alertData, data);
    });


    test('addChart adds a chart item', () {
      final data = VegaChartData(question: 'Q', answer: 'A');
      state.addChart(data, 'query', {});

      expect(state.items.length, 1);
      expect(state.items.first.type, DashboardDataType.analytics);
      expect(state.items.first.chartData, data);
    });

    test('addSqlResults adds SQL item and updates BigQuery state', () {
      state.addSqlResults(
        'SELECT 1',
        ['col1'],
        [
          {'col1': 1},
        ],
        'run_sql',
      );

      expect(state.items.length, 1);
      expect(state.items.first.type, DashboardDataType.analytics);
      expect(state.items.first.sqlData?.query, 'SELECT 1');
      expect(state.bigQueryColumns, ['col1']);
    });

    test('items have unique IDs', () {
      final trace1 = Trace(traceId: 't1', spans: []);
      final trace2 = Trace(traceId: 't2', spans: []);
      state.addTrace(trace1, 'tool', {});
      state.addTrace(trace2, 'tool', {});

      expect(state.items[0].id, isNot(state.items[1].id));
    });
  });

  // ===========================================================================
  // Filtering items
  // ===========================================================================
  group('DashboardState filtering', () {
    test('itemsOfType filters correctly', () {
      state.addTrace(Trace(traceId: 't1', spans: []), 'tool', {});
      state.addLogEntries(const LogEntriesData(entries: []), 'tool', {});
      state.addTrace(Trace(traceId: 't2', spans: []), 'tool', {});

      expect(state.itemsOfType(DashboardDataType.traces).length, 2);
      expect(state.itemsOfType(DashboardDataType.logs).length, 1);
      expect(state.itemsOfType(DashboardDataType.metrics).length, 0);
    });

    test('typeCounts returns correct counts', () {
      state.addTrace(Trace(traceId: 't1', spans: []), 'tool', {});
      state.addTrace(Trace(traceId: 't2', spans: []), 'tool', {});
      state.addLogEntries(const LogEntriesData(entries: []), 'tool', {});

      final counts = state.typeCounts;
      expect(counts[DashboardDataType.traces], 2);
      expect(counts[DashboardDataType.logs], 1);
      expect(counts.containsKey(DashboardDataType.metrics), isFalse);
    });
  });

  // ===========================================================================
  // Removing / clearing items
  // ===========================================================================
  group('DashboardState removing/clearing', () {
    test('removeItem removes by ID', () {
      state.addTrace(Trace(traceId: 't1', spans: []), 'tool', {});
      final id = state.items.first.id;
      state.removeItem(id);
      expect(state.items, isEmpty);
    });

    test('clearManualItems removes only manual items', () {
      state.addTrace(
        Trace(traceId: 't1', spans: []),
        'tool',
        {},
        source: DataSource.agent,
      );
      state.addTrace(
        Trace(traceId: 't2', spans: []),
        'tool',
        {},
        source: DataSource.manual,
      );

      state.clearManualItems();
      expect(state.items.length, 1);
      expect(state.items.first.traceData?.traceId, 't1');
    });

    test('clear resets all state', () {
      state.addTrace(Trace(traceId: 't1', spans: []), 'tool', {});
      state.setActiveTab(DashboardDataType.logs);
      state.setLoading(DashboardDataType.traces, true);
      state.setError(DashboardDataType.logs, 'error');
      state.setBigQueryResults(
        ['a'],
        [
          {'a': 1},
        ],
      );
      state.setMetricsQueryLanguage(1);

      state.clear();
      expect(state.items, isEmpty);
      expect(state.hasData, isFalse);
      expect(state.isLoading(DashboardDataType.traces), isFalse);
      expect(state.errorFor(DashboardDataType.logs), isNull);
      expect(state.bigQueryColumns, isEmpty);
      expect(state.bigQueryResults, isEmpty);
      expect(state.autoRefresh, isFalse);
      expect(state.metricsQueryLanguage, 0);
    });
  });

  // ===========================================================================
  // Loading and error states
  // ===========================================================================
  group('DashboardState loading/error', () {
    test('setLoading sets and gets loading state', () {
      expect(state.isLoading(DashboardDataType.traces), isFalse);
      state.setLoading(DashboardDataType.traces, true);
      expect(state.isLoading(DashboardDataType.traces), isTrue);
    });

    test('setLoading clears error when loading starts', () {
      state.setError(DashboardDataType.traces, 'some error');
      state.setLoading(DashboardDataType.traces, true);
      expect(state.errorFor(DashboardDataType.traces), isNull);
    });

    test('setError sets and gets error state', () {
      expect(state.errorFor(DashboardDataType.logs), isNull);
      state.setError(DashboardDataType.logs, 'Connection failed');
      expect(state.errorFor(DashboardDataType.logs), 'Connection failed');
    });
  });

  // ===========================================================================
  // BigQuery results
  // ===========================================================================
  group('DashboardState BigQuery', () {
    test('setBigQueryResults stores columns and rows', () {
      state.setBigQueryResults(
        ['name', 'age'],
        [
          {'name': 'Alice', 'age': 30},
          {'name': 'Bob', 'age': 25},
        ],
      );
      expect(state.bigQueryColumns, ['name', 'age']);
      expect(state.bigQueryResults.length, 2);
    });

    test('clearBigQueryResults resets BQ state', () {
      state.setBigQueryResults(
        ['a'],
        [
          {'a': 1},
        ],
      );
      state.clearBigQueryResults();
      expect(state.bigQueryColumns, isEmpty);
      expect(state.bigQueryResults, isEmpty);
    });

    test('bigQueryResults returns unmodifiable list', () {
      state.setBigQueryResults(
        ['a'],
        [
          {'a': 1},
        ],
      );
      expect(() => state.bigQueryResults.add({'b': 2}), throwsA(anything));
    });
  });

  // ===========================================================================
  // Query filters
  // ===========================================================================
  group('DashboardState query filters', () {
    test('setLastQueryFilter stores filter', () {
      state.setLastQueryFilter(DashboardDataType.logs, 'severity=ERROR');
      expect(
        state.getLastQueryFilter(DashboardDataType.logs),
        'severity=ERROR',
      );
    });

    test('getLastQueryFilter returns null for unset types', () {
      expect(state.getLastQueryFilter(DashboardDataType.traces), isNull);
    });
  });

  // ===========================================================================
  // Auto-refresh
  // ===========================================================================
  group('DashboardState auto-refresh', () {
    test('toggleAutoRefresh toggles state', () {
      expect(state.autoRefresh, isFalse);
      state.toggleAutoRefresh();
      expect(state.autoRefresh, isTrue);
      state.toggleAutoRefresh();
      expect(state.autoRefresh, isFalse);
    });
  });

  // ===========================================================================
  // addFromEvent
  // ===========================================================================
  group('DashboardState addFromEvent', () {
    test('returns false for null category', () {
      final result = state.addFromEvent({'data': {}});
      expect(result, isFalse);
    });

    test('returns false for null data', () {
      final result = state.addFromEvent({'category': 'traces'});
      expect(result, isFalse);
    });

    test('returns false for non-map data', () {
      final result = state.addFromEvent({
        'category': 'traces',
        'data': 'not a map',
      });
      expect(result, isFalse);
    });

    test('returns false for unknown widget_type', () {
      final result = state.addFromEvent({
        'category': 'traces',
        'widget_type': 'x-sre-unknown',
        'data': {},
      });
      expect(result, isFalse);
    });

    test('processes council synthesis event', () {
      final result = state.addFromEvent({
        'category': 'council',
        'widget_type': 'x-sre-council-synthesis',
        'tool_name': 'run_council',
        'data': {
          'synthesis': 'Test synthesis',
          'overall_severity': 'warning',
          'overall_confidence': 0.85,
          'mode': 'standard',
          'rounds': 1,
        },
      });
      expect(result, isTrue);
      expect(state.items.length, 1);
      expect(state.items.first.type, DashboardDataType.council);
    });

    test('processes vega chart event', () {
      final result = state.addFromEvent({
        'category': 'charts',
        'widget_type': 'x-sre-vega-chart',
        'tool_name': 'query',
        'data': {'question': 'Q', 'answer': 'A', 'vega_lite_charts': []},
      });
      expect(result, isTrue);
      expect(state.items.first.type, DashboardDataType.analytics);
    });

    test('rejects empty trace spans', () {
      final result = state.addFromEvent({
        'category': 'traces',
        'widget_type': 'x-sre-trace-waterfall',
        'data': {'trace_id': 't1', 'spans': []},
      });
      expect(result, isFalse);
    });

    test('rejects empty log entries', () {
      final result = state.addFromEvent({
        'category': 'logs',
        'widget_type': 'x-sre-log-entries-viewer',
        'data': {'entries': []},
      });
      expect(result, isFalse);
    });

    test('rejects empty metric points', () {
      final result = state.addFromEvent({
        'category': 'metrics',
        'widget_type': 'x-sre-metric-chart',
        'data': {'metric_name': 'cpu', 'points': [], 'labels': {}},
      });
      expect(result, isFalse);
    });


    test('auto-opens dashboard on first data', () {
      expect(state.isOpen, isFalse);
      state.addFromEvent({
        'category': 'council',
        'widget_type': 'x-sre-council-synthesis',
        'data': {
          'synthesis': 'Test',
          'overall_severity': 'info',
          'overall_confidence': 0.5,
          'mode': 'fast',
          'rounds': 1,
        },
      });
      expect(state.isOpen, isTrue);
    });
  });

  // ===========================================================================
  // classifyComponent
  // ===========================================================================
  group('classifyComponent', () {
    test('maps known component types', () {
      expect(
        classifyComponent('x-sre-log-entries-viewer'),
        DashboardDataType.logs,
      );
      expect(
        classifyComponent('x-sre-log-pattern-viewer'),
        DashboardDataType.logs,
      );
      expect(
        classifyComponent('x-sre-metric-chart'),
        DashboardDataType.metrics,
      );
      expect(
        classifyComponent('x-sre-metrics-dashboard'),
        DashboardDataType.metrics,
      );
      expect(
        classifyComponent('x-sre-trace-waterfall'),
        DashboardDataType.traces,
      );
      expect(
        classifyComponent('x-sre-incident-timeline'),
        DashboardDataType.alerts,
      );
      expect(
        classifyComponent('x-sre-council-synthesis'),
        DashboardDataType.council,
      );
      expect(
        classifyComponent('x-sre-vega-chart'),
        DashboardDataType.analytics,
      );
    });

    test('returns null for unknown component', () {
      expect(classifyComponent('x-sre-unknown'), isNull);
      expect(classifyComponent(''), isNull);
    });
  });

  // ===========================================================================
  // Dispose
  // ===========================================================================
  group('DashboardState dispose', () {
    test('dispose cancels auto-refresh timer', () {
      state.toggleAutoRefresh();
      expect(state.autoRefresh, isTrue);
      state.dispose();
      // Verify no crash after dispose
    });
  });
}
