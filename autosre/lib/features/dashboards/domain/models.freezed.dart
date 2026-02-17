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
mixin _$GridPosition {

 int get x; int get y; int get width; int get height;
/// Create a copy of GridPosition
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$GridPositionCopyWith<GridPosition> get copyWith => _$GridPositionCopyWithImpl<GridPosition>(this as GridPosition, _$identity);

  /// Serializes this GridPosition to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is GridPosition&&(identical(other.x, x) || other.x == x)&&(identical(other.y, y) || other.y == y)&&(identical(other.width, width) || other.width == width)&&(identical(other.height, height) || other.height == height));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,x,y,width,height);

@override
String toString() {
  return 'GridPosition(x: $x, y: $y, width: $width, height: $height)';
}


}

/// @nodoc
abstract mixin class $GridPositionCopyWith<$Res>  {
  factory $GridPositionCopyWith(GridPosition value, $Res Function(GridPosition) _then) = _$GridPositionCopyWithImpl;
@useResult
$Res call({
 int x, int y, int width, int height
});




}
/// @nodoc
class _$GridPositionCopyWithImpl<$Res>
    implements $GridPositionCopyWith<$Res> {
  _$GridPositionCopyWithImpl(this._self, this._then);

  final GridPosition _self;
  final $Res Function(GridPosition) _then;

/// Create a copy of GridPosition
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? x = null,Object? y = null,Object? width = null,Object? height = null,}) {
  return _then(_self.copyWith(
x: null == x ? _self.x : x // ignore: cast_nullable_to_non_nullable
as int,y: null == y ? _self.y : y // ignore: cast_nullable_to_non_nullable
as int,width: null == width ? _self.width : width // ignore: cast_nullable_to_non_nullable
as int,height: null == height ? _self.height : height // ignore: cast_nullable_to_non_nullable
as int,
  ));
}

}


/// Adds pattern-matching-related methods to [GridPosition].
extension GridPositionPatterns on GridPosition {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _GridPosition value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _GridPosition() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _GridPosition value)  $default,){
final _that = this;
switch (_that) {
case _GridPosition():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _GridPosition value)?  $default,){
final _that = this;
switch (_that) {
case _GridPosition() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( int x,  int y,  int width,  int height)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _GridPosition() when $default != null:
return $default(_that.x,_that.y,_that.width,_that.height);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( int x,  int y,  int width,  int height)  $default,) {final _that = this;
switch (_that) {
case _GridPosition():
return $default(_that.x,_that.y,_that.width,_that.height);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( int x,  int y,  int width,  int height)?  $default,) {final _that = this;
switch (_that) {
case _GridPosition() when $default != null:
return $default(_that.x,_that.y,_that.width,_that.height);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _GridPosition implements GridPosition {
  const _GridPosition({this.x = 0, this.y = 0, this.width = 12, this.height = 4});
  factory _GridPosition.fromJson(Map<String, dynamic> json) => _$GridPositionFromJson(json);

@override@JsonKey() final  int x;
@override@JsonKey() final  int y;
@override@JsonKey() final  int width;
@override@JsonKey() final  int height;

/// Create a copy of GridPosition
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$GridPositionCopyWith<_GridPosition> get copyWith => __$GridPositionCopyWithImpl<_GridPosition>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$GridPositionToJson(this, );
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _GridPosition&&(identical(other.x, x) || other.x == x)&&(identical(other.y, y) || other.y == y)&&(identical(other.width, width) || other.width == width)&&(identical(other.height, height) || other.height == height));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,x,y,width,height);

@override
String toString() {
  return 'GridPosition(x: $x, y: $y, width: $width, height: $height)';
}


}

/// @nodoc
abstract mixin class _$GridPositionCopyWith<$Res> implements $GridPositionCopyWith<$Res> {
  factory _$GridPositionCopyWith(_GridPosition value, $Res Function(_GridPosition) _then) = __$GridPositionCopyWithImpl;
@override @useResult
$Res call({
 int x, int y, int width, int height
});




}
/// @nodoc
class __$GridPositionCopyWithImpl<$Res>
    implements _$GridPositionCopyWith<$Res> {
  __$GridPositionCopyWithImpl(this._self, this._then);

  final _GridPosition _self;
  final $Res Function(_GridPosition) _then;

/// Create a copy of GridPosition
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? x = null,Object? y = null,Object? width = null,Object? height = null,}) {
  return _then(_GridPosition(
x: null == x ? _self.x : x // ignore: cast_nullable_to_non_nullable
as int,y: null == y ? _self.y : y // ignore: cast_nullable_to_non_nullable
as int,width: null == width ? _self.width : width // ignore: cast_nullable_to_non_nullable
as int,height: null == height ? _self.height : height // ignore: cast_nullable_to_non_nullable
as int,
  ));
}


}


/// @nodoc
mixin _$TimeRange {

 String get preset; String? get start; String? get end;@JsonKey(name: 'refresh_interval_seconds') int? get refreshIntervalSeconds;
/// Create a copy of TimeRange
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$TimeRangeCopyWith<TimeRange> get copyWith => _$TimeRangeCopyWithImpl<TimeRange>(this as TimeRange, _$identity);

  /// Serializes this TimeRange to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is TimeRange&&(identical(other.preset, preset) || other.preset == preset)&&(identical(other.start, start) || other.start == start)&&(identical(other.end, end) || other.end == end)&&(identical(other.refreshIntervalSeconds, refreshIntervalSeconds) || other.refreshIntervalSeconds == refreshIntervalSeconds));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,preset,start,end,refreshIntervalSeconds);

@override
String toString() {
  return 'TimeRange(preset: $preset, start: $start, end: $end, refreshIntervalSeconds: $refreshIntervalSeconds)';
}


}

/// @nodoc
abstract mixin class $TimeRangeCopyWith<$Res>  {
  factory $TimeRangeCopyWith(TimeRange value, $Res Function(TimeRange) _then) = _$TimeRangeCopyWithImpl;
@useResult
$Res call({
 String preset, String? start, String? end,@JsonKey(name: 'refresh_interval_seconds') int? refreshIntervalSeconds
});




}
/// @nodoc
class _$TimeRangeCopyWithImpl<$Res>
    implements $TimeRangeCopyWith<$Res> {
  _$TimeRangeCopyWithImpl(this._self, this._then);

  final TimeRange _self;
  final $Res Function(TimeRange) _then;

/// Create a copy of TimeRange
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? preset = null,Object? start = freezed,Object? end = freezed,Object? refreshIntervalSeconds = freezed,}) {
  return _then(_self.copyWith(
preset: null == preset ? _self.preset : preset // ignore: cast_nullable_to_non_nullable
as String,start: freezed == start ? _self.start : start // ignore: cast_nullable_to_non_nullable
as String?,end: freezed == end ? _self.end : end // ignore: cast_nullable_to_non_nullable
as String?,refreshIntervalSeconds: freezed == refreshIntervalSeconds ? _self.refreshIntervalSeconds : refreshIntervalSeconds // ignore: cast_nullable_to_non_nullable
as int?,
  ));
}

}


/// Adds pattern-matching-related methods to [TimeRange].
extension TimeRangePatterns on TimeRange {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _TimeRange value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _TimeRange() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _TimeRange value)  $default,){
final _that = this;
switch (_that) {
case _TimeRange():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _TimeRange value)?  $default,){
final _that = this;
switch (_that) {
case _TimeRange() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String preset,  String? start,  String? end, @JsonKey(name: 'refresh_interval_seconds')  int? refreshIntervalSeconds)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _TimeRange() when $default != null:
return $default(_that.preset,_that.start,_that.end,_that.refreshIntervalSeconds);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String preset,  String? start,  String? end, @JsonKey(name: 'refresh_interval_seconds')  int? refreshIntervalSeconds)  $default,) {final _that = this;
switch (_that) {
case _TimeRange():
return $default(_that.preset,_that.start,_that.end,_that.refreshIntervalSeconds);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String preset,  String? start,  String? end, @JsonKey(name: 'refresh_interval_seconds')  int? refreshIntervalSeconds)?  $default,) {final _that = this;
switch (_that) {
case _TimeRange() when $default != null:
return $default(_that.preset,_that.start,_that.end,_that.refreshIntervalSeconds);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _TimeRange implements TimeRange {
  const _TimeRange({this.preset = '1h', this.start, this.end, @JsonKey(name: 'refresh_interval_seconds') this.refreshIntervalSeconds});
  factory _TimeRange.fromJson(Map<String, dynamic> json) => _$TimeRangeFromJson(json);

@override@JsonKey() final  String preset;
@override final  String? start;
@override final  String? end;
@override@JsonKey(name: 'refresh_interval_seconds') final  int? refreshIntervalSeconds;

/// Create a copy of TimeRange
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$TimeRangeCopyWith<_TimeRange> get copyWith => __$TimeRangeCopyWithImpl<_TimeRange>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$TimeRangeToJson(this, );
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _TimeRange&&(identical(other.preset, preset) || other.preset == preset)&&(identical(other.start, start) || other.start == start)&&(identical(other.end, end) || other.end == end)&&(identical(other.refreshIntervalSeconds, refreshIntervalSeconds) || other.refreshIntervalSeconds == refreshIntervalSeconds));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,preset,start,end,refreshIntervalSeconds);

@override
String toString() {
  return 'TimeRange(preset: $preset, start: $start, end: $end, refreshIntervalSeconds: $refreshIntervalSeconds)';
}


}

/// @nodoc
abstract mixin class _$TimeRangeCopyWith<$Res> implements $TimeRangeCopyWith<$Res> {
  factory _$TimeRangeCopyWith(_TimeRange value, $Res Function(_TimeRange) _then) = __$TimeRangeCopyWithImpl;
@override @useResult
$Res call({
 String preset, String? start, String? end,@JsonKey(name: 'refresh_interval_seconds') int? refreshIntervalSeconds
});




}
/// @nodoc
class __$TimeRangeCopyWithImpl<$Res>
    implements _$TimeRangeCopyWith<$Res> {
  __$TimeRangeCopyWithImpl(this._self, this._then);

  final _TimeRange _self;
  final $Res Function(_TimeRange) _then;

/// Create a copy of TimeRange
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? preset = null,Object? start = freezed,Object? end = freezed,Object? refreshIntervalSeconds = freezed,}) {
  return _then(_TimeRange(
preset: null == preset ? _self.preset : preset // ignore: cast_nullable_to_non_nullable
as String,start: freezed == start ? _self.start : start // ignore: cast_nullable_to_non_nullable
as String?,end: freezed == end ? _self.end : end // ignore: cast_nullable_to_non_nullable
as String?,refreshIntervalSeconds: freezed == refreshIntervalSeconds ? _self.refreshIntervalSeconds : refreshIntervalSeconds // ignore: cast_nullable_to_non_nullable
as int?,
  ));
}


}


