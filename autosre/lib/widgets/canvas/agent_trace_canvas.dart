import 'dart:math' as math;

import 'package:flutter/material.dart';
import '../../models/adk_schema.dart';
import '../../theme/app_theme.dart';

/// Agent interaction timeline widget.
///
/// Displays a waterfall-style timeline of agent spans, color-coded by kind
/// (agent invocation, LLM call, tool execution, sub-agent delegation),
/// with token badges and model indicators.
class AgentTraceCanvas extends StatefulWidget {
  final AgentTraceData data;

  const AgentTraceCanvas({super.key, required this.data});

  @override
  State<AgentTraceCanvas> createState() => _AgentTraceCanvasState();
}

class _AgentTraceCanvasState extends State<AgentTraceCanvas> {
  int? _selectedIndex;

  Color _kindColor(String kind) {
    switch (kind) {
      case 'agent_invocation':
        return AppColors.primaryTeal;
      case 'llm_call':
        return AppColors.secondaryPurple;
      case 'tool_execution':
        return AppColors.warning;
      case 'sub_agent_delegation':
        return AppColors.primaryCyan;
      default:
        return Colors.grey;
    }
  }

  IconData _kindIcon(String kind) {
    switch (kind) {
      case 'agent_invocation':
        return Icons.smart_toy;
      case 'llm_call':
        return Icons.auto_awesome;
      case 'tool_execution':
        return Icons.build;
      case 'sub_agent_delegation':
        return Icons.account_tree;
      default:
        return Icons.circle;
    }
  }

  String _kindLabel(String kind) {
    switch (kind) {
      case 'agent_invocation':
        return 'Agent';
      case 'llm_call':
        return 'LLM';
      case 'tool_execution':
        return 'Tool';
      case 'sub_agent_delegation':
        return 'Sub-Agent';
      default:
        return 'Unknown';
    }
  }

