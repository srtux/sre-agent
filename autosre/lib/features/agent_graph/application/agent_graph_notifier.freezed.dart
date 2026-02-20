// GENERATED CODE - DO NOT MODIFY BY HAND
// coverage:ignore-file
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'agent_graph_notifier.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

// dart format off
T _$identity<T>(T value) => value;
/// @nodoc
mixin _$AgentGraphState {

 MultiTraceGraphPayload? get payload; bool get isLoading; String? get error; SelectedGraphElement? get selectedElement; String get dataset; int get timeRangeHours; int? get sampleLimit;
/// Create a copy of AgentGraphState
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$AgentGraphStateCopyWith<AgentGraphState> get copyWith => _$AgentGraphStateCopyWithImpl<AgentGraphState>(this as AgentGraphState, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is AgentGraphState&&(identical(other.payload, payload) || other.payload == payload)&&(identical(other.isLoading, isLoading) || other.isLoading == isLoading)&&(identical(other.error, error) || other.error == error)&&(identical(other.selectedElement, selectedElement) || other.selectedElement == selectedElement)&&(identical(other.dataset, dataset) || other.dataset == dataset)&&(identical(other.timeRangeHours, timeRangeHours) || other.timeRangeHours == timeRangeHours)&&(identical(other.sampleLimit, sampleLimit) || other.sampleLimit == sampleLimit));
}


@override
int get hashCode => Object.hash(runtimeType,payload,isLoading,error,selectedElement,dataset,timeRangeHours,sampleLimit);

@override
String toString() {
  return 'AgentGraphState(payload: $payload, isLoading: $isLoading, error: $error, selectedElement: $selectedElement, dataset: $dataset, timeRangeHours: $timeRangeHours, sampleLimit: $sampleLimit)';
}


}

/// @nodoc
abstract mixin class $AgentGraphStateCopyWith<$Res>  {
  factory $AgentGraphStateCopyWith(AgentGraphState value, $Res Function(AgentGraphState) _then) = _$AgentGraphStateCopyWithImpl;
@useResult
$Res call({
 MultiTraceGraphPayload? payload, bool isLoading, String? error, SelectedGraphElement? selectedElement, String dataset, int timeRangeHours, int? sampleLimit
});


$MultiTraceGraphPayloadCopyWith<$Res>? get payload;$SelectedGraphElementCopyWith<$Res>? get selectedElement;

}
/// @nodoc
class _$AgentGraphStateCopyWithImpl<$Res>
    implements $AgentGraphStateCopyWith<$Res> {
  _$AgentGraphStateCopyWithImpl(this._self, this._then);

  final AgentGraphState _self;
  final $Res Function(AgentGraphState) _then;

/// Create a copy of AgentGraphState
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? payload = freezed,Object? isLoading = null,Object? error = freezed,Object? selectedElement = freezed,Object? dataset = null,Object? timeRangeHours = null,Object? sampleLimit = freezed,}) {
  return _then(_self.copyWith(
payload: freezed == payload ? _self.payload : payload // ignore: cast_nullable_to_non_nullable
as MultiTraceGraphPayload?,isLoading: null == isLoading ? _self.isLoading : isLoading // ignore: cast_nullable_to_non_nullable
as bool,error: freezed == error ? _self.error : error // ignore: cast_nullable_to_non_nullable
as String?,selectedElement: freezed == selectedElement ? _self.selectedElement : selectedElement // ignore: cast_nullable_to_non_nullable
as SelectedGraphElement?,dataset: null == dataset ? _self.dataset : dataset // ignore: cast_nullable_to_non_nullable
as String,timeRangeHours: null == timeRangeHours ? _self.timeRangeHours : timeRangeHours // ignore: cast_nullable_to_non_nullable
as int,sampleLimit: freezed == sampleLimit ? _self.sampleLimit : sampleLimit // ignore: cast_nullable_to_non_nullable
as int?,
  ));
}
/// Create a copy of AgentGraphState
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$MultiTraceGraphPayloadCopyWith<$Res>? get payload {
    if (_self.payload == null) {
    return null;
  }

  return $MultiTraceGraphPayloadCopyWith<$Res>(_self.payload!, (value) {
    return _then(_self.copyWith(payload: value));
  });
}/// Create a copy of AgentGraphState
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SelectedGraphElementCopyWith<$Res>? get selectedElement {
    if (_self.selectedElement == null) {
    return null;
  }

  return $SelectedGraphElementCopyWith<$Res>(_self.selectedElement!, (value) {
    return _then(_self.copyWith(selectedElement: value));
  });
}
}