/// @nodoc
mixin _$DatasourceRef {

 String get type; String? get uid;@JsonKey(name: 'project_id') String? get projectId;
/// Create a copy of DatasourceRef
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$DatasourceRefCopyWith<DatasourceRef> get copyWith => _$DatasourceRefCopyWithImpl<DatasourceRef>(this as DatasourceRef, _$identity);

  /// Serializes this DatasourceRef to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is DatasourceRef&&(identical(other.type, type) || other.type == type)&&(identical(other.uid, uid) || other.uid == uid)&&(identical(other.projectId, projectId) || other.projectId == projectId));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,type,uid,projectId);

@override
String toString() {
  return 'DatasourceRef(type: $type, uid: $uid, projectId: $projectId)';
}


}

/// @nodoc
abstract mixin class $DatasourceRefCopyWith<$Res>  {
  factory $DatasourceRefCopyWith(DatasourceRef value, $Res Function(DatasourceRef) _then) = _$DatasourceRefCopyWithImpl;
@useResult
$Res call({
 String type, String? uid,@JsonKey(name: 'project_id') String? projectId
});




}
/// @nodoc
class _$DatasourceRefCopyWithImpl<$Res>
    implements $DatasourceRefCopyWith<$Res> {
  _$DatasourceRefCopyWithImpl(this._self, this._then);

  final DatasourceRef _self;
  final $Res Function(DatasourceRef) _then;

/// Create a copy of DatasourceRef
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? type = null,Object? uid = freezed,Object? projectId = freezed,}) {
  return _then(_self.copyWith(
type: null == type ? _self.type : type // ignore: cast_nullable_to_non_nullable
as String,uid: freezed == uid ? _self.uid : uid // ignore: cast_nullable_to_non_nullable
as String?,projectId: freezed == projectId ? _self.projectId : projectId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

}


/// Adds pattern-matching-related methods to [DatasourceRef].
extension DatasourceRefPatterns on DatasourceRef {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _DatasourceRef value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _DatasourceRef() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _DatasourceRef value)  $default,){
final _that = this;
switch (_that) {
case _DatasourceRef():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _DatasourceRef value)?  $default,){
final _that = this;
switch (_that) {
case _DatasourceRef() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String type,  String? uid, @JsonKey(name: 'project_id')  String? projectId)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _DatasourceRef() when $default != null:
return $default(_that.type,_that.uid,_that.projectId);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String type,  String? uid, @JsonKey(name: 'project_id')  String? projectId)  $default,) {final _that = this;
switch (_that) {
case _DatasourceRef():
return $default(_that.type,_that.uid,_that.projectId);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String type,  String? uid, @JsonKey(name: 'project_id')  String? projectId)?  $default,) {final _that = this;
switch (_that) {
case _DatasourceRef() when $default != null:
return $default(_that.type,_that.uid,_that.projectId);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _DatasourceRef implements DatasourceRef {
  const _DatasourceRef({required this.type, this.uid, @JsonKey(name: 'project_id') this.projectId});
  factory _DatasourceRef.fromJson(Map<String, dynamic> json) => _$DatasourceRefFromJson(json);

@override final  String type;
@override final  String? uid;
@override@JsonKey(name: 'project_id') final  String? projectId;

/// Create a copy of DatasourceRef
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$DatasourceRefCopyWith<_DatasourceRef> get copyWith => __$DatasourceRefCopyWithImpl<_DatasourceRef>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$DatasourceRefToJson(this, );
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _DatasourceRef&&(identical(other.type, type) || other.type == type)&&(identical(other.uid, uid) || other.uid == uid)&&(identical(other.projectId, projectId) || other.projectId == projectId));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,type,uid,projectId);

@override
String toString() {
  return 'DatasourceRef(type: $type, uid: $uid, projectId: $projectId)';
}


}

