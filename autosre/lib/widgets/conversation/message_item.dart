import 'package:flutter/material.dart';
import 'package:flutter_markdown_plus/flutter_markdown_plus.dart';
import 'package:genui/genui.dart';
import 'package:provider/provider.dart';

import '../../models/adk_schema.dart';
import '../../services/auth_service.dart';
import '../../theme/app_theme.dart';
import '../tool_log.dart';

/// Standalone Agent Avatar widget for reuse.
class AgentAvatar extends StatelessWidget {
  const AgentAvatar({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(right: 8),
      width: 32,
      height: 32,
      decoration: BoxDecoration(
        color: AppColors.secondaryPurple.withValues(alpha: 0.2),
        shape: BoxShape.circle,
        border: Border.all(
          color: AppColors.secondaryPurple.withValues(alpha: 0.3),
          width: 1,
        ),
      ),
      child: const Icon(
        Icons.smart_toy,
        size: 18,
        color: AppColors.secondaryPurple,
      ),
    );
  }
}

/// Animated message item widget that renders user, AI text, or AI UI messages.
class MessageItem extends StatefulWidget {
  final ChatMessage message;
  final GenUiHost host;
  final AnimationController animation;
  final ValueNotifier<Map<String, ToolLog>>? toolCallState;

  const MessageItem({
    super.key,
    required this.message,
    required this.host,
    required this.animation,
    this.toolCallState,
  });

  @override
  State<MessageItem> createState() => _MessageItemState();
}

