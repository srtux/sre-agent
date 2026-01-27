import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:genui/genui.dart';
import 'package:http/http.dart' as http;
import '../services/auth_service.dart';
import '../services/connectivity_service.dart';

/// A ContentGenerator that connects to the Python SRE Agent.
class ADKContentGenerator implements ContentGenerator {
  final StreamController<A2uiMessage> _a2uiController =
      StreamController<A2uiMessage>.broadcast();
  final StreamController<String> _textController =
      StreamController<String>.broadcast();
  final StreamController<ContentGeneratorError> _errorController =
      StreamController<ContentGeneratorError>.broadcast();
  final StreamController<String> _sessionController =
      StreamController<String>.broadcast();
  final StreamController<String> _uiMessageController =
      StreamController<String>.broadcast();
  final StreamController<List<String>> _suggestionsController =
      StreamController<List<String>>.broadcast();
  final ValueNotifier<bool> _isProcessing = ValueNotifier(false);
  final ValueNotifier<bool> _isConnected = ValueNotifier(false);

  bool _isDisposed = false;

  /// Current HTTP client for cancellation support.
  http.Client? _currentClient;
  StreamSubscription<String>? _streamSubscription;
  Timer? _healthCheckTimer;

  static const Duration _requestTimeout = Duration(seconds: 30);
  static const Duration _healthCheckTimeout = Duration(seconds: 5);
  static const int _maxRetries = 2;
  static const Duration _retryDelay = Duration(seconds: 2);

  String? projectId;
  String? sessionId;

  /// Stream of session ID updates (emitted when backend assigns/creates session).
  Stream<String> get sessionStream => _sessionController.stream;

  /// Stream of new UI surface IDs to be added as messages.
  Stream<String> get uiMessageStream => _uiMessageController.stream;

  /// Stream of suggested actions.
  Stream<List<String>> get suggestionsStream => _suggestionsController.stream;

  /// The base URL of the connected agent.
  String get baseUrl => _baseUrl;

  /// Returns the base API URL based on the runtime environment.
  String get _baseUrl {
    if (kDebugMode) {
      return 'http://127.0.0.1:8001';
    }
    return '';
  }

  String get _healthUrl => '$_baseUrl/health';

