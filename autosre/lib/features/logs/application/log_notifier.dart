import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../domain/models.dart';
import '../data/log_repository.dart';

part 'log_notifier.freezed.dart';
part 'log_notifier.g.dart';

@freezed
class LogNotifierState with _$LogNotifierState {
  const factory LogNotifierState({
    @Default([]) List<LogEntry> entries,
    @Default(false) bool isLoading,
    String? error,
    String? nextPageToken,
    String? currentFilter,
    String? projectId,
  }) = _LogNotifierState;
}

@riverpod
class LogNotifier extends _$LogNotifier {
  late final LogRepository _repository;

  @override
  LogNotifierState build() {
    _repository = ref.watch(logRepositoryProvider);
    return const LogNotifierState(isLoading: true);
  }

  Future<void> fetchLogs({
    String? filter,
    String? projectId,
    bool append = false,
  }) async {
    state = state.copyWith(
      isLoading: true,
      error: null,
      currentFilter: filter ?? state.currentFilter,
      projectId: projectId ?? state.projectId,
    );

    try {
      final data = await _repository.queryLogs(
        filter: state.currentFilter ?? '',
        projectId: state.projectId,
        pageToken: append ? state.nextPageToken : null,
      );

      state = state.copyWith(
        entries: append ? [...state.entries, ...data.entries] : data.entries,
        isLoading: false,
        nextPageToken: data.nextPageToken,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  void loadMore() {
    if (state.nextPageToken != null && !state.isLoading) {
      fetchLogs(append: true);
    }
  }
}
