import 'package:flutter/material.dart';
import '../models/adk_schema.dart';
import '../theme/app_theme.dart';
import 'log_pattern_helpers.dart';
import 'log_pattern_painters.dart';

/// A single row in the log pattern analysis table.
class LogPatternRow extends StatefulWidget {
  final LogPattern pattern;
  final int index;
  final int total;
  final Animation<double> animation;
  final bool isSelected;
  final VoidCallback onTap;

  const LogPatternRow({
    super.key,
    required this.pattern,
    required this.index,
    required this.total,
    required this.animation,
    required this.isSelected,
    required this.onTap,
  });

  @override
  State<LogPatternRow> createState() => _LogPatternRowState();
}

class _LogPatternRowState extends State<LogPatternRow> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    final severity = getDominantSeverity(widget.pattern);
    final severityColor = getLogSeverityColor(severity);
    final distribution = generateFrequencyDistribution(widget.pattern.count);
    final trend = getFrequencyTrend(distribution);

    final staggerDelay = widget.index / widget.total;
    final animValue = ((widget.animation.value - staggerDelay * 0.3) / 0.7)
        .clamp(0.0, 1.0);

    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedOpacity(
          duration: const Duration(milliseconds: 200),
          opacity: animValue,
          child: Container(
            margin: const EdgeInsets.only(bottom: 1),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: widget.isSelected
                  ? severityColor.withValues(alpha: 0.1)
                  : _isHovered
                  ? Colors.white.withValues(alpha: 0.04)
                  : Colors.white.withValues(alpha: 0.015),
              border: Border(
                left: BorderSide(
                  color: widget.isSelected ? severityColor : Colors.transparent,
                  width: 3,
                ),
                right: const BorderSide(color: AppColors.surfaceBorder),
                bottom: const BorderSide(color: AppColors.surfaceBorder),
              ),
            ),
            child: Row(
              children: [
                // Trend indicator
                SizedBox(width: 100, child: _buildTrendIndicator(trend)),

                // Count
                SizedBox(
                  width: 100,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 3,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.primaryTeal.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      formatLogCount(widget.pattern.count),
                      style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: AppColors.primaryTeal,
                        fontFamily: 'monospace',
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                ),

                // Severity badge
                SizedBox(
                  width: 140,
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 6,
                      vertical: 3,
                    ),
                    decoration: BoxDecoration(
                      color: severityColor.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(
                        color: severityColor.withValues(alpha: 0.3),
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          getLogSeverityIcon(severity),
                          size: 10,
                          color: severityColor,
                        ),
                        const SizedBox(width: 3),
                        Text(
                          severity,
                          style: TextStyle(
                            fontSize: 9,
                            fontWeight: FontWeight.w600,
                            color: severityColor,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

                const SizedBox(width: 8),

                // Pattern template with syntax highlighting
                Expanded(
                  child: _buildHighlightedTemplate(widget.pattern.template),
                ),

                // Mini sparkline
                SizedBox(
                  width: 80,
                  height: 24,
                  child: CustomPaint(
                    painter: FrequencySparklinePainter(
                      values: distribution,
                      color: severityColor,
                      animation: animValue,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildTrendIndicator(String trend) {
    Color color;
    IconData icon;
    String label;

    switch (trend) {
      case 'up':
        color = AppColors.error;
        icon = Icons.trending_up;
        label = 'Up';
        break;
      case 'down':
        color = AppColors.success;
        icon = Icons.trending_down;
        label = 'Down';
        break;
      default:
        color = AppColors.textMuted;
        icon = Icons.trending_flat;
        label = 'Stable';
    }

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(icon, size: 14, color: color),
        const SizedBox(width: 2),
        Text(
          label,
          style: TextStyle(
            fontSize: 9,
            color: color,
            fontWeight: FontWeight.w500,
          ),
        ),
      ],
    );
  }

  Widget _buildHighlightedTemplate(String template) {
    final regex = RegExp(r'(<\*>|\{[^}]+\}|\[[^\]]+\]|%[a-zA-Z]+)');
    final matches = regex.allMatches(template);

    if (matches.isEmpty) {
      return Text(
        template,
        style: const TextStyle(
          fontSize: 11,
          color: AppColors.textSecondary,
          fontFamily: 'monospace',
        ),
        maxLines: 2,
        overflow: TextOverflow.ellipsis,
      );
    }

    var spans = <InlineSpan>[];
    var lastEnd = 0;

    for (final match in matches) {
      if (match.start > lastEnd) {
        spans.add(
          TextSpan(
            text: template.substring(lastEnd, match.start),
            style: const TextStyle(
              fontSize: 11,
              color: AppColors.textSecondary,
              fontFamily: 'monospace',
            ),
          ),
        );
      }
      spans.add(
        TextSpan(
          text: match.group(0),
          style: const TextStyle(
            fontSize: 11,
            color: AppColors.primaryCyan,
            fontFamily: 'monospace',
            fontWeight: FontWeight.w500,
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
            fontSize: 11,
            color: AppColors.textSecondary,
            fontFamily: 'monospace',
          ),
        ),
      );
    }

    return RichText(
      text: TextSpan(children: spans),
      maxLines: 2,
      overflow: TextOverflow.ellipsis,
    );
  }
}
