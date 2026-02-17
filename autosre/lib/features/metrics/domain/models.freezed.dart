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
mixin _$MetricPoint implements DiagnosticableTreeMixin {

 DateTime get timestamp; double get value;@JsonKey(name: 'is_anomaly') bool get isAnomaly;
/// Create a copy of MetricPoint
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$MetricPointCopyWith<MetricPoint> get copyWith => _$MetricPointCopyWithImpl<MetricPoint>(this as MetricPoint, _$identity);

  /// Serializes this MetricPoint to a JSON map.
  Map<String, dynamic> toJson();

@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'MetricPoint'))
    ..add(DiagnosticsProperty('timestamp', timestamp))..add(DiagnosticsProperty('value', value))..add(DiagnosticsProperty('isAnomaly', isAnomaly));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is MetricPoint&&(identical(other.timestamp, timestamp) || other.timestamp == timestamp)&&(identical(other.value, value) || other.value == value)&&(identical(other.isAnomaly, isAnomaly) || other.isAnomaly == isAnomaly));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,timestamp,value,isAnomaly);

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'MetricPoint(timestamp: $timestamp, value: $value, isAnomaly: $isAnomaly)';
}


}

/// @nodoc
abstract mixin class $MetricPointCopyWith<$Res>  {
  factory $MetricPointCopyWith(MetricPoint value, $Res Function(MetricPoint) _then) = _$MetricPointCopyWithImpl;
@useResult
$Res call({
 DateTime timestamp, double value,@JsonKey(name: 'is_anomaly') bool isAnomaly
});




}
/// @nodoc
class _$MetricPointCopyWithImpl<$Res>
    implements $MetricPointCopyWith<$Res> {
  _$MetricPointCopyWithImpl(this._self, this._then);

  final MetricPoint _self;
  final $Res Function(MetricPoint) _then;

/// Create a copy of MetricPoint
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? timestamp = null,Object? value = null,Object? isAnomaly = null,}) {
  return _then(_self.copyWith(
timestamp: null == timestamp ? _self.timestamp : timestamp // ignore: cast_nullable_to_non_nullable
as DateTime,value: null == value ? _self.value : value // ignore: cast_nullable_to_non_nullable
as double,isAnomaly: null == isAnomaly ? _self.isAnomaly : isAnomaly // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}

}


/// Adds pattern-matching-related methods to [MetricPoint].
extension MetricPointPatterns on MetricPoint {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _MetricPoint value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _MetricPoint() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _MetricPoint value)  $default,){
final _that = this;
switch (_that) {
case _MetricPoint():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _MetricPoint value)?  $default,){
final _that = this;
switch (_that) {
case _MetricPoint() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( DateTime timestamp,  double value, @JsonKey(name: 'is_anomaly')  bool isAnomaly)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _MetricPoint() when $default != null:
return $default(_that.timestamp,_that.value,_that.isAnomaly);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( DateTime timestamp,  double value, @JsonKey(name: 'is_anomaly')  bool isAnomaly)  $default,) {final _that = this;
switch (_that) {
case _MetricPoint():
return $default(_that.timestamp,_that.value,_that.isAnomaly);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( DateTime timestamp,  double value, @JsonKey(name: 'is_anomaly')  bool isAnomaly)?  $default,) {final _that = this;
switch (_that) {
case _MetricPoint() when $default != null:
return $default(_that.timestamp,_that.value,_that.isAnomaly);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _MetricPoint with DiagnosticableTreeMixin implements MetricPoint {
  const _MetricPoint({required this.timestamp, this.value = 0.0, @JsonKey(name: 'is_anomaly') this.isAnomaly = false});
  factory _MetricPoint.fromJson(Map<String, dynamic> json) => _$MetricPointFromJson(json);

@override final  DateTime timestamp;
@override@JsonKey() final  double value;
@override@JsonKey(name: 'is_anomaly') final  bool isAnomaly;

/// Create a copy of MetricPoint
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$MetricPointCopyWith<_MetricPoint> get copyWith => __$MetricPointCopyWithImpl<_MetricPoint>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$MetricPointToJson(this, );
}
@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'MetricPoint'))
    ..add(DiagnosticsProperty('timestamp', timestamp))..add(DiagnosticsProperty('value', value))..add(DiagnosticsProperty('isAnomaly', isAnomaly));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _MetricPoint&&(identical(other.timestamp, timestamp) || other.timestamp == timestamp)&&(identical(other.value, value) || other.value == value)&&(identical(other.isAnomaly, isAnomaly) || other.isAnomaly == isAnomaly));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,timestamp,value,isAnomaly);

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'MetricPoint(timestamp: $timestamp, value: $value, isAnomaly: $isAnomaly)';
}


}

