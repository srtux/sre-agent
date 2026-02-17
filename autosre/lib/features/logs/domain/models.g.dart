// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'models.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_LogPattern _$LogPatternFromJson(Map<String, dynamic> json) => _LogPattern(
  template: json['template'] as String? ?? '',
  count: (json['count'] as num?)?.toInt() ?? 0,
  severityCounts:
      (json['severity_counts'] as Map<String, dynamic>?)?.map(
        (k, e) => MapEntry(k, (e as num).toInt()),
      ) ??
      const {},
);

Map<String, dynamic> _$LogPatternToJson(_LogPattern instance) =>
    <String, dynamic>{
      'template': instance.template,
      'count': instance.count,
      'severity_counts': instance.severityCounts,
    };
