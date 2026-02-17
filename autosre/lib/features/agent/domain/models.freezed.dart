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
mixin _$AgentNode implements DiagnosticableTreeMixin {

 String get id; String get name; String get type;// 'coordinator', 'sub_agent', 'tool', 'data_source'
 String get status;// 'idle', 'active', 'completed', 'error'
 List<String> get connections; Map<String, dynamic>? get metadata;
/// Create a copy of AgentNode
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$AgentNodeCopyWith<AgentNode> get copyWith => _$AgentNodeCopyWithImpl<AgentNode>(this as AgentNode, _$identity);

  /// Serializes this AgentNode to a JSON map.
  Map<String, dynamic> toJson();

@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'AgentNode'))
    ..add(DiagnosticsProperty('id', id))..add(DiagnosticsProperty('name', name))..add(DiagnosticsProperty('type', type))..add(DiagnosticsProperty('status', status))..add(DiagnosticsProperty('connections', connections))..add(DiagnosticsProperty('metadata', metadata));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is AgentNode&&(identical(other.id, id) || other.id == id)&&(identical(other.name, name) || other.name == name)&&(identical(other.type, type) || other.type == type)&&(identical(other.status, status) || other.status == status)&&const DeepCollectionEquality().equals(other.connections, connections)&&const DeepCollectionEquality().equals(other.metadata, metadata));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,id,name,type,status,const DeepCollectionEquality().hash(connections),const DeepCollectionEquality().hash(metadata));

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'AgentNode(id: $id, name: $name, type: $type, status: $status, connections: $connections, metadata: $metadata)';
}


}

/// @nodoc
abstract mixin class $AgentNodeCopyWith<$Res>  {
  factory $AgentNodeCopyWith(AgentNode value, $Res Function(AgentNode) _then) = _$AgentNodeCopyWithImpl;
@useResult
$Res call({
 String id, String name, String type, String status, List<String> connections, Map<String, dynamic>? metadata
});




}
/// @nodoc
class _$AgentNodeCopyWithImpl<$Res>
    implements $AgentNodeCopyWith<$Res> {
  _$AgentNodeCopyWithImpl(this._self, this._then);

  final AgentNode _self;
  final $Res Function(AgentNode) _then;

/// Create a copy of AgentNode
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? id = null,Object? name = null,Object? type = null,Object? status = null,Object? connections = null,Object? metadata = freezed,}) {
  return _then(_self.copyWith(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,type: null == type ? _self.type : type // ignore: cast_nullable_to_non_nullable
as String,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as String,connections: null == connections ? _self.connections : connections // ignore: cast_nullable_to_non_nullable
as List<String>,metadata: freezed == metadata ? _self.metadata : metadata // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>?,
  ));
}

}


/// Adds pattern-matching-related methods to [AgentNode].
extension AgentNodePatterns on AgentNode {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _AgentNode value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _AgentNode() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _AgentNode value)  $default,){
final _that = this;
switch (_that) {
case _AgentNode():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _AgentNode value)?  $default,){
final _that = this;
switch (_that) {
case _AgentNode() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( String id,  String name,  String type,  String status,  List<String> connections,  Map<String, dynamic>? metadata)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _AgentNode() when $default != null:
return $default(_that.id,_that.name,_that.type,_that.status,_that.connections,_that.metadata);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( String id,  String name,  String type,  String status,  List<String> connections,  Map<String, dynamic>? metadata)  $default,) {final _that = this;
switch (_that) {
case _AgentNode():
return $default(_that.id,_that.name,_that.type,_that.status,_that.connections,_that.metadata);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( String id,  String name,  String type,  String status,  List<String> connections,  Map<String, dynamic>? metadata)?  $default,) {final _that = this;
switch (_that) {
case _AgentNode() when $default != null:
return $default(_that.id,_that.name,_that.type,_that.status,_that.connections,_that.metadata);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _AgentNode with DiagnosticableTreeMixin implements AgentNode {
  const _AgentNode({required this.id, required this.name, required this.type, required this.status, final  List<String> connections = const [], final  Map<String, dynamic>? metadata}): _connections = connections,_metadata = metadata;
  factory _AgentNode.fromJson(Map<String, dynamic> json) => _$AgentNodeFromJson(json);

@override final  String id;
@override final  String name;
@override final  String type;
// 'coordinator', 'sub_agent', 'tool', 'data_source'
@override final  String status;
// 'idle', 'active', 'completed', 'error'
 final  List<String> _connections;
// 'idle', 'active', 'completed', 'error'
@override@JsonKey() List<String> get connections {
  if (_connections is EqualUnmodifiableListView) return _connections;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_connections);
}

 final  Map<String, dynamic>? _metadata;
@override Map<String, dynamic>? get metadata {
  final value = _metadata;
  if (value == null) return null;
  if (_metadata is EqualUnmodifiableMapView) return _metadata;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableMapView(value);
}


/// Create a copy of AgentNode
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$AgentNodeCopyWith<_AgentNode> get copyWith => __$AgentNodeCopyWithImpl<_AgentNode>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$AgentNodeToJson(this, );
}
@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'AgentNode'))
    ..add(DiagnosticsProperty('id', id))..add(DiagnosticsProperty('name', name))..add(DiagnosticsProperty('type', type))..add(DiagnosticsProperty('status', status))..add(DiagnosticsProperty('connections', connections))..add(DiagnosticsProperty('metadata', metadata));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _AgentNode&&(identical(other.id, id) || other.id == id)&&(identical(other.name, name) || other.name == name)&&(identical(other.type, type) || other.type == type)&&(identical(other.status, status) || other.status == status)&&const DeepCollectionEquality().equals(other._connections, _connections)&&const DeepCollectionEquality().equals(other._metadata, _metadata));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,id,name,type,status,const DeepCollectionEquality().hash(_connections),const DeepCollectionEquality().hash(_metadata));

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'AgentNode(id: $id, name: $name, type: $type, status: $status, connections: $connections, metadata: $metadata)';
}


}