/// @nodoc
abstract mixin class _$MetricPointCopyWith<$Res> implements $MetricPointCopyWith<$Res> {
  factory _$MetricPointCopyWith(_MetricPoint value, $Res Function(_MetricPoint) _then) = __$MetricPointCopyWithImpl;
@override @useResult
$Res call({
 DateTime timestamp, double value,@JsonKey(name: 'is_anomaly') bool isAnomaly
});




}
/// @nodoc
class __$MetricPointCopyWithImpl<$Res>
    implements _$MetricPointCopyWith<$Res> {
  __$MetricPointCopyWithImpl(this._self, this._then);

  final _MetricPoint _self;
  final $Res Function(_MetricPoint) _then;

/// Create a copy of MetricPoint
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? timestamp = null,Object? value = null,Object? isAnomaly = null,}) {
  return _then(_MetricPoint(
timestamp: null == timestamp ? _self.timestamp : timestamp // ignore: cast_nullable_to_non_nullable
as DateTime,value: null == value ? _self.value : value // ignore: cast_nullable_to_non_nullable
as double,isAnomaly: null == isAnomaly ? _self.isAnomaly : isAnomaly // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}


}


/// @nodoc
mixin _$MetricSeries implements DiagnosticableTreeMixin {

@JsonKey(name: 'metric_name') String get metricName; List<MetricPoint> get points; Map<String, dynamic> get labels;
/// Create a copy of MetricSeries
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$MetricSeriesCopyWith<MetricSeries> get copyWith => _$MetricSeriesCopyWithImpl<MetricSeries>(this as MetricSeries, _$identity);

  /// Serializes this MetricSeries to a JSON map.
  Map<String, dynamic> toJson();

@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'MetricSeries'))
    ..add(DiagnosticsProperty('metricName', metricName))..add(DiagnosticsProperty('points', points))..add(DiagnosticsProperty('labels', labels));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is MetricSeries&&(identical(other.metricName, metricName) || other.metricName == metricName)&&const DeepCollectionEquality().equals(other.points, points)&&const DeepCollectionEquality().equals(other.labels, labels));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,metricName,const DeepCollectionEquality().hash(points),const DeepCollectionEquality().hash(labels));

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'MetricSeries(metricName: $metricName, points: $points, labels: $labels)';
}


}

/// @nodoc
abstract mixin class $MetricSeriesCopyWith<$Res>  {
  factory $MetricSeriesCopyWith(MetricSeries value, $Res Function(MetricSeries) _then) = _$MetricSeriesCopyWithImpl;
@useResult
$Res call({
@JsonKey(name: 'metric_name') String metricName, List<MetricPoint> points, Map<String, dynamic> labels
});




}
/// @nodoc
class _$MetricSeriesCopyWithImpl<$Res>
    implements $MetricSeriesCopyWith<$Res> {
  _$MetricSeriesCopyWithImpl(this._self, this._then);

  final MetricSeries _self;
  final $Res Function(MetricSeries) _then;

/// Create a copy of MetricSeries
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? metricName = null,Object? points = null,Object? labels = null,}) {
  return _then(_self.copyWith(
metricName: null == metricName ? _self.metricName : metricName // ignore: cast_nullable_to_non_nullable
as String,points: null == points ? _self.points : points // ignore: cast_nullable_to_non_nullable
as List<MetricPoint>,labels: null == labels ? _self.labels : labels // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>,
  ));
}

}


