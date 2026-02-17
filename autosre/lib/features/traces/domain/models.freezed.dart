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
mixin _$SpanInfo implements DiagnosticableTreeMixin {

@JsonKey(name: 'span_id') String get spanId;@JsonKey(name: 'trace_id') String get traceId; String get name;@JsonKey(name: 'start_time') DateTime get startTime;@JsonKey(name: 'end_time') DateTime get endTime; Map<String, dynamic> get attributes; String get status;// 'OK', 'ERROR'
@JsonKey(name: 'parent_span_id') String? get parentSpanId;
/// Create a copy of SpanInfo
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$SpanInfoCopyWith<SpanInfo> get copyWith => _$SpanInfoCopyWithImpl<SpanInfo>(this as SpanInfo, _$identity);

  /// Serializes this SpanInfo to a JSON map.
  Map<String, dynamic> toJson();

@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'SpanInfo'))
    ..add(DiagnosticsProperty('spanId', spanId))..add(DiagnosticsProperty('traceId', traceId))..add(DiagnosticsProperty('name', name))..add(DiagnosticsProperty('startTime', startTime))..add(DiagnosticsProperty('endTime', endTime))..add(DiagnosticsProperty('attributes', attributes))..add(DiagnosticsProperty('status', status))..add(DiagnosticsProperty('parentSpanId', parentSpanId));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is SpanInfo&&(identical(other.spanId, spanId) || other.spanId == spanId)&&(identical(other.traceId, traceId) || other.traceId == traceId)&&(identical(other.name, name) || other.name == name)&&(identical(other.startTime, startTime) || other.startTime == startTime)&&(identical(other.endTime, endTime) || other.endTime == endTime)&&const DeepCollectionEquality().equals(other.attributes, attributes)&&(identical(other.status, status) || other.status == status)&&(identical(other.parentSpanId, parentSpanId) || other.parentSpanId == parentSpanId));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,spanId,traceId,name,startTime,endTime,const DeepCollectionEquality().hash(attributes),status,parentSpanId);

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'SpanInfo(spanId: $spanId, traceId: $traceId, name: $name, startTime: $startTime, endTime: $endTime, attributes: $attributes, status: $status, parentSpanId: $parentSpanId)';
}


}

