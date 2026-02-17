// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'models.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;

/// @nodoc
mixin _$LogPattern implements DiagnosticableTreeMixin {

 String get template; int get count;@JsonKey(name: 'severity_counts') Map<String, int> get severityCounts;
/// Create a copy of LogPattern
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$LogPatternCopyWith<LogPattern> get copyWith => _$LogPatternCopyWithImpl<LogPattern>(this as LogPattern, _$identity);

  /// Serializes this LogPattern to a JSON map.
  Map<String, dynamic> toJson();

@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'LogPattern'))
    ..add(DiagnosticsProperty('template', template))..add(DiagnosticsProperty('count', count))..add(DiagnosticsProperty('severityCounts', severityCounts));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is LogPattern&&(identical(other.template, template) || other.template == template)&&(identical(other.count, count) || other.count == count)&&const DeepCollectionEquality().equals(other.severityCounts, severityCounts));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,template,count,const DeepCollectionEquality().hash(severityCounts));

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'LogPattern(template: $template, count: $count, severityCounts: $severityCounts)';
}


}

/// @nodoc
abstract mixin class $LogPatternCopyWith<$Res>  {
  factory $LogPatternCopyWith(LogPattern value, $Res Function(LogPattern) _then) = _$LogPatternCopyWithImpl;
@useResult
$Res call({
 String template, int count,@JsonKey(name: 'severity_counts') Map<String, int> severityCounts
});




}
/// @nodoc
class _$LogPatternCopyWithImpl<$Res>
    implements $LogPatternCopyWith<$Res> {
  _$LogPatternCopyWithImpl(this._self, this._then);

  final LogPattern _self;
  final $Res Function(LogPattern) _then;

/// Create a copy of LogPattern
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? template = null,Object? count = null,Object? severityCounts = null,}) {
  return _then(_self.copyWith(
template: null == template ? _self.template : template // ignore: cast_nullable_to_non_nullable
as String,count: null == count ? _self.count : count // ignore: cast_nullable_to_non_nullable
as int,severityCounts: null == severityCounts ? _self.severityCounts : severityCounts // ignore: cast_nullable_to_non_nullable
as Map<String, int>,
  ));
}

}


/// Adds pattern-matching-related methods to [LogPattern].
extension LogPatternPatterns on LogPattern {
/// A variant of `map` that fallback to returning `orElse`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _LogPattern value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _LogPattern() when $default != null:
return $default(_that);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// Callbacks receives the raw object, upcasted.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case final Subclass2 value:
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _LogPattern value)  $default,){
final _that = this;
switch (_that) {
case _LogPattern():
return $default(_that);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `map` that fallback to returning `null`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _LogPattern value)?  $default,){
final _that = this;
switch (_that) {
case _LogPattern() when $default != null:
return $default(_that);case _:
  return null;

}
}
/// A variant of `when` that fallback to an `orElse` callback.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String template,  int count, @JsonKey(name: 'severity_counts')  Map<String, int> severityCounts)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _LogPattern() when $default != null:
return $default(_that.template,_that.count,_that.severityCounts);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// As opposed to `map`, this offers destructuring.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case Subclass2(:final field2):
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String template,  int count, @JsonKey(name: 'severity_counts')  Map<String, int> severityCounts)  $default,) {final _that = this;
switch (_that) {
case _LogPattern():
return $default(_that.template,_that.count,_that.severityCounts);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `when` that fallback to returning `null`
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String template,  int count, @JsonKey(name: 'severity_counts')  Map<String, int> severityCounts)?  $default,) {final _that = this;
switch (_that) {
case _LogPattern() when $default != null:
return $default(_that.template,_that.count,_that.severityCounts);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _LogPattern with DiagnosticableTreeMixin implements LogPattern {
  const _LogPattern({this.template = '', this.count = 0, @JsonKey(name: 'severity_counts') final  Map<String, int> severityCounts = const {}}): _severityCounts = severityCounts;
  factory _LogPattern.fromJson(Map<String, dynamic> json) => _$LogPatternFromJson(json);

@override@JsonKey() final  String template;
@override@JsonKey() final  int count;
 final  Map<String, int> _severityCounts;
@override@JsonKey(name: 'severity_counts') Map<String, int> get severityCounts {
  if (_severityCounts is EqualUnmodifiableMapView) return _severityCounts;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableMapView(_severityCounts);
}


/// Create a copy of LogPattern
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$LogPatternCopyWith<_LogPattern> get copyWith => __$LogPatternCopyWithImpl<_LogPattern>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$LogPatternToJson(this, );
}
@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'LogPattern'))
    ..add(DiagnosticsProperty('template', template))..add(DiagnosticsProperty('count', count))..add(DiagnosticsProperty('severityCounts', severityCounts));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _LogPattern&&(identical(other.template, template) || other.template == template)&&(identical(other.count, count) || other.count == count)&&const DeepCollectionEquality().equals(other._severityCounts, _severityCounts));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,template,count,const DeepCollectionEquality().hash(_severityCounts));

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'LogPattern(template: $template, count: $count, severityCounts: $severityCounts)';
}


}

