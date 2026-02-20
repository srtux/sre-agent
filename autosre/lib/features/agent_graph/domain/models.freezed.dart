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

 String get id; String get type; String? get label; String? get description;@JsonKey(name: 'execution_count') int get executionCount;@JsonKey(name: 'total_tokens') int get totalTokens;@JsonKey(name: 'input_tokens') int get inputTokens;@JsonKey(name: 'output_tokens') int get outputTokens;@JsonKey(name: 'error_count') int get errorCount;@JsonKey(name: 'has_error') bool get hasError;@JsonKey(name: 'avg_duration_ms') double get avgDurationMs;@JsonKey(name: 'p95_duration_ms') double get p95DurationMs;@JsonKey(name: 'error_rate_pct') double get errorRatePct;@JsonKey(name: 'total_cost') double? get totalCost;@JsonKey(name: 'tool_call_count') int get toolCallCount;@JsonKey(name: 'llm_call_count') int get llmCallCount;@JsonKey(name: 'unique_sessions') int get uniqueSessions;@JsonKey(name: 'is_root') bool get isRoot;@JsonKey(name: 'is_leaf') bool get isLeaf;@JsonKey(name: 'is_user_entry_point') bool get isUserEntryPoint;// User node flag
@JsonKey(name: 'is_user_node') bool get isUserNode;// Tree/DAG hierarchy support
@JsonKey(name: 'child_node_ids') List<String> get childNodeIds;@JsonKey(includeFromJson: false, includeToJson: false) bool get isExpanded;@JsonKey(name: 'depth') int get depth;// Hierarchical rollup metrics (includes all downstream descendants)
@JsonKey(name: 'downstream_total_tokens') int get downstreamTotalTokens;@JsonKey(name: 'downstream_total_cost') double? get downstreamTotalCost;@JsonKey(name: 'downstream_tool_call_count') int get downstreamToolCallCount;@JsonKey(name: 'downstream_llm_call_count') int get downstreamLlmCallCount;
/// Create a copy of MultiTraceNode
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$MultiTraceNodeCopyWith<MultiTraceNode> get copyWith => _$MultiTraceNodeCopyWithImpl<MultiTraceNode>(this as MultiTraceNode, _$identity);

  /// Serializes this MultiTraceNode to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is MultiTraceNode&&(identical(other.id, id) || other.id == id)&&(identical(other.type, type) || other.type == type)&&(identical(other.label, label) || other.label == label)&&(identical(other.description, description) || other.description == description)&&(identical(other.executionCount, executionCount) || other.executionCount == executionCount)&&(identical(other.totalTokens, totalTokens) || other.totalTokens == totalTokens)&&(identical(other.inputTokens, inputTokens) || other.inputTokens == inputTokens)&&(identical(other.outputTokens, outputTokens) || other.outputTokens == outputTokens)&&(identical(other.errorCount, errorCount) || other.errorCount == errorCount)&&(identical(other.hasError, hasError) || other.hasError == hasError)&&(identical(other.avgDurationMs, avgDurationMs) || other.avgDurationMs == avgDurationMs)&&(identical(other.p95DurationMs, p95DurationMs) || other.p95DurationMs == p95DurationMs)&&(identical(other.errorRatePct, errorRatePct) || other.errorRatePct == errorRatePct)&&(identical(other.totalCost, totalCost) || other.totalCost == totalCost)&&(identical(other.toolCallCount, toolCallCount) || other.toolCallCount == toolCallCount)&&(identical(other.llmCallCount, llmCallCount) || other.llmCallCount == llmCallCount)&&(identical(other.uniqueSessions, uniqueSessions) || other.uniqueSessions == uniqueSessions)&&(identical(other.isRoot, isRoot) || other.isRoot == isRoot)&&(identical(other.isLeaf, isLeaf) || other.isLeaf == isLeaf)&&(identical(other.isUserEntryPoint, isUserEntryPoint) || other.isUserEntryPoint == isUserEntryPoint)&&(identical(other.isUserNode, isUserNode) || other.isUserNode == isUserNode)&&const DeepCollectionEquality().equals(other.childNodeIds, childNodeIds)&&(identical(other.isExpanded, isExpanded) || other.isExpanded == isExpanded)&&(identical(other.depth, depth) || other.depth == depth)&&(identical(other.downstreamTotalTokens, downstreamTotalTokens) || other.downstreamTotalTokens == downstreamTotalTokens)&&(identical(other.downstreamTotalCost, downstreamTotalCost) || other.downstreamTotalCost == downstreamTotalCost)&&(identical(other.downstreamToolCallCount, downstreamToolCallCount) || other.downstreamToolCallCount == downstreamToolCallCount)&&(identical(other.downstreamLlmCallCount, downstreamLlmCallCount) || other.downstreamLlmCallCount == downstreamLlmCallCount));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hashAll([runtimeType,id,type,label,description,executionCount,totalTokens,inputTokens,outputTokens,errorCount,hasError,avgDurationMs,p95DurationMs,errorRatePct,totalCost,toolCallCount,llmCallCount,uniqueSessions,isRoot,isLeaf,isUserEntryPoint,isUserNode,const DeepCollectionEquality().hash(childNodeIds),isExpanded,depth,downstreamTotalTokens,downstreamTotalCost,downstreamToolCallCount,downstreamLlmCallCount]);

@override
String toString() {
  return 'MultiTraceNode(id: $id, type: $type, label: $label, description: $description, executionCount: $executionCount, totalTokens: $totalTokens, inputTokens: $inputTokens, outputTokens: $outputTokens, errorCount: $errorCount, hasError: $hasError, avgDurationMs: $avgDurationMs, p95DurationMs: $p95DurationMs, errorRatePct: $errorRatePct, totalCost: $totalCost, toolCallCount: $toolCallCount, llmCallCount: $llmCallCount, uniqueSessions: $uniqueSessions, isRoot: $isRoot, isLeaf: $isLeaf, isUserEntryPoint: $isUserEntryPoint, isUserNode: $isUserNode, childNodeIds: $childNodeIds, isExpanded: $isExpanded, depth: $depth, downstreamTotalTokens: $downstreamTotalTokens, downstreamTotalCost: $downstreamTotalCost, downstreamToolCallCount: $downstreamToolCallCount, downstreamLlmCallCount: $downstreamLlmCallCount)';
}


}

