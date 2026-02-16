import 'dart:async';

import 'package:flutter/foundation.dart';

import '../models/adk_schema.dart';
import '../models/time_range.dart';
import 'data_utils.dart';

/// Tracks whether data came from the agent or a manual user query.
enum DataSource { agent, manual }

/// Categorizes tool call data for dashboard display.
enum DashboardDataType {
  logs,
  metrics,
  traces,
  alerts,
  remediation,
  council,
  analytics,
}

/// A set of tabular results from an SQL query.
class SqlResultSet {
  final String query;
  final List<String> columns;
  final List<Map<String, dynamic>> rows;

  SqlResultSet({
    required this.query,
    required this.columns,
    required this.rows,
  });
}

/// A single item collected from a tool call for dashboard display.
class DashboardItem {
  final String id;
  final DashboardDataType type;
  final String toolName;
  final DateTime timestamp;
  final Map<String, dynamic> rawData;

  // Parsed typed data (one will be non-null based on type)
  final LogEntriesData? logData;
  final List<LogPattern>? logPatterns;
  final MetricSeries? metricSeries;
  final MetricsDashboardData? metricsDashboard;
  final Trace? traceData;
  final IncidentTimelineData? alertData;
  final RemediationPlan? remediationPlan;
  final CouncilSynthesisData? councilData;
  final VegaChartData? chartData;
  final SqlResultSet? sqlData;

  // Track data origin for dual-stream architecture
  final DataSource source;

  DashboardItem({
    required this.id,
    required this.type,
    required this.toolName,
    required this.timestamp,
    required this.rawData,
    this.source = DataSource.agent,
    this.logData,
    this.logPatterns,
    this.metricSeries,
    this.metricsDashboard,
    this.traceData,
    this.alertData,
    this.remediationPlan,
    this.councilData,
    this.chartData,
    this.sqlData,
  });
}

/// Maps tool/component names to dashboard data types.
DashboardDataType? classifyComponent(String componentType) {
  switch (componentType) {
    case 'x-sre-log-entries-viewer':
    case 'x-sre-log-pattern-viewer':
      return DashboardDataType.logs;
    case 'x-sre-metric-chart':
    case 'x-sre-metrics-dashboard':
      return DashboardDataType.metrics;
    case 'x-sre-trace-waterfall':
      return DashboardDataType.traces;
    case 'x-sre-incident-timeline':
      return DashboardDataType.alerts;
    case 'x-sre-remediation-plan':
      return DashboardDataType.remediation;
    case 'x-sre-council-synthesis':
      return DashboardDataType.council;
    case 'x-sre-vega-chart':
      return DashboardDataType.analytics;
    default:
      return null;
  }
}

/// Central state for the investigation dashboard.
///
/// Collects tool call results from the A2UI stream and makes them
/// available as categorized, interactive data panels.
class DashboardState extends ChangeNotifier {
  /// Maximum number of dashboard items to retain (oldest evicted first).
  static const int _maxItems = 200;

  final List<DashboardItem> _items = [];
  int _itemCounter = 0;

  /// Whether the dashboard panel is visible.
  bool _isOpen = false;
  bool get isOpen => _isOpen;

  /// Currently selected tab in the dashboard.
  DashboardDataType _activeTab = DashboardDataType.traces;
  DashboardDataType get activeTab => _activeTab;

  /// Time range for manual queries.
  TimeRange _timeRange = TimeRange.fromPreset(TimeRangePreset.oneHour);
  TimeRange get timeRange => _timeRange;

  /// Loading states per panel type.
  final Map<DashboardDataType, bool> _loadingStates = {};

  /// Error messages per panel type.
  final Map<DashboardDataType, String?> _errorStates = {};

  /// Last manual query filters per panel type.
  final Map<DashboardDataType, String> _lastQueryFilters = {};

  /// Selected metrics query language index (0 = MQL/ListTimeSeries, 1 = PromQL).
  int _metricsQueryLanguage = 0;
  int get metricsQueryLanguage => _metricsQueryLanguage;

  void setMetricsQueryLanguage(int index) {
    if (_metricsQueryLanguage != index) {
      _metricsQueryLanguage = index;
      notifyListeners();
    }
  }

  /// BigQuery SQL query results stored as tabular data.
  List<Map<String, dynamic>> _bigQueryResults = [];
  List<Map<String, dynamic>> get bigQueryResults =>
      List.unmodifiable(_bigQueryResults);

