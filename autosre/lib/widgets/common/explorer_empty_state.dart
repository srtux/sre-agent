import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../theme/app_theme.dart';

/// Empty state widget with a "Run Query" prompt for explorer panels.
///
/// Displays a centered layout with a large icon, title, description, an optional
/// monospace query hint in a code block, and an action button with a gradient.
/// Uses glass morphism card styling consistent with the Deep Space aesthetic.
class ExplorerEmptyState extends StatelessWidget {
  /// Large icon displayed at the top of the empty state.
  final IconData icon;

  /// Title text, e.g. "Metrics Explorer".
  final String title;

  /// Descriptive explanation text.
  final String description;

  /// Optional example query shown in a monospace code block.
  final String? queryHint;

  /// Callback for the "Run Query" button. If null, the button is hidden.
  final VoidCallback? onRunQuery;

  const ExplorerEmptyState({
    super.key,
    required this.icon,
    required this.title,
    required this.description,
    this.queryHint,
    this.onRunQuery,
  });

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Container(
        constraints: const BoxConstraints(maxWidth: 420),
        margin: const EdgeInsets.all(24),
        decoration: GlassDecoration.card(borderRadius: 16, opacity: 0.06),
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 36),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Icon
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.primaryCyan.withValues(alpha: 0.08),
                shape: BoxShape.circle,
              ),
              child: Icon(
                icon,
                size: 48,
                color: AppColors.primaryCyan.withValues(alpha: 0.7),
              ),
            ),
            const SizedBox(height: 20),
            // Title
            Text(
              title,
              style: GoogleFonts.inter(
                fontSize: 18,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
                letterSpacing: -0.3,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            // Description
            Text(
              description,
              style: const TextStyle(
                fontSize: 13,
                color: AppColors.textSecondary,
                height: 1.5,
              ),
              textAlign: TextAlign.center,
            ),
            // Query hint code block
            if (queryHint != null) ...[
              const SizedBox(height: 16),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 10,
                ),
                decoration: BoxDecoration(
                  color: AppColors.backgroundDark.withValues(alpha: 0.6),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(
                    color: AppColors.surfaceBorder.withValues(alpha: 0.4),
                  ),
                ),
                child: Text(
                  queryHint!,
                  style: GoogleFonts.jetBrainsMono(
                    fontSize: 11,
                    color: AppColors.primaryCyan.withValues(alpha: 0.8),
                    height: 1.5,
                  ),
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
            // Run Query button
            if (onRunQuery != null) ...[
              const SizedBox(height: 24),
              _buildRunQueryButton(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildRunQueryButton() {
    return Semantics(
      button: true,
      label: 'Run query',
      child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [AppColors.primaryTeal, AppColors.primaryCyan],
            begin: Alignment.centerLeft,
            end: Alignment.centerRight,
          ),
          borderRadius: BorderRadius.circular(10),
          boxShadow: [
            BoxShadow(
              color: AppColors.primaryCyan.withValues(alpha: 0.2),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: onRunQuery,
            borderRadius: BorderRadius.circular(10),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 12),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    Icons.play_arrow_rounded,
                    size: 18,
                    color: Colors.white,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'Run Query',
                    style: GoogleFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: Colors.white,
                      letterSpacing: 0.3,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
