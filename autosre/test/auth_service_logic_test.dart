import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/services/auth_service.dart';

void main() {
  group('AuthService Structural Tests', () {
    test('AuthService singleton and constructor are working', () {
      final instance1 = AuthService.instance;
      final instance2 = AuthService();
      expect(instance1, same(instance2));
    });

    test('AuthService initial state', () {
      final auth = AuthService.instance;
      expect(auth.isAuthenticated, isFalse);
      expect(
        auth.isLoading,
        isTrue,
      ); // Initialized to true until init() finishes
      expect(auth.currentUser, isNull);
    });

    test('extractTokenFromHeaders basic parsing', () {
      final headers = {'Authorization': 'Bearer abc-123'};
      final token = AuthService.extractTokenFromHeaders(headers);
      expect(token, 'abc-123');
    });
  });
}