/// Adds pattern-matching-related methods to [MetricSeries].
extension MetricSeriesPatterns on MetricSeries {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _MetricSeries value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _MetricSeries() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _MetricSeries value)  $default,){
final _that = this;
switch (_that) {
case _MetricSeries():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _MetricSeries value)?  $default,){
final _that = this;
switch (_that) {
case _MetricSeries() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function(@JsonKey(name: 'metric_name')  String metricName,  List<MetricPoint> points,  Map<String, dynamic> labels)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _MetricSeries() when $default != null:
return $default(_that.metricName,_that.points,_that.labels);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function(@JsonKey(name: 'metric_name')  String metricName,  List<MetricPoint> points,  Map<String, dynamic> labels)  $default,) {final _that = this;
switch (_that) {
case _MetricSeries():
return $default(_that.metricName,_that.points,_that.labels);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function(@JsonKey(name: 'metric_name')  String metricName,  List<MetricPoint> points,  Map<String, dynamic> labels)?  $default,) {final _that = this;
switch (_that) {
case _MetricSeries() when $default != null:
return $default(_that.metricName,_that.points,_that.labels);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _MetricSeries with DiagnosticableTreeMixin implements MetricSeries {
  const _MetricSeries({@JsonKey(name: 'metric_name') required this.metricName, required final  List<MetricPoint> points, final  Map<String, dynamic> labels = const {}}): _points = points,_labels = labels;
  factory _MetricSeries.fromJson(Map<String, dynamic> json) => _$MetricSeriesFromJson(json);

@override@JsonKey(name: 'metric_name') final  String metricName;
 final  List<MetricPoint> _points;
@override List<MetricPoint> get points {
  if (_points is EqualUnmodifiableListView) return _points;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_points);
}

 final  Map<String, dynamic> _labels;
@override@JsonKey() Map<String, dynamic> get labels {
  if (_labels is EqualUnmodifiableMapView) return _labels;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableMapView(_labels);
}


/// Create a copy of MetricSeries
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$MetricSeriesCopyWith<_MetricSeries> get copyWith => __$MetricSeriesCopyWithImpl<_MetricSeries>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$MetricSeriesToJson(this, );
}
@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'MetricSeries'))
    ..add(DiagnosticsProperty('metricName', metricName))..add(DiagnosticsProperty('points', points))..add(DiagnosticsProperty('labels', labels));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _MetricSeries&&(identical(other.metricName, metricName) || other.metricName == metricName)&&const DeepCollectionEquality().equals(other._points, _points)&&const DeepCollectionEquality().equals(other._labels, _labels));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,metricName,const DeepCollectionEquality().hash(_points),const DeepCollectionEquality().hash(_labels));

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'MetricSeries(metricName: $metricName, points: $points, labels: $labels)';
}


}

/// @nodoc
abstract mixin class _$MetricSeriesCopyWith<$Res> implements $MetricSeriesCopyWith<$Res> {
  factory _$MetricSeriesCopyWith(_MetricSeries value, $Res Function(_MetricSeries) _then) = __$MetricSeriesCopyWithImpl;
@override @useResult
$Res call({
@JsonKey(name: 'metric_name') String metricName, List<MetricPoint> points, Map<String, dynamic> labels
});




}
/// @nodoc
class __$MetricSeriesCopyWithImpl<$Res>
    implements _$MetricSeriesCopyWith<$Res> {
  __$MetricSeriesCopyWithImpl(this._self, this._then);

  final _MetricSeries _self;
  final $Res Function(_MetricSeries) _then;

/// Create a copy of MetricSeries
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? metricName = null,Object? points = null,Object? labels = null,}) {
  return _then(_MetricSeries(
metricName: null == metricName ? _self.metricName : metricName // ignore: cast_nullable_to_non_nullable
as String,points: null == points ? _self._points : points // ignore: cast_nullable_to_non_nullable
as List<MetricPoint>,labels: null == labels ? _self._labels : labels // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>,
  ));
}


}


/// @nodoc
mixin _$MetricDataPoint implements DiagnosticableTreeMixin {

 DateTime get timestamp; double get value;
/// Create a copy of MetricDataPoint
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$MetricDataPointCopyWith<MetricDataPoint> get copyWith => _$MetricDataPointCopyWithImpl<MetricDataPoint>(this as MetricDataPoint, _$identity);

  /// Serializes this MetricDataPoint to a JSON map.
  Map<String, dynamic> toJson();

@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'MetricDataPoint'))
    ..add(DiagnosticsProperty('timestamp', timestamp))..add(DiagnosticsProperty('value', value));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is MetricDataPoint&&(identical(other.timestamp, timestamp) || other.timestamp == timestamp)&&(identical(other.value, value) || other.value == value));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,timestamp,value);

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'MetricDataPoint(timestamp: $timestamp, value: $value)';
}


}