/// @nodoc
abstract mixin class _$DatasourceRefCopyWith<$Res> implements $DatasourceRefCopyWith<$Res> {
  factory _$DatasourceRefCopyWith(_DatasourceRef value, $Res Function(_DatasourceRef) _then) = __$DatasourceRefCopyWithImpl;
@override @useResult
$Res call({
 String type, String? uid,@JsonKey(name: 'project_id') String? projectId
});




}
/// @nodoc
class __$DatasourceRefCopyWithImpl<$Res>
    implements _$DatasourceRefCopyWith<$Res> {
  __$DatasourceRefCopyWithImpl(this._self, this._then);

  final _DatasourceRef _self;
  final $Res Function(_DatasourceRef) _then;

/// Create a copy of DatasourceRef
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? type = null,Object? uid = freezed,Object? projectId = freezed,}) {
  return _then(_DatasourceRef(
type: null == type ? _self.type : type // ignore: cast_nullable_to_non_nullable
as String,uid: freezed == uid ? _self.uid : uid // ignore: cast_nullable_to_non_nullable
as String?,projectId: freezed == projectId ? _self.projectId : projectId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}


}


/// @nodoc
mixin _$PanelQuery {

 DatasourceRef? get datasource; Map<String, dynamic>? get prometheus;@JsonKey(name: 'cloud_monitoring') Map<String, dynamic>? get cloudMonitoring; Map<String, dynamic>? get logs; Map<String, dynamic>? get bigquery; bool get hidden;@JsonKey(name: 'ref_id') String? get refId;
/// Create a copy of PanelQuery
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$PanelQueryCopyWith<PanelQuery> get copyWith => _$PanelQueryCopyWithImpl<PanelQuery>(this as PanelQuery, _$identity);

  /// Serializes this PanelQuery to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is PanelQuery&&(identical(other.datasource, datasource) || other.datasource == datasource)&&const DeepCollectionEquality().equals(other.prometheus, prometheus)&&const DeepCollectionEquality().equals(other.cloudMonitoring, cloudMonitoring)&&const DeepCollectionEquality().equals(other.logs, logs)&&const DeepCollectionEquality().equals(other.bigquery, bigquery)&&(identical(other.hidden, hidden) || other.hidden == hidden)&&(identical(other.refId, refId) || other.refId == refId));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,datasource,const DeepCollectionEquality().hash(prometheus),const DeepCollectionEquality().hash(cloudMonitoring),const DeepCollectionEquality().hash(logs),const DeepCollectionEquality().hash(bigquery),hidden,refId);

@override
String toString() {
  return 'PanelQuery(datasource: $datasource, prometheus: $prometheus, cloudMonitoring: $cloudMonitoring, logs: $logs, bigquery: $bigquery, hidden: $hidden, refId: $refId)';
}


}

/// @nodoc
abstract mixin class $PanelQueryCopyWith<$Res>  {
  factory $PanelQueryCopyWith(PanelQuery value, $Res Function(PanelQuery) _then) = _$PanelQueryCopyWithImpl;
@useResult
$Res call({
 DatasourceRef? datasource, Map<String, dynamic>? prometheus,@JsonKey(name: 'cloud_monitoring') Map<String, dynamic>? cloudMonitoring, Map<String, dynamic>? logs, Map<String, dynamic>? bigquery, bool hidden,@JsonKey(name: 'ref_id') String? refId
});


$DatasourceRefCopyWith<$Res>? get datasource;

}
/// @nodoc
class _$PanelQueryCopyWithImpl<$Res>
    implements $PanelQueryCopyWith<$Res> {
  _$PanelQueryCopyWithImpl(this._self, this._then);

  final PanelQuery _self;
  final $Res Function(PanelQuery) _then;

/// Create a copy of PanelQuery
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? datasource = freezed,Object? prometheus = freezed,Object? cloudMonitoring = freezed,Object? logs = freezed,Object? bigquery = freezed,Object? hidden = null,Object? refId = freezed,}) {
  return _then(_self.copyWith(
datasource: freezed == datasource ? _self.datasource : datasource // ignore: cast_nullable_to_non_nullable
as DatasourceRef?,prometheus: freezed == prometheus ? _self.prometheus : prometheus // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>?,cloudMonitoring: freezed == cloudMonitoring ? _self.cloudMonitoring : cloudMonitoring // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>?,logs: freezed == logs ? _self.logs : logs // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>?,bigquery: freezed == bigquery ? _self.bigquery : bigquery // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>?,hidden: null == hidden ? _self.hidden : hidden // ignore: cast_nullable_to_non_nullable
as bool,refId: freezed == refId ? _self.refId : refId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}
/// Create a copy of PanelQuery
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$DatasourceRefCopyWith<$Res>? get datasource {
    if (_self.datasource == null) {
    return null;
  }

  return $DatasourceRefCopyWith<$Res>(_self.datasource!, (value) {
    return _then(_self.copyWith(datasource: value));
  });
}
}


/// Adds pattern-matching-related methods to [PanelQuery].
extension PanelQueryPatterns on PanelQuery {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _PanelQuery value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _PanelQuery() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _PanelQuery value)  $default,){
final _that = this;
switch (_that) {
case _PanelQuery():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _PanelQuery value)?  $default,){
final _that = this;
switch (_that) {
case _PanelQuery() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( DatasourceRef? datasource,  Map<String, dynamic>? prometheus, @JsonKey(name: 'cloud_monitoring')  Map<String, dynamic>? cloudMonitoring,  Map<String, dynamic>? logs,  Map<String, dynamic>? bigquery,  bool hidden, @JsonKey(name: 'ref_id')  String? refId)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _PanelQuery() when $default != null:
return $default(_that.datasource,_that.prometheus,_that.cloudMonitoring,_that.logs,_that.bigquery,_that.hidden,_that.refId);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( DatasourceRef? datasource,  Map<String, dynamic>? prometheus, @JsonKey(name: 'cloud_monitoring')  Map<String, dynamic>? cloudMonitoring,  Map<String, dynamic>? logs,  Map<String, dynamic>? bigquery,  bool hidden, @JsonKey(name: 'ref_id')  String? refId)  $default,) {final _that = this;
switch (_that) {
case _PanelQuery():
return $default(_that.datasource,_that.prometheus,_that.cloudMonitoring,_that.logs,_that.bigquery,_that.hidden,_that.refId);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( DatasourceRef? datasource,  Map<String, dynamic>? prometheus, @JsonKey(name: 'cloud_monitoring')  Map<String, dynamic>? cloudMonitoring,  Map<String, dynamic>? logs,  Map<String, dynamic>? bigquery,  bool hidden, @JsonKey(name: 'ref_id')  String? refId)?  $default,) {final _that = this;
switch (_that) {
case _PanelQuery() when $default != null:
return $default(_that.datasource,_that.prometheus,_that.cloudMonitoring,_that.logs,_that.bigquery,_that.hidden,_that.refId);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _PanelQuery implements PanelQuery {
  const _PanelQuery({this.datasource, final  Map<String, dynamic>? prometheus, @JsonKey(name: 'cloud_monitoring') final  Map<String, dynamic>? cloudMonitoring, final  Map<String, dynamic>? logs, final  Map<String, dynamic>? bigquery, this.hidden = false, @JsonKey(name: 'ref_id') this.refId}): _prometheus = prometheus,_cloudMonitoring = cloudMonitoring,_logs = logs,_bigquery = bigquery;
  factory _PanelQuery.fromJson(Map<String, dynamic> json) => _$PanelQueryFromJson(json);

@override final  DatasourceRef? datasource;
 final  Map<String, dynamic>? _prometheus;
@override Map<String, dynamic>? get prometheus {
  final value = _prometheus;
  if (value == null) return null;
  if (_prometheus is EqualUnmodifiableMapView) return _prometheus;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableMapView(value);
}

 final  Map<String, dynamic>? _cloudMonitoring;
@override@JsonKey(name: 'cloud_monitoring') Map<String, dynamic>? get cloudMonitoring {
  final value = _cloudMonitoring;
  if (value == null) return null;
  if (_cloudMonitoring is EqualUnmodifiableMapView) return _cloudMonitoring;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableMapView(value);
}

 final  Map<String, dynamic>? _logs;
@override Map<String, dynamic>? get logs {
  final value = _logs;
  if (value == null) return null;
  if (_logs is EqualUnmodifiableMapView) return _logs;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableMapView(value);
}

 final  Map<String, dynamic>? _bigquery;
@override Map<String, dynamic>? get bigquery {
  final value = _bigquery;
  if (value == null) return null;
  if (_bigquery is EqualUnmodifiableMapView) return _bigquery;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableMapView(value);
}

@override@JsonKey() final  bool hidden;
@override@JsonKey(name: 'ref_id') final  String? refId;

/// Create a copy of PanelQuery
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$PanelQueryCopyWith<_PanelQuery> get copyWith => __$PanelQueryCopyWithImpl<_PanelQuery>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$PanelQueryToJson(this, );
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _PanelQuery&&(identical(other.datasource, datasource) || other.datasource == datasource)&&const DeepCollectionEquality().equals(other._prometheus, _prometheus)&&const DeepCollectionEquality().equals(other._cloudMonitoring, _cloudMonitoring)&&const DeepCollectionEquality().equals(other._logs, _logs)&&const DeepCollectionEquality().equals(other._bigquery, _bigquery)&&(identical(other.hidden, hidden) || other.hidden == hidden)&&(identical(other.refId, refId) || other.refId == refId));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,datasource,const DeepCollectionEquality().hash(_prometheus),const DeepCollectionEquality().hash(_cloudMonitoring),const DeepCollectionEquality().hash(_logs),const DeepCollectionEquality().hash(_bigquery),hidden,refId);

@override
String toString() {
  return 'PanelQuery(datasource: $datasource, prometheus: $prometheus, cloudMonitoring: $cloudMonitoring, logs: $logs, bigquery: $bigquery, hidden: $hidden, refId: $refId)';
}


}

/// @nodoc
abstract mixin class _$PanelQueryCopyWith<$Res> implements $PanelQueryCopyWith<$Res> {
  factory _$PanelQueryCopyWith(_PanelQuery value, $Res Function(_PanelQuery) _then) = __$PanelQueryCopyWithImpl;
@override @useResult
$Res call({
 DatasourceRef? datasource, Map<String, dynamic>? prometheus,@JsonKey(name: 'cloud_monitoring') Map<String, dynamic>? cloudMonitoring, Map<String, dynamic>? logs, Map<String, dynamic>? bigquery, bool hidden,@JsonKey(name: 'ref_id') String? refId
});


@override $DatasourceRefCopyWith<$Res>? get datasource;

}
/// @nodoc
class __$PanelQueryCopyWithImpl<$Res>
    implements _$PanelQueryCopyWith<$Res> {
  __$PanelQueryCopyWithImpl(this._self, this._then);

  final _PanelQuery _self;
  final $Res Function(_PanelQuery) _then;

/// Create a copy of PanelQuery
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? datasource = freezed,Object? prometheus = freezed,Object? cloudMonitoring = freezed,Object? logs = freezed,Object? bigquery = freezed,Object? hidden = null,Object? refId = freezed,}) {
  return _then(_PanelQuery(
datasource: freezed == datasource ? _self.datasource : datasource // ignore: cast_nullable_to_non_nullable
as DatasourceRef?,prometheus: freezed == prometheus ? _self._prometheus : prometheus // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>?,cloudMonitoring: freezed == cloudMonitoring ? _self._cloudMonitoring : cloudMonitoring // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>?,logs: freezed == logs ? _self._logs : logs // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>?,bigquery: freezed == bigquery ? _self._bigquery : bigquery // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>?,hidden: null == hidden ? _self.hidden : hidden // ignore: cast_nullable_to_non_nullable
as bool,refId: freezed == refId ? _self.refId : refId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

/// Create a copy of PanelQuery
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$DatasourceRefCopyWith<$Res>? get datasource {
    if (_self.datasource == null) {
    return null;
  }

  return $DatasourceRefCopyWith<$Res>(_self.datasource!, (value) {
    return _then(_self.copyWith(datasource: value));
  });
}
}


/// @nodoc
mixin _$DashboardPanel {

 String get id; String get title; PanelType get type; String get description;@JsonKey(name: 'grid_position') GridPosition get gridPosition; List<PanelQuery> get queries; List<Map<String, dynamic>> get thresholds; Map<String, dynamic>? get display;@JsonKey(name: 'text_content') Map<String, dynamic>? get textContent; DatasourceRef? get datasource; String? get unit; int? get decimals;@JsonKey(name: 'color_scheme') String? get colorScheme; Map<String, dynamic>? get options;
/// Create a copy of DashboardPanel
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$DashboardPanelCopyWith<DashboardPanel> get copyWith => _$DashboardPanelCopyWithImpl<DashboardPanel>(this as DashboardPanel, _$identity);

  /// Serializes this DashboardPanel to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is DashboardPanel&&(identical(other.id, id) || other.id == id)&&(identical(other.title, title) || other.title == title)&&(identical(other.type, type) || other.type == type)&&(identical(other.description, description) || other.description == description)&&(identical(other.gridPosition, gridPosition) || other.gridPosition == gridPosition)&&const DeepCollectionEquality().equals(other.queries, queries)&&const DeepCollectionEquality().equals(other.thresholds, thresholds)&&const DeepCollectionEquality().equals(other.display, display)&&const DeepCollectionEquality().equals(other.textContent, textContent)&&(identical(other.datasource, datasource) || other.datasource == datasource)&&(identical(other.unit, unit) || other.unit == unit)&&(identical(other.decimals, decimals) || other.decimals == decimals)&&(identical(other.colorScheme, colorScheme) || other.colorScheme == colorScheme)&&const DeepCollectionEquality().equals(other.options, options));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,id,title,type,description,gridPosition,const DeepCollectionEquality().hash(queries),const DeepCollectionEquality().hash(thresholds),const DeepCollectionEquality().hash(display),const DeepCollectionEquality().hash(textContent),datasource,unit,decimals,colorScheme,const DeepCollectionEquality().hash(options));

@override
String toString() {
  return 'DashboardPanel(id: $id, title: $title, type: $type, description: $description, gridPosition: $gridPosition, queries: $queries, thresholds: $thresholds, display: $display, textContent: $textContent, datasource: $datasource, unit: $unit, decimals: $decimals, colorScheme: $colorScheme, options: $options)';
}


}

/// @nodoc
abstract mixin class $DashboardPanelCopyWith<$Res>  {
  factory $DashboardPanelCopyWith(DashboardPanel value, $Res Function(DashboardPanel) _then) = _$DashboardPanelCopyWithImpl;
@useResult
$Res call({
 String id, String title, PanelType type, String description,@JsonKey(name: 'grid_position') GridPosition gridPosition, List<PanelQuery> queries, List<Map<String, dynamic>> thresholds, Map<String, dynamic>? display,@JsonKey(name: 'text_content') Map<String, dynamic>? textContent, DatasourceRef? datasource, String? unit, int? decimals,@JsonKey(name: 'color_scheme') String? colorScheme, Map<String, dynamic>? options
});


$GridPositionCopyWith<$Res> get gridPosition;$DatasourceRefCopyWith<$Res>? get datasource;

}
/// @nodoc
class _$DashboardPanelCopyWithImpl<$Res>
    implements $DashboardPanelCopyWith<$Res> {
  _$DashboardPanelCopyWithImpl(this._self, this._then);

  final DashboardPanel _self;
  final $Res Function(DashboardPanel) _then;

/// Create a copy of DashboardPanel
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? title = null,Object? type = null,Object? description = null,Object? gridPosition = null,Object? queries = null,Object? thresholds = null,Object? display = freezed,Object? textContent = freezed,Object? datasource = freezed,Object? unit = freezed,Object? decimals = freezed,Object? colorScheme = freezed,Object? options = freezed,}) {
  return _then(_self.copyWith(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,type: null == type ? _self.type : type // ignore: cast_nullable_to_non_nullable
as PanelType,description: null == description ? _self.description : description // ignore: cast_nullable_to_non_nullable
as String,gridPosition: null == gridPosition ? _self.gridPosition : gridPosition // ignore: cast_nullable_to_non_nullable
as GridPosition,queries: null == queries ? _self.queries : queries // ignore: cast_nullable_to_non_nullable
as List<PanelQuery>,thresholds: null == thresholds ? _self.thresholds : thresholds // ignore: cast_nullable_to_non_nullable
as List<Map<String, dynamic>>,display: freezed == display ? _self.display : display // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>?,textContent: freezed == textContent ? _self.textContent : textContent // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>?,datasource: freezed == datasource ? _self.datasource : datasource // ignore: cast_nullable_to_non_nullable
as DatasourceRef?,unit: freezed == unit ? _self.unit : unit // ignore: cast_nullable_to_non_nullable
as String?,decimals: freezed == decimals ? _self.decimals : decimals // ignore: cast_nullable_to_non_nullable
as int?,colorScheme: freezed == colorScheme ? _self.colorScheme : colorScheme // ignore: cast_nullable_to_non_nullable
as String?,options: freezed == options ? _self.options : options // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>?,
  ));
}
/// Create a copy of DashboardPanel
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$GridPositionCopyWith<$Res> get gridPosition {

  return $GridPositionCopyWith<$Res>(_self.gridPosition, (value) {
    return _then(_self.copyWith(gridPosition: value));
  });
}/// Create a copy of DashboardPanel
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$DatasourceRefCopyWith<$Res>? get datasource {
    if (_self.datasource == null) {
    return null;
  }

  return $DatasourceRefCopyWith<$Res>(_self.datasource!, (value) {
    return _then(_self.copyWith(datasource: value));
  });
}
}


/// Adds pattern-matching-related methods to [DashboardPanel].
extension DashboardPanelPatterns on DashboardPanel {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _DashboardPanel value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _DashboardPanel() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _DashboardPanel value)  $default,){
final _that = this;
switch (_that) {
case _DashboardPanel():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _DashboardPanel value)?  $default,){
final _that = this;
switch (_that) {
case _DashboardPanel() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id,  String title,  PanelType type,  String description, @JsonKey(name: 'grid_position')  GridPosition gridPosition,  List<PanelQuery> queries,  List<Map<String, dynamic>> thresholds,  Map<String, dynamic>? display, @JsonKey(name: 'text_content')  Map<String, dynamic>? textContent,  DatasourceRef? datasource,  String? unit,  int? decimals, @JsonKey(name: 'color_scheme')  String? colorScheme,  Map<String, dynamic>? options)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _DashboardPanel() when $default != null:
return $default(_that.id,_that.title,_that.type,_that.description,_that.gridPosition,_that.queries,_that.thresholds,_that.display,_that.textContent,_that.datasource,_that.unit,_that.decimals,_that.colorScheme,_that.options);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id,  String title,  PanelType type,  String description, @JsonKey(name: 'grid_position')  GridPosition gridPosition,  List<PanelQuery> queries,  List<Map<String, dynamic>> thresholds,  Map<String, dynamic>? display, @JsonKey(name: 'text_content')  Map<String, dynamic>? textContent,  DatasourceRef? datasource,  String? unit,  int? decimals, @JsonKey(name: 'color_scheme')  String? colorScheme,  Map<String, dynamic>? options)  $default,) {final _that = this;
switch (_that) {
case _DashboardPanel():
return $default(_that.id,_that.title,_that.type,_that.description,_that.gridPosition,_that.queries,_that.thresholds,_that.display,_that.textContent,_that.datasource,_that.unit,_that.decimals,_that.colorScheme,_that.options);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id,  String title,  PanelType type,  String description, @JsonKey(name: 'grid_position')  GridPosition gridPosition,  List<PanelQuery> queries,  List<Map<String, dynamic>> thresholds,  Map<String, dynamic>? display, @JsonKey(name: 'text_content')  Map<String, dynamic>? textContent,  DatasourceRef? datasource,  String? unit,  int? decimals, @JsonKey(name: 'color_scheme')  String? colorScheme,  Map<String, dynamic>? options)?  $default,) {final _that = this;
switch (_that) {
case _DashboardPanel() when $default != null:
return $default(_that.id,_that.title,_that.type,_that.description,_that.gridPosition,_that.queries,_that.thresholds,_that.display,_that.textContent,_that.datasource,_that.unit,_that.decimals,_that.colorScheme,_that.options);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _DashboardPanel implements DashboardPanel {
  const _DashboardPanel({required this.id, required this.title, this.type = PanelType.timeSeries, this.description = '', @JsonKey(name: 'grid_position') this.gridPosition = const GridPosition(), final  List<PanelQuery> queries = const [], final  List<Map<String, dynamic>> thresholds = const [], final  Map<String, dynamic>? display, @JsonKey(name: 'text_content') final  Map<String, dynamic>? textContent, this.datasource, this.unit, this.decimals, @JsonKey(name: 'color_scheme') this.colorScheme, final  Map<String, dynamic>? options}): _queries = queries,_thresholds = thresholds,_display = display,_textContent = textContent,_options = options;
  factory _DashboardPanel.fromJson(Map<String, dynamic> json) => _$DashboardPanelFromJson(json);

@override final  String id;
@override final  String title;
@override@JsonKey() final  PanelType type;
@override@JsonKey() final  String description;
@override@JsonKey(name: 'grid_position') final  GridPosition gridPosition;
 final  List<PanelQuery> _queries;
@override@JsonKey() List<PanelQuery> get queries {
  if (_queries is EqualUnmodifiableListView) return _queries;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_queries);
}

 final  List<Map<String, dynamic>> _thresholds;
@override@JsonKey() List<Map<String, dynamic>> get thresholds {
  if (_thresholds is EqualUnmodifiableListView) return _thresholds;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_thresholds);
}

 final  Map<String, dynamic>? _display;
@override Map<String, dynamic>? get display {
  final value = _display;
  if (value == null) return null;
  if (_display is EqualUnmodifiableMapView) return _display;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableMapView(value);
}

 final  Map<String, dynamic>? _textContent;
@override@JsonKey(name: 'text_content') Map<String, dynamic>? get textContent {
  final value = _textContent;
  if (value == null) return null;
  if (_textContent is EqualUnmodifiableMapView) return _textContent;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableMapView(value);
}

@override final  DatasourceRef? datasource;
@override final  String? unit;
@override final  int? decimals;
@override@JsonKey(name: 'color_scheme') final  String? colorScheme;
 final  Map<String, dynamic>? _options;
@override Map<String, dynamic>? get options {
  final value = _options;
  if (value == null) return null;
  if (_options is EqualUnmodifiableMapView) return _options;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableMapView(value);
}


/// Create a copy of DashboardPanel
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$DashboardPanelCopyWith<_DashboardPanel> get copyWith => __$DashboardPanelCopyWithImpl<_DashboardPanel>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$DashboardPanelToJson(this, );
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _DashboardPanel&&(identical(other.id, id) || other.id == id)&&(identical(other.title, title) || other.title == title)&&(identical(other.type, type) || other.type == type)&&(identical(other.description, description) || other.description == description)&&(identical(other.gridPosition, gridPosition) || other.gridPosition == gridPosition)&&const DeepCollectionEquality().equals(other._queries, _queries)&&const DeepCollectionEquality().equals(other._thresholds, _thresholds)&&const DeepCollectionEquality().equals(other._display, _display)&&const DeepCollectionEquality().equals(other._textContent, _textContent)&&(identical(other.datasource, datasource) || other.datasource == datasource)&&(identical(other.unit, unit) || other.unit == unit)&&(identical(other.decimals, decimals) || other.decimals == decimals)&&(identical(other.colorScheme, colorScheme) || other.colorScheme == colorScheme)&&const DeepCollectionEquality().equals(other._options, _options));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,id,title,type,description,gridPosition,const DeepCollectionEquality().hash(_queries),const DeepCollectionEquality().hash(_thresholds),const DeepCollectionEquality().hash(_display),const DeepCollectionEquality().hash(_textContent),datasource,unit,decimals,colorScheme,const DeepCollectionEquality().hash(_options));

