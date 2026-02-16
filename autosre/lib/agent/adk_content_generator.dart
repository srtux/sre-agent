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
  final StreamController<Map<String, dynamic>> _dashboardController =
      StreamController<Map<String, dynamic>>.broadcast();
  final StreamController<Map<String, dynamic>> _toolCallController =
      StreamController<Map<String, dynamic>>.broadcast();
  final StreamController<Map<String, dynamic>> _traceInfoController =
      StreamController<Map<String, dynamic>>.broadcast();
  final StreamController<Map<String, dynamic>> _memoryController =
      StreamController<Map<String, dynamic>>.broadcast();
  final StreamController<Map<String, dynamic>> _agentActivityController =
      StreamController<Map<String, dynamic>>.broadcast();
  final StreamController<Map<String, dynamic>> _councilGraphController =
      StreamController<Map<String, dynamic>>.broadcast();
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

  /// Stream of dashboard data events (separate from A2UI).
  Stream<Map<String, dynamic>> get dashboardStream =>
      _dashboardController.stream;

  /// Stream of tool call/response events for inline chat display.
  Stream<Map<String, dynamic>> get toolCallStream => _toolCallController.stream;

  /// Stream of trace_info events for Cloud Trace deep linking.
  Stream<Map<String, dynamic>> get traceInfoStream =>
      _traceInfoController.stream;

  /// Stream of memory events (memorizing, searching, pattern learning).
  Stream<Map<String, dynamic>> get memoryStream => _memoryController.stream;

  /// Stream of agent_activity events for council dashboard visualization.
  Stream<Map<String, dynamic>> get agentActivityStream =>
      _agentActivityController.stream;

  /// Stream of council_graph events for full investigation visualization.
  Stream<Map<String, dynamic>> get councilGraphStream =>
      _councilGraphController.stream;

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
      if (!_isDisposed) {
        _isConnected.value = true;
        ConnectivityService().updateStatus(true);
      }
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

    // Prevent concurrent requests: cancel in-flight request before starting new one
    if (_isProcessing.value) {
      cancelRequest();
    }

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

        _streamSubscription = response.stream
            .transform(utf8.decoder)
            .transform(const LineSplitter())
            .listen((line) {
              lineCount++;
              if (line.trim().isEmpty) return;
              try {
                final data = jsonDecode(line);
                final type = data['type'];

                if (type == 'text') {
                  _textController.add(data['content']);
                } else if (type == 'error') {
                  final errorMessage =
                      data['error'] as String? ?? 'Unknown error';
                  _textController.add('\n\n**Error:** $errorMessage\n');
                  _errorController.add(
                    ContentGeneratorError(
                      Exception(errorMessage),
                      StackTrace.current,
                    ),
                  );
                } else if (type == 'tool_call' || type == 'tool_response') {
                  // Simple inline tool call/response events
                  _toolCallController.add(Map<String, dynamic>.from(data));
                } else if (type == 'a2ui') {
                  final msgJson = data['message'] as Map<String, dynamic>;
                  try {
                    final msg = A2uiMessage.fromJson(msgJson);
                    _a2uiController.add(msg);
                  } catch (parseError) {
                    debugPrint('A2UI parse error: $parseError');
                  }
                } else if (type == 'ui') {
                  final newSurfaceId = data['surface_id'] as String?;
                  if (newSurfaceId != null) {
                    _uiMessageController.add(newSurfaceId);
                  }
                } else if (type == 'trace_info') {
                  debugPrint('🔗 [TRACE_INFO] trace_id=${data['trace_id']}');
                  _traceInfoController.add(Map<String, dynamic>.from(data));
                } else if (type == 'dashboard') {
                  debugPrint(
                    '📊 [DASHBOARD] category=${data['category']}, tool=${data['tool_name']}',
                  );
                  _dashboardController.add(Map<String, dynamic>.from(data));
                } else if (type == 'memory') {
                  debugPrint(
                    '🧠 [MEMORY] action=${data['action']}, title=${data['title']}',
                  );
                  _memoryController.add(Map<String, dynamic>.from(data));
                } else if (type == 'session') {
                  final newSessionId = data['session_id'] as String?;
                  if (newSessionId != null) {
                    sessionId = newSessionId;
                    _sessionController.add(newSessionId);
                    debugPrint(
                      '🔑 [SESSION] Session ID updated: $newSessionId',
                    );
                  }
                } else if (type == 'agent_activity') {
                  debugPrint(
                    '🤖 [AGENT_ACTIVITY] agent=${data['agent']?['agent_name']}',
                  );
                  _agentActivityController.add(Map<String, dynamic>.from(data));
                } else if (type == 'council_graph') {
                  debugPrint(
                    '🏛️ [COUNCIL_GRAPH] investigation=${data['investigation_id']}, agents=${(data['agents'] as List?)?.length ?? 0}',
                  );
                  _councilGraphController.add(Map<String, dynamic>.from(data));
                } else {
                  debugPrint('❓ [UNKNOWN] Unknown event type: $type');
                }
              } catch (e, stack) {
                debugPrint('❌ [PARSE_ERROR] Error parsing line $lineCount: $e');
                debugPrint(
                  '❌ [PARSE_ERROR] Line content: ${line.length > 500 ? "${line.substring(0, 500)}..." : line}',
                );
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

        // Fetch new contextual suggestions after successful request
        unawaited(fetchSuggestions());
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
    if (_isDisposed) return;
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
    _dashboardController.close();
    _toolCallController.close();
    _traceInfoController.close();
    _memoryController.close();
    _agentActivityController.close();
    _councilGraphController.close();
    _isProcessing.dispose();
    _isConnected.dispose();
  }
}