/// @nodoc
abstract mixin class $SpanInfoCopyWith<$Res>  {
  factory $SpanInfoCopyWith(SpanInfo value, $Res Function(SpanInfo) _then) = _$SpanInfoCopyWithImpl;
@useResult
$Res call({
@JsonKey(name: 'span_id') String spanId,@JsonKey(name: 'trace_id') String traceId, String name,@JsonKey(name: 'start_time') DateTime startTime,@JsonKey(name: 'end_time') DateTime endTime, Map<String, dynamic> attributes, String status,@JsonKey(name: 'parent_span_id') String? parentSpanId
});




}
/// @nodoc
class _$SpanInfoCopyWithImpl<$Res>
    implements $SpanInfoCopyWith<$Res> {
  _$SpanInfoCopyWithImpl(this._self, this._then);

  final SpanInfo _self;
  final $Res Function(SpanInfo) _then;

/// Create a copy of SpanInfo
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? spanId = null,Object? traceId = null,Object? name = null,Object? startTime = null,Object? endTime = null,Object? attributes = null,Object? status = null,Object? parentSpanId = freezed,}) {
  return _then(_self.copyWith(
spanId: null == spanId ? _self.spanId : spanId // ignore: cast_nullable_to_non_nullable
as String,traceId: null == traceId ? _self.traceId : traceId // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,startTime: null == startTime ? _self.startTime : startTime // ignore: cast_nullable_to_non_nullable
as DateTime,endTime: null == endTime ? _self.endTime : endTime // ignore: cast_nullable_to_non_nullable
as DateTime,attributes: null == attributes ? _self.attributes : attributes // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as String,parentSpanId: freezed == parentSpanId ? _self.parentSpanId : parentSpanId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

}


/// Adds pattern-matching-related methods to [SpanInfo].
extension SpanInfoPatterns on SpanInfo {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _SpanInfo value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _SpanInfo() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _SpanInfo value)  $default,){
final _that = this;
switch (_that) {
case _SpanInfo():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _SpanInfo value)?  $default,){
final _that = this;
switch (_that) {
case _SpanInfo() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function(@JsonKey(name: 'span_id')  String spanId, @JsonKey(name: 'trace_id')  String traceId,  String name, @JsonKey(name: 'start_time')  DateTime startTime, @JsonKey(name: 'end_time')  DateTime endTime,  Map<String, dynamic> attributes,  String status, @JsonKey(name: 'parent_span_id')  String? parentSpanId)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _SpanInfo() when $default != null:
return $default(_that.spanId,_that.traceId,_that.name,_that.startTime,_that.endTime,_that.attributes,_that.status,_that.parentSpanId);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function(@JsonKey(name: 'span_id')  String spanId, @JsonKey(name: 'trace_id')  String traceId,  String name, @JsonKey(name: 'start_time')  DateTime startTime, @JsonKey(name: 'end_time')  DateTime endTime,  Map<String, dynamic> attributes,  String status, @JsonKey(name: 'parent_span_id')  String? parentSpanId)  $default,) {final _that = this;
switch (_that) {
case _SpanInfo():
return $default(_that.spanId,_that.traceId,_that.name,_that.startTime,_that.endTime,_that.attributes,_that.status,_that.parentSpanId);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function(@JsonKey(name: 'span_id')  String spanId, @JsonKey(name: 'trace_id')  String traceId,  String name, @JsonKey(name: 'start_time')  DateTime startTime, @JsonKey(name: 'end_time')  DateTime endTime,  Map<String, dynamic> attributes,  String status, @JsonKey(name: 'parent_span_id')  String? parentSpanId)?  $default,) {final _that = this;
switch (_that) {
case _SpanInfo() when $default != null:
return $default(_that.spanId,_that.traceId,_that.name,_that.startTime,_that.endTime,_that.attributes,_that.status,_that.parentSpanId);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _SpanInfo extends SpanInfo with DiagnosticableTreeMixin {
  const _SpanInfo({@JsonKey(name: 'span_id') required this.spanId, @JsonKey(name: 'trace_id') required this.traceId, required this.name, @JsonKey(name: 'start_time') required this.startTime, @JsonKey(name: 'end_time') required this.endTime, final  Map<String, dynamic> attributes = const {}, this.status = 'OK', @JsonKey(name: 'parent_span_id') this.parentSpanId}): _attributes = attributes,super._();
  factory _SpanInfo.fromJson(Map<String, dynamic> json) => _$SpanInfoFromJson(json);

@override@JsonKey(name: 'span_id') final  String spanId;
@override@JsonKey(name: 'trace_id') final  String traceId;
@override final  String name;
@override@JsonKey(name: 'start_time') final  DateTime startTime;
@override@JsonKey(name: 'end_time') final  DateTime endTime;
 final  Map<String, dynamic> _attributes;
@override@JsonKey() Map<String, dynamic> get attributes {
  if (_attributes is EqualUnmodifiableMapView) return _attributes;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableMapView(_attributes);
}

@override@JsonKey() final  String status;
// 'OK', 'ERROR'
@override@JsonKey(name: 'parent_span_id') final  String? parentSpanId;

/// Create a copy of SpanInfo
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$SpanInfoCopyWith<_SpanInfo> get copyWith => __$SpanInfoCopyWithImpl<_SpanInfo>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$SpanInfoToJson(this, );
}
@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'SpanInfo'))
    ..add(DiagnosticsProperty('spanId', spanId))..add(DiagnosticsProperty('traceId', traceId))..add(DiagnosticsProperty('name', name))..add(DiagnosticsProperty('startTime', startTime))..add(DiagnosticsProperty('endTime', endTime))..add(DiagnosticsProperty('attributes', attributes))..add(DiagnosticsProperty('status', status))..add(DiagnosticsProperty('parentSpanId', parentSpanId));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _SpanInfo&&(identical(other.spanId, spanId) || other.spanId == spanId)&&(identical(other.traceId, traceId) || other.traceId == traceId)&&(identical(other.name, name) || other.name == name)&&(identical(other.startTime, startTime) || other.startTime == startTime)&&(identical(other.endTime, endTime) || other.endTime == endTime)&&const DeepCollectionEquality().equals(other._attributes, _attributes)&&(identical(other.status, status) || other.status == status)&&(identical(other.parentSpanId, parentSpanId) || other.parentSpanId == parentSpanId));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,spanId,traceId,name,startTime,endTime,const DeepCollectionEquality().hash(_attributes),status,parentSpanId);

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'SpanInfo(spanId: $spanId, traceId: $traceId, name: $name, startTime: $startTime, endTime: $endTime, attributes: $attributes, status: $status, parentSpanId: $parentSpanId)';
}


}