@override
String toString() {
  return 'DashboardPanel(id: $id, title: $title, type: $type, description: $description, gridPosition: $gridPosition, queries: $queries, thresholds: $thresholds, display: $display, textContent: $textContent, datasource: $datasource, unit: $unit, decimals: $decimals, colorScheme: $colorScheme, options: $options)';
}


}

/// @nodoc
abstract mixin class _$DashboardPanelCopyWith<$Res> implements $DashboardPanelCopyWith<$Res> {
  factory _$DashboardPanelCopyWith(_DashboardPanel value, $Res Function(_DashboardPanel) _then) = __$DashboardPanelCopyWithImpl;
@override @useResult
$Res call({
 String id, String title, PanelType type, String description,@JsonKey(name: 'grid_position') GridPosition gridPosition, List<PanelQuery> queries, List<Map<String, dynamic>> thresholds, Map<String, dynamic>? display,@JsonKey(name: 'text_content') Map<String, dynamic>? textContent, DatasourceRef? datasource, String? unit, int? decimals,@JsonKey(name: 'color_scheme') String? colorScheme, Map<String, dynamic>? options
});


@override $GridPositionCopyWith<$Res> get gridPosition;@override $DatasourceRefCopyWith<$Res>? get datasource;

}
/// @nodoc
class __$DashboardPanelCopyWithImpl<$Res>
    implements _$DashboardPanelCopyWith<$Res> {
  __$DashboardPanelCopyWithImpl(this._self, this._then);

  final _DashboardPanel _self;
  final $Res Function(_DashboardPanel) _then;

/// Create a copy of DashboardPanel
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? title = null,Object? type = null,Object? description = null,Object? gridPosition = null,Object? queries = null,Object? thresholds = null,Object? display = freezed,Object? textContent = freezed,Object? datasource = freezed,Object? unit = freezed,Object? decimals = freezed,Object? colorScheme = freezed,Object? options = freezed,}) {
  return _then(_DashboardPanel(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,title: null == title ? _self.title : title // ignore: cast_nullable_to_non_nullable
as String,type: null == type ? _self.type : type // ignore: cast_nullable_to_non_nullable
as PanelType,description: null == description ? _self.description : description // ignore: cast_nullable_to_non_nullable
as String,gridPosition: null == gridPosition ? _self.gridPosition : gridPosition // ignore: cast_nullable_to_non_nullable
as GridPosition,queries: null == queries ? _self._queries : queries // ignore: cast_nullable_to_non_nullable
as List<PanelQuery>,thresholds: null == thresholds ? _self._thresholds : thresholds // ignore: cast_nullable_to_non_nullable
as List<Map<String, dynamic>>,display: freezed == display ? _self._display : display // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>?,textContent: freezed == textContent ? _self._textContent : textContent // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>?,datasource: freezed == datasource ? _self.datasource : datasource // ignore: cast_nullable_to_non_nullable
as DatasourceRef?,unit: freezed == unit ? _self.unit : unit // ignore: cast_nullable_to_non_nullable
as String?,decimals: freezed == decimals ? _self.decimals : decimals // ignore: cast_nullable_to_non_nullable
as int?,colorScheme: freezed == colorScheme ? _self.colorScheme : colorScheme // ignore: cast_nullable_to_non_nullable
as String?,options: freezed == options ? _self._options : options // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>?,
  ));
}

/// Create a copy of DashboardPanel
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$GridPositionCopyWith<$Res> get gridPosition {

  return $GridPositionCopyWith<$Res>(_self.gridPosition, (value) {
    return _then(_self.copyWith(gridPosition: value));
  });
}/// Create a copy of DashboardPanel
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$DatasourceRefCopyWith<$Res>? get datasource {
    if (_self.datasource == null) {
    return null;
  }

  return $DatasourceRefCopyWith<$Res>(_self.datasource!, (value) {
    return _then(_self.copyWith(datasource: value));
  });
}
}


/// @nodoc
mixin _$DashboardVariable {

 String get name; String get type; String? get label; String? get description; String? get query; List<String> get values;@JsonKey(name: 'default_value') String? get defaultValue; bool get multi;@JsonKey(name: 'include_all') bool get includeAll;
/// Create a copy of DashboardVariable
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$DashboardVariableCopyWith<DashboardVariable> get copyWith => _$DashboardVariableCopyWithImpl<DashboardVariable>(this as DashboardVariable, _$identity);

  /// Serializes this DashboardVariable to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is DashboardVariable&&(identical(other.name, name) || other.name == name)&&(identical(other.type, type) || other.type == type)&&(identical(other.label, label) || other.label == label)&&(identical(other.description, description) || other.description == description)&&(identical(other.query, query) || other.query == query)&&const DeepCollectionEquality().equals(other.values, values)&&(identical(other.defaultValue, defaultValue) || other.defaultValue == defaultValue)&&(identical(other.multi, multi) || other.multi == multi)&&(identical(other.includeAll, includeAll) || other.includeAll == includeAll));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,name,type,label,description,query,const DeepCollectionEquality().hash(values),defaultValue,multi,includeAll);

@override
String toString() {
  return 'DashboardVariable(name: $name, type: $type, label: $label, description: $description, query: $query, values: $values, defaultValue: $defaultValue, multi: $multi, includeAll: $includeAll)';
}


}