/// @nodoc
abstract mixin class _$AgentNodeCopyWith<$Res> implements $AgentNodeCopyWith<$Res> {
  factory _$AgentNodeCopyWith(_AgentNode value, $Res Function(_AgentNode) _then) = __$AgentNodeCopyWithImpl;
@override @useResult
$Res call({
 String id, String name, String type, String status, List<String> connections, Map<String, dynamic>? metadata
});




}
/// @nodoc
class __$AgentNodeCopyWithImpl<$Res>
    implements _$AgentNodeCopyWith<$Res> {
  __$AgentNodeCopyWithImpl(this._self, this._then);

  final _AgentNode _self;
  final $Res Function(_AgentNode) _then;

/// Create a copy of AgentNode
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? id = null,Object? name = null,Object? type = null,Object? status = null,Object? connections = null,Object? metadata = freezed,}) {
  return _then(_AgentNode(
id: null == id ? _self.id : id // ignore: cast_nullable_to_non_nullable
as String,name: null == name ? _self.name : name // ignore: cast_nullable_to_non_nullable
as String,type: null == type ? _self.type : type // ignore: cast_nullable_to_non_nullable
as String,status: null == status ? _self.status : status // ignore: cast_nullable_to_non_nullable
as String,connections: null == connections ? _self._connections : connections // ignore: cast_nullable_to_non_nullable
as List<String>,metadata: freezed == metadata ? _self._metadata : metadata // ignore: cast_nullable_to_non_nullable
as Map<String, dynamic>?,
  ));
}


}


/// @nodoc
mixin _$AgentActivityData implements DiagnosticableTreeMixin {

 List<AgentNode> get nodes;@JsonKey(name: 'current_phase') String get currentPhase;@JsonKey(name: 'active_node_id') String? get activeNodeId;@JsonKey(name: 'completed_steps') List<String> get completedSteps; String? get message;
/// Create a copy of AgentActivityData
/// with the given fields replaced by the non-null parameter values.
@JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
$AgentActivityDataCopyWith<AgentActivityData> get copyWith => _$AgentActivityDataCopyWithImpl<AgentActivityData>(this as AgentActivityData, _$identity);

  /// Serializes this AgentActivityData to a JSON map.
  Map<String, dynamic> toJson();

@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'AgentActivityData'))
    ..add(DiagnosticsProperty('nodes', nodes))..add(DiagnosticsProperty('currentPhase', currentPhase))..add(DiagnosticsProperty('activeNodeId', activeNodeId))..add(DiagnosticsProperty('completedSteps', completedSteps))..add(DiagnosticsProperty('message', message));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is AgentActivityData&&const DeepCollectionEquality().equals(other.nodes, nodes)&&(identical(other.currentPhase, currentPhase) || other.currentPhase == currentPhase)&&(identical(other.activeNodeId, activeNodeId) || other.activeNodeId == activeNodeId)&&const DeepCollectionEquality().equals(other.completedSteps, completedSteps)&&(identical(other.message, message) || other.message == message));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,const DeepCollectionEquality().hash(nodes),currentPhase,activeNodeId,const DeepCollectionEquality().hash(completedSteps),message);

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'AgentActivityData(nodes: $nodes, currentPhase: $currentPhase, activeNodeId: $activeNodeId, completedSteps: $completedSteps, message: $message)';
}


}