/// @nodoc
abstract mixin class $MetricDataPointCopyWith<$Res>  {
  factory $MetricDataPointCopyWith(MetricDataPoint value, $Res Function(MetricDataPoint) _then) = _$MetricDataPointCopyWithImpl;
@useResult
$Res call({
 DateTime timestamp, double value
});




}
/// @nodoc
class _$MetricDataPointCopyWithImpl<$Res>
    implements $MetricDataPointCopyWith<$Res> {
  _$MetricDataPointCopyWithImpl(this._self, this._then);

  final MetricDataPoint _self;
  final $Res Function(MetricDataPoint) _then;

/// Create a copy of MetricDataPoint
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? timestamp = null,Object? value = null,}) {
  return _then(_self.copyWith(
timestamp: null == timestamp ? _self.timestamp : timestamp // ignore: cast_nullable_to_non_nullable
as DateTime,value: null == value ? _self.value : value // ignore: cast_nullable_to_non_nullable
as double,
  ));
}

}


/// Adds pattern-matching-related methods to [MetricDataPoint].
extension MetricDataPointPatterns on MetricDataPoint {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _MetricDataPoint value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _MetricDataPoint() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _MetricDataPoint value)  $default,){
final _that = this;
switch (_that) {
case _MetricDataPoint():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _MetricDataPoint value)?  $default,){
final _that = this;
switch (_that) {
case _MetricDataPoint() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( DateTime timestamp,  double value)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _MetricDataPoint() when $default != null:
return $default(_that.timestamp,_that.value);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( DateTime timestamp,  double value)  $default,) {final _that = this;
switch (_that) {
case _MetricDataPoint():
return $default(_that.timestamp,_that.value);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( DateTime timestamp,  double value)?  $default,) {final _that = this;
switch (_that) {
case _MetricDataPoint() when $default != null:
return $default(_that.timestamp,_that.value);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _MetricDataPoint with DiagnosticableTreeMixin implements MetricDataPoint {
  const _MetricDataPoint({required this.timestamp, required this.value});
  factory _MetricDataPoint.fromJson(Map<String, dynamic> json) => _$MetricDataPointFromJson(json);

@override final  DateTime timestamp;
@override final  double value;

/// Create a copy of MetricDataPoint
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$MetricDataPointCopyWith<_MetricDataPoint> get copyWith => __$MetricDataPointCopyWithImpl<_MetricDataPoint>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$MetricDataPointToJson(this, );
}
@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'MetricDataPoint'))
    ..add(DiagnosticsProperty('timestamp', timestamp))..add(DiagnosticsProperty('value', value));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _MetricDataPoint&&(identical(other.timestamp, timestamp) || other.timestamp == timestamp)&&(identical(other.value, value) || other.value == value));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,timestamp,value);

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'MetricDataPoint(timestamp: $timestamp, value: $value)';
}


}

/// @nodoc
abstract mixin class _$MetricDataPointCopyWith<$Res> implements $MetricDataPointCopyWith<$Res> {
  factory _$MetricDataPointCopyWith(_MetricDataPoint value, $Res Function(_MetricDataPoint) _then) = __$MetricDataPointCopyWithImpl;
@override @useResult
$Res call({
 DateTime timestamp, double value
});




}
/// @nodoc
class __$MetricDataPointCopyWithImpl<$Res>
    implements _$MetricDataPointCopyWith<$Res> {
  __$MetricDataPointCopyWithImpl(this._self, this._then);

  final _MetricDataPoint _self;
  final $Res Function(_MetricDataPoint) _then;

/// Create a copy of MetricDataPoint
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? timestamp = null,Object? value = null,}) {
  return _then(_MetricDataPoint(
timestamp: null == timestamp ? _self.timestamp : timestamp // ignore: cast_nullable_to_non_nullable
as DateTime,value: null == value ? _self.value : value // ignore: cast_nullable_to_non_nullable
as double,
  ));
}


}


