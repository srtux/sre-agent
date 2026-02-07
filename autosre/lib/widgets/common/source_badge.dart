import 'package:flutter/material.dart';

import '../../services/dashboard_state.dart';
import '../../theme/app_theme.dart';

/// Badge that shows "MANUAL" for manually-queried dashboard items.
///
/// Renders as an empty [SizedBox] for agent-sourced items.
class SourceBadge extends StatelessWidget {
  final DataSource source;

  const SourceBadge({super.key, required this.source});

  @override
  Widget build(BuildContext context) {
    if (source == DataSource.agent) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
      decoration: BoxDecoration(
        color: AppColors.primaryCyan.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(4),
      ),
      child: const Text(
        'MANUAL',
        style: TextStyle(
          fontSize: 8,
          fontWeight: FontWeight.w600,
          color: AppColors.primaryCyan,
        ),
      ),
    );
  }
}
