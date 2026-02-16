import 'package:flutter/material.dart';

import '../../theme/app_theme.dart';

/// Compact error banner used inside dashboard panels to display query errors.
class ErrorBanner extends StatelessWidget {
  final String message;
  final VoidCallback? onDismiss;

  const ErrorBanner({super.key, required this.message, this.onDismiss});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: AppColors.error.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: AppColors.error.withValues(alpha: 0.3)),
        ),
        child: Row(
          children: [
            Expanded(
              child: Text(
                message,
                style: const TextStyle(fontSize: 11, color: AppColors.error),
              ),
            ),
            if (onDismiss != null)
              IconButton(
                icon: const Icon(Icons.close_rounded, size: 14),
                color: AppColors.error.withValues(alpha: 0.6),
                padding: EdgeInsets.zero,
                constraints: const BoxConstraints(),
                onPressed: onDismiss,
                tooltip: 'Dismiss Error',
              ),
          ],
        ),
      ),
    );
  }
}
