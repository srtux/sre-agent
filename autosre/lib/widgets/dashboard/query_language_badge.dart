import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../theme/app_theme.dart';

/// A compact badge that displays the active query language for a dashboard panel.
///
/// Optionally links to external documentation via [onHelpTap].
class QueryLanguageBadge extends StatelessWidget {
  final String language;
  final IconData icon;
  final Color color;
  final VoidCallback? onHelpTap;

  const QueryLanguageBadge({
    super.key,
    required this.language,
    this.icon = Icons.code_rounded,
    this.color = AppColors.primaryCyan,
    this.onHelpTap,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.12),
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: color.withValues(alpha: 0.25)),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 12, color: color),
              const SizedBox(width: 5),
              Text(
                language,
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 10,
                  fontWeight: FontWeight.w500,
                  color: color,
                ),
              ),
            ],
          ),
        ),
        if (onHelpTap != null)
          Padding(
            padding: const EdgeInsets.only(left: 4),
            child: InkWell(
              borderRadius: BorderRadius.circular(4),
              onTap: onHelpTap,
              child: Padding(
                padding: const EdgeInsets.all(2),
                child: Icon(
                  Icons.help_outline_rounded,
                  size: 14,
                  color: AppColors.textMuted.withValues(alpha: 0.7),
                ),
              ),
            ),
          ),
      ],
    );
  }
}
