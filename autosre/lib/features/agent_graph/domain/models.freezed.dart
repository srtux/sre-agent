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
mixin _$MultiTraceNode {

 String get id; String get type; String? get label; String? get description;@JsonKey(name: 'execution_count') int get executionCount;@JsonKey(name: 'total_tokens') int get totalTokens;@JsonKey(name: 'error_count') int get errorCount;@JsonKey(name: 'has_error') bool get hasError;@JsonKey(name: 'avg_duration_ms') double get avgDurationMs;@JsonKey(name: 'error_rate_pct') double get errorRatePct;@JsonKey(name: 'unique_sessions') int get uniqueSessions;@JsonKey(name: 'is_root') bool get isRoot;@JsonKey(name: 'is_leaf') bool get isLeaf;
/// Create a copy of MultiTraceNode
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$MultiTraceNodeCopyWith<MultiTraceNode> get copyWith => _$MultiTraceNodeCopyWithImpl<MultiTraceNode>(this as MultiTraceNode, _$identity);

  /// Serializes this MultiTraceNode to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is MultiTraceNode&&(identical(other.id, id) || other.id == id)&&(identical(other.type, type) || other.type == type)&&(identical(other.label, label) || other.label == label)&&(identical(other.description, description) || other.description == description)&&(identical(other.executionCount, executionCount) || other.executionCount == executionCount)&&(identical(other.totalTokens, totalTokens) || other.totalTokens == totalTokens)&&(identical(other.errorCount, errorCount) || other.errorCount == errorCount)&&(identical(other.hasError, hasError) || other.hasError == hasError)&&(identical(other.avgDurationMs, avgDurationMs) || other.avgDurationMs == avgDurationMs)&&(identical(other.errorRatePct, errorRatePct) || other.errorRatePct == errorRatePct)&&(identical(other.uniqueSessions, uniqueSessions) || other.uniqueSessions == uniqueSessions)&&(identical(other.isRoot, isRoot) || other.isRoot == isRoot)&&(identical(other.isLeaf, isLeaf) || other.isLeaf == isLeaf));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,id,type,label,description,executionCount,totalTokens,errorCount,hasError,avgDurationMs,errorRatePct,uniqueSessions,isRoot,isLeaf);

@override
String toString() {
  return 'MultiTraceNode(id: $id, type: $type, label: $label, description: $description, executionCount: $executionCount, totalTokens: $totalTokens, errorCount: $errorCount, hasError: $hasError, avgDurationMs: $avgDurationMs, errorRatePct: $errorRatePct, uniqueSessions: $uniqueSessions, isRoot: $isRoot, isLeaf: $isLeaf)';
}


}

