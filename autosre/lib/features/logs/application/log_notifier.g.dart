// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'log_notifier.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(LogNotifier)
final logProvider = LogNotifierProvider._();

final class LogNotifierProvider
    extends $NotifierProvider<LogNotifier, LogNotifierState> {
  LogNotifierProvider._()
    : super(
        from: null,
        argument: null,
        retry: null,
        name: r'logProvider',
        isAutoDispose: true,
        dependencies: null,
        $allTransitiveDependencies: null,
      );

  @override
  String debugGetCreateSourceHash() => _$logNotifierHash();

  @$internal
  @override
  LogNotifier create() => LogNotifier();

  /// {@macro riverpod.override_with_value}
  Override overrideWithValue(LogNotifierState value) {
    return $ProviderOverride(
      origin: this,
      providerOverride: $SyncValueProvider<LogNotifierState>(value),
    );
  }
}

String _$logNotifierHash() => r'b07e070c4957cbff1ead81d35d392b92a8231d2a';

abstract class _$LogNotifier extends $Notifier<LogNotifierState> {
  LogNotifierState build();
  @$mustCallSuper
  @override
  void runBuild() {
    final ref = this.ref as $Ref<LogNotifierState, LogNotifierState>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<LogNotifierState, LogNotifierState>,
              LogNotifierState,
              Object?,
              Object?
            >;
    element.handleCreate(ref, build);
  }
}
