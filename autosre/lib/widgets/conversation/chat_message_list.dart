import 'package:flutter/material.dart';
import 'package:genui/genui.dart';

import '../../models/adk_schema.dart';
import '../../theme/app_theme.dart';
import '../tech_grid_painter.dart';
import 'message_item.dart';

/// Displays the scrollable list of chat messages with a typing indicator.
class ChatMessageList extends StatelessWidget {
  final List<ChatMessage> messages;
  final bool isProcessing;
  final ScrollController scrollController;
  final GenUiConversation conversation;
  final AnimationController typingAnimation;
  final ValueNotifier<Map<String, ToolLog>> toolCallState;

  const ChatMessageList({
    super.key,
    required this.messages,
    required this.isProcessing,
    required this.scrollController,
    required this.conversation,
    required this.typingAnimation,
    required this.toolCallState,
  });

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        // 1. Tech Grid Background
        const Positioned.fill(child: CustomPaint(painter: TechGridPainter())),
        // Gradient Overlay for Fade Effect
        const Positioned.fill(
          child: DecoratedBox(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                stops: [0.5, 1.0],
                colors: [Colors.transparent, AppColors.backgroundDark],
              ),
            ),
          ),
        ),

        // 2. Centered Chat Stream
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 900),
            child: ListView.builder(
              controller: scrollController,
              padding: const EdgeInsets.fromLTRB(8, 12, 8, 12),
              itemCount: messages.length + 1, // +1 for typing indicator
              itemBuilder: (context, index) {
                if (index == messages.length) {
                  if (!isProcessing) return const SizedBox.shrink();
                  return _TypingIndicator(animation: typingAnimation);
                }
                final msg = messages[index];

                // Determine vertical spacing
                var topSpacing = 4.0;
                if (index > 0) {
                  final prevMsg = messages[index - 1];
                  final isSameSender =
                      (msg is UserMessage && prevMsg is UserMessage) ||
                      ((msg is AiTextMessage || msg is AiUiMessage) &&
                          (prevMsg is AiTextMessage || prevMsg is AiUiMessage));
                  if (!isSameSender) {
                    topSpacing = 24.0;
                  }
                } else {
                  topSpacing = 16.0;
                }

                return Padding(
                  padding: EdgeInsets.only(top: topSpacing),
                  child: MessageItem(
                    message: msg,
                    host: conversation.host,
                    animation: typingAnimation,
                    toolCallState: toolCallState,
                  ),
                );
              },
            ),
          ),
        ),
      ],
    );
  }
}

/// Animated typing indicator showing bouncing dots.
class _TypingIndicator extends StatelessWidget {
  final AnimationController animation;

  const _TypingIndicator({required this.animation});

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            const AgentAvatar(),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: AppColors.secondaryPurple.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: AppColors.secondaryPurple.withValues(alpha: 0.1),
                  width: 1,
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: List.generate(3, (index) {
                  return AnimatedBuilder(
                    animation: animation,
                    builder: (context, child) {
                      final delay = index * 0.2;
                      final animValue = ((animation.value + delay) % 1.0 * 2.0)
                          .clamp(0.0, 1.0);
                      final bounce =
                          (animValue < 0.5
                              ? animValue * 2
                              : 2 - animValue * 2) *
                          0.4;

                      return Container(
                        margin: EdgeInsets.only(right: index < 2 ? 4 : 0),
                        child: Transform.translate(
                          offset: Offset(0, -bounce * 4),
                          child: Container(
                            width: 6,
                            height: 6,
                            decoration: BoxDecoration(
                              color: AppColors.secondaryPurple.withValues(
                                alpha: 0.4 + bounce,
                              ),
                              shape: BoxShape.circle,
                            ),
                          ),
                        ),
                      );
                    },
                  );
                }),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