  /// Column names from the most recent BigQuery result set.
  List<String> _bigQueryColumns = [];
  List<String> get bigQueryColumns => List.unmodifiable(_bigQueryColumns);

  void setBigQueryResults(
    List<String> columns,
    List<Map<String, dynamic>> rows,
  ) {
    _bigQueryColumns = columns;
    _bigQueryResults = flattenBigQueryResults(rows);
    notifyListeners();
  }

  void addSqlResults(
    String query,
    List<String> columns,
    List<Map<String, dynamic>> rows,
    String toolName, {
    DataSource source = DataSource.agent,
  }) {
    _itemCounter++;
    final flattenedRows = flattenBigQueryResults(rows);

    // Also update the "latest" single view
    _bigQueryColumns = columns;
    _bigQueryResults = flattenedRows;

    _addItemBounded(
      DashboardItem(
        id: 'sql-$_itemCounter',
        type: DashboardDataType.analytics,
        toolName: toolName,
        timestamp: DateTime.now(),
        rawData: {'query': query, 'columns': columns, 'rows': flattenedRows},
        source: source,
        sqlData: SqlResultSet(
          query: query,
          columns: columns,
          rows: flattenedRows,
        ),
      ),
    );
    notifyListeners();
  }

  void clearBigQueryResults() {
    _bigQueryColumns = [];
    _bigQueryResults = [];
    notifyListeners();
  }

  String? getLastQueryFilter(DashboardDataType type) => _lastQueryFilters[type];
  void setLastQueryFilter(DashboardDataType type, String filter) {
    _lastQueryFilters[type] = filter;
    // We don't necessarily need to notifyListeners just for text updates,
    // but the text field could read it to retain state.
  }

  /// Auto-refresh toggle.
  bool _autoRefresh = false;
  bool get autoRefresh => _autoRefresh;
  Timer? _refreshTimer;
  VoidCallback? _onAutoRefresh;

  /// Appends an item to [_items] and evicts oldest items if over [_maxItems].
  void _addItemBounded(DashboardItem item) {
    _items.add(item);
    if (_items.length > _maxItems) {
      _items.removeRange(0, _items.length - _maxItems);
    }
  }

  /// All collected items.
  List<DashboardItem> get items => List.unmodifiable(_items);

  /// Items filtered by type.
  List<DashboardItem> itemsOfType(DashboardDataType type) =>
      _items.where((i) => i.type == type).toList();

  /// Count of items per type for badge display.
  Map<DashboardDataType, int> get typeCounts {
    final counts = <DashboardDataType, int>{};
    for (final type in DashboardDataType.values) {
      final count = _items.where((i) => i.type == type).length;
      if (count > 0) counts[type] = count;
    }
    return counts;
  }

  /// Whether there is any data to show.
  bool get hasData => _items.isNotEmpty;

  void toggleDashboard() {
    _isOpen = !_isOpen;
    notifyListeners();
  }

  void openDashboard() {
    if (!_isOpen) {
      _isOpen = true;
      notifyListeners();
    }
  }

  void closeDashboard() {
    if (_isOpen) {
      _isOpen = false;
      notifyListeners();
    }
  }

  /// Remove a specific item by ID.
  void removeItem(String itemId) {
    _items.removeWhere((item) => item.id == itemId);
    notifyListeners();
  }

  void setActiveTab(DashboardDataType tab) {
    if (_activeTab != tab) {
      _activeTab = tab;
      notifyListeners();
    }
  }

  /// Add a trace result to the dashboard.
  void addTrace(
    Trace trace,
    String toolName,
    Map<String, dynamic> raw, {
    DataSource source = DataSource.agent,
  }) {
    _itemCounter++;
    _addItemBounded(
      DashboardItem(
        id: 'trace-$_itemCounter',
        type: DashboardDataType.traces,
        toolName: toolName,
        timestamp: DateTime.now(),
        rawData: raw,
        source: source,
        traceData: trace,
      ),
    );
    notifyListeners();
  }

  /// Add a log entries result to the dashboard.
  void addLogEntries(
    LogEntriesData data,
    String toolName,
    Map<String, dynamic> raw, {
    DataSource source = DataSource.agent,
  }) {
    _itemCounter++;
    _addItemBounded(
      DashboardItem(
        id: 'logs-$_itemCounter',
        type: DashboardDataType.logs,
        toolName: toolName,
        timestamp: DateTime.now(),
        rawData: raw,
        source: source,
        logData: data,
      ),
    );
    notifyListeners();
  }