/// @nodoc
abstract mixin class $MultiTraceNodeCopyWith<$Res>  {
  factory $MultiTraceNodeCopyWith(MultiTraceNode value, $Res Function(MultiTraceNode) _then) = _$MultiTraceNodeCopyWithImpl;
@useResult
$Res call({
 String id, String type, String? label, String? description,@JsonKey(name: 'execution_count') int executionCount,@JsonKey(name: 'total_tokens') int totalTokens,@JsonKey(name: 'error_count') int errorCount,@JsonKey(name: 'has_error') bool hasError,@JsonKey(name: 'avg_duration_ms') double avgDurationMs,@JsonKey(name: 'error_rate_pct') double errorRatePct,@JsonKey(name: 'unique_sessions') int uniqueSessions,@JsonKey(name: 'is_root') bool isRoot,@JsonKey(name: 'is_leaf') bool isLeaf
});




}
/// @nodoc
class _$MultiTraceNodeCopyWithImpl<$Res>
    implements $MultiTraceNodeCopyWith<$Res> {
  _$MultiTraceNodeCopyWithImpl(this._self, this._then);

  final MultiTraceNode _self;
  final $Res Function(MultiTraceNode) _then;

/// Create a copy of MultiTraceNode
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? type = null,Object? label = freezed,Object? description = freezed,Object? executionCount = null,Object? totalTokens = null,Object? errorCount = null,Object? hasError = null,Object? avgDurationMs = null,Object? errorRatePct = null,Object? uniqueSessions = null,Object? isRoot = null,Object? isLeaf = null,}) {
  return _then(_self.copyWith(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,type: null == type ? _self.type : type // ignore: cast_nullable_to_non_nullable
as String,label: freezed == label ? _self.label : label // ignore: cast_nullable_to_non_nullable
as String?,description: freezed == description ? _self.description : description // ignore: cast_nullable_to_non_nullable
as String?,executionCount: null == executionCount ? _self.executionCount : executionCount // ignore: cast_nullable_to_non_nullable
as int,totalTokens: null == totalTokens ? _self.totalTokens : totalTokens // ignore: cast_nullable_to_non_nullable
as int,errorCount: null == errorCount ? _self.errorCount : errorCount // ignore: cast_nullable_to_non_nullable
as int,hasError: null == hasError ? _self.hasError : hasError // ignore: cast_nullable_to_non_nullable
as bool,avgDurationMs: null == avgDurationMs ? _self.avgDurationMs : avgDurationMs // ignore: cast_nullable_to_non_nullable
as double,errorRatePct: null == errorRatePct ? _self.errorRatePct : errorRatePct // ignore: cast_nullable_to_non_nullable
as double,uniqueSessions: null == uniqueSessions ? _self.uniqueSessions : uniqueSessions // ignore: cast_nullable_to_non_nullable
as int,isRoot: null == isRoot ? _self.isRoot : isRoot // ignore: cast_nullable_to_non_nullable
as bool,isLeaf: null == isLeaf ? _self.isLeaf : isLeaf // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}

}


/// Adds pattern-matching-related methods to [MultiTraceNode].
extension MultiTraceNodePatterns on MultiTraceNode {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _MultiTraceNode value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _MultiTraceNode() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _MultiTraceNode value)  $default,){
final _that = this;
switch (_that) {
case _MultiTraceNode():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _MultiTraceNode value)?  $default,){
final _that = this;
switch (_that) {
case _MultiTraceNode() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id,  String type,  String? label,  String? description, @JsonKey(name: 'execution_count')  int executionCount, @JsonKey(name: 'total_tokens')  int totalTokens, @JsonKey(name: 'error_count')  int errorCount, @JsonKey(name: 'has_error')  bool hasError, @JsonKey(name: 'avg_duration_ms')  double avgDurationMs, @JsonKey(name: 'error_rate_pct')  double errorRatePct, @JsonKey(name: 'unique_sessions')  int uniqueSessions, @JsonKey(name: 'is_root')  bool isRoot, @JsonKey(name: 'is_leaf')  bool isLeaf)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _MultiTraceNode() when $default != null:
return $default(_that.id,_that.type,_that.label,_that.description,_that.executionCount,_that.totalTokens,_that.errorCount,_that.hasError,_that.avgDurationMs,_that.errorRatePct,_that.uniqueSessions,_that.isRoot,_that.isLeaf);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id,  String type,  String? label,  String? description, @JsonKey(name: 'execution_count')  int executionCount, @JsonKey(name: 'total_tokens')  int totalTokens, @JsonKey(name: 'error_count')  int errorCount, @JsonKey(name: 'has_error')  bool hasError, @JsonKey(name: 'avg_duration_ms')  double avgDurationMs, @JsonKey(name: 'error_rate_pct')  double errorRatePct, @JsonKey(name: 'unique_sessions')  int uniqueSessions, @JsonKey(name: 'is_root')  bool isRoot, @JsonKey(name: 'is_leaf')  bool isLeaf)  $default,) {final _that = this;
switch (_that) {
case _MultiTraceNode():
return $default(_that.id,_that.type,_that.label,_that.description,_that.executionCount,_that.totalTokens,_that.errorCount,_that.hasError,_that.avgDurationMs,_that.errorRatePct,_that.uniqueSessions,_that.isRoot,_that.isLeaf);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id,  String type,  String? label,  String? description, @JsonKey(name: 'execution_count')  int executionCount, @JsonKey(name: 'total_tokens')  int totalTokens, @JsonKey(name: 'error_count')  int errorCount, @JsonKey(name: 'has_error')  bool hasError, @JsonKey(name: 'avg_duration_ms')  double avgDurationMs, @JsonKey(name: 'error_rate_pct')  double errorRatePct, @JsonKey(name: 'unique_sessions')  int uniqueSessions, @JsonKey(name: 'is_root')  bool isRoot, @JsonKey(name: 'is_leaf')  bool isLeaf)?  $default,) {final _that = this;
switch (_that) {
case _MultiTraceNode() when $default != null:
return $default(_that.id,_that.type,_that.label,_that.description,_that.executionCount,_that.totalTokens,_that.errorCount,_that.hasError,_that.avgDurationMs,_that.errorRatePct,_that.uniqueSessions,_that.isRoot,_that.isLeaf);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _MultiTraceNode implements MultiTraceNode {
  const _MultiTraceNode({required this.id, required this.type, this.label, this.description, @JsonKey(name: 'execution_count') this.executionCount = 0, @JsonKey(name: 'total_tokens') this.totalTokens = 0, @JsonKey(name: 'error_count') this.errorCount = 0, @JsonKey(name: 'has_error') this.hasError = false, @JsonKey(name: 'avg_duration_ms') this.avgDurationMs = 0.0, @JsonKey(name: 'error_rate_pct') this.errorRatePct = 0.0, @JsonKey(name: 'unique_sessions') this.uniqueSessions = 0, @JsonKey(name: 'is_root') this.isRoot = false, @JsonKey(name: 'is_leaf') this.isLeaf = false});
  factory _MultiTraceNode.fromJson(Map<String, dynamic> json) => _$MultiTraceNodeFromJson(json);

@override final  String id;
@override final  String type;
@override final  String? label;
@override final  String? description;
@override@JsonKey(name: 'execution_count') final  int executionCount;
@override@JsonKey(name: 'total_tokens') final  int totalTokens;
@override@JsonKey(name: 'error_count') final  int errorCount;
@override@JsonKey(name: 'has_error') final  bool hasError;
@override@JsonKey(name: 'avg_duration_ms') final  double avgDurationMs;
@override@JsonKey(name: 'error_rate_pct') final  double errorRatePct;
@override@JsonKey(name: 'unique_sessions') final  int uniqueSessions;
@override@JsonKey(name: 'is_root') final  bool isRoot;
@override@JsonKey(name: 'is_leaf') final  bool isLeaf;

/// Create a copy of MultiTraceNode
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$MultiTraceNodeCopyWith<_MultiTraceNode> get copyWith => __$MultiTraceNodeCopyWithImpl<_MultiTraceNode>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$MultiTraceNodeToJson(this, );
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _MultiTraceNode&&(identical(other.id, id) || other.id == id)&&(identical(other.type, type) || other.type == type)&&(identical(other.label, label) || other.label == label)&&(identical(other.description, description) || other.description == description)&&(identical(other.executionCount, executionCount) || other.executionCount == executionCount)&&(identical(other.totalTokens, totalTokens) || other.totalTokens == totalTokens)&&(identical(other.errorCount, errorCount) || other.errorCount == errorCount)&&(identical(other.hasError, hasError) || other.hasError == hasError)&&(identical(other.avgDurationMs, avgDurationMs) || other.avgDurationMs == avgDurationMs)&&(identical(other.errorRatePct, errorRatePct) || other.errorRatePct == errorRatePct)&&(identical(other.uniqueSessions, uniqueSessions) || other.uniqueSessions == uniqueSessions)&&(identical(other.isRoot, isRoot) || other.isRoot == isRoot)&&(identical(other.isLeaf, isLeaf) || other.isLeaf == isLeaf));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,id,type,label,description,executionCount,totalTokens,errorCount,hasError,avgDurationMs,errorRatePct,uniqueSessions,isRoot,isLeaf);

@override
String toString() {
  return 'MultiTraceNode(id: $id, type: $type, label: $label, description: $description, executionCount: $executionCount, totalTokens: $totalTokens, errorCount: $errorCount, hasError: $hasError, avgDurationMs: $avgDurationMs, errorRatePct: $errorRatePct, uniqueSessions: $uniqueSessions, isRoot: $isRoot, isLeaf: $isLeaf)';
}


}