/// @nodoc
abstract mixin class _$LogPatternCopyWith<$Res> implements $LogPatternCopyWith<$Res> {
  factory _$LogPatternCopyWith(_LogPattern value, $Res Function(_LogPattern) _then) = __$LogPatternCopyWithImpl;
@override @useResult
$Res call({
 String template, int count,@JsonKey(name: 'severity_counts') Map<String, int> severityCounts
});




}
/// @nodoc
class __$LogPatternCopyWithImpl<$Res>
    implements _$LogPatternCopyWith<$Res> {
  __$LogPatternCopyWithImpl(this._self, this._then);

  final _LogPattern _self;
  final $Res Function(_LogPattern) _then;

/// Create a copy of LogPattern
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? template = null,Object? count = null,Object? severityCounts = null,}) {
  return _then(_LogPattern(
template: null == template ? _self.template : template // ignore: cast_nullable_to_non_nullable
as String,count: null == count ? _self.count : count // ignore: cast_nullable_to_non_nullable
as int,severityCounts: null == severityCounts ? _self._severityCounts : severityCounts // ignore: cast_nullable_to_non_nullable
as Map<String, int>,
  ));
}


}

/// @nodoc
mixin _$LogEntry implements DiagnosticableTreeMixin {

@JsonKey(name: 'insert_id') String get insertId; DateTime get timestamp; String get severity;// 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
 dynamic get payload;// Can be String (text) or Map (JSON)
@JsonKey(name: 'resource_labels') Map<String, String> get resourceLabels;@JsonKey(name: 'resource_type') String get resourceType;@JsonKey(name: 'trace_id') String? get traceId;@JsonKey(name: 'span_id') String? get spanId;@JsonKey(name: 'http_request') Map<String, dynamic>? get httpRequest;
/// Create a copy of LogEntry
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$LogEntryCopyWith<LogEntry> get copyWith => _$LogEntryCopyWithImpl<LogEntry>(this as LogEntry, _$identity);


@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'LogEntry'))
    ..add(DiagnosticsProperty('insertId', insertId))..add(DiagnosticsProperty('timestamp', timestamp))..add(DiagnosticsProperty('severity', severity))..add(DiagnosticsProperty('payload', payload))..add(DiagnosticsProperty('resourceLabels', resourceLabels))..add(DiagnosticsProperty('resourceType', resourceType))..add(DiagnosticsProperty('traceId', traceId))..add(DiagnosticsProperty('spanId', spanId))..add(DiagnosticsProperty('httpRequest', httpRequest));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is LogEntry&&(identical(other.insertId, insertId) || other.insertId == insertId)&&(identical(other.timestamp, timestamp) || other.timestamp == timestamp)&&(identical(other.severity, severity) || other.severity == severity)&&const DeepCollectionEquality().equals(other.payload, payload)&&const DeepCollectionEquality().equals(other.resourceLabels, resourceLabels)&&(identical(other.resourceType, resourceType) || other.resourceType == resourceType)&&(identical(other.traceId, traceId) || other.traceId == traceId)&&(identical(other.spanId, spanId) || other.spanId == spanId)&&const DeepCollectionEquality().equals(other.httpRequest, httpRequest));
}


