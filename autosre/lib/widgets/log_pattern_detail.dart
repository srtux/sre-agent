import 'package:flutter/material.dart';
import '../models/adk_schema.dart';
import '../theme/app_theme.dart';
import 'log_pattern_helpers.dart';
import 'log_pattern_painters.dart';

/// Expanded detail panel for a selected log pattern.
class LogPatternDetail extends StatelessWidget {
  final LogPattern pattern;
  final VoidCallback onClose;

  const LogPatternDetail({
    super.key,
    required this.pattern,
    required this.onClose,
  });

  @override
  Widget build(BuildContext context) {
    final severity = getDominantSeverity(pattern);
    final severityColor = getLogSeverityColor(severity);
    final distribution = generateFrequencyDistribution(pattern.count);

    return Container(
      margin: const EdgeInsets.all(12),
      padding: const EdgeInsets.all(14),
      decoration: GlassDecoration.elevated(
        borderRadius: 12,
        withGlow: severity == 'ERROR',
        glowColor: severityColor,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: severityColor.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Icon(
                  getLogSeverityIcon(severity),
                  size: 16,
                  color: severityColor,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Pattern Details',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    Text(
                      '${pattern.count} occurrences',
                      style: const TextStyle(
                        fontSize: 10,
                        color: AppColors.textMuted,
                      ),
                    ),
                  ],
                ),
              ),
              IconButton(
                icon: const Icon(Icons.close, size: 16),
                onPressed: onClose,
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
                color: AppColors.textMuted,
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Template with full highlighting
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.3),
              borderRadius: BorderRadius.circular(8),
            ),
            child: SelectableText.rich(
              TextSpan(children: _buildHighlightedSpans(pattern.template)),
            ),
          ),

          const SizedBox(height: 12),

          // Frequency distribution chart
          const Text(
            'Frequency Distribution',
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w600,
              color: AppColors.textMuted,
            ),
          ),
          const SizedBox(height: 6),
          SizedBox(
            height: 40,
            child: CustomPaint(
              painter: FrequencyBarPainter(
                values: distribution,
                color: severityColor,
              ),
              child: Container(),
            ),
          ),

          const SizedBox(height: 12),

          // Severity breakdown
          const Text(
            'Severity Breakdown',
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w600,
              color: AppColors.textMuted,
            ),
          ),
          const SizedBox(height: 6),
          _buildSeverityBreakdownBar(),
        ],
      ),
    );
  }

  List<TextSpan> _buildHighlightedSpans(String template) {
    final regex = RegExp(r'(<\*>|\{[^}]+\}|\[[^\]]+\]|%[a-zA-Z]+)');
    final matches = regex.allMatches(template);
    var spans = <TextSpan>[];
    var lastEnd = 0;

    for (final match in matches) {
      if (match.start > lastEnd) {
        spans.add(
          TextSpan(
            text: template.substring(lastEnd, match.start),
            style: const TextStyle(
              fontSize: 12,
              color: AppColors.textSecondary,
              fontFamily: 'monospace',
              height: 1.5,
            ),
          ),
        );
      }
      spans.add(
        TextSpan(
          text: match.group(0),
          style: TextStyle(
            fontSize: 12,
            color: AppColors.primaryCyan,
            fontFamily: 'monospace',
            fontWeight: FontWeight.w600,
            backgroundColor: AppColors.primaryCyan.withValues(alpha: 0.1),
            height: 1.5,
          ),
        ),
      );
      lastEnd = match.end;
    }

    if (lastEnd < template.length) {
      spans.add(
        TextSpan(
          text: template.substring(lastEnd),
          style: const TextStyle(
            fontSize: 12,
            color: AppColors.textSecondary,
            fontFamily: 'monospace',
            height: 1.5,
          ),
        ),
      );
    }

    return spans;
  }

  Widget _buildSeverityBreakdownBar() {
    final total = pattern.severityCounts.values.fold(0, (a, b) => a + b);
    if (total == 0) return const SizedBox.shrink();

    return Column(
      children: [
        // Stacked bar
        Container(
          height: 8,
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(4)),
          clipBehavior: Clip.antiAlias,
          child: Row(
            children: pattern.severityCounts.entries.map((e) {
              final percent = e.value / total;
              return Expanded(
                flex: (percent * 100).round(),
                child: Container(color: getLogSeverityColor(e.key)),
              );
            }).toList(),
          ),
        ),
        const SizedBox(height: 8),
        // Legend
        Wrap(
          spacing: 12,
          runSpacing: 6,
          children: pattern.severityCounts.entries.map((e) {
            final color = getLogSeverityColor(e.key);
            final percent = (e.value / total * 100).toStringAsFixed(1);
            return Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 8,
                  height: 8,
                  decoration: BoxDecoration(
                    color: color,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
                const SizedBox(width: 4),
                Text(
                  '${e.key}: ${e.value} ($percent%)',
                  style: const TextStyle(
                    fontSize: 10,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            );
          }).toList(),
        ),
      ],
    );
  }
}
