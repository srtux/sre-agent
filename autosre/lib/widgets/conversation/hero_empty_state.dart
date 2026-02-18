import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../services/auth_service.dart';
import '../../theme/app_theme.dart';
import '../../widgets/glow_action_chip.dart';
import '../../widgets/tech_grid_painter.dart';
import '../../widgets/unified_prompt_input.dart';

/// The hero/empty state shown when no messages exist in the conversation.
///
/// Displays a personalized greeting, the main prompt input, and
/// suggested action chips.
class HeroEmptyState extends StatelessWidget {
  final bool isProcessing;
  final GlobalKey inputKey;
  final TextEditingController textController;
  final FocusNode focusNode;
  final VoidCallback onSend;
  final VoidCallback onCancel;
  final ValueNotifier<List<String>> suggestedActions;

  const HeroEmptyState({
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
    final authService = Provider.of<AuthService>(context, listen: false);
    final user = authService.currentUser;
    var name = 'there';
    if (user?.displayName != null && user!.displayName!.isNotEmpty) {
      name = user.displayName!.split(' ').first;
    }

    return Stack(
      children: [
        const Positioned.fill(child: RepaintBoundary(child: CustomPaint(painter: TechGridPainter()))),
        Center(
          child: SingleChildScrollView(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20),
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 1000),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    // Greeting
                    ShaderMask(
                      shaderCallback: (bounds) => const LinearGradient(
                        colors: [
                          AppColors.primaryBlue,
                          AppColors.secondaryPurple,
                        ],
                      ).createShader(bounds),
                      child: Text(
                        'Hi $name',
                        style: const TextStyle(
                          fontSize: 48,
                          fontWeight: FontWeight.w600,
                          color: Colors.white,
                        ),
                      ),
                    ),
                    const SizedBox(height: 12),
                    const Text(
                      'Where should we start debugging?',
                      style: TextStyle(
                        fontSize: 24,
                        color: AppColors.textSecondary,
                        fontWeight: FontWeight.w400,
                      ),
                      textAlign: TextAlign.center,
                    ),
                    const SizedBox(height: 48),

                    // Hero Input Field
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 700),
                      child: UnifiedPromptInput(
                        key: inputKey,
                        controller: textController,
                        focusNode: focusNode,
                        isProcessing: isProcessing,
                        onSend: onSend,
                        onCancel: onCancel,
                      ),
                    ),

                    const SizedBox(height: 32),

                    // Action Chips
                    ValueListenableBuilder<List<String>>(
                      valueListenable: suggestedActions,
                      builder: (context, suggestions, _) {
                        if (suggestions.isEmpty) {
                          return const SizedBox.shrink();
                        }

                        final displaySuggestions = suggestions.take(4).toList();

                        return SingleChildScrollView(
                          scrollDirection: Axis.horizontal,
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: displaySuggestions.asMap().entries.map((
                              entry,
                            ) {
                              final index = entry.key;
                              final suggestion = entry.value;
                              return Padding(
                                padding: EdgeInsets.only(
                                  right: index < displaySuggestions.length - 1
                                      ? 12
                                      : 0,
                                ),
                                child: GlowActionChip(
                                  label: suggestion,
                                  icon: Icons.bolt_rounded,
                                  onTap: () {
                                    textController.text = suggestion;
                                    onSend();
                                  },
                                ),
                              );
                            }).toList(),
                          ),
                        );
                      },
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}
