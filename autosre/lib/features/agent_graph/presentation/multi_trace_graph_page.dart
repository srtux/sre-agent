import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../models/time_range.dart';
import '../../../theme/app_theme.dart';
import '../../../widgets/common/unified_time_picker.dart';
import '../application/agent_graph_notifier.dart';
import '../data/agent_graph_repository.dart';
import 'agent_graph_details_panel.dart';
import 'interactive_graph_canvas.dart';

/// Full-page view for the Multi-Trace Agent Graph Dashboard.
///
/// Layout:
/// ┌──────────────────────────────────────────────────────┐
/// │  [TimePicker]  [Dataset Input]  [Refresh]            │
/// ├──────────────────────────────────┬───────────────────┤
/// │                                  │                   │
/// │   GraphView Canvas               │  Detail Panel     │
/// │                                  │                   │
/// └──────────────────────────────────┴───────────────────┘
class MultiTraceGraphPage extends ConsumerStatefulWidget {
  const MultiTraceGraphPage({super.key});

  @override
  ConsumerState<MultiTraceGraphPage> createState() =>
      _MultiTraceGraphPageState();
}

class _MultiTraceGraphPageState extends ConsumerState<MultiTraceGraphPage> {
  late final TextEditingController _datasetController;
  late TimeRange _timeRange;


  @override
  void initState() {
    super.initState();
    _datasetController = TextEditingController(text: kDefaultDataset);
    _timeRange = TimeRange.fromPreset(TimeRangePreset.sixHours);
  }

  @override
  void dispose() {
    _datasetController.dispose();
    super.dispose();
  }

  int get _timeRangeHours {
    final hours = _timeRange.duration.inHours;
    return hours > 0 ? hours : 1;
  }

  void _runQuery() {
    ref.read(agentGraphProvider.notifier).fetchGraph(
          dataset: _datasetController.text.trim(),
          timeRangeHours: _timeRangeHours,
        );
  }

