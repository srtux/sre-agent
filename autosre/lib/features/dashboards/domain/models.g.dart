// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_GridPosition _$GridPositionFromJson(Map<String, dynamic> json) =>
    _GridPosition(
      x: (json['x'] as num?)?.toInt() ?? 0,
      y: (json['y'] as num?)?.toInt() ?? 0,
      width: (json['width'] as num?)?.toInt() ?? 12,
      height: (json['height'] as num?)?.toInt() ?? 4,
    );

Map<String, dynamic> _$GridPositionToJson(_GridPosition instance) =>
    <String, dynamic>{
      'x': instance.x,
      'y': instance.y,
      'width': instance.width,
      'height': instance.height,
    };

_TimeRange _$TimeRangeFromJson(Map<String, dynamic> json) => _TimeRange(
  preset: json['preset'] as String? ?? '1h',
  start: json['start'] as String?,
  end: json['end'] as String?,
  refreshIntervalSeconds: (json['refresh_interval_seconds'] as num?)?.toInt(),
);

Map<String, dynamic> _$TimeRangeToJson(_TimeRange instance) =>
    <String, dynamic>{
      'preset': instance.preset,
      'start': instance.start,
      'end': instance.end,
      'refresh_interval_seconds': instance.refreshIntervalSeconds,
    };

_DatasourceRef _$DatasourceRefFromJson(Map<String, dynamic> json) =>
    _DatasourceRef(
      type: json['type'] as String,
      uid: json['uid'] as String?,
      projectId: json['project_id'] as String?,
    );

Map<String, dynamic> _$DatasourceRefToJson(_DatasourceRef instance) =>
    <String, dynamic>{
      'type': instance.type,
      'uid': instance.uid,
      'project_id': instance.projectId,
    };

_PanelQuery _$PanelQueryFromJson(Map<String, dynamic> json) => _PanelQuery(
  datasource: json['datasource'] == null
      ? null
      : DatasourceRef.fromJson(json['datasource'] as Map<String, dynamic>),
  prometheus: json['prometheus'] as Map<String, dynamic>?,
  cloudMonitoring: json['cloud_monitoring'] as Map<String, dynamic>?,
  logs: json['logs'] as Map<String, dynamic>?,
  bigquery: json['bigquery'] as Map<String, dynamic>?,
  hidden: json['hidden'] as bool? ?? false,
  refId: json['ref_id'] as String?,
);

Map<String, dynamic> _$PanelQueryToJson(_PanelQuery instance) =>
    <String, dynamic>{
      'datasource': instance.datasource,
      'prometheus': instance.prometheus,
      'cloud_monitoring': instance.cloudMonitoring,
      'logs': instance.logs,
      'bigquery': instance.bigquery,
      'hidden': instance.hidden,
      'ref_id': instance.refId,
    };

_DashboardPanel _$DashboardPanelFromJson(Map<String, dynamic> json) =>
    _DashboardPanel(
      id: json['id'] as String,
      title: json['title'] as String,
      type:
          $enumDecodeNullable(_$PanelTypeEnumMap, json['type']) ??
          PanelType.timeSeries,
      description: json['description'] as String? ?? '',
      gridPosition: json['grid_position'] == null
          ? const GridPosition()
          : GridPosition.fromJson(
              json['grid_position'] as Map<String, dynamic>,
            ),
      queries:
          (json['queries'] as List<dynamic>?)
              ?.map((e) => PanelQuery.fromJson(e as Map<String, dynamic>))
              .toList() ??
          const [],
      thresholds:
          (json['thresholds'] as List<dynamic>?)
              ?.map((e) => e as Map<String, dynamic>)
              .toList() ??
          const [],
      display: json['display'] as Map<String, dynamic>?,
      textContent: json['text_content'] as Map<String, dynamic>?,
      datasource: json['datasource'] == null
          ? null
          : DatasourceRef.fromJson(json['datasource'] as Map<String, dynamic>),
      unit: json['unit'] as String?,
      decimals: (json['decimals'] as num?)?.toInt(),
      colorScheme: json['color_scheme'] as String?,
      options: json['options'] as Map<String, dynamic>?,
    );

Map<String, dynamic> _$DashboardPanelToJson(_DashboardPanel instance) =>
    <String, dynamic>{
      'id': instance.id,
      'title': instance.title,
      'type': instance.type,
      'description': instance.description,
      'grid_position': instance.gridPosition,
      'queries': instance.queries,
      'thresholds': instance.thresholds,
      'display': instance.display,
      'text_content': instance.textContent,
      'datasource': instance.datasource,
      'unit': instance.unit,
      'decimals': instance.decimals,
      'color_scheme': instance.colorScheme,
      'options': instance.options,
    };

const _$PanelTypeEnumMap = {
  PanelType.timeSeries: 'time_series',
  PanelType.gauge: 'gauge',
  PanelType.stat: 'stat',
  PanelType.table: 'table',
  PanelType.logs: 'logs',
  PanelType.traces: 'traces',
  PanelType.pie: 'pie',
  PanelType.heatmap: 'heatmap',
  PanelType.bar: 'bar',
  PanelType.text: 'text',
  PanelType.alertChart: 'alert_chart',
  PanelType.scorecard: 'scorecard',
  PanelType.scatter: 'scatter',
  PanelType.treemap: 'treemap',
  PanelType.errorReporting: 'error_reporting',
  PanelType.incidentList: 'incident_list',
};

