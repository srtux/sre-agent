import 'package:flutter/material.dart';
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../theme/app_theme.dart';

class HelpCard extends StatefulWidget {
  final IconData icon;
  final String title;
  final String description;
  final String? expandedContent;
  final VoidCallback? onTap;

  const HelpCard({
    super.key,
    required this.icon,
    required this.title,
    required this.description,
    this.expandedContent,
    this.onTap,
  });

  @override
  State<HelpCard> createState() => _HelpCardState();
}

class _HelpCardState extends State<HelpCard> {
  bool _isExpanded = false;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: '${widget.title} help card',
      expanded: _isExpanded,
      child: Container(
      decoration: BoxDecoration(
        color: AppColors.backgroundCard.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: AppColors.surfaceBorder,
          width: 1,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.3),
            blurRadius: 15,
            offset: const Offset(0, 5),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: () {
            setState(() {
              _isExpanded = !_isExpanded;
            });
            widget.onTap?.call();
          },
          child: Padding(
            padding: const EdgeInsets.all(20.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: AppColors.primaryTeal.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(
                          color: AppColors.primaryTeal.withValues(alpha: 0.3),
                        ),
                      ),
                      child: Icon(
                        widget.icon,
                        color: AppColors.primaryTeal,
                        size: 26,
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                      child: Text(
                        widget.title,
                        style: const TextStyle(
                          color: AppColors.textPrimary,
                          fontSize: 18,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 0.3,
                        ),
                      ),
                    ),
                    if (widget.expandedContent != null || widget.onTap != null)
                      Container(
                        padding: const EdgeInsets.all(4),
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: Colors.white.withValues(alpha: 0.05),
                        ),
                        child: Icon(
                          _isExpanded ? Icons.expand_less : Icons.expand_more,
                          color: AppColors.textSecondary,
                          size: 20,
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 16),
                Text(
                  widget.description,
                  style: const TextStyle(
                    color: AppColors.textSecondary,
                    fontSize: 15,
                    height: 1.5,
                  ),
                ),
                if (_isExpanded) ...[
                  const SizedBox(height: 20),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.black.withValues(alpha: 0.25),
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: AppColors.surfaceBorder,
                      ),
                    ),
                    child: widget.expandedContent != null
                        ? MarkdownBody(
                            data: widget.expandedContent!,
                            styleSheet: MarkdownStyleSheet(
                              p: const TextStyle(
                                color: AppColors.textSecondary,
                                fontSize: 14,
                                height: 1.6,
                              ),
                              h3: const TextStyle(
                                color: AppColors.textPrimary,
                                fontSize: 16,
                                fontWeight: FontWeight.w600,
                                height: 2.0,
                              ),
                              strong: const TextStyle(
                                color: AppColors.primaryCyan,
                                fontWeight: FontWeight.w700,
                              ),
                              code: GoogleFonts.jetBrainsMono(
                                backgroundColor: Colors.black.withValues(alpha: 0.3),
                                color: AppColors.success,
                                fontSize: 13,
                              ),
                              codeblockDecoration: BoxDecoration(
                                color: Colors.black.withValues(alpha: 0.3),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              listBullet: const TextStyle(color: AppColors.primaryTeal),
                            ),
                          )
                        : const Center(
                            child: Padding(
                              padding: EdgeInsets.symmetric(vertical: 20),
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: AppColors.primaryTeal,
                              ),
                            ),
                          ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    ),
    );
  }
}
