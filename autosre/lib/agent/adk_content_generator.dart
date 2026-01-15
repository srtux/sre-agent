
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
  bool _isDisposed = false;

  /// Number of retry attempts for failed requests.
  static const int _maxRetries = 2;

  /// Delay between retries (exponential backoff base).
  static const Duration _retryDelay = Duration(seconds: 1);
  String get _baseUrl {
    if (kDebugMode) {
      return 'http://localhost:8001/api/genui/chat';
    }
    return '/api/genui/chat';
  }

  final ValueNotifier<bool> _isConnected = ValueNotifier(false);
  Timer? _healthCheckTimer;

  String get _healthUrl {
    if (kDebugMode) {
      return 'http://localhost:8001/openapi.json';
    }
    return '/openapi.json';
  }

  /// Currently selected project ID to include in requests.
  String? projectId;

  ADKContentGenerator({this.projectId}) {
    _startHealthCheck();
  }

  void _startHealthCheck() {
    // Initial check
    _checkConnection();
    // Periodic check every 10 seconds
    _healthCheckTimer = Timer.periodic(const Duration(seconds: 10), (_) {
      _checkConnection();
    });
  }

  Future<void> _checkConnection() async {
    if (_isDisposed) return;
    try {
      await http.get(Uri.parse(_healthUrl));
      if (_isDisposed) return;
      // Any response from the server means we are connected
      _isConnected.value = true;
    } catch (e) {
      if (!_isDisposed) {
        _isConnected.value = false;
      }
    }
  }

  @override
  Stream<A2uiMessage> get a2uiMessageStream => _a2uiController.stream;

  @override
  Stream<String> get textResponseStream => _textController.stream;

  @override
  Stream<ContentGeneratorError> get errorStream => _errorController.stream;

  @override
  ValueListenable<bool> get isProcessing => _isProcessing;

  ValueListenable<bool> get isConnected => _isConnected; // Expose connection status

  @override
  Future<void> sendRequest(
    ChatMessage message, {
    Iterable<ChatMessage>? history,
    A2UiClientCapabilities? clientCapabilities,
  }) async {
    if (message is! UserMessage) return;

    _isProcessing.value = true;

    Exception? lastError;
    StackTrace? lastStackTrace;

    for (int attempt = 0; attempt <= _maxRetries; attempt++) {
      if (_isDisposed) break;

      try {
          // Retry delay with exponential backoff
          if (attempt > 0) {
            final delay = _retryDelay * (1 << (attempt - 1));
            debugPrint("Retrying request (attempt ${attempt + 1}/${_maxRetries + 1}) after ${delay.inSeconds}s...");
            await Future.delayed(delay);
          }

          final request = http.Request('POST', Uri.parse(_baseUrl));
          request.headers['Content-Type'] = 'application/json';

          final requestBody = <String, dynamic>{
              "messages": [
                  {"role": "user", "text": message.text}
              ]
          };

          // Include project_id if set
          if (projectId != null && projectId!.isNotEmpty) {
              requestBody["project_id"] = projectId;
          }

          request.body = jsonEncode(requestBody);

          final response = await request.send();

          if (response.statusCode != 200) {
              throw Exception('Failed to connect to agent: ${response.statusCode}');
          }

          _isConnected.value = true; // Request succeeded, so we are connected

          // Parse stream line by line
          // Store subscription to prevent memory leak
          final subscription = response.stream
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
              });
          await subscription.asFuture();

          // Success - exit retry loop
          return;

      } catch (e, st) {
          lastError = e is Exception ? e : Exception(e.toString());
          lastStackTrace = st;
          debugPrint("Request failed (attempt ${attempt + 1}): $e");

          if (!_isDisposed) {
            _isConnected.value = false;
          }
      }
    }

    // All retries exhausted - report error
    if (!_isDisposed && lastError != null) {
      _errorController.add(ContentGeneratorError(lastError, lastStackTrace));
    }

    if (!_isDisposed) {
      _isProcessing.value = false;
    }
  }

  @override
  void dispose() {
    _isDisposed = true;
    _healthCheckTimer?.cancel();
    _a2uiController.close();
    _textController.close();
    _errorController.close();
    _isProcessing.dispose();
    _isConnected.dispose();
  }
}
