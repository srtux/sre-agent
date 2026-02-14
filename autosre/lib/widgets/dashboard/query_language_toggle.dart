import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../theme/app_theme.dart';

/// A compact toggle that switches between two or more query languages.
///
/// Used by the metrics panel to toggle between ListTimeSeries filter and PromQL.
class QueryLanguageToggle extends StatelessWidget {
  final List<String> languages;
  final int selectedIndex;
  final ValueChanged<int> onChanged;
  final Color activeColor;

  const QueryLanguageToggle({
    super.key,
    required this.languages,
    required this.selectedIndex,
    required this.onChanged,
    this.activeColor = AppColors.warning,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(2),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: AppColors.surfaceBorder.withValues(alpha: 0.3),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: List.generate(languages.length, (index) {
          final isActive = index == selectedIndex;
          return GestureDetector(
            onTap: () => onChanged(index),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: isActive
                    ? activeColor.withValues(alpha: 0.15)
                    : Colors.transparent,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(
                  color: isActive
                      ? activeColor.withValues(alpha: 0.3)
                      : Colors.transparent,
                ),
              ),
              child: Text(
                languages[index],
                style: GoogleFonts.jetBrainsMono(
                  fontSize: 10,
                  fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
                  color: isActive ? activeColor : AppColors.textMuted,
                ),
              ),
            ),
          );
        }),
      ),
    );
  }
}
