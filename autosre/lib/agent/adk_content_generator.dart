
import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:genui/genui.dart';
import 'package:http/http.dart' as http;



/// A ContentGenerator that connects to the Python SRE Agent.
class ADKContentGenerator implements ContentGenerator {
  final StreamController<A2uiMessage> _a2uiController = StreamController<A2uiMessage>.broadcast();
  final StreamController<String> _textController = StreamController<String>.broadcast();
  final StreamController<ContentGeneratorError> _errorController = StreamController<ContentGeneratorError>.broadcast();
  final ValueNotifier<bool> _isProcessing = ValueNotifier(false);
  final String _baseUrl = 'http://localhost:8001/api/genui/chat';

  @override
  Stream<A2uiMessage> get a2uiMessageStream => _a2uiController.stream;

  @override
  Stream<String> get textResponseStream => _textController.stream;

  @override
  Stream<ContentGeneratorError> get errorStream => _errorController.stream;

  @override
  ValueListenable<bool> get isProcessing => _isProcessing;

  @override
  Future<void> sendRequest(
    ChatMessage message, {
    Iterable<ChatMessage>? history,
    A2UiClientCapabilities? clientCapabilities,
  }) async {
    if (message is! UserMessage) return;

    _isProcessing.value = true;

    try {
        final request = http.Request('POST', Uri.parse(_baseUrl));
        request.headers['Content-Type'] = 'application/json';
        request.body = jsonEncode({
            "messages": [
                {"role": "user", "text": message.text}
            ]
        });

        final response = await request.send();

        if (response.statusCode != 200) {
            throw Exception('Failed to connect to agent: ${response.statusCode}');
        }

        // Parse stream line by line
        await response.stream
            .transform(utf8.decoder)
            .transform(const LineSplitter())
            .listen((line) {
                if (line.trim().isEmpty) return;
                try {
                    final data = jsonDecode(line);
                    final type = data['type'];

                    if (type == 'text') {
                        _textController.add(data['content']);
                    } else if (type == 'a2ui') {
                        final msgJson = data['message'] as Map<String, dynamic>;
                        final msg = A2uiMessage.fromJson(msgJson);
                        _a2uiController.add(msg);
                    }
                } catch (e) {
                    debugPrint("Error parsing line: $e");
                }
            }).asFuture();

    } catch (e, st) {
        _errorController.add(ContentGeneratorError(e, st));
    } finally {
        _isProcessing.value = false;
    }
  }

  @override
  void dispose() {
    _a2uiController.close();
    _textController.close();
    _errorController.close();
    _isProcessing.dispose();
  }
}
