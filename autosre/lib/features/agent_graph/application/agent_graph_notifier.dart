import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';

import '../data/agent_graph_repository.dart';
import '../domain/models.dart';

part 'agent_graph_notifier.freezed.dart';
part 'agent_graph_notifier.g.dart';

@freezed
abstract class AgentGraphState with _$AgentGraphState {
  const factory AgentGraphState({
    @Default(null) MultiTraceGraphPayload? payload,
    @Default(false) bool isLoading,
    String? error,
    @Default(null) SelectedGraphElement? selectedElement,
    @Default(kDefaultDataset) String dataset,
    @Default(6) int timeRangeHours,
    @Default(null) int? sampleLimit,
  }) = _AgentGraphState;
}

@riverpod
class AgentGraphNotifier extends _$AgentGraphNotifier {
  late final AgentGraphRepository _repository;

  @override
  AgentGraphState build() {
    _repository = ref.watch(agentGraphRepositoryProvider);
    return const AgentGraphState();
  }

  /// Execute the graph query and update the state.
  Future<void> fetchGraph({
    String? dataset,
    int? timeRangeHours,
    int? sampleLimit,
    String? projectId,
  }) async {
    if (state.isLoading) return;
    final ds = dataset ?? state.dataset;
    final hours = timeRangeHours ?? state.timeRangeHours;
    final limit = sampleLimit ?? state.sampleLimit;

    state = state.copyWith(
      isLoading: true,
      error: null,
      dataset: ds,
      timeRangeHours: hours,
      sampleLimit: limit,
      selectedElement: null,
    );

    try {
      final payload = await _repository.fetchGraph(
        dataset: ds,
        timeRangeHours: hours,
        sampleLimit: limit,
        projectId: projectId,
      );
      state = state.copyWith(payload: payload, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  void selectNode(MultiTraceNode node) {
    state = state.copyWith(
      selectedElement: SelectedGraphElement.node(node),
    );
  }

  void selectEdge(MultiTraceEdge edge) {
    state = state.copyWith(
      selectedElement: SelectedGraphElement.edge(edge),
    );
  }

  void clearSelection() {
    state = state.copyWith(selectedElement: null);
  }

  void updateDataset(String dataset) {
    state = state.copyWith(dataset: dataset);
  }

  void updateTimeRange(int hours) {
    state = state.copyWith(timeRangeHours: hours);
  }

  void updateSampleLimit(int? limit) {
    state = state.copyWith(sampleLimit: limit);
  }
}