/// @nodoc
abstract mixin class _$SpanInfoCopyWith<$Res> implements $SpanInfoCopyWith<$Res> {
  factory _$SpanInfoCopyWith(_SpanInfo value, $Res Function(_SpanInfo) _then) = __$SpanInfoCopyWithImpl;
@override @useResult
$Res call({
@JsonKey(name: 'span_id') String spanId,@JsonKey(name: 'trace_id') String traceId, String name,@JsonKey(name: 'start_time') DateTime startTime,@JsonKey(name: 'end_time') DateTime endTime, Map<String, dynamic> attributes, String status,@JsonKey(name: 'parent_span_id') String? parentSpanId
});




}
/// @nodoc
class __$SpanInfoCopyWithImpl<$Res>
    implements _$SpanInfoCopyWith<$Res> {
  __$SpanInfoCopyWithImpl(this._self, this._then);

  final _SpanInfo _self;
  final $Res Function(_SpanInfo) _then;

/// Create a copy of SpanInfo
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? spanId = null,Object? traceId = null,Object? name = null,Object? startTime = null,Object? endTime = null,Object? attributes = null,Object? status = null,Object? parentSpanId = freezed,}) {
  return _then(_SpanInfo(
spanId: null == spanId ? _self.spanId : spanId // ignore: cast_nullable_to_non_nullable
as String,traceId: null == traceId ? _self.traceId : traceId // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,startTime: null == startTime ? _self.startTime : startTime // ignore: cast_nullable_to_non_nullable
as DateTime,endTime: null == endTime ? _self.endTime : endTime // ignore: cast_nullable_to_non_nullable
as DateTime,attributes: null == attributes ? _self._attributes : attributes // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as String,parentSpanId: freezed == parentSpanId ? _self.parentSpanId : parentSpanId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}


}


/// @nodoc
mixin _$Trace implements DiagnosticableTreeMixin {

@JsonKey(name: 'trace_id') String get traceId; List<SpanInfo> get spans;
/// Create a copy of Trace
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$TraceCopyWith<Trace> get copyWith => _$TraceCopyWithImpl<Trace>(this as Trace, _$identity);

  /// Serializes this Trace to a JSON map.
  Map<String, dynamic> toJson();

@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'Trace'))
    ..add(DiagnosticsProperty('traceId', traceId))..add(DiagnosticsProperty('spans', spans));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Trace&&(identical(other.traceId, traceId) || other.traceId == traceId)&&const DeepCollectionEquality().equals(other.spans, spans));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,traceId,const DeepCollectionEquality().hash(spans));

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'Trace(traceId: $traceId, spans: $spans)';
}


}