/// @nodoc
abstract mixin class _$MultiTraceNodeCopyWith<$Res> implements $MultiTraceNodeCopyWith<$Res> {
  factory _$MultiTraceNodeCopyWith(_MultiTraceNode value, $Res Function(_MultiTraceNode) _then) = __$MultiTraceNodeCopyWithImpl;
@override @useResult
$Res call({
 String id, String type, String? label, String? description,@JsonKey(name: 'execution_count') int executionCount,@JsonKey(name: 'total_tokens') int totalTokens,@JsonKey(name: 'error_count') int errorCount,@JsonKey(name: 'has_error') bool hasError,@JsonKey(name: 'avg_duration_ms') double avgDurationMs,@JsonKey(name: 'error_rate_pct') double errorRatePct,@JsonKey(name: 'unique_sessions') int uniqueSessions,@JsonKey(name: 'is_root') bool isRoot,@JsonKey(name: 'is_leaf') bool isLeaf
});




}
/// @nodoc
class __$MultiTraceNodeCopyWithImpl<$Res>
    implements _$MultiTraceNodeCopyWith<$Res> {
  __$MultiTraceNodeCopyWithImpl(this._self, this._then);

  final _MultiTraceNode _self;
  final $Res Function(_MultiTraceNode) _then;

/// Create a copy of MultiTraceNode
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? type = null,Object? label = freezed,Object? description = freezed,Object? executionCount = null,Object? totalTokens = null,Object? errorCount = null,Object? hasError = null,Object? avgDurationMs = null,Object? errorRatePct = null,Object? uniqueSessions = null,Object? isRoot = null,Object? isLeaf = null,}) {
  return _then(_MultiTraceNode(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,type: null == type ? _self.type : type // ignore: cast_nullable_to_non_nullable
as String,label: freezed == label ? _self.label : label // ignore: cast_nullable_to_non_nullable
as String?,description: freezed == description ? _self.description : description // ignore: cast_nullable_to_non_nullable
as String?,executionCount: null == executionCount ? _self.executionCount : executionCount // ignore: cast_nullable_to_non_nullable
as int,totalTokens: null == totalTokens ? _self.totalTokens : totalTokens // ignore: cast_nullable_to_non_nullable
as int,errorCount: null == errorCount ? _self.errorCount : errorCount // ignore: cast_nullable_to_non_nullable
as int,hasError: null == hasError ? _self.hasError : hasError // ignore: cast_nullable_to_non_nullable
as bool,avgDurationMs: null == avgDurationMs ? _self.avgDurationMs : avgDurationMs // ignore: cast_nullable_to_non_nullable
as double,errorRatePct: null == errorRatePct ? _self.errorRatePct : errorRatePct // ignore: cast_nullable_to_non_nullable
as double,uniqueSessions: null == uniqueSessions ? _self.uniqueSessions : uniqueSessions // ignore: cast_nullable_to_non_nullable
as int,isRoot: null == isRoot ? _self.isRoot : isRoot // ignore: cast_nullable_to_non_nullable
as bool,isLeaf: null == isLeaf ? _self.isLeaf : isLeaf // ignore: cast_nullable_to_non_nullable
as bool,
  ));
}


}


/// @nodoc
mixin _$MultiTraceEdge {

@JsonKey(name: 'source_id') String get sourceId;@JsonKey(name: 'target_id') String get targetId;@JsonKey(name: 'source_type') String get sourceType;@JsonKey(name: 'target_type') String get targetType;@JsonKey(name: 'call_count') int get callCount;@JsonKey(name: 'error_count') int get errorCount;@JsonKey(name: 'error_rate_pct') double get errorRatePct;@JsonKey(name: 'sample_error') String? get sampleError;@JsonKey(name: 'total_tokens') int get edgeTokens;@JsonKey(name: 'avg_tokens_per_call') int get avgTokensPerCall;@JsonKey(name: 'avg_duration_ms') double get avgDurationMs;@JsonKey(name: 'p95_duration_ms') double get p95DurationMs;@JsonKey(name: 'unique_sessions') int get uniqueSessions;
/// Create a copy of MultiTraceEdge
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$MultiTraceEdgeCopyWith<MultiTraceEdge> get copyWith => _$MultiTraceEdgeCopyWithImpl<MultiTraceEdge>(this as MultiTraceEdge, _$identity);

  /// Serializes this MultiTraceEdge to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is MultiTraceEdge&&(identical(other.sourceId, sourceId) || other.sourceId == sourceId)&&(identical(other.targetId, targetId) || other.targetId == targetId)&&(identical(other.sourceType, sourceType) || other.sourceType == sourceType)&&(identical(other.targetType, targetType) || other.targetType == targetType)&&(identical(other.callCount, callCount) || other.callCount == callCount)&&(identical(other.errorCount, errorCount) || other.errorCount == errorCount)&&(identical(other.errorRatePct, errorRatePct) || other.errorRatePct == errorRatePct)&&(identical(other.sampleError, sampleError) || other.sampleError == sampleError)&&(identical(other.edgeTokens, edgeTokens) || other.edgeTokens == edgeTokens)&&(identical(other.avgTokensPerCall, avgTokensPerCall) || other.avgTokensPerCall == avgTokensPerCall)&&(identical(other.avgDurationMs, avgDurationMs) || other.avgDurationMs == avgDurationMs)&&(identical(other.p95DurationMs, p95DurationMs) || other.p95DurationMs == p95DurationMs)&&(identical(other.uniqueSessions, uniqueSessions) || other.uniqueSessions == uniqueSessions));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,sourceId,targetId,sourceType,targetType,callCount,errorCount,errorRatePct,sampleError,edgeTokens,avgTokensPerCall,avgDurationMs,p95DurationMs,uniqueSessions);

@override
String toString() {
  return 'MultiTraceEdge(sourceId: $sourceId, targetId: $targetId, sourceType: $sourceType, targetType: $targetType, callCount: $callCount, errorCount: $errorCount, errorRatePct: $errorRatePct, sampleError: $sampleError, edgeTokens: $edgeTokens, avgTokensPerCall: $avgTokensPerCall, avgDurationMs: $avgDurationMs, p95DurationMs: $p95DurationMs, uniqueSessions: $uniqueSessions)';
}


}

