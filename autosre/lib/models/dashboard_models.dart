/// Dashboard data models following the Perses-compatible spec.
///
/// These models mirror the backend Pydantic models and support
/// serialization to/from JSON for API communication.
library;

enum DashboardSource {
  local,
  cloudMonitoring;

  String get value {
    switch (this) {
      case DashboardSource.local:
        return 'local';
      case DashboardSource.cloudMonitoring:
        return 'cloud_monitoring';
    }
  }

  static DashboardSource fromString(String value) {
    switch (value) {
      case 'cloud_monitoring':
        return DashboardSource.cloudMonitoring;
      default:
        return DashboardSource.local;
    }
  }
}

enum PanelType {
  timeSeries,
  gauge,
  stat,
  table,
  logs,
  traces,
  pie,
  heatmap,
  bar,
  text,
  alertChart,
  scorecard,
  scatter,
  treemap,
  errorReporting,
  incidentList;

  String get value {
    switch (this) {
      case PanelType.timeSeries:
        return 'time_series';
      case PanelType.gauge:
        return 'gauge';
      case PanelType.stat:
        return 'stat';
      case PanelType.table:
        return 'table';
      case PanelType.logs:
        return 'logs';
      case PanelType.traces:
        return 'traces';
      case PanelType.pie:
        return 'pie';
      case PanelType.heatmap:
        return 'heatmap';
      case PanelType.bar:
        return 'bar';
      case PanelType.text:
        return 'text';
      case PanelType.alertChart:
        return 'alert_chart';
      case PanelType.scorecard:
        return 'scorecard';
      case PanelType.scatter:
        return 'scatter';
      case PanelType.treemap:
        return 'treemap';
      case PanelType.errorReporting:
        return 'error_reporting';
      case PanelType.incidentList:
        return 'incident_list';
    }
  }

  String get displayName {
    switch (this) {
      case PanelType.timeSeries:
        return 'Time Series';
      case PanelType.gauge:
        return 'Gauge';
      case PanelType.stat:
        return 'Stat';
      case PanelType.table:
        return 'Table';
      case PanelType.logs:
        return 'Logs';
      case PanelType.traces:
        return 'Traces';
      case PanelType.pie:
        return 'Pie Chart';
      case PanelType.heatmap:
        return 'Heatmap';
      case PanelType.bar:
        return 'Bar Chart';
      case PanelType.text:
        return 'Text';
      case PanelType.alertChart:
        return 'Alert Chart';
      case PanelType.scorecard:
        return 'Scorecard';
      case PanelType.scatter:
        return 'Scatter Plot';
      case PanelType.treemap:
        return 'Treemap';
      case PanelType.errorReporting:
        return 'Error Reporting';
      case PanelType.incidentList:
        return 'Incident List';
    }
  }

  static PanelType fromString(String value) {
    switch (value) {
      case 'time_series':
        return PanelType.timeSeries;
      case 'gauge':
        return PanelType.gauge;
      case 'stat':
        return PanelType.stat;
      case 'table':
        return PanelType.table;
      case 'logs':
        return PanelType.logs;
      case 'traces':
        return PanelType.traces;
      case 'pie':
        return PanelType.pie;
      case 'heatmap':
        return PanelType.heatmap;
      case 'bar':
        return PanelType.bar;
      case 'text':
        return PanelType.text;
      case 'alert_chart':
        return PanelType.alertChart;
      case 'scorecard':
        return PanelType.scorecard;
      case 'scatter':
        return PanelType.scatter;
      case 'treemap':
        return PanelType.treemap;
      case 'error_reporting':
        return PanelType.errorReporting;
      case 'incident_list':
        return PanelType.incidentList;
      default:
        return PanelType.timeSeries;
    }
  }
}

enum DatasourceType {
  prometheus,
  cloudMonitoring,
  loki,
  bigquery,
  tempo;

  String get value {
    switch (this) {
      case DatasourceType.prometheus:
        return 'prometheus';
      case DatasourceType.cloudMonitoring:
        return 'cloud_monitoring';
      case DatasourceType.loki:
        return 'loki';
      case DatasourceType.bigquery:
        return 'bigquery';
      case DatasourceType.tempo:
        return 'tempo';
    }
  }

