import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import 'postmortem_data.dart';

/// Checklist of postmortem action items with progress tracking.
class PostmortemActionItems extends StatefulWidget {
  final List<PostmortemActionItem> items;
  final Animation<double> animation;

  const PostmortemActionItems({
    super.key,
    required this.items,
    required this.animation,
  });

  @override
  State<PostmortemActionItems> createState() => _PostmortemActionItemsState();
}

class _PostmortemActionItemsState extends State<PostmortemActionItems> {
  final Set<int> _checkedActions = {};

  @override
  void initState() {
    super.initState();
    for (var i = 0; i < widget.items.length; i++) {
      if (widget.items[i].completed) {
        _checkedActions.add(i);
      }
    }
  }

  Color _priorityColor(ActionPriority priority) {
    switch (priority) {
      case ActionPriority.p0:
        return AppColors.error;
      case ActionPriority.p1:
        return AppColors.warning;
      case ActionPriority.p2:
        return AppColors.info;
    }
  }

  String _priorityLabel(ActionPriority priority) {
    switch (priority) {
      case ActionPriority.p0:
        return 'P0';
      case ActionPriority.p1:
        return 'P1';
      case ActionPriority.p2:
        return 'P2';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          children: [
            Icon(
              Icons.checklist_rounded,
              size: 16,
              color: AppColors.primaryTeal,
            ),
            SizedBox(width: 8),
            Text(
              'Action Items',
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: AppColors.textPrimary,
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        ...List.generate(widget.items.length, (index) {
          final item = widget.items[index];
          final isChecked = _checkedActions.contains(index);
          final pColor = _priorityColor(item.priority);
          final pLabel = _priorityLabel(item.priority);

          final staggerDelay = index / widget.items.length;
          final animValue =
              ((widget.animation.value - staggerDelay * 0.3) / 0.7).clamp(
                0.0,
                1.0,
              );

          return AnimatedOpacity(
            duration: const Duration(milliseconds: 200),
            opacity: animValue,
            child: AnimatedSlide(
              duration: const Duration(milliseconds: 300),
              offset: Offset(0, (1 - animValue) * 0.1),
              child: Container(
                margin: const EdgeInsets.only(bottom: 8),
                decoration: GlassDecoration.card(
                  borderRadius: 10,
                  borderColor: isChecked
                      ? AppColors.success.withValues(alpha: 0.3)
                      : null,
                ),
                child: InkWell(
                  onTap: () {
                    setState(() {
                      if (_checkedActions.contains(index)) {
                        _checkedActions.remove(index);
                      } else {
                        _checkedActions.add(index);
                      }
                    });
                  },
                  borderRadius: BorderRadius.circular(10),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Row(
                      children: [
                        // Checkbox
                        AnimatedContainer(
                          duration: const Duration(milliseconds: 200),
                          width: 22,
                          height: 22,
                          decoration: BoxDecoration(
                            gradient: isChecked
                                ? LinearGradient(
                                    colors: [
                                      AppColors.success,
                                      AppColors.success.withValues(alpha: 0.8),
                                    ],
                                  )
                                : null,
                            color: isChecked
                                ? null
                                : Colors.white.withValues(alpha: 0.1),
                            borderRadius: BorderRadius.circular(6),
                            border: Border.all(
                              color: isChecked
                                  ? AppColors.success
                                  : AppColors.surfaceBorder,
                            ),
                          ),
                          child: isChecked
                              ? const Icon(
                                  Icons.check,
                                  size: 14,
                                  color: Colors.white,
                                )
                              : null,
                        ),
                        const SizedBox(width: 10),

                        // Priority badge
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 6,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: pColor.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(
                              color: pColor.withValues(alpha: 0.3),
                            ),
                          ),
                          child: Text(
                            pLabel,
                            style: TextStyle(
                              fontSize: 10,
                              fontWeight: FontWeight.w700,
                              color: pColor,
                              letterSpacing: 0.5,
                            ),
                          ),
                        ),
                        const SizedBox(width: 10),

                        // Description
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                item.description,
                                style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w500,
                                  color: isChecked
                                      ? AppColors.textMuted
                                      : AppColors.textPrimary,
                                  decoration: isChecked
                                      ? TextDecoration.lineThrough
                                      : null,
                                ),
                              ),
                              if (item.owner != null) ...[
                                const SizedBox(height: 2),
                                Text(
                                  'Owner: ${item.owner}',
                                  style: const TextStyle(
                                    fontSize: 11,
                                    color: AppColors.textMuted,
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          );
        }),
      ],
    );
  }
}