/// @nodoc
mixin _$DashboardMetric implements DiagnosticableTreeMixin {

 String get id; String get name; String get unit;@JsonKey(name: 'current_value') double get currentValue;@JsonKey(name: 'previous_value') double? get previousValue; double? get threshold; List<MetricDataPoint> get history; String get status;// 'normal', 'warning', 'critical'
@JsonKey(name: 'anomaly_description') String? get anomalyDescription;
/// Create a copy of DashboardMetric
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$DashboardMetricCopyWith<DashboardMetric> get copyWith => _$DashboardMetricCopyWithImpl<DashboardMetric>(this as DashboardMetric, _$identity);

  /// Serializes this DashboardMetric to a JSON map.
  Map<String, dynamic> toJson();

@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'DashboardMetric'))
    ..add(DiagnosticsProperty('id', id))..add(DiagnosticsProperty('name', name))..add(DiagnosticsProperty('unit', unit))..add(DiagnosticsProperty('currentValue', currentValue))..add(DiagnosticsProperty('previousValue', previousValue))..add(DiagnosticsProperty('threshold', threshold))..add(DiagnosticsProperty('history', history))..add(DiagnosticsProperty('status', status))..add(DiagnosticsProperty('anomalyDescription', anomalyDescription));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is DashboardMetric&&(identical(other.id, id) || other.id == id)&&(identical(other.name, name) || other.name == name)&&(identical(other.unit, unit) || other.unit == unit)&&(identical(other.currentValue, currentValue) || other.currentValue == currentValue)&&(identical(other.previousValue, previousValue) || other.previousValue == previousValue)&&(identical(other.threshold, threshold) || other.threshold == threshold)&&const DeepCollectionEquality().equals(other.history, history)&&(identical(other.status, status) || other.status == status)&&(identical(other.anomalyDescription, anomalyDescription) || other.anomalyDescription == anomalyDescription));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,id,name,unit,currentValue,previousValue,threshold,const DeepCollectionEquality().hash(history),status,anomalyDescription);

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'DashboardMetric(id: $id, name: $name, unit: $unit, currentValue: $currentValue, previousValue: $previousValue, threshold: $threshold, history: $history, status: $status, anomalyDescription: $anomalyDescription)';
}


}

