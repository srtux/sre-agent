// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'log_notifier.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$LogNotifierState {

 List<LogEntry> get entries; bool get isLoading; String? get error;/// Timestamp of the oldest loaded entry; used as the cursor for
/// loading older entries (cursor-based pagination).
 DateTime? get oldestEntryTimestamp; String? get oldestEntryInsertId; bool get noMoreOldEntries; String? get currentFilter; String? get projectId;
/// Create a copy of LogNotifierState
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$LogNotifierStateCopyWith<LogNotifierState> get copyWith => _$LogNotifierStateCopyWithImpl<LogNotifierState>(this as LogNotifierState, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is LogNotifierState&&const DeepCollectionEquality().equals(other.entries, entries)&&(identical(other.isLoading, isLoading) || other.isLoading == isLoading)&&(identical(other.error, error) || other.error == error)&&(identical(other.oldestEntryTimestamp, oldestEntryTimestamp) || other.oldestEntryTimestamp == oldestEntryTimestamp)&&(identical(other.oldestEntryInsertId, oldestEntryInsertId) || other.oldestEntryInsertId == oldestEntryInsertId)&&(identical(other.noMoreOldEntries, noMoreOldEntries) || other.noMoreOldEntries == noMoreOldEntries)&&(identical(other.currentFilter, currentFilter) || other.currentFilter == currentFilter)&&(identical(other.projectId, projectId) || other.projectId == projectId));
}


@override
int get hashCode => Object.hash(runtimeType,const DeepCollectionEquality().hash(entries),isLoading,error,oldestEntryTimestamp,oldestEntryInsertId,noMoreOldEntries,currentFilter,projectId);

@override
String toString() {
  return 'LogNotifierState(entries: $entries, isLoading: $isLoading, error: $error, oldestEntryTimestamp: $oldestEntryTimestamp, oldestEntryInsertId: $oldestEntryInsertId, noMoreOldEntries: $noMoreOldEntries, currentFilter: $currentFilter, projectId: $projectId)';
}


}

/// @nodoc
abstract mixin class $LogNotifierStateCopyWith<$Res>  {
  factory $LogNotifierStateCopyWith(LogNotifierState value, $Res Function(LogNotifierState) _then) = _$LogNotifierStateCopyWithImpl;
@useResult
$Res call({
 List<LogEntry> entries, bool isLoading, String? error, DateTime? oldestEntryTimestamp, String? oldestEntryInsertId, bool noMoreOldEntries, String? currentFilter, String? projectId
});




}
/// @nodoc
class _$LogNotifierStateCopyWithImpl<$Res>
    implements $LogNotifierStateCopyWith<$Res> {
  _$LogNotifierStateCopyWithImpl(this._self, this._then);

  final LogNotifierState _self;
  final $Res Function(LogNotifierState) _then;

/// Create a copy of LogNotifierState
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? entries = null,Object? isLoading = null,Object? error = freezed,Object? oldestEntryTimestamp = freezed,Object? oldestEntryInsertId = freezed,Object? noMoreOldEntries = null,Object? currentFilter = freezed,Object? projectId = freezed,}) {
  return _then(_self.copyWith(
entries: null == entries ? _self.entries : entries // ignore: cast_nullable_to_non_nullable
as List<LogEntry>,isLoading: null == isLoading ? _self.isLoading : isLoading // ignore: cast_nullable_to_non_nullable
as bool,error: freezed == error ? _self.error : error // ignore: cast_nullable_to_non_nullable
as String?,oldestEntryTimestamp: freezed == oldestEntryTimestamp ? _self.oldestEntryTimestamp : oldestEntryTimestamp // ignore: cast_nullable_to_non_nullable
as DateTime?,oldestEntryInsertId: freezed == oldestEntryInsertId ? _self.oldestEntryInsertId : oldestEntryInsertId // ignore: cast_nullable_to_non_nullable
as String?,noMoreOldEntries: null == noMoreOldEntries ? _self.noMoreOldEntries : noMoreOldEntries // ignore: cast_nullable_to_non_nullable
as bool,currentFilter: freezed == currentFilter ? _self.currentFilter : currentFilter // ignore: cast_nullable_to_non_nullable
as String?,projectId: freezed == projectId ? _self.projectId : projectId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

}


/// Adds pattern-matching-related methods to [LogNotifierState].
extension LogNotifierStatePatterns on LogNotifierState {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _LogNotifierState value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _LogNotifierState() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _LogNotifierState value)  $default,){
final _that = this;
switch (_that) {
case _LogNotifierState():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _LogNotifierState value)?  $default,){
final _that = this;
switch (_that) {
case _LogNotifierState() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( List<LogEntry> entries,  bool isLoading,  String? error,  DateTime? oldestEntryTimestamp,  String? oldestEntryInsertId,  bool noMoreOldEntries,  String? currentFilter,  String? projectId)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _LogNotifierState() when $default != null:
return $default(_that.entries,_that.isLoading,_that.error,_that.oldestEntryTimestamp,_that.oldestEntryInsertId,_that.noMoreOldEntries,_that.currentFilter,_that.projectId);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( List<LogEntry> entries,  bool isLoading,  String? error,  DateTime? oldestEntryTimestamp,  String? oldestEntryInsertId,  bool noMoreOldEntries,  String? currentFilter,  String? projectId)  $default,) {final _that = this;
switch (_that) {
case _LogNotifierState():
return $default(_that.entries,_that.isLoading,_that.error,_that.oldestEntryTimestamp,_that.oldestEntryInsertId,_that.noMoreOldEntries,_that.currentFilter,_that.projectId);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( List<LogEntry> entries,  bool isLoading,  String? error,  DateTime? oldestEntryTimestamp,  String? oldestEntryInsertId,  bool noMoreOldEntries,  String? currentFilter,  String? projectId)?  $default,) {final _that = this;
switch (_that) {
case _LogNotifierState() when $default != null:
return $default(_that.entries,_that.isLoading,_that.error,_that.oldestEntryTimestamp,_that.oldestEntryInsertId,_that.noMoreOldEntries,_that.currentFilter,_that.projectId);case _:
  return null;

}
}

}

/// @nodoc


class _LogNotifierState implements LogNotifierState {
  const _LogNotifierState({final  List<LogEntry> entries = const [], this.isLoading = false, this.error, this.oldestEntryTimestamp, this.oldestEntryInsertId, this.noMoreOldEntries = false, this.currentFilter, this.projectId}): _entries = entries;


 final  List<LogEntry> _entries;
@override@JsonKey() List<LogEntry> get entries {
  if (_entries is EqualUnmodifiableListView) return _entries;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_entries);
}

@override@JsonKey() final  bool isLoading;
@override final  String? error;
/// Timestamp of the oldest loaded entry; used as the cursor for
/// loading older entries (cursor-based pagination).
@override final  DateTime? oldestEntryTimestamp;
@override final  String? oldestEntryInsertId;
@override@JsonKey() final  bool noMoreOldEntries;
@override final  String? currentFilter;
@override final  String? projectId;

/// Create a copy of LogNotifierState
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$LogNotifierStateCopyWith<_LogNotifierState> get copyWith => __$LogNotifierStateCopyWithImpl<_LogNotifierState>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _LogNotifierState&&const DeepCollectionEquality().equals(other._entries, _entries)&&(identical(other.isLoading, isLoading) || other.isLoading == isLoading)&&(identical(other.error, error) || other.error == error)&&(identical(other.oldestEntryTimestamp, oldestEntryTimestamp) || other.oldestEntryTimestamp == oldestEntryTimestamp)&&(identical(other.oldestEntryInsertId, oldestEntryInsertId) || other.oldestEntryInsertId == oldestEntryInsertId)&&(identical(other.noMoreOldEntries, noMoreOldEntries) || other.noMoreOldEntries == noMoreOldEntries)&&(identical(other.currentFilter, currentFilter) || other.currentFilter == currentFilter)&&(identical(other.projectId, projectId) || other.projectId == projectId));
}


