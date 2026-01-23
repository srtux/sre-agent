import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:autosre/pages/conversation_page.dart';
import 'package:autosre/services/auth_service.dart';
import 'package:autosre/services/project_service.dart';
import 'package:google_sign_in/google_sign_in.dart' as gsi;
import 'package:google_sign_in_platform_interface/google_sign_in_platform_interface.dart';
import 'package:plugin_platform_interface/plugin_platform_interface.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    GoogleSignInPlatform.instance = MockGoogleSignIn();

    // Setup Mock Services
    AuthService.mockInstance = MockAuthService();
    ProjectService.mockInstance = MockProjectService();
  });

  tearDown(() {
    AuthService.mockInstance = null;
    ProjectService.mockInstance = null;
  });

  testWidgets('ConversationPage builds correctly and shows logo', (WidgetTester tester) async {
    // Set a desktop-like size
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;

    await tester.pumpWidget(
      MaterialApp(
        home: ChangeNotifierProvider<AuthService>.value(
          value: AuthService.instance,
          child: const ConversationPage(),
        ),
      ),
    );

    // Initial pump
    await tester.pump();

    // Verify logo icon
    expect(find.byIcon(Icons.smart_toy), findsAtLeast(1));

    // Verify input area elements
    expect(find.byType(TextField), findsAtLeast(1));
    expect(find.text('Ask anything...'), findsOneWidget);

    addTearDown(tester.view.resetPhysicalSize);
  });
}

class MockAuthService extends ChangeNotifier implements AuthService {
  @override
  bool get isAuthenticated => true;

  @override
  bool get isLoading => false;

  @override
  Future<void> init() async {}

  @override
  String? get idToken => 'mock-id-token';

  @override
  String? get accessToken => 'mock-access-token';

  @override
  gsi.GoogleSignInAccount? get currentUser => null;

  @override
  Future<http.Client> getAuthenticatedClient() async => http.Client();

  @override
  Future<void> signIn() async {}

  @override
  Future<void> signOut() async {}
}

class MockProjectService extends ChangeNotifier implements ProjectService {
  @override
  ValueListenable<List<GcpProject>> get projects => ValueNotifier([]);
  @override
  ValueListenable<List<GcpProject>> get recentProjects => ValueNotifier([]);
  @override
  ValueListenable<GcpProject?> get selectedProject => ValueNotifier(null);
  @override
  ValueListenable<bool> get isLoading => ValueNotifier(false);
  @override
  ValueListenable<String?> get error => ValueNotifier(null);
  @override
  String? get selectedProjectId => null;

  @override
  Future<void> fetchProjects({String? query}) async {}
  @override
  Future<void> loadSavedProject() async {}
  @override
  void selectProject(String projectId) {}
  @override
  void selectProjectInstance(GcpProject? project) {}
  @override
  void clearSelection() {}
}

class MockGoogleSignIn extends Fake
    with MockPlatformInterfaceMixin
    implements GoogleSignInPlatform {
  @override
  Future<void> init(InitParameters params) async {}

  Future<GoogleSignInUserData?> signInSilently() async => null;

  @override
  Future<AuthenticationResults?> attemptLightweightAuthentication(dynamic options) async => null;

  @override
  Stream<AuthenticationEvent> get authenticationEvents => const Stream.empty();

  Future<void> initialize() async {}

  Future<void> attemptLightweightAuthenticationWithDefaultOptions() async {}
}
