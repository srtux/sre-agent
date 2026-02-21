import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../domain/models.dart';
import '../data/log_repository.dart';

part 'log_notifier.freezed.dart';
part 'log_notifier.g.dart';

@freezed
abstract class LogNotifierState with _$LogNotifierState {
  const factory LogNotifierState({
    @Default([]) List<LogEntry> entries,
    @Default(false) bool isLoading,
    String? error,

    /// Timestamp of the oldest loaded entry; used as the cursor for
    /// loading older entries (cursor-based pagination).
    DateTime? oldestEntryTimestamp,
    String? oldestEntryInsertId,
    @Default(false) bool noMoreOldEntries,
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
    int minutesAgo = 15,
    int limit = 50,
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
        cursorTimestamp: append ? state.oldestEntryTimestamp : null,
        cursorInsertId: append ? state.oldestEntryInsertId : null,
        limit: limit,
        minutesAgo: append ? null : minutesAgo,
      );

      final allEntries = append
          ? [...state.entries, ...data.entries]
          : data.entries;

      // Track the oldest entry for next cursor page
      DateTime? oldestTs;
      String? oldestId;
      if (allEntries.isNotEmpty) {
        final oldest = allEntries.reduce(
          (a, b) => a.timestamp.isBefore(b.timestamp) ? a : b,
        );
        oldestTs = oldest.timestamp;
        oldestId = oldest.insertId;
      }

      state = state.copyWith(
        entries: allEntries,
        isLoading: false,
        oldestEntryTimestamp: oldestTs,
        oldestEntryInsertId: oldestId,
        noMoreOldEntries: data.entries.length < limit,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  void loadMore() {
    if (!state.noMoreOldEntries &&
        !state.isLoading &&
        state.entries.isNotEmpty) {
      fetchLogs(append: true);
    }
  }
}