/// @nodoc
abstract mixin class $DashboardMetricCopyWith<$Res>  {
  factory $DashboardMetricCopyWith(DashboardMetric value, $Res Function(DashboardMetric) _then) = _$DashboardMetricCopyWithImpl;
@useResult
$Res call({
 String id, String name, String unit,@JsonKey(name: 'current_value') double currentValue,@JsonKey(name: 'previous_value') double? previousValue, double? threshold, List<MetricDataPoint> history, String status,@JsonKey(name: 'anomaly_description') String? anomalyDescription
});




}
/// @nodoc
class _$DashboardMetricCopyWithImpl<$Res>
    implements $DashboardMetricCopyWith<$Res> {
  _$DashboardMetricCopyWithImpl(this._self, this._then);

  final DashboardMetric _self;
  final $Res Function(DashboardMetric) _then;

/// Create a copy of DashboardMetric
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? name = null,Object? unit = null,Object? currentValue = null,Object? previousValue = freezed,Object? threshold = freezed,Object? history = null,Object? status = null,Object? anomalyDescription = freezed,}) {
  return _then(_self.copyWith(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,unit: null == unit ? _self.unit : unit // ignore: cast_nullable_to_non_nullable
as String,currentValue: null == currentValue ? _self.currentValue : currentValue // ignore: cast_nullable_to_non_nullable
as double,previousValue: freezed == previousValue ? _self.previousValue : previousValue // ignore: cast_nullable_to_non_nullable
as double?,threshold: freezed == threshold ? _self.threshold : threshold // ignore: cast_nullable_to_non_nullable
as double?,history: null == history ? _self.history : history // ignore: cast_nullable_to_non_nullable
as List<MetricDataPoint>,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as String,anomalyDescription: freezed == anomalyDescription ? _self.anomalyDescription : anomalyDescription // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

}


/// Adds pattern-matching-related methods to [DashboardMetric].
extension DashboardMetricPatterns on DashboardMetric {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _DashboardMetric value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _DashboardMetric() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _DashboardMetric value)  $default,){
final _that = this;
switch (_that) {
case _DashboardMetric():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _DashboardMetric value)?  $default,){
final _that = this;
switch (_that) {
case _DashboardMetric() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id,  String name,  String unit, @JsonKey(name: 'current_value')  double currentValue, @JsonKey(name: 'previous_value')  double? previousValue,  double? threshold,  List<MetricDataPoint> history,  String status, @JsonKey(name: 'anomaly_description')  String? anomalyDescription)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _DashboardMetric() when $default != null:
return $default(_that.id,_that.name,_that.unit,_that.currentValue,_that.previousValue,_that.threshold,_that.history,_that.status,_that.anomalyDescription);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id,  String name,  String unit, @JsonKey(name: 'current_value')  double currentValue, @JsonKey(name: 'previous_value')  double? previousValue,  double? threshold,  List<MetricDataPoint> history,  String status, @JsonKey(name: 'anomaly_description')  String? anomalyDescription)  $default,) {final _that = this;
switch (_that) {
case _DashboardMetric():
return $default(_that.id,_that.name,_that.unit,_that.currentValue,_that.previousValue,_that.threshold,_that.history,_that.status,_that.anomalyDescription);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id,  String name,  String unit, @JsonKey(name: 'current_value')  double currentValue, @JsonKey(name: 'previous_value')  double? previousValue,  double? threshold,  List<MetricDataPoint> history,  String status, @JsonKey(name: 'anomaly_description')  String? anomalyDescription)?  $default,) {final _that = this;
switch (_that) {
case _DashboardMetric() when $default != null:
return $default(_that.id,_that.name,_that.unit,_that.currentValue,_that.previousValue,_that.threshold,_that.history,_that.status,_that.anomalyDescription);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _DashboardMetric extends DashboardMetric with DiagnosticableTreeMixin {
  const _DashboardMetric({required this.id, required this.name, required this.unit, @JsonKey(name: 'current_value') required this.currentValue, @JsonKey(name: 'previous_value') this.previousValue, this.threshold, final  List<MetricDataPoint> history = const [], this.status = 'normal', @JsonKey(name: 'anomaly_description') this.anomalyDescription}): _history = history,super._();
  factory _DashboardMetric.fromJson(Map<String, dynamic> json) => _$DashboardMetricFromJson(json);

@override final  String id;
@override final  String name;
@override final  String unit;
@override@JsonKey(name: 'current_value') final  double currentValue;
@override@JsonKey(name: 'previous_value') final  double? previousValue;
@override final  double? threshold;
 final  List<MetricDataPoint> _history;
@override@JsonKey() List<MetricDataPoint> get history {
  if (_history is EqualUnmodifiableListView) return _history;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_history);
}

@override@JsonKey() final  String status;
// 'normal', 'warning', 'critical'
@override@JsonKey(name: 'anomaly_description') final  String? anomalyDescription;

/// Create a copy of DashboardMetric
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$DashboardMetricCopyWith<_DashboardMetric> get copyWith => __$DashboardMetricCopyWithImpl<_DashboardMetric>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$DashboardMetricToJson(this, );
}
@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'DashboardMetric'))
    ..add(DiagnosticsProperty('id', id))..add(DiagnosticsProperty('name', name))..add(DiagnosticsProperty('unit', unit))..add(DiagnosticsProperty('currentValue', currentValue))..add(DiagnosticsProperty('previousValue', previousValue))..add(DiagnosticsProperty('threshold', threshold))..add(DiagnosticsProperty('history', history))..add(DiagnosticsProperty('status', status))..add(DiagnosticsProperty('anomalyDescription', anomalyDescription));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _DashboardMetric&&(identical(other.id, id) || other.id == id)&&(identical(other.name, name) || other.name == name)&&(identical(other.unit, unit) || other.unit == unit)&&(identical(other.currentValue, currentValue) || other.currentValue == currentValue)&&(identical(other.previousValue, previousValue) || other.previousValue == previousValue)&&(identical(other.threshold, threshold) || other.threshold == threshold)&&const DeepCollectionEquality().equals(other._history, _history)&&(identical(other.status, status) || other.status == status)&&(identical(other.anomalyDescription, anomalyDescription) || other.anomalyDescription == anomalyDescription));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,id,name,unit,currentValue,previousValue,threshold,const DeepCollectionEquality().hash(_history),status,anomalyDescription);

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'DashboardMetric(id: $id, name: $name, unit: $unit, currentValue: $currentValue, previousValue: $previousValue, threshold: $threshold, history: $history, status: $status, anomalyDescription: $anomalyDescription)';
}


}

