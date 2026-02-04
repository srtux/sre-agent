import 'package:flutter/foundation.dart';

import '../models/adk_schema.dart';

/// Categorizes tool call data for dashboard display.
enum DashboardDataType {
  logs,
  metrics,
  traces,
  alerts,
  remediation,
  council,
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

  DashboardItem({
    required this.id,
    required this.type,
    required this.toolName,
    required this.timestamp,
    required this.rawData,
    this.logData,
    this.logPatterns,
    this.metricSeries,
    this.metricsDashboard,
    this.traceData,
    this.alertData,
    this.remediationPlan,
    this.councilData,
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
    default:
      return null;
  }
}

/// Central state for the investigation dashboard.
///
/// Collects tool call results from the A2UI stream and makes them
/// available as categorized, interactive data panels.
class DashboardState extends ChangeNotifier {
  final List<DashboardItem> _items = [];
  int _itemCounter = 0;

  /// Whether the dashboard panel is visible.
  bool _isOpen = false;
  bool get isOpen => _isOpen;

  /// Currently selected tab in the dashboard.
  DashboardDataType _activeTab = DashboardDataType.traces;
  DashboardDataType get activeTab => _activeTab;

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

  void setActiveTab(DashboardDataType tab) {
    if (_activeTab != tab) {
      _activeTab = tab;
      notifyListeners();
    }
  }

  /// Add a trace result to the dashboard.
  void addTrace(Trace trace, String toolName, Map<String, dynamic> raw) {
    _itemCounter++;
    _items.add(DashboardItem(
      id: 'trace-$_itemCounter',
      type: DashboardDataType.traces,
      toolName: toolName,
      timestamp: DateTime.now(),
      rawData: raw,
      traceData: trace,
    ));
    notifyListeners();
  }

  /// Add a log entries result to the dashboard.
  void addLogEntries(
      LogEntriesData data, String toolName, Map<String, dynamic> raw) {
    _itemCounter++;
    _items.add(DashboardItem(
      id: 'logs-$_itemCounter',
      type: DashboardDataType.logs,
      toolName: toolName,
      timestamp: DateTime.now(),
      rawData: raw,
      logData: data,
    ));
    notifyListeners();
  }

  /// Add log patterns to the dashboard.
  void addLogPatterns(
      List<LogPattern> patterns, String toolName, Map<String, dynamic> raw) {
    _itemCounter++;
    _items.add(DashboardItem(
      id: 'log-patterns-$_itemCounter',
      type: DashboardDataType.logs,
      toolName: toolName,
      timestamp: DateTime.now(),
      rawData: raw,
      logPatterns: patterns,
    ));
    notifyListeners();
  }

  /// Add a metric series result to the dashboard.
  void addMetricSeries(
      MetricSeries series, String toolName, Map<String, dynamic> raw) {
    _itemCounter++;
    _items.add(DashboardItem(
      id: 'metric-$_itemCounter',
      type: DashboardDataType.metrics,
      toolName: toolName,
      timestamp: DateTime.now(),
      rawData: raw,
      metricSeries: series,
    ));
    notifyListeners();
  }

  /// Add a metrics dashboard result.
  void addMetricsDashboard(
      MetricsDashboardData data, String toolName, Map<String, dynamic> raw) {
    _itemCounter++;
    _items.add(DashboardItem(
      id: 'metrics-dashboard-$_itemCounter',
      type: DashboardDataType.metrics,
      toolName: toolName,
      timestamp: DateTime.now(),
      rawData: raw,
      metricsDashboard: data,
    ));
    notifyListeners();
  }

  /// Add an alert/incident timeline result.
  void addAlerts(
      IncidentTimelineData data, String toolName, Map<String, dynamic> raw) {
    _itemCounter++;
    _items.add(DashboardItem(
      id: 'alert-$_itemCounter',
      type: DashboardDataType.alerts,
      toolName: toolName,
      timestamp: DateTime.now(),
      rawData: raw,
      alertData: data,
    ));
    notifyListeners();
  }

  /// Add a remediation plan result.
  void addRemediation(
      RemediationPlan plan, String toolName, Map<String, dynamic> raw) {
    _itemCounter++;
    _items.add(DashboardItem(
      id: 'remediation-$_itemCounter',
      type: DashboardDataType.remediation,
      toolName: toolName,
      timestamp: DateTime.now(),
      rawData: raw,
      remediationPlan: plan,
    ));
    notifyListeners();
  }

  /// Add a council synthesis result to the dashboard.
  void addCouncilSynthesis(
      CouncilSynthesisData data, String toolName, Map<String, dynamic> raw) {
    _itemCounter++;
    _items.add(DashboardItem(
      id: 'council-$_itemCounter',
      type: DashboardDataType.council,
      toolName: toolName,
      timestamp: DateTime.now(),
      rawData: raw,
      councilData: data,
    ));
    notifyListeners();
  }

  /// Process a dashboard event received from the backend's dedicated channel.
  ///
  /// This is the primary way to feed data into the dashboard. Events have
  /// the shape: `{category, widget_type, tool_name, data}`.
  /// Returns true if data was added successfully.
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
      switch (widgetType) {
        case 'x-sre-trace-waterfall':
          final trace = Trace.fromJson(dataMap);
          if (trace.spans.isEmpty) return false;
          addTrace(trace, toolName, dataMap);

        case 'x-sre-log-entries-viewer':
          final logData = LogEntriesData.fromJson(dataMap);
          if (logData.entries.isEmpty) return false;
          addLogEntries(logData, toolName, dataMap);

        case 'x-sre-log-pattern-viewer':
          final patterns = _parseLogPatterns(dataMap);
          if (patterns.isEmpty) return false;
          addLogPatterns(patterns, toolName, dataMap);

        case 'x-sre-metric-chart':
          final series = MetricSeries.fromJson(dataMap);
          if (series.points.isEmpty) return false;
          addMetricSeries(series, toolName, dataMap);

        case 'x-sre-metrics-dashboard':
          final metricsData = MetricsDashboardData.fromJson(dataMap);
          if (metricsData.metrics.isEmpty) return false;
          addMetricsDashboard(metricsData, toolName, dataMap);

        case 'x-sre-incident-timeline':
          final timelineData = IncidentTimelineData.fromJson(dataMap);
          if (timelineData.events.isEmpty) return false;
          addAlerts(timelineData, toolName, dataMap);

        case 'x-sre-remediation-plan':
          final plan = RemediationPlan.fromJson(dataMap);
          if (plan.steps.isEmpty) return false;
          addRemediation(plan, toolName, dataMap);

        case 'x-sre-council-synthesis':
          final council = CouncilSynthesisData.fromJson(dataMap);
          addCouncilSynthesis(council, toolName, dataMap);

        default:
          debugPrint('Unknown dashboard widget_type: $widgetType');
          return false;
      }

      // Auto-open dashboard on first data
      final dashType = _categoryFromString(category);
      if (dashType != null && !_isOpen) {
        openDashboard();
        setActiveTab(dashType);
      }

      return true;
    } catch (e) {
      debugPrint('Error processing dashboard event: $e');
      return false;
    }
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

  /// Clear all collected data (e.g. on new session).
  void clear() {
    _items.clear();
    _itemCounter = 0;
    notifyListeners();
  }
}