  /// Add log patterns to the dashboard.
  void addLogPatterns(
    List<LogPattern> patterns,
    String toolName,
    Map<String, dynamic> raw, {
    DataSource source = DataSource.agent,
  }) {
    _itemCounter++;
    _addItemBounded(
      DashboardItem(
        id: 'log-patterns-$_itemCounter',
        type: DashboardDataType.logs,
        toolName: toolName,
        timestamp: DateTime.now(),
        rawData: raw,
        source: source,
        logPatterns: patterns,
      ),
    );
    notifyListeners();
  }

  /// Add a metric series result to the dashboard.
  void addMetricSeries(
    MetricSeries series,
    String toolName,
    Map<String, dynamic> raw, {
    DataSource source = DataSource.agent,
  }) {
    _itemCounter++;
    _addItemBounded(
      DashboardItem(
        id: 'metric-$_itemCounter',
        type: DashboardDataType.metrics,
        toolName: toolName,
        timestamp: DateTime.now(),
        rawData: raw,
        source: source,
        metricSeries: series,
      ),
    );
    notifyListeners();
  }

  /// Add a metrics dashboard result.
  void addMetricsDashboard(
    MetricsDashboardData data,
    String toolName,
    Map<String, dynamic> raw, {
    DataSource source = DataSource.agent,
  }) {
    _itemCounter++;
    _addItemBounded(
      DashboardItem(
        id: 'metrics-dashboard-$_itemCounter',
        type: DashboardDataType.metrics,
        toolName: toolName,
        timestamp: DateTime.now(),
        rawData: raw,
        source: source,
        metricsDashboard: data,
      ),
    );
    notifyListeners();
  }

  /// Add an alert/incident timeline result.
  void addAlerts(
    IncidentTimelineData data,
    String toolName,
    Map<String, dynamic> raw, {
    DataSource source = DataSource.agent,
  }) {
    _itemCounter++;
    _addItemBounded(
      DashboardItem(
        id: 'alert-$_itemCounter',
        type: DashboardDataType.alerts,
        toolName: toolName,
        timestamp: DateTime.now(),
        rawData: raw,
        source: source,
        alertData: data,
      ),
    );
    notifyListeners();
  }

  /// Add a remediation plan result.
  void addRemediation(
    RemediationPlan plan,
    String toolName,
    Map<String, dynamic> raw, {
    DataSource source = DataSource.agent,
  }) {
    _itemCounter++;
    _addItemBounded(
      DashboardItem(
        id: 'remediation-$_itemCounter',
        type: DashboardDataType.remediation,
        toolName: toolName,
        timestamp: DateTime.now(),
        rawData: raw,
        source: source,
        remediationPlan: plan,
      ),
    );
    notifyListeners();
  }

  /// Add a chart (Vega-Lite) result to the dashboard.
  void addChart(
    VegaChartData data,
    String toolName,
    Map<String, dynamic> raw, {
    DataSource source = DataSource.agent,
  }) {
    _itemCounter++;
    _addItemBounded(
      DashboardItem(
        id: 'chart-$_itemCounter',
        type: DashboardDataType.analytics,
        toolName: toolName,
        timestamp: DateTime.now(),
        rawData: raw,
        source: source,
        chartData: data,
      ),
    );
    notifyListeners();
  }

  /// Add a council synthesis result to the dashboard.
  void addCouncilSynthesis(
    CouncilSynthesisData data,
    String toolName,
    Map<String, dynamic> raw, {
    DataSource source = DataSource.agent,
  }) {
    _itemCounter++;
    _addItemBounded(
      DashboardItem(
        id: 'council-$_itemCounter',
        type: DashboardDataType.council,
        toolName: toolName,
        timestamp: DateTime.now(),
        rawData: raw,
        source: source,
        councilData: data,
      ),
    );
    notifyListeners();
  }

