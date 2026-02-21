import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:genui/genui.dart';

import '../agent/adk_content_generator.dart';
import '../catalog.dart';
import '../models/adk_schema.dart';
import '../services/dashboard_state.dart';
import '../services/session_service.dart';

String _encodeJsonMap(dynamic obj) {
  try {
    return const JsonEncoder.withIndent('  ').convert(obj);
  } catch (_) {
    return obj.toString();
  }
}

/// Callback signature for showing status/error toasts.
typedef ToastCallback = void Function(String message, {bool isError});

/// Manages the stream subscriptions, conversation lifecycle, and tool call
/// state for [ConversationPage].
///
/// Extracts all stream wiring out of the page state so the page can focus
/// on layout orchestration.
class ConversationController {
  ConversationController({
    required this.sessionService,
    required this.dashboardState,
    required this.onScrollToBottom,
    required this.showToast,
    required this.isMounted,
  });

  final SessionService sessionService;
  final DashboardState dashboardState;
  final void Function({bool force}) onScrollToBottom;
  final ToastCallback showToast;
  final bool Function() isMounted;

  // --- Public observable state ---

  GenUiConversation? conversation;
  ADKContentGenerator? contentGenerator;
  late A2uiMessageProcessor messageProcessor;

  /// Inline tool call state: call_id -> ToolLog.
  final ValueNotifier<Map<String, ToolLog>> toolCallState = ValueNotifier({});

  /// Suggested follow-up actions.
  final ValueNotifier<List<String>> suggestedActions = ValueNotifier([
    "Analyze last hour's logs",
    'List active incidents',
    'Check for high latency',
  ]);

  /// Current agent trace info for Cloud Trace deep linking.
  String? currentTraceUrl;
  String? currentTraceId;

  // --- Private subscriptions ---

  StreamSubscription<String>? _sessionSubscription;
  StreamSubscription<ContentGeneratorError>? _errorSubscription;
  StreamSubscription<String>? _uiMessageSubscription;
  StreamSubscription<List<String>>? _suggestionsSubscription;
  StreamSubscription<Map<String, dynamic>>? _dashboardSubscription;
  StreamSubscription<Map<String, dynamic>>? _toolCallSubscription;
  StreamSubscription<Map<String, dynamic>>? _traceInfoSubscription;
  StreamSubscription<Map<String, dynamic>>? _memorySubscription;

  /// Initialize (or re-initialize) the conversation and all stream
  /// subscriptions. Call this on first build and when resetting sessions.
  ///
  /// [widgetContentGenerator] is an optional externally-provided generator
  /// (e.g. for testing). If null a new one is created.
  ///
  /// [projectId] is the currently selected GCP project.
  ///
  /// Returns `true` so callers can use it inside `setState`.
  bool initialize({
    ADKContentGenerator? widgetContentGenerator,
    required String? projectId,
  }) {
    final sreCatalog = CatalogRegistry.createSreCatalog();

    messageProcessor = A2uiMessageProcessor(
      catalogs: [sreCatalog, CoreCatalogItems.asCatalog()],
    );

    // Dispose previous conversation and generator
    conversation?.dispose();
    if (contentGenerator != widgetContentGenerator) {
      contentGenerator?.dispose();
    }

    final newGenerator = widgetContentGenerator ?? ADKContentGenerator();
    contentGenerator = newGenerator;
    newGenerator.projectId = projectId;

    // --- Wire up all stream subscriptions ---

    _sessionSubscription?.cancel();
    _sessionSubscription = newGenerator.sessionStream.listen((sessionId) {
      sessionService.setCurrentSession(sessionId);
      sessionService.fetchSessions();
    });

    _errorSubscription?.cancel();
    _errorSubscription = newGenerator.errorStream.listen((error) {
      if (isMounted()) {
        showToast('Agent Error: ${error.error}', isError: true);
        debugPrint(
          'ContentGenerator Error: ${error.error}\n${error.stackTrace}',
        );
      }
    });

    final conv = GenUiConversation(
      a2uiMessageProcessor: messageProcessor,
      contentGenerator: newGenerator,
      onSurfaceAdded: (_) => onScrollToBottom(force: true),
      onSurfaceUpdated: (_) => onScrollToBottom(),
      onTextResponse: (_) => onScrollToBottom(),
    );
    conversation = conv;

    _traceInfoSubscription?.cancel();
    _traceInfoSubscription = newGenerator.traceInfoStream.listen((event) {
      if (!isMounted()) return;
      currentTraceId = event['trace_id'] as String?;
      currentTraceUrl = event['trace_url'] as String?;
      // Caller should call setState after calling initialize.
    });

    _memorySubscription?.cancel();
    _memorySubscription = newGenerator.memoryStream.listen((event) {
      if (!isMounted()) return;
      final action = event['action'] as String? ?? '';
      final title = event['title'] as String? ?? 'Memory event';
      final category = event['category'] as String? ?? '';

      debugPrint(
        '\u{1F9E0} [MEMORY] action=$action, title=$title, category=$category',
      );

      if (action == 'stored' || action == 'pattern_learned') {
        showToast('\u{1F9E0} $title', isError: false);
      }
    });

    _dashboardSubscription?.cancel();
    _dashboardSubscription = newGenerator.dashboardStream.listen((event) {
      debugPrint(
        '\u{1F4CA} [DASH] Received dashboard event: category=${event['category']}, tool=${event['tool_name']}',
      );
      dashboardState.addFromEvent(event);
    });

    _toolCallSubscription?.cancel();
    _toolCallSubscription = newGenerator.toolCallStream.listen((event) {
      if (!isMounted()) return;
      final eventType = event['type'] as String;

      if (eventType == 'tool_call') {
        _handleToolCall(event, conv);
      } else if (eventType == 'tool_response') {
        _handleToolResponse(event);
      }
    });

    _uiMessageSubscription?.cancel();
    _uiMessageSubscription = newGenerator.uiMessageStream.listen((surfaceId) {
      if (!isMounted()) return;

      final messenger = conv.conversation;
      if (messenger is ValueNotifier<List<ChatMessage>>) {
        final currentMessages = List<ChatMessage>.from(messenger.value);
        final alreadyHas = currentMessages.any(
          (m) => m is AiUiMessage && m.surfaceId == surfaceId,
        );
        if (!alreadyHas) {
          currentMessages.add(
            AiUiMessage(
              definition: UiDefinition(surfaceId: surfaceId),
              surfaceId: surfaceId,
            ),
          );
          messenger.value = currentMessages;
        }
      }
    });

    _suggestionsSubscription?.cancel();
    _suggestionsSubscription = newGenerator.suggestionsStream.listen((
      suggestions,
    ) {
      if (isMounted()) {
        suggestedActions.value = suggestions;
      }
    });

    newGenerator.fetchSuggestions();

    return true;
  }

