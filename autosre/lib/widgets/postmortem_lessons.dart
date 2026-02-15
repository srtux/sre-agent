import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// Lessons learned section showing what went well and what went poorly.
class PostmortemLessons extends StatelessWidget {
  final List<String> whatWentWell;
  final List<String> whatWentPoorly;

  const PostmortemLessons({
    super.key,
    required this.whatWentWell,
    required this.whatWentPoorly,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          children: [
            Icon(
              Icons.school_rounded,
              size: 16,
              color: AppColors.secondaryPurple,
            ),
            SizedBox(width: 8),
            Text(
              'Lessons Learned',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),

        // What went well
        if (whatWentWell.isNotEmpty)
          _LessonsList(
            title: 'What Went Well',
            items: whatWentWell,
            icon: Icons.thumb_up_alt_rounded,
            color: AppColors.success,
          ),
        if (whatWentWell.isNotEmpty && whatWentPoorly.isNotEmpty)
          const SizedBox(height: 10),

        // What went poorly
        if (whatWentPoorly.isNotEmpty)
          _LessonsList(
            title: 'What Went Poorly',
            items: whatWentPoorly,
            icon: Icons.thumb_down_alt_rounded,
            color: AppColors.error,
          ),
      ],
    );
  }
}

class _LessonsList extends StatelessWidget {
  final String title;
  final List<String> items;
  final IconData icon;
  final Color color;

  const _LessonsList({
    required this.title,
    required this.items,
    required this.icon,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: GlassDecoration.card(
        borderRadius: 10,
        borderColor: color.withValues(alpha: 0.2),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 14, color: color),
              const SizedBox(width: 6),
              Text(
                title,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: color,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ...items.map((item) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Container(
                      width: 4,
                      height: 4,
                      decoration: BoxDecoration(
                        color: color.withValues(alpha: 0.6),
                        shape: BoxShape.circle,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      item,
                      style: const TextStyle(
                        fontSize: 12,
                        color: AppColors.textSecondary,
                        height: 1.5,
                      ),
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
      ),
    );
  }
}