@override
int get hashCode => Object.hash(runtimeType,const DeepCollectionEquality().hash(_entries),isLoading,error,oldestEntryTimestamp,oldestEntryInsertId,noMoreOldEntries,currentFilter,projectId);

@override
String toString() {
  return 'LogNotifierState(entries: $entries, isLoading: $isLoading, error: $error, oldestEntryTimestamp: $oldestEntryTimestamp, oldestEntryInsertId: $oldestEntryInsertId, noMoreOldEntries: $noMoreOldEntries, currentFilter: $currentFilter, projectId: $projectId)';
}


}

/// @nodoc
abstract mixin class _$LogNotifierStateCopyWith<$Res> implements $LogNotifierStateCopyWith<$Res> {
  factory _$LogNotifierStateCopyWith(_LogNotifierState value, $Res Function(_LogNotifierState) _then) = __$LogNotifierStateCopyWithImpl;
@override @useResult
$Res call({
 List<LogEntry> entries, bool isLoading, String? error, DateTime? oldestEntryTimestamp, String? oldestEntryInsertId, bool noMoreOldEntries, String? currentFilter, String? projectId
});




}
/// @nodoc
class __$LogNotifierStateCopyWithImpl<$Res>
    implements _$LogNotifierStateCopyWith<$Res> {
  __$LogNotifierStateCopyWithImpl(this._self, this._then);

  final _LogNotifierState _self;
  final $Res Function(_LogNotifierState) _then;

/// Create a copy of LogNotifierState
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? entries = null,Object? isLoading = null,Object? error = freezed,Object? oldestEntryTimestamp = freezed,Object? oldestEntryInsertId = freezed,Object? noMoreOldEntries = null,Object? currentFilter = freezed,Object? projectId = freezed,}) {
  return _then(_LogNotifierState(
entries: null == entries ? _self._entries : entries // ignore: cast_nullable_to_non_nullable
as List<LogEntry>,isLoading: null == isLoading ? _self.isLoading : isLoading // ignore: cast_nullable_to_non_nullable
as bool,error: freezed == error ? _self.error : error // ignore: cast_nullable_to_non_nullable
as String?,oldestEntryTimestamp: freezed == oldestEntryTimestamp ? _self.oldestEntryTimestamp : oldestEntryTimestamp // ignore: cast_nullable_to_non_nullable
as DateTime?,oldestEntryInsertId: freezed == oldestEntryInsertId ? _self.oldestEntryInsertId : oldestEntryInsertId // ignore: cast_nullable_to_non_nullable
as String?,noMoreOldEntries: null == noMoreOldEntries ? _self.noMoreOldEntries : noMoreOldEntries // ignore: cast_nullable_to_non_nullable
as bool,currentFilter: freezed == currentFilter ? _self.currentFilter : currentFilter // ignore: cast_nullable_to_non_nullable
as String?,projectId: freezed == projectId ? _self.projectId : projectId // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}


}

// dart format on