/// @nodoc
abstract mixin class $MultiTraceEdgeCopyWith<$Res>  {
  factory $MultiTraceEdgeCopyWith(MultiTraceEdge value, $Res Function(MultiTraceEdge) _then) = _$MultiTraceEdgeCopyWithImpl;
@useResult
$Res call({
@JsonKey(name: 'source_id') String sourceId,@JsonKey(name: 'target_id') String targetId,@JsonKey(name: 'source_type') String sourceType,@JsonKey(name: 'target_type') String targetType,@JsonKey(name: 'call_count') int callCount,@JsonKey(name: 'error_count') int errorCount,@JsonKey(name: 'error_rate_pct') double errorRatePct,@JsonKey(name: 'sample_error') String? sampleError,@JsonKey(name: 'total_tokens') int edgeTokens,@JsonKey(name: 'avg_tokens_per_call') int avgTokensPerCall,@JsonKey(name: 'avg_duration_ms') double avgDurationMs,@JsonKey(name: 'p95_duration_ms') double p95DurationMs,@JsonKey(name: 'unique_sessions') int uniqueSessions
});




}
/// @nodoc
class _$MultiTraceEdgeCopyWithImpl<$Res>
    implements $MultiTraceEdgeCopyWith<$Res> {
  _$MultiTraceEdgeCopyWithImpl(this._self, this._then);

  final MultiTraceEdge _self;
  final $Res Function(MultiTraceEdge) _then;

/// Create a copy of MultiTraceEdge
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? sourceId = null,Object? targetId = null,Object? sourceType = null,Object? targetType = null,Object? callCount = null,Object? errorCount = null,Object? errorRatePct = null,Object? sampleError = freezed,Object? edgeTokens = null,Object? avgTokensPerCall = null,Object? avgDurationMs = null,Object? p95DurationMs = null,Object? uniqueSessions = null,}) {
  return _then(_self.copyWith(
sourceId: null == sourceId ? _self.sourceId : sourceId // ignore: cast_nullable_to_non_nullable
as String,targetId: null == targetId ? _self.targetId : targetId // ignore: cast_nullable_to_non_nullable
as String,sourceType: null == sourceType ? _self.sourceType : sourceType // ignore: cast_nullable_to_non_nullable
as String,targetType: null == targetType ? _self.targetType : targetType // ignore: cast_nullable_to_non_nullable
as String,callCount: null == callCount ? _self.callCount : callCount // ignore: cast_nullable_to_non_nullable
as int,errorCount: null == errorCount ? _self.errorCount : errorCount // ignore: cast_nullable_to_non_nullable
as int,errorRatePct: null == errorRatePct ? _self.errorRatePct : errorRatePct // ignore: cast_nullable_to_non_nullable
as double,sampleError: freezed == sampleError ? _self.sampleError : sampleError // ignore: cast_nullable_to_non_nullable
as String?,edgeTokens: null == edgeTokens ? _self.edgeTokens : edgeTokens // ignore: cast_nullable_to_non_nullable
as int,avgTokensPerCall: null == avgTokensPerCall ? _self.avgTokensPerCall : avgTokensPerCall // ignore: cast_nullable_to_non_nullable
as int,avgDurationMs: null == avgDurationMs ? _self.avgDurationMs : avgDurationMs // ignore: cast_nullable_to_non_nullable
as double,p95DurationMs: null == p95DurationMs ? _self.p95DurationMs : p95DurationMs // ignore: cast_nullable_to_non_nullable
as double,uniqueSessions: null == uniqueSessions ? _self.uniqueSessions : uniqueSessions // ignore: cast_nullable_to_non_nullable
as int,
  ));
}

}


