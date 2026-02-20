import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../../theme/app_theme.dart';
import '../../../services/explorer_query_service.dart';
import '../domain/models.dart';

/// Right-hand detail panel showing full metadata for a selected node or edge.
class AgentGraphDetailsPanel extends StatelessWidget {
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
  Widget build(BuildContext context) {
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
                SelectedNode(:final node) => _buildNodeDetail(context, node),
                SelectedEdge(:final edge) => _buildEdgeDetail(context, edge),
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

  Widget _buildNodeDetail(BuildContext context, MultiTraceNode node) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _metricCard(
          label: 'Type',
          value: node.type,
          icon: _nodeIcon(node.type),
          color: _nodeColor(node.type),
        ),
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
        ],
        if (payload.nodes.isNotEmpty) ...[
          const SizedBox(height: 8),
          _buildTokenPercentage(node.totalTokens),
        ],
        if ((node.type.toLowerCase() == 'agent' ||
                node.type.toLowerCase() == 'sub_agent') &&
            (node.toolCallCount > 0 || node.llmCallCount > 0)) ...[
          const SizedBox(height: 12),
          const Text('Sub-call Distribution',
              style: TextStyle(
                  color: Colors.white70,
                  fontSize: 11,
                  fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          _metricRow('Tool Calls', node.toolCallCount.toString(), Icons.build),
          _metricRow(
              'LLM Calls', node.llmCallCount.toString(), Icons.auto_awesome),
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
          ],
        ),
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
      ],
    );
  }

  // ---------------------------------------------------------------------------
  // Edge detail
  // ---------------------------------------------------------------------------

  Widget _buildEdgeDetail(BuildContext context, MultiTraceEdge edge) {
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
      ],
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
}