/// @nodoc
abstract mixin class $DashboardVariableCopyWith<$Res>  {
  factory $DashboardVariableCopyWith(DashboardVariable value, $Res Function(DashboardVariable) _then) = _$DashboardVariableCopyWithImpl;
@useResult
$Res call({
 String name, String type, String? label, String? description, String? query, List<String> values,@JsonKey(name: 'default_value') String? defaultValue, bool multi,@JsonKey(name: 'include_all') bool includeAll
});




}
/// @nodoc
class _$DashboardVariableCopyWithImpl<$Res>
    implements $DashboardVariableCopyWith<$Res> {
  _$DashboardVariableCopyWithImpl(this._self, this._then);

  final DashboardVariable _self;
  final $Res Function(DashboardVariable) _then;

/// Create a copy of DashboardVariable
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? name = null,Object? type = null,Object? label = freezed,Object? description = freezed,Object? query = freezed,Object? values = null,Object? defaultValue = freezed,Object? multi = null,Object? includeAll = null,}) {
  return _then(_self.copyWith(
name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,type: null == type ? _self.type : type // ignore: cast_nullable_to_non_nullable
as String,label: freezed == label ? _self.label : label // ignore: cast_nullable_to_non_nullable
as String?,description: freezed == description ? _self.description : description // ignore: cast_nullable_to_non_nullable
as String?,query: freezed == query ? _self.query : query // ignore: cast_nullable_to_non_nullable
as String?,values: null == values ? _self.values : values // ignore: cast_nullable_to_non_nullable
as List<String>,defaultValue: freezed == defaultValue ? _self.defaultValue : defaultValue // ignore: cast_nullable_to_non_nullable
as String?,multi: null == multi ? _self.multi : multi // ignore: cast_nullable_to_non_nullable
as bool,includeAll: null == includeAll ? _self.includeAll : includeAll // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}

}


/// Adds pattern-matching-related methods to [DashboardVariable].
extension DashboardVariablePatterns on DashboardVariable {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _DashboardVariable value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _DashboardVariable() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _DashboardVariable value)  $default,){
final _that = this;
switch (_that) {
case _DashboardVariable():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _DashboardVariable value)?  $default,){
final _that = this;
switch (_that) {
case _DashboardVariable() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String name,  String type,  String? label,  String? description,  String? query,  List<String> values, @JsonKey(name: 'default_value')  String? defaultValue,  bool multi, @JsonKey(name: 'include_all')  bool includeAll)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _DashboardVariable() when $default != null:
return $default(_that.name,_that.type,_that.label,_that.description,_that.query,_that.values,_that.defaultValue,_that.multi,_that.includeAll);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String name,  String type,  String? label,  String? description,  String? query,  List<String> values, @JsonKey(name: 'default_value')  String? defaultValue,  bool multi, @JsonKey(name: 'include_all')  bool includeAll)  $default,) {final _that = this;
switch (_that) {
case _DashboardVariable():
return $default(_that.name,_that.type,_that.label,_that.description,_that.query,_that.values,_that.defaultValue,_that.multi,_that.includeAll);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String name,  String type,  String? label,  String? description,  String? query,  List<String> values, @JsonKey(name: 'default_value')  String? defaultValue,  bool multi, @JsonKey(name: 'include_all')  bool includeAll)?  $default,) {final _that = this;
switch (_that) {
case _DashboardVariable() when $default != null:
return $default(_that.name,_that.type,_that.label,_that.description,_that.query,_that.values,_that.defaultValue,_that.multi,_that.includeAll);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _DashboardVariable implements DashboardVariable {
  const _DashboardVariable({required this.name, this.type = 'query', this.label, this.description, this.query, final  List<String> values = const [], @JsonKey(name: 'default_value') this.defaultValue, this.multi = false, @JsonKey(name: 'include_all') this.includeAll = false}): _values = values;
  factory _DashboardVariable.fromJson(Map<String, dynamic> json) => _$DashboardVariableFromJson(json);

@override final  String name;
@override@JsonKey() final  String type;
@override final  String? label;
@override final  String? description;
@override final  String? query;
 final  List<String> _values;
@override@JsonKey() List<String> get values {
  if (_values is EqualUnmodifiableListView) return _values;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_values);
}

@override@JsonKey(name: 'default_value') final  String? defaultValue;
@override@JsonKey() final  bool multi;
@override@JsonKey(name: 'include_all') final  bool includeAll;

/// Create a copy of DashboardVariable
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$DashboardVariableCopyWith<_DashboardVariable> get copyWith => __$DashboardVariableCopyWithImpl<_DashboardVariable>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$DashboardVariableToJson(this, );
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _DashboardVariable&&(identical(other.name, name) || other.name == name)&&(identical(other.type, type) || other.type == type)&&(identical(other.label, label) || other.label == label)&&(identical(other.description, description) || other.description == description)&&(identical(other.query, query) || other.query == query)&&const DeepCollectionEquality().equals(other._values, _values)&&(identical(other.defaultValue, defaultValue) || other.defaultValue == defaultValue)&&(identical(other.multi, multi) || other.multi == multi)&&(identical(other.includeAll, includeAll) || other.includeAll == includeAll));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,name,type,label,description,query,const DeepCollectionEquality().hash(_values),defaultValue,multi,includeAll);

@override
String toString() {
  return 'DashboardVariable(name: $name, type: $type, label: $label, description: $description, query: $query, values: $values, defaultValue: $defaultValue, multi: $multi, includeAll: $includeAll)';
}


}