/// Adds pattern-matching-related methods to [MultiTraceEdge].
extension MultiTraceEdgePatterns on MultiTraceEdge {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _MultiTraceEdge value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _MultiTraceEdge() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _MultiTraceEdge value)  $default,){
final _that = this;
switch (_that) {
case _MultiTraceEdge():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _MultiTraceEdge value)?  $default,){
final _that = this;
switch (_that) {
case _MultiTraceEdge() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function(@JsonKey(name: 'source_id')  String sourceId, @JsonKey(name: 'target_id')  String targetId, @JsonKey(name: 'source_type')  String sourceType, @JsonKey(name: 'target_type')  String targetType, @JsonKey(name: 'call_count')  int callCount, @JsonKey(name: 'error_count')  int errorCount, @JsonKey(name: 'error_rate_pct')  double errorRatePct, @JsonKey(name: 'sample_error')  String? sampleError, @JsonKey(name: 'total_tokens')  int edgeTokens, @JsonKey(name: 'avg_tokens_per_call')  int avgTokensPerCall, @JsonKey(name: 'avg_duration_ms')  double avgDurationMs, @JsonKey(name: 'p95_duration_ms')  double p95DurationMs, @JsonKey(name: 'unique_sessions')  int uniqueSessions)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _MultiTraceEdge() when $default != null:
return $default(_that.sourceId,_that.targetId,_that.sourceType,_that.targetType,_that.callCount,_that.errorCount,_that.errorRatePct,_that.sampleError,_that.edgeTokens,_that.avgTokensPerCall,_that.avgDurationMs,_that.p95DurationMs,_that.uniqueSessions);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function(@JsonKey(name: 'source_id')  String sourceId, @JsonKey(name: 'target_id')  String targetId, @JsonKey(name: 'source_type')  String sourceType, @JsonKey(name: 'target_type')  String targetType, @JsonKey(name: 'call_count')  int callCount, @JsonKey(name: 'error_count')  int errorCount, @JsonKey(name: 'error_rate_pct')  double errorRatePct, @JsonKey(name: 'sample_error')  String? sampleError, @JsonKey(name: 'total_tokens')  int edgeTokens, @JsonKey(name: 'avg_tokens_per_call')  int avgTokensPerCall, @JsonKey(name: 'avg_duration_ms')  double avgDurationMs, @JsonKey(name: 'p95_duration_ms')  double p95DurationMs, @JsonKey(name: 'unique_sessions')  int uniqueSessions)  $default,) {final _that = this;
switch (_that) {
case _MultiTraceEdge():
return $default(_that.sourceId,_that.targetId,_that.sourceType,_that.targetType,_that.callCount,_that.errorCount,_that.errorRatePct,_that.sampleError,_that.edgeTokens,_that.avgTokensPerCall,_that.avgDurationMs,_that.p95DurationMs,_that.uniqueSessions);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function(@JsonKey(name: 'source_id')  String sourceId, @JsonKey(name: 'target_id')  String targetId, @JsonKey(name: 'source_type')  String sourceType, @JsonKey(name: 'target_type')  String targetType, @JsonKey(name: 'call_count')  int callCount, @JsonKey(name: 'error_count')  int errorCount, @JsonKey(name: 'error_rate_pct')  double errorRatePct, @JsonKey(name: 'sample_error')  String? sampleError, @JsonKey(name: 'total_tokens')  int edgeTokens, @JsonKey(name: 'avg_tokens_per_call')  int avgTokensPerCall, @JsonKey(name: 'avg_duration_ms')  double avgDurationMs, @JsonKey(name: 'p95_duration_ms')  double p95DurationMs, @JsonKey(name: 'unique_sessions')  int uniqueSessions)?  $default,) {final _that = this;
switch (_that) {
case _MultiTraceEdge() when $default != null:
return $default(_that.sourceId,_that.targetId,_that.sourceType,_that.targetType,_that.callCount,_that.errorCount,_that.errorRatePct,_that.sampleError,_that.edgeTokens,_that.avgTokensPerCall,_that.avgDurationMs,_that.p95DurationMs,_that.uniqueSessions);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _MultiTraceEdge implements MultiTraceEdge {
  const _MultiTraceEdge({@JsonKey(name: 'source_id') required this.sourceId, @JsonKey(name: 'target_id') required this.targetId, @JsonKey(name: 'source_type') this.sourceType = '', @JsonKey(name: 'target_type') this.targetType = '', @JsonKey(name: 'call_count') this.callCount = 0, @JsonKey(name: 'error_count') this.errorCount = 0, @JsonKey(name: 'error_rate_pct') this.errorRatePct = 0.0, @JsonKey(name: 'sample_error') this.sampleError, @JsonKey(name: 'total_tokens') this.edgeTokens = 0, @JsonKey(name: 'avg_tokens_per_call') this.avgTokensPerCall = 0, @JsonKey(name: 'avg_duration_ms') this.avgDurationMs = 0.0, @JsonKey(name: 'p95_duration_ms') this.p95DurationMs = 0.0, @JsonKey(name: 'unique_sessions') this.uniqueSessions = 0});
  factory _MultiTraceEdge.fromJson(Map<String, dynamic> json) => _$MultiTraceEdgeFromJson(json);

@override@JsonKey(name: 'source_id') final  String sourceId;
@override@JsonKey(name: 'target_id') final  String targetId;
@override@JsonKey(name: 'source_type') final  String sourceType;
@override@JsonKey(name: 'target_type') final  String targetType;
@override@JsonKey(name: 'call_count') final  int callCount;
@override@JsonKey(name: 'error_count') final  int errorCount;
@override@JsonKey(name: 'error_rate_pct') final  double errorRatePct;
@override@JsonKey(name: 'sample_error') final  String? sampleError;
@override@JsonKey(name: 'total_tokens') final  int edgeTokens;
@override@JsonKey(name: 'avg_tokens_per_call') final  int avgTokensPerCall;
@override@JsonKey(name: 'avg_duration_ms') final  double avgDurationMs;
@override@JsonKey(name: 'p95_duration_ms') final  double p95DurationMs;
@override@JsonKey(name: 'unique_sessions') final  int uniqueSessions;

/// Create a copy of MultiTraceEdge
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$MultiTraceEdgeCopyWith<_MultiTraceEdge> get copyWith => __$MultiTraceEdgeCopyWithImpl<_MultiTraceEdge>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$MultiTraceEdgeToJson(this, );
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _MultiTraceEdge&&(identical(other.sourceId, sourceId) || other.sourceId == sourceId)&&(identical(other.targetId, targetId) || other.targetId == targetId)&&(identical(other.sourceType, sourceType) || other.sourceType == sourceType)&&(identical(other.targetType, targetType) || other.targetType == targetType)&&(identical(other.callCount, callCount) || other.callCount == callCount)&&(identical(other.errorCount, errorCount) || other.errorCount == errorCount)&&(identical(other.errorRatePct, errorRatePct) || other.errorRatePct == errorRatePct)&&(identical(other.sampleError, sampleError) || other.sampleError == sampleError)&&(identical(other.edgeTokens, edgeTokens) || other.edgeTokens == edgeTokens)&&(identical(other.avgTokensPerCall, avgTokensPerCall) || other.avgTokensPerCall == avgTokensPerCall)&&(identical(other.avgDurationMs, avgDurationMs) || other.avgDurationMs == avgDurationMs)&&(identical(other.p95DurationMs, p95DurationMs) || other.p95DurationMs == p95DurationMs)&&(identical(other.uniqueSessions, uniqueSessions) || other.uniqueSessions == uniqueSessions));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,sourceId,targetId,sourceType,targetType,callCount,errorCount,errorRatePct,sampleError,edgeTokens,avgTokensPerCall,avgDurationMs,p95DurationMs,uniqueSessions);

@override
String toString() {
  return 'MultiTraceEdge(sourceId: $sourceId, targetId: $targetId, sourceType: $sourceType, targetType: $targetType, callCount: $callCount, errorCount: $errorCount, errorRatePct: $errorRatePct, sampleError: $sampleError, edgeTokens: $edgeTokens, avgTokensPerCall: $avgTokensPerCall, avgDurationMs: $avgDurationMs, p95DurationMs: $p95DurationMs, uniqueSessions: $uniqueSessions)';
}


}

/// @nodoc
abstract mixin class _$MultiTraceEdgeCopyWith<$Res> implements $MultiTraceEdgeCopyWith<$Res> {
  factory _$MultiTraceEdgeCopyWith(_MultiTraceEdge value, $Res Function(_MultiTraceEdge) _then) = __$MultiTraceEdgeCopyWithImpl;
@override @useResult
$Res call({
@JsonKey(name: 'source_id') String sourceId,@JsonKey(name: 'target_id') String targetId,@JsonKey(name: 'source_type') String sourceType,@JsonKey(name: 'target_type') String targetType,@JsonKey(name: 'call_count') int callCount,@JsonKey(name: 'error_count') int errorCount,@JsonKey(name: 'error_rate_pct') double errorRatePct,@JsonKey(name: 'sample_error') String? sampleError,@JsonKey(name: 'total_tokens') int edgeTokens,@JsonKey(name: 'avg_tokens_per_call') int avgTokensPerCall,@JsonKey(name: 'avg_duration_ms') double avgDurationMs,@JsonKey(name: 'p95_duration_ms') double p95DurationMs,@JsonKey(name: 'unique_sessions') int uniqueSessions
});




}
/// @nodoc
class __$MultiTraceEdgeCopyWithImpl<$Res>
    implements _$MultiTraceEdgeCopyWith<$Res> {
  __$MultiTraceEdgeCopyWithImpl(this._self, this._then);

  final _MultiTraceEdge _self;
  final $Res Function(_MultiTraceEdge) _then;

/// Create a copy of MultiTraceEdge
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? sourceId = null,Object? targetId = null,Object? sourceType = null,Object? targetType = null,Object? callCount = null,Object? errorCount = null,Object? errorRatePct = null,Object? sampleError = freezed,Object? edgeTokens = null,Object? avgTokensPerCall = null,Object? avgDurationMs = null,Object? p95DurationMs = null,Object? uniqueSessions = null,}) {
  return _then(_MultiTraceEdge(
sourceId: null == sourceId ? _self.sourceId : sourceId // ignore: cast_nullable_to_non_nullable
as String,targetId: null == targetId ? _self.targetId : targetId // ignore: cast_nullable_to_non_nullable
as String,sourceType: null == sourceType ? _self.sourceType : sourceType // ignore: cast_nullable_to_non_nullable
as String,targetType: null == targetType ? _self.targetType : targetType // ignore: cast_nullable_to_non_nullable
as String,callCount: null == callCount ? _self.callCount : callCount // ignore: cast_nullable_to_non_nullable
as int,errorCount: null == errorCount ? _self.errorCount : errorCount // ignore: cast_nullable_to_non_nullable
as int,errorRatePct: null == errorRatePct ? _self.errorRatePct : errorRatePct // ignore: cast_nullable_to_non_nullable
as double,sampleError: freezed == sampleError ? _self.sampleError : sampleError // ignore: cast_nullable_to_non_nullable
as String?,edgeTokens: null == edgeTokens ? _self.edgeTokens : edgeTokens // ignore: cast_nullable_to_non_nullable
as int,avgTokensPerCall: null == avgTokensPerCall ? _self.avgTokensPerCall : avgTokensPerCall // ignore: cast_nullable_to_non_nullable
as int,avgDurationMs: null == avgDurationMs ? _self.avgDurationMs : avgDurationMs // ignore: cast_nullable_to_non_nullable
as double,p95DurationMs: null == p95DurationMs ? _self.p95DurationMs : p95DurationMs // ignore: cast_nullable_to_non_nullable
as double,uniqueSessions: null == uniqueSessions ? _self.uniqueSessions : uniqueSessions // ignore: cast_nullable_to_non_nullable
as int,
  ));
}


}


