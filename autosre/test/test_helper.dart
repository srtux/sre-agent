
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:provider/provider.dart';
import 'package:autosre/services/auth_service.dart';
import 'package:autosre/services/project_service.dart';
import 'package:autosre/services/session_service.dart';
import 'package:autosre/services/tool_config_service.dart';
import 'package:autosre/services/connectivity_service.dart';
import 'package:autosre/services/prompt_history_service.dart';
import 'package:autosre/services/dashboard_state.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:http/http.dart' as http;
import 'package:autosre/agent/adk_content_generator.dart';
import 'package:genui/genui.dart';
import 'dart:async';

class MockAuthService extends ChangeNotifier implements AuthService {
  final bool _authenticated;
  MockAuthService({bool authenticated = true}) : _authenticated = authenticated;

  @override bool get isAuthenticated => _authenticated;
  @override bool get isAuthEnabled => true;
  @override bool get isGuestMode => false;
  @override bool get isGuestModeEnabled => false;
  @override bool get isLoading => false;
  @override GoogleSignInAccount? get currentUser => null;
  @override String? get accessToken => null;
  @override String? get idToken => null;
  @override Future<void> init() async {}
  @override Future<void> signIn() async {}
  @override Future<void> signOut() async {}
  @override void loginAsGuest() {}
  @override void reset() {}
  @override set currentUser(GoogleSignInAccount? user) {}
  @override Future<Map<String, String>> getAuthHeaders() async => {};
  @override Future<http.Client> getAuthenticatedClient() async => http.Client();
}

class MockProjectService implements ProjectService {
  @override ValueListenable<List<GcpProject>> get projects => ValueNotifier([]);
  @override ValueListenable<List<GcpProject>> get recentProjects => ValueNotifier([]);
  @override ValueListenable<List<GcpProject>> get starredProjects => ValueNotifier([]);
  @override ValueListenable<GcpProject?> get selectedProject => ValueNotifier(null);
  @override ValueListenable<bool> get isLoading => ValueNotifier(false);
  @override ValueListenable<String?> get error => ValueNotifier(null);
  @override String? get selectedProjectId => null;
  @override Future<void> fetchProjects({String? query}) async {}
  @override Future<void> loadSavedProject() async {}
  @override bool isStarred(String projectId) => false;
  @override Future<void> toggleStar(GcpProject project) async {}
  @override void selectProject(String projectId) {}
  @override void selectProjectInstance(GcpProject? project) {}
  @override void clearSelection() {}
  @override void dispose() {}
}

class MockSessionService implements SessionService {
  @override ValueListenable<List<SessionSummary>> get sessions => ValueNotifier([]);
  @override ValueListenable<String?> get currentSessionId => ValueNotifier(null);
  @override ValueListenable<bool> get isLoading => ValueNotifier(false);
  @override ValueListenable<String?> get error => ValueNotifier(null);
  @override Future<void> fetchSessions({String? userId}) async {}
  @override Future<void> fetchHistory({bool force = false, String? userId}) async {}
  @override Future<Session?> createSession({String? userId, String? title, String? projectId}) async => null;
  @override Future<Session?> getSession(String sessionId) async => null;
  @override Future<bool> deleteSession(String sessionId) async => true;
  @override Future<bool> renameSession(String sessionId, String newTitle) async => true;
  @override void setCurrentSession(String? sessionId) {}
  @override Future<void> startNewSession() async {}
  @override void dispose() {}
}

class MockPromptHistoryService implements PromptHistoryService {
  @override Future<void> addPrompt(String prompt) async {}
  @override Future<List<String>> getHistory() async => [];
}

class MockConnectivityService extends ChangeNotifier implements ConnectivityService {
  @override ValueListenable<ConnectivityStatus> get status => ValueNotifier(ConnectivityStatus.connected);
  @override void updateStatus(bool isConnected) {}
}

class MockToolConfigService implements ToolConfigService {
  @override ValueListenable<bool> get isLoading => ValueNotifier(false);
  @override ValueListenable<String?> get error => ValueNotifier(null);
  @override ValueListenable<ToolConfigSummary?> get summary => ValueNotifier(null);
  @override ValueListenable<Set<String>> get testingTools => ValueNotifier({});
  @override ValueListenable<Map<ToolCategory, List<ToolConfig>>> get toolsByCategory => ValueNotifier({});

  @override Future<void> fetchConfigs() async {}
  @override Future<ToolTestResult?> testTool(String toolName) async => null;
  @override Future<Map<String, ToolTestResult>> testAllTools({ToolCategory? category}) async => {};
  @override Future<bool> setToolEnabled(String toolName, bool enabled) async => true;
  @override Future<bool> bulkUpdateTools(Map<String, bool> updates) async => true;
  @override Future<bool> enableCategory(ToolCategory category) async => true;
  @override Future<bool> disableCategory(ToolCategory category) async => true;
  @override void dispose() {}
}