@override
int get hashCode => Object.hash(runtimeType,insertId,timestamp,severity,const DeepCollectionEquality().hash(payload),const DeepCollectionEquality().hash(resourceLabels),resourceType,traceId,spanId,const DeepCollectionEquality().hash(httpRequest));

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'LogEntry(insertId: $insertId, timestamp: $timestamp, severity: $severity, payload: $payload, resourceLabels: $resourceLabels, resourceType: $resourceType, traceId: $traceId, spanId: $spanId, httpRequest: $httpRequest)';
}


}

/// @nodoc
abstract mixin class $LogEntryCopyWith<$Res>  {
  factory $LogEntryCopyWith(LogEntry value, $Res Function(LogEntry) _then) = _$LogEntryCopyWithImpl;
@useResult
$Res call({
@JsonKey(name: 'insert_id') String insertId, DateTime timestamp, String severity, dynamic payload,@JsonKey(name: 'resource_labels') Map<String, String> resourceLabels,@JsonKey(name: 'resource_type') String resourceType,@JsonKey(name: 'trace_id') String? traceId,@JsonKey(name: 'span_id') String? spanId,@JsonKey(name: 'http_request') Map<String, dynamic>? httpRequest
});




}
/// @nodoc
class _$LogEntryCopyWithImpl<$Res>
    implements $LogEntryCopyWith<$Res> {
  _$LogEntryCopyWithImpl(this._self, this._then);

  final LogEntry _self;
  final $Res Function(LogEntry) _then;

/// Create a copy of LogEntry
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? insertId = null,Object? timestamp = null,Object? severity = null,Object? payload = freezed,Object? resourceLabels = null,Object? resourceType = null,Object? traceId = freezed,Object? spanId = freezed,Object? httpRequest = freezed,}) {
  return _then(_self.copyWith(
insertId: null == insertId ? _self.insertId : insertId // ignore: cast_nullable_to_non_nullable
as String,timestamp: null == timestamp ? _self.timestamp : timestamp // ignore: cast_nullable_to_non_nullable
as DateTime,severity: null == severity ? _self.severity : severity // ignore: cast_nullable_to_non_nullable
as String,payload: freezed == payload ? _self.payload : payload // ignore: cast_nullable_to_non_nullable
as dynamic,resourceLabels: null == resourceLabels ? _self.resourceLabels : resourceLabels // ignore: cast_nullable_to_non_nullable
as Map<String, String>,resourceType: null == resourceType ? _self.resourceType : resourceType // ignore: cast_nullable_to_non_nullable
as String,traceId: freezed == traceId ? _self.traceId : traceId // ignore: cast_nullable_to_non_nullable
as String?,spanId: freezed == spanId ? _self.spanId : spanId // ignore: cast_nullable_to_non_nullable
as String?,httpRequest: freezed == httpRequest ? _self.httpRequest : httpRequest // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>?,
  ));
}

}


