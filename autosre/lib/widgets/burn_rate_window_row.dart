import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import 'slo_burn_rate_data.dart';

/// A single expandable window row in the SLO burn rate analysis.
class BurnRateWindowRow extends StatefulWidget {
  final BurnRateWindow window;

  const BurnRateWindowRow({super.key, required this.window});

  @override
  State<BurnRateWindowRow> createState() => _BurnRateWindowRowState();
}

class _BurnRateWindowRowState extends State<BurnRateWindowRow> {
  bool _isExpanded = false;

  String _formatDuration(Duration d) {
    if (d.inHours >= 24) {
      final days = d.inDays;
      return '${days}d';
    } else if (d.inHours > 0) {
      return '${d.inHours}h';
    }
    return '${d.inMinutes}m';
  }

  @override
  Widget build(BuildContext context) {
    final isTriggered = widget.window.alertTriggered;
    final burnRatio =
        (widget.window.burnRate / widget.window.threshold).clamp(0.0, 2.0);

    final Color windowColor;
    if (isTriggered) {
      windowColor = AppColors.error;
    } else if (burnRatio > 0.7) {
      windowColor = AppColors.warning;
    } else {
      windowColor = AppColors.success;
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: GlassDecoration.card(
        borderRadius: 10,
        borderColor:
            isTriggered ? AppColors.error.withValues(alpha: 0.3) : null,
      ),
      child: Column(
        children: [
          InkWell(
            onTap: () {
              setState(() {
                _isExpanded = !_isExpanded;
              });
            },
            borderRadius: BorderRadius.circular(10),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Row(
                children: [
                  // Alert status indicator
                  Container(
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: windowColor,
                      shape: BoxShape.circle,
                      boxShadow: [
                        if (isTriggered)
                          BoxShadow(
                            color: windowColor.withValues(alpha: 0.6),
                            blurRadius: 6,
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 10),

                  // Window label
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          widget.window.label,
                          style: const TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w500,
                            color: AppColors.textPrimary,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          _formatDuration(widget.window.windowDuration),
                          style: const TextStyle(
                            fontSize: 11,
                            color: AppColors.textMuted,
                          ),
                        ),
                      ],
                    ),
                  ),

                  // Burn rate value
                  Text(
                    '${widget.window.burnRate.toStringAsFixed(2)}x',
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w700,
                      fontFamily: 'monospace',
                      color: windowColor,
                    ),
                  ),
                  const SizedBox(width: 8),

                  // Alert triggered badge
                  if (isTriggered)
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 6,
                        vertical: 2,
                      ),
                      decoration: BoxDecoration(
                        color: AppColors.error.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(
                          color: AppColors.error.withValues(alpha: 0.3),
                        ),
                      ),
                      child: const Text(
                        'ALERT',
                        style: TextStyle(
                          fontSize: 9,
                          fontWeight: FontWeight.w700,
                          color: AppColors.error,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ),

                  const SizedBox(width: 6),

                  // Expand chevron
                  AnimatedRotation(
                    duration: const Duration(milliseconds: 200),
                    turns: _isExpanded ? 0.5 : 0,
                    child: const Icon(
                      Icons.expand_more,
                      size: 18,
                      color: AppColors.textMuted,
                    ),
                  ),
                ],
              ),
            ),
          ),

          // Expanded details
          AnimatedCrossFade(
            duration: const Duration(milliseconds: 200),
            firstChild: Padding(
              padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Burn rate bar
                  Row(
                    children: [
                      const Text(
                        'Burn Rate',
                        style: TextStyle(
                          fontSize: 11,
                          color: AppColors.textMuted,
                        ),
                      ),
                      const Spacer(),
                      Text(
                        'Threshold: ${widget.window.threshold.toStringAsFixed(1)}x',
                        style: const TextStyle(
                          fontSize: 11,
                          color: AppColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Stack(
                    children: [
                      Container(
                        height: 6,
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.1),
                          borderRadius: BorderRadius.circular(3),
                        ),
                      ),
                      LayoutBuilder(
                        builder: (context, constraints) {
                          final barWidth = constraints.maxWidth *
                              (burnRatio / 2.0).clamp(0.0, 1.0);
                          return Container(
                            height: 6,
                            width: barWidth,
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                colors: [
                                  windowColor,
                                  windowColor.withValues(alpha: 0.7),
                                ],
                              ),
                              borderRadius: BorderRadius.circular(3),
                            ),
                          );
                        },
                      ),
                      // Threshold marker
                      LayoutBuilder(
                        builder: (context, constraints) {
                          final markerPos = constraints.maxWidth *
                              (widget.window.threshold /
                                      (widget.window.threshold * 2.0))
                                  .clamp(0.0, 1.0);
                          return Positioned(
                            left: markerPos,
                            child: Container(
                              width: 2,
                              height: 6,
                              color: AppColors.textSecondary,
                            ),
                          );
                        },
                      ),
                    ],
                  ),
                ],
              ),
            ),
            secondChild: const SizedBox.shrink(),
            crossFadeState: _isExpanded
                ? CrossFadeState.showFirst
                : CrossFadeState.showSecond,
          ),
        ],
      ),
    );
  }
}