/// @nodoc
abstract mixin class _$DashboardVariableCopyWith<$Res> implements $DashboardVariableCopyWith<$Res> {
  factory _$DashboardVariableCopyWith(_DashboardVariable value, $Res Function(_DashboardVariable) _then) = __$DashboardVariableCopyWithImpl;
@override @useResult
$Res call({
 String name, String type, String? label, String? description, String? query, List<String> values,@JsonKey(name: 'default_value') String? defaultValue, bool multi,@JsonKey(name: 'include_all') bool includeAll
});




}
/// @nodoc
class __$DashboardVariableCopyWithImpl<$Res>
    implements _$DashboardVariableCopyWith<$Res> {
  __$DashboardVariableCopyWithImpl(this._self, this._then);

  final _DashboardVariable _self;
  final $Res Function(_DashboardVariable) _then;

/// Create a copy of DashboardVariable
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? name = null,Object? type = null,Object? label = freezed,Object? description = freezed,Object? query = freezed,Object? values = null,Object? defaultValue = freezed,Object? multi = null,Object? includeAll = null,}) {
  return _then(_DashboardVariable(
name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,type: null == type ? _self.type : type // ignore: cast_nullable_to_non_nullable
as String,label: freezed == label ? _self.label : label // ignore: cast_nullable_to_non_nullable
as String?,description: freezed == description ? _self.description : description // ignore: cast_nullable_to_non_nullable
as String?,query: freezed == query ? _self.query : query // ignore: cast_nullable_to_non_nullable
as String?,values: null == values ? _self._values : values // ignore: cast_nullable_to_non_nullable
as List<String>,defaultValue: freezed == defaultValue ? _self.defaultValue : defaultValue // ignore: cast_nullable_to_non_nullable
as String?,multi: null == multi ? _self.multi : multi // ignore: cast_nullable_to_non_nullable
as bool,includeAll: null == includeAll ? _self.includeAll : includeAll // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}


}


/// @nodoc
mixin _$DashboardFilter {

 String get key; String get value; String get operator; String? get label;
/// Create a copy of DashboardFilter
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$DashboardFilterCopyWith<DashboardFilter> get copyWith => _$DashboardFilterCopyWithImpl<DashboardFilter>(this as DashboardFilter, _$identity);

  /// Serializes this DashboardFilter to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is DashboardFilter&&(identical(other.key, key) || other.key == key)&&(identical(other.value, value) || other.value == value)&&(identical(other.operator, operator) || other.operator == operator)&&(identical(other.label, label) || other.label == label));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,key,value,operator,label);

@override
String toString() {
  return 'DashboardFilter(key: $key, value: $value, operator: $operator, label: $label)';
}


}

/// @nodoc
abstract mixin class $DashboardFilterCopyWith<$Res>  {
  factory $DashboardFilterCopyWith(DashboardFilter value, $Res Function(DashboardFilter) _then) = _$DashboardFilterCopyWithImpl;
@useResult
$Res call({
 String key, String value, String operator, String? label
});




}
/// @nodoc
class _$DashboardFilterCopyWithImpl<$Res>
    implements $DashboardFilterCopyWith<$Res> {
  _$DashboardFilterCopyWithImpl(this._self, this._then);

  final DashboardFilter _self;
  final $Res Function(DashboardFilter) _then;

/// Create a copy of DashboardFilter
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? key = null,Object? value = null,Object? operator = null,Object? label = freezed,}) {
  return _then(_self.copyWith(
key: null == key ? _self.key : key // ignore: cast_nullable_to_non_nullable
as String,value: null == value ? _self.value : value // ignore: cast_nullable_to_non_nullable
as String,operator: null == operator ? _self.operator : operator // ignore: cast_nullable_to_non_nullable
as String,label: freezed == label ? _self.label : label // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

}


/// Adds pattern-matching-related methods to [DashboardFilter].
extension DashboardFilterPatterns on DashboardFilter {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _DashboardFilter value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _DashboardFilter() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _DashboardFilter value)  $default,){
final _that = this;
switch (_that) {
case _DashboardFilter():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _DashboardFilter value)?  $default,){
final _that = this;
switch (_that) {
case _DashboardFilter() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String key,  String value,  String operator,  String? label)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _DashboardFilter() when $default != null:
return $default(_that.key,_that.value,_that.operator,_that.label);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String key,  String value,  String operator,  String? label)  $default,) {final _that = this;
switch (_that) {
case _DashboardFilter():
return $default(_that.key,_that.value,_that.operator,_that.label);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String key,  String value,  String operator,  String? label)?  $default,) {final _that = this;
switch (_that) {
case _DashboardFilter() when $default != null:
return $default(_that.key,_that.value,_that.operator,_that.label);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _DashboardFilter implements DashboardFilter {
  const _DashboardFilter({required this.key, required this.value, this.operator = '=', this.label});
  factory _DashboardFilter.fromJson(Map<String, dynamic> json) => _$DashboardFilterFromJson(json);

@override final  String key;
@override final  String value;
@override@JsonKey() final  String operator;
@override final  String? label;

/// Create a copy of DashboardFilter
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$DashboardFilterCopyWith<_DashboardFilter> get copyWith => __$DashboardFilterCopyWithImpl<_DashboardFilter>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$DashboardFilterToJson(this, );
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _DashboardFilter&&(identical(other.key, key) || other.key == key)&&(identical(other.value, value) || other.value == value)&&(identical(other.operator, operator) || other.operator == operator)&&(identical(other.label, label) || other.label == label));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,key,value,operator,label);

@override
String toString() {
  return 'DashboardFilter(key: $key, value: $value, operator: $operator, label: $label)';
}


}

/// @nodoc
abstract mixin class _$DashboardFilterCopyWith<$Res> implements $DashboardFilterCopyWith<$Res> {
  factory _$DashboardFilterCopyWith(_DashboardFilter value, $Res Function(_DashboardFilter) _then) = __$DashboardFilterCopyWithImpl;
@override @useResult
$Res call({
 String key, String value, String operator, String? label
});




}
/// @nodoc
class __$DashboardFilterCopyWithImpl<$Res>
    implements _$DashboardFilterCopyWith<$Res> {
  __$DashboardFilterCopyWithImpl(this._self, this._then);

  final _DashboardFilter _self;
  final $Res Function(_DashboardFilter) _then;

/// Create a copy of DashboardFilter
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? key = null,Object? value = null,Object? operator = null,Object? label = freezed,}) {
  return _then(_DashboardFilter(
key: null == key ? _self.key : key // ignore: cast_nullable_to_non_nullable
as String,value: null == value ? _self.value : value // ignore: cast_nullable_to_non_nullable
as String,operator: null == operator ? _self.operator : operator // ignore: cast_nullable_to_non_nullable
as String,label: freezed == label ? _self.label : label // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}


}


/// @nodoc
mixin _$DashboardMetadata {

@JsonKey(name: 'created_at') String? get createdAt;@JsonKey(name: 'updated_at') String? get updatedAt;@JsonKey(name: 'created_by') String? get createdBy; int get version; List<String> get tags; bool get starred; String? get folder;
/// Create a copy of DashboardMetadata
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$DashboardMetadataCopyWith<DashboardMetadata> get copyWith => _$DashboardMetadataCopyWithImpl<DashboardMetadata>(this as DashboardMetadata, _$identity);

  /// Serializes this DashboardMetadata to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is DashboardMetadata&&(identical(other.createdAt, createdAt) || other.createdAt == createdAt)&&(identical(other.updatedAt, updatedAt) || other.updatedAt == updatedAt)&&(identical(other.createdBy, createdBy) || other.createdBy == createdBy)&&(identical(other.version, version) || other.version == version)&&const DeepCollectionEquality().equals(other.tags, tags)&&(identical(other.starred, starred) || other.starred == starred)&&(identical(other.folder, folder) || other.folder == folder));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,createdAt,updatedAt,createdBy,version,const DeepCollectionEquality().hash(tags),starred,folder);

@override
String toString() {
  return 'DashboardMetadata(createdAt: $createdAt, updatedAt: $updatedAt, createdBy: $createdBy, version: $version, tags: $tags, starred: $starred, folder: $folder)';
}


}

/// @nodoc
abstract mixin class $DashboardMetadataCopyWith<$Res>  {
  factory $DashboardMetadataCopyWith(DashboardMetadata value, $Res Function(DashboardMetadata) _then) = _$DashboardMetadataCopyWithImpl;
@useResult
$Res call({
@JsonKey(name: 'created_at') String? createdAt,@JsonKey(name: 'updated_at') String? updatedAt,@JsonKey(name: 'created_by') String? createdBy, int version, List<String> tags, bool starred, String? folder
});




}
/// @nodoc
class _$DashboardMetadataCopyWithImpl<$Res>
    implements $DashboardMetadataCopyWith<$Res> {
  _$DashboardMetadataCopyWithImpl(this._self, this._then);

  final DashboardMetadata _self;
  final $Res Function(DashboardMetadata) _then;

/// Create a copy of DashboardMetadata
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? createdAt = freezed,Object? updatedAt = freezed,Object? createdBy = freezed,Object? version = null,Object? tags = null,Object? starred = null,Object? folder = freezed,}) {
  return _then(_self.copyWith(
createdAt: freezed == createdAt ? _self.createdAt : createdAt // ignore: cast_nullable_to_non_nullable
as String?,updatedAt: freezed == updatedAt ? _self.updatedAt : updatedAt // ignore: cast_nullable_to_non_nullable
as String?,createdBy: freezed == createdBy ? _self.createdBy : createdBy // ignore: cast_nullable_to_non_nullable
as String?,version: null == version ? _self.version : version // ignore: cast_nullable_to_non_nullable
as int,tags: null == tags ? _self.tags : tags // ignore: cast_nullable_to_non_nullable
as List<String>,starred: null == starred ? _self.starred : starred // ignore: cast_nullable_to_non_nullable
as bool,folder: freezed == folder ? _self.folder : folder // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

}


/// Adds pattern-matching-related methods to [DashboardMetadata].
extension DashboardMetadataPatterns on DashboardMetadata {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _DashboardMetadata value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _DashboardMetadata() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _DashboardMetadata value)  $default,){
final _that = this;
switch (_that) {
case _DashboardMetadata():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _DashboardMetadata value)?  $default,){
final _that = this;
switch (_that) {
case _DashboardMetadata() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function(@JsonKey(name: 'created_at')  String? createdAt, @JsonKey(name: 'updated_at')  String? updatedAt, @JsonKey(name: 'created_by')  String? createdBy,  int version,  List<String> tags,  bool starred,  String? folder)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _DashboardMetadata() when $default != null:
return $default(_that.createdAt,_that.updatedAt,_that.createdBy,_that.version,_that.tags,_that.starred,_that.folder);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function(@JsonKey(name: 'created_at')  String? createdAt, @JsonKey(name: 'updated_at')  String? updatedAt, @JsonKey(name: 'created_by')  String? createdBy,  int version,  List<String> tags,  bool starred,  String? folder)  $default,) {final _that = this;
switch (_that) {
case _DashboardMetadata():
return $default(_that.createdAt,_that.updatedAt,_that.createdBy,_that.version,_that.tags,_that.starred,_that.folder);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function(@JsonKey(name: 'created_at')  String? createdAt, @JsonKey(name: 'updated_at')  String? updatedAt, @JsonKey(name: 'created_by')  String? createdBy,  int version,  List<String> tags,  bool starred,  String? folder)?  $default,) {final _that = this;
switch (_that) {
case _DashboardMetadata() when $default != null:
return $default(_that.createdAt,_that.updatedAt,_that.createdBy,_that.version,_that.tags,_that.starred,_that.folder);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _DashboardMetadata implements DashboardMetadata {
  const _DashboardMetadata({@JsonKey(name: 'created_at') this.createdAt, @JsonKey(name: 'updated_at') this.updatedAt, @JsonKey(name: 'created_by') this.createdBy, this.version = 1, final  List<String> tags = const [], this.starred = false, this.folder}): _tags = tags;
  factory _DashboardMetadata.fromJson(Map<String, dynamic> json) => _$DashboardMetadataFromJson(json);

@override@JsonKey(name: 'created_at') final  String? createdAt;
@override@JsonKey(name: 'updated_at') final  String? updatedAt;
@override@JsonKey(name: 'created_by') final  String? createdBy;
@override@JsonKey() final  int version;
 final  List<String> _tags;
@override@JsonKey() List<String> get tags {
  if (_tags is EqualUnmodifiableListView) return _tags;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_tags);
}

@override@JsonKey() final  bool starred;
@override final  String? folder;

/// Create a copy of DashboardMetadata
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$DashboardMetadataCopyWith<_DashboardMetadata> get copyWith => __$DashboardMetadataCopyWithImpl<_DashboardMetadata>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$DashboardMetadataToJson(this, );
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _DashboardMetadata&&(identical(other.createdAt, createdAt) || other.createdAt == createdAt)&&(identical(other.updatedAt, updatedAt) || other.updatedAt == updatedAt)&&(identical(other.createdBy, createdBy) || other.createdBy == createdBy)&&(identical(other.version, version) || other.version == version)&&const DeepCollectionEquality().equals(other._tags, _tags)&&(identical(other.starred, starred) || other.starred == starred)&&(identical(other.folder, folder) || other.folder == folder));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,createdAt,updatedAt,createdBy,version,const DeepCollectionEquality().hash(_tags),starred,folder);

@override
String toString() {
  return 'DashboardMetadata(createdAt: $createdAt, updatedAt: $updatedAt, createdBy: $createdBy, version: $version, tags: $tags, starred: $starred, folder: $folder)';
}


}

/// @nodoc
abstract mixin class _$DashboardMetadataCopyWith<$Res> implements $DashboardMetadataCopyWith<$Res> {
  factory _$DashboardMetadataCopyWith(_DashboardMetadata value, $Res Function(_DashboardMetadata) _then) = __$DashboardMetadataCopyWithImpl;
@override @useResult
$Res call({
@JsonKey(name: 'created_at') String? createdAt,@JsonKey(name: 'updated_at') String? updatedAt,@JsonKey(name: 'created_by') String? createdBy, int version, List<String> tags, bool starred, String? folder
});




}
/// @nodoc
class __$DashboardMetadataCopyWithImpl<$Res>
    implements _$DashboardMetadataCopyWith<$Res> {
  __$DashboardMetadataCopyWithImpl(this._self, this._then);

  final _DashboardMetadata _self;
  final $Res Function(_DashboardMetadata) _then;

/// Create a copy of DashboardMetadata
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? createdAt = freezed,Object? updatedAt = freezed,Object? createdBy = freezed,Object? version = null,Object? tags = null,Object? starred = null,Object? folder = freezed,}) {
  return _then(_DashboardMetadata(
createdAt: freezed == createdAt ? _self.createdAt : createdAt // ignore: cast_nullable_to_non_nullable
as String?,updatedAt: freezed == updatedAt ? _self.updatedAt : updatedAt // ignore: cast_nullable_to_non_nullable
as String?,createdBy: freezed == createdBy ? _self.createdBy : createdBy // ignore: cast_nullable_to_non_nullable
as String?,version: null == version ? _self.version : version // ignore: cast_nullable_to_non_nullable
as int,tags: null == tags ? _self._tags : tags // ignore: cast_nullable_to_non_nullable
as List<String>,starred: null == starred ? _self.starred : starred // ignore: cast_nullable_to_non_nullable
as bool,folder: freezed == folder ? _self.folder : folder // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}


}


/// @nodoc
mixin _$Dashboard {

 String get id; String? get name;@JsonKey(name: 'display_name') String get displayName; String get description; DashboardSource get source;@JsonKey(name: 'project_id') String? get projectId; List<DashboardPanel> get panels; List<DashboardVariable> get variables; List<DashboardFilter> get filters;@JsonKey(name: 'time_range') TimeRange get timeRange; Map<String, String> get labels;@JsonKey(name: 'grid_columns') int get gridColumns; DashboardMetadata get metadata;
/// Create a copy of Dashboard
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$DashboardCopyWith<Dashboard> get copyWith => _$DashboardCopyWithImpl<Dashboard>(this as Dashboard, _$identity);

  /// Serializes this Dashboard to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is Dashboard&&(identical(other.id, id) || other.id == id)&&(identical(other.name, name) || other.name == name)&&(identical(other.displayName, displayName) || other.displayName == displayName)&&(identical(other.description, description) || other.description == description)&&(identical(other.source, source) || other.source == source)&&(identical(other.projectId, projectId) || other.projectId == projectId)&&const DeepCollectionEquality().equals(other.panels, panels)&&const DeepCollectionEquality().equals(other.variables, variables)&&const DeepCollectionEquality().equals(other.filters, filters)&&(identical(other.timeRange, timeRange) || other.timeRange == timeRange)&&const DeepCollectionEquality().equals(other.labels, labels)&&(identical(other.gridColumns, gridColumns) || other.gridColumns == gridColumns)&&(identical(other.metadata, metadata) || other.metadata == metadata));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,id,name,displayName,description,source,projectId,const DeepCollectionEquality().hash(panels),const DeepCollectionEquality().hash(variables),const DeepCollectionEquality().hash(filters),timeRange,const DeepCollectionEquality().hash(labels),gridColumns,metadata);

@override
String toString() {
  return 'Dashboard(id: $id, name: $name, displayName: $displayName, description: $description, source: $source, projectId: $projectId, panels: $panels, variables: $variables, filters: $filters, timeRange: $timeRange, labels: $labels, gridColumns: $gridColumns, metadata: $metadata)';
}


}

/// @nodoc
abstract mixin class $DashboardCopyWith<$Res>  {
  factory $DashboardCopyWith(Dashboard value, $Res Function(Dashboard) _then) = _$DashboardCopyWithImpl;
@useResult
$Res call({
 String id, String? name,@JsonKey(name: 'display_name') String displayName, String description, DashboardSource source,@JsonKey(name: 'project_id') String? projectId, List<DashboardPanel> panels, List<DashboardVariable> variables, List<DashboardFilter> filters,@JsonKey(name: 'time_range') TimeRange timeRange, Map<String, String> labels,@JsonKey(name: 'grid_columns') int gridColumns, DashboardMetadata metadata
});


$TimeRangeCopyWith<$Res> get timeRange;$DashboardMetadataCopyWith<$Res> get metadata;

}
/// @nodoc
class _$DashboardCopyWithImpl<$Res>
    implements $DashboardCopyWith<$Res> {
  _$DashboardCopyWithImpl(this._self, this._then);

  final Dashboard _self;
  final $Res Function(Dashboard) _then;

/// Create a copy of Dashboard
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? name = freezed,Object? displayName = null,Object? description = null,Object? source = null,Object? projectId = freezed,Object? panels = null,Object? variables = null,Object? filters = null,Object? timeRange = null,Object? labels = null,Object? gridColumns = null,Object? metadata = null,}) {
  return _then(_self.copyWith(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,name: freezed == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String?,displayName: null == displayName ? _self.displayName : displayName // ignore: cast_nullable_to_non_nullable
as String,description: null == description ? _self.description : description // ignore: cast_nullable_to_non_nullable
as String,source: null == source ? _self.source : source // ignore: cast_nullable_to_non_nullable
as DashboardSource,projectId: freezed == projectId ? _self.projectId : projectId // ignore: cast_nullable_to_non_nullable
as String?,panels: null == panels ? _self.panels : panels // ignore: cast_nullable_to_non_nullable
as List<DashboardPanel>,variables: null == variables ? _self.variables : variables // ignore: cast_nullable_to_non_nullable
as List<DashboardVariable>,filters: null == filters ? _self.filters : filters // ignore: cast_nullable_to_non_nullable
as List<DashboardFilter>,timeRange: null == timeRange ? _self.timeRange : timeRange // ignore: cast_nullable_to_non_nullable
as TimeRange,labels: null == labels ? _self.labels : labels // ignore: cast_nullable_to_non_nullable
as Map<String, String>,gridColumns: null == gridColumns ? _self.gridColumns : gridColumns // ignore: cast_nullable_to_non_nullable
as int,metadata: null == metadata ? _self.metadata : metadata // ignore: cast_nullable_to_non_nullable
as DashboardMetadata,
  ));
}
/// Create a copy of Dashboard
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$TimeRangeCopyWith<$Res> get timeRange {

  return $TimeRangeCopyWith<$Res>(_self.timeRange, (value) {
    return _then(_self.copyWith(timeRange: value));
  });
}/// Create a copy of Dashboard
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$DashboardMetadataCopyWith<$Res> get metadata {

  return $DashboardMetadataCopyWith<$Res>(_self.metadata, (value) {
    return _then(_self.copyWith(metadata: value));
  });
}
}


/// Adds pattern-matching-related methods to [Dashboard].
extension DashboardPatterns on Dashboard {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _Dashboard value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _Dashboard() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _Dashboard value)  $default,){
final _that = this;
switch (_that) {
case _Dashboard():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _Dashboard value)?  $default,){
final _that = this;
switch (_that) {
case _Dashboard() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id,  String? name, @JsonKey(name: 'display_name')  String displayName,  String description,  DashboardSource source, @JsonKey(name: 'project_id')  String? projectId,  List<DashboardPanel> panels,  List<DashboardVariable> variables,  List<DashboardFilter> filters, @JsonKey(name: 'time_range')  TimeRange timeRange,  Map<String, String> labels, @JsonKey(name: 'grid_columns')  int gridColumns,  DashboardMetadata metadata)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _Dashboard() when $default != null:
return $default(_that.id,_that.name,_that.displayName,_that.description,_that.source,_that.projectId,_that.panels,_that.variables,_that.filters,_that.timeRange,_that.labels,_that.gridColumns,_that.metadata);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id,  String? name, @JsonKey(name: 'display_name')  String displayName,  String description,  DashboardSource source, @JsonKey(name: 'project_id')  String? projectId,  List<DashboardPanel> panels,  List<DashboardVariable> variables,  List<DashboardFilter> filters, @JsonKey(name: 'time_range')  TimeRange timeRange,  Map<String, String> labels, @JsonKey(name: 'grid_columns')  int gridColumns,  DashboardMetadata metadata)  $default,) {final _that = this;
switch (_that) {
case _Dashboard():
return $default(_that.id,_that.name,_that.displayName,_that.description,_that.source,_that.projectId,_that.panels,_that.variables,_that.filters,_that.timeRange,_that.labels,_that.gridColumns,_that.metadata);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id,  String? name, @JsonKey(name: 'display_name')  String displayName,  String description,  DashboardSource source, @JsonKey(name: 'project_id')  String? projectId,  List<DashboardPanel> panels,  List<DashboardVariable> variables,  List<DashboardFilter> filters, @JsonKey(name: 'time_range')  TimeRange timeRange,  Map<String, String> labels, @JsonKey(name: 'grid_columns')  int gridColumns,  DashboardMetadata metadata)?  $default,) {final _that = this;
switch (_that) {
case _Dashboard() when $default != null:
return $default(_that.id,_that.name,_that.displayName,_that.description,_that.source,_that.projectId,_that.panels,_that.variables,_that.filters,_that.timeRange,_that.labels,_that.gridColumns,_that.metadata);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _Dashboard implements Dashboard {
  const _Dashboard({required this.id, this.name, @JsonKey(name: 'display_name') required this.displayName, this.description = '', this.source = DashboardSource.local, @JsonKey(name: 'project_id') this.projectId, final  List<DashboardPanel> panels = const [], final  List<DashboardVariable> variables = const [], final  List<DashboardFilter> filters = const [], @JsonKey(name: 'time_range') this.timeRange = const TimeRange(), final  Map<String, String> labels = const {}, @JsonKey(name: 'grid_columns') this.gridColumns = 24, this.metadata = const DashboardMetadata()}): _panels = panels,_variables = variables,_filters = filters,_labels = labels;
  factory _Dashboard.fromJson(Map<String, dynamic> json) => _$DashboardFromJson(json);

@override final  String id;
@override final  String? name;
@override@JsonKey(name: 'display_name') final  String displayName;
@override@JsonKey() final  String description;
@override@JsonKey() final  DashboardSource source;
@override@JsonKey(name: 'project_id') final  String? projectId;
 final  List<DashboardPanel> _panels;
@override@JsonKey() List<DashboardPanel> get panels {
  if (_panels is EqualUnmodifiableListView) return _panels;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_panels);
}

 final  List<DashboardVariable> _variables;
@override@JsonKey() List<DashboardVariable> get variables {
  if (_variables is EqualUnmodifiableListView) return _variables;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_variables);
}

 final  List<DashboardFilter> _filters;
@override@JsonKey() List<DashboardFilter> get filters {
  if (_filters is EqualUnmodifiableListView) return _filters;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_filters);
}