  /// Update the most recent council item with an activity graph.
  ///
  /// This is called when a council_graph event arrives after the synthesis.
  void updateCouncilWithActivityGraph(CouncilActivityGraph graph) {
    // Find the most recent council item
    for (var i = _items.length - 1; i >= 0; i--) {
      final item = _items[i];
      if (item.type == DashboardDataType.council && item.councilData != null) {
        // Create updated council data with the activity graph
        final updatedCouncil = CouncilSynthesisData(
          synthesis: item.councilData!.synthesis,
          overallSeverity: item.councilData!.overallSeverity,
          overallConfidence: item.councilData!.overallConfidence,
          mode: item.councilData!.mode,
          rounds: item.councilData!.rounds,
          panels: item.councilData!.panels,
          criticReport: item.councilData!.criticReport,
          activityGraph: graph,
          rawData: item.councilData!.rawData,
        );

        // Replace the item with updated data
        _items[i] = DashboardItem(
          id: item.id,
          type: item.type,
          toolName: item.toolName,
          timestamp: item.timestamp,
          rawData: item.rawData,
          source: item.source,
          councilData: updatedCouncil,
        );
        notifyListeners();
        return;
      }
    }
  }

  /// Process a dashboard event received from the backend's dedicated channel.
  ///
  /// This is the primary way to feed data into the dashboard. Events have
  /// the shape: `{category, widget_type, tool_name, data}`.
  /// Returns true if data was added successfully.
  ///
  /// Uses a single [notifyListeners] call at the end to avoid excessive
  /// widget rebuilds (the individual add* helpers each call notifyListeners,
  /// so we use the private _addItem* variants here).
  bool addFromEvent(Map<String, dynamic> event) {
    final category = event['category'] as String?;
    final toolName = event['tool_name'] as String? ?? 'unknown';
    final widgetType = event['widget_type'] as String?;
    final data = event['data'];

    if (category == null || data == null) return false;

    // Convert data to a Map if needed
    final Map<String, dynamic> dataMap;
    if (data is Map) {
      dataMap = Map<String, dynamic>.from(data);
    } else {
      return false;
    }

    try {
      // Parse and add items WITHOUT individual notifyListeners calls.
      // A single notifyListeners is fired at the end of this method.
      switch (widgetType) {
        case 'x-sre-trace-waterfall':
          final trace = Trace.fromJson(dataMap);
          if (trace.spans.isEmpty) return false;
          _addItemSilent(
            DashboardDataType.traces,
            toolName,
            dataMap,
            traceData: trace,
          );

        case 'x-sre-log-entries-viewer':
          final logData = LogEntriesData.fromJson(dataMap);
          if (logData.entries.isEmpty) return false;
          _addItemSilent(
            DashboardDataType.logs,
            toolName,
            dataMap,
            logData: logData,
          );

        case 'x-sre-log-pattern-viewer':
          final patterns = _parseLogPatterns(dataMap);
          if (patterns.isEmpty) return false;
          _addItemSilent(
            DashboardDataType.logs,
            toolName,
            dataMap,
            logPatterns: patterns,
          );

        case 'x-sre-metric-chart':
          final series = MetricSeries.fromJson(dataMap);
          if (series.points.isEmpty) return false;
          _addItemSilent(
            DashboardDataType.metrics,
            toolName,
            dataMap,
            metricSeries: series,
          );

        case 'x-sre-metrics-dashboard':
          final metricsData = MetricsDashboardData.fromJson(dataMap);
          if (metricsData.metrics.isEmpty) return false;
          _addItemSilent(
            DashboardDataType.metrics,
            toolName,
            dataMap,
            metricsDashboard: metricsData,
          );

        case 'x-sre-incident-timeline':
          final timelineData = IncidentTimelineData.fromJson(dataMap);
          if (timelineData.events.isEmpty) return false;
          _addItemSilent(
            DashboardDataType.alerts,
            toolName,
            dataMap,
            alertData: timelineData,
          );

        case 'x-sre-remediation-plan':
          final plan = RemediationPlan.fromJson(dataMap);
          if (plan.steps.isEmpty) return false;
          _addItemSilent(
            DashboardDataType.remediation,
            toolName,
            dataMap,
            remediationPlan: plan,
          );

        case 'x-sre-council-synthesis':
          final council = CouncilSynthesisData.fromJson(dataMap);
          _addItemSilent(
            DashboardDataType.council,
            toolName,
            dataMap,
            councilData: council,
          );

        case 'x-sre-vega-chart':
          final chart = VegaChartData.fromJson(dataMap);
          _addItemSilent(
            DashboardDataType.analytics,
            toolName,
            dataMap,
            chartData: chart,
          );

        default:
          debugPrint('Unknown dashboard widget_type: $widgetType');
          return false;
      }

      // Auto-open dashboard on first data
      final dashType = _categoryFromString(category);
      if (dashType != null && !_isOpen) {
        _isOpen = true;
        _activeTab = dashType;
      }

      // Single notification for the entire event processing.
      notifyListeners();
      return true;
    } catch (e) {
      debugPrint('Error processing dashboard event: $e');
      return false;
    }
  }