  static DatasourceType fromString(String value) {
    switch (value) {
      case 'cloud_monitoring':
        return DatasourceType.cloudMonitoring;
      case 'loki':
        return DatasourceType.loki;
      case 'bigquery':
        return DatasourceType.bigquery;
      case 'tempo':
        return DatasourceType.tempo;
      default:
        return DatasourceType.prometheus;
    }
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

class GridPosition {
  final int x;
  final int y;
  final int width;
  final int height;

  const GridPosition({
    this.x = 0,
    this.y = 0,
    this.width = 12,
    this.height = 4,
  });

  factory GridPosition.fromJson(Map<String, dynamic> json) {
    return GridPosition(
      x: json['x'] as int? ?? 0,
      y: json['y'] as int? ?? 0,
      width: json['width'] as int? ?? 12,
      height: json['height'] as int? ?? 4,
    );
  }

  Map<String, dynamic> toJson() => {
        'x': x,
        'y': y,
        'width': width,
        'height': height,
      };

  GridPosition copyWith({int? x, int? y, int? width, int? height}) {
    return GridPosition(
      x: x ?? this.x,
      y: y ?? this.y,
      width: width ?? this.width,
      height: height ?? this.height,
    );
  }
}

class TimeRange {
  final String preset;
  final String? start;
  final String? end;
  final int? refreshIntervalSeconds;

  const TimeRange({
    this.preset = '1h',
    this.start,
    this.end,
    this.refreshIntervalSeconds,
  });

  factory TimeRange.fromJson(Map<String, dynamic> json) {
    return TimeRange(
      preset: json['preset'] as String? ?? '1h',
      start: json['start'] as String?,
      end: json['end'] as String?,
      refreshIntervalSeconds: json['refresh_interval_seconds'] as int?,
    );
  }

  Map<String, dynamic> toJson() {
    final map = <String, dynamic>{'preset': preset};
    if (start != null) map['start'] = start;
    if (end != null) map['end'] = end;
    if (refreshIntervalSeconds != null) {
      map['refresh_interval_seconds'] = refreshIntervalSeconds;
    }
    return map;
  }
}

class DatasourceRef {
  final String type;
  final String? uid;
  final String? projectId;

  const DatasourceRef({
    required this.type,
    this.uid,
    this.projectId,
  });

  factory DatasourceRef.fromJson(Map<String, dynamic> json) {
    return DatasourceRef(
      type: json['type'] as String? ?? 'prometheus',
      uid: json['uid'] as String?,
      projectId: json['project_id'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    final map = <String, dynamic>{'type': type};
    if (uid != null) map['uid'] = uid;
    if (projectId != null) map['project_id'] = projectId;
    return map;
  }
}

class PanelQuery {
  final DatasourceRef? datasource;
  final Map<String, dynamic>? prometheus;
  final Map<String, dynamic>? cloudMonitoring;
  final Map<String, dynamic>? logs;
  final Map<String, dynamic>? bigquery;
  final bool hidden;
  final String? refId;

  const PanelQuery({
    this.datasource,
    this.prometheus,
    this.cloudMonitoring,
    this.logs,
    this.bigquery,
    this.hidden = false,
    this.refId,
  });

  factory PanelQuery.fromJson(Map<String, dynamic> json) {
    return PanelQuery(
      datasource: json['datasource'] != null
          ? DatasourceRef.fromJson(json['datasource'] as Map<String, dynamic>)
          : null,
      prometheus: json['prometheus'] as Map<String, dynamic>?,
      cloudMonitoring: json['cloud_monitoring'] as Map<String, dynamic>?,
      logs: json['logs'] as Map<String, dynamic>?,
      bigquery: json['bigquery'] as Map<String, dynamic>?,
      hidden: json['hidden'] as bool? ?? false,
      refId: json['ref_id'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    final map = <String, dynamic>{};
    if (datasource != null) map['datasource'] = datasource!.toJson();
    if (prometheus != null) map['prometheus'] = prometheus;
    if (cloudMonitoring != null) map['cloud_monitoring'] = cloudMonitoring;
    if (logs != null) map['logs'] = logs;
    if (bigquery != null) map['bigquery'] = bigquery;
    if (hidden) map['hidden'] = hidden;
    if (refId != null) map['ref_id'] = refId;
    return map;
  }
}

class DashboardPanel {
  final String id;
  final String title;
  final PanelType type;
  final String description;
  final GridPosition gridPosition;
  final List<PanelQuery> queries;
  final List<Map<String, dynamic>> thresholds;
  final Map<String, dynamic>? display;
  final Map<String, dynamic>? textContent;
  final DatasourceRef? datasource;
  final String? unit;
  final int? decimals;
  final String? colorScheme;
  final Map<String, dynamic>? options;

  const DashboardPanel({
    required this.id,
    required this.title,
    this.type = PanelType.timeSeries,
    this.description = '',
    this.gridPosition = const GridPosition(),
    this.queries = const [],
    this.thresholds = const [],
    this.display,
    this.textContent,
    this.datasource,
    this.unit,
    this.decimals,
    this.colorScheme,
    this.options,
  });

  factory DashboardPanel.fromJson(Map<String, dynamic> json) {
    return DashboardPanel(
      id: json['id'] as String? ?? '',
      title: json['title'] as String? ?? '',
      type: PanelType.fromString(json['type'] as String? ?? 'time_series'),
      description: json['description'] as String? ?? '',
      gridPosition: json['grid_position'] != null
          ? GridPosition.fromJson(
              json['grid_position'] as Map<String, dynamic>)
          : const GridPosition(),
      queries: (json['queries'] as List<dynamic>?)
              ?.map((q) => PanelQuery.fromJson(q as Map<String, dynamic>))
              .toList() ??
          [],
      thresholds: (json['thresholds'] as List<dynamic>?)
              ?.map((t) => t as Map<String, dynamic>)
              .toList() ??
          [],
      display: json['display'] as Map<String, dynamic>?,
      textContent: json['text_content'] as Map<String, dynamic>?,
      datasource: json['datasource'] != null
          ? DatasourceRef.fromJson(json['datasource'] as Map<String, dynamic>)
          : null,
      unit: json['unit'] as String?,
      decimals: json['decimals'] as int?,
      colorScheme: json['color_scheme'] as String?,
      options: json['options'] as Map<String, dynamic>?,
    );
  }

  Map<String, dynamic> toJson() {
    final map = <String, dynamic>{
      'id': id,
      'title': title,
      'type': type.value,
      'description': description,
      'grid_position': gridPosition.toJson(),
      'queries': queries.map((q) => q.toJson()).toList(),
      'thresholds': thresholds,
    };
    if (display != null) map['display'] = display;
    if (textContent != null) map['text_content'] = textContent;
    if (datasource != null) map['datasource'] = datasource!.toJson();
    if (unit != null) map['unit'] = unit;
    if (decimals != null) map['decimals'] = decimals;
    if (colorScheme != null) map['color_scheme'] = colorScheme;
    if (options != null) map['options'] = options;
    return map;
  }

  DashboardPanel copyWith({
    String? id,
    String? title,
    PanelType? type,
    String? description,
    GridPosition? gridPosition,
    List<PanelQuery>? queries,
    List<Map<String, dynamic>>? thresholds,
    Map<String, dynamic>? display,
    Map<String, dynamic>? textContent,
    DatasourceRef? datasource,
    String? unit,
    int? decimals,
    String? colorScheme,
    Map<String, dynamic>? options,
  }) {
    return DashboardPanel(
      id: id ?? this.id,
      title: title ?? this.title,
      type: type ?? this.type,
      description: description ?? this.description,
      gridPosition: gridPosition ?? this.gridPosition,
      queries: queries ?? this.queries,
      thresholds: thresholds ?? this.thresholds,
      display: display ?? this.display,
      textContent: textContent ?? this.textContent,
      datasource: datasource ?? this.datasource,
      unit: unit ?? this.unit,
      decimals: decimals ?? this.decimals,
      colorScheme: colorScheme ?? this.colorScheme,
      options: options ?? this.options,
    );
  }
}

class DashboardVariable {
  final String name;
  final String type;
  final String? label;
  final String? description;
  final String? query;
  final List<String> values;
  final String? defaultValue;
  final bool multi;
  final bool includeAll;

  const DashboardVariable({
    required this.name,
    this.type = 'query',
    this.label,
    this.description,
    this.query,
    this.values = const [],
    this.defaultValue,
    this.multi = false,
    this.includeAll = false,
  });

  factory DashboardVariable.fromJson(Map<String, dynamic> json) {
    return DashboardVariable(
      name: json['name'] as String? ?? '',
      type: json['type'] as String? ?? 'query',
      label: json['label'] as String?,
      description: json['description'] as String?,
      query: json['query'] as String?,
      values: (json['values'] as List<dynamic>?)
              ?.map((v) => v as String)
              .toList() ??
          [],
      defaultValue: json['default_value'] as String?,
      multi: json['multi'] as bool? ?? false,
      includeAll: json['include_all'] as bool? ?? false,
    );
  }

  Map<String, dynamic> toJson() {
    final map = <String, dynamic>{
      'name': name,
      'type': type,
    };
    if (label != null) map['label'] = label;
    if (description != null) map['description'] = description;
    if (query != null) map['query'] = query;
    if (values.isNotEmpty) map['values'] = values;
    if (defaultValue != null) map['default_value'] = defaultValue;
    if (multi) map['multi'] = multi;
    if (includeAll) map['include_all'] = includeAll;
    return map;
  }
}

class DashboardFilter {
  final String key;
  final String value;
  final String operator;
  final String? label;

  const DashboardFilter({
    required this.key,
    required this.value,
    this.operator = '=',
    this.label,
  });

  factory DashboardFilter.fromJson(Map<String, dynamic> json) {
    return DashboardFilter(
      key: json['key'] as String? ?? '',
      value: json['value'] as String? ?? '',
      operator: json['operator'] as String? ?? '=',
      label: json['label'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    final map = <String, dynamic>{
      'key': key,
      'value': value,
      'operator': operator,
    };
    if (label != null) map['label'] = label;
    return map;
  }
}

class DashboardMetadata {
  final String? createdAt;
  final String? updatedAt;
  final String? createdBy;
  final int version;
  final List<String> tags;
  final bool starred;
  final String? folder;

  const DashboardMetadata({
    this.createdAt,
    this.updatedAt,
    this.createdBy,
    this.version = 1,
    this.tags = const [],
    this.starred = false,
    this.folder,
  });

  factory DashboardMetadata.fromJson(Map<String, dynamic> json) {
    return DashboardMetadata(
      createdAt: json['created_at'] as String?,
      updatedAt: json['updated_at'] as String?,
      createdBy: json['created_by'] as String?,
      version: json['version'] as int? ?? 1,
      tags: (json['tags'] as List<dynamic>?)
              ?.map((t) => t as String)
              .toList() ??
          [],
      starred: json['starred'] as bool? ?? false,
      folder: json['folder'] as String?,
    );
  }

  Map<String, dynamic> toJson() {
    final map = <String, dynamic>{
      'version': version,
      'tags': tags,
      'starred': starred,
    };
    if (createdAt != null) map['created_at'] = createdAt;
    if (updatedAt != null) map['updated_at'] = updatedAt;
    if (createdBy != null) map['created_by'] = createdBy;
    if (folder != null) map['folder'] = folder;
    return map;
  }
}

class DashboardModel {
  final String id;
  final String? name;
  final String displayName;
  final String description;
  final DashboardSource source;
  final String? projectId;
  final List<DashboardPanel> panels;
  final List<DashboardVariable> variables;
  final List<DashboardFilter> filters;
  final TimeRange timeRange;
  final Map<String, String> labels;
  final int gridColumns;
  final DashboardMetadata metadata;

  const DashboardModel({
    required this.id,
    this.name,
    required this.displayName,
    this.description = '',
    this.source = DashboardSource.local,
    this.projectId,
    this.panels = const [],
    this.variables = const [],
    this.filters = const [],
    this.timeRange = const TimeRange(),
    this.labels = const {},
    this.gridColumns = 24,
    this.metadata = const DashboardMetadata(),
  });

  factory DashboardModel.fromJson(Map<String, dynamic> json) {
    return DashboardModel(
      id: json['id'] as String? ?? '',
      name: json['name'] as String?,
      displayName: json['display_name'] as String? ?? 'Untitled',
      description: json['description'] as String? ?? '',
      source:
          DashboardSource.fromString(json['source'] as String? ?? 'local'),
      projectId: json['project_id'] as String?,
      panels: (json['panels'] as List<dynamic>?)
              ?.map((p) =>
                  DashboardPanel.fromJson(p as Map<String, dynamic>))
              .toList() ??
          [],
      variables: (json['variables'] as List<dynamic>?)
              ?.map((v) =>
                  DashboardVariable.fromJson(v as Map<String, dynamic>))
              .toList() ??
          [],
      filters: (json['filters'] as List<dynamic>?)
              ?.map((f) =>
                  DashboardFilter.fromJson(f as Map<String, dynamic>))
              .toList() ??
          [],
      timeRange: json['time_range'] != null
          ? TimeRange.fromJson(json['time_range'] as Map<String, dynamic>)
          : const TimeRange(),
      labels: (json['labels'] as Map<String, dynamic>?)
              ?.map((k, v) => MapEntry(k, v.toString())) ??
          {},
      gridColumns: json['grid_columns'] as int? ?? 24,
      metadata: json['metadata'] != null
          ? DashboardMetadata.fromJson(
              json['metadata'] as Map<String, dynamic>)
          : const DashboardMetadata(),
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        if (name != null) 'name': name,
        'display_name': displayName,
        'description': description,
        'source': source.value,
        if (projectId != null) 'project_id': projectId,
        'panels': panels.map((p) => p.toJson()).toList(),
        'variables': variables.map((v) => v.toJson()).toList(),
        'filters': filters.map((f) => f.toJson()).toList(),
        'time_range': timeRange.toJson(),
        'labels': labels,
        'grid_columns': gridColumns,
        'metadata': metadata.toJson(),
      };

  DashboardModel copyWith({
    String? id,
    String? name,
    String? displayName,
    String? description,
    DashboardSource? source,
    String? projectId,
    List<DashboardPanel>? panels,
    List<DashboardVariable>? variables,
    List<DashboardFilter>? filters,
    TimeRange? timeRange,
    Map<String, String>? labels,
    int? gridColumns,
    DashboardMetadata? metadata,
  }) {
    return DashboardModel(
      id: id ?? this.id,
      name: name ?? this.name,
      displayName: displayName ?? this.displayName,
      description: description ?? this.description,
      source: source ?? this.source,
      projectId: projectId ?? this.projectId,
      panels: panels ?? this.panels,
      variables: variables ?? this.variables,
      filters: filters ?? this.filters,
      timeRange: timeRange ?? this.timeRange,
      labels: labels ?? this.labels,
      gridColumns: gridColumns ?? this.gridColumns,
      metadata: metadata ?? this.metadata,
    );
  }
}

class DashboardSummary {
  final String id;
  final String displayName;
  final String description;
  final DashboardSource source;
  final int panelCount;
  final DashboardMetadata? metadata;
  final Map<String, String> labels;

  const DashboardSummary({
    required this.id,
    required this.displayName,
    this.description = '',
    this.source = DashboardSource.local,
    this.panelCount = 0,
    this.metadata,
    this.labels = const {},
  });

  factory DashboardSummary.fromJson(Map<String, dynamic> json) {
    return DashboardSummary(
      id: json['id'] as String? ?? '',
      displayName: json['display_name'] as String? ?? 'Untitled',
      description: json['description'] as String? ?? '',
      source:
          DashboardSource.fromString(json['source'] as String? ?? 'local'),
      panelCount: json['panel_count'] as int? ?? 0,
      metadata: json['metadata'] != null
          ? DashboardMetadata.fromJson(
              json['metadata'] as Map<String, dynamic>)
          : null,
      labels: (json['labels'] as Map<String, dynamic>?)
              ?.map((k, v) => MapEntry(k, v.toString())) ??
          {},
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'display_name': displayName,
        'description': description,
        'source': source.value,
        'panel_count': panelCount,
        if (metadata != null) 'metadata': metadata!.toJson(),
        'labels': labels,
      };
}