class _MessageItemState extends State<MessageItem>
    with SingleTickerProviderStateMixin {
  late AnimationController _entryController;
  late Animation<double> _fadeAnimation;
  late Animation<Offset> _slideAnimation;

  @override
  void initState() {
    super.initState();
    _entryController = AnimationController(
      duration: const Duration(milliseconds: 400),
      vsync: this,
    );

    _fadeAnimation = CurvedAnimation(
      parent: _entryController,
      curve: Curves.easeOut,
    );

    _slideAnimation =
        Tween<Offset>(begin: const Offset(0, 0.015), end: Offset.zero).animate(
          CurvedAnimation(parent: _entryController, curve: Curves.easeOutCubic),
        );

    _entryController.forward();
  }

  @override
  void dispose() {
    _entryController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _fadeAnimation,
      child: SlideTransition(
        position: _slideAnimation,
        child: _buildMessageContent(context),
      ),
    );
  }

  Widget _buildMessageContent(BuildContext context) {
    final msg = widget.message;

    if (msg is UserMessage) {
      return _buildUserMessage(msg);
    } else if (msg is AiTextMessage) {
      return _buildAiTextMessage(msg);
    } else if (msg is AiUiMessage) {
      return _buildAiUiMessage(msg);
    }
    return const SizedBox.shrink();
  }

  Widget _buildUserMessage(UserMessage msg) {
    final isShort = !msg.text.contains('\n') && msg.text.length < 80;
    return Align(
      alignment: Alignment.centerRight,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.end,
        crossAxisAlignment: isShort
            ? CrossAxisAlignment.center
            : CrossAxisAlignment.start,
        children: [
          Flexible(
            child: Container(
              constraints: const BoxConstraints(maxWidth: 900),
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 12,
                ),
                decoration: BoxDecoration(
                  color: AppColors.primaryBlue.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: AppColors.primaryBlue.withValues(alpha: 0.3),
                    width: 1,
                  ),
                ),
                child: SelectionArea(
                  child: MarkdownBody(
                    data: msg.text,
                    styleSheet: MarkdownStyleSheet(
                      p: const TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        height: 1.4,
                      ),
                      code: TextStyle(
                        backgroundColor: Colors.black.withValues(alpha: 0.2),
                        color: Colors.white,
                        fontSize: 12,
                        fontFamily: AppTheme.codeStyle.fontFamily,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          // User Avatar
          Container(
            width: 32,
            height: 32,
            decoration: const BoxDecoration(
              shape: BoxShape.circle,
              color: AppColors.primaryTeal,
            ),
            clipBehavior: Clip.antiAlias,
            child: Consumer<AuthService>(
              builder: (context, auth, _) {
                final user = auth.currentUser;
                if (user?.photoUrl != null) {
                  return Image.network(user!.photoUrl!, fit: BoxFit.cover);
                }
                return Center(
                  child: Text(
                    (user?.displayName ?? 'U').substring(0, 1).toUpperCase(),
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAiTextMessage(AiTextMessage msg) {
    final isShort = !msg.text.contains('\n') && msg.text.length < 80;
    return Align(
      alignment: Alignment.centerLeft,
      child: Row(
        crossAxisAlignment: isShort
            ? CrossAxisAlignment.center
            : CrossAxisAlignment.start,
        children: [
          const AgentAvatar(),
          Flexible(
            child: Container(
              constraints: const BoxConstraints(maxWidth: 900),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.1),
                  width: 1,
                ),
              ),
              child: SelectionArea(
                child: MarkdownBody(
                  data: _sanitizeMarkdown(msg.text),
                  styleSheet: _aiMarkdownStyleSheet,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAiUiMessage(AiUiMessage msg) {
    // Check if this is an inline tool call
    final toolState = widget.toolCallState;
    if (toolState != null) {
      final toolLog = toolState.value[msg.surfaceId];
      if (toolLog != null) {
        return ValueListenableBuilder<Map<String, ToolLog>>(
          valueListenable: toolState,
          builder: (context, state, _) {
            final currentLog = state[msg.surfaceId];
            if (currentLog == null) return const SizedBox.shrink();
            return Align(
              alignment: Alignment.centerLeft,
              child: Padding(
                padding: const EdgeInsets.only(left: 44),
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 700),
                  child: ToolLogWidget(log: currentLog),
                ),
              ),
            );
          },
        );
      }
    }

    // Fallback: render via GenUI surface
    final host = widget.host;
    return Align(
      alignment: Alignment.centerLeft,
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const AgentAvatar(),
          Flexible(
            child: Container(
              constraints: const BoxConstraints(maxWidth: 950),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(10),
                child: GenUiSurface(host: host, surfaceId: msg.surfaceId),
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _sanitizeMarkdown(String text) {
    return text;
  }

  MarkdownStyleSheet get _aiMarkdownStyleSheet {
    return MarkdownStyleSheet(
      p: const TextStyle(
        color: AppColors.textPrimary,
        fontSize: 14,
        height: 1.6,
      ),
      pPadding: const EdgeInsets.only(bottom: 16),
      h1: const TextStyle(
        color: AppColors.primaryTeal,
        fontSize: 24,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.5,
      ),
      h1Padding: const EdgeInsets.only(top: 24, bottom: 12),
      h2: const TextStyle(
        color: AppColors.primaryCyan,
        fontSize: 20,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.3,
      ),
      h2Padding: const EdgeInsets.only(top: 20, bottom: 10),
      h3: const TextStyle(
        color: Colors.white,
        fontSize: 16,
        fontWeight: FontWeight.w600,
      ),
      h3Padding: const EdgeInsets.only(top: 12, bottom: 4),
      code: TextStyle(
        backgroundColor: const Color(0xFF0F172A),
        color: AppColors.primaryCyan,
        fontSize: 13,
        fontFamily: AppTheme.codeStyle.fontFamily,
        fontWeight: FontWeight.w500,
      ),
      codeblockDecoration: BoxDecoration(
        color: const Color(0xFF0F172A),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white.withValues(alpha: 0.1)),
      ),
      blockquoteDecoration: BoxDecoration(
        color: AppColors.primaryTeal.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border(
          left: BorderSide(
            color: AppColors.primaryTeal.withValues(alpha: 0.5),
            width: 3,
          ),
        ),
      ),
      blockquotePadding: const EdgeInsets.all(12),
      tableHead: const TextStyle(
        fontWeight: FontWeight.w700,
        color: Colors.white,
        fontSize: 12,
      ),
      tableBody: const TextStyle(color: AppColors.textSecondary, fontSize: 12),
      tableBorder: TableBorder.all(
        color: Colors.white.withValues(alpha: 0.1),
        width: 1,
        borderRadius: BorderRadius.circular(8),
      ),
      tableCellsPadding: const EdgeInsets.symmetric(
        horizontal: 12,
        vertical: 8,
      ),
      tableCellsDecoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.02),
      ),
      listBullet: const TextStyle(
        color: AppColors.primaryTeal,
        fontWeight: FontWeight.bold,
      ),
      listIndent: 20,
      listBulletPadding: const EdgeInsets.only(right: 8),
    );
  }
}