/// @nodoc
abstract mixin class $TraceCopyWith<$Res>  {
  factory $TraceCopyWith(Trace value, $Res Function(Trace) _then) = _$TraceCopyWithImpl;
@useResult
$Res call({
@JsonKey(name: 'trace_id') String traceId, List<SpanInfo> spans
});




}
/// @nodoc
class _$TraceCopyWithImpl<$Res>
    implements $TraceCopyWith<$Res> {
  _$TraceCopyWithImpl(this._self, this._then);

  final Trace _self;
  final $Res Function(Trace) _then;

/// Create a copy of Trace
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? traceId = null,Object? spans = null,}) {
  return _then(_self.copyWith(
traceId: null == traceId ? _self.traceId : traceId // ignore: cast_nullable_to_non_nullable
as String,spans: null == spans ? _self.spans : spans // ignore: cast_nullable_to_non_nullable
as List<SpanInfo>,
  ));
}

}


/// Adds pattern-matching-related methods to [Trace].
extension TracePatterns on Trace {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Trace value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Trace() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Trace value)  $default,){
final _that = this;
switch (_that) {
case _Trace():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Trace value)?  $default,){
final _that = this;
switch (_that) {
case _Trace() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function(@JsonKey(name: 'trace_id')  String traceId,  List<SpanInfo> spans)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Trace() when $default != null:
return $default(_that.traceId,_that.spans);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function(@JsonKey(name: 'trace_id')  String traceId,  List<SpanInfo> spans)  $default,) {final _that = this;
switch (_that) {
case _Trace():
return $default(_that.traceId,_that.spans);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function(@JsonKey(name: 'trace_id')  String traceId,  List<SpanInfo> spans)?  $default,) {final _that = this;
switch (_that) {
case _Trace() when $default != null:
return $default(_that.traceId,_that.spans);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _Trace with DiagnosticableTreeMixin implements Trace {
  const _Trace({@JsonKey(name: 'trace_id') required this.traceId, required final  List<SpanInfo> spans}): _spans = spans;
  factory _Trace.fromJson(Map<String, dynamic> json) => _$TraceFromJson(json);

@override@JsonKey(name: 'trace_id') final  String traceId;
 final  List<SpanInfo> _spans;
@override List<SpanInfo> get spans {
  if (_spans is EqualUnmodifiableListView) return _spans;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_spans);
}


/// Create a copy of Trace
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$TraceCopyWith<_Trace> get copyWith => __$TraceCopyWithImpl<_Trace>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$TraceToJson(this, );
}
@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'Trace'))
    ..add(DiagnosticsProperty('traceId', traceId))..add(DiagnosticsProperty('spans', spans));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _Trace&&(identical(other.traceId, traceId) || other.traceId == traceId)&&const DeepCollectionEquality().equals(other._spans, _spans));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,traceId,const DeepCollectionEquality().hash(_spans));

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'Trace(traceId: $traceId, spans: $spans)';
}


}

/// @nodoc
abstract mixin class _$TraceCopyWith<$Res> implements $TraceCopyWith<$Res> {
  factory _$TraceCopyWith(_Trace value, $Res Function(_Trace) _then) = __$TraceCopyWithImpl;
@override @useResult
$Res call({
@JsonKey(name: 'trace_id') String traceId, List<SpanInfo> spans
});




}
/// @nodoc
class __$TraceCopyWithImpl<$Res>
    implements _$TraceCopyWith<$Res> {
  __$TraceCopyWithImpl(this._self, this._then);

  final _Trace _self;
  final $Res Function(_Trace) _then;

/// Create a copy of Trace
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? traceId = null,Object? spans = null,}) {
  return _then(_Trace(
traceId: null == traceId ? _self.traceId : traceId // ignore: cast_nullable_to_non_nullable
as String,spans: null == spans ? _self._spans : spans // ignore: cast_nullable_to_non_nullable
as List<SpanInfo>,
  ));
}


}

// dart format on
