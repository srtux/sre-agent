import 'package:flutter/material.dart';

import '../../theme/app_theme.dart';
import '../../widgets/glow_action_chip.dart';
import '../../widgets/unified_prompt_input.dart';

/// The bottom input area with suggested action chips and the unified prompt input.
class ChatInputArea extends StatelessWidget {
  final bool isProcessing;
  final GlobalKey inputKey;
  final TextEditingController textController;
  final FocusNode focusNode;
  final VoidCallback onSend;
  final VoidCallback onCancel;
  final ValueNotifier<List<String>> suggestedActions;

  const ChatInputArea({
    super.key,
    required this.isProcessing,
    required this.inputKey,
    required this.textController,
    required this.focusNode,
    required this.onSend,
    required this.onCancel,
    required this.suggestedActions,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
      decoration: const BoxDecoration(
        color: Colors.transparent,
      ),
      child: SafeArea(
        top: false,
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 900),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Suggested Actions
                _buildSuggestedActions(),
                const SizedBox(height: 12),
                // Unified Input Container
                UnifiedPromptInput(
                  key: inputKey,
                  controller: textController,
                  focusNode: focusNode,
                  isProcessing: isProcessing,
                  onSend: onSend,
                  onCancel: onCancel,
                ),
                // Compact keyboard hint
                Align(
                  alignment: Alignment.centerLeft,
                  child: Padding(
                    padding: const EdgeInsets.only(top: 8, left: 16),
                    child: Text(
                      'Enter to send \u2022 Shift+Enter for new line',
                      style: TextStyle(
                        fontSize: 11,
                        color:
                            AppColors.textMuted.withValues(alpha: 0.6),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildSuggestedActions() {
    return ValueListenableBuilder<List<String>>(
      valueListenable: suggestedActions,
      builder: (context, suggestions, _) {
        if (suggestions.isEmpty) return const SizedBox.shrink();

        return Padding(
          padding: const EdgeInsets.only(bottom: 4),
          child: SizedBox(
            height: 34,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              physics: const BouncingScrollPhysics(),
              itemCount: suggestions.length,
              separatorBuilder: (context, index) =>
                  const SizedBox(width: 10),
              padding: const EdgeInsets.symmetric(horizontal: 4),
              itemBuilder: (context, index) {
                final action = suggestions[index];
                return GlowActionChip(
                  label: action,
                  icon: Icons.bolt_rounded,
                  compact: true,
                  onTap: () {
                    textController.text = action;
                    onSend();
                  },
                );
              },
            ),
          ),
        );
      },
    );
  }
}
