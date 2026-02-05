import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../models/adk_schema.dart';
import '../../theme/app_theme.dart';

/// Widget that visualizes the council investigation activity graph.
///
/// Shows:
/// - Agent hierarchy (root -> orchestrator -> panels -> critic -> synthesizer)
/// - Tool calls made by each agent
/// - Sequence timeline of all events
class CouncilActivityGraphWidget extends StatefulWidget {
  final CouncilActivityGraph graph;
  final VoidCallback? onToolCallTap;

  const CouncilActivityGraphWidget({
    super.key,
    required this.graph,
    this.onToolCallTap,
  });

  @override
  State<CouncilActivityGraphWidget> createState() =>
      _CouncilActivityGraphWidgetState();
}

class _CouncilActivityGraphWidgetState
    extends State<CouncilActivityGraphWidget> {
  String? _selectedAgentId;
  bool _showTimeline = false;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.backgroundCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.surfaceBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeader(),
          _buildModeToggle(),
          Expanded(
            child: _showTimeline ? _buildTimelineView() : _buildGraphView(),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(
            color: AppColors.surfaceBorder.withValues(alpha: 0.5),
          ),
        ),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  AppColors.secondaryPurple.withValues(alpha: 0.2),
                  AppColors.primaryTeal.withValues(alpha: 0.15),
                ],
              ),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(
              Icons.account_tree_rounded,
              size: 16,
              color: AppColors.secondaryPurple,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Investigation Activity',
                  style: GoogleFonts.inter(
                    fontSize: 13,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textPrimary,
                  ),
                ),
                Text(
                  '${widget.graph.agents.length} agents • ${widget.graph.totalToolCalls} tool calls • ${widget.graph.totalLLMCalls} LLM calls',
                  style: GoogleFonts.inter(
                    fontSize: 10,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ),
          ),
          _buildModeBadge(widget.graph.mode),
        ],
      ),
    );
  }

  Widget _buildModeToggle() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Row(
        children: [
          _buildToggleButton(
            label: 'Graph',
            icon: Icons.account_tree_rounded,
            isSelected: !_showTimeline,
            onTap: () => setState(() => _showTimeline = false),
          ),
          const SizedBox(width: 8),
          _buildToggleButton(
            label: 'Timeline',
            icon: Icons.timeline_rounded,
            isSelected: _showTimeline,
            onTap: () => setState(() => _showTimeline = true),
          ),
        ],
      ),
    );
  }

  Widget _buildToggleButton({
    required String label,
    required IconData icon,
    required bool isSelected,
    required VoidCallback onTap,
  }) {
    final color = isSelected ? AppColors.primaryTeal : AppColors.textMuted;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected
              ? AppColors.primaryTeal.withValues(alpha: 0.15)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: isSelected
                ? AppColors.primaryTeal.withValues(alpha: 0.3)
                : AppColors.surfaceBorder,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 12, color: color),
            const SizedBox(width: 4),
            Text(
              label,
              style: GoogleFonts.inter(
                fontSize: 10,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                color: color,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildGraphView() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Root agents
          ...widget.graph.rootAgents.map((agent) => _buildAgentNode(agent, 0)),
        ],
      ),
    );
  }

  Widget _buildAgentNode(CouncilAgentActivity agent, int depth) {
    final isSelected = _selectedAgentId == agent.agentId;
    final children = widget.graph.getChildren(agent.agentId);
    final statusColor = _getStatusColor(agent.status);
    final typeColor = _getAgentTypeColor(agent.agentType);

    return Padding(
      padding: EdgeInsets.only(left: depth * 20.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Agent card
          InkWell(
            onTap: () => setState(() {
              _selectedAgentId = isSelected ? null : agent.agentId;
            }),
            borderRadius: BorderRadius.circular(8),
            child: Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: isSelected
                    ? typeColor.withValues(alpha: 0.15)
                    : AppColors.backgroundDark.withValues(alpha: 0.5),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: isSelected
                      ? typeColor.withValues(alpha: 0.5)
                      : AppColors.surfaceBorder,
                  width: isSelected ? 1.5 : 1,
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Agent header
                  Row(
                    children: [
                      // Connector line
                      if (depth > 0)
                        Container(
                          width: 16,
                          height: 2,
                          color: AppColors.surfaceBorder,
                          margin: const EdgeInsets.only(right: 8),
                        ),
                      // Agent icon
                      Container(
                        padding: const EdgeInsets.all(5),
                        decoration: BoxDecoration(
                          color: typeColor.withValues(alpha: 0.2),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Icon(
                          _getAgentIcon(agent.agentType),
                          size: 12,
                          color: typeColor,
                        ),
                      ),
                      const SizedBox(width: 8),
                      // Agent name and type
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              agent.agentName,
                              style: GoogleFonts.inter(
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                                color: AppColors.textPrimary,
                              ),
                            ),
                            Text(
                              agent.agentType.displayName,
                              style: GoogleFonts.inter(
                                fontSize: 9,
                                color: typeColor,
                              ),
                            ),
                          ],
                        ),
                      ),
                      // Status indicator
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 6,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: statusColor.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Container(
                              width: 5,
                              height: 5,
                              decoration: BoxDecoration(
                                color: statusColor,
                                shape: BoxShape.circle,
                              ),
                            ),
                            const SizedBox(width: 4),
                            Text(
                              agent.status.toUpperCase(),
                              style: TextStyle(
                                fontSize: 8,
                                fontWeight: FontWeight.w600,
                                color: statusColor,
                              ),
                            ),
                          ],
                        ),
                      ),
                      // Expand indicator
                      if (agent.toolCalls.isNotEmpty || agent.llmCalls.isNotEmpty)
                        Icon(
                          isSelected
                              ? Icons.keyboard_arrow_up_rounded
                              : Icons.keyboard_arrow_down_rounded,
                          size: 16,
                          color: AppColors.textMuted,
                        ),
                    ],
                  ),
                  // Stats row
                  if (agent.toolCalls.isNotEmpty || agent.llmCalls.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Row(
                        children: [
                          _buildStatBadge(
                            Icons.build_rounded,
                            '${agent.totalToolCalls} tools',
                            AppColors.primaryCyan,
                          ),
                          const SizedBox(width: 6),
                          _buildStatBadge(
                            Icons.psychology_rounded,
                            '${agent.totalLLMCalls} LLM',
                            AppColors.secondaryPurple,
                          ),
                          if (agent.errorCount > 0) ...[
                            const SizedBox(width: 6),
                            _buildStatBadge(
                              Icons.error_outline_rounded,
                              '${agent.errorCount} errors',
                              AppColors.error,
                            ),
                          ],
                        ],
                      ),
                    ),
                  // Expanded tool calls
                  if (isSelected && agent.toolCalls.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    const Divider(height: 1),
                    const SizedBox(height: 8),
                    Text(
                      'Tool Calls',
                      style: GoogleFonts.inter(
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 6),
                    ...agent.toolCalls.map((call) => _buildToolCallItem(call)),
                  ],
                  // Output summary
                  if (isSelected && agent.outputSummary.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    Text(
                      'Output',
                      style: GoogleFonts.inter(
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      agent.outputSummary,
                      style: GoogleFonts.inter(
                        fontSize: 10,
                        color: AppColors.textSecondary,
                        height: 1.4,
                      ),
                      maxLines: 3,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ],
              ),
            ),
          ),
          // Children agents
          ...children.map((child) => _buildAgentNode(child, depth + 1)),
        ],
      ),
    );
  }

  Widget _buildToolCallItem(ToolCallRecord call) {
    final statusColor = call.isError
        ? AppColors.error
        : call.isPending
            ? AppColors.warning
            : AppColors.success;

    return Container(
      margin: const EdgeInsets.only(bottom: 4),
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: AppColors.backgroundDark.withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(
          color: call.hasDashboardData
              ? AppColors.primaryCyan.withValues(alpha: 0.3)
              : AppColors.surfaceBorder.withValues(alpha: 0.5),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.build_circle_rounded,
                size: 10,
                color: statusColor,
              ),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  call.toolName,
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 10,
                    fontWeight: FontWeight.w500,
                    color: AppColors.textPrimary,
                  ),
                ),
              ),
              if (call.hasDashboardData)
                Tooltip(
                  message: 'Data visible in ${call.dashboardCategory} tab',
                  child: const Icon(
                    Icons.dashboard_rounded,
                    size: 10,
                    color: AppColors.primaryCyan,
                  ),
                ),
              if (call.durationMs > 0) ...[
                const SizedBox(width: 4),
                Text(
                  '${call.durationMs}ms',
                  style: GoogleFonts.inter(
                    fontSize: 9,
                    color: AppColors.textMuted,
                  ),
                ),
              ],
            ],
          ),
          if (call.resultSummary.isNotEmpty) ...[
            const SizedBox(height: 4),
            Text(
              call.resultSummary,
              style: GoogleFonts.inter(
                fontSize: 9,
                color: AppColors.textMuted,
                height: 1.3,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildTimelineView() {
    final allCalls = widget.graph.allToolCallsSorted;
    if (allCalls.isEmpty) {
      return Center(
        child: Text(
          'No tool calls recorded',
          style: GoogleFonts.inter(
            fontSize: 12,
            color: AppColors.textMuted,
          ),
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: allCalls.length,
      itemBuilder: (context, index) {
        final call = allCalls[index];
        final agent = _findAgentForToolCall(call);
        return _buildTimelineItem(call, agent, index == 0, index == allCalls.length - 1);
      },
    );
  }

  CouncilAgentActivity? _findAgentForToolCall(ToolCallRecord call) {
    for (final agent in widget.graph.agents) {
      if (agent.toolCalls.any((c) => c.callId == call.callId)) {
        return agent;
      }
    }
    return null;
  }

  Widget _buildTimelineItem(
    ToolCallRecord call,
    CouncilAgentActivity? agent,
    bool isFirst,
    bool isLast,
  ) {
    final statusColor = call.isError
        ? AppColors.error
        : call.isPending
            ? AppColors.warning
            : AppColors.success;

    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Timeline line
          SizedBox(
            width: 24,
            child: Column(
              children: [
                if (!isFirst)
                  Expanded(
                    child: Container(
                      width: 2,
                      color: AppColors.surfaceBorder,
                    ),
                  ),
                Container(
                  width: 10,
                  height: 10,
                  decoration: BoxDecoration(
                    color: statusColor,
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: AppColors.backgroundCard,
                      width: 2,
                    ),
                  ),
                ),
                if (!isLast)
                  Expanded(
                    child: Container(
                      width: 2,
                      color: AppColors.surfaceBorder,
                    ),
                  ),
              ],
            ),
          ),
          // Content
          Expanded(
            child: Container(
              margin: const EdgeInsets.only(left: 8, bottom: 8),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: AppColors.backgroundDark.withValues(alpha: 0.5),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppColors.surfaceBorder),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          call.toolName,
                          style: GoogleFonts.jetBrainsMono(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textPrimary,
                          ),
                        ),
                      ),
                      if (call.timestamp.isNotEmpty)
                        Text(
                          _formatTimestamp(call.timestamp),
                          style: GoogleFonts.inter(
                            fontSize: 9,
                            color: AppColors.textMuted,
                          ),
                        ),
                    ],
                  ),
                  if (agent != null) ...[
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Icon(
                          _getAgentIcon(agent.agentType),
                          size: 10,
                          color: _getAgentTypeColor(agent.agentType),
                        ),
                        const SizedBox(width: 4),
                        Text(
                          agent.agentName,
                          style: GoogleFonts.inter(
                            fontSize: 9,
                            color: _getAgentTypeColor(agent.agentType),
                          ),
                        ),
                      ],
                    ),
                  ],
                  if (call.resultSummary.isNotEmpty) ...[
                    const SizedBox(height: 6),
                    Text(
                      call.resultSummary,
                      style: GoogleFonts.inter(
                        fontSize: 10,
                        color: AppColors.textSecondary,
                        height: 1.3,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                  if (call.hasDashboardData) ...[
                    const SizedBox(height: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 6,
                        vertical: 3,
                      ),
                      decoration: BoxDecoration(
                        color: AppColors.primaryCyan.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(
                            Icons.dashboard_rounded,
                            size: 10,
                            color: AppColors.primaryCyan,
                          ),
                          const SizedBox(width: 4),
                          Text(
                            'View in ${call.dashboardCategory}',
                            style: GoogleFonts.inter(
                              fontSize: 9,
                              fontWeight: FontWeight.w500,
                              color: AppColors.primaryCyan,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatBadge(IconData icon, String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 10, color: color),
          const SizedBox(width: 3),
          Text(
            text,
            style: TextStyle(
              fontSize: 9,
              fontWeight: FontWeight.w500,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildModeBadge(String mode) {
    Color color;
    IconData icon;
    switch (mode.toLowerCase()) {
      case 'fast':
        color = AppColors.success;
        icon = Icons.flash_on_rounded;
        break;
      case 'debate':
        color = AppColors.secondaryPurple;
        icon = Icons.forum_rounded;
        break;
      default:
        color = AppColors.primaryCyan;
        icon = Icons.auto_awesome_rounded;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 10, color: color),
          const SizedBox(width: 4),
          Text(
            mode.toUpperCase(),
            style: GoogleFonts.inter(
              fontSize: 9,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  IconData _getAgentIcon(CouncilAgentType type) {
    switch (type) {
      case CouncilAgentType.root:
        return Icons.account_tree_rounded;
      case CouncilAgentType.orchestrator:
        return Icons.hub_rounded;
      case CouncilAgentType.panel:
        return Icons.psychology_rounded;
      case CouncilAgentType.critic:
        return Icons.forum_rounded;
      case CouncilAgentType.synthesizer:
        return Icons.summarize_rounded;
      case CouncilAgentType.subAgent:
        return Icons.smart_toy_rounded;
    }
  }

  Color _getAgentTypeColor(CouncilAgentType type) {
    switch (type) {
      case CouncilAgentType.root:
        return AppColors.primaryTeal;
      case CouncilAgentType.orchestrator:
        return AppColors.primaryBlue;
      case CouncilAgentType.panel:
        return AppColors.primaryCyan;
      case CouncilAgentType.critic:
        return AppColors.secondaryPurple;
      case CouncilAgentType.synthesizer:
        return AppColors.warning;
      case CouncilAgentType.subAgent:
        return AppColors.textSecondary;
    }
  }

  Color _getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'completed':
        return AppColors.success;
      case 'running':
        return AppColors.primaryCyan;
      case 'error':
        return AppColors.error;
      default:
        return AppColors.textMuted;
    }
  }

  String _formatTimestamp(String timestamp) {
    try {
      final dt = DateTime.parse(timestamp);
      return '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}:${dt.second.toString().padLeft(2, '0')}';
    } catch (_) {
      return timestamp;
    }
  }
}
