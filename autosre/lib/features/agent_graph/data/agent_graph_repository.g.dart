// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'agent_graph_repository.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(agentGraphRepository)
final agentGraphRepositoryProvider = AgentGraphRepositoryProvider._();

final class AgentGraphRepositoryProvider
    extends
        $FunctionalProvider<
          AgentGraphRepository,
          AgentGraphRepository,
          AgentGraphRepository
        >
    with $Provider<AgentGraphRepository> {
  AgentGraphRepositoryProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'agentGraphRepositoryProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$agentGraphRepositoryHash();

  @$internal
  @override
  $ProviderElement<AgentGraphRepository> $createElement(
    $ProviderPointer pointer,
  ) => $ProviderElement(pointer);

  @override
  AgentGraphRepository create(Ref ref) {
    return agentGraphRepository(ref);
  }

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(AgentGraphRepository value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<AgentGraphRepository>(value),
    );
  }
}

String _$agentGraphRepositoryHash() =>
    r'0d9b17027822ff723be0499977d81cc3f1cf60f3';