/// Adds pattern-matching-related methods to [LogEntry].
extension LogEntryPatterns on LogEntry {
/// A variant of `map` that fallback to returning `orElse`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _LogEntry value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _LogEntry() when $default != null:
return $default(_that);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// Callbacks receives the raw object, upcasted.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case final Subclass2 value:
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _LogEntry value)  $default,){
final _that = this;
switch (_that) {
case _LogEntry():
return $default(_that);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `map` that fallback to returning `null`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _LogEntry value)?  $default,){
final _that = this;
switch (_that) {
case _LogEntry() when $default != null:
return $default(_that);case _:
  return null;

}
}
/// A variant of `when` that fallback to an `orElse` callback.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function(@JsonKey(name: 'insert_id')  String insertId,  DateTime timestamp,  String severity,  dynamic payload, @JsonKey(name: 'resource_labels')  Map<String, String> resourceLabels, @JsonKey(name: 'resource_type')  String resourceType, @JsonKey(name: 'trace_id')  String? traceId, @JsonKey(name: 'span_id')  String? spanId, @JsonKey(name: 'http_request')  Map<String, dynamic>? httpRequest)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _LogEntry() when $default != null:
return $default(_that.insertId,_that.timestamp,_that.severity,_that.payload,_that.resourceLabels,_that.resourceType,_that.traceId,_that.spanId,_that.httpRequest);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// As opposed to `map`, this offers destructuring.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case Subclass2(:final field2):
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function(@JsonKey(name: 'insert_id')  String insertId,  DateTime timestamp,  String severity,  dynamic payload, @JsonKey(name: 'resource_labels')  Map<String, String> resourceLabels, @JsonKey(name: 'resource_type')  String resourceType, @JsonKey(name: 'trace_id')  String? traceId, @JsonKey(name: 'span_id')  String? spanId, @JsonKey(name: 'http_request')  Map<String, dynamic>? httpRequest)  $default,) {final _that = this;
switch (_that) {
case _LogEntry():
return $default(_that.insertId,_that.timestamp,_that.severity,_that.payload,_that.resourceLabels,_that.resourceType,_that.traceId,_that.spanId,_that.httpRequest);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `when` that fallback to returning `null`
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function(@JsonKey(name: 'insert_id')  String insertId,  DateTime timestamp,  String severity,  dynamic payload, @JsonKey(name: 'resource_labels')  Map<String, String> resourceLabels, @JsonKey(name: 'resource_type')  String resourceType, @JsonKey(name: 'trace_id')  String? traceId, @JsonKey(name: 'span_id')  String? spanId, @JsonKey(name: 'http_request')  Map<String, dynamic>? httpRequest)?  $default,) {final _that = this;
switch (_that) {
case _LogEntry() when $default != null:
return $default(_that.insertId,_that.timestamp,_that.severity,_that.payload,_that.resourceLabels,_that.resourceType,_that.traceId,_that.spanId,_that.httpRequest);case _:
  return null;

}
}

}

/// @nodoc


class _LogEntry extends LogEntry with DiagnosticableTreeMixin {
  const _LogEntry({@JsonKey(name: 'insert_id') required this.insertId, required this.timestamp, this.severity = 'INFO', required this.payload, @JsonKey(name: 'resource_labels') final  Map<String, String> resourceLabels = const {}, @JsonKey(name: 'resource_type') this.resourceType = 'unknown', @JsonKey(name: 'trace_id') this.traceId, @JsonKey(name: 'span_id') this.spanId, @JsonKey(name: 'http_request') final  Map<String, dynamic>? httpRequest}): _resourceLabels = resourceLabels,_httpRequest = httpRequest,super._();


@override@JsonKey(name: 'insert_id') final  String insertId;
@override final  DateTime timestamp;
@override@JsonKey() final  String severity;
// 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
@override final  dynamic payload;
// Can be String (text) or Map (JSON)
 final  Map<String, String> _resourceLabels;
// Can be String (text) or Map (JSON)
@override@JsonKey(name: 'resource_labels') Map<String, String> get resourceLabels {
  if (_resourceLabels is EqualUnmodifiableMapView) return _resourceLabels;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableMapView(_resourceLabels);
}

@override@JsonKey(name: 'resource_type') final  String resourceType;
@override@JsonKey(name: 'trace_id') final  String? traceId;
@override@JsonKey(name: 'span_id') final  String? spanId;
 final  Map<String, dynamic>? _httpRequest;
@override@JsonKey(name: 'http_request') Map<String, dynamic>? get httpRequest {
  final value = _httpRequest;
  if (value == null) return null;
  if (_httpRequest is EqualUnmodifiableMapView) return _httpRequest;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableMapView(value);
}


/// Create a copy of LogEntry
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$LogEntryCopyWith<_LogEntry> get copyWith => __$LogEntryCopyWithImpl<_LogEntry>(this, _$identity);


@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'LogEntry'))
    ..add(DiagnosticsProperty('insertId', insertId))..add(DiagnosticsProperty('timestamp', timestamp))..add(DiagnosticsProperty('severity', severity))..add(DiagnosticsProperty('payload', payload))..add(DiagnosticsProperty('resourceLabels', resourceLabels))..add(DiagnosticsProperty('resourceType', resourceType))..add(DiagnosticsProperty('traceId', traceId))..add(DiagnosticsProperty('spanId', spanId))..add(DiagnosticsProperty('httpRequest', httpRequest));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _LogEntry&&(identical(other.insertId, insertId) || other.insertId == insertId)&&(identical(other.timestamp, timestamp) || other.timestamp == timestamp)&&(identical(other.severity, severity) || other.severity == severity)&&const DeepCollectionEquality().equals(other.payload, payload)&&const DeepCollectionEquality().equals(other._resourceLabels, _resourceLabels)&&(identical(other.resourceType, resourceType) || other.resourceType == resourceType)&&(identical(other.traceId, traceId) || other.traceId == traceId)&&(identical(other.spanId, spanId) || other.spanId == spanId)&&const DeepCollectionEquality().equals(other._httpRequest, _httpRequest));
}


