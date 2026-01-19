import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../theme/app_theme.dart';

class UnifiedPromptInput extends StatelessWidget {
  final TextEditingController controller;
  final FocusNode focusNode;
  final VoidCallback onSend;
  final VoidCallback onCancel;
  final bool isProcessing;

  const UnifiedPromptInput({
    super.key,
    required this.controller,
    required this.focusNode,
    required this.onSend,
    required this.onCancel,
    required this.isProcessing,
  });

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 600),
      curve: Curves.easeInOut,
      height: 60,
      decoration: BoxDecoration(
        color: const Color(0xFF0F172A), // Dark Navy/Black
        borderRadius: BorderRadius.circular(50), // Full rounded pill
        border: Border.all(
          color: isProcessing
              ? AppColors.secondaryPurple.withValues(alpha: 0.6)
              : Colors.white.withValues(alpha: 0.15),
          width: isProcessing ? 1.5 : 1,
        ),
        boxShadow: [
          // Deep shadow for "floating" lift
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.5),
            blurRadius: 24,
            offset: const Offset(0, 8),
          ),
          // Processing Glow or Ambient Light
          if (isProcessing)
            BoxShadow(
              color: AppColors.secondaryPurple.withValues(alpha: 0.2),
              blurRadius: 16,
              spreadRadius: 2,
            ),
        ],
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          // Magic Icon
          Padding(
            padding: const EdgeInsets.only(left: 20, right: 12),
            child: Icon(
              Icons.auto_awesome,
              color: AppColors.primaryTeal,
              size: 22,
            ),
          ),
          // Text Field
          Expanded(
            child: TextField(
              controller: controller,
              focusNode: focusNode,
              onSubmitted: (_) {
                if (!HardwareKeyboard.instance.isShiftPressed) {
                  onSend();
                }
              },
              maxLines: 1, // Fixed height implies single line or restricted
              minLines: 1,
              style: const TextStyle(
                color: Colors.white, // Bright White
                fontSize: 16,
                height: 1.5,
              ),
              cursorColor: AppColors.primaryTeal,
              decoration: InputDecoration(
                hintText: "Ask anything...",
                hintStyle: TextStyle(
                  color: AppColors.textMuted.withValues(alpha: 0.7),
                  fontSize: 16,
                ),
                filled: false,
                isDense: true,
                border: InputBorder.none,
                enabledBorder: InputBorder.none,
                focusedBorder: InputBorder.none,
                errorBorder: InputBorder.none,
                disabledBorder: InputBorder.none,
                contentPadding: EdgeInsets.zero,
              ),
            ),
          ),
          // Send/Stop Button
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: _UnifiedSendButton(
              isProcessing: isProcessing,
              onPressed: onSend,
              onCancel: onCancel,
            ),
          ),
        ],
      ),
    );
  }
}

class _UnifiedSendButton extends StatelessWidget {
  final bool isProcessing;
  final VoidCallback onPressed;
  final VoidCallback onCancel;

  const _UnifiedSendButton({
    required this.isProcessing,
    required this.onPressed,
    required this.onCancel,
  });

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: isProcessing ? 'Stop' : 'Send',
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: isProcessing ? onCancel : onPressed,
          borderRadius: BorderRadius.circular(20),
          child: Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: isProcessing
                  ? AppColors.error
                  : AppColors.primaryTeal,
              shape: BoxShape.circle,
            ),
            child: Icon(
              isProcessing ? Icons.stop_rounded : Icons.arrow_upward_rounded,
              color: isProcessing ? Colors.white : AppColors.backgroundDark,
              size: 20,
            ),
          ),
        ),
      ),
    );
  }
}
