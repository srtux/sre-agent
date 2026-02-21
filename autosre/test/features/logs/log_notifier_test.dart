import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/features/logs/application/log_notifier.dart';
import 'package:autosre/features/logs/data/log_repository.dart';
import 'package:autosre/features/logs/domain/models.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class MockLogRepository extends Fake implements LogRepository {
  LogEntriesData? mockResult;
  Object? mockError;
  String? lastFilter;
  DateTime? lastCursorTimestamp;
  String? lastCursorInsertId;

  @override
  Future<LogEntriesData> queryLogs({
    required String filter,
    String? projectId,
    DateTime? cursorTimestamp,
    String? cursorInsertId,
    int? limit,
    int? minutesAgo,
  }) async {
    lastFilter = filter;
    lastCursorTimestamp = cursorTimestamp;
    lastCursorInsertId = cursorInsertId;
    if (mockError != null) throw mockError!;
    return mockResult ?? const LogEntriesData(entries: []);
  }
}

void main() {
  late MockLogRepository mockRepository;

  setUp(() {
    mockRepository = MockLogRepository();
  });

  ProviderContainer createContainer({
    required MockLogRepository mockRepository,
  }) {
    final container = ProviderContainer(
      overrides: [logRepositoryProvider.overrideWithValue(mockRepository)],
    );
    addTearDown(container.dispose);
    return container;
  }

  group('LogNotifier', () {
    test('initial state is loading', () {
      final container = createContainer(mockRepository: mockRepository);
      final state = container.read(logProvider);
      expect(state.isLoading, true);
      expect(state.entries, isEmpty);
    });

    test('fetchLogs updates state on success', () async {
      final container = createContainer(mockRepository: mockRepository);
      final notifier = container.read(logProvider.notifier);

      final entryTimestamp = DateTime.parse('2026-02-16T00:00:00Z');
      final mockEntries = LogEntriesData(
        entries: [
          LogEntry(
            insertId: 'entry1',
            timestamp: entryTimestamp,
            payload: 'Test log',
          ),
        ],
      );

      mockRepository.mockResult = mockEntries;

      await notifier.fetchLogs(filter: 'test');

      final state = container.read(logProvider);
      expect(state.isLoading, false);
      expect(state.entries.length, 1);
      expect(state.entries.first.payload, 'Test log');
      // Cursor is derived from the oldest entry
      expect(state.oldestEntryTimestamp, entryTimestamp);
      expect(state.oldestEntryInsertId, 'entry1');
      expect(state.noMoreOldEntries, true); // 1 entry < default limit of 50
      expect(mockRepository.lastFilter, 'test');
    });

    test('fetchLogs with append=true passes cursor to repository', () async {
      final container = createContainer(mockRepository: mockRepository);
      final notifier = container.read(logProvider.notifier);

      final oldTs = DateTime.parse('2026-02-16T00:00:00Z');
      // Prime the state with an existing entry so there's a cursor to pass
      mockRepository.mockResult = LogEntriesData(
        entries: [LogEntry(insertId: 'old1', timestamp: oldTs, payload: 'Old')],
      );
      await notifier.fetchLogs(filter: 'test');

      // Now load more (append)
      final newerTs = DateTime.parse('2026-02-16T01:00:00Z');
      mockRepository.mockResult = LogEntriesData(
        entries: [
          LogEntry(insertId: 'old2', timestamp: newerTs, payload: 'Old2'),
        ],
      );
      await notifier.fetchLogs(filter: 'test', append: true);

      expect(mockRepository.lastCursorTimestamp, oldTs);
      expect(mockRepository.lastCursorInsertId, 'old1');
    });

    test('noMoreOldEntries is false when full page returned', () async {
      final container = createContainer(mockRepository: mockRepository);
      final notifier = container.read(logProvider.notifier);

      // Return exactly limit entries to signal there may be more
      const limit = 2;
      mockRepository.mockResult = LogEntriesData(
        entries: List.generate(
          limit,
          (i) => LogEntry(
            insertId: 'e$i',
            timestamp: DateTime.parse('2026-02-16T00:00:0${i}Z'),
            payload: 'log $i',
          ),
        ),
      );

      await notifier.fetchLogs(filter: '', limit: limit);

      final state = container.read(logProvider);
      expect(state.noMoreOldEntries, false);
    });

    test('loadMore is no-op when noMoreOldEntries is true', () async {
      final container = createContainer(mockRepository: mockRepository);
      final notifier = container.read(logProvider.notifier);

      // Empty result → noMoreOldEntries = true
      mockRepository.mockResult = const LogEntriesData(entries: []);
      await notifier.fetchLogs(filter: '');
      expect(container.read(logProvider).noMoreOldEntries, true);

      // loadMore should not trigger a repository call
      notifier.loadMore();

      // State remains unchanged
      final state = container.read(logProvider);
      expect(state.entries, isEmpty);
    });

    group('LogNotifier Error Handling', () {
      test('fetchLogs updates state with error on failure', () async {
        final container = createContainer(mockRepository: mockRepository);
        final notifier = container.read(logProvider.notifier);

        mockRepository.mockError = Exception('Failed to fetch logs');

        await notifier.fetchLogs(filter: 'test');

        final state = container.read(logProvider);
        expect(state.isLoading, false);
        expect(state.error, contains('Failed to fetch logs'));
      });
    });
  });
}