/// @nodoc
abstract mixin class $AgentActivityDataCopyWith<$Res>  {
  factory $AgentActivityDataCopyWith(AgentActivityData value, $Res Function(AgentActivityData) _then) = _$AgentActivityDataCopyWithImpl;
@useResult
$Res call({
 List<AgentNode> nodes,@JsonKey(name: 'current_phase') String currentPhase,@JsonKey(name: 'active_node_id') String? activeNodeId,@JsonKey(name: 'completed_steps') List<String> completedSteps, String? message
});




}
/// @nodoc
class _$AgentActivityDataCopyWithImpl<$Res>
    implements $AgentActivityDataCopyWith<$Res> {
  _$AgentActivityDataCopyWithImpl(this._self, this._then);

  final AgentActivityData _self;
  final $Res Function(AgentActivityData) _then;

/// Create a copy of AgentActivityData
/// with the given fields replaced by the non-null parameter values.
@pragma('vm:prefer-inline') @override $Res call({Object? nodes = null,Object? currentPhase = null,Object? activeNodeId = freezed,Object? completedSteps = null,Object? message = freezed,}) {
  return _then(_self.copyWith(
nodes: null == nodes ? _self.nodes : nodes // ignore: cast_nullable_to_non_nullable
as List<AgentNode>,currentPhase: null == currentPhase ? _self.currentPhase : currentPhase // ignore: cast_nullable_to_non_nullable
as String,activeNodeId: freezed == activeNodeId ? _self.activeNodeId : activeNodeId // ignore: cast_nullable_to_non_nullable
as String?,completedSteps: null == completedSteps ? _self.completedSteps : completedSteps // ignore: cast_nullable_to_non_nullable
as List<String>,message: freezed == message ? _self.message : message // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}

}


/// Adds pattern-matching-related methods to [AgentActivityData].
extension AgentActivityDataPatterns on AgentActivityData {
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

@optionalTypeArgs TResult maybeMap<TResult extends Object?>(TResult Function( _AgentActivityData value)?  $default,{required TResult orElse(),}){
final _that = this;
switch (_that) {
case _AgentActivityData() when $default != null:
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

@optionalTypeArgs TResult map<TResult extends Object?>(TResult Function( _AgentActivityData value)  $default,){
final _that = this;
switch (_that) {
case _AgentActivityData():
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

@optionalTypeArgs TResult? mapOrNull<TResult extends Object?>(TResult? Function( _AgentActivityData value)?  $default,){
final _that = this;
switch (_that) {
case _AgentActivityData() when $default != null:
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

@optionalTypeArgs TResult maybeWhen<TResult extends Object?>(TResult Function( List<AgentNode> nodes, @JsonKey(name: 'current_phase')  String currentPhase, @JsonKey(name: 'active_node_id')  String? activeNodeId, @JsonKey(name: 'completed_steps')  List<String> completedSteps,  String? message)?  $default,{required TResult orElse(),}) {final _that = this;
switch (_that) {
case _AgentActivityData() when $default != null:
return $default(_that.nodes,_that.currentPhase,_that.activeNodeId,_that.completedSteps,_that.message);case _:
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

@optionalTypeArgs TResult when<TResult extends Object?>(TResult Function( List<AgentNode> nodes, @JsonKey(name: 'current_phase')  String currentPhase, @JsonKey(name: 'active_node_id')  String? activeNodeId, @JsonKey(name: 'completed_steps')  List<String> completedSteps,  String? message)  $default,) {final _that = this;
switch (_that) {
case _AgentActivityData():
return $default(_that.nodes,_that.currentPhase,_that.activeNodeId,_that.completedSteps,_that.message);case _:
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

@optionalTypeArgs TResult? whenOrNull<TResult extends Object?>(TResult? Function( List<AgentNode> nodes, @JsonKey(name: 'current_phase')  String currentPhase, @JsonKey(name: 'active_node_id')  String? activeNodeId, @JsonKey(name: 'completed_steps')  List<String> completedSteps,  String? message)?  $default,) {final _that = this;
switch (_that) {
case _AgentActivityData() when $default != null:
return $default(_that.nodes,_that.currentPhase,_that.activeNodeId,_that.completedSteps,_that.message);case _:
  return null;

}
}

}

/// @nodoc
@JsonSerializable()

class _AgentActivityData with DiagnosticableTreeMixin implements AgentActivityData {
  const _AgentActivityData({required final  List<AgentNode> nodes, @JsonKey(name: 'current_phase') required this.currentPhase, @JsonKey(name: 'active_node_id') this.activeNodeId, @JsonKey(name: 'completed_steps') final  List<String> completedSteps = const [], this.message}): _nodes = nodes,_completedSteps = completedSteps;
  factory _AgentActivityData.fromJson(Map<String, dynamic> json) => _$AgentActivityDataFromJson(json);

 final  List<AgentNode> _nodes;
@override List<AgentNode> get nodes {
  if (_nodes is EqualUnmodifiableListView) return _nodes;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_nodes);
}

@override@JsonKey(name: 'current_phase') final  String currentPhase;
@override@JsonKey(name: 'active_node_id') final  String? activeNodeId;
 final  List<String> _completedSteps;
@override@JsonKey(name: 'completed_steps') List<String> get completedSteps {
  if (_completedSteps is EqualUnmodifiableListView) return _completedSteps;
  // ignore: implicit_dynamic_type
  return EqualUnmodifiableListView(_completedSteps);
}

@override final  String? message;

/// Create a copy of AgentActivityData
/// with the given fields replaced by the non-null parameter values.
@override @JsonKey(includeFromJson: false, includeToJson: false)
@pragma('vm:prefer-inline')
_$AgentActivityDataCopyWith<_AgentActivityData> get copyWith => __$AgentActivityDataCopyWithImpl<_AgentActivityData>(this, _$identity);

@override
Map<String, dynamic> toJson() {
  return _$AgentActivityDataToJson(this, );
}
@override
void debugFillProperties(DiagnosticPropertiesBuilder properties) {
  properties
    ..add(DiagnosticsProperty('type', 'AgentActivityData'))
    ..add(DiagnosticsProperty('nodes', nodes))..add(DiagnosticsProperty('currentPhase', currentPhase))..add(DiagnosticsProperty('activeNodeId', activeNodeId))..add(DiagnosticsProperty('completedSteps', completedSteps))..add(DiagnosticsProperty('message', message));
}

@override
bool operator ==(Object other) {
  return identical(this, other) || (other.runtimeType == runtimeType&&other is _AgentActivityData&&const DeepCollectionEquality().equals(other._nodes, _nodes)&&(identical(other.currentPhase, currentPhase) || other.currentPhase == currentPhase)&&(identical(other.activeNodeId, activeNodeId) || other.activeNodeId == activeNodeId)&&const DeepCollectionEquality().equals(other._completedSteps, _completedSteps)&&(identical(other.message, message) || other.message == message));
}

@JsonKey(includeFromJson: false, includeToJson: false)
@override
int get hashCode => Object.hash(runtimeType,const DeepCollectionEquality().hash(_nodes),currentPhase,activeNodeId,const DeepCollectionEquality().hash(_completedSteps),message);

@override
String toString({ DiagnosticLevel minLevel = DiagnosticLevel.info }) {
  return 'AgentActivityData(nodes: $nodes, currentPhase: $currentPhase, activeNodeId: $activeNodeId, completedSteps: $completedSteps, message: $message)';
}


}

/// @nodoc
abstract mixin class _$AgentActivityDataCopyWith<$Res> implements $AgentActivityDataCopyWith<$Res> {
  factory _$AgentActivityDataCopyWith(_AgentActivityData value, $Res Function(_AgentActivityData) _then) = __$AgentActivityDataCopyWithImpl;
@override @useResult
$Res call({
 List<AgentNode> nodes,@JsonKey(name: 'current_phase') String currentPhase,@JsonKey(name: 'active_node_id') String? activeNodeId,@JsonKey(name: 'completed_steps') List<String> completedSteps, String? message
});




}
/// @nodoc
class __$AgentActivityDataCopyWithImpl<$Res>
    implements _$AgentActivityDataCopyWith<$Res> {
  __$AgentActivityDataCopyWithImpl(this._self, this._then);

  final _AgentActivityData _self;
  final $Res Function(_AgentActivityData) _then;

/// Create a copy of AgentActivityData
/// with the given fields replaced by the non-null parameter values.
@override @pragma('vm:prefer-inline') $Res call({Object? nodes = null,Object? currentPhase = null,Object? activeNodeId = freezed,Object? completedSteps = null,Object? message = freezed,}) {
  return _then(_AgentActivityData(
nodes: null == nodes ? _self._nodes : nodes // ignore: cast_nullable_to_non_nullable
as List<AgentNode>,currentPhase: null == currentPhase ? _self.currentPhase : currentPhase // ignore: cast_nullable_to_non_nullable
as String,activeNodeId: freezed == activeNodeId ? _self.activeNodeId : activeNodeId // ignore: cast_nullable_to_non_nullable
as String?,completedSteps: null == completedSteps ? _self._completedSteps : completedSteps // ignore: cast_nullable_to_non_nullable
as List<String>,message: freezed == message ? _self.message : message // ignore: cast_nullable_to_non_nullable
as String?,
  ));
}


}

// dart format on
