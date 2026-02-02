import 'package:flutter/foundation.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:autosre/services/prompt_history_service.dart';
import 'package:autosre/services/auth_service.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:http/http.dart' as http;

// Mock GoogleSignInAuthentication
class MockGoogleSignInAuthentication implements GoogleSignInAuthentication {
  @override
  String? get idToken => 'mock_id_token';

  // ignore: deprecated_member_use
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// Mock GoogleSignInAccount
class MockGoogleSignInAccount implements GoogleSignInAccount {
  @override
  final String email;

  @override
  String get id => 'id_$email';

  @override
  String? get displayName => 'Test User';

  @override
  String? get photoUrl => null;

  MockGoogleSignInAccount(this.email);

  // ignore: deprecated_member_use
  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

// Mock AuthService
class MockAuthService extends ChangeNotifier implements AuthService {
  GoogleSignInAccount? _currentUser;

  @override
  GoogleSignInAccount? get currentUser => _currentUser;

  @override
  set currentUser(GoogleSignInAccount? user) {
    _currentUser = user;
    notifyListeners();
  }

  void setCurrentUser(GoogleSignInAccount? user) {
    currentUser = user;
  }

  @override
  void reset() {}

  // Boilerplate implementation of AuthService abstract members
  @override
  String? get accessToken => 'mock_token';
  @override
  String? get idToken => 'mock_id_token';
  @override
  bool get isAuthEnabled => true;
  @override
  bool get isAuthenticated => _currentUser != null;
  @override
  bool get isLoading => false;

  @override
  Future<void> init() async {}
  @override
  Future<http.Client> getAuthenticatedClient() async => http.Client();
  @override
  Future<Map<String, String>> getAuthHeaders() async => {};
  @override
  Future<void> signIn() async {}
  @override
  Future<void> signOut() async {}
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late PromptHistoryService service;
  late MockAuthService mockAuthService;

  setUp(() {
    // Reset SharedPreferences
    SharedPreferences.setMockInitialValues({});

    // Mock AuthService
    mockAuthService = MockAuthService();
    AuthService.mockInstance = mockAuthService;

    // Initialize service
    service = PromptHistoryService();
  });

  tearDown(() {
    AuthService.mockInstance = null;
  });

  group('PromptHistoryService', () {
    test('should not save if user is not logged in', () async {
      mockAuthService.currentUser = null;

      await service.addPrompt('test prompt');

      final history = await service.getHistory();
      expect(history, isEmpty);
    });

    test('should save prompt for logged in user', () async {
      final user = MockGoogleSignInAccount('test@example.com');
      mockAuthService.setCurrentUser(user);

      await service.addPrompt('test prompt');

      final history = await service.getHistory();
      expect(history, ['test prompt']);
    });

    test('should not save empty prompt', () async {
      final user = MockGoogleSignInAccount('test@example.com');
      mockAuthService.setCurrentUser(user);

      await service.addPrompt('   ');

      final history = await service.getHistory();
      expect(history, isEmpty);
    });

    test('should deduplicate prompts (move to end)', () async {
      final user = MockGoogleSignInAccount('test@example.com');
      mockAuthService.setCurrentUser(user);

      await service.addPrompt('one');
      await service.addPrompt('two');
      await service.addPrompt('one'); // Duplicate

      final history = await service.getHistory();
      expect(history, ['two', 'one']); // 'one' moved to end
    });

    test('should separate history by user email', () async {
      // User 1
      final user1 = MockGoogleSignInAccount('user1@example.com');
      mockAuthService.setCurrentUser(user1);
      await service.addPrompt('prompt1');

      // User 2
      final user2 = MockGoogleSignInAccount('user2@example.com');
      mockAuthService.setCurrentUser(user2);
      await service.addPrompt('prompt2');

      // Check User 1 again
      mockAuthService.setCurrentUser(user1);
      final history1 = await service.getHistory();
      expect(history1, ['prompt1']);

      // Check User 2 again
      mockAuthService.setCurrentUser(user2);
      final history2 = await service.getHistory();
      expect(history2, ['prompt2']);
    });

    test('should limit history size', () async {
      final user = MockGoogleSignInAccount('test@example.com');
      mockAuthService.setCurrentUser(user);

      // Add 60 prompts
      for (var i = 0; i < 60; i++) {
        await service.addPrompt('prompt $i');
      }

      final history = await service.getHistory();
      expect(history.length, 50); // Max size
      expect(history.last, 'prompt 59');
      expect(history.first, 'prompt 10'); // Oldest kept (0-9 removed)
    });
  });
}