/// @nodoc
abstract mixin class _$DashboardMetricCopyWith<$Res> implements $DashboardMetricCopyWith<$Res> {
  factory _$DashboardMetricCopyWith(_DashboardMetric value, $Res Function(_DashboardMetric) _then) = __$DashboardMetricCopyWithImpl;
@override @useResult
$Res call({
 String id, String name, String unit,@JsonKey(name: 'current_value') double currentValue,@JsonKey(name: 'previous_value') double? previousValue, double? threshold, List<MetricDataPoint> history, String status,@JsonKey(name: 'anomaly_description') String? anomalyDescription
});




}
/// @nodoc
class __$DashboardMetricCopyWithImpl<$Res>
    implements _$DashboardMetricCopyWith<$Res> {
  __$DashboardMetricCopyWithImpl(this._self, this._then);

  final _DashboardMetric _self;
  final $Res Function(_DashboardMetric) _then;

/// Create a copy of DashboardMetric
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? name = null,Object? unit = null,Object? currentValue = null,Object? previousValue = freezed,Object? threshold = freezed,Object? history = null,Object? status = null,Object? anomalyDescription = freezed,}) {
  return _then(_DashboardMetric(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,unit: null == unit ? _self.unit : unit // ignore: cast_nullable_to_non_nullable
as String,currentValue: null == currentValue ? _self.currentValue : currentValue // ignore: cast_nullable_to_non_nullable
as double,previousValue: freezed == previousValue ? _self.previousValue : previousValue // ignore: cast_nullable_to_non_nullable
as double?,threshold: freezed == threshold ? _self.threshold : threshold // ignore: cast_nullable_to_non_nullable
as double?,history: null == history ? _self._history : history // ignore: cast_nullable_to_non_nullable
as List<MetricDataPoint>,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as String,anomalyDescription: freezed == anomalyDescription ? _self.anomalyDescription : anomalyDescription // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}


}


/// @nodoc
mixin _$MetricsDashboardData implements DiagnosticableTreeMixin {

 String get title;@JsonKey(name: 'service_name') String? get serviceName; List<DashboardMetric> get metrics;@JsonKey(name: 'last_updated') DateTime? get lastUpdated;
/// Create a copy of MetricsDashboardData
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$MetricsDashboardDataCopyWith<MetricsDashboardData> get copyWith => _$MetricsDashboardDataCopyWithImpl<MetricsDashboardData>(this as MetricsDashboardData, _$identity);

  /// Serializes this MetricsDashboardData to a JSON map.
  Map<String, dynamic> toJson();

@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'MetricsDashboardData'))
    ..add(DiagnosticsProperty('title', title))..add(DiagnosticsProperty('serviceName', serviceName))..add(DiagnosticsProperty('metrics', metrics))..add(DiagnosticsProperty('lastUpdated', lastUpdated));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is MetricsDashboardData&&(identical(other.title, title) || other.title == title)&&(identical(other.serviceName, serviceName) || other.serviceName == serviceName)&&const DeepCollectionEquality().equals(other.metrics, metrics)&&(identical(other.lastUpdated, lastUpdated) || other.lastUpdated == lastUpdated));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,title,serviceName,const DeepCollectionEquality().hash(metrics),lastUpdated);

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'MetricsDashboardData(title: $title, serviceName: $serviceName, metrics: $metrics, lastUpdated: $lastUpdated)';
}


}

/// @nodoc
abstract mixin class $MetricsDashboardDataCopyWith<$Res>  {
  factory $MetricsDashboardDataCopyWith(MetricsDashboardData value, $Res Function(MetricsDashboardData) _then) = _$MetricsDashboardDataCopyWithImpl;
@useResult
$Res call({
 String title,@JsonKey(name: 'service_name') String? serviceName, List<DashboardMetric> metrics,@JsonKey(name: 'last_updated') DateTime? lastUpdated
});




}
/// @nodoc
class _$MetricsDashboardDataCopyWithImpl<$Res>
    implements $MetricsDashboardDataCopyWith<$Res> {
  _$MetricsDashboardDataCopyWithImpl(this._self, this._then);

  final MetricsDashboardData _self;
  final $Res Function(MetricsDashboardData) _then;

/// Create a copy of MetricsDashboardData
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? title = null,Object? serviceName = freezed,Object? metrics = null,Object? lastUpdated = freezed,}) {
  return _then(_self.copyWith(
title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,serviceName: freezed == serviceName ? _self.serviceName : serviceName // ignore: cast_nullable_to_non_nullable
as String?,metrics: null == metrics ? _self.metrics : metrics // ignore: cast_nullable_to_non_nullable
as List<DashboardMetric>,lastUpdated: freezed == lastUpdated ? _self.lastUpdated : lastUpdated // ignore: cast_nullable_to_non_nullable
as DateTime?,
  ));
}

}