/// @nodoc
abstract mixin class $MultiTraceNodeCopyWith<$Res>  {
  factory $MultiTraceNodeCopyWith(MultiTraceNode value, $Res Function(MultiTraceNode) _then) = _$MultiTraceNodeCopyWithImpl;
@useResult
$Res call({
 String id, String type, String? label, String? description,@JsonKey(name: 'execution_count') int executionCount,@JsonKey(name: 'total_tokens') int totalTokens,@JsonKey(name: 'input_tokens') int inputTokens,@JsonKey(name: 'output_tokens') int outputTokens,@JsonKey(name: 'error_count') int errorCount,@JsonKey(name: 'has_error') bool hasError,@JsonKey(name: 'avg_duration_ms') double avgDurationMs,@JsonKey(name: 'p95_duration_ms') double p95DurationMs,@JsonKey(name: 'error_rate_pct') double errorRatePct,@JsonKey(name: 'total_cost') double? totalCost,@JsonKey(name: 'tool_call_count') int toolCallCount,@JsonKey(name: 'llm_call_count') int llmCallCount,@JsonKey(name: 'unique_sessions') int uniqueSessions,@JsonKey(name: 'is_root') bool isRoot,@JsonKey(name: 'is_leaf') bool isLeaf,@JsonKey(name: 'is_user_entry_point') bool isUserEntryPoint,@JsonKey(name: 'is_user_node') bool isUserNode,@JsonKey(name: 'child_node_ids') List<String> childNodeIds,@JsonKey(includeFromJson: false, includeToJson: false) bool isExpanded,@JsonKey(name: 'depth') int depth,@JsonKey(name: 'downstream_total_tokens') int downstreamTotalTokens,@JsonKey(name: 'downstream_total_cost') double? downstreamTotalCost,@JsonKey(name: 'downstream_tool_call_count') int downstreamToolCallCount,@JsonKey(name: 'downstream_llm_call_count') int downstreamLlmCallCount
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
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? type = null,Object? label = freezed,Object? description = freezed,Object? executionCount = null,Object? totalTokens = null,Object? inputTokens = null,Object? outputTokens = null,Object? errorCount = null,Object? hasError = null,Object? avgDurationMs = null,Object? p95DurationMs = null,Object? errorRatePct = null,Object? totalCost = freezed,Object? toolCallCount = null,Object? llmCallCount = null,Object? uniqueSessions = null,Object? isRoot = null,Object? isLeaf = null,Object? isUserEntryPoint = null,Object? isUserNode = null,Object? childNodeIds = null,Object? isExpanded = null,Object? depth = null,Object? downstreamTotalTokens = null,Object? downstreamTotalCost = freezed,Object? downstreamToolCallCount = null,Object? downstreamLlmCallCount = null,}) {
  return _then(_self.copyWith(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,type: null == type ? _self.type : type // ignore: cast_nullable_to_non_nullable
as String,label: freezed == label ? _self.label : label // ignore: cast_nullable_to_non_nullable
as String?,description: freezed == description ? _self.description : description // ignore: cast_nullable_to_non_nullable
as String?,executionCount: null == executionCount ? _self.executionCount : executionCount // ignore: cast_nullable_to_non_nullable
as int,totalTokens: null == totalTokens ? _self.totalTokens : totalTokens // ignore: cast_nullable_to_non_nullable
as int,inputTokens: null == inputTokens ? _self.inputTokens : inputTokens // ignore: cast_nullable_to_non_nullable
as int,outputTokens: null == outputTokens ? _self.outputTokens : outputTokens // ignore: cast_nullable_to_non_nullable
as int,errorCount: null == errorCount ? _self.errorCount : errorCount // ignore: cast_nullable_to_non_nullable
as int,hasError: null == hasError ? _self.hasError : hasError // ignore: cast_nullable_to_non_nullable
as bool,avgDurationMs: null == avgDurationMs ? _self.avgDurationMs : avgDurationMs // ignore: cast_nullable_to_non_nullable
as double,p95DurationMs: null == p95DurationMs ? _self.p95DurationMs : p95DurationMs // ignore: cast_nullable_to_non_nullable
as double,errorRatePct: null == errorRatePct ? _self.errorRatePct : errorRatePct // ignore: cast_nullable_to_non_nullable
as double,totalCost: freezed == totalCost ? _self.totalCost : totalCost // ignore: cast_nullable_to_non_nullable
as double?,toolCallCount: null == toolCallCount ? _self.toolCallCount : toolCallCount // ignore: cast_nullable_to_non_nullable
as int,llmCallCount: null == llmCallCount ? _self.llmCallCount : llmCallCount // ignore: cast_nullable_to_non_nullable
as int,uniqueSessions: null == uniqueSessions ? _self.uniqueSessions : uniqueSessions // ignore: cast_nullable_to_non_nullable
as int,isRoot: null == isRoot ? _self.isRoot : isRoot // ignore: cast_nullable_to_non_nullable
as bool,isLeaf: null == isLeaf ? _self.isLeaf : isLeaf // ignore: cast_nullable_to_non_nullable
as bool,isUserEntryPoint: null == isUserEntryPoint ? _self.isUserEntryPoint : isUserEntryPoint // ignore: cast_nullable_to_non_nullable
as bool,isUserNode: null == isUserNode ? _self.isUserNode : isUserNode // ignore: cast_nullable_to_non_nullable
as bool,childNodeIds: null == childNodeIds ? _self.childNodeIds : childNodeIds // ignore: cast_nullable_to_non_nullable
as List<String>,isExpanded: null == isExpanded ? _self.isExpanded : isExpanded // ignore: cast_nullable_to_non_nullable
as bool,depth: null == depth ? _self.depth : depth // ignore: cast_nullable_to_non_nullable
as int,downstreamTotalTokens: null == downstreamTotalTokens ? _self.downstreamTotalTokens : downstreamTotalTokens // ignore: cast_nullable_to_non_nullable
as int,downstreamTotalCost: freezed == downstreamTotalCost ? _self.downstreamTotalCost : downstreamTotalCost // ignore: cast_nullable_to_non_nullable
as double?,downstreamToolCallCount: null == downstreamToolCallCount ? _self.downstreamToolCallCount : downstreamToolCallCount // ignore: cast_nullable_to_non_nullable
as int,downstreamLlmCallCount: null == downstreamLlmCallCount ? _self.downstreamLlmCallCount : downstreamLlmCallCount // ignore: cast_nullable_to_non_nullable
as int,
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id,  String type,  String? label,  String? description, @JsonKey(name: 'execution_count')  int executionCount, @JsonKey(name: 'total_tokens')  int totalTokens, @JsonKey(name: 'input_tokens')  int inputTokens, @JsonKey(name: 'output_tokens')  int outputTokens, @JsonKey(name: 'error_count')  int errorCount, @JsonKey(name: 'has_error')  bool hasError, @JsonKey(name: 'avg_duration_ms')  double avgDurationMs, @JsonKey(name: 'p95_duration_ms')  double p95DurationMs, @JsonKey(name: 'error_rate_pct')  double errorRatePct, @JsonKey(name: 'total_cost')  double? totalCost, @JsonKey(name: 'tool_call_count')  int toolCallCount, @JsonKey(name: 'llm_call_count')  int llmCallCount, @JsonKey(name: 'unique_sessions')  int uniqueSessions, @JsonKey(name: 'is_root')  bool isRoot, @JsonKey(name: 'is_leaf')  bool isLeaf, @JsonKey(name: 'is_user_entry_point')  bool isUserEntryPoint, @JsonKey(name: 'is_user_node')  bool isUserNode, @JsonKey(name: 'child_node_ids')  List<String> childNodeIds, @JsonKey(includeFromJson: false, includeToJson: false)  bool isExpanded, @JsonKey(name: 'depth')  int depth, @JsonKey(name: 'downstream_total_tokens')  int downstreamTotalTokens, @JsonKey(name: 'downstream_total_cost')  double? downstreamTotalCost, @JsonKey(name: 'downstream_tool_call_count')  int downstreamToolCallCount, @JsonKey(name: 'downstream_llm_call_count')  int downstreamLlmCallCount)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _MultiTraceNode() when $default != null:
return $default(_that.id,_that.type,_that.label,_that.description,_that.executionCount,_that.totalTokens,_that.inputTokens,_that.outputTokens,_that.errorCount,_that.hasError,_that.avgDurationMs,_that.p95DurationMs,_that.errorRatePct,_that.totalCost,_that.toolCallCount,_that.llmCallCount,_that.uniqueSessions,_that.isRoot,_that.isLeaf,_that.isUserEntryPoint,_that.isUserNode,_that.childNodeIds,_that.isExpanded,_that.depth,_that.downstreamTotalTokens,_that.downstreamTotalCost,_that.downstreamToolCallCount,_that.downstreamLlmCallCount);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id,  String type,  String? label,  String? description, @JsonKey(name: 'execution_count')  int executionCount, @JsonKey(name: 'total_tokens')  int totalTokens, @JsonKey(name: 'input_tokens')  int inputTokens, @JsonKey(name: 'output_tokens')  int outputTokens, @JsonKey(name: 'error_count')  int errorCount, @JsonKey(name: 'has_error')  bool hasError, @JsonKey(name: 'avg_duration_ms')  double avgDurationMs, @JsonKey(name: 'p95_duration_ms')  double p95DurationMs, @JsonKey(name: 'error_rate_pct')  double errorRatePct, @JsonKey(name: 'total_cost')  double? totalCost, @JsonKey(name: 'tool_call_count')  int toolCallCount, @JsonKey(name: 'llm_call_count')  int llmCallCount, @JsonKey(name: 'unique_sessions')  int uniqueSessions, @JsonKey(name: 'is_root')  bool isRoot, @JsonKey(name: 'is_leaf')  bool isLeaf, @JsonKey(name: 'is_user_entry_point')  bool isUserEntryPoint, @JsonKey(name: 'is_user_node')  bool isUserNode, @JsonKey(name: 'child_node_ids')  List<String> childNodeIds, @JsonKey(includeFromJson: false, includeToJson: false)  bool isExpanded, @JsonKey(name: 'depth')  int depth, @JsonKey(name: 'downstream_total_tokens')  int downstreamTotalTokens, @JsonKey(name: 'downstream_total_cost')  double? downstreamTotalCost, @JsonKey(name: 'downstream_tool_call_count')  int downstreamToolCallCount, @JsonKey(name: 'downstream_llm_call_count')  int downstreamLlmCallCount)  $default,) {final _that = this;
switch (_that) {
case _MultiTraceNode():
return $default(_that.id,_that.type,_that.label,_that.description,_that.executionCount,_that.totalTokens,_that.inputTokens,_that.outputTokens,_that.errorCount,_that.hasError,_that.avgDurationMs,_that.p95DurationMs,_that.errorRatePct,_that.totalCost,_that.toolCallCount,_that.llmCallCount,_that.uniqueSessions,_that.isRoot,_that.isLeaf,_that.isUserEntryPoint,_that.isUserNode,_that.childNodeIds,_that.isExpanded,_that.depth,_that.downstreamTotalTokens,_that.downstreamTotalCost,_that.downstreamToolCallCount,_that.downstreamLlmCallCount);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id,  String type,  String? label,  String? description, @JsonKey(name: 'execution_count')  int executionCount, @JsonKey(name: 'total_tokens')  int totalTokens, @JsonKey(name: 'input_tokens')  int inputTokens, @JsonKey(name: 'output_tokens')  int outputTokens, @JsonKey(name: 'error_count')  int errorCount, @JsonKey(name: 'has_error')  bool hasError, @JsonKey(name: 'avg_duration_ms')  double avgDurationMs, @JsonKey(name: 'p95_duration_ms')  double p95DurationMs, @JsonKey(name: 'error_rate_pct')  double errorRatePct, @JsonKey(name: 'total_cost')  double? totalCost, @JsonKey(name: 'tool_call_count')  int toolCallCount, @JsonKey(name: 'llm_call_count')  int llmCallCount, @JsonKey(name: 'unique_sessions')  int uniqueSessions, @JsonKey(name: 'is_root')  bool isRoot, @JsonKey(name: 'is_leaf')  bool isLeaf, @JsonKey(name: 'is_user_entry_point')  bool isUserEntryPoint, @JsonKey(name: 'is_user_node')  bool isUserNode, @JsonKey(name: 'child_node_ids')  List<String> childNodeIds, @JsonKey(includeFromJson: false, includeToJson: false)  bool isExpanded, @JsonKey(name: 'depth')  int depth, @JsonKey(name: 'downstream_total_tokens')  int downstreamTotalTokens, @JsonKey(name: 'downstream_total_cost')  double? downstreamTotalCost, @JsonKey(name: 'downstream_tool_call_count')  int downstreamToolCallCount, @JsonKey(name: 'downstream_llm_call_count')  int downstreamLlmCallCount)?  $default,) {final _that = this;
switch (_that) {
case _MultiTraceNode() when $default != null:
return $default(_that.id,_that.type,_that.label,_that.description,_that.executionCount,_that.totalTokens,_that.inputTokens,_that.outputTokens,_that.errorCount,_that.hasError,_that.avgDurationMs,_that.p95DurationMs,_that.errorRatePct,_that.totalCost,_that.toolCallCount,_that.llmCallCount,_that.uniqueSessions,_that.isRoot,_that.isLeaf,_that.isUserEntryPoint,_that.isUserNode,_that.childNodeIds,_that.isExpanded,_that.depth,_that.downstreamTotalTokens,_that.downstreamTotalCost,_that.downstreamToolCallCount,_that.downstreamLlmCallCount);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _MultiTraceNode implements MultiTraceNode {
  const _MultiTraceNode({required this.id, required this.type, this.label, this.description, @JsonKey(name: 'execution_count') this.executionCount = 0, @JsonKey(name: 'total_tokens') this.totalTokens = 0, @JsonKey(name: 'input_tokens') this.inputTokens = 0, @JsonKey(name: 'output_tokens') this.outputTokens = 0, @JsonKey(name: 'error_count') this.errorCount = 0, @JsonKey(name: 'has_error') this.hasError = false, @JsonKey(name: 'avg_duration_ms') this.avgDurationMs = 0.0, @JsonKey(name: 'p95_duration_ms') this.p95DurationMs = 0.0, @JsonKey(name: 'error_rate_pct') this.errorRatePct = 0.0, @JsonKey(name: 'total_cost') this.totalCost, @JsonKey(name: 'tool_call_count') this.toolCallCount = 0, @JsonKey(name: 'llm_call_count') this.llmCallCount = 0, @JsonKey(name: 'unique_sessions') this.uniqueSessions = 0, @JsonKey(name: 'is_root') this.isRoot = false, @JsonKey(name: 'is_leaf') this.isLeaf = false, @JsonKey(name: 'is_user_entry_point') this.isUserEntryPoint = false, @JsonKey(name: 'is_user_node') this.isUserNode = false, @JsonKey(name: 'child_node_ids') final  List<String> childNodeIds = const [], @JsonKey(includeFromJson: false, includeToJson: false) this.isExpanded = true, @JsonKey(name: 'depth') this.depth = 0, @JsonKey(name: 'downstream_total_tokens') this.downstreamTotalTokens = 0, @JsonKey(name: 'downstream_total_cost') this.downstreamTotalCost, @JsonKey(name: 'downstream_tool_call_count') this.downstreamToolCallCount = 0, @JsonKey(name: 'downstream_llm_call_count') this.downstreamLlmCallCount = 0}): _childNodeIds = childNodeIds;
  factory _MultiTraceNode.fromJson(Map<String, dynamic> json) => _$MultiTraceNodeFromJson(json);

@override final  String id;
@override final  String type;
@override final  String? label;
@override final  String? description;
@override@JsonKey(name: 'execution_count') final  int executionCount;
@override@JsonKey(name: 'total_tokens') final  int totalTokens;
@override@JsonKey(name: 'input_tokens') final  int inputTokens;
@override@JsonKey(name: 'output_tokens') final  int outputTokens;
@override@JsonKey(name: 'error_count') final  int errorCount;
@override@JsonKey(name: 'has_error') final  bool hasError;
@override@JsonKey(name: 'avg_duration_ms') final  double avgDurationMs;
@override@JsonKey(name: 'p95_duration_ms') final  double p95DurationMs;
@override@JsonKey(name: 'error_rate_pct') final  double errorRatePct;
@override@JsonKey(name: 'total_cost') final  double? totalCost;
@override@JsonKey(name: 'tool_call_count') final  int toolCallCount;
@override@JsonKey(name: 'llm_call_count') final  int llmCallCount;
@override@JsonKey(name: 'unique_sessions') final  int uniqueSessions;
@override@JsonKey(name: 'is_root') final  bool isRoot;
@override@JsonKey(name: 'is_leaf') final  bool isLeaf;
@override@JsonKey(name: 'is_user_entry_point') final  bool isUserEntryPoint;
// User node flag
@override@JsonKey(name: 'is_user_node') final  bool isUserNode;
// Tree/DAG hierarchy support
 final  List<String> _childNodeIds;
// Tree/DAG hierarchy support
@override@JsonKey(name: 'child_node_ids') List<String> get childNodeIds {
  if (_childNodeIds is EqualUnmodifiableListView) return _childNodeIds;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_childNodeIds);
}

@override@JsonKey(includeFromJson: false, includeToJson: false) final  bool isExpanded;
@override@JsonKey(name: 'depth') final  int depth;
// Hierarchical rollup metrics (includes all downstream descendants)
@override@JsonKey(name: 'downstream_total_tokens') final  int downstreamTotalTokens;
@override@JsonKey(name: 'downstream_total_cost') final  double? downstreamTotalCost;
@override@JsonKey(name: 'downstream_tool_call_count') final  int downstreamToolCallCount;
@override@JsonKey(name: 'downstream_llm_call_count') final  int downstreamLlmCallCount;

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
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _MultiTraceNode&&(identical(other.id, id) || other.id == id)&&(identical(other.type, type) || other.type == type)&&(identical(other.label, label) || other.label == label)&&(identical(other.description, description) || other.description == description)&&(identical(other.executionCount, executionCount) || other.executionCount == executionCount)&&(identical(other.totalTokens, totalTokens) || other.totalTokens == totalTokens)&&(identical(other.inputTokens, inputTokens) || other.inputTokens == inputTokens)&&(identical(other.outputTokens, outputTokens) || other.outputTokens == outputTokens)&&(identical(other.errorCount, errorCount) || other.errorCount == errorCount)&&(identical(other.hasError, hasError) || other.hasError == hasError)&&(identical(other.avgDurationMs, avgDurationMs) || other.avgDurationMs == avgDurationMs)&&(identical(other.p95DurationMs, p95DurationMs) || other.p95DurationMs == p95DurationMs)&&(identical(other.errorRatePct, errorRatePct) || other.errorRatePct == errorRatePct)&&(identical(other.totalCost, totalCost) || other.totalCost == totalCost)&&(identical(other.toolCallCount, toolCallCount) || other.toolCallCount == toolCallCount)&&(identical(other.llmCallCount, llmCallCount) || other.llmCallCount == llmCallCount)&&(identical(other.uniqueSessions, uniqueSessions) || other.uniqueSessions == uniqueSessions)&&(identical(other.isRoot, isRoot) || other.isRoot == isRoot)&&(identical(other.isLeaf, isLeaf) || other.isLeaf == isLeaf)&&(identical(other.isUserEntryPoint, isUserEntryPoint) || other.isUserEntryPoint == isUserEntryPoint)&&(identical(other.isUserNode, isUserNode) || other.isUserNode == isUserNode)&&const DeepCollectionEquality().equals(other._childNodeIds, _childNodeIds)&&(identical(other.isExpanded, isExpanded) || other.isExpanded == isExpanded)&&(identical(other.depth, depth) || other.depth == depth)&&(identical(other.downstreamTotalTokens, downstreamTotalTokens) || other.downstreamTotalTokens == downstreamTotalTokens)&&(identical(other.downstreamTotalCost, downstreamTotalCost) || other.downstreamTotalCost == downstreamTotalCost)&&(identical(other.downstreamToolCallCount, downstreamToolCallCount) || other.downstreamToolCallCount == downstreamToolCallCount)&&(identical(other.downstreamLlmCallCount, downstreamLlmCallCount) || other.downstreamLlmCallCount == downstreamLlmCallCount));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hashAll([runtimeType,id,type,label,description,executionCount,totalTokens,inputTokens,outputTokens,errorCount,hasError,avgDurationMs,p95DurationMs,errorRatePct,totalCost,toolCallCount,llmCallCount,uniqueSessions,isRoot,isLeaf,isUserEntryPoint,isUserNode,const DeepCollectionEquality().hash(_childNodeIds),isExpanded,depth,downstreamTotalTokens,downstreamTotalCost,downstreamToolCallCount,downstreamLlmCallCount]);

@override
String toString() {
  return 'MultiTraceNode(id: $id, type: $type, label: $label, description: $description, executionCount: $executionCount, totalTokens: $totalTokens, inputTokens: $inputTokens, outputTokens: $outputTokens, errorCount: $errorCount, hasError: $hasError, avgDurationMs: $avgDurationMs, p95DurationMs: $p95DurationMs, errorRatePct: $errorRatePct, totalCost: $totalCost, toolCallCount: $toolCallCount, llmCallCount: $llmCallCount, uniqueSessions: $uniqueSessions, isRoot: $isRoot, isLeaf: $isLeaf, isUserEntryPoint: $isUserEntryPoint, isUserNode: $isUserNode, childNodeIds: $childNodeIds, isExpanded: $isExpanded, depth: $depth, downstreamTotalTokens: $downstreamTotalTokens, downstreamTotalCost: $downstreamTotalCost, downstreamToolCallCount: $downstreamToolCallCount, downstreamLlmCallCount: $downstreamLlmCallCount)';
}


}

/// @nodoc
abstract mixin class _$MultiTraceNodeCopyWith<$Res> implements $MultiTraceNodeCopyWith<$Res> {
  factory _$MultiTraceNodeCopyWith(_MultiTraceNode value, $Res Function(_MultiTraceNode) _then) = __$MultiTraceNodeCopyWithImpl;
@override @useResult
$Res call({
 String id, String type, String? label, String? description,@JsonKey(name: 'execution_count') int executionCount,@JsonKey(name: 'total_tokens') int totalTokens,@JsonKey(name: 'input_tokens') int inputTokens,@JsonKey(name: 'output_tokens') int outputTokens,@JsonKey(name: 'error_count') int errorCount,@JsonKey(name: 'has_error') bool hasError,@JsonKey(name: 'avg_duration_ms') double avgDurationMs,@JsonKey(name: 'p95_duration_ms') double p95DurationMs,@JsonKey(name: 'error_rate_pct') double errorRatePct,@JsonKey(name: 'total_cost') double? totalCost,@JsonKey(name: 'tool_call_count') int toolCallCount,@JsonKey(name: 'llm_call_count') int llmCallCount,@JsonKey(name: 'unique_sessions') int uniqueSessions,@JsonKey(name: 'is_root') bool isRoot,@JsonKey(name: 'is_leaf') bool isLeaf,@JsonKey(name: 'is_user_entry_point') bool isUserEntryPoint,@JsonKey(name: 'is_user_node') bool isUserNode,@JsonKey(name: 'child_node_ids') List<String> childNodeIds,@JsonKey(includeFromJson: false, includeToJson: false) bool isExpanded,@JsonKey(name: 'depth') int depth,@JsonKey(name: 'downstream_total_tokens') int downstreamTotalTokens,@JsonKey(name: 'downstream_total_cost') double? downstreamTotalCost,@JsonKey(name: 'downstream_tool_call_count') int downstreamToolCallCount,@JsonKey(name: 'downstream_llm_call_count') int downstreamLlmCallCount
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
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? type = null,Object? label = freezed,Object? description = freezed,Object? executionCount = null,Object? totalTokens = null,Object? inputTokens = null,Object? outputTokens = null,Object? errorCount = null,Object? hasError = null,Object? avgDurationMs = null,Object? p95DurationMs = null,Object? errorRatePct = null,Object? totalCost = freezed,Object? toolCallCount = null,Object? llmCallCount = null,Object? uniqueSessions = null,Object? isRoot = null,Object? isLeaf = null,Object? isUserEntryPoint = null,Object? isUserNode = null,Object? childNodeIds = null,Object? isExpanded = null,Object? depth = null,Object? downstreamTotalTokens = null,Object? downstreamTotalCost = freezed,Object? downstreamToolCallCount = null,Object? downstreamLlmCallCount = null,}) {
  return _then(_MultiTraceNode(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,type: null == type ? _self.type : type // ignore: cast_nullable_to_non_nullable
as String,label: freezed == label ? _self.label : label // ignore: cast_nullable_to_non_nullable
as String?,description: freezed == description ? _self.description : description // ignore: cast_nullable_to_non_nullable
as String?,executionCount: null == executionCount ? _self.executionCount : executionCount // ignore: cast_nullable_to_non_nullable
as int,totalTokens: null == totalTokens ? _self.totalTokens : totalTokens // ignore: cast_nullable_to_non_nullable
as int,inputTokens: null == inputTokens ? _self.inputTokens : inputTokens // ignore: cast_nullable_to_non_nullable
as int,outputTokens: null == outputTokens ? _self.outputTokens : outputTokens // ignore: cast_nullable_to_non_nullable
as int,errorCount: null == errorCount ? _self.errorCount : errorCount // ignore: cast_nullable_to_non_nullable
as int,hasError: null == hasError ? _self.hasError : hasError // ignore: cast_nullable_to_non_nullable
as bool,avgDurationMs: null == avgDurationMs ? _self.avgDurationMs : avgDurationMs // ignore: cast_nullable_to_non_nullable
as double,p95DurationMs: null == p95DurationMs ? _self.p95DurationMs : p95DurationMs // ignore: cast_nullable_to_non_nullable
as double,errorRatePct: null == errorRatePct ? _self.errorRatePct : errorRatePct // ignore: cast_nullable_to_non_nullable
as double,totalCost: freezed == totalCost ? _self.totalCost : totalCost // ignore: cast_nullable_to_non_nullable
as double?,toolCallCount: null == toolCallCount ? _self.toolCallCount : toolCallCount // ignore: cast_nullable_to_non_nullable
as int,llmCallCount: null == llmCallCount ? _self.llmCallCount : llmCallCount // ignore: cast_nullable_to_non_nullable
as int,uniqueSessions: null == uniqueSessions ? _self.uniqueSessions : uniqueSessions // ignore: cast_nullable_to_non_nullable
as int,isRoot: null == isRoot ? _self.isRoot : isRoot // ignore: cast_nullable_to_non_nullable
as bool,isLeaf: null == isLeaf ? _self.isLeaf : isLeaf // ignore: cast_nullable_to_non_nullable
as bool,isUserEntryPoint: null == isUserEntryPoint ? _self.isUserEntryPoint : isUserEntryPoint // ignore: cast_nullable_to_non_nullable
as bool,isUserNode: null == isUserNode ? _self.isUserNode : isUserNode // ignore: cast_nullable_to_non_nullable
as bool,childNodeIds: null == childNodeIds ? _self._childNodeIds : childNodeIds // ignore: cast_nullable_to_non_nullable
as List<String>,isExpanded: null == isExpanded ? _self.isExpanded : isExpanded // ignore: cast_nullable_to_non_nullable
as bool,depth: null == depth ? _self.depth : depth // ignore: cast_nullable_to_non_nullable
as int,downstreamTotalTokens: null == downstreamTotalTokens ? _self.downstreamTotalTokens : downstreamTotalTokens // ignore: cast_nullable_to_non_nullable
as int,downstreamTotalCost: freezed == downstreamTotalCost ? _self.downstreamTotalCost : downstreamTotalCost // ignore: cast_nullable_to_non_nullable
as double?,downstreamToolCallCount: null == downstreamToolCallCount ? _self.downstreamToolCallCount : downstreamToolCallCount // ignore: cast_nullable_to_non_nullable
as int,downstreamLlmCallCount: null == downstreamLlmCallCount ? _self.downstreamLlmCallCount : downstreamLlmCallCount // ignore: cast_nullable_to_non_nullable
as int,
  ));
}


}


/// @nodoc
mixin _$MultiTraceEdge {

@JsonKey(name: 'source_id') String get sourceId;@JsonKey(name: 'target_id') String get targetId;@JsonKey(name: 'source_type') String get sourceType;@JsonKey(name: 'target_type') String get targetType;@JsonKey(name: 'call_count') int get callCount;@JsonKey(name: 'error_count') int get errorCount;@JsonKey(name: 'error_rate_pct') double get errorRatePct;@JsonKey(name: 'sample_error') String? get sampleError;@JsonKey(name: 'total_tokens') int get edgeTokens;@JsonKey(name: 'input_tokens') int get inputTokens;@JsonKey(name: 'output_tokens') int get outputTokens;@JsonKey(name: 'avg_tokens_per_call') int get avgTokensPerCall;@JsonKey(name: 'avg_duration_ms') double get avgDurationMs;@JsonKey(name: 'p95_duration_ms') double get p95DurationMs;@JsonKey(name: 'unique_sessions') int get uniqueSessions;@JsonKey(name: 'total_cost') double? get totalCost;// Back-edge detection (for cycle rendering)
@JsonKey(name: 'is_back_edge') bool get isBackEdge;// Normalized flow weight (0.0 to 1.0) for animation speed
@JsonKey(name: 'flow_weight') double get flowWeight;
/// Create a copy of MultiTraceEdge
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$MultiTraceEdgeCopyWith<MultiTraceEdge> get copyWith => _$MultiTraceEdgeCopyWithImpl<MultiTraceEdge>(this as MultiTraceEdge, _$identity);

  /// Serializes this MultiTraceEdge to a JSON map.
  Map<String, dynamic> toJson();


@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is MultiTraceEdge&&(identical(other.sourceId, sourceId) || other.sourceId == sourceId)&&(identical(other.targetId, targetId) || other.targetId == targetId)&&(identical(other.sourceType, sourceType) || other.sourceType == sourceType)&&(identical(other.targetType, targetType) || other.targetType == targetType)&&(identical(other.callCount, callCount) || other.callCount == callCount)&&(identical(other.errorCount, errorCount) || other.errorCount == errorCount)&&(identical(other.errorRatePct, errorRatePct) || other.errorRatePct == errorRatePct)&&(identical(other.sampleError, sampleError) || other.sampleError == sampleError)&&(identical(other.edgeTokens, edgeTokens) || other.edgeTokens == edgeTokens)&&(identical(other.inputTokens, inputTokens) || other.inputTokens == inputTokens)&&(identical(other.outputTokens, outputTokens) || other.outputTokens == outputTokens)&&(identical(other.avgTokensPerCall, avgTokensPerCall) || other.avgTokensPerCall == avgTokensPerCall)&&(identical(other.avgDurationMs, avgDurationMs) || other.avgDurationMs == avgDurationMs)&&(identical(other.p95DurationMs, p95DurationMs) || other.p95DurationMs == p95DurationMs)&&(identical(other.uniqueSessions, uniqueSessions) || other.uniqueSessions == uniqueSessions)&&(identical(other.totalCost, totalCost) || other.totalCost == totalCost)&&(identical(other.isBackEdge, isBackEdge) || other.isBackEdge == isBackEdge)&&(identical(other.flowWeight, flowWeight) || other.flowWeight == flowWeight));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,sourceId,targetId,sourceType,targetType,callCount,errorCount,errorRatePct,sampleError,edgeTokens,inputTokens,outputTokens,avgTokensPerCall,avgDurationMs,p95DurationMs,uniqueSessions,totalCost,isBackEdge,flowWeight);

