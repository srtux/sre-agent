
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

class MockAuthService extends ChangeNotifier implements AuthService {
  final bool _authenticated;
  MockAuthService({bool authenticated = true}) : _authenticated = authenticated;

  @override bool get isAuthenticated => _authenticated;
  @override bool get isAuthEnabled => true;
  @override bool get isLoading => false;
  @override GoogleSignInAccount? get currentUser => null;
  @override String? get accessToken => null;
  @override String? get idToken => null;
  @override Future<void> init() async {}
  @override Future<void> signIn() async {}
  @override Future<void> signOut() async {}
  @override void reset() {}
  @override set currentUser(GoogleSignInAccount? user) {}
  @override Future<Map<String, String>> getAuthHeaders() async => {};
  @override Future<http.Client> getAuthenticatedClient() async => http.Client();
}

class MockProjectService implements ProjectService {
  @override ValueListenable<List<GcpProject>> get projects => ValueNotifier([]);
  @override ValueListenable<List<GcpProject>> get recentProjects => ValueNotifier([]);
  @override ValueListenable<GcpProject?> get selectedProject => ValueNotifier(null);
  @override ValueListenable<bool> get isLoading => ValueNotifier(false);
  @override ValueListenable<String?> get error => ValueNotifier(null);
  @override String? get selectedProjectId => null;
  @override Future<void> fetchProjects({String? query}) async {}
  @override Future<void> loadSavedProject() async {}
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