/// @nodoc
mixin _$MultiTraceGraphPayload {

 List<MultiTraceNode> get nodes; List<MultiTraceEdge> get edges;
/// Create a copy of MultiTraceGraphPayload
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$MultiTraceGraphPayloadCopyWith<MultiTraceGraphPayload> get copyWith => _$MultiTraceGraphPayloadCopyWithImpl<MultiTraceGraphPayload>(this as MultiTraceGraphPayload, _$identity);

  /// Serializes this MultiTraceGraphPayload to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is MultiTraceGraphPayload&&const DeepCollectionEquality().equals(other.nodes, nodes)&&const DeepCollectionEquality().equals(other.edges, edges));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,const DeepCollectionEquality().hash(nodes),const DeepCollectionEquality().hash(edges));

@override
String toString() {
  return 'MultiTraceGraphPayload(nodes: $nodes, edges: $edges)';
}


}

/// @nodoc
abstract mixin class $MultiTraceGraphPayloadCopyWith<$Res>  {
  factory $MultiTraceGraphPayloadCopyWith(MultiTraceGraphPayload value, $Res Function(MultiTraceGraphPayload) _then) = _$MultiTraceGraphPayloadCopyWithImpl;
@useResult
$Res call({
 List<MultiTraceNode> nodes, List<MultiTraceEdge> edges
});




}
/// @nodoc
class _$MultiTraceGraphPayloadCopyWithImpl<$Res>
    implements $MultiTraceGraphPayloadCopyWith<$Res> {
  _$MultiTraceGraphPayloadCopyWithImpl(this._self, this._then);

  final MultiTraceGraphPayload _self;
  final $Res Function(MultiTraceGraphPayload) _then;

/// Create a copy of MultiTraceGraphPayload
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? nodes = null,Object? edges = null,}) {
  return _then(_self.copyWith(
nodes: null == nodes ? _self.nodes : nodes // ignore: cast_nullable_to_non_nullable
as List<MultiTraceNode>,edges: null == edges ? _self.edges : edges // ignore: cast_nullable_to_non_nullable
as List<MultiTraceEdge>,
  ));
}

}