@override@JsonKey(name: 'time_range') final  TimeRange timeRange;
 final  Map<String, String> _labels;
@override@JsonKey() Map<String, String> get labels {
  if (_labels is EqualUnmodifiableMapView) return _labels;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableMapView(_labels);
}

@override@JsonKey(name: 'grid_columns') final  int gridColumns;
@override@JsonKey() final  DashboardMetadata metadata;

/// Create a copy of Dashboard
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$DashboardCopyWith<_Dashboard> get copyWith => __$DashboardCopyWithImpl<_Dashboard>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$DashboardToJson(this, );
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _Dashboard&&(identical(other.id, id) || other.id == id)&&(identical(other.name, name) || other.name == name)&&(identical(other.displayName, displayName) || other.displayName == displayName)&&(identical(other.description, description) || other.description == description)&&(identical(other.source, source) || other.source == source)&&(identical(other.projectId, projectId) || other.projectId == projectId)&&const DeepCollectionEquality().equals(other._panels, _panels)&&const DeepCollectionEquality().equals(other._variables, _variables)&&const DeepCollectionEquality().equals(other._filters, _filters)&&(identical(other.timeRange, timeRange) || other.timeRange == timeRange)&&const DeepCollectionEquality().equals(other._labels, _labels)&&(identical(other.gridColumns, gridColumns) || other.gridColumns == gridColumns)&&(identical(other.metadata, metadata) || other.metadata == metadata));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,id,name,displayName,description,source,projectId,const DeepCollectionEquality().hash(_panels),const DeepCollectionEquality().hash(_variables),const DeepCollectionEquality().hash(_filters),timeRange,const DeepCollectionEquality().hash(_labels),gridColumns,metadata);

@override
String toString() {
  return 'Dashboard(id: $id, name: $name, displayName: $displayName, description: $description, source: $source, projectId: $projectId, panels: $panels, variables: $variables, filters: $filters, timeRange: $timeRange, labels: $labels, gridColumns: $gridColumns, metadata: $metadata)';
}


}