  @override
  Widget build(BuildContext context) {
    final graphState = ref.watch(agentGraphProvider);

    return Scaffold(
      backgroundColor: AppColors.backgroundDark,
      body: Column(
        children: [
          _buildControlBar(),
          Expanded(
            child: Row(
              children: [
                // Main canvas area.
                Expanded(child: _buildCanvasArea(graphState)),
                // Detail panel (shown when an element is selected).
                if (graphState.selectedElement != null &&
                    graphState.payload != null)
                  AgentGraphDetailsPanel(
                    payload: graphState.payload!,
                    selected: graphState.selectedElement,
                    onClose: () => ref
                        .read(agentGraphProvider.notifier)
                        .clearSelection(),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Control bar
  // ---------------------------------------------------------------------------

  Widget _buildControlBar() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: const BoxDecoration(
        color: AppColors.backgroundCard,
        border: Border(
          bottom: BorderSide(color: AppColors.surfaceBorder, width: 1),
        ),
      ),
      child: Row(
        children: [
          IconButton(
            icon: const Icon(Icons.arrow_back, color: Colors.white70),
            onPressed: () => Navigator.of(context).pop(),
            tooltip: 'Back to Dashboard',
            visualDensity: VisualDensity.compact,
          ),
          const SizedBox(width: 8),
          const Icon(Icons.account_tree, color: AppColors.primaryCyan, size: 20),
          const SizedBox(width: 10),
          const Text(
            'Agent Graph',
            style: TextStyle(
              color: Colors.white,
              fontSize: 16,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(width: 24),
          // Time picker.
          SizedBox(
            width: 240,
            child: UnifiedTimePicker(
              currentRange: _timeRange,
              onChanged: (range) {
                setState(() => _timeRange = range);
              },
              showRefreshButton: false,
              showAutoRefresh: false,
            ),
          ),
          const SizedBox(width: 16),

          // Dataset input.
          SizedBox(
            width: 280,
            child: TextField(
              controller: _datasetController,
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: InputDecoration(
                isDense: true,
                contentPadding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                hintText: 'BigQuery dataset (e.g. project.dataset)',
                hintStyle: const TextStyle(color: Colors.white24, fontSize: 12),
                filled: true,
                fillColor: Colors.white.withValues(alpha: 0.05),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: AppColors.surfaceBorder),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide: const BorderSide(color: AppColors.surfaceBorder),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(8),
                  borderSide:
                      const BorderSide(color: AppColors.primaryCyan, width: 1),
                ),
                prefixIcon: const Icon(Icons.storage,
                    color: Colors.white24, size: 16),
              ),
              onSubmitted: (_) => _runQuery(),
            ),
          ),
          const SizedBox(width: 12),

          // Refresh / Run button.
          _RunButton(
            isLoading: ref.watch(agentGraphProvider).isLoading,
            onPressed: _runQuery,
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Canvas area
  // ---------------------------------------------------------------------------

  Widget _buildCanvasArea(AgentGraphState graphState) {
    if (graphState.isLoading) {
      return const Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            CircularProgressIndicator(color: AppColors.primaryCyan),
            SizedBox(height: 16),
            Text(
              'Querying BigQuery...',
              style: TextStyle(color: Colors.white54, fontSize: 13),
            ),
          ],
        ),
      );
    }

    if (graphState.error != null) {
      return Center(
        child: Container(
          margin: const EdgeInsets.all(32),
          padding: const EdgeInsets.all(20),
          decoration: BoxDecoration(
            color: AppColors.error.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(12),
            border:
                Border.all(color: AppColors.error.withValues(alpha: 0.3)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, color: AppColors.error, size: 36),
              const SizedBox(height: 12),
              const Text('Query Failed',
                  style: TextStyle(
                      color: AppColors.error,
                      fontSize: 15,
                      fontWeight: FontWeight.w600)),
              const SizedBox(height: 8),
              Text(
                graphState.error!,
                style: const TextStyle(
                    color: Colors.white54,
                    fontSize: 12,
                    fontFamily: 'monospace'),
                textAlign: TextAlign.center,
                maxLines: 6,
                overflow: TextOverflow.ellipsis,
              ),
              const SizedBox(height: 16),
              TextButton.icon(
                onPressed: _runQuery,
                icon: const Icon(Icons.refresh, size: 16),
                label: const Text('Retry'),
                style: TextButton.styleFrom(foregroundColor: AppColors.error),
              ),
            ],
          ),
        ),
      );
    }

    final payload = graphState.payload;
    if (payload == null) {
      return _buildEmptyState();
    }

    return InteractiveGraphCanvas(
      payload: payload,
      onNodeSelected: (node) =>
          ref.read(agentGraphProvider.notifier).selectNode(node),
      onEdgeSelected: (edge) =>
          ref.read(agentGraphProvider.notifier).selectEdge(edge),
      onSelectionCleared: () =>
          ref.read(agentGraphProvider.notifier).clearSelection(),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.account_tree_outlined,
              color: AppColors.primaryCyan.withValues(alpha: 0.3), size: 64),
          const SizedBox(height: 16),
          const Text(
            'Multi-Trace Agent Graph',
            style: TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 8),
          const Text(
            'Visualize agent execution flow across multiple traces.\n'
            'Set a time range and click Run to start.',
            textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white38, fontSize: 13),
          ),
          const SizedBox(height: 24),
          FilledButton.icon(
            onPressed: _runQuery,
            icon: const Icon(Icons.play_arrow, size: 18),
            label: const Text('Run Query'),
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.primaryCyan,
              foregroundColor: Colors.white,
              padding:
                  const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Run button with loading indicator
// ---------------------------------------------------------------------------

class _RunButton extends StatelessWidget {
  final bool isLoading;
  final VoidCallback onPressed;

  const _RunButton({required this.isLoading, required this.onPressed});

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      height: 36,
      child: FilledButton.icon(
        onPressed: isLoading ? null : onPressed,
        icon: isLoading
            ? const SizedBox(
                width: 14,
                height: 14,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  color: Colors.white54,
                ),
              )
            : const Icon(Icons.play_arrow, size: 16),
        label: Text(isLoading ? 'Running...' : 'Run'),
        style: FilledButton.styleFrom(
          backgroundColor: AppColors.primaryCyan,
          foregroundColor: Colors.white,
          disabledBackgroundColor: AppColors.primaryCyan.withValues(alpha: 0.3),
          padding: const EdgeInsets.symmetric(horizontal: 16),
          textStyle: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
        ),
      ),
    );
  }
}
