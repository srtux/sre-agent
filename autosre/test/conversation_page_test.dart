import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:autosre/pages/conversation_page.dart';
import 'package:autosre/services/auth_service.dart';
import 'package:google_sign_in_platform_interface/google_sign_in_platform_interface.dart';
import 'package:plugin_platform_interface/plugin_platform_interface.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    GoogleSignInPlatform.instance = MockGoogleSignIn();
  });

  testWidgets('ConversationPage builds correctly and shows input area', (WidgetTester tester) async {
    // Set a desktop-like size
    tester.view.physicalSize = const Size(1280, 800);
    tester.view.devicePixelRatio = 1.0;

    final authService = AuthService();
    // We don't need to call init() if we just want to render the page,
    // but the page might expect some state.

    await tester.pumpWidget(
      ChangeNotifierProvider<AuthService>.value(
        value: authService,
        child: const MaterialApp(
          home: ConversationPage(),
        ),
      ),
    );

    // Initial pump to build the widget
    await tester.pump();

    // Verify key UI elements are present
    expect(find.text('AutoSRE'), findsAtLeast(1)); // Title in AppBar
    expect(find.byIcon(Icons.smart_toy), findsAtLeast(1)); // Logo

    // Check for the input area (UnifiedPromptInput is in both hero and active states)
    expect(find.byType(TextField), findsOneWidget);
    expect(find.text('Ask anything...'), findsOneWidget);

    // Note: The keyboard hint 'Enter to send...' is only in the active conversation view,
    // not in the initial Hero empty state.

    addTearDown(tester.view.resetPhysicalSize);
  });
}

class MockGoogleSignIn extends Fake
    with MockPlatformInterfaceMixin
    implements GoogleSignInPlatform {
  @override
  Future<void> init(InitParameters params) async {}

  @override
  Future<GoogleSignInUserData?> signInSilently() async => null;

  @override
  Future<AuthenticationResults?> attemptLightweightAuthentication(dynamic options) async => null;

  @override
  Stream<AuthenticationEvent> get authenticationEvents => const Stream.empty();

  @override
  Future<void> initialize() async {}

  @override
  Future<void> attemptLightweightAuthenticationWithDefaultOptions() async {}
}
