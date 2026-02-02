import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/services/auth_service.dart';

void main() {
  group('AuthService Guest Login Tests', () {
    late AuthService auth;

    setUp(() {
      // Get the singleton instance
      auth = AuthService.instance;
      // Reset state if possible, though AuthService doesn't have a full reset,
      // we can call loginAsGuest and then check state.
    });

    test('loginAsGuest updates state correctly', () {
      // Given the initial state (might be authenticated or not depending on other tests)

      // When logging in as guest
      auth.loginAsGuest();

      // Then
      expect(auth.isAuthenticated, isTrue);
      expect(auth.isAuthEnabled, isFalse);
      expect(auth.isLoading, isFalse);
      expect(auth.currentUser, isNull);
    });

    test('getAuthHeaders returns bypass token in guest mode', () async {
      // When in guest mode
      auth.loginAsGuest();

      // Then
      final headers = await auth.getAuthHeaders();
      expect(headers['Authorization'], 'Bearer dev-mode-bypass-token');
    });
  });
}