_DashboardVariable _$DashboardVariableFromJson(Map<String, dynamic> json) =>
    _DashboardVariable(
      name: json['name'] as String,
      type: json['type'] as String? ?? 'query',
      label: json['label'] as String?,
      description: json['description'] as String?,
      query: json['query'] as String?,
      values:
          (json['values'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          const [],
      defaultValue: json['default_value'] as String?,
      multi: json['multi'] as bool? ?? false,
      includeAll: json['include_all'] as bool? ?? false,
    );

Map<String, dynamic> _$DashboardVariableToJson(_DashboardVariable instance) =>
    <String, dynamic>{
      'name': instance.name,
      'type': instance.type,
      'label': instance.label,
      'description': instance.description,
      'query': instance.query,
      'values': instance.values,
      'default_value': instance.defaultValue,
      'multi': instance.multi,
      'include_all': instance.includeAll,
    };

_DashboardFilter _$DashboardFilterFromJson(Map<String, dynamic> json) =>
    _DashboardFilter(
      key: json['key'] as String,
      value: json['value'] as String,
      operator: json['operator'] as String? ?? '=',
      label: json['label'] as String?,
    );

Map<String, dynamic> _$DashboardFilterToJson(_DashboardFilter instance) =>
    <String, dynamic>{
      'key': instance.key,
      'value': instance.value,
      'operator': instance.operator,
      'label': instance.label,
    };

_DashboardMetadata _$DashboardMetadataFromJson(Map<String, dynamic> json) =>
    _DashboardMetadata(
      createdAt: json['created_at'] as String?,
      updatedAt: json['updated_at'] as String?,
      createdBy: json['created_by'] as String?,
      version: (json['version'] as num?)?.toInt() ?? 1,
      tags:
          (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList() ??
          const [],
      starred: json['starred'] as bool? ?? false,
      folder: json['folder'] as String?,
    );

Map<String, dynamic> _$DashboardMetadataToJson(_DashboardMetadata instance) =>
    <String, dynamic>{
      'created_at': instance.createdAt,
      'updated_at': instance.updatedAt,
      'created_by': instance.createdBy,
      'version': instance.version,
      'tags': instance.tags,
      'starred': instance.starred,
      'folder': instance.folder,
    };

_Dashboard _$DashboardFromJson(Map<String, dynamic> json) => _Dashboard(
  id: json['id'] as String,
  name: json['name'] as String?,
  displayName: json['display_name'] as String,
  description: json['description'] as String? ?? '',
  source:
      $enumDecodeNullable(_$DashboardSourceEnumMap, json['source']) ??
      DashboardSource.local,
  projectId: json['project_id'] as String?,
  panels:
      (json['panels'] as List<dynamic>?)
          ?.map((e) => DashboardPanel.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const [],
  variables:
      (json['variables'] as List<dynamic>?)
          ?.map((e) => DashboardVariable.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const [],
  filters:
      (json['filters'] as List<dynamic>?)
          ?.map((e) => DashboardFilter.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const [],
  timeRange: json['time_range'] == null
      ? const TimeRange()
      : TimeRange.fromJson(json['time_range'] as Map<String, dynamic>),
  labels:
      (json['labels'] as Map<String, dynamic>?)?.map(
        (k, e) => MapEntry(k, e as String),
      ) ??
      const {},
  gridColumns: (json['grid_columns'] as num?)?.toInt() ?? 24,
  metadata: json['metadata'] == null
      ? const DashboardMetadata()
      : DashboardMetadata.fromJson(json['metadata'] as Map<String, dynamic>),
);

Map<String, dynamic> _$DashboardToJson(_Dashboard instance) =>
    <String, dynamic>{
      'id': instance.id,
      'name': instance.name,
      'display_name': instance.displayName,
      'description': instance.description,
      'source': _$DashboardSourceEnumMap[instance.source]!,
      'project_id': instance.projectId,
      'panels': instance.panels,
      'variables': instance.variables,
      'filters': instance.filters,
      'time_range': instance.timeRange,
      'labels': instance.labels,
      'grid_columns': instance.gridColumns,
      'metadata': instance.metadata,
    };

const _$DashboardSourceEnumMap = {
  DashboardSource.local: 'local',
  DashboardSource.cloudMonitoring: 'cloud_monitoring',
};

_DashboardSummary _$DashboardSummaryFromJson(Map<String, dynamic> json) =>
    _DashboardSummary(
      id: json['id'] as String,
      displayName: json['display_name'] as String,
      description: json['description'] as String? ?? '',
      source:
          $enumDecodeNullable(_$DashboardSourceEnumMap, json['source']) ??
          DashboardSource.local,
      panelCount: (json['panel_count'] as num?)?.toInt() ?? 0,
      metadata: json['metadata'] == null
          ? null
          : DashboardMetadata.fromJson(
              json['metadata'] as Map<String, dynamic>,
            ),
      labels:
          (json['labels'] as Map<String, dynamic>?)?.map(
            (k, e) => MapEntry(k, e as String),
          ) ??
          const {},
    );

Map<String, dynamic> _$DashboardSummaryToJson(_DashboardSummary instance) =>
    <String, dynamic>{
      'id': instance.id,
      'display_name': instance.displayName,
      'description': instance.description,
      'source': _$DashboardSourceEnumMap[instance.source]!,
      'panel_count': instance.panelCount,
      'metadata': instance.metadata,
      'labels': instance.labels,
    };

const _$DatasourceTypeEnumMap = {
  DatasourceType.prometheus: 'prometheus',
  DatasourceType.cloudMonitoring: 'cloud_monitoring',
  DatasourceType.loki: 'loki',
  DatasourceType.bigquery: 'bigquery',
  DatasourceType.tempo: 'tempo',
};
