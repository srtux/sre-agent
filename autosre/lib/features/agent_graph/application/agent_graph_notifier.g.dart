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
    r'aa078ef42633570df6156aefed6a9382acd3d392';

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