  /// Adds a DashboardItem without calling notifyListeners.
  /// Used by [addFromEvent] to batch multiple state changes.
  void _addItemSilent(
    DashboardDataType type,
    String toolName,
    Map<String, dynamic> rawData, {
    Trace? traceData,
    LogEntriesData? logData,
    List<LogPattern>? logPatterns,
    MetricSeries? metricSeries,
    MetricsDashboardData? metricsDashboard,
    IncidentTimelineData? alertData,
    RemediationPlan? remediationPlan,
    CouncilSynthesisData? councilData,
    VegaChartData? chartData,
  }) {
    _itemCounter++;
    final prefix = type.name;
    _addItemBounded(
      DashboardItem(
        id: '$prefix-$_itemCounter',
        type: type,
        toolName: toolName,
        timestamp: DateTime.now(),
        rawData: rawData,
        traceData: traceData,
        logData: logData,
        logPatterns: logPatterns,
        metricSeries: metricSeries,
        metricsDashboard: metricsDashboard,
        alertData: alertData,
        remediationPlan: remediationPlan,
        councilData: councilData,
        chartData: chartData,
      ),
    );
  }

  static DashboardDataType? _categoryFromString(String category) {
    switch (category) {
      case 'traces':
        return DashboardDataType.traces;
      case 'logs':
        return DashboardDataType.logs;
      case 'metrics':
        return DashboardDataType.metrics;
      case 'alerts':
        return DashboardDataType.alerts;
      case 'remediation':
        return DashboardDataType.remediation;
      case 'council':
        return DashboardDataType.council;
      case 'charts':
      case 'sql':
      case 'analytics':
        return DashboardDataType.analytics;
      default:
        return null;
    }
  }

  static List<LogPattern> _parseLogPatterns(Map<String, dynamic> data) {
    List<dynamic>? rawList;
    if (data.containsKey('patterns') && data['patterns'] is List) {
      rawList = data['patterns'] as List;
    }
    if (rawList == null) return [];
    return rawList
        .map((item) => LogPattern.fromJson(Map<String, dynamic>.from(item)))
        .toList();
  }

  // =========================================================================
  // Time Range & Loading State Management
  // =========================================================================

  /// Whether a panel type is currently loading data.
  bool isLoading(DashboardDataType type) => _loadingStates[type] ?? false;

  /// Error message for a panel type, or null if no error.
  String? errorFor(DashboardDataType type) => _errorStates[type];

  /// Set the time range for manual queries.
  void setTimeRange(TimeRange range) {
    _timeRange = range;
    notifyListeners();
  }

  /// Set loading state for a panel type.
  void setLoading(DashboardDataType type, bool loading) {
    _loadingStates[type] = loading;
    if (loading) _errorStates[type] = null;
    notifyListeners();
  }

  /// Set error state for a panel type.
  void setError(DashboardDataType type, String? error) {
    _errorStates[type] = error;
    notifyListeners();
  }

  /// Toggle auto-refresh. Call [setAutoRefreshCallback] first.
  void toggleAutoRefresh() {
    _autoRefresh = !_autoRefresh;
    // Always cancel existing timer first to prevent leaks.
    _refreshTimer?.cancel();
    _refreshTimer = null;
    if (_autoRefresh) {
      _refreshTimer = Timer.periodic(
        const Duration(seconds: 30),
        (_) => _onAutoRefresh?.call(),
      );
    }
    notifyListeners();
  }

  /// Register the callback invoked on each auto-refresh tick.
  void setAutoRefreshCallback(VoidCallback callback) {
    _onAutoRefresh = callback;
  }

  /// Remove only manually-queried items (preserve agent data).
  void clearManualItems() {
    _items.removeWhere((i) => i.source == DataSource.manual);
    notifyListeners();
  }

  /// Clear all collected data (e.g. on new session).
  void clear() {
    _items.clear();
    _itemCounter = 0;
    _loadingStates.clear();
    _errorStates.clear();
    _lastQueryFilters.clear();
    _bigQueryColumns = [];
    _bigQueryResults = [];
    _metricsQueryLanguage = 0;
    _refreshTimer?.cancel();
    _refreshTimer = null;
    _autoRefresh = false;
    notifyListeners();
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }
}