@override
int get hashCode => Object.hash(runtimeType,insertId,timestamp,severity,const DeepCollectionEquality().hash(payload),const DeepCollectionEquality().hash(_resourceLabels),resourceType,traceId,spanId,const DeepCollectionEquality().hash(_httpRequest));

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'LogEntry(insertId: $insertId, timestamp: $timestamp, severity: $severity, payload: $payload, resourceLabels: $resourceLabels, resourceType: $resourceType, traceId: $traceId, spanId: $spanId, httpRequest: $httpRequest)';
}


}

/// @nodoc
abstract mixin class _$LogEntryCopyWith<$Res> implements $LogEntryCopyWith<$Res> {
  factory _$LogEntryCopyWith(_LogEntry value, $Res Function(_LogEntry) _then) = __$LogEntryCopyWithImpl;
@override @useResult
$Res call({
@JsonKey(name: 'insert_id') String insertId, DateTime timestamp, String severity, dynamic payload,@JsonKey(name: 'resource_labels') Map<String, String> resourceLabels,@JsonKey(name: 'resource_type') String resourceType,@JsonKey(name: 'trace_id') String? traceId,@JsonKey(name: 'span_id') String? spanId,@JsonKey(name: 'http_request') Map<String, dynamic>? httpRequest
});




}
/// @nodoc
class __$LogEntryCopyWithImpl<$Res>
    implements _$LogEntryCopyWith<$Res> {
  __$LogEntryCopyWithImpl(this._self, this._then);

  final _LogEntry _self;
  final $Res Function(_LogEntry) _then;

/// Create a copy of LogEntry
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? insertId = null,Object? timestamp = null,Object? severity = null,Object? payload = freezed,Object? resourceLabels = null,Object? resourceType = null,Object? traceId = freezed,Object? spanId = freezed,Object? httpRequest = freezed,}) {
  return _then(_LogEntry(
insertId: null == insertId ? _self.insertId : insertId // ignore: cast_nullable_to_non_nullable
as String,timestamp: null == timestamp ? _self.timestamp : timestamp // ignore: cast_nullable_to_non_nullable
as DateTime,severity: null == severity ? _self.severity : severity // ignore: cast_nullable_to_non_nullable
as String,payload: freezed == payload ? _self.payload : payload // ignore: cast_nullable_to_non_nullable
as dynamic,resourceLabels: null == resourceLabels ? _self._resourceLabels : resourceLabels // ignore: cast_nullable_to_non_nullable
as Map<String, String>,resourceType: null == resourceType ? _self.resourceType : resourceType // ignore: cast_nullable_to_non_nullable
as String,traceId: freezed == traceId ? _self.traceId : traceId // ignore: cast_nullable_to_non_nullable
as String?,spanId: freezed == spanId ? _self.spanId : spanId // ignore: cast_nullable_to_non_nullable
as String?,httpRequest: freezed == httpRequest ? _self._httpRequest : httpRequest // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>?,
  ));
}


}

/// @nodoc
mixin _$LogEntriesData implements DiagnosticableTreeMixin {

 List<LogEntry> get entries; String? get filter;@JsonKey(name: 'project_id') String? get projectId;@JsonKey(name: 'next_page_token') String? get nextPageToken; int? get limit;
/// Create a copy of LogEntriesData
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$LogEntriesDataCopyWith<LogEntriesData> get copyWith => _$LogEntriesDataCopyWithImpl<LogEntriesData>(this as LogEntriesData, _$identity);


@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'LogEntriesData'))
    ..add(DiagnosticsProperty('entries', entries))..add(DiagnosticsProperty('filter', filter))..add(DiagnosticsProperty('projectId', projectId))..add(DiagnosticsProperty('nextPageToken', nextPageToken))..add(DiagnosticsProperty('limit', limit));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is LogEntriesData&&const DeepCollectionEquality().equals(other.entries, entries)&&(identical(other.filter, filter) || other.filter == filter)&&(identical(other.projectId, projectId) || other.projectId == projectId)&&(identical(other.nextPageToken, nextPageToken) || other.nextPageToken == nextPageToken)&&(identical(other.limit, limit) || other.limit == limit));
}


