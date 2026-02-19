import 'dart:async';

import 'package:autosre/features/agent_graph/application/agent_graph_notifier.dart';
import 'package:autosre/features/agent_graph/data/agent_graph_repository.dart';
import 'package:autosre/features/agent_graph/domain/models.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

class MockAgentGraphRepository extends Fake implements AgentGraphRepository {
  MultiTraceGraphPayload? mockResult;
  Object? mockError;
  Completer<MultiTraceGraphPayload>? completer;

  @override
  Future<MultiTraceGraphPayload> fetchGraph({
    String dataset = kDefaultDataset,
    int timeRangeHours = 6,
    String? projectId,
  }) async {
    if (completer != null) return completer!.future;
    if (mockError != null) throw mockError!;
    return mockResult ?? const MultiTraceGraphPayload();
  }
}

void main() {
  late MockAgentGraphRepository mockRepository;

  setUp(() {
    mockRepository = MockAgentGraphRepository();
  });

  ProviderContainer createContainer({
    required MockAgentGraphRepository mockRepository,
  }) {
    final container = ProviderContainer(
      overrides: [
        agentGraphRepositoryProvider.overrideWithValue(mockRepository),
      ],
    );
    addTearDown(container.dispose);
    return container;
  }

  group('AgentGraphNotifier', () {
    test('initial state has isLoading=false, payload=null, error=null', () {
      final container = createContainer(mockRepository: mockRepository);
      final state = container.read(agentGraphProvider);

      expect(state.isLoading, false);
      expect(state.payload, isNull);
      expect(state.error, isNull);
    });

    test('fetchGraph sets isLoading true during fetch then false after',
        () async {
      final completer = Completer<MultiTraceGraphPayload>();
      mockRepository.completer = completer;

      final container = createContainer(mockRepository: mockRepository);
      final notifier = container.read(agentGraphProvider.notifier);

      final future = notifier.fetchGraph();

      // While the future is pending, isLoading should be true.
      expect(container.read(agentGraphProvider).isLoading, true);

      completer.complete(const MultiTraceGraphPayload());
      await future;

      final state = container.read(agentGraphProvider);
      expect(state.isLoading, false);
    });

    test('fetchGraph on success sets payload and clears error', () async {
      final container = createContainer(mockRepository: mockRepository);
      final notifier = container.read(agentGraphProvider.notifier);

      const payload = MultiTraceGraphPayload(
        nodes: [
          MultiTraceNode(id: 'agent-1', type: 'Agent'),
        ],
        edges: [
          MultiTraceEdge(sourceId: 'agent-1', targetId: 'tool-1'),
        ],
      );
      mockRepository.mockResult = payload;

      await notifier.fetchGraph();

      final state = container.read(agentGraphProvider);
      expect(state.isLoading, false);
      expect(state.payload, isNotNull);
      expect(state.payload!.nodes.length, 1);
      expect(state.payload!.edges.length, 1);
      expect(state.error, isNull);
    });

    test('fetchGraph on error sets error string', () async {
      final container = createContainer(mockRepository: mockRepository);
      final notifier = container.read(agentGraphProvider.notifier);

      mockRepository.mockError = Exception('Network failure');

      await notifier.fetchGraph();

      final state = container.read(agentGraphProvider);
      expect(state.isLoading, false);
      expect(state.error, contains('Network failure'));
    });

    test('fetchGraph clears selectedElement', () async {
      final container = createContainer(mockRepository: mockRepository);
      final notifier = container.read(agentGraphProvider.notifier);

      // First select a node so selectedElement is non-null.
      const node = MultiTraceNode(id: 'agent-1', type: 'Agent');
      notifier.selectNode(node);
      expect(
        container.read(agentGraphProvider).selectedElement,
        isNotNull,
      );

      // fetchGraph should clear it.
      await notifier.fetchGraph();

      expect(container.read(agentGraphProvider).selectedElement, isNull);
    });

    test('selectNode updates selectedElement to SelectedNode', () {
      final container = createContainer(mockRepository: mockRepository);
      final notifier = container.read(agentGraphProvider.notifier);

      const node = MultiTraceNode(id: 'agent-1', type: 'Agent');
      notifier.selectNode(node);

      final state = container.read(agentGraphProvider);
      expect(state.selectedElement, isA<SelectedNode>());
      final selected = state.selectedElement! as SelectedNode;
      expect(selected.node.id, 'agent-1');
    });

    test('selectEdge updates selectedElement to SelectedEdge', () {
      final container = createContainer(mockRepository: mockRepository);
      final notifier = container.read(agentGraphProvider.notifier);

      const edge = MultiTraceEdge(
        sourceId: 'agent-1',
        targetId: 'tool-1',
      );
      notifier.selectEdge(edge);

      final state = container.read(agentGraphProvider);
      expect(state.selectedElement, isA<SelectedEdge>());
      final selected = state.selectedElement! as SelectedEdge;
      expect(selected.edge.sourceId, 'agent-1');
      expect(selected.edge.targetId, 'tool-1');
    });

    test('clearSelection sets selectedElement to null', () {
      final container = createContainer(mockRepository: mockRepository);
      final notifier = container.read(agentGraphProvider.notifier);

      // Select first, then clear.
      const node = MultiTraceNode(id: 'agent-1', type: 'Agent');
      notifier.selectNode(node);
      expect(
        container.read(agentGraphProvider).selectedElement,
        isNotNull,
      );

      notifier.clearSelection();

      expect(container.read(agentGraphProvider).selectedElement, isNull);
    });

    test('updateDataset updates the dataset in state', () {
      final container = createContainer(mockRepository: mockRepository);
      final notifier = container.read(agentGraphProvider.notifier);

      expect(container.read(agentGraphProvider).dataset, kDefaultDataset);

      notifier.updateDataset('my-project.custom_dataset');

      expect(
        container.read(agentGraphProvider).dataset,
        'my-project.custom_dataset',
      );
    });

    test('updateTimeRange updates the timeRangeHours in state', () {
      final container = createContainer(mockRepository: mockRepository);
      final notifier = container.read(agentGraphProvider.notifier);

      expect(container.read(agentGraphProvider).timeRangeHours, 6);

      notifier.updateTimeRange(24);

      expect(container.read(agentGraphProvider).timeRangeHours, 24);
    });
  });
}
