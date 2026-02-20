import 'package:flutter/material.dart';

import '../../../theme/app_theme.dart';
import '../domain/models.dart';
import 'glassmorphism_card.dart';
import 'metric_badge.dart';

/// A rich tooltip overlay anchored near a graph node or edge.
///
/// For nodes it shows token breakdown, latency, cost, error info, and
/// downstream totals. For edges it shows call count, error rate, token
/// flow, and latency.
class NodeTooltipOverlay extends StatelessWidget {
  /// The node to display info for (mutually exclusive with [edge]).
  final MultiTraceNode? node;

  /// The edge to display info for (mutually exclusive with [node]).
  final MultiTraceEdge? edge;

  /// Screen position to anchor the tooltip near.
  final Offset position;

  /// Called when the user taps outside to dismiss the tooltip.
  final VoidCallback onDismiss;

  const NodeTooltipOverlay({
    super.key,
    this.node,
    this.edge,
    required this.position,
    required this.onDismiss,
  });

  @override
  Widget build(BuildContext context) {
    final screenSize = MediaQuery.of(context).size;

    // Position tooltip avoiding screen edges
    var left = position.dx + 12;
    var top = position.dy + 12;
    const maxWidth = 280.0;

    if (left + maxWidth > screenSize.width - 16) {
      left = position.dx - maxWidth - 12;
    }
    if (top + 200 > screenSize.height - 16) {
      top = position.dy - 200;
    }
    left = left.clamp(8.0, screenSize.width - maxWidth - 8);
    top = top.clamp(8.0, screenSize.height - 80);

    return Stack(
      children: [
        // Dismiss scrim
        Positioned.fill(
          child: GestureDetector(
            onTap: onDismiss,
            behavior: HitTestBehavior.opaque,
            child: const ColoredBox(color: Colors.transparent),
          ),
        ),
        // Tooltip card
        Positioned(
          left: left,
          top: top,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: maxWidth),
            child: GlassmorphismCard(
              padding: const EdgeInsets.all(12),
              child: node != null ? _buildNodeContent() : _buildEdgeContent(),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildNodeContent() {
    final n = node!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        // Header
        Row(
          children: [
            Icon(
              _nodeTypeIcon(n.type),
              size: 14,
              color: AppColors.primaryCyan,
            ),
            const SizedBox(width: 6),
            Expanded(
              child: Text(
                n.label ?? n.id,
                style: const TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        Text(
          n.type.toUpperCase(),
          style: const TextStyle(
            fontSize: 9,
            fontWeight: FontWeight.w500,
            color: AppColors.textMuted,
            letterSpacing: 0.8,
          ),
        ),
        const Divider(height: 12),

        // Token breakdown bars
        _buildTokenBars(n.inputTokens, n.outputTokens),
        const SizedBox(height: 8),

        // Metrics row
        Wrap(
          spacing: 4,
          runSpacing: 4,
          children: [
            MetricBadge.latency(n.avgDurationMs),
            if (n.p95DurationMs > 0)
              MetricBadge(
                icon: Icons.trending_up,
                value: 'p95 ${_formatMs(n.p95DurationMs)}',
                color: AppColors.warning,
                tooltip: 'p95 latency: ${n.p95DurationMs.toStringAsFixed(1)}ms',
              ),
            if (n.totalCost != null && n.totalCost! > 0)
              MetricBadge.cost(n.totalCost!),
            if (n.errorCount > 0) MetricBadge.errorRate(n.errorRatePct),
            MetricBadge.subcalls(n.toolCallCount, n.llmCallCount),
          ],
        ),

        // Downstream totals
        if (n.downstreamTotalTokens > 0) ...[
          const SizedBox(height: 8),
          const Divider(height: 1),
          const SizedBox(height: 6),
          const Text(
            'DOWNSTREAM TOTALS',
            style: TextStyle(
              fontSize: 9,
              fontWeight: FontWeight.w600,
              color: AppColors.textMuted,
              letterSpacing: 0.8,
            ),
          ),
          const SizedBox(height: 4),
          Wrap(
            spacing: 4,
            runSpacing: 4,
            children: [
              MetricBadge.tokens(n.downstreamTotalTokens),
              if (n.downstreamTotalCost != null && n.downstreamTotalCost! > 0)
                MetricBadge.cost(n.downstreamTotalCost!),
              MetricBadge.subcalls(
                n.downstreamToolCallCount,
                n.downstreamLlmCallCount,
              ),
            ],
          ),
        ],

        // Execution stats
        const SizedBox(height: 6),
        Text(
          '${n.executionCount} executions across ${n.uniqueSessions} sessions',
          style: const TextStyle(
            fontSize: 10,
            color: AppColors.textMuted,
          ),
        ),
      ],
    );
  }

  Widget _buildEdgeContent() {
    final e = edge!;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        // Header
        Row(
          children: [
            const Icon(
              Icons.arrow_forward,
              size: 14,
              color: AppColors.primaryCyan,
            ),
            const SizedBox(width: 6),
            Expanded(
              child: Text(
                '${e.sourceId} \u2192 ${e.targetId}',
                style: const TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ),
        if (e.isBackEdge) ...[
          const SizedBox(height: 2),
          const Text(
            'BACK EDGE (CYCLE)',
            style: TextStyle(
              fontSize: 9,
              fontWeight: FontWeight.w600,
              color: AppColors.warning,
              letterSpacing: 0.8,
            ),
          ),
        ],
        const Divider(height: 12),

        // Metrics
        Wrap(
          spacing: 4,
          runSpacing: 4,
          children: [
            MetricBadge(
              icon: Icons.repeat,
              value: '${e.callCount} calls',
              color: AppColors.primaryCyan,
              tooltip: '${e.callCount} total calls',
            ),
            if (e.errorCount > 0) MetricBadge.errorRate(e.errorRatePct),
            MetricBadge.tokens(e.edgeTokens),
            MetricBadge.latency(e.avgDurationMs),
            if (e.p95DurationMs > 0)
              MetricBadge(
                icon: Icons.trending_up,
                value: 'p95 ${_formatMs(e.p95DurationMs)}',
                color: AppColors.warning,
              ),
          ],
        ),

        // Token breakdown
        if (e.inputTokens > 0 || e.outputTokens > 0) ...[
          const SizedBox(height: 8),
          _buildTokenBars(e.inputTokens, e.outputTokens),
        ],

        // Error sample
        if (e.sampleError != null) ...[
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: AppColors.error.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(4),
            ),
            child: Text(
              e.sampleError!,
              style: const TextStyle(
                fontSize: 10,
                color: AppColors.error,
              ),
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],

        // Stats footer
        const SizedBox(height: 6),
        Text(
          '${e.uniqueSessions} sessions \u2022 ~${e.avgTokensPerCall} tokens/call',
          style: const TextStyle(
            fontSize: 10,
            color: AppColors.textMuted,
          ),
        ),
      ],
    );
  }

  Widget _buildTokenBars(int input, int output) {
    final total = input + output;
    if (total == 0) return const SizedBox.shrink();

    final inputPct = input / total;
    final outputPct = output / total;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                'Input: ${_formatTokens(input)}',
                style: const TextStyle(
                  fontSize: 10,
                  color: AppColors.primaryCyan,
                ),
              ),
            ),
            Text(
              'Output: ${_formatTokens(output)}',
              style: const TextStyle(
                fontSize: 10,
                color: AppColors.secondaryPurple,
              ),
            ),
          ],
        ),
        const SizedBox(height: 3),
        ClipRRect(
          borderRadius: BorderRadius.circular(2),
          child: SizedBox(
            height: 4,
            child: Row(
              children: [
                Expanded(
                  flex: (inputPct * 100).round().clamp(1, 100),
                  child: Container(
                    color: AppColors.primaryCyan.withValues(alpha: 0.7),
                  ),
                ),
                Expanded(
                  flex: (outputPct * 100).round().clamp(1, 100),
                  child: Container(
                    color: AppColors.secondaryPurple.withValues(alpha: 0.7),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  IconData _nodeTypeIcon(String type) {
    return switch (type.toLowerCase()) {
      'agent' => Icons.smart_toy_outlined,
      'tool' => Icons.build_outlined,
      'llm' => Icons.auto_awesome,
      'user' => Icons.person_outline,
      _ => Icons.circle_outlined,
    };
  }

  static String _formatMs(double ms) {
    if (ms < 1000) return '${ms.toStringAsFixed(0)}ms';
    return '${(ms / 1000).toStringAsFixed(1)}s';
  }

  static String _formatTokens(int count) {
    if (count < 1000) return '$count';
    if (count < 1000000) return '${(count / 1000).toStringAsFixed(1)}K';
    return '${(count / 1000000).toStringAsFixed(1)}M';
  }
}