@override
int get hashCode => Object.hash(runtimeType,const DeepCollectionEquality().hash(entries),filter,projectId,nextPageToken,limit);

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'LogEntriesData(entries: $entries, filter: $filter, projectId: $projectId, nextPageToken: $nextPageToken, limit: $limit)';
}


}

/// @nodoc
abstract mixin class $LogEntriesDataCopyWith<$Res>  {
  factory $LogEntriesDataCopyWith(LogEntriesData value, $Res Function(LogEntriesData) _then) = _$LogEntriesDataCopyWithImpl;
@useResult
$Res call({
 List<LogEntry> entries, String? filter,@JsonKey(name: 'project_id') String? projectId,@JsonKey(name: 'next_page_token') String? nextPageToken, int? limit
});




}
/// @nodoc
class _$LogEntriesDataCopyWithImpl<$Res>
    implements $LogEntriesDataCopyWith<$Res> {
  _$LogEntriesDataCopyWithImpl(this._self, this._then);

  final LogEntriesData _self;
  final $Res Function(LogEntriesData) _then;

/// Create a copy of LogEntriesData
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? entries = null,Object? filter = freezed,Object? projectId = freezed,Object? nextPageToken = freezed,Object? limit = freezed,}) {
  return _then(_self.copyWith(
entries: null == entries ? _self.entries : entries // ignore: cast_nullable_to_non_nullable
as List<LogEntry>,filter: freezed == filter ? _self.filter : filter // ignore: cast_nullable_to_non_nullable
as String?,projectId: freezed == projectId ? _self.projectId : projectId // ignore: cast_nullable_to_non_nullable
as String?,nextPageToken: freezed == nextPageToken ? _self.nextPageToken : nextPageToken // ignore: cast_nullable_to_non_nullable
as String?,limit: freezed == limit ? _self.limit : limit // ignore: cast_nullable_to_non_nullable
as int?,
  ));
}

}


/// Adds pattern-matching-related methods to [LogEntriesData].
extension LogEntriesDataPatterns on LogEntriesData {
/// A variant of `map` that fallback to returning `orElse`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _LogEntriesData value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _LogEntriesData() when $default != null:
return $default(_that);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// Callbacks receives the raw object, upcasted.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case final Subclass2 value:
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _LogEntriesData value)  $default,){
final _that = this;
switch (_that) {
case _LogEntriesData():
return $default(_that);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `map` that fallback to returning `null`.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case final Subclass value:
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _LogEntriesData value)?  $default,){
final _that = this;
switch (_that) {
case _LogEntriesData() when $default != null:
return $default(_that);case _:
  return null;

}
}
/// A variant of `when` that fallback to an `orElse` callback.
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return orElse();
/// }
/// ```

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( List<LogEntry> entries,  String? filter, @JsonKey(name: 'project_id')  String? projectId, @JsonKey(name: 'next_page_token')  String? nextPageToken,  int? limit)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _LogEntriesData() when $default != null:
return $default(_that.entries,_that.filter,_that.projectId,_that.nextPageToken,_that.limit);case _:
  return orElse();

}
}
/// A `switch`-like method, using callbacks.
///
/// As opposed to `map`, this offers destructuring.
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case Subclass2(:final field2):
///     return ...;
/// }
/// ```

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( List<LogEntry> entries,  String? filter, @JsonKey(name: 'project_id')  String? projectId, @JsonKey(name: 'next_page_token')  String? nextPageToken,  int? limit)  $default,) {final _that = this;
switch (_that) {
case _LogEntriesData():
return $default(_that.entries,_that.filter,_that.projectId,_that.nextPageToken,_that.limit);case _:
  throw StateError('Unexpected subclass');

}
}
/// A variant of `when` that fallback to returning `null`
///
/// It is equivalent to doing:
/// ```dart
/// switch (sealedClass) {
///   case Subclass(:final field):
///     return ...;
///   case _:
///     return null;
/// }
/// ```

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( List<LogEntry> entries,  String? filter, @JsonKey(name: 'project_id')  String? projectId, @JsonKey(name: 'next_page_token')  String? nextPageToken,  int? limit)?  $default,) {final _that = this;
switch (_that) {
case _LogEntriesData() when $default != null:
return $default(_that.entries,_that.filter,_that.projectId,_that.nextPageToken,_that.limit);case _:
  return null;

}
}

}