  void _handleToolCall(Map<String, dynamic> event, GenUiConversation conv) {
    final callId = event['call_id'] as String;
    final toolName = event['tool_name'] as String;
    final args = Map<String, dynamic>.from(event['args'] ?? {});

    final toolLog = ToolLog(toolName: toolName, args: args, status: 'running');

    final updated = Map<String, ToolLog>.from(toolCallState.value);
    updated[callId] = toolLog;
    toolCallState.value = updated;

    final messenger = conv.conversation;
    if (messenger is ValueNotifier<List<ChatMessage>>) {
      final currentMessages = List<ChatMessage>.from(messenger.value);
      final alreadyHas = currentMessages.any(
        (m) => m is AiUiMessage && m.surfaceId == callId,
      );
      if (!alreadyHas) {
        currentMessages.add(
          AiUiMessage(
            definition: UiDefinition(surfaceId: callId),
            surfaceId: callId,
          ),
        );
        messenger.value = currentMessages;
      }
    }
    onScrollToBottom();
  }

  void _handleToolResponse(Map<String, dynamic> event) {
    final callId = event['call_id'] as String;
    final toolName = event['tool_name'] as String;
    final status = event['status'] as String? ?? 'completed';
    final result = event['result'];

    // JSON encoding of typical tool results is fast (<1ms). Using compute()
    // on Flutter Web runs synchronously on the main thread with added
    // serialization overhead, which is counter-productive.
    String? resultStr;
    if (result != null) {
      if (result is String) {
        resultStr = result;
      } else {
        resultStr = _encodeJsonMap(result);
      }
    }

    if (!isMounted()) return;

    final existing = toolCallState.value[callId];
    final args = existing?.args ?? {};

    final toolLog = ToolLog(
      toolName: toolName,
      args: args,
      status: status,
      result: resultStr,
    );

    final updated = Map<String, ToolLog>.from(toolCallState.value);
    updated[callId] = toolLog;
    toolCallState.value = updated;
  }

  /// Clear all session state for a fresh investigation.
  void clearSessionState() {
    contentGenerator?.clearSession();
    sessionService.startNewSession();
    dashboardState.clear();
    toolCallState.value = {};
    currentTraceUrl = null;
    currentTraceId = null;
  }

  /// Cancel all subscriptions and dispose resources.
  void dispose() {
    _sessionSubscription?.cancel();
    _errorSubscription?.cancel();
    _uiMessageSubscription?.cancel();
    _suggestionsSubscription?.cancel();
    _dashboardSubscription?.cancel();
    _toolCallSubscription?.cancel();
    _traceInfoSubscription?.cancel();
    _memorySubscription?.cancel();
    toolCallState.dispose();
    suggestedActions.dispose();
    conversation?.dispose();
    contentGenerator?.dispose();
  }
}
