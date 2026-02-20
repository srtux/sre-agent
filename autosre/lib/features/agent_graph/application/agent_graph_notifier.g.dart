// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'agent_graph_notifier.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(AgentGraphNotifier)
final agentGraphProvider = AgentGraphNotifierProvider._();

final class AgentGraphNotifierProvider
    extends $NotifierProvider<AgentGraphNotifier, AgentGraphState> {
  AgentGraphNotifierProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'agentGraphProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$agentGraphNotifierHash();

  @$internal
  @override
  AgentGraphNotifier create() => AgentGraphNotifier();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(AgentGraphState value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<AgentGraphState>(value),
    );
  }
}

String _$agentGraphNotifierHash() =>
    r'd14e5b19aff1690ece6b6b0843d0419abe1730a5';

abstract class _$AgentGraphNotifier extends $Notifier<AgentGraphState> {
  AgentGraphState build();
  @$mustCallSuper
  @override
  void runBuild() {
    final ref = this.ref as $Ref<AgentGraphState, AgentGraphState>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<AgentGraphState, AgentGraphState>,
              AgentGraphState,
              Object?,
              Object?
            >;
    element.handleCreate(ref, build);
  }
}

@ProviderFor(fetchExtendedNodeDetails)
final fetchExtendedNodeDetailsProvider = FetchExtendedNodeDetailsFamily._();

final class FetchExtendedNodeDetailsProvider
    extends
        $FunctionalProvider<
          AsyncValue<Map<String, dynamic>>,
          Map<String, dynamic>,
          FutureOr<Map<String, dynamic>>
        >
    with
        $FutureModifier<Map<String, dynamic>>,
        $FutureProvider<Map<String, dynamic>> {
  FetchExtendedNodeDetailsProvider._({
    required FetchExtendedNodeDetailsFamily super.from,
    required String super.argument,
  }) : super(
         retry: null,
         name: r'fetchExtendedNodeDetailsProvider',
         isAutoDispose: true,
         dependencies: null,
         $allTransitiveDependencies: null,
       );

  @override
  String debugGetCreateSourceHash() => _$fetchExtendedNodeDetailsHash();

  @override
  String toString() {
    return r'fetchExtendedNodeDetailsProvider'
        ''
        '($argument)';
  }

  @$internal
  @override
  $FutureProviderElement<Map<String, dynamic>> $createElement(
    $ProviderPointer pointer,
  ) => $FutureProviderElement(pointer);

  @override
  FutureOr<Map<String, dynamic>> create(Ref ref) {
    final argument = this.argument as String;
    return fetchExtendedNodeDetails(ref, argument);
  }

  @override
  bool operator ==(Object other) {
    return other is FetchExtendedNodeDetailsProvider &&
        other.argument == argument;
  }

  @override
  int get hashCode {
    return argument.hashCode;
  }
}

String _$fetchExtendedNodeDetailsHash() =>
    r'd156318de6255bc4f61b0d4ab70b17594eecd473';

final class FetchExtendedNodeDetailsFamily extends $Family
    with $FunctionalFamilyOverride<FutureOr<Map<String, dynamic>>, String> {
  FetchExtendedNodeDetailsFamily._()
    : super(
        retry: null,
        name: r'fetchExtendedNodeDetailsProvider',
        dependencies: null,
        $allTransitiveDependencies: null,
        isAutoDispose: true,
      );

  FetchExtendedNodeDetailsProvider call(String nodeId) =>
      FetchExtendedNodeDetailsProvider._(argument: nodeId, from: this);

  @override
  String toString() => r'fetchExtendedNodeDetailsProvider';
}

@ProviderFor(fetchExtendedEdgeDetails)
final fetchExtendedEdgeDetailsProvider = FetchExtendedEdgeDetailsFamily._();

final class FetchExtendedEdgeDetailsProvider
    extends
        $FunctionalProvider<
          AsyncValue<Map<String, dynamic>>,
          Map<String, dynamic>,
          FutureOr<Map<String, dynamic>>
        >
    with
        $FutureModifier<Map<String, dynamic>>,
        $FutureProvider<Map<String, dynamic>> {
  FetchExtendedEdgeDetailsProvider._({
    required FetchExtendedEdgeDetailsFamily super.from,
    required (String, String) super.argument,
  }) : super(
         retry: null,
         name: r'fetchExtendedEdgeDetailsProvider',
         isAutoDispose: true,
         dependencies: null,
         $allTransitiveDependencies: null,
       );

  @override
  String debugGetCreateSourceHash() => _$fetchExtendedEdgeDetailsHash();

  @override
  String toString() {
    return r'fetchExtendedEdgeDetailsProvider'
        ''
        '$argument';
  }

  @$internal
  @override
  $FutureProviderElement<Map<String, dynamic>> $createElement(
    $ProviderPointer pointer,
  ) => $FutureProviderElement(pointer);

  @override
  FutureOr<Map<String, dynamic>> create(Ref ref) {
    final argument = this.argument as (String, String);
    return fetchExtendedEdgeDetails(ref, argument.$1, argument.$2);
  }

  @override
  bool operator ==(Object other) {
    return other is FetchExtendedEdgeDetailsProvider &&
        other.argument == argument;
  }

  @override
  int get hashCode {
    return argument.hashCode;
  }
}

String _$fetchExtendedEdgeDetailsHash() =>
    r'b98390e674c1eb883cc3b74cb5d9f870e5c8cef0';

final class FetchExtendedEdgeDetailsFamily extends $Family
    with
        $FunctionalFamilyOverride<
          FutureOr<Map<String, dynamic>>,
          (String, String)
        > {
  FetchExtendedEdgeDetailsFamily._()
    : super(
        retry: null,
        name: r'fetchExtendedEdgeDetailsProvider',
        dependencies: null,
        $allTransitiveDependencies: null,
        isAutoDispose: true,
      );

  FetchExtendedEdgeDetailsProvider call(String sourceId, String targetId) =>
      FetchExtendedEdgeDetailsProvider._(
        argument: (sourceId, targetId),
        from: this,
      );

  @override
  String toString() => r'fetchExtendedEdgeDetailsProvider';
}
