import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../theme/app_theme.dart';
import '../../../services/explorer_query_service.dart';
import '../domain/models.dart';
import '../application/agent_graph_notifier.dart';

/// Right-hand detail panel showing full metadata for a selected node or edge.
class AgentGraphDetailsPanel extends ConsumerWidget {
  final MultiTraceGraphPayload payload;
  final SelectedGraphElement? selected;
  final VoidCallback? onClose;

  const AgentGraphDetailsPanel({
    super.key,
    required this.payload,
    required this.selected,
    this.onClose,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sel = selected;
    if (sel == null) return const SizedBox.shrink();

    return Container(
      width: 320,
      decoration: const BoxDecoration(
        color: AppColors.backgroundCard,
        border: Border(
          left: BorderSide(color: AppColors.surfaceBorder, width: 1),
        ),
      ),
      child: Column(
        children: [
          _buildHeader(sel),
          Expanded(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: switch (sel) {
                SelectedNode(:final node) => _buildNodeDetail(
                  context,
                  ref,
                  node,
                ),
                SelectedEdge(:final edge) => _buildEdgeDetail(
                  context,
                  ref,
                  edge,
                ),
                SelectedPath(:final nodeIds, :final label) =>
                  _buildPathDetail(nodeIds, label),
              },
            ),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Header
  // ---------------------------------------------------------------------------

  Widget _buildHeader(SelectedGraphElement sel) {
    final (icon, title, color) = switch (sel) {
      SelectedNode(:final node) => (
          _nodeIcon(node.type),
          node.id,
          _nodeColor(node.type),
        ),
      SelectedEdge(:final edge) => (
          Icons.arrow_forward,
          '${edge.sourceId} → ${edge.targetId}',
          AppColors.primaryBlue,
        ),
      SelectedPath(:final nodeIds, :final label) => (
          Icons.timeline,
          label ?? 'Path (${nodeIds.length} nodes)',
          AppColors.secondaryPurple,
        ),
    };

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        border: const Border(
          bottom: BorderSide(color: AppColors.surfaceBorder, width: 1),
        ),
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              title,
              style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w600,
                fontSize: 14,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          if (onClose != null)
            IconButton(
              icon: const Icon(Icons.close, size: 16, color: Colors.white54),
              onPressed: onClose,
              padding: EdgeInsets.zero,
              constraints: const BoxConstraints(),
            ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Node detail
  // ---------------------------------------------------------------------------

  Widget _buildNodeDetail(
    BuildContext context,
    WidgetRef ref,
    MultiTraceNode node,
  ) {
    final extendedDetails = ref.watch(
      fetchExtendedNodeDetailsProvider(node.id),
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _metricCard(
          label: 'Type',
          value: node.type,
          icon: _nodeIcon(node.type),
          color: _nodeColor(node.type),
        ),
        if (node.depth > 0) ...[
          const SizedBox(height: 8),
          _metricRow('Depth', 'Level ${node.depth}', Icons.layers),
        ],
        if (node.description != null && node.description!.isNotEmpty) ...[
          const SizedBox(height: 12),
          const Text('Description',
              style: TextStyle(
                  color: Colors.white70,
                  fontSize: 11,
                  fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.04),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppColors.surfaceBorder),
            ),
            child: SelectableText(
              node.description!,
              style: const TextStyle(color: Colors.white60, fontSize: 12),
            ),
          ),
        ],
        const SizedBox(height: 12),
        _metricCard(
          label: 'Total Tokens',
          value: _formatTokens(node.totalTokens),
          icon: Icons.token,
          color: AppColors.primaryCyan,
        ),
        if (node.totalCost != null && node.totalCost! > 0) ...[
          const SizedBox(height: 8),
          _metricCard(
            label: 'Estimated Cost',
            value: '\$${_formatCost(node.totalCost!)}',
            icon: Icons.attach_money,
            color: const Color(0xFF00E676),
          ),
        ],
        const SizedBox(height: 12),
        const Text('Token Breakdown',
            style: TextStyle(
                color: Colors.white70,
                fontSize: 11,
                fontWeight: FontWeight.w600)),
        const SizedBox(height: 8),
        _metricRow('Input Tokens', _formatTokens(node.inputTokens), Icons.input),
        _metricRow('Output Tokens', _formatTokens(node.outputTokens), Icons.output),
        if (node.totalTokens > 0) ...[
          const SizedBox(height: 8),
          _buildMetricBar('Input / Total', node.inputTokens.toDouble(),
              node.totalTokens.toDouble(), AppColors.primaryCyan),
          const SizedBox(height: 4),
          _buildMetricBar('Output / Total', node.outputTokens.toDouble(),
              node.totalTokens.toDouble(), AppColors.warning),
        ],
        if (node.avgDurationMs > 0) ...[
          const SizedBox(height: 8),
          _metricCard(
            label: 'Avg Latency',
            value: '${node.avgDurationMs.toStringAsFixed(1)} ms',
            icon: Icons.timer,
            color: AppColors.primaryTeal,
          ),
        ],
        if (node.p95DurationMs > 0) ...[
          const SizedBox(height: 8),
          _metricCard(
            label: 'P95 Latency',
            value: '${node.p95DurationMs.toStringAsFixed(1)} ms',
            icon: Icons.speed,
            color: AppColors.warning,
          ),
        ],
        if (node.hasError) ...[
          const SizedBox(height: 8),
          _metricCard(
            label: 'Error Rate',
            value: '${node.errorRatePct.toStringAsFixed(1)}%',
            icon: Icons.error_outline,
            color: AppColors.error,
          ),
          const SizedBox(height: 8),
          _buildMetricBar(
              'Error Rate', node.errorRatePct, 100.0, AppColors.error),
        ],
        if (payload.nodes.isNotEmpty) ...[
          const SizedBox(height: 8),
          _buildTokenPercentage(node.totalTokens),
        ],
        if (node.downstreamTotalTokens > node.totalTokens) ...[
          const Divider(color: AppColors.surfaceBorder, height: 24),
          const Text('Downstream Impact',
              style: TextStyle(
                  color: Colors.white70,
                  fontSize: 11,
                  fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          _metricRow('Downstream Tokens',
              _formatTokens(node.downstreamTotalTokens), Icons.token),
          if (node.downstreamTotalCost != null &&
              node.downstreamTotalCost! > 0)
            _metricRow(
                'Downstream Cost',
                '\$${_formatCost(node.downstreamTotalCost!)}',
                Icons.attach_money,
                valueColor: const Color(0xFF00E676)),
          _metricRow('Downstream Tools',
              '${node.downstreamToolCallCount} calls', Icons.build),
          _metricRow('Downstream LLMs',
              '${node.downstreamLlmCallCount} calls', Icons.auto_awesome),
          const SizedBox(height: 8),
          _buildMetricBar(
              'Node / Downstream Tokens',
              node.totalTokens.toDouble(),
              node.downstreamTotalTokens.toDouble(),
              AppColors.primaryCyan),
        ],
        if ((node.type.toLowerCase() == 'agent' ||
                node.type.toLowerCase() == 'sub_agent') &&
            (node.toolCallCount > 0 || node.llmCallCount > 0)) ...[
          const Divider(color: AppColors.surfaceBorder, height: 24),
          const Text('Subcall Distribution',
              style: TextStyle(
                  color: Colors.white70,
                  fontSize: 11,
                  fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          _metricRow('Tool Calls', node.toolCallCount.toString(), Icons.build),
          _metricRow(
              'LLM Calls', node.llmCallCount.toString(), Icons.auto_awesome),
          const SizedBox(height: 8),
          _buildMetricBar(
              'Tools',
              node.toolCallCount.toDouble(),
              (node.toolCallCount + node.llmCallCount).toDouble(),
              AppColors.warning),
          const SizedBox(height: 4),
          _buildMetricBar(
              'LLMs',
              node.llmCallCount.toDouble(),
              (node.toolCallCount + node.llmCallCount).toDouble(),
              AppColors.secondaryPurple),
        ],
        const SizedBox(height: 8),
        Row(
          children: [
            if (node.isRoot)
              _badge('Root', AppColors.primaryCyan),
            if (node.isRoot && node.isLeaf) const SizedBox(width: 8),
            if (node.isLeaf)
              _badge('Leaf', AppColors.warning),
            if (node.hasError) ...[
              const SizedBox(width: 8),
              _badge('Has Errors', AppColors.error),
            ],
            if (node.isUserEntryPoint) ...[
              const SizedBox(width: 8),
              _badge('User Entry', AppColors.primaryBlue),
            ],
            if (node.isUserNode) ...[
              const SizedBox(width: 8),
              _badge('Session Entry Point', AppColors.secondaryPurple),
            ],
          ],
        ),
        if (node.childNodeIds.isNotEmpty) ...[
          const Divider(color: AppColors.surfaceBorder, height: 24),
          Text('Children (${node.childNodeIds.length} nodes)',
              style: const TextStyle(
                  color: Colors.white70,
                  fontSize: 11,
                  fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          ...node.childNodeIds.take(8).map(
                (childId) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 2),
                  child: Row(
                    children: [
                      const Icon(Icons.subdirectory_arrow_right,
                          size: 14, color: Colors.white24),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(childId,
                            style: const TextStyle(
                                color: Colors.white60, fontSize: 12)),
                      ),
                    ],
                  ),
                ),
              ),
          if (node.childNodeIds.length > 8)
            Padding(
              padding: const EdgeInsets.only(top: 4),
              child: Text(
                'and ${node.childNodeIds.length - 8} more...',
                style: TextStyle(
                    color: Colors.grey[500],
                    fontSize: 11,
                    fontStyle: FontStyle.italic),
              ),
            ),
        ],
        const SizedBox(height: 16),
        SizedBox(
          width: double.infinity,
          child: FilledButton.icon(
            onPressed: () {
              // Navigate back to the dashboard trace explorer
              // Node IDs are typically either tool names like 'BigQueryTool' or agents like 'router'
              // We'll search traces containing this node name
              context.read<ExplorerQueryService>().queryTraceFilter(
                filter: 'text:"${node.id}"',
              );
              Navigator.of(context).pop();
            },
            icon: const Icon(Icons.travel_explore, size: 16),
            label: const Text('Explore Traces'),
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.primaryTeal.withValues(alpha: 0.2),
              foregroundColor: AppColors.primaryTeal,
              side: const BorderSide(color: AppColors.primaryTeal),
              padding: const EdgeInsets.symmetric(vertical: 12),
            ),
          ),
        ),
        const SizedBox(height: 16),
        const Divider(color: AppColors.surfaceBorder, height: 24),
        const Text(
          'Latency Details (Extended)',
          style: TextStyle(
            color: Colors.white70,
            fontSize: 11,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 8),
        extendedDetails.when(
          data: (data) =>
              _buildExtendedLatency(data['latency'] as Map<String, dynamic>?),
          loading: () => const Center(
            child: Padding(
              padding: EdgeInsets.all(8.0),
              child: SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            ),
          ),
          error: (e, st) => Text(
            'Failed to load: $e',
            style: const TextStyle(color: AppColors.error, fontSize: 10),
          ),
        ),
        const SizedBox(height: 16),
        const Text(
          'Recent Errors (Extended)',
          style: TextStyle(
            color: Colors.white70,
            fontSize: 11,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 8),
        extendedDetails.when(
          data: (data) =>
              _buildExtendedErrors(data['top_errors'] as List<dynamic>?),
          loading: () => const SizedBox.shrink(),
          error: (e, st) => const SizedBox.shrink(),
        ),
      ],
    );
  }

  // ---------------------------------------------------------------------------
  // Edge detail
  // ---------------------------------------------------------------------------

  Widget _buildPathDetail(List<String> nodeIds, String? label) {
    // Build a lookup map from payload for node type coloring.
    final nodeMap = {for (final n in payload.nodes) n.id: n};

    // Compute path-level token total.
    var pathTokens = 0;
    for (final id in nodeIds) {
      final n = nodeMap[id];
      if (n != null) pathTokens += n.totalTokens;
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (label != null)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text(label,
                style: const TextStyle(
                    color: Colors.white, fontSize: 14,
                    fontWeight: FontWeight.w600)),
          ),
        Row(
          children: [
            Icon(Icons.timeline, size: 14, color: Colors.grey[400]),
            const SizedBox(width: 6),
            Text(
              '${nodeIds.length} nodes  ·  ${nodeIds.isNotEmpty ? '${nodeIds.first} → ${nodeIds.last}' : ''}',
              style: TextStyle(color: Colors.grey[400], fontSize: 12),
            ),
          ],
        ),
        if (pathTokens > 0) ...[
          const SizedBox(height: 6),
          _metricRow('Path Tokens', _formatTokens(pathTokens), Icons.token),
        ],
        const SizedBox(height: 12),
        ...nodeIds.asMap().entries.map((entry) {
          final idx = entry.key;
          final id = entry.value;
          final node = nodeMap[id];
          final dotColor = node != null
              ? _pathNodeColor(node.type)
              : Colors.grey;
          final isLast = idx == nodeIds.length - 1;

          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 1),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Icon(Icons.circle, size: 8, color: dotColor),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(id,
                          style: const TextStyle(
                              color: Colors.white70, fontSize: 13)),
                    ),
                    if (node != null)
                      Text(node.type,
                          style: TextStyle(
                              color: dotColor.withValues(alpha: 0.7),
                              fontSize: 10)),
                  ],
                ),
                if (!isLast)
                  const Padding(
                    padding: EdgeInsets.only(left: 3, top: 1, bottom: 1),
                    child: Icon(Icons.arrow_downward,
                        size: 12, color: Colors.white24),
                  ),
              ],
            ),
          );
        }),
      ],
    );
  }

  Color _pathNodeColor(String type) {
    switch (type.toLowerCase()) {
      case 'agent':
      case 'sub_agent':
        return AppColors.primaryTeal;
      case 'tool':
        return AppColors.warning;
      case 'llm':
      case 'llm_model':
        return AppColors.secondaryPurple;
      case 'user':
        return AppColors.primaryBlue;
      default:
        return Colors.grey;
    }
  }

  Widget _buildEdgeDetail(
    BuildContext context,
    WidgetRef ref,
    MultiTraceEdge edge,
  ) {
    final extendedDetails = ref.watch(
      fetchExtendedEdgeDetailsProvider(edge.sourceId, edge.targetId),
    );

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _metricRow('Call Count', edge.callCount.toString(), Icons.repeat),
        _metricRow('Unique Sessions', edge.uniqueSessions.toString(),
            Icons.people_outline),
        if (edge.totalCost != null && edge.totalCost! > 0)
          _metricRow('Estimated Cost', '\$${_formatCost(edge.totalCost!)}',
              Icons.attach_money,
              valueColor: const Color(0xFF00E676)),
        const Divider(color: AppColors.surfaceBorder, height: 24),
        const Text('Performance',
            style: TextStyle(
                color: Colors.white70,
                fontSize: 11,
                fontWeight: FontWeight.w600)),
        const SizedBox(height: 8),
        _metricRow(
          'Avg Duration',
          '${edge.avgDurationMs.toStringAsFixed(1)} ms',
          Icons.timer_outlined,
        ),
        _metricRow(
          'P95 Duration',
          '${edge.p95DurationMs.toStringAsFixed(1)} ms',
          Icons.speed,
        ),
        _metricRow(
          'Avg Tokens/Call',
          _formatTokens(edge.avgTokensPerCall),
          Icons.token,
        ),
        _metricRow(
          'Total Edge Tokens',
          _formatTokens(edge.edgeTokens),
          Icons.data_usage,
        ),
        _metricRow(
          'Input Tokens',
          _formatTokens(edge.inputTokens),
          Icons.input,
        ),
        _metricRow(
          'Output Tokens',
          _formatTokens(edge.outputTokens),
          Icons.output,
        ),
        const Divider(color: AppColors.surfaceBorder, height: 24),
        const Text('Errors',
            style: TextStyle(
                color: Colors.white70,
                fontSize: 11,
                fontWeight: FontWeight.w600)),
        const SizedBox(height: 8),
        _metricRow(
          'Error Count',
          edge.errorCount.toString(),
          Icons.error_outline,
          valueColor: edge.errorCount > 0 ? AppColors.error : null,
        ),
        _metricRow(
          'Error Rate',
          '${edge.errorRatePct.toStringAsFixed(2)}%',
          Icons.warning_amber,
          valueColor: edge.errorRatePct > 0 ? AppColors.error : null,
        ),
        if (edge.sampleError != null && edge.sampleError!.isNotEmpty) ...[
          const SizedBox(height: 12),
          const Text('Sample Error',
              style: TextStyle(
                  color: AppColors.error,
                  fontSize: 11,
                  fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: AppColors.error.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppColors.error.withValues(alpha: 0.3)),
            ),
            child: SelectableText(
              edge.sampleError!,
              style: const TextStyle(
                color: AppColors.error,
                fontSize: 11,
                fontFamily: 'monospace',
              ),
            ),
          ),
        ],
        const SizedBox(height: 16),
        SizedBox(
          width: double.infinity,
          child: FilledButton.icon(
            onPressed: () {
              // Navigate back to the dashboard trace explorer
              context.read<ExplorerQueryService>().queryTraceFilter(
                filter: 'text:"${edge.sourceId}" text:"${edge.targetId}"',
              );
              Navigator.of(context).pop();
            },
            icon: const Icon(Icons.travel_explore, size: 16),
            label: const Text('Explore Traces'),
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.primaryTeal.withValues(alpha: 0.2),
              foregroundColor: AppColors.primaryTeal,
              side: const BorderSide(color: AppColors.primaryTeal),
              padding: const EdgeInsets.symmetric(vertical: 12),
            ),
          ),
        ),
        const SizedBox(height: 16),
        const Divider(color: AppColors.surfaceBorder, height: 24),
        const Text(
          'Latency Details (Extended)',
          style: TextStyle(
            color: Colors.white70,
            fontSize: 11,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 8),
        extendedDetails.when(
          data: (data) =>
              _buildExtendedLatency(data['latency'] as Map<String, dynamic>?),
          loading: () => const Center(
            child: Padding(
              padding: EdgeInsets.all(8.0),
              child: SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            ),
          ),
          error: (e, st) => Text(
            'Failed to load: $e',
            style: const TextStyle(color: AppColors.error, fontSize: 10),
          ),
        ),
        const SizedBox(height: 16),
        const Text(
          'Recent Errors (Extended)',
          style: TextStyle(
            color: Colors.white70,
            fontSize: 11,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 8),
        extendedDetails.when(
          data: (data) =>
              _buildExtendedErrors(data['top_errors'] as List<dynamic>?),
          loading: () => const SizedBox.shrink(),
          error: (e, st) => const SizedBox.shrink(),
        ),
      ],
    );
  }

  // ---------------------------------------------------------------------------
  // Extended Details Formatting
  // ---------------------------------------------------------------------------

  Widget _buildExtendedLatency(Map<String, dynamic>? latencyData) {
    if (latencyData == null || latencyData.isEmpty) {
      return const Text(
        'No extended latency data available.',
        style: TextStyle(color: Colors.white38, fontSize: 12),
      );
    }

    final p50 = (latencyData['p50'] as num?)?.toDouble() ?? 0.0;
    final p90 = (latencyData['p90'] as num?)?.toDouble() ?? 0.0;
    final p99 = (latencyData['p99'] as num?)?.toDouble() ?? 0.0;
    final maxVal = (latencyData['max_val'] as num?)?.toDouble() ?? 0.0;

    return Column(
      children: [
        _metricRow('P50', '${p50.toStringAsFixed(1)} ms', Icons.speed),
        _metricRow('P90', '${p90.toStringAsFixed(1)} ms', Icons.speed),
        _metricRow('P99', '${p99.toStringAsFixed(1)} ms', Icons.speed),
        _metricRow('Max', '${maxVal.toStringAsFixed(1)} ms', Icons.timer),
      ],
    );
  }

  Widget _buildExtendedErrors(List<dynamic>? errors) {
    if (errors == null || errors.isEmpty) {
      return const Text(
        'No recent errors found.',
        style: TextStyle(color: Colors.white38, fontSize: 12),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: errors
          .map(
            (err) => Padding(
              padding: const EdgeInsets.only(bottom: 8.0),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AppColors.error.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: AppColors.error.withValues(alpha: 0.3),
                  ),
                ),
                child: Text(
                  err.toString(),
                  style: const TextStyle(
                    color: AppColors.error,
                    fontSize: 11,
                    fontFamily: 'monospace',
                  ),
                ),
              ),
            ),
          )
          .toList(),
    );
  }

  // ---------------------------------------------------------------------------
  // Reusable widgets
  // ---------------------------------------------------------------------------

  Widget _metricCard({
    required String label,
    required String value,
    required IconData icon,
    required Color color,
  }) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: color.withValues(alpha: 0.2)),
      ),
      child: Row(
        children: [
          Icon(icon, color: color, size: 18),
          const SizedBox(width: 10),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label,
                  style:
                      const TextStyle(color: Colors.white38, fontSize: 10)),
              Text(value,
                  style: TextStyle(
                      color: color,
                      fontSize: 16,
                      fontWeight: FontWeight.w600)),
            ],
          ),
        ],
      ),
    );
  }

  Widget _metricRow(
    String label,
    String value,
    IconData icon, {
    Color? valueColor,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(icon, color: Colors.white24, size: 14),
          const SizedBox(width: 8),
          Expanded(
            child: Text(label,
                style: const TextStyle(color: Colors.white54, fontSize: 12)),
          ),
          Text(
            value,
            style: TextStyle(
              color: valueColor ?? Colors.white,
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  Widget _badge(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        label,
        style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.w600),
      ),
    );
  }

  Widget _buildTokenPercentage(int nodeTokens) {
    if (nodeTokens == 0) return const SizedBox.shrink();

    final totalGraphTokens = payload.nodes.fold(
      0,
      (sum, n) => sum + n.totalTokens,
    );
    if (totalGraphTokens == 0) return const SizedBox.shrink();

    final pct = (nodeTokens / totalGraphTokens * 100);

    return Row(
      children: [
        Expanded(
          child: LinearProgressIndicator(
            value: pct / 100,
            backgroundColor: Colors.white10,
            color: AppColors.primaryCyan,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 8),
        Text(
          '${pct.toStringAsFixed(1)}% of total',
          style: const TextStyle(color: Colors.white54, fontSize: 10),
        ),
      ],
    );
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  Color _nodeColor(String type) {
    switch (type.toLowerCase()) {
      case 'agent':
        return AppColors.primaryTeal;
      case 'tool':
        return AppColors.warning;
      case 'llm':
      case 'llm_model':
        return AppColors.secondaryPurple;
      case 'sub_agent':
        return AppColors.primaryCyan;
      default:
        return Colors.grey;
    }
  }

  IconData _nodeIcon(String type) {
    switch (type.toLowerCase()) {
      case 'agent':
      case 'sub_agent':
        return Icons.psychology;
      case 'tool':
        return Icons.build;
      case 'llm':
      case 'llm_model':
        return Icons.auto_awesome;
      default:
        return Icons.circle;
    }
  }

  String _formatTokens(int tokens) {
    if (tokens >= 1000000) return '${(tokens / 1000000).toStringAsFixed(1)}M';
    if (tokens >= 1000) return '${(tokens / 1000).toStringAsFixed(1)}K';
    return '$tokens';
  }

  String _formatCost(double cost) {
    if (cost >= 1.0) return cost.toStringAsFixed(2);
    if (cost >= 0.01) return cost.toStringAsFixed(3);
    return cost.toStringAsFixed(4);
  }

  Widget _buildMetricBar(
    String label,
    double value,
    double maxValue,
    Color color,
  ) {
    final ratio = maxValue > 0 ? (value / maxValue).clamp(0.0, 1.0) : 0.0;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label,
                style: TextStyle(color: Colors.grey[400], fontSize: 11)),
            Text(value.toStringAsFixed(1),
                style: const TextStyle(color: Colors.white70, fontSize: 11)),
          ],
        ),
        const SizedBox(height: 4),
        ClipRRect(
          borderRadius: BorderRadius.circular(2),
          child: LinearProgressIndicator(
            value: ratio,
            backgroundColor: Colors.white.withValues(alpha: 0.05),
            valueColor: AlwaysStoppedAnimation(color),
            minHeight: 4,
          ),
        ),
      ],
    );
  }
}