/// Adds pattern-matching-related methods to [MultiTraceGraphPayload].
extension MultiTraceGraphPayloadPatterns on MultiTraceGraphPayload {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _MultiTraceGraphPayload value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _MultiTraceGraphPayload() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _MultiTraceGraphPayload value)  $default,){
final _that = this;
switch (_that) {
case _MultiTraceGraphPayload():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _MultiTraceGraphPayload value)?  $default,){
final _that = this;
switch (_that) {
case _MultiTraceGraphPayload() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( List<MultiTraceNode> nodes,  List<MultiTraceEdge> edges)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _MultiTraceGraphPayload() when $default != null:
return $default(_that.nodes,_that.edges);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( List<MultiTraceNode> nodes,  List<MultiTraceEdge> edges)  $default,) {final _that = this;
switch (_that) {
case _MultiTraceGraphPayload():
return $default(_that.nodes,_that.edges);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( List<MultiTraceNode> nodes,  List<MultiTraceEdge> edges)?  $default,) {final _that = this;
switch (_that) {
case _MultiTraceGraphPayload() when $default != null:
return $default(_that.nodes,_that.edges);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _MultiTraceGraphPayload implements MultiTraceGraphPayload {
  const _MultiTraceGraphPayload({final  List<MultiTraceNode> nodes = const [], final  List<MultiTraceEdge> edges = const []}): _nodes = nodes,_edges = edges;
  factory _MultiTraceGraphPayload.fromJson(Map<String, dynamic> json) => _$MultiTraceGraphPayloadFromJson(json);

 final  List<MultiTraceNode> _nodes;
@override@JsonKey() List<MultiTraceNode> get nodes {
  if (_nodes is EqualUnmodifiableListView) return _nodes;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_nodes);
}

 final  List<MultiTraceEdge> _edges;
@override@JsonKey() List<MultiTraceEdge> get edges {
  if (_edges is EqualUnmodifiableListView) return _edges;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_edges);
}


/// Create a copy of MultiTraceGraphPayload
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$MultiTraceGraphPayloadCopyWith<_MultiTraceGraphPayload> get copyWith => __$MultiTraceGraphPayloadCopyWithImpl<_MultiTraceGraphPayload>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$MultiTraceGraphPayloadToJson(this, );
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _MultiTraceGraphPayload&&const DeepCollectionEquality().equals(other._nodes, _nodes)&&const DeepCollectionEquality().equals(other._edges, _edges));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,const DeepCollectionEquality().hash(_nodes),const DeepCollectionEquality().hash(_edges));

@override
String toString() {
  return 'MultiTraceGraphPayload(nodes: $nodes, edges: $edges)';
}


}

/// @nodoc
abstract mixin class _$MultiTraceGraphPayloadCopyWith<$Res> implements $MultiTraceGraphPayloadCopyWith<$Res> {
  factory _$MultiTraceGraphPayloadCopyWith(_MultiTraceGraphPayload value, $Res Function(_MultiTraceGraphPayload) _then) = __$MultiTraceGraphPayloadCopyWithImpl;
@override @useResult
$Res call({
 List<MultiTraceNode> nodes, List<MultiTraceEdge> edges
});




}
/// @nodoc
class __$MultiTraceGraphPayloadCopyWithImpl<$Res>
    implements _$MultiTraceGraphPayloadCopyWith<$Res> {
  __$MultiTraceGraphPayloadCopyWithImpl(this._self, this._then);

  final _MultiTraceGraphPayload _self;
  final $Res Function(_MultiTraceGraphPayload) _then;

/// Create a copy of MultiTraceGraphPayload
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? nodes = null,Object? edges = null,}) {
  return _then(_MultiTraceGraphPayload(
nodes: null == nodes ? _self._nodes : nodes // ignore: cast_nullable_to_non_nullable
as List<MultiTraceNode>,edges: null == edges ? _self._edges : edges // ignore: cast_nullable_to_non_nullable
as List<MultiTraceEdge>,
  ));
}


}

/// @nodoc
mixin _$SelectedGraphElement {





@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is SelectedGraphElement);
}


@override
int get hashCode => runtimeType.hashCode;

@override
String toString() {
  return 'SelectedGraphElement()';
}


}

