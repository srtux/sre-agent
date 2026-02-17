import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/features/logs/application/log_notifier.dart';
import 'package:autosre/features/logs/data/log_repository.dart';
import 'package:autosre/features/logs/domain/models.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class MockLogRepository extends Fake implements LogRepository {
  LogEntriesData? mockResult;
  Object? mockError;
  String? lastFilter;

  @override
  Future<LogEntriesData> queryLogs({
    required String filter,
    String? projectId,
    String? pageToken,
    int? limit,
  }) async {
    lastFilter = filter;
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
      overrides: [
        logRepositoryProvider.overrideWithValue(mockRepository),
      ],
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

      final mockEntries = LogEntriesData(
        entries: [
          LogEntry(
            insertId: '1',
            timestamp: DateTime.now(),
            payload: 'Test log',
          ),
        ],
        nextPageToken: 'token123',
      );

      mockRepository.mockResult = mockEntries;

      await notifier.fetchLogs(filter: 'test');

      final state = container.read(logProvider);
      expect(state.isLoading, false);
      expect(state.entries.length, 1);
      expect(state.entries.first.payload, 'Test log');
      expect(state.nextPageToken, 'token123');
      expect(mockRepository.lastFilter, 'test');
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
