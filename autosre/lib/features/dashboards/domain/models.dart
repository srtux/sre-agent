import 'package:freezed_annotation/freezed_annotation.dart';

part 'models.freezed.dart';
part 'models.g.dart';

@JsonEnum(alwaysCreate: true)
enum DashboardSource {
  @JsonValue('local')
  local,
  @JsonValue('cloud_monitoring')
  cloudMonitoring;

  static DashboardSource fromString(String value) {
    if (value == 'cloud_monitoring') return DashboardSource.cloudMonitoring;
    return DashboardSource.local;
  }
}

@JsonEnum(alwaysCreate: true)
enum PanelType {
  @JsonValue('time_series')
  timeSeries,
  @JsonValue('gauge')
  gauge,
  @JsonValue('stat')
  stat,
  @JsonValue('table')
  table,
  @JsonValue('logs')
  logs,
  @JsonValue('traces')
  traces,
  @JsonValue('pie')
  pie,
  @JsonValue('heatmap')
  heatmap,
  @JsonValue('bar')
  bar,
  @JsonValue('text')
  text,
  @JsonValue('alert_chart')
  alertChart,
  @JsonValue('scorecard')
  scorecard,
  @JsonValue('scatter')
  scatter,
  @JsonValue('treemap')
  treemap,
  @JsonValue('error_reporting')
  errorReporting,
  @JsonValue('incident_list')
  incidentList;

  String get displayName {
    switch (this) {
      case PanelType.timeSeries: return 'Time Series';
      case PanelType.gauge: return 'Gauge';
      case PanelType.stat: return 'Stat';
      case PanelType.table: return 'Table';
      case PanelType.logs: return 'Logs';
      case PanelType.traces: return 'Traces';
      case PanelType.pie: return 'Pie Chart';
      case PanelType.heatmap: return 'Heatmap';
      case PanelType.bar: return 'Bar Chart';
      case PanelType.text: return 'Text';
      case PanelType.alertChart: return 'Alert Chart';
      case PanelType.scorecard: return 'Scorecard';
      case PanelType.scatter: return 'Scatter Plot';
      case PanelType.treemap: return 'Treemap';
      case PanelType.errorReporting: return 'Error Reporting';
      case PanelType.incidentList: return 'Incident List';
    }
  }

  static PanelType fromString(String value) {
    return PanelType.values.firstWhere(
      (e) => e.name == value || (e.toJson() as String) == value,
      orElse: () => PanelType.timeSeries,
    );
  }

  Object? toJson() => _$PanelTypeEnumMap[this];
}

@JsonEnum(alwaysCreate: true)
enum DatasourceType {
  @JsonValue('prometheus')
  prometheus,
  @JsonValue('cloud_monitoring')
  cloudMonitoring,
  @JsonValue('loki')
  loki,
  @JsonValue('bigquery')
  bigquery,
  @JsonValue('tempo')
  tempo;

  static DatasourceType fromString(String value) {
    if (value == 'cloud_monitoring') return DatasourceType.cloudMonitoring;
    if (value == 'loki') return DatasourceType.loki;
    if (value == 'bigquery') return DatasourceType.bigquery;
    if (value == 'tempo') return DatasourceType.tempo;
    return DatasourceType.prometheus;
  }
}

enum TimeRangePreset {
  fiveMinutes('5m', 'Last 5 minutes'),
  fifteenMinutes('15m', 'Last 15 minutes'),
  thirtyMinutes('30m', 'Last 30 minutes'),
  oneHour('1h', 'Last 1 hour'),
  threeHours('3h', 'Last 3 hours'),
  sixHours('6h', 'Last 6 hours'),
  twelveHours('12h', 'Last 12 hours'),
  twentyFourHours('24h', 'Last 24 hours'),
  twoDays('2d', 'Last 2 days'),
  sevenDays('7d', 'Last 7 days'),
  thirtyDays('30d', 'Last 30 days'),
  custom('custom', 'Custom');

  const TimeRangePreset(this.value, this.displayName);
  final String value;
  final String displayName;

  static TimeRangePreset fromString(String value) {
    return TimeRangePreset.values.firstWhere(
      (e) => e.value == value,
      orElse: () => TimeRangePreset.oneHour,
    );
  }
}

@freezed
abstract class GridPosition with _$GridPosition {
  const factory GridPosition({
    @Default(0) int x,
    @Default(0) int y,
    @Default(12) int width,
    @Default(4) int height,
  }) = _GridPosition;

  factory GridPosition.fromJson(Map<String, dynamic> json) =>
      _$GridPositionFromJson(json);
}

@freezed
abstract class TimeRange with _$TimeRange {
  const factory TimeRange({
    @Default('1h') String preset,
    String? start,
    String? end,
    @JsonKey(name: 'refresh_interval_seconds') int? refreshIntervalSeconds,
  }) = _TimeRange;