class MockADKContentGenerator implements ADKContentGenerator {
  final StreamController<A2uiMessage> _a2uiController = StreamController<A2uiMessage>.broadcast();
  final StreamController<String> _textController = StreamController<String>.broadcast();
  final StreamController<ContentGeneratorError> _errorController = StreamController<ContentGeneratorError>.broadcast();
  final StreamController<String> _sessionController = StreamController<String>.broadcast();
  final StreamController<String> _uiMessageController = StreamController<String>.broadcast();
  final StreamController<List<String>> _suggestionsController = StreamController<List<String>>.broadcast();
  final StreamController<Map<String, dynamic>> _dashboardController = StreamController<Map<String, dynamic>>.broadcast();
  final StreamController<Map<String, dynamic>> _toolCallController = StreamController<Map<String, dynamic>>.broadcast();
  final ValueNotifier<bool> _isProcessing = ValueNotifier(false);
  final ValueNotifier<bool> _isConnected = ValueNotifier(true);

  @override Stream<A2uiMessage> get a2uiMessageStream => _a2uiController.stream;
  @override Stream<String> get textResponseStream => _textController.stream;
  @override Stream<ContentGeneratorError> get errorStream => _errorController.stream;
  @override Stream<String> get sessionStream => _sessionController.stream;
  @override Stream<String> get uiMessageStream => _uiMessageController.stream;
  @override Stream<List<String>> get suggestionsStream => _suggestionsController.stream;
  @override Stream<Map<String, dynamic>> get dashboardStream => _dashboardController.stream;
  @override Stream<Map<String, dynamic>> get toolCallStream => _toolCallController.stream;
  @override ValueListenable<bool> get isProcessing => _isProcessing;
  @override ValueListenable<bool> get isConnected => _isConnected;

  @override String? projectId;
  @override String? sessionId;
  @override String get baseUrl => 'http://mock';

  void emitToolCall(Map<String, dynamic> event) => _toolCallController.add(event);
  void emitText(String text) => _textController.add(text);
  void emitUiMessage(String surfaceId) => _uiMessageController.add(surfaceId);
  void setProcessing(bool value) => _isProcessing.value = value;

  @override Future<void> sendRequest(ChatMessage message, {Iterable<ChatMessage>? history, A2UiClientCapabilities? clientCapabilities}) async {}
  @override Future<void> fetchSuggestions() async {}
  @override void cancelRequest() {}
  @override void clearSession() {}
  @override void dispose() {
    _a2uiController.close();
    _textController.close();
    _errorController.close();
    _sessionController.close();
    _uiMessageController.close();
    _suggestionsController.close();
    _dashboardController.close();
    _toolCallController.close();
    // Only dispose if they haven't been disposed yet?
    // Actually, it's safer to just catch or avoid if double-dip.
    // In this case, ConversationPage also disposes it.
  }

  @override dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void setupMockSingletons({
  AuthService? auth,
  ProjectService? project,
  SessionService? session,
  ToolConfigService? toolConfig,
  PromptHistoryService? promptHistory,
  ConnectivityService? connectivity,
}) {
  AuthService.mockInstance = auth ?? MockAuthService();
  ProjectService.mockInstance = project ?? MockProjectService();
  SessionService.mockInstance = session ?? MockSessionService();
  ToolConfigService.mockInstance = toolConfig ?? MockToolConfigService();
  PromptHistoryService.mockInstance = promptHistory ?? MockPromptHistoryService();
  ConnectivityService.mockInstance = connectivity ?? MockConnectivityService();
}

void clearMockSingletons() {
  AuthService.mockInstance = null;
  ProjectService.mockInstance = null;
  SessionService.mockInstance = null;
  ToolConfigService.mockInstance = null;
  PromptHistoryService.mockInstance = null;
  ConnectivityService.mockInstance = null;
}

Widget wrapWithProviders(Widget child, {
  AuthService? auth,
  ProjectService? project,
  SessionService? session,
  ToolConfigService? toolConfig,
  PromptHistoryService? promptHistory,
  DashboardState? dashboard,
  ConnectivityService? connectivity,
}) {
  final actualAuth = auth ?? MockAuthService();
  final actualProject = project ?? MockProjectService();
  final actualSession = session ?? MockSessionService();
  final actualToolConfig = toolConfig ?? MockToolConfigService();
  final actualPromptHistory = promptHistory ?? MockPromptHistoryService();
  final actualDashboard = dashboard ?? DashboardState();
  final actualConnectivity = connectivity ?? MockConnectivityService();

  // Also set singletons for non-widget code
  setupMockSingletons(
    auth: actualAuth,
    project: actualProject,
    session: actualSession,
    toolConfig: actualToolConfig,
    promptHistory: actualPromptHistory,
    connectivity: actualConnectivity,
  );

  return MultiProvider(
    providers: [
      ChangeNotifierProvider<AuthService>.value(value: actualAuth),
      Provider<ProjectService>.value(value: actualProject),
      Provider<SessionService>.value(value: actualSession),
      Provider<ToolConfigService>.value(value: actualToolConfig),
      Provider<PromptHistoryService>.value(value: actualPromptHistory),
      ChangeNotifierProvider<DashboardState>.value(value: actualDashboard),
      ChangeNotifierProvider<ConnectivityService>.value(value: actualConnectivity),
    ],
    child: child,
  );
}