@override
String toString() {
  return 'MultiTraceEdge(sourceId: $sourceId, targetId: $targetId, sourceType: $sourceType, targetType: $targetType, callCount: $callCount, errorCount: $errorCount, errorRatePct: $errorRatePct, sampleError: $sampleError, edgeTokens: $edgeTokens, inputTokens: $inputTokens, outputTokens: $outputTokens, avgTokensPerCall: $avgTokensPerCall, avgDurationMs: $avgDurationMs, p95DurationMs: $p95DurationMs, uniqueSessions: $uniqueSessions, totalCost: $totalCost, isBackEdge: $isBackEdge, flowWeight: $flowWeight)';
}


}

/// @nodoc
abstract mixin class $MultiTraceEdgeCopyWith<$Res>  {
  factory $MultiTraceEdgeCopyWith(MultiTraceEdge value, $Res Function(MultiTraceEdge) _then) = _$MultiTraceEdgeCopyWithImpl;
@useResult
$Res call({
@JsonKey(name: 'source_id') String sourceId,@JsonKey(name: 'target_id') String targetId,@JsonKey(name: 'source_type') String sourceType,@JsonKey(name: 'target_type') String targetType,@JsonKey(name: 'call_count') int callCount,@JsonKey(name: 'error_count') int errorCount,@JsonKey(name: 'error_rate_pct') double errorRatePct,@JsonKey(name: 'sample_error') String? sampleError,@JsonKey(name: 'total_tokens') int edgeTokens,@JsonKey(name: 'input_tokens') int inputTokens,@JsonKey(name: 'output_tokens') int outputTokens,@JsonKey(name: 'avg_tokens_per_call') int avgTokensPerCall,@JsonKey(name: 'avg_duration_ms') double avgDurationMs,@JsonKey(name: 'p95_duration_ms') double p95DurationMs,@JsonKey(name: 'unique_sessions') int uniqueSessions,@JsonKey(name: 'total_cost') double? totalCost,@JsonKey(name: 'is_back_edge') bool isBackEdge,@JsonKey(name: 'flow_weight') double flowWeight
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
@pragma('vm:prefer-inline') @override $Res call({Object? sourceId = null,Object? targetId = null,Object? sourceType = null,Object? targetType = null,Object? callCount = null,Object? errorCount = null,Object? errorRatePct = null,Object? sampleError = freezed,Object? edgeTokens = null,Object? inputTokens = null,Object? outputTokens = null,Object? avgTokensPerCall = null,Object? avgDurationMs = null,Object? p95DurationMs = null,Object? uniqueSessions = null,Object? totalCost = freezed,Object? isBackEdge = null,Object? flowWeight = null,}) {
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
as int,inputTokens: null == inputTokens ? _self.inputTokens : inputTokens // ignore: cast_nullable_to_non_nullable
as int,outputTokens: null == outputTokens ? _self.outputTokens : outputTokens // ignore: cast_nullable_to_non_nullable
as int,avgTokensPerCall: null == avgTokensPerCall ? _self.avgTokensPerCall : avgTokensPerCall // ignore: cast_nullable_to_non_nullable
as int,avgDurationMs: null == avgDurationMs ? _self.avgDurationMs : avgDurationMs // ignore: cast_nullable_to_non_nullable
as double,p95DurationMs: null == p95DurationMs ? _self.p95DurationMs : p95DurationMs // ignore: cast_nullable_to_non_nullable
as double,uniqueSessions: null == uniqueSessions ? _self.uniqueSessions : uniqueSessions // ignore: cast_nullable_to_non_nullable
as int,totalCost: freezed == totalCost ? _self.totalCost : totalCost // ignore: cast_nullable_to_non_nullable
as double?,isBackEdge: null == isBackEdge ? _self.isBackEdge : isBackEdge // ignore: cast_nullable_to_non_nullable
as bool,flowWeight: null == flowWeight ? _self.flowWeight : flowWeight // ignore: cast_nullable_to_non_nullable
as double,
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function(@JsonKey(name: 'source_id')  String sourceId, @JsonKey(name: 'target_id')  String targetId, @JsonKey(name: 'source_type')  String sourceType, @JsonKey(name: 'target_type')  String targetType, @JsonKey(name: 'call_count')  int callCount, @JsonKey(name: 'error_count')  int errorCount, @JsonKey(name: 'error_rate_pct')  double errorRatePct, @JsonKey(name: 'sample_error')  String? sampleError, @JsonKey(name: 'total_tokens')  int edgeTokens, @JsonKey(name: 'input_tokens')  int inputTokens, @JsonKey(name: 'output_tokens')  int outputTokens, @JsonKey(name: 'avg_tokens_per_call')  int avgTokensPerCall, @JsonKey(name: 'avg_duration_ms')  double avgDurationMs, @JsonKey(name: 'p95_duration_ms')  double p95DurationMs, @JsonKey(name: 'unique_sessions')  int uniqueSessions, @JsonKey(name: 'total_cost')  double? totalCost, @JsonKey(name: 'is_back_edge')  bool isBackEdge, @JsonKey(name: 'flow_weight')  double flowWeight)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _MultiTraceEdge() when $default != null:
return $default(_that.sourceId,_that.targetId,_that.sourceType,_that.targetType,_that.callCount,_that.errorCount,_that.errorRatePct,_that.sampleError,_that.edgeTokens,_that.inputTokens,_that.outputTokens,_that.avgTokensPerCall,_that.avgDurationMs,_that.p95DurationMs,_that.uniqueSessions,_that.totalCost,_that.isBackEdge,_that.flowWeight);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function(@JsonKey(name: 'source_id')  String sourceId, @JsonKey(name: 'target_id')  String targetId, @JsonKey(name: 'source_type')  String sourceType, @JsonKey(name: 'target_type')  String targetType, @JsonKey(name: 'call_count')  int callCount, @JsonKey(name: 'error_count')  int errorCount, @JsonKey(name: 'error_rate_pct')  double errorRatePct, @JsonKey(name: 'sample_error')  String? sampleError, @JsonKey(name: 'total_tokens')  int edgeTokens, @JsonKey(name: 'input_tokens')  int inputTokens, @JsonKey(name: 'output_tokens')  int outputTokens, @JsonKey(name: 'avg_tokens_per_call')  int avgTokensPerCall, @JsonKey(name: 'avg_duration_ms')  double avgDurationMs, @JsonKey(name: 'p95_duration_ms')  double p95DurationMs, @JsonKey(name: 'unique_sessions')  int uniqueSessions, @JsonKey(name: 'total_cost')  double? totalCost, @JsonKey(name: 'is_back_edge')  bool isBackEdge, @JsonKey(name: 'flow_weight')  double flowWeight)  $default,) {final _that = this;
switch (_that) {
case _MultiTraceEdge():
return $default(_that.sourceId,_that.targetId,_that.sourceType,_that.targetType,_that.callCount,_that.errorCount,_that.errorRatePct,_that.sampleError,_that.edgeTokens,_that.inputTokens,_that.outputTokens,_that.avgTokensPerCall,_that.avgDurationMs,_that.p95DurationMs,_that.uniqueSessions,_that.totalCost,_that.isBackEdge,_that.flowWeight);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function(@JsonKey(name: 'source_id')  String sourceId, @JsonKey(name: 'target_id')  String targetId, @JsonKey(name: 'source_type')  String sourceType, @JsonKey(name: 'target_type')  String targetType, @JsonKey(name: 'call_count')  int callCount, @JsonKey(name: 'error_count')  int errorCount, @JsonKey(name: 'error_rate_pct')  double errorRatePct, @JsonKey(name: 'sample_error')  String? sampleError, @JsonKey(name: 'total_tokens')  int edgeTokens, @JsonKey(name: 'input_tokens')  int inputTokens, @JsonKey(name: 'output_tokens')  int outputTokens, @JsonKey(name: 'avg_tokens_per_call')  int avgTokensPerCall, @JsonKey(name: 'avg_duration_ms')  double avgDurationMs, @JsonKey(name: 'p95_duration_ms')  double p95DurationMs, @JsonKey(name: 'unique_sessions')  int uniqueSessions, @JsonKey(name: 'total_cost')  double? totalCost, @JsonKey(name: 'is_back_edge')  bool isBackEdge, @JsonKey(name: 'flow_weight')  double flowWeight)?  $default,) {final _that = this;
switch (_that) {
case _MultiTraceEdge() when $default != null:
return $default(_that.sourceId,_that.targetId,_that.sourceType,_that.targetType,_that.callCount,_that.errorCount,_that.errorRatePct,_that.sampleError,_that.edgeTokens,_that.inputTokens,_that.outputTokens,_that.avgTokensPerCall,_that.avgDurationMs,_that.p95DurationMs,_that.uniqueSessions,_that.totalCost,_that.isBackEdge,_that.flowWeight);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _MultiTraceEdge implements MultiTraceEdge {
  const _MultiTraceEdge({@JsonKey(name: 'source_id') required this.sourceId, @JsonKey(name: 'target_id') required this.targetId, @JsonKey(name: 'source_type') this.sourceType = '', @JsonKey(name: 'target_type') this.targetType = '', @JsonKey(name: 'call_count') this.callCount = 0, @JsonKey(name: 'error_count') this.errorCount = 0, @JsonKey(name: 'error_rate_pct') this.errorRatePct = 0.0, @JsonKey(name: 'sample_error') this.sampleError, @JsonKey(name: 'total_tokens') this.edgeTokens = 0, @JsonKey(name: 'input_tokens') this.inputTokens = 0, @JsonKey(name: 'output_tokens') this.outputTokens = 0, @JsonKey(name: 'avg_tokens_per_call') this.avgTokensPerCall = 0, @JsonKey(name: 'avg_duration_ms') this.avgDurationMs = 0.0, @JsonKey(name: 'p95_duration_ms') this.p95DurationMs = 0.0, @JsonKey(name: 'unique_sessions') this.uniqueSessions = 0, @JsonKey(name: 'total_cost') this.totalCost, @JsonKey(name: 'is_back_edge') this.isBackEdge = false, @JsonKey(name: 'flow_weight') this.flowWeight = 0.5});
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
@override@JsonKey(name: 'input_tokens') final  int inputTokens;
@override@JsonKey(name: 'output_tokens') final  int outputTokens;
@override@JsonKey(name: 'avg_tokens_per_call') final  int avgTokensPerCall;
@override@JsonKey(name: 'avg_duration_ms') final  double avgDurationMs;
@override@JsonKey(name: 'p95_duration_ms') final  double p95DurationMs;
@override@JsonKey(name: 'unique_sessions') final  int uniqueSessions;
@override@JsonKey(name: 'total_cost') final  double? totalCost;
// Back-edge detection (for cycle rendering)
@override@JsonKey(name: 'is_back_edge') final  bool isBackEdge;
// Normalized flow weight (0.0 to 1.0) for animation speed
@override@JsonKey(name: 'flow_weight') final  double flowWeight;

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
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _MultiTraceEdge&&(identical(other.sourceId, sourceId) || other.sourceId == sourceId)&&(identical(other.targetId, targetId) || other.targetId == targetId)&&(identical(other.sourceType, sourceType) || other.sourceType == sourceType)&&(identical(other.targetType, targetType) || other.targetType == targetType)&&(identical(other.callCount, callCount) || other.callCount == callCount)&&(identical(other.errorCount, errorCount) || other.errorCount == errorCount)&&(identical(other.errorRatePct, errorRatePct) || other.errorRatePct == errorRatePct)&&(identical(other.sampleError, sampleError) || other.sampleError == sampleError)&&(identical(other.edgeTokens, edgeTokens) || other.edgeTokens == edgeTokens)&&(identical(other.inputTokens, inputTokens) || other.inputTokens == inputTokens)&&(identical(other.outputTokens, outputTokens) || other.outputTokens == outputTokens)&&(identical(other.avgTokensPerCall, avgTokensPerCall) || other.avgTokensPerCall == avgTokensPerCall)&&(identical(other.avgDurationMs, avgDurationMs) || other.avgDurationMs == avgDurationMs)&&(identical(other.p95DurationMs, p95DurationMs) || other.p95DurationMs == p95DurationMs)&&(identical(other.uniqueSessions, uniqueSessions) || other.uniqueSessions == uniqueSessions)&&(identical(other.totalCost, totalCost) || other.totalCost == totalCost)&&(identical(other.isBackEdge, isBackEdge) || other.isBackEdge == isBackEdge)&&(identical(other.flowWeight, flowWeight) || other.flowWeight == flowWeight));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,sourceId,targetId,sourceType,targetType,callCount,errorCount,errorRatePct,sampleError,edgeTokens,inputTokens,outputTokens,avgTokensPerCall,avgDurationMs,p95DurationMs,uniqueSessions,totalCost,isBackEdge,flowWeight);

@override
String toString() {
  return 'MultiTraceEdge(sourceId: $sourceId, targetId: $targetId, sourceType: $sourceType, targetType: $targetType, callCount: $callCount, errorCount: $errorCount, errorRatePct: $errorRatePct, sampleError: $sampleError, edgeTokens: $edgeTokens, inputTokens: $inputTokens, outputTokens: $outputTokens, avgTokensPerCall: $avgTokensPerCall, avgDurationMs: $avgDurationMs, p95DurationMs: $p95DurationMs, uniqueSessions: $uniqueSessions, totalCost: $totalCost, isBackEdge: $isBackEdge, flowWeight: $flowWeight)';
}


}

/// @nodoc
abstract mixin class _$MultiTraceEdgeCopyWith<$Res> implements $MultiTraceEdgeCopyWith<$Res> {
  factory _$MultiTraceEdgeCopyWith(_MultiTraceEdge value, $Res Function(_MultiTraceEdge) _then) = __$MultiTraceEdgeCopyWithImpl;
@override @useResult
$Res call({
@JsonKey(name: 'source_id') String sourceId,@JsonKey(name: 'target_id') String targetId,@JsonKey(name: 'source_type') String sourceType,@JsonKey(name: 'target_type') String targetType,@JsonKey(name: 'call_count') int callCount,@JsonKey(name: 'error_count') int errorCount,@JsonKey(name: 'error_rate_pct') double errorRatePct,@JsonKey(name: 'sample_error') String? sampleError,@JsonKey(name: 'total_tokens') int edgeTokens,@JsonKey(name: 'input_tokens') int inputTokens,@JsonKey(name: 'output_tokens') int outputTokens,@JsonKey(name: 'avg_tokens_per_call') int avgTokensPerCall,@JsonKey(name: 'avg_duration_ms') double avgDurationMs,@JsonKey(name: 'p95_duration_ms') double p95DurationMs,@JsonKey(name: 'unique_sessions') int uniqueSessions,@JsonKey(name: 'total_cost') double? totalCost,@JsonKey(name: 'is_back_edge') bool isBackEdge,@JsonKey(name: 'flow_weight') double flowWeight
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
@override @pragma('vm:prefer-inline') $Res call({Object? sourceId = null,Object? targetId = null,Object? sourceType = null,Object? targetType = null,Object? callCount = null,Object? errorCount = null,Object? errorRatePct = null,Object? sampleError = freezed,Object? edgeTokens = null,Object? inputTokens = null,Object? outputTokens = null,Object? avgTokensPerCall = null,Object? avgDurationMs = null,Object? p95DurationMs = null,Object? uniqueSessions = null,Object? totalCost = freezed,Object? isBackEdge = null,Object? flowWeight = null,}) {
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
as int,inputTokens: null == inputTokens ? _self.inputTokens : inputTokens // ignore: cast_nullable_to_non_nullable
as int,outputTokens: null == outputTokens ? _self.outputTokens : outputTokens // ignore: cast_nullable_to_non_nullable
as int,avgTokensPerCall: null == avgTokensPerCall ? _self.avgTokensPerCall : avgTokensPerCall // ignore: cast_nullable_to_non_nullable
as int,avgDurationMs: null == avgDurationMs ? _self.avgDurationMs : avgDurationMs // ignore: cast_nullable_to_non_nullable
as double,p95DurationMs: null == p95DurationMs ? _self.p95DurationMs : p95DurationMs // ignore: cast_nullable_to_non_nullable
as double,uniqueSessions: null == uniqueSessions ? _self.uniqueSessions : uniqueSessions // ignore: cast_nullable_to_non_nullable
as int,totalCost: freezed == totalCost ? _self.totalCost : totalCost // ignore: cast_nullable_to_non_nullable
as double?,isBackEdge: null == isBackEdge ? _self.isBackEdge : isBackEdge // ignore: cast_nullable_to_non_nullable
as bool,flowWeight: null == flowWeight ? _self.flowWeight : flowWeight // ignore: cast_nullable_to_non_nullable
as double,
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>({TResult Function( SelectedNode value)?  node,TResult Function( SelectedEdge value)?  edge,TResult Function( SelectedPath value)?  path,required TResult orElse(),}){
final _that = this;
switch (_that) {
case SelectedNode() when node != null:
return node(_that);case SelectedEdge() when edge != null:
return edge(_that);case SelectedPath() when path != null:
return path(_that);case _:
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

@optionalTypeArgs TResult map<TResult extends Object?>({required TResult Function( SelectedNode value)  node,required TResult Function( SelectedEdge value)  edge,required TResult Function( SelectedPath value)  path,}){
final _that = this;
switch (_that) {
case SelectedNode():
return node(_that);case SelectedEdge():
return edge(_that);case SelectedPath():
return path(_that);}
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>({TResult? Function( SelectedNode value)?  node,TResult? Function( SelectedEdge value)?  edge,TResult? Function( SelectedPath value)?  path,}){
final _that = this;
switch (_that) {
case SelectedNode() when node != null:
return node(_that);case SelectedEdge() when edge != null:
return edge(_that);case SelectedPath() when path != null:
return path(_that);case _:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>({TResult Function( MultiTraceNode node)?  node,TResult Function( MultiTraceEdge edge)?  edge,TResult Function( List<String> nodeIds,  String? label)?  path,required TResult orElse(),}) {final _that = this;
switch (_that) {
case SelectedNode() when node != null:
return node(_that.node);case SelectedEdge() when edge != null:
return edge(_that.edge);case SelectedPath() when path != null:
return path(_that.nodeIds,_that.label);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>({required TResult Function( MultiTraceNode node)  node,required TResult Function( MultiTraceEdge edge)  edge,required TResult Function( List<String> nodeIds,  String? label)  path,}) {final _that = this;
switch (_that) {
case SelectedNode():
return node(_that.node);case SelectedEdge():
return edge(_that.edge);case SelectedPath():
return path(_that.nodeIds,_that.label);}
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>({TResult? Function( MultiTraceNode node)?  node,TResult? Function( MultiTraceEdge edge)?  edge,TResult? Function( List<String> nodeIds,  String? label)?  path,}) {final _that = this;
switch (_that) {
case SelectedNode() when node != null:
return node(_that.node);case SelectedEdge() when edge != null:
return edge(_that.edge);case SelectedPath() when path != null:
return path(_that.nodeIds,_that.label);case _:
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

/// @nodoc


class SelectedPath implements SelectedGraphElement {
  const SelectedPath(final  List<String> nodeIds, {this.label}): _nodeIds = nodeIds;
  

 final  List<String> _nodeIds;
 List<String> get nodeIds {
  if (_nodeIds is EqualUnmodifiableListView) return _nodeIds;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_nodeIds);
}

 final  String? label;

/// Create a copy of SelectedGraphElement
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$SelectedPathCopyWith<SelectedPath> get copyWith => _$SelectedPathCopyWithImpl<SelectedPath>(this, _$identity);



@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is SelectedPath&&const DeepCollectionEquality().equals(other._nodeIds, _nodeIds)&&(identical(other.label, label) || other.label == label));
}


@override
int get hashCode => Object.hash(runtimeType,const DeepCollectionEquality().hash(_nodeIds),label);

@override
String toString() {
  return 'SelectedGraphElement.path(nodeIds: $nodeIds, label: $label)';
}


}

/// @nodoc
abstract mixin class $SelectedPathCopyWith<$Res> implements $SelectedGraphElementCopyWith<$Res> {
  factory $SelectedPathCopyWith(SelectedPath value, $Res Function(SelectedPath) _then) = _$SelectedPathCopyWithImpl;
@useResult
$Res call({
 List<String> nodeIds, String? label
});




}
/// @nodoc
class _$SelectedPathCopyWithImpl<$Res>
    implements $SelectedPathCopyWith<$Res> {
  _$SelectedPathCopyWithImpl(this._self, this._then);

  final SelectedPath _self;
  final $Res Function(SelectedPath) _then;

/// Create a copy of SelectedGraphElement
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') $Res call({Object? nodeIds = null,Object? label = freezed,}) {
  return _then(SelectedPath(
null == nodeIds ? _self._nodeIds : nodeIds // ignore: cast_nullable_to_non_nullable
as List<String>,label: freezed == label ? _self.label : label // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}


}

// dart format on
