// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'dashboard_notifiers.dart';

// **************************************************************************
// RiverpodGenerator
// **************************************************************************

// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint, type=warning

@ProviderFor(Dashboards)
final dashboardsProvider = DashboardsFamily._();

final class DashboardsProvider
    extends $AsyncNotifierProvider<Dashboards, List<DashboardSummary>> {
  DashboardsProvider._({
    required DashboardsFamily super.from,
    required ({String? projectId, bool includeCloud}) super.argument,
  }) : super(
         retry: null,
         name: r'dashboardsProvider',
         isAutoDispose: true,
         dependencies: null,
         $allTransitiveDependencies: null,
       );

  @override
  String debugGetCreateSourceHash() => _$dashboardsHash();

  @override
  String toString() {
    return r'dashboardsProvider'
        ''
        '$argument';
  }

  @$internal
  @override
  Dashboards create() => Dashboards();

  @override
  bool operator ==(Object other) {
    return other is DashboardsProvider && other.argument == argument;
  }

  @override
  int get hashCode {
    return argument.hashCode;
  }
}

String _$dashboardsHash() => r'f6a9e7d7eb2bd6cbae3e189e5bd0e11d1bc0106b';

final class DashboardsFamily extends $Family
    with
        $ClassFamilyOverride<
          Dashboards,
          AsyncValue<List<DashboardSummary>>,
          List<DashboardSummary>,
          FutureOr<List<DashboardSummary>>,
          ({String? projectId, bool includeCloud})
        > {
  DashboardsFamily._()
    : super(
        retry: null,
        name: r'dashboardsProvider',
        dependencies: null,
        $allTransitiveDependencies: null,
        isAutoDispose: true,
      );

  DashboardsProvider call({String? projectId, bool includeCloud = true}) =>
      DashboardsProvider._(
        argument: (projectId: projectId, includeCloud: includeCloud),
        from: this,
      );

  @override
  String toString() => r'dashboardsProvider';
}

abstract class _$Dashboards extends $AsyncNotifier<List<DashboardSummary>> {
  late final _$args = ref.$arg as ({String? projectId, bool includeCloud});
  String? get projectId => _$args.projectId;
  bool get includeCloud => _$args.includeCloud;

  FutureOr<List<DashboardSummary>> build({
    String? projectId,
    bool includeCloud = true,
  });
  @$mustCallSuper
  @override
  void runBuild() {
    final ref =
        this.ref
            as $Ref<AsyncValue<List<DashboardSummary>>, List<DashboardSummary>>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<
                AsyncValue<List<DashboardSummary>>,
                List<DashboardSummary>
              >,
              AsyncValue<List<DashboardSummary>>,
              Object?,
              Object?
            >;
    element.handleCreate(
      ref,
      () =>
          build(projectId: _$args.projectId, includeCloud: _$args.includeCloud),
    );
  }
}

@ProviderFor(DashboardDetail)
final dashboardDetailProvider = DashboardDetailFamily._();

final class DashboardDetailProvider
    extends $AsyncNotifierProvider<DashboardDetail, Dashboard> {
  DashboardDetailProvider._({
    required DashboardDetailFamily super.from,
    required String super.argument,
  }) : super(
         retry: null,
         name: r'dashboardDetailProvider',
         isAutoDispose: true,
         dependencies: null,
         $allTransitiveDependencies: null,
       );

  @override
  String debugGetCreateSourceHash() => _$dashboardDetailHash();

  @override
  String toString() {
    return r'dashboardDetailProvider'
        ''
        '($argument)';
  }

  @$internal
  @override
  DashboardDetail create() => DashboardDetail();

  @override
  bool operator ==(Object other) {
    return other is DashboardDetailProvider && other.argument == argument;
  }

  @override
  int get hashCode {
    return argument.hashCode;
  }
}

String _$dashboardDetailHash() => r'b642c86671e24a8440e4a8dc22af9ae73dac9284';

final class DashboardDetailFamily extends $Family
    with
        $ClassFamilyOverride<
          DashboardDetail,
          AsyncValue<Dashboard>,
          Dashboard,
          FutureOr<Dashboard>,
          String
        > {
  DashboardDetailFamily._()
    : super(
        retry: null,
        name: r'dashboardDetailProvider',
        dependencies: null,
        $allTransitiveDependencies: null,
        isAutoDispose: true,
      );

  DashboardDetailProvider call(String dashboardId) =>
      DashboardDetailProvider._(argument: dashboardId, from: this);

  @override
  String toString() => r'dashboardDetailProvider';
}

abstract class _$DashboardDetail extends $AsyncNotifier<Dashboard> {
  late final _$args = ref.$arg as String;
  String get dashboardId => _$args;

  FutureOr<Dashboard> build(String dashboardId);
  @$mustCallSuper
  @override
  void runBuild() {
    final ref = this.ref as $Ref<AsyncValue<Dashboard>, Dashboard>;
    final element =
        ref.element
            as $ClassProviderElement<
              AnyNotifier<AsyncValue<Dashboard>, Dashboard>,
              AsyncValue<Dashboard>,
              Object?,
              Object?
            >;
    element.handleCreate(ref, () => build(_$args));
  }
}