/// Adds pattern-matching-related methods to [AgentGraphState].
extension AgentGraphStatePatterns on AgentGraphState {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _AgentGraphState value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _AgentGraphState() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _AgentGraphState value)  $default,){
final _that = this;
switch (_that) {
case _AgentGraphState():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _AgentGraphState value)?  $default,){
final _that = this;
switch (_that) {
case _AgentGraphState() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( MultiTraceGraphPayload? payload,  bool isLoading,  String? error,  SelectedGraphElement? selectedElement,  String dataset,  int timeRangeHours,  int? sampleLimit)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _AgentGraphState() when $default != null:
return $default(_that.payload,_that.isLoading,_that.error,_that.selectedElement,_that.dataset,_that.timeRangeHours,_that.sampleLimit);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( MultiTraceGraphPayload? payload,  bool isLoading,  String? error,  SelectedGraphElement? selectedElement,  String dataset,  int timeRangeHours,  int? sampleLimit)  $default,) {final _that = this;
switch (_that) {
case _AgentGraphState():
return $default(_that.payload,_that.isLoading,_that.error,_that.selectedElement,_that.dataset,_that.timeRangeHours,_that.sampleLimit);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( MultiTraceGraphPayload? payload,  bool isLoading,  String? error,  SelectedGraphElement? selectedElement,  String dataset,  int timeRangeHours,  int? sampleLimit)?  $default,) {final _that = this;
switch (_that) {
case _AgentGraphState() when $default != null:
return $default(_that.payload,_that.isLoading,_that.error,_that.selectedElement,_that.dataset,_that.timeRangeHours,_that.sampleLimit);case _:
  return null;

}
}

}

/// @nodoc


class _AgentGraphState implements AgentGraphState {
  const _AgentGraphState({this.payload = null, this.isLoading = false, this.error, this.selectedElement = null, this.dataset = kDefaultDataset, this.timeRangeHours = 6, this.sampleLimit = null});


@override@JsonKey() final  MultiTraceGraphPayload? payload;
@override@JsonKey() final  bool isLoading;
@override final  String? error;
@override@JsonKey() final  SelectedGraphElement? selectedElement;
@override@JsonKey() final  String dataset;
@override@JsonKey() final  int timeRangeHours;
@override@JsonKey() final  int? sampleLimit;

/// Create a copy of AgentGraphState
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$AgentGraphStateCopyWith<_AgentGraphState> get copyWith => __$AgentGraphStateCopyWithImpl<_AgentGraphState>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _AgentGraphState&&(identical(other.payload, payload) || other.payload == payload)&&(identical(other.isLoading, isLoading) || other.isLoading == isLoading)&&(identical(other.error, error) || other.error == error)&&(identical(other.selectedElement, selectedElement) || other.selectedElement == selectedElement)&&(identical(other.dataset, dataset) || other.dataset == dataset)&&(identical(other.timeRangeHours, timeRangeHours) || other.timeRangeHours == timeRangeHours)&&(identical(other.sampleLimit, sampleLimit) || other.sampleLimit == sampleLimit));
}


@override
int get hashCode => Object.hash(runtimeType,payload,isLoading,error,selectedElement,dataset,timeRangeHours,sampleLimit);

@override
String toString() {
  return 'AgentGraphState(payload: $payload, isLoading: $isLoading, error: $error, selectedElement: $selectedElement, dataset: $dataset, timeRangeHours: $timeRangeHours, sampleLimit: $sampleLimit)';
}


}

/// @nodoc
abstract mixin class _$AgentGraphStateCopyWith<$Res> implements $AgentGraphStateCopyWith<$Res> {
  factory _$AgentGraphStateCopyWith(_AgentGraphState value, $Res Function(_AgentGraphState) _then) = __$AgentGraphStateCopyWithImpl;
@override @useResult
$Res call({
 MultiTraceGraphPayload? payload, bool isLoading, String? error, SelectedGraphElement? selectedElement, String dataset, int timeRangeHours, int? sampleLimit
});


@override $MultiTraceGraphPayloadCopyWith<$Res>? get payload;@override $SelectedGraphElementCopyWith<$Res>? get selectedElement;

}
/// @nodoc
class __$AgentGraphStateCopyWithImpl<$Res>
    implements _$AgentGraphStateCopyWith<$Res> {
  __$AgentGraphStateCopyWithImpl(this._self, this._then);

  final _AgentGraphState _self;
  final $Res Function(_AgentGraphState) _then;

/// Create a copy of AgentGraphState
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? payload = freezed,Object? isLoading = null,Object? error = freezed,Object? selectedElement = freezed,Object? dataset = null,Object? timeRangeHours = null,Object? sampleLimit = freezed,}) {
  return _then(_AgentGraphState(
payload: freezed == payload ? _self.payload : payload // ignore: cast_nullable_to_non_nullable
as MultiTraceGraphPayload?,isLoading: null == isLoading ? _self.isLoading : isLoading // ignore: cast_nullable_to_non_nullable
as bool,error: freezed == error ? _self.error : error // ignore: cast_nullable_to_non_nullable
as String?,selectedElement: freezed == selectedElement ? _self.selectedElement : selectedElement // ignore: cast_nullable_to_non_nullable
as SelectedGraphElement?,dataset: null == dataset ? _self.dataset : dataset // ignore: cast_nullable_to_non_nullable
as String,timeRangeHours: null == timeRangeHours ? _self.timeRangeHours : timeRangeHours // ignore: cast_nullable_to_non_nullable
as int,sampleLimit: freezed == sampleLimit ? _self.sampleLimit : sampleLimit // ignore: cast_nullable_to_non_nullable
as int?,
  ));
}

/// Create a copy of AgentGraphState
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$MultiTraceGraphPayloadCopyWith<$Res>? get payload {
    if (_self.payload == null) {
    return null;
  }

  return $MultiTraceGraphPayloadCopyWith<$Res>(_self.payload!, (value) {
    return _then(_self.copyWith(payload: value));
  });
}/// Create a copy of AgentGraphState
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$SelectedGraphElementCopyWith<$Res>? get selectedElement {
    if (_self.selectedElement == null) {
    return null;
  }

  return $SelectedGraphElementCopyWith<$Res>(_self.selectedElement!, (value) {
    return _then(_self.copyWith(selectedElement: value));
  });
}
}

// dart format on
