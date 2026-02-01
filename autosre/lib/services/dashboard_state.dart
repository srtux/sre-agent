import 'package:flutter/foundation.dart';
import '../models/adk_schema.dart';

/// Categorizes tool call data for dashboard display.
enum DashboardDataType {
  logs,
  metrics,
  traces,
  alerts,
  remediation,
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

  /// Clear all collected data (e.g. on new session).
  void clear() {
    _items.clear();
    _itemCounter = 0;
    notifyListeners();
  }
}
