import 'package:flutter/material.dart';

import '../../theme/app_theme.dart';
import '../../theme/design_tokens.dart' as tokens;

/// Wraps the chat UI to provide maximize and close controls.
class ChatPanelWrapper extends StatelessWidget {
  final Widget child;
  final bool isMaximized;
  final VoidCallback onToggleMaximize;
  final VoidCallback onClose;
  final VoidCallback onStartNewSession;

  const ChatPanelWrapper({
    super.key,
    required this.child,
    required this.isMaximized,
    required this.onToggleMaximize,
    required this.onClose,
    required this.onStartNewSession,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.backgroundDark,
        border: Border(
          left: BorderSide(
            color: AppColors.surfaceBorder.withValues(alpha: 0.8),
            width: 1,
          ),
        ),
      ),
      child: Column(
        children: [
          // Toolbar
          Container(
            height: 48,
            padding: const EdgeInsets.symmetric(horizontal: tokens.Spacing.sm),
            decoration: BoxDecoration(
              border: Border(
                bottom: BorderSide(
                  color: AppColors.surfaceBorder.withValues(alpha: 0.5),
                  width: 1,
                ),
              ),
            ),
            child: Row(
              children: [
                const Icon(
                  Icons.chat_bubble_outline,
                  size: 16,
                  color: AppColors.textMuted,
                ),
                const SizedBox(width: tokens.Spacing.sm),
                const Text(
                  'Conversation',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: AppColors.textSecondary,
                  ),
                ),
                const Spacer(),
                Builder(
                  builder: (context) {
                    return Tooltip(
                      message: 'History & Sessions',
                      child: IconButton(
                        icon: const Icon(Icons.history, size: 16),
                        onPressed: () {
                          Scaffold.of(context).openEndDrawer();
                        },
                        color: AppColors.textMuted,
                        splashRadius: 16,
                      ),
                    );
                  },
                ),
                const SizedBox(width: tokens.Spacing.xs),
                Tooltip(
                  message: 'New Investigation',
                  child: IconButton(
                    icon: const Icon(Icons.add_comment_outlined, size: 16),
                    onPressed: onStartNewSession,
                    color: AppColors.textMuted,
                    splashRadius: 16,
                  ),
                ),
                const SizedBox(width: tokens.Spacing.xs),
                Tooltip(
                  message: isMaximized ? 'Restore down' : 'Maximize',
                  child: IconButton(
                    icon: Icon(
                      isMaximized ? Icons.close_fullscreen : Icons.open_in_full,
                      size: 14,
                    ),
                    onPressed: onToggleMaximize,
                    color: AppColors.textMuted,
                    splashRadius: 16,
                  ),
                ),
                const SizedBox(width: tokens.Spacing.xs),
                Tooltip(
                  message: 'Close Chat',
                  child: IconButton(
                    icon: const Icon(Icons.close, size: 16),
                    onPressed: onClose,
                    color: AppColors.textMuted,
                    splashRadius: 16,
                  ),
                ),
              ],
            ),
          ),
          // Content
          Expanded(child: child),
        ],
      ),
    );
  }
}