/// @nodoc
abstract mixin class _$DashboardCopyWith<$Res> implements $DashboardCopyWith<$Res> {
  factory _$DashboardCopyWith(_Dashboard value, $Res Function(_Dashboard) _then) = __$DashboardCopyWithImpl;
@override @useResult
$Res call({
 String id, String? name,@JsonKey(name: 'display_name') String displayName, String description, DashboardSource source,@JsonKey(name: 'project_id') String? projectId, List<DashboardPanel> panels, List<DashboardVariable> variables, List<DashboardFilter> filters,@JsonKey(name: 'time_range') TimeRange timeRange, Map<String, String> labels,@JsonKey(name: 'grid_columns') int gridColumns, DashboardMetadata metadata
});


@override $TimeRangeCopyWith<$Res> get timeRange;@override $DashboardMetadataCopyWith<$Res> get metadata;

}
/// @nodoc
class __$DashboardCopyWithImpl<$Res>
    implements _$DashboardCopyWith<$Res> {
  __$DashboardCopyWithImpl(this._self, this._then);

  final _Dashboard _self;
  final $Res Function(_Dashboard) _then;

/// Create a copy of Dashboard
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? name = freezed,Object? displayName = null,Object? description = null,Object? source = null,Object? projectId = freezed,Object? panels = null,Object? variables = null,Object? filters = null,Object? timeRange = null,Object? labels = null,Object? gridColumns = null,Object? metadata = null,}) {
  return _then(_Dashboard(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,name: freezed == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String?,displayName: null == displayName ? _self.displayName : displayName // ignore: cast_nullable_to_non_nullable
as String,description: null == description ? _self.description : description // ignore: cast_nullable_to_non_nullable
as String,source: null == source ? _self.source : source // ignore: cast_nullable_to_non_nullable
as DashboardSource,projectId: freezed == projectId ? _self.projectId : projectId // ignore: cast_nullable_to_non_nullable
as String?,panels: null == panels ? _self._panels : panels // ignore: cast_nullable_to_non_nullable
as List<DashboardPanel>,variables: null == variables ? _self._variables : variables // ignore: cast_nullable_to_non_nullable
as List<DashboardVariable>,filters: null == filters ? _self._filters : filters // ignore: cast_nullable_to_non_nullable
as List<DashboardFilter>,timeRange: null == timeRange ? _self.timeRange : timeRange // ignore: cast_nullable_to_non_nullable
as TimeRange,labels: null == labels ? _self._labels : labels // ignore: cast_nullable_to_non_nullable
as Map<String, String>,gridColumns: null == gridColumns ? _self.gridColumns : gridColumns // ignore: cast_nullable_to_non_nullable
as int,metadata: null == metadata ? _self.metadata : metadata // ignore: cast_nullable_to_non_nullable
as DashboardMetadata,
  ));
}

/// Create a copy of Dashboard
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$TimeRangeCopyWith<$Res> get timeRange {

  return $TimeRangeCopyWith<$Res>(_self.timeRange, (value) {
    return _then(_self.copyWith(timeRange: value));
  });
}/// Create a copy of Dashboard
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$DashboardMetadataCopyWith<$Res> get metadata {

  return $DashboardMetadataCopyWith<$Res>(_self.metadata, (value) {
    return _then(_self.copyWith(metadata: value));
  });
}
}


/// @nodoc
mixin _$DashboardSummary {

 String get id;@JsonKey(name: 'display_name') String get displayName; String get description; DashboardSource get source;@JsonKey(name: 'panel_count') int get panelCount; DashboardMetadata? get metadata; Map<String, String> get labels;
/// Create a copy of DashboardSummary
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$DashboardSummaryCopyWith<DashboardSummary> get copyWith => _$DashboardSummaryCopyWithImpl<DashboardSummary>(this as DashboardSummary, _$identity);

  /// Serializes this DashboardSummary to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is DashboardSummary&&(identical(other.id, id) || other.id == id)&&(identical(other.displayName, displayName) || other.displayName == displayName)&&(identical(other.description, description) || other.description == description)&&(identical(other.source, source) || other.source == source)&&(identical(other.panelCount, panelCount) || other.panelCount == panelCount)&&(identical(other.metadata, metadata) || other.metadata == metadata)&&const DeepCollectionEquality().equals(other.labels, labels));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,id,displayName,description,source,panelCount,metadata,const DeepCollectionEquality().hash(labels));

@override
String toString() {
  return 'DashboardSummary(id: $id, displayName: $displayName, description: $description, source: $source, panelCount: $panelCount, metadata: $metadata, labels: $labels)';
}


}

/// @nodoc
abstract mixin class $DashboardSummaryCopyWith<$Res>  {
  factory $DashboardSummaryCopyWith(DashboardSummary value, $Res Function(DashboardSummary) _then) = _$DashboardSummaryCopyWithImpl;
@useResult
$Res call({
 String id,@JsonKey(name: 'display_name') String displayName, String description, DashboardSource source,@JsonKey(name: 'panel_count') int panelCount, DashboardMetadata? metadata, Map<String, String> labels
});


$DashboardMetadataCopyWith<$Res>? get metadata;

}
/// @nodoc
class _$DashboardSummaryCopyWithImpl<$Res>
    implements $DashboardSummaryCopyWith<$Res> {
  _$DashboardSummaryCopyWithImpl(this._self, this._then);

  final DashboardSummary _self;
  final $Res Function(DashboardSummary) _then;

/// Create a copy of DashboardSummary
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? displayName = null,Object? description = null,Object? source = null,Object? panelCount = null,Object? metadata = freezed,Object? labels = null,}) {
  return _then(_self.copyWith(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,displayName: null == displayName ? _self.displayName : displayName // ignore: cast_nullable_to_non_nullable
as String,description: null == description ? _self.description : description // ignore: cast_nullable_to_non_nullable
as String,source: null == source ? _self.source : source // ignore: cast_nullable_to_non_nullable
as DashboardSource,panelCount: null == panelCount ? _self.panelCount : panelCount // ignore: cast_nullable_to_non_nullable
as int,metadata: freezed == metadata ? _self.metadata : metadata // ignore: cast_nullable_to_non_nullable
as DashboardMetadata?,labels: null == labels ? _self.labels : labels // ignore: cast_nullable_to_non_nullable
as Map<String, String>,
  ));
}
/// Create a copy of DashboardSummary
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$DashboardMetadataCopyWith<$Res>? get metadata {
    if (_self.metadata == null) {
    return null;
  }

  return $DashboardMetadataCopyWith<$Res>(_self.metadata!, (value) {
    return _then(_self.copyWith(metadata: value));
  });
}
}


/// Adds pattern-matching-related methods to [DashboardSummary].
extension DashboardSummaryPatterns on DashboardSummary {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _DashboardSummary value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _DashboardSummary() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _DashboardSummary value)  $default,){
final _that = this;
switch (_that) {
case _DashboardSummary():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _DashboardSummary value)?  $default,){
final _that = this;
switch (_that) {
case _DashboardSummary() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id, @JsonKey(name: 'display_name')  String displayName,  String description,  DashboardSource source, @JsonKey(name: 'panel_count')  int panelCount,  DashboardMetadata? metadata,  Map<String, String> labels)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _DashboardSummary() when $default != null:
return $default(_that.id,_that.displayName,_that.description,_that.source,_that.panelCount,_that.metadata,_that.labels);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id, @JsonKey(name: 'display_name')  String displayName,  String description,  DashboardSource source, @JsonKey(name: 'panel_count')  int panelCount,  DashboardMetadata? metadata,  Map<String, String> labels)  $default,) {final _that = this;
switch (_that) {
case _DashboardSummary():
return $default(_that.id,_that.displayName,_that.description,_that.source,_that.panelCount,_that.metadata,_that.labels);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id, @JsonKey(name: 'display_name')  String displayName,  String description,  DashboardSource source, @JsonKey(name: 'panel_count')  int panelCount,  DashboardMetadata? metadata,  Map<String, String> labels)?  $default,) {final _that = this;
switch (_that) {
case _DashboardSummary() when $default != null:
return $default(_that.id,_that.displayName,_that.description,_that.source,_that.panelCount,_that.metadata,_that.labels);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _DashboardSummary implements DashboardSummary {
  const _DashboardSummary({required this.id, @JsonKey(name: 'display_name') required this.displayName, this.description = '', this.source = DashboardSource.local, @JsonKey(name: 'panel_count') this.panelCount = 0, this.metadata, final  Map<String, String> labels = const {}}): _labels = labels;
  factory _DashboardSummary.fromJson(Map<String, dynamic> json) => _$DashboardSummaryFromJson(json);

@override final  String id;
@override@JsonKey(name: 'display_name') final  String displayName;
@override@JsonKey() final  String description;
@override@JsonKey() final  DashboardSource source;
@override@JsonKey(name: 'panel_count') final  int panelCount;
@override final  DashboardMetadata? metadata;
 final  Map<String, String> _labels;
@override@JsonKey() Map<String, String> get labels {
  if (_labels is EqualUnmodifiableMapView) return _labels;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableMapView(_labels);
}


/// Create a copy of DashboardSummary
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$DashboardSummaryCopyWith<_DashboardSummary> get copyWith => __$DashboardSummaryCopyWithImpl<_DashboardSummary>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$DashboardSummaryToJson(this, );
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _DashboardSummary&&(identical(other.id, id) || other.id == id)&&(identical(other.displayName, displayName) || other.displayName == displayName)&&(identical(other.description, description) || other.description == description)&&(identical(other.source, source) || other.source == source)&&(identical(other.panelCount, panelCount) || other.panelCount == panelCount)&&(identical(other.metadata, metadata) || other.metadata == metadata)&&const DeepCollectionEquality().equals(other._labels, _labels));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,id,displayName,description,source,panelCount,metadata,const DeepCollectionEquality().hash(_labels));

@override
String toString() {
  return 'DashboardSummary(id: $id, displayName: $displayName, description: $description, source: $source, panelCount: $panelCount, metadata: $metadata, labels: $labels)';
}


}

/// @nodoc
abstract mixin class _$DashboardSummaryCopyWith<$Res> implements $DashboardSummaryCopyWith<$Res> {
  factory _$DashboardSummaryCopyWith(_DashboardSummary value, $Res Function(_DashboardSummary) _then) = __$DashboardSummaryCopyWithImpl;
@override @useResult
$Res call({
 String id,@JsonKey(name: 'display_name') String displayName, String description, DashboardSource source,@JsonKey(name: 'panel_count') int panelCount, DashboardMetadata? metadata, Map<String, String> labels
});


@override $DashboardMetadataCopyWith<$Res>? get metadata;

}
/// @nodoc
class __$DashboardSummaryCopyWithImpl<$Res>
    implements _$DashboardSummaryCopyWith<$Res> {
  __$DashboardSummaryCopyWithImpl(this._self, this._then);

  final _DashboardSummary _self;
  final $Res Function(_DashboardSummary) _then;

/// Create a copy of DashboardSummary
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? displayName = null,Object? description = null,Object? source = null,Object? panelCount = null,Object? metadata = freezed,Object? labels = null,}) {
  return _then(_DashboardSummary(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,displayName: null == displayName ? _self.displayName : displayName // ignore: cast_nullable_to_non_nullable
as String,description: null == description ? _self.description : description // ignore: cast_nullable_to_non_nullable
as String,source: null == source ? _self.source : source // ignore: cast_nullable_to_non_nullable
as DashboardSource,panelCount: null == panelCount ? _self.panelCount : panelCount // ignore: cast_nullable_to_non_nullable
as int,metadata: freezed == metadata ? _self.metadata : metadata // ignore: cast_nullable_to_non_nullable
as DashboardMetadata?,labels: null == labels ? _self._labels : labels // ignore: cast_nullable_to_non_nullable
as Map<String, String>,
  ));
}

/// Create a copy of DashboardSummary
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$DashboardMetadataCopyWith<$Res>? get metadata {
    if (_self.metadata == null) {
    return null;
  }

  return $DashboardMetadataCopyWith<$Res>(_self.metadata!, (value) {
    return _then(_self.copyWith(metadata: value));
  });
}
}

// dart format on
