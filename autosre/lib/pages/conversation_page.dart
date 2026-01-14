import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:genui/genui.dart';

import '../agent/adk_content_generator.dart';
import '../catalog.dart';


class ConversationPage extends StatefulWidget {
  const ConversationPage({super.key});

  @override
  State<ConversationPage> createState() => _ConversationPageState();
}

class _ConversationPageState extends State<ConversationPage> {
  late final A2uiMessageProcessor _messageProcessor;
  late final GenUiConversation _conversation;
  late final ADKContentGenerator _contentGenerator;
  final TextEditingController _textController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();

    final sreCatalog = CatalogRegistry.createSreCatalog();

    _messageProcessor = A2uiMessageProcessor(
      catalogs: [
        sreCatalog,
        CoreCatalogItems.asCatalog(),
      ],
    );

    _contentGenerator = ADKContentGenerator();

    _conversation = GenUiConversation(
      a2uiMessageProcessor: _messageProcessor,
      contentGenerator: _contentGenerator,
      onSurfaceAdded: (update) => _scrollToBottom(),
      onSurfaceUpdated: (update) {},
      onTextResponse: (text) => _scrollToBottom(),
    );
  }

  void _scrollToBottom() {
    Future.delayed(const Duration(milliseconds: 100), () {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _sendMessage() {
    if (_textController.text.trim().isEmpty) return;
    final text = _textController.text;
    _textController.clear();

    _conversation.sendRequest(UserMessage.text(text));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("AutoSRE"), backgroundColor: Colors.black26),
      body: Column(
        children: [
          Expanded(
            child: ValueListenableBuilder<List<ChatMessage>>(
              valueListenable: _conversation.conversation,
              builder: (context, messages, _) {
                return ListView.builder(
                  controller: _scrollController,
                  padding: const EdgeInsets.all(16),
                  itemCount: messages.length,
                  itemBuilder: (context, index) {
                    final msg = messages[index];
                    return _buildMessageItem(msg);
                  },
                );
              },
            ),
          ),
          _buildInputArea(),
        ],
      ),
    );
  }

  Widget _buildMessageItem(ChatMessage msg) {
    if (msg is UserMessage) {
      return Align(
        alignment: Alignment.centerRight,
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 4),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.teal.withValues(alpha: 0.2),
            borderRadius: BorderRadius.circular(12),
          ),
          child: MarkdownBody(
            data: msg.text,
            styleSheet: MarkdownStyleSheet(
              p: const TextStyle(color: Colors.white),
            ),
          ),
        ),
      );
    } else if (msg is AiTextMessage) {
      return Align(
        alignment: Alignment.centerLeft,
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 4),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white10,
            borderRadius: BorderRadius.circular(12),
          ),
          child: MarkdownBody(
            data: msg.text,
            styleSheet: MarkdownStyleSheet(
              p: const TextStyle(color: Colors.white),
            ),
          ),
        ),
      );
    } else if (msg is AiUiMessage) {
      return Align(
        alignment: Alignment.centerLeft,
        child: GenUiSurface(
          host: _conversation.host,
          surfaceId: msg.surfaceId,
        ),
      );
    }
    return const SizedBox();
  }

  Widget _buildInputArea() {
    return Container(
      padding: const EdgeInsets.all(16),
      color: Colors.black12,
      child: Row(
        children: [
          Expanded(
            child: TextField(
              controller: _textController,
              onSubmitted: (_) => _sendMessage(),
              decoration: InputDecoration(
                hintText: "Ask AutoSRE...",
                filled: true,
                fillColor: Colors.white.withValues(alpha: 0.05),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(24),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
          ),
          const SizedBox(width: 8),
          IconButton.filled(
            onPressed: _sendMessage,
            icon: const Icon(Icons.arrow_upward),
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _conversation.dispose();
    super.dispose();
  }
}
