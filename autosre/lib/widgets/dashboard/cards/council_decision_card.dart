import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';
import '../../../theme/app_theme.dart';
import '../../../services/dashboard_state.dart';
import '../../../models/adk_schema.dart';

/// A premium card widget for displaying council decisions and debate outcomes.
///
/// Replaces raw JSON dumps with a readable, engaging summary including
/// agent consensus, votes, and reasoning.
class CouncilDecisionCard extends StatelessWidget {
  final DashboardItem item;

  const CouncilDecisionCard({
    super.key,
    required this.item,
  });

  @override
  Widget build(BuildContext context) {
    final data = item.rawData;
    final council = item.councilData;

    // Use specific votes if available, otherwise map from panels
    final votes = data['votes'] as List<dynamic>? ??
                               council?.panels.map((p) => {
                                 'agent': p.displayName,
                                 'vote': p.severity == 'healthy' ? 'yes' : (p.severity == 'critical' ? 'no' : 'info'),
                                 'reason': p.summary,
                               }).toList() ?? [];

    // Support both the new data format and the existing CouncilSynthesisData model
    final summary = data['summary'] ??
                  data['conclusion'] ??
                  council?.synthesis ??
                  'No conclusion available.';

    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // New Summary Header with Severity and Confidence
          if (council != null) ...[
            _buildSummaryHeader(council),
            const SizedBox(height: 20),
          ],

          // Panel Status Overview Grid
          if (council != null && council.panels.isNotEmpty) ...[
            _buildPanelGrid(council.panels),
            const SizedBox(height: 24),
          ],

          // Vote Tally Section
          if (votes.isNotEmpty) ...[
            Text(
              'EXPERT CONSENSUS',
              style: GoogleFonts.inter(
                fontSize: 10,
                fontWeight: FontWeight.w800,
                color: AppColors.textMuted,
                letterSpacing: 1.2,
              ),
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 16,
              runSpacing: 16,
              children: votes.map((v) => _buildAgentVote(v)).toList(),
            ),
            const SizedBox(height: 24),
            Container(
              height: 1,
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  colors: [
                    AppColors.surfaceBorder,
                    AppColors.surfaceBorder.withValues(alpha: 0.2),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 20),
          ],

          // Content Body
          Text(
            'CONCLUSION & REASONING',
            style: GoogleFonts.inter(
              fontSize: 10,
              fontWeight: FontWeight.w800,
              color: AppColors.textMuted,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: 12),
          MarkdownBody(
            data: summary.toString(),
            styleSheet: MarkdownStyleSheet(
              p: GoogleFonts.inter(
                fontSize: 13,
                color: AppColors.textSecondary,
                height: 1.6,
              ),
              strong: GoogleFonts.inter(
                fontWeight: FontWeight.w700,
                color: AppColors.textPrimary,
              ),
              code: GoogleFonts.jetBrainsMono(
                fontSize: 11,
                backgroundColor: AppColors.backgroundDark.withValues(alpha: 0.5),
                color: AppColors.primaryCyan,
              ),
            ),
          ),

          const SizedBox(height: 24),

          // Detailed Findings Section
          if (council != null && council.panels.isNotEmpty) ...[
            Text(
              'FINDINGS BY PANEL',
              style: GoogleFonts.inter(
                fontSize: 10,
                fontWeight: FontWeight.w800,
                color: AppColors.textMuted,
                letterSpacing: 1.2,
              ),
            ),
            const SizedBox(height: 12),
            ...council.panels.map((panel) => _buildPanelFinding(panel)),
            const SizedBox(height: 16),
          ],

          // Technical Details (ExpansionTile)
          Theme(
            data: Theme.of(context).copyWith(
              dividerColor: Colors.transparent,
              hoverColor: Colors.transparent,
              splashColor: Colors.transparent,
            ),
            child: ExpansionTile(
              title: Text(
                'View Raw Data',
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 10,
                  fontWeight: FontWeight.w500,
                  color: AppColors.textMuted.withValues(alpha: 0.7),
                ),
              ),
              tilePadding: EdgeInsets.zero,
              childrenPadding: EdgeInsets.zero,
              iconColor: AppColors.textMuted,
              collapsedIconColor: AppColors.textMuted,
              children: [
                const SizedBox(height: 8),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppColors.backgroundDark.withValues(alpha: 0.5),
                    borderRadius: BorderRadius.circular(8),
                    border: Border.all(
                      color: AppColors.surfaceBorder.withValues(alpha: 0.5),
                    ),
                  ),
                  child: SelectableText(
                    const JsonEncoder.withIndent('  ').convert(data),
                    style: GoogleFonts.jetBrainsMono(
                      fontSize: 11,
                      color: AppColors.textSecondary.withValues(alpha: 0.8),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryHeader(CouncilSynthesisData council) {
    final severityColor = _getSeverityColor(council.overallSeverity);
    final confidencePercent = (council.overallConfidence * 100).toInt();

    return Row(
      children: [
        // Severity Indicator
        Expanded(
          flex: 3,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: severityColor.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: severityColor.withValues(alpha: 0.2),
              ),
            ),
            child: Row(
              children: [
                Icon(
                  council.overallSeverity == 'healthy'
                    ? Icons.check_circle_rounded
                    : (council.overallSeverity == 'critical'
                        ? Icons.report_rounded
                        : Icons.info_rounded),
                  size: 16,
                  color: severityColor,
                ),
                const SizedBox(width: 8),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'OVERALL SEVERITY',
                      style: GoogleFonts.inter(
                        fontSize: 8,
                        fontWeight: FontWeight.w800,
                        color: severityColor.withValues(alpha: 0.7),
                        letterSpacing: 0.5,
                      ),
                    ),
                    Text(
                      council.overallSeverity.toUpperCase(),
                      style: GoogleFonts.inter(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: severityColor,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
        const SizedBox(width: 12),
        // Confidence Indicator
        Expanded(
          flex: 2,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: AppColors.backgroundDark.withValues(alpha: 0.3),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: AppColors.surfaceBorder.withValues(alpha: 0.5),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'CONFIDENCE',
                  style: GoogleFonts.inter(
                    fontSize: 8,
                    fontWeight: FontWeight.w800,
                    color: AppColors.textMuted,
                    letterSpacing: 0.5,
                  ),
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Expanded(
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(2),
                        child: LinearProgressIndicator(
                          value: council.overallConfidence,
                          minHeight: 4,
                          backgroundColor: AppColors.surfaceBorder.withValues(alpha: 0.3),
                          valueColor: AlwaysStoppedAnimation<Color>(
                            council.overallConfidence > 0.8
                              ? AppColors.primaryCyan
                              : (council.overallConfidence > 0.5
                                  ? AppColors.warning
                                  : AppColors.error),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      '$confidencePercent%',
                      style: GoogleFonts.jetBrainsMono(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                        color: AppColors.textPrimary,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildPanelGrid(List<PanelFinding> panels) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'PANEL STATUS',
          style: GoogleFonts.inter(
            fontSize: 10,
            fontWeight: FontWeight.w800,
            color: AppColors.textMuted,
            letterSpacing: 1.2,
          ),
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 12,
          runSpacing: 12,
          children: panels.map((p) => _buildPanelBadge(p)).toList(),
        ),
      ],
    );
  }

  Widget _buildPanelBadge(PanelFinding panel) {
    final severityColor = _getSeverityColor(panel.severity);
    final icon = _getPanelIcon(panel.panel);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.backgroundDark.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: severityColor.withValues(alpha: 0.3),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: severityColor),
          const SizedBox(width: 8),
          Text(
            panel.panel.toUpperCase(),
            style: GoogleFonts.inter(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(width: 6),
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(
              color: severityColor,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: severityColor.withValues(alpha: 0.5),
                  blurRadius: 4,
                  spreadRadius: 1,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPanelFinding(PanelFinding finding) {
    final severityColor = _getSeverityColor(finding.severity);
    final icon = _getPanelIcon(finding.panel);

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: AppColors.backgroundDark.withValues(alpha: 0.3),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: AppColors.surfaceBorder.withValues(alpha: 0.5),
        ),
      ),
      child: ExpansionTile(
        key: PageStorageKey<String>(finding.panel),
        leading: Container(
          padding: const EdgeInsets.all(6),
          decoration: BoxDecoration(
            color: severityColor.withValues(alpha: 0.15),
            shape: BoxShape.circle,
          ),
          child: Icon(icon, size: 14, color: severityColor),
        ),
        title: Row(
          children: [
            Expanded(
              child: Text(
                finding.displayName.toUpperCase(),
                style: GoogleFonts.inter(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                  letterSpacing: 0.5,
                ),
              ),
            ),
            Text(
              '${(finding.confidence * 100).toInt()}%',
              style: GoogleFonts.jetBrainsMono(
                fontSize: 10,
                fontWeight: FontWeight.w600,
                color: AppColors.textMuted,
              ),
            ),
          ],
        ),
        subtitle: Text(
          finding.summary,
          style: GoogleFonts.inter(
            fontSize: 12,
            color: AppColors.textSecondary,
          ),
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
          decoration: BoxDecoration(
            color: severityColor.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(4),
            border: Border.all(color: severityColor.withValues(alpha: 0.2)),
          ),
          child: Text(
            finding.severity.toUpperCase(),
            style: TextStyle(
              fontSize: 8,
              fontWeight: FontWeight.w800,
              color: severityColor,
            ),
          ),
        ),
        childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
        expandedCrossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Divider(height: 1, color: AppColors.surfaceBorder),
          const SizedBox(height: 12),
          Text(
            'SUMMARY',
            style: GoogleFonts.inter(
              fontSize: 9,
              fontWeight: FontWeight.w800,
              color: AppColors.textMuted,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            finding.summary,
            style: GoogleFonts.inter(
              fontSize: 13,
              color: AppColors.textSecondary,
              height: 1.5,
            ),
          ),
          if (finding.evidence.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(
              'EVIDENCE',
              style: GoogleFonts.inter(
                fontSize: 9,
                fontWeight: FontWeight.w800,
                color: AppColors.textMuted,
              ),
            ),
            const SizedBox(height: 8),
            ...finding.evidence.map((e) => _buildBulletItem(e)),
          ],
          if (finding.recommendedActions.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(
              'RECOMMENDED ACTIONS',
              style: GoogleFonts.inter(
                fontSize: 9,
                fontWeight: FontWeight.w800,
                color: AppColors.textMuted,
              ),
            ),
            const SizedBox(height: 8),
            ...finding.recommendedActions.map((a) => _buildBulletItem(a, isAction: true)),
          ],
        ],
      ),
    );
  }

  Widget _buildBulletItem(String text, {bool isAction = false}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 5),
            child: Icon(
              isAction ? Icons.bolt_rounded : Icons.circle,
              size: isAction ? 12 : 6,
              color: isAction ? AppColors.warning : AppColors.textMuted.withValues(alpha: 0.5),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: GoogleFonts.inter(
                fontSize: 12,
                color: AppColors.textSecondary,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Color _getSeverityColor(String severity) {
    switch (severity.toLowerCase()) {
      case 'critical':
        return AppColors.error;
      case 'warning':
        return AppColors.warning;
      case 'info':
        return AppColors.info;
      case 'healthy':
        return AppColors.success;
      default:
        return AppColors.textMuted;
    }
  }

  IconData _getPanelIcon(String panel) {
    switch (panel.toLowerCase()) {
      case 'trace':
        return Icons.timeline_rounded;
      case 'metrics':
        return Icons.show_chart_rounded;
      case 'logs':
        return Icons.article_outlined;
      case 'alerts':
        return Icons.notifications_active_outlined;
      default:
        return Icons.psychology_rounded;
    }
  }

  /// Builds the header row meant to be used in [DashboardCardWrapper.header].
  static Widget buildHeader(DashboardItem item) {
    final data = item.rawData;
    final council = item.councilData;

    // Subject mapping: rawData['subject'] or default to "Council of Experts" if it looks like the old model
    final subject = data['subject']?.toString() ??
                  (council != null ? 'Council of Experts' : 'Council Debate');

    // Status mapping: rawData['status'] or map council severity to status
    var status = data['status']?.toString().toLowerCase() ?? '';
    if (status.isEmpty && council != null) {
      status = council.overallSeverity == 'healthy' ? 'approved' :
               (council.overallSeverity == 'critical' ? 'rejected' : 'in progress');
    } else if (status.isEmpty) {
      status = 'in progress';
    }

    return Row(
      children: [
        Container(
          padding: const EdgeInsets.all(6),
          decoration: BoxDecoration(
            color: AppColors.primaryTeal.withValues(alpha: 0.15),
            borderRadius: BorderRadius.circular(6),
          ),
          child: const Icon(
            Icons.gavel_rounded,
            size: 14,
            color: AppColors.primaryTeal,
          ),
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            subject,
            style: GoogleFonts.inter(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
            overflow: TextOverflow.ellipsis,
          ),
        ),
        const SizedBox(width: 8),
        _buildStatusBadge(status),
      ],
    );
  }

  static Widget _buildStatusBadge(String status) {
    Color bgColor;
    String label;

    if (status == 'approved') {
      bgColor = AppColors.success;
      label = 'APPROVED';
    } else if (status == 'rejected') {
      bgColor = AppColors.error;
      label = 'REJECTED';
    } else {
      bgColor = AppColors.warning;
      label = 'IN PROGRESS';
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: bgColor.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(
          color: bgColor.withValues(alpha: 0.2),
        ),
      ),
      child: Text(
        label,
        style: GoogleFonts.inter(
          fontSize: 9,
          fontWeight: FontWeight.w800,
          color: bgColor,
          letterSpacing: 0.5,
        ),
      ),
    );
  }

  Widget _buildAgentVote(dynamic voteMap) {
    final agentName = voteMap['agent']?.toString() ?? 'Agent';
    final voteValue = voteMap['vote']?.toString().toLowerCase() ?? '';
    final reason = voteMap['reason']?.toString() ?? 'No reasoning provided.';

    final isYes = voteValue == 'yes' || voteValue == 'approve';
    final isNo = voteValue == 'no' || voteValue == 'reject';

    return Tooltip(
      message: '$agentName: $reason',
      preferBelow: false,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Stack(
            children: [
              _AgentAvatar(name: agentName),
              Positioned(
                right: 0,
                bottom: 0,
                child: Container(
                  padding: const EdgeInsets.all(2),
                  decoration: BoxDecoration(
                    color: isYes
                        ? AppColors.success
                        : (isNo ? AppColors.error : AppColors.warning),
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: AppColors.backgroundCard,
                      width: 2,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.2),
                        blurRadius: 4,
                        offset: const Offset(0, 2),
                      ),
                    ],
                  ),
                  child: Icon(
                    isYes ? Icons.check : (isNo ? Icons.close : Icons.priority_high),
                    size: 8,
                    color: Colors.white,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          SizedBox(
            width: 50,
            child: Text(
              agentName,
              style: GoogleFonts.inter(
                fontSize: 9,
                fontWeight: FontWeight.w500,
                color: AppColors.textMuted,
              ),
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }
}

class _AgentAvatar extends StatelessWidget {
  final String name;
  const _AgentAvatar({required this.name});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 36,
      height: 36,
      decoration: BoxDecoration(
        color: AppColors.secondaryPurple.withValues(alpha: 0.15),
        shape: BoxShape.circle,
        border: Border.all(
          color: AppColors.secondaryPurple.withValues(alpha: 0.3),
          width: 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: AppColors.secondaryPurple.withValues(alpha: 0.1),
            blurRadius: 8,
            spreadRadius: 1,
          ),
        ],
      ),
      child: const Icon(
        Icons.smart_toy_rounded,
        size: 20,
        color: AppColors.secondaryPurple,
      ),
    );
  }
}