  @override
  Widget build(BuildContext context) {
    final data = widget.data;
    if (data.nodes.isEmpty) {
      return const Center(
        child: Text(
          'No agent trace data',
          style: TextStyle(color: Colors.white70),
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _buildHeader(data),
        const SizedBox(height: 8),
        _buildLegend(),
        const SizedBox(height: 8),
        Expanded(child: _buildTimeline(data)),
        if (_selectedIndex != null)
          _buildDetailPanel(data.nodes[_selectedIndex!]),
      ],
    );
  }

  Widget _buildHeader(AgentTraceData data) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.smart_toy,
                color: AppColors.primaryCyan,
                size: 20,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  data.rootAgentName ?? 'Agent Trace',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              _chip(
                '${data.totalDurationMs.toStringAsFixed(0)}ms',
                Colors.white24,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: [
              _chip(
                'Trace: ${data.traceId.substring(0, math.min(12, data.traceId.length))}...',
                Colors.white10,
              ),
              _chip(
                'In: ${_formatTokens(data.totalInputTokens)}',
                AppColors.primaryCyan.withValues(alpha: 0.2),
              ),
              _chip(
                'Out: ${_formatTokens(data.totalOutputTokens)}',
                AppColors.secondaryPurple.withValues(alpha: 0.2),
              ),
              _chip(
                '${data.llmCallCount} LLM',
                AppColors.secondaryPurple.withValues(alpha: 0.2),
              ),
              _chip(
                '${data.toolCallCount} Tools',
                AppColors.warning.withValues(alpha: 0.2),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _chip(String text, Color bgColor) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        text,
        style: const TextStyle(color: Colors.white70, fontSize: 11),
      ),
    );
  }

  Widget _buildLegend() {
    const kinds = [
      'agent_invocation',
      'llm_call',
      'tool_execution',
      'sub_agent_delegation',
    ];
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: kinds.map((kind) {
          return Padding(
            padding: const EdgeInsets.only(right: 16),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 10,
                  height: 10,
                  decoration: BoxDecoration(
                    color: _kindColor(kind),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(width: 4),
                Text(
                  _kindLabel(kind),
                  style: const TextStyle(color: Colors.white54, fontSize: 11),
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _buildTimeline(AgentTraceData data) {
    final totalMs = data.totalDurationMs > 0 ? data.totalDurationMs : 1.0;

    return ListView.builder(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      itemCount: data.nodes.length,
      itemBuilder: (context, index) {
        final node = data.nodes[index];
        final isSelected = _selectedIndex == index;
        final barStart = node.startOffsetMs / totalMs;
        final barWidth = math.max(node.durationMs / totalMs, 0.01);

        return GestureDetector(
          onTap: () =>
              setState(() => _selectedIndex = isSelected ? null : index),
          child: Container(
            margin: const EdgeInsets.only(bottom: 2),
            padding: const EdgeInsets.symmetric(vertical: 4),
            decoration: BoxDecoration(
              color: isSelected
                  ? Colors.white.withValues(alpha: 0.05)
                  : Colors.transparent,
              borderRadius: BorderRadius.circular(4),
            ),
            child: Row(
              children: [
                // Indent + icon
                SizedBox(width: (node.depth * 16.0) + 4),
                Icon(
                  _kindIcon(node.kind),
                  color: _kindColor(node.kind),
                  size: 14,
                ),
                const SizedBox(width: 6),
                // Name
                SizedBox(
                  width: 140,
                  child: Text(
                    node.toolName ?? node.agentName ?? node.name,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      color: node.hasError ? Colors.redAccent : Colors.white70,
                      fontSize: 12,
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                // Timeline bar
                Expanded(
                  child: LayoutBuilder(
                    builder: (context, constraints) {
                      final maxWidth = constraints.maxWidth;
                      return Stack(
                        children: [
                          // Background track
                          Container(
                            height: 18,
                            decoration: BoxDecoration(
                              color: Colors.white.withValues(alpha: 0.03),
                              borderRadius: BorderRadius.circular(3),
                            ),
                          ),
                          // Bar
                          Positioned(
                            left: barStart * maxWidth,
                            child: Container(
                              width: math.max(barWidth * maxWidth, 4),
                              height: 18,
                              decoration: BoxDecoration(
                                color: _kindColor(
                                  node.kind,
                                ).withValues(alpha: 0.7),
                                borderRadius: BorderRadius.circular(3),
                                border: node.hasError
                                    ? Border.all(
                                        color: Colors.redAccent,
                                        width: 1,
                                      )
                                    : null,
                              ),
                              alignment: Alignment.centerLeft,
                              padding: const EdgeInsets.symmetric(
                                horizontal: 4,
                              ),
                              child: _buildBarContent(node),
                            ),
                          ),
                        ],
                      );
                    },
                  ),
                ),
                // Duration
                SizedBox(
                  width: 60,
                  child: Text(
                    '${node.durationMs.toStringAsFixed(0)}ms',
                    textAlign: TextAlign.right,
                    style: const TextStyle(color: Colors.white38, fontSize: 11),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildBarContent(AgentTraceNode node) {
    final parts = <Widget>[];

    if (node.inputTokens != null || node.outputTokens != null) {
      parts.add(
        Text(
          'in:${node.inputTokens ?? 0}/out:${node.outputTokens ?? 0}',
          style: const TextStyle(color: Colors.white, fontSize: 9),
          overflow: TextOverflow.ellipsis,
        ),
      );
    }

    if (node.modelUsed != null) {
      parts.add(
        Text(
          node.modelUsed!.split('/').last,
          style: const TextStyle(color: Colors.white54, fontSize: 9),
          overflow: TextOverflow.ellipsis,
        ),
      );
    }

    if (parts.isEmpty) return const SizedBox.shrink();
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: parts.take(1).toList(),
    );
  }

  Widget _buildDetailPanel(AgentTraceNode node) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(12),
      margin: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Colors.black26,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: _kindColor(node.kind).withValues(alpha: 0.4)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Icon(
                _kindIcon(node.kind),
                color: _kindColor(node.kind),
                size: 16,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  node.name,
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                  ),
                ),
              ),
              IconButton(
                icon: const Icon(Icons.close, size: 16, color: Colors.white54),
                onPressed: () => setState(() => _selectedIndex = null),
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
              ),
            ],
          ),
          const SizedBox(height: 8),
          _detailRow('Kind', _kindLabel(node.kind)),
          _detailRow('Operation', node.operation),
          if (node.agentName != null) _detailRow('Agent', node.agentName!),
          if (node.toolName != null) _detailRow('Tool', node.toolName!),
          if (node.modelUsed != null) _detailRow('Model', node.modelUsed!),
          _detailRow('Duration', '${node.durationMs.toStringAsFixed(1)}ms'),
          if (node.inputTokens != null)
            _detailRow('Input Tokens', '${node.inputTokens}'),
          if (node.outputTokens != null)
            _detailRow('Output Tokens', '${node.outputTokens}'),
          if (node.hasError)
            _detailRow('Status', 'ERROR', valueColor: Colors.redAccent),
        ],
      ),
    );
  }

  Widget _detailRow(String label, String value, {Color? valueColor}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 2),
      child: Row(
        children: [
          SizedBox(
            width: 100,
            child: Text(
              label,
              style: const TextStyle(color: Colors.white38, fontSize: 11),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                color: valueColor ?? Colors.white70,
                fontSize: 11,
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _formatTokens(int tokens) {
    if (tokens >= 1000000) return '${(tokens / 1000000).toStringAsFixed(1)}M';
    if (tokens >= 1000) return '${(tokens / 1000).toStringAsFixed(1)}K';
    return tokens.toString();
  }
}
