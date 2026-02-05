import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../models/adk_schema.dart';
import '../../services/dashboard_state.dart';
import '../../theme/app_theme.dart';
import 'council_activity_graph.dart';

/// Dashboard panel showing council investigation results with expert panel visualization.
///
/// Displays the council's investigation including:
/// - Investigation mode and overall status
/// - Individual expert panel findings (Trace, Metrics, Logs, Alerts)
/// - Critic's debate analysis (for debate mode)
/// - Activity graph showing agent hierarchy and tool calls
/// - Synthesized conclusion
class LiveCouncilPanel extends StatefulWidget {
  final List<DashboardItem> items;
  const LiveCouncilPanel({super.key, required this.items});

  @override
  State<LiveCouncilPanel> createState() => _LiveCouncilPanelState();
}

class _LiveCouncilPanelState extends State<LiveCouncilPanel> {
  // Track expanded panels
  final Set<String> _expandedPanels = {};
  bool _showCriticReport = false;
  bool _showActivityGraph = false;

  @override
  Widget build(BuildContext context) {
    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: widget.items.length,
      itemBuilder: (context, index) {
        final item = widget.items[index];
        final council = item.councilData;
        if (council == null) return const SizedBox.shrink();

        return Padding(
          padding: const EdgeInsets.only(bottom: 16),
          child: _buildCouncilCard(council),
        );
      },
    );
  }

  Widget _buildCouncilCard(CouncilSynthesisData council) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.backgroundCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.surfaceBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildHeader(council),
          _buildMetricsRow(council),
          _buildViewToggle(council),
          if (_showActivityGraph && council.hasActivityGraph)
            _buildActivityGraphSection(council)
          else ...[
            if (council.panels.isNotEmpty) _buildExpertPanelsSection(council),
            if (council.hasCriticReport) _buildCriticSection(council),
          ],
          _buildSynthesisSection(council),
        ],
      ),
    );
  }

  Widget _buildViewToggle(CouncilSynthesisData council) {
    if (!council.hasActivityGraph && council.panels.isEmpty) {
      return const SizedBox.shrink();
    }

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      child: Row(
        children: [
          _buildToggleButton(
            label: 'Expert Findings',
            icon: Icons.psychology_rounded,
            isSelected: !_showActivityGraph,
            onTap: () => setState(() => _showActivityGraph = false),
          ),
          const SizedBox(width: 8),
          if (council.hasActivityGraph)
            _buildToggleButton(
              label: 'Activity Graph',
              icon: Icons.account_tree_rounded,
              isSelected: _showActivityGraph,
              onTap: () => setState(() => _showActivityGraph = true),
              badge: '${council.totalToolCalls}',
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
    String? badge,
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
            if (badge != null) ...[
              const SizedBox(width: 4),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  badge,
                  style: TextStyle(
                    fontSize: 9,
                    fontWeight: FontWeight.w600,
                    color: color,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildActivityGraphSection(CouncilSynthesisData council) {
    if (council.activityGraph == null) return const SizedBox.shrink();

    return Container(
      margin: const EdgeInsets.fromLTRB(14, 0, 14, 8),
      height: 400, // Fixed height for the graph
      child: CouncilActivityGraphWidget(graph: council.activityGraph!),
    );
  }

  Widget _buildHeader(CouncilSynthesisData council) {
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 10),
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
                  AppColors.primaryTeal.withValues(alpha: 0.2),
                  AppColors.primaryCyan.withValues(alpha: 0.15),
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(8),
            ),
            child: const Icon(
              Icons.groups_rounded,
              size: 18,
              color: AppColors.primaryTeal,
            ),
          ),
          const SizedBox(width: 10),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Council of Experts',
                style: GoogleFonts.inter(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
              Text(
                '${council.panels.length} experts • ${council.rounds} round${council.rounds > 1 ? 's' : ''}',
                style: GoogleFonts.inter(
                  fontSize: 11,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
          const Spacer(),
          _buildModeBadge(council.mode),
          const SizedBox(width: 8),
          _buildSeverityBadge(council.overallSeverity),
        ],
      ),
    );
  }

  Widget _buildMetricsRow(CouncilSynthesisData council) {
    final confidence = council.overallConfidence;

    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 6),
      child: Row(
        children: [
          // Confidence meter
          Expanded(
            child: _buildConfidenceMeter(confidence),
          ),
          const SizedBox(width: 12),
          // Round indicator (for debate mode)
          if (council.isDebateMode)
            _buildRoundIndicator(council.rounds),
        ],
      ),
    );
  }

  Widget _buildConfidenceMeter(double confidence) {
    final color = confidence >= 0.85
        ? AppColors.success
        : confidence >= 0.5
            ? AppColors.warning
            : AppColors.error;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(Icons.verified_rounded, size: 12, color: color),
            const SizedBox(width: 4),
            Text(
              'Council Confidence',
              style: GoogleFonts.inter(
                fontSize: 10,
                fontWeight: FontWeight.w500,
                color: AppColors.textSecondary,
              ),
            ),
            const Spacer(),
            Text(
              '${(confidence * 100).toStringAsFixed(0)}%',
              style: GoogleFonts.inter(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: color,
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: confidence,
            backgroundColor: color.withValues(alpha: 0.15),
            valueColor: AlwaysStoppedAnimation<Color>(color),
            minHeight: 6,
          ),
        ),
      ],
    );
  }

  Widget _buildRoundIndicator(int rounds) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: AppColors.secondaryPurple.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: AppColors.secondaryPurple.withValues(alpha: 0.3),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(
            Icons.loop_rounded,
            size: 12,
            color: AppColors.secondaryPurple,
          ),
          const SizedBox(width: 4),
          Text(
            '$rounds debate${rounds > 1 ? 's' : ''}',
            style: GoogleFonts.inter(
              fontSize: 10,
              fontWeight: FontWeight.w600,
              color: AppColors.secondaryPurple,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildExpertPanelsSection(CouncilSynthesisData council) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 8),
          child: Row(
            children: [
              const Icon(
                Icons.psychology_rounded,
                size: 14,
                color: AppColors.primaryCyan,
              ),
              const SizedBox(width: 6),
              Text(
                'Expert Findings',
                style: GoogleFonts.inter(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
        ),
        ...council.panels.map((panel) => _buildExpertPanelCard(panel)),
      ],
    );
  }

  Widget _buildExpertPanelCard(PanelFinding panel) {
    final isExpanded = _expandedPanels.contains(panel.panel);
    final severityColor = _getSeverityColor(panel.severity);
    final panelIcon = _getPanelIcon(panel.panel);

    return Container(
      margin: const EdgeInsets.fromLTRB(14, 0, 14, 8),
      decoration: BoxDecoration(
        color: AppColors.backgroundDark.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: severityColor.withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        children: [
          // Panel header (always visible)
          InkWell(
            onTap: () {
              setState(() {
                if (isExpanded) {
                  _expandedPanels.remove(panel.panel);
                } else {
                  _expandedPanels.add(panel.panel);
                }
              });
            },
            borderRadius: BorderRadius.circular(10),
            child: Padding(
              padding: const EdgeInsets.all(10),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: severityColor.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Icon(panelIcon, size: 14, color: severityColor),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          panel.displayName,
                          style: GoogleFonts.inter(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textPrimary,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          panel.summary,
                          maxLines: isExpanded ? 10 : 2,
                          overflow: TextOverflow.ellipsis,
                          style: GoogleFonts.inter(
                            fontSize: 10,
                            color: AppColors.textSecondary,
                            height: 1.4,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  Column(
                    children: [
                      _buildMiniSeverityBadge(panel.severity),
                      const SizedBox(height: 4),
                      Text(
                        '${(panel.confidence * 100).toStringAsFixed(0)}%',
                        style: GoogleFonts.inter(
                          fontSize: 9,
                          fontWeight: FontWeight.w600,
                          color: AppColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(width: 4),
                  Icon(
                    isExpanded
                        ? Icons.keyboard_arrow_up_rounded
                        : Icons.keyboard_arrow_down_rounded,
                    size: 18,
                    color: AppColors.textMuted,
                  ),
                ],
              ),
            ),
          ),
          // Expanded content
          if (isExpanded) ...[
            Container(
              width: double.infinity,
              padding: const EdgeInsets.fromLTRB(10, 0, 10, 10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (panel.evidence.isNotEmpty) ...[
                    _buildExpandedSection(
                      'Evidence',
                      Icons.fact_check_rounded,
                      panel.evidence,
                      AppColors.info,
                    ),
                  ],
                  if (panel.recommendedActions.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    _buildExpandedSection(
                      'Recommended Actions',
                      Icons.lightbulb_rounded,
                      panel.recommendedActions,
                      AppColors.warning,
                    ),
                  ],
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildExpandedSection(
    String title,
    IconData icon,
    List<String> items,
    Color color,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 11, color: color),
            const SizedBox(width: 4),
            Text(
              title,
              style: GoogleFonts.inter(
                fontSize: 10,
                fontWeight: FontWeight.w600,
                color: color,
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        ...items.map(
          (item) => Padding(
            padding: const EdgeInsets.only(left: 15, bottom: 3),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '•',
                  style: TextStyle(
                    fontSize: 10,
                    color: color.withValues(alpha: 0.6),
                  ),
                ),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    item,
                    style: GoogleFonts.inter(
                      fontSize: 10,
                      color: AppColors.textSecondary,
                      height: 1.3,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildCriticSection(CouncilSynthesisData council) {
    final critic = council.criticReport!;

    return Container(
      margin: const EdgeInsets.fromLTRB(14, 4, 14, 0),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            AppColors.secondaryPurple.withValues(alpha: 0.1),
            AppColors.primaryTeal.withValues(alpha: 0.05),
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: AppColors.secondaryPurple.withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        children: [
          // Critic header
          InkWell(
            onTap: () => setState(() => _showCriticReport = !_showCriticReport),
            borderRadius: BorderRadius.circular(10),
            child: Padding(
              padding: const EdgeInsets.all(10),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(6),
                    decoration: BoxDecoration(
                      color: AppColors.secondaryPurple.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: const Icon(
                      Icons.forum_rounded,
                      size: 14,
                      color: AppColors.secondaryPurple,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Debate Analysis',
                          style: GoogleFonts.inter(
                            fontSize: 11,
                            fontWeight: FontWeight.w600,
                            color: AppColors.textPrimary,
                          ),
                        ),
                        Text(
                          _getCriticSummary(critic),
                          style: GoogleFonts.inter(
                            fontSize: 10,
                            color: AppColors.textSecondary,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Icon(
                    _showCriticReport
                        ? Icons.keyboard_arrow_up_rounded
                        : Icons.keyboard_arrow_down_rounded,
                    size: 18,
                    color: AppColors.textMuted,
                  ),
                ],
              ),
            ),
          ),
          // Expanded critic content
          if (_showCriticReport)
            Padding(
              padding: const EdgeInsets.fromLTRB(10, 0, 10, 10),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (critic.agreements.isNotEmpty)
                    _buildCriticList(
                      'Agreements',
                      Icons.check_circle_rounded,
                      critic.agreements,
                      AppColors.success,
                    ),
                  if (critic.contradictions.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    _buildCriticList(
                      'Contradictions',
                      Icons.warning_rounded,
                      critic.contradictions,
                      AppColors.error,
                    ),
                  ],
                  if (critic.gaps.isNotEmpty) ...[
                    const SizedBox(height: 8),
                    _buildCriticList(
                      'Gaps',
                      Icons.help_rounded,
                      critic.gaps,
                      AppColors.warning,
                    ),
                  ],
                  const SizedBox(height: 8),
                  Row(
                    children: [
                      const Icon(
                        Icons.analytics_rounded,
                        size: 11,
                        color: AppColors.primaryCyan,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        'Revised Confidence: ',
                        style: GoogleFonts.inter(
                          fontSize: 10,
                          color: AppColors.textSecondary,
                        ),
                      ),
                      Text(
                        '${(critic.revisedConfidence * 100).toStringAsFixed(0)}%',
                        style: GoogleFonts.inter(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: AppColors.primaryCyan,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildCriticList(
    String title,
    IconData icon,
    List<String> items,
    Color color,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 11, color: color),
            const SizedBox(width: 4),
            Text(
              title,
              style: GoogleFonts.inter(
                fontSize: 10,
                fontWeight: FontWeight.w600,
                color: color,
              ),
            ),
            const SizedBox(width: 4),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                '${items.length}',
                style: TextStyle(
                  fontSize: 9,
                  fontWeight: FontWeight.w600,
                  color: color,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        ...items.map(
          (item) => Padding(
            padding: const EdgeInsets.only(left: 15, bottom: 3),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '•',
                  style: TextStyle(
                    fontSize: 10,
                    color: color.withValues(alpha: 0.6),
                  ),
                ),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    item,
                    style: GoogleFonts.inter(
                      fontSize: 10,
                      color: AppColors.textSecondary,
                      height: 1.3,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildSynthesisSection(CouncilSynthesisData council) {
    if (council.synthesis.isEmpty) return const SizedBox.shrink();

    return Container(
      margin: const EdgeInsets.all(14),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.backgroundDark.withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: AppColors.primaryTeal.withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.summarize_rounded,
                size: 12,
                color: AppColors.primaryTeal,
              ),
              const SizedBox(width: 6),
              Text(
                'Council Synthesis',
                style: GoogleFonts.inter(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: AppColors.primaryTeal,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            council.synthesis,
            style: GoogleFonts.inter(
              fontSize: 11,
              color: AppColors.textSecondary,
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }

  String _getCriticSummary(CriticReport critic) {
    final parts = <String>[];
    if (critic.agreements.isNotEmpty) {
      parts.add('${critic.agreements.length} agreement${critic.agreements.length > 1 ? 's' : ''}');
    }
    if (critic.contradictions.isNotEmpty) {
      parts.add('${critic.contradictions.length} contradiction${critic.contradictions.length > 1 ? 's' : ''}');
    }
    if (critic.gaps.isNotEmpty) {
      parts.add('${critic.gaps.length} gap${critic.gaps.length > 1 ? 's' : ''}');
    }
    return parts.isEmpty ? 'Analysis complete' : parts.join(' • ');
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
      default: // standard
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
          Icon(icon, size: 11, color: color),
          const SizedBox(width: 4),
          Text(
            mode.toUpperCase(),
            style: GoogleFonts.inter(
              fontSize: 10,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSeverityBadge(String severity) {
    final color = _getSeverityColor(severity);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Text(
        severity.toUpperCase(),
        style: GoogleFonts.inter(
          fontSize: 10,
          fontWeight: FontWeight.w600,
          color: color,
        ),
      ),
    );
  }

  Widget _buildMiniSeverityBadge(String severity) {
    final color = _getSeverityColor(severity);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        severity.toUpperCase(),
        style: TextStyle(
          fontSize: 8,
          fontWeight: FontWeight.w600,
          color: color,
        ),
      ),
    );
  }

  Color _getSeverityColor(String severity) {
    switch (severity.toLowerCase()) {
      case 'critical':
        return AppColors.error;
      case 'warning':
        return AppColors.warning;
      case 'healthy':
        return AppColors.success;
      default: // info
        return AppColors.primaryCyan;
    }
  }

  IconData _getPanelIcon(String panel) {
    switch (panel.toLowerCase()) {
      case 'trace':
        return Icons.timeline_rounded;
      case 'metrics':
        return Icons.analytics_rounded;
      case 'logs':
        return Icons.description_rounded;
      case 'alerts':
        return Icons.notifications_active_rounded;
      default:
        return Icons.help_outline_rounded;
    }
  }
}