  factory TimeRange.fromJson(Map<String, dynamic> json) =>
      _$TimeRangeFromJson(json);
}

@freezed
abstract class DatasourceRef with _$DatasourceRef {
  const factory DatasourceRef({
    required String type,
    String? uid,
    @JsonKey(name: 'project_id') String? projectId,
  }) = _DatasourceRef;

  factory DatasourceRef.fromJson(Map<String, dynamic> json) =>
      _$DatasourceRefFromJson(json);
}

@freezed
abstract class PanelQuery with _$PanelQuery {
  const factory PanelQuery({
    DatasourceRef? datasource,
    Map<String, dynamic>? prometheus,
    @JsonKey(name: 'cloud_monitoring') Map<String, dynamic>? cloudMonitoring,
    Map<String, dynamic>? logs,
    Map<String, dynamic>? bigquery,
    @Default(false) bool hidden,
    @JsonKey(name: 'ref_id') String? refId,
  }) = _PanelQuery;

  factory PanelQuery.fromJson(Map<String, dynamic> json) =>
      _$PanelQueryFromJson(json);
}

@freezed
abstract class DashboardPanel with _$DashboardPanel {
  const factory DashboardPanel({
    required String id,
    required String title,
    @Default(PanelType.timeSeries) PanelType type,
    @Default('') String description,
    @JsonKey(name: 'grid_position') @Default(GridPosition()) GridPosition gridPosition,
    @Default([]) List<PanelQuery> queries,
    @Default([]) List<Map<String, dynamic>> thresholds,
    Map<String, dynamic>? display,
    @JsonKey(name: 'text_content') Map<String, dynamic>? textContent,
    DatasourceRef? datasource,
    String? unit,
    int? decimals,
    @JsonKey(name: 'color_scheme') String? colorScheme,
    Map<String, dynamic>? options,
  }) = _DashboardPanel;

  factory DashboardPanel.fromJson(Map<String, dynamic> json) =>
      _$DashboardPanelFromJson(json);
}

@freezed
abstract class DashboardVariable with _$DashboardVariable {
  const factory DashboardVariable({
    required String name,
    @Default('query') String type,
    String? label,
    String? description,
    String? query,
    @Default([]) List<String> values,
    @JsonKey(name: 'default_value') String? defaultValue,
    @Default(false) bool multi,
    @JsonKey(name: 'include_all') @Default(false) bool includeAll,
  }) = _DashboardVariable;

  factory DashboardVariable.fromJson(Map<String, dynamic> json) =>
      _$DashboardVariableFromJson(json);
}

@freezed
abstract class DashboardFilter with _$DashboardFilter {
  const factory DashboardFilter({
    required String key,
    required String value,
    @Default('=') String operator,
    String? label,
  }) = _DashboardFilter;

  factory DashboardFilter.fromJson(Map<String, dynamic> json) =>
      _$DashboardFilterFromJson(json);
}

@freezed
abstract class DashboardMetadata with _$DashboardMetadata {
  const factory DashboardMetadata({
    @JsonKey(name: 'created_at') String? createdAt,
    @JsonKey(name: 'updated_at') String? updatedAt,
    @JsonKey(name: 'created_by') String? createdBy,
    @Default(1) int version,
    @Default([]) List<String> tags,
    @Default(false) bool starred,
    String? folder,
  }) = _DashboardMetadata;

  factory DashboardMetadata.fromJson(Map<String, dynamic> json) =>
      _$DashboardMetadataFromJson(json);
}

@freezed
abstract class Dashboard with _$Dashboard {
  const factory Dashboard({
    required String id,
    String? name,
    @JsonKey(name: 'display_name') required String displayName,
    @Default('') String description,
    @Default(DashboardSource.local) DashboardSource source,
    @JsonKey(name: 'project_id') String? projectId,
    @Default([]) List<DashboardPanel> panels,
    @Default([]) List<DashboardVariable> variables,
    @Default([]) List<DashboardFilter> filters,
    @JsonKey(name: 'time_range') @Default(TimeRange()) TimeRange timeRange,
    @Default({}) Map<String, String> labels,
    @JsonKey(name: 'grid_columns') @Default(24) int gridColumns,
    @Default(DashboardMetadata()) DashboardMetadata metadata,
  }) = _Dashboard;

  factory Dashboard.fromJson(Map<String, dynamic> json) =>
      _$DashboardFromJson(json);
}

@freezed
abstract class DashboardSummary with _$DashboardSummary {
  const factory DashboardSummary({
    required String id,
    @JsonKey(name: 'display_name') required String displayName,
    @Default('') String description,
    @Default(DashboardSource.local) DashboardSource source,
    @JsonKey(name: 'panel_count') @Default(0) int panelCount,
    DashboardMetadata? metadata,
    @Default({}) Map<String, String> labels,
  }) = _DashboardSummary;

  factory DashboardSummary.fromJson(Map<String, dynamic> json) =>
      _$DashboardSummaryFromJson(json);
}