/// Adds pattern-matching-related methods to [MetricsDashboardData].
extension MetricsDashboardDataPatterns on MetricsDashboardData {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _MetricsDashboardData value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _MetricsDashboardData() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _MetricsDashboardData value)  $default,){
final _that = this;
switch (_that) {
case _MetricsDashboardData():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _MetricsDashboardData value)?  $default,){
final _that = this;
switch (_that) {
case _MetricsDashboardData() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String title, @JsonKey(name: 'service_name')  String? serviceName,  List<DashboardMetric> metrics, @JsonKey(name: 'last_updated')  DateTime? lastUpdated)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _MetricsDashboardData() when $default != null:
return $default(_that.title,_that.serviceName,_that.metrics,_that.lastUpdated);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String title, @JsonKey(name: 'service_name')  String? serviceName,  List<DashboardMetric> metrics, @JsonKey(name: 'last_updated')  DateTime? lastUpdated)  $default,) {final _that = this;
switch (_that) {
case _MetricsDashboardData():
return $default(_that.title,_that.serviceName,_that.metrics,_that.lastUpdated);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String title, @JsonKey(name: 'service_name')  String? serviceName,  List<DashboardMetric> metrics, @JsonKey(name: 'last_updated')  DateTime? lastUpdated)?  $default,) {final _that = this;
switch (_that) {
case _MetricsDashboardData() when $default != null:
return $default(_that.title,_that.serviceName,_that.metrics,_that.lastUpdated);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _MetricsDashboardData with DiagnosticableTreeMixin implements MetricsDashboardData {
  const _MetricsDashboardData({this.title = 'Metrics Dashboard', @JsonKey(name: 'service_name') this.serviceName, required final  List<DashboardMetric> metrics, @JsonKey(name: 'last_updated') this.lastUpdated}): _metrics = metrics;
  factory _MetricsDashboardData.fromJson(Map<String, dynamic> json) => _$MetricsDashboardDataFromJson(json);

@override@JsonKey() final  String title;
@override@JsonKey(name: 'service_name') final  String? serviceName;
 final  List<DashboardMetric> _metrics;
@override List<DashboardMetric> get metrics {
  if (_metrics is EqualUnmodifiableListView) return _metrics;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_metrics);
}

@override@JsonKey(name: 'last_updated') final  DateTime? lastUpdated;

/// Create a copy of MetricsDashboardData
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$MetricsDashboardDataCopyWith<_MetricsDashboardData> get copyWith => __$MetricsDashboardDataCopyWithImpl<_MetricsDashboardData>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$MetricsDashboardDataToJson(this, );
}
@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'MetricsDashboardData'))
    ..add(DiagnosticsProperty('title', title))..add(DiagnosticsProperty('serviceName', serviceName))..add(DiagnosticsProperty('metrics', metrics))..add(DiagnosticsProperty('lastUpdated', lastUpdated));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _MetricsDashboardData&&(identical(other.title, title) || other.title == title)&&(identical(other.serviceName, serviceName) || other.serviceName == serviceName)&&const DeepCollectionEquality().equals(other._metrics, _metrics)&&(identical(other.lastUpdated, lastUpdated) || other.lastUpdated == lastUpdated));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,title,serviceName,const DeepCollectionEquality().hash(_metrics),lastUpdated);

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'MetricsDashboardData(title: $title, serviceName: $serviceName, metrics: $metrics, lastUpdated: $lastUpdated)';
}


}

/// @nodoc
abstract mixin class _$MetricsDashboardDataCopyWith<$Res> implements $MetricsDashboardDataCopyWith<$Res> {
  factory _$MetricsDashboardDataCopyWith(_MetricsDashboardData value, $Res Function(_MetricsDashboardData) _then) = __$MetricsDashboardDataCopyWithImpl;
@override @useResult
$Res call({
 String title,@JsonKey(name: 'service_name') String? serviceName, List<DashboardMetric> metrics,@JsonKey(name: 'last_updated') DateTime? lastUpdated
});




}
/// @nodoc
class __$MetricsDashboardDataCopyWithImpl<$Res>
    implements _$MetricsDashboardDataCopyWith<$Res> {
  __$MetricsDashboardDataCopyWithImpl(this._self, this._then);

  final _MetricsDashboardData _self;
  final $Res Function(_MetricsDashboardData) _then;

/// Create a copy of MetricsDashboardData
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? title = null,Object? serviceName = freezed,Object? metrics = null,Object? lastUpdated = freezed,}) {
  return _then(_MetricsDashboardData(
title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,serviceName: freezed == serviceName ? _self.serviceName : serviceName // ignore: cast_nullable_to_non_nullable
as String?,metrics: null == metrics ? _self._metrics : metrics // ignore: cast_nullable_to_non_nullable
as List<DashboardMetric>,lastUpdated: freezed == lastUpdated ? _self.lastUpdated : lastUpdated // ignore: cast_nullable_to_non_nullable
as DateTime?,
  ));
}


}

// dart format on