/// @nodoc


class _LogEntriesData extends LogEntriesData with DiagnosticableTreeMixin {
  const _LogEntriesData({required final  List<LogEntry> entries, this.filter, @JsonKey(name: 'project_id') this.projectId, @JsonKey(name: 'next_page_token') this.nextPageToken, this.limit}): _entries = entries,super._();


 final  List<LogEntry> _entries;
@override List<LogEntry> get entries {
  if (_entries is EqualUnmodifiableListView) return _entries;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_entries);
}

@override final  String? filter;
@override@JsonKey(name: 'project_id') final  String? projectId;
@override@JsonKey(name: 'next_page_token') final  String? nextPageToken;
@override final  int? limit;

/// Create a copy of LogEntriesData
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$LogEntriesDataCopyWith<_LogEntriesData> get copyWith => __$LogEntriesDataCopyWithImpl<_LogEntriesData>(this, _$identity);


@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'LogEntriesData'))
    ..add(DiagnosticsProperty('entries', entries))..add(DiagnosticsProperty('filter', filter))..add(DiagnosticsProperty('projectId', projectId))..add(DiagnosticsProperty('nextPageToken', nextPageToken))..add(DiagnosticsProperty('limit', limit));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _LogEntriesData&&const DeepCollectionEquality().equals(other._entries, _entries)&&(identical(other.filter, filter) || other.filter == filter)&&(identical(other.projectId, projectId) || other.projectId == projectId)&&(identical(other.nextPageToken, nextPageToken) || other.nextPageToken == nextPageToken)&&(identical(other.limit, limit) || other.limit == limit));
}


@override
int get hashCode => Object.hash(runtimeType,const DeepCollectionEquality().hash(_entries),filter,projectId,nextPageToken,limit);

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'LogEntriesData(entries: $entries, filter: $filter, projectId: $projectId, nextPageToken: $nextPageToken, limit: $limit)';
}


}

/// @nodoc
abstract mixin class _$LogEntriesDataCopyWith<$Res> implements $LogEntriesDataCopyWith<$Res> {
  factory _$LogEntriesDataCopyWith(_LogEntriesData value, $Res Function(_LogEntriesData) _then) = __$LogEntriesDataCopyWithImpl;
@override @useResult
$Res call({
 List<LogEntry> entries, String? filter,@JsonKey(name: 'project_id') String? projectId,@JsonKey(name: 'next_page_token') String? nextPageToken, int? limit
});




}
/// @nodoc
class __$LogEntriesDataCopyWithImpl<$Res>
    implements _$LogEntriesDataCopyWith<$Res> {
  __$LogEntriesDataCopyWithImpl(this._self, this._then);

  final _LogEntriesData _self;
  final $Res Function(_LogEntriesData) _then;

/// Create a copy of LogEntriesData
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? entries = null,Object? filter = freezed,Object? projectId = freezed,Object? nextPageToken = freezed,Object? limit = freezed,}) {
  return _then(_LogEntriesData(
entries: null == entries ? _self._entries : entries // ignore: cast_nullable_to_non_nullable
as List<LogEntry>,filter: freezed == filter ? _self.filter : filter // ignore: cast_nullable_to_non_nullable
as String?,projectId: freezed == projectId ? _self.projectId : projectId // ignore: cast_nullable_to_non_nullable
as String?,nextPageToken: freezed == nextPageToken ? _self.nextPageToken : nextPageToken // ignore: cast_nullable_to_non_nullable
as String?,limit: freezed == limit ? _self.limit : limit // ignore: cast_nullable_to_non_nullable
as int?,
  ));
}


}

// dart format on