/// @nodoc
class $SelectedGraphElementCopyWith<$Res>  {
$SelectedGraphElementCopyWith(SelectedGraphElement _, $Res Function(SelectedGraphElement) __);
}


/// Adds pattern-matching-related methods to [SelectedGraphElement].
extension SelectedGraphElementPatterns on SelectedGraphElement {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>({TResult Function( SelectedNode value)?  node,TResult Function( SelectedEdge value)?  edge,required TResult orElse(),}){
final _that = this;
switch (_that) {
case SelectedNode() when node != null:
return node(_that);case SelectedEdge() when edge != null:
return edge(_that);case _:
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

@optionalTypeArgs TResult map<TResult extends Object?>({required TResult Function( SelectedNode value)  node,required TResult Function( SelectedEdge value)  edge,}){
final _that = this;
switch (_that) {
case SelectedNode():
return node(_that);case SelectedEdge():
return edge(_that);}
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>({TResult? Function( SelectedNode value)?  node,TResult? Function( SelectedEdge value)?  edge,}){
final _that = this;
switch (_that) {
case SelectedNode() when node != null:
return node(_that);case SelectedEdge() when edge != null:
return edge(_that);case _:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>({TResult Function( MultiTraceNode node)?  node,TResult Function( MultiTraceEdge edge)?  edge,required TResult orElse(),}) {final _that = this;
switch (_that) {
case SelectedNode() when node != null:
return node(_that.node);case SelectedEdge() when edge != null:
return edge(_that.edge);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>({required TResult Function( MultiTraceNode node)  node,required TResult Function( MultiTraceEdge edge)  edge,}) {final _that = this;
switch (_that) {
case SelectedNode():
return node(_that.node);case SelectedEdge():
return edge(_that.edge);}
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>({TResult? Function( MultiTraceNode node)?  node,TResult? Function( MultiTraceEdge edge)?  edge,}) {final _that = this;
switch (_that) {
case SelectedNode() when node != null:
return node(_that.node);case SelectedEdge() when edge != null:
return edge(_that.edge);case _:
  return null;

}
}

}

/// @nodoc


class SelectedNode implements SelectedGraphElement {
  const SelectedNode(this.node);


 final  MultiTraceNode node;

/// Create a copy of SelectedGraphElement
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$SelectedNodeCopyWith<SelectedNode> get copyWith => _$SelectedNodeCopyWithImpl<SelectedNode>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is SelectedNode&&(identical(other.node, node) || other.node == node));
}


@override
int get hashCode => Object.hash(runtimeType,node);

@override
String toString() {
  return 'SelectedGraphElement.node(node: $node)';
}


}

/// @nodoc
abstract mixin class $SelectedNodeCopyWith<$Res> implements $SelectedGraphElementCopyWith<$Res> {
  factory $SelectedNodeCopyWith(SelectedNode value, $Res Function(SelectedNode) _then) = _$SelectedNodeCopyWithImpl;
@useResult
$Res call({
 MultiTraceNode node
});


$MultiTraceNodeCopyWith<$Res> get node;

}
/// @nodoc
class _$SelectedNodeCopyWithImpl<$Res>
    implements $SelectedNodeCopyWith<$Res> {
  _$SelectedNodeCopyWithImpl(this._self, this._then);

  final SelectedNode _self;
  final $Res Function(SelectedNode) _then;

/// Create a copy of SelectedGraphElement
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') $Res call({Object? node = null,}) {
  return _then(SelectedNode(
null == node ? _self.node : node // ignore: cast_nullable_to_non_nullable
as MultiTraceNode,
  ));
}

/// Create a copy of SelectedGraphElement
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$MultiTraceNodeCopyWith<$Res> get node {

  return $MultiTraceNodeCopyWith<$Res>(_self.node, (value) {
    return _then(_self.copyWith(node: value));
  });
}
}

/// @nodoc


class SelectedEdge implements SelectedGraphElement {
  const SelectedEdge(this.edge);


 final  MultiTraceEdge edge;

/// Create a copy of SelectedGraphElement
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$SelectedEdgeCopyWith<SelectedEdge> get copyWith => _$SelectedEdgeCopyWithImpl<SelectedEdge>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is SelectedEdge&&(identical(other.edge, edge) || other.edge == edge));
}


@override
int get hashCode => Object.hash(runtimeType,edge);

@override
String toString() {
  return 'SelectedGraphElement.edge(edge: $edge)';
}


}

/// @nodoc
abstract mixin class $SelectedEdgeCopyWith<$Res> implements $SelectedGraphElementCopyWith<$Res> {
  factory $SelectedEdgeCopyWith(SelectedEdge value, $Res Function(SelectedEdge) _then) = _$SelectedEdgeCopyWithImpl;
@useResult
$Res call({
 MultiTraceEdge edge
});


$MultiTraceEdgeCopyWith<$Res> get edge;

}
/// @nodoc
class _$SelectedEdgeCopyWithImpl<$Res>
    implements $SelectedEdgeCopyWith<$Res> {
  _$SelectedEdgeCopyWithImpl(this._self, this._then);

  final SelectedEdge _self;
  final $Res Function(SelectedEdge) _then;

/// Create a copy of SelectedGraphElement
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') $Res call({Object? edge = null,}) {
  return _then(SelectedEdge(
null == edge ? _self.edge : edge // ignore: cast_nullable_to_non_nullable
as MultiTraceEdge,
  ));
}

/// Create a copy of SelectedGraphElement
/// with the given fields replaced by the non-null parameter values.
@override
@pragma('vm:prefer-inline')
$MultiTraceEdgeCopyWith<$Res> get edge {

  return $MultiTraceEdgeCopyWith<$Res>(_self.edge, (value) {
    return _then(_self.copyWith(edge: value));
  });
}
}

// dart format on