  ADKContentGenerator({this.projectId, this.sessionId}) {
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
      await http.get(Uri.parse(_healthUrl)).timeout(_healthCheckTimeout);
      if (_isDisposed) return;
      // Any response from the server means we are connected
      _isConnected.value = true;
      ConnectivityService().updateStatus(true);
    } catch (e) {
      if (!_isDisposed) {
        _isConnected.value = false;
        ConnectivityService().updateStatus(false);
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

  ValueListenable<bool> get isConnected =>
      _isConnected; // Expose connection status

  /// Cancels the current request if one is in progress.
  void cancelRequest() {
    if (_currentClient != null) {
      debugPrint('Cancelling current request...');

      // Cancel the stream subscription first
      _streamSubscription?.cancel();
      _streamSubscription = null;

      // Close the HTTP client
      _currentClient!.close();
      _currentClient = null;

      // Update processing state
      _isProcessing.value = false;

      // Add cancellation message
      _textController.add('\n\n*Request cancelled by user.*');
    }
  }

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

    // Create a new client for this request (allows cancellation)
    try {
      _currentClient = await AuthService().getAuthenticatedClient();
    } catch (e) {
      debugPrint('Error getting authenticated client: $e');
      // Rethrow to notify the UI that authentication failed
      rethrow;
    }

    for (var attempt = 0; attempt <= _maxRetries; attempt++) {
      if (_isDisposed || _currentClient == null) break;

      try {
        // Retry delay with exponential backoff
        if (attempt > 0) {
          final delay = _retryDelay * (1 << (attempt - 1));
          debugPrint(
            'Retrying request (attempt ${attempt + 1}/${_maxRetries + 1}) after ${delay.inSeconds}s...',
          );
          await Future.delayed(delay);
        }

        if (_currentClient == null) break; // Check again after delay

        // Use the /agent endpoint where the ADK app is mounted
        final request = http.Request('POST', Uri.parse('$_baseUrl/agent'));
        request.headers['Content-Type'] = 'application/json';

        final requestBody = <String, dynamic>{
          'messages': [
            {'role': 'user', 'text': message.text},
          ],
        };

        // Include session_id if set
        if (sessionId != null && sessionId!.isNotEmpty) {
          requestBody['session_id'] = sessionId;
        }

        // Include user_id from auth service
        final userId = AuthService().currentUser?.email;
        if (userId != null) {
          requestBody['user_id'] = userId;
        }

        request.body = jsonEncode(requestBody);

        final response = await _currentClient!
            .send(request)
            .timeout(_requestTimeout);

        if (response.statusCode != 200) {
          throw Exception('Failed to connect to agent: ${response.statusCode}');
        }

        _isConnected.value = true; // Request succeeded, so we are connected
        ConnectivityService().updateStatus(true);

        // Parse stream line by line
        // Store subscription to allow cancellation
        var lineCount = 0;
        var a2uiCount = 0;
        var uiCount = 0;
        var textCount = 0;

        _streamSubscription = response.stream
            .transform(utf8.decoder)
            .transform(const LineSplitter())
            .listen((line) {
              lineCount++;
              if (line.trim().isEmpty) {
                debugPrint('📥 [LINE $lineCount] Empty line, skipping');
                return;
              }
              try {
                debugPrint('📥 [LINE $lineCount] Received: ${line.length > 200 ? "${line.substring(0, 200)}..." : line}');

                final data = jsonDecode(line);
                final type = data['type'];

                debugPrint('📥 [LINE $lineCount] Parsed type: $type');

                if (type == 'text') {
                  textCount++;
                  final content = data['content'] as String?;
                  debugPrint('📝 [TEXT #$textCount] Content length: ${content?.length ?? 0}');
                  _textController.add(data['content']);
                } else if (type == 'error') {
                  // Handle error events from backend
                  final errorMessage = data['error'] as String? ?? 'Unknown error';
                  debugPrint('⚠️ [ERROR] Agent error received: $errorMessage');

                  // Show error in chat as text
                  _textController.add('\n\n**Error:** $errorMessage\n');

                  // Also emit to error stream for StatusToast notification
                  _errorController.add(
                    ContentGeneratorError(
                      Exception(errorMessage),
                      StackTrace.current,
                    ),
                  );
                } else if (type == 'a2ui') {
                  a2uiCount++;
                  final msgJson = data['message'] as Map<String, dynamic>;

                  // Detailed A2UI debugging
                  debugPrint('🎯 [A2UI #$a2uiCount] ===== A2UI MESSAGE RECEIVED =====');
                  debugPrint('🎯 [A2UI #$a2uiCount] Raw message keys: ${msgJson.keys.toList()}');

                  if (msgJson.containsKey('beginRendering')) {
                    final br = msgJson['beginRendering'] as Map<String, dynamic>?;
                    debugPrint('🎯 [A2UI #$a2uiCount] Type: beginRendering');
                    debugPrint('🎯 [A2UI #$a2uiCount] surfaceId: ${br?['surfaceId']}');
                    debugPrint('🎯 [A2UI #$a2uiCount] root: ${br?['root']}');
                    final components = br?['components'] as List?;
                    debugPrint('🎯 [A2UI #$a2uiCount] components count: ${components?.length ?? 0}');
                    if (components != null && components.isNotEmpty) {
                      for (var i = 0; i < components.length; i++) {
                        final comp = components[i] as Map<String, dynamic>?;
                        debugPrint('🎯 [A2UI #$a2uiCount] Component[$i] id: ${comp?['id']}');
                        debugPrint('🎯 [A2UI #$a2uiCount] Component[$i] type: ${comp?['type']}');
                        debugPrint('🎯 [A2UI #$a2uiCount] Component[$i] keys: ${comp?.keys.toList()}');
                        if (comp?.containsKey('component') == true) {
                          final inner = comp!['component'] as Map<String, dynamic>?;
                          debugPrint('🎯 [A2UI #$a2uiCount] Component[$i].component keys: ${inner?.keys.toList()}');
                          debugPrint('🎯 [A2UI #$a2uiCount] Component[$i].component.type: ${inner?['type']}');
                        }
                      }
                    }
                  } else if (msgJson.containsKey('surfaceUpdate')) {
                    final su = msgJson['surfaceUpdate'] as Map<String, dynamic>?;
                    debugPrint('🎯 [A2UI #$a2uiCount] Type: surfaceUpdate');
                    debugPrint('🎯 [A2UI #$a2uiCount] surfaceId: ${su?['surfaceId']}');
                    final components = su?['components'] as List?;
                    debugPrint('🎯 [A2UI #$a2uiCount] components count: ${components?.length ?? 0}');
                  }

                  debugPrint('🎯 [A2UI #$a2uiCount] Parsing A2uiMessage...');
                  try {
                    final msg = A2uiMessage.fromJson(msgJson);
                    debugPrint('🎯 [A2UI #$a2uiCount] Parsed successfully: ${msg.runtimeType}');
                    debugPrint('🎯 [A2UI #$a2uiCount] Emitting to a2uiController...');
                    _a2uiController.add(msg);
                    debugPrint('🎯 [A2UI #$a2uiCount] ✅ Emitted to stream');
                  } catch (parseError, parseStack) {
                    debugPrint('🎯 [A2UI #$a2uiCount] ❌ Parse error: $parseError');
                    debugPrint('🎯 [A2UI #$a2uiCount] Stack: $parseStack');
                  }
                  debugPrint('🎯 [A2UI #$a2uiCount] ===== END A2UI MESSAGE =====');
                } else if (type == 'ui') {
                  uiCount++;
                  // New UI component that should be added as a message bubble
                  final newSurfaceId = data['surface_id'] as String?;
                  debugPrint('🖼️ [UI #$uiCount] ===== UI MARKER RECEIVED =====');
                  debugPrint('🖼️ [UI #$uiCount] surface_id: $newSurfaceId');
                  debugPrint('🖼️ [UI #$uiCount] a2ui messages received so far: $a2uiCount');
                  if (newSurfaceId != null) {
                    debugPrint('🖼️ [UI #$uiCount] Emitting to uiMessageController...');
                    _uiMessageController.add(newSurfaceId);
                    debugPrint('🖼️ [UI #$uiCount] ✅ Emitted to stream');
                  } else {
                    debugPrint('🖼️ [UI #$uiCount] ⚠️ surface_id is null, skipping');
                  }
                  debugPrint('🖼️ [UI #$uiCount] ===== END UI MARKER =====');
                } else if (type == 'session') {
                  // Update session ID from server
                  final newSessionId = data['session_id'] as String?;
                  if (newSessionId != null) {
                    sessionId = newSessionId;
                    _sessionController.add(newSessionId);
                    debugPrint('🔑 [SESSION] Session ID updated: $newSessionId');
                  }
                } else {
                  debugPrint('❓ [UNKNOWN] Unknown event type: $type');
                }
              } catch (e, stack) {
                debugPrint('❌ [PARSE_ERROR] Error parsing line $lineCount: $e');
                debugPrint('❌ [PARSE_ERROR] Line content: ${line.length > 500 ? "${line.substring(0, 500)}..." : line}');
                debugPrint('❌ [PARSE_ERROR] Stack: $stack');
              }
            });
        await _streamSubscription!.asFuture();

        // Success - exit retry loop
        _currentClient = null;
        _streamSubscription = null;
        if (!_isDisposed) {
          _isProcessing.value = false;
        }
        return;
      } catch (e, st) {
        // Check if this was a cancellation
        if (_currentClient == null) {
          debugPrint('Request was cancelled');
          break;
        }

        // Check if stream subscription was cancelled
        if (_streamSubscription == null) {
          debugPrint('Stream was cancelled');
          break;
        }

        lastError = e is Exception ? e : Exception(e.toString());
        lastStackTrace = st;
        debugPrint('Request failed (attempt ${attempt + 1}): $e');

        if (!_isDisposed) {
          _isConnected.value = false;
          ConnectivityService().updateStatus(false);
        }
      }
    }

    _currentClient = null;

    // All retries exhausted - report error
    if (!_isDisposed && lastError != null) {
      _errorController.add(
        ContentGeneratorError(lastError, lastStackTrace ?? StackTrace.empty),
      );
    }

    if (!_isDisposed) {
      _isProcessing.value = false;
    }

    // Fetch new contextual suggestions after request is complete
    unawaited(fetchSuggestions());
  }

  /// Fetches contextual suggestions from the backend.
  Future<void> fetchSuggestions() async {
    if (_isDisposed) return;
    try {
      final queryParams = <String, String>{};
      if (projectId != null) queryParams['project_id'] = projectId!;
      if (sessionId != null) queryParams['session_id'] = sessionId!;

      final uri = Uri.parse(
        '$_baseUrl/api/suggestions',
      ).replace(queryParameters: queryParams);

      // We must get an authenticated client. If this throws, it means we are not logged in.
      final client = await AuthService.instance.getAuthenticatedClient();

      final response = await client
          .get(uri)
          .timeout(const Duration(seconds: 10)); // Increased timeout

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final suggestions = List<String>.from(data['suggestions'] ?? []);
        if (suggestions.isNotEmpty && !_isDisposed) {
          _suggestionsController.add(suggestions);
        }
      }
    } catch (e) {
      debugPrint('Error fetching suggestions: $e');
    }
  }

  /// Clears the current session (for starting a new conversation).
  void clearSession() {
    sessionId = null;
  }

  @override
  void dispose() {
    _isDisposed = true;
    _streamSubscription?.cancel();
    _streamSubscription = null;
    _currentClient?.close();
    _currentClient = null;
    _healthCheckTimer?.cancel();
    _a2uiController.close();
    _textController.close();
    _uiMessageController.close();
    _errorController.close();
    _sessionController.close();
    _suggestionsController.close();
    _isProcessing.dispose();
    _isConnected.dispose();
  }
}
