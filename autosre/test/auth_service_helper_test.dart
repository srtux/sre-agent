import 'package:flutter_test/flutter_test.dart';
import 'package:autosre/services/auth_service.dart';

void main() {
  group('AuthService Helper Tests', () {
    test('extractTokenFromHeaders returns null for empty headers', () {
      final headers = <String, String>{};
      expect(AuthService.extractTokenFromHeaders(headers), null);
    });

    test(
      'extractTokenFromHeaders returns null for headers without Authorization',
      () {
        final headers = {'Content-Type': 'application/json'};
        expect(AuthService.extractTokenFromHeaders(headers), null);
      },
    );

    test('extractTokenFromHeaders parses Bearer token correctly', () {
      final headers = {'Authorization': 'Bearer 123456789'};
      expect(AuthService.extractTokenFromHeaders(headers), '123456789');
    });

    test('extractTokenFromHeaders returns raw header if not Bearer', () {
      final headers = {'Authorization': 'Basic 123456'};
      expect(AuthService.extractTokenFromHeaders(headers), 'Basic 123456');
    });

    test(
      'extractTokenFromHeaders handles different key casing if map is not case insensitive (standard map)',
      () {
        // Note: Map<String, String> is case sensitive by default in Dart.
        // AuthService expects specific 'Authorization' key as per GoogleSignIn spec.
        final headers = {'authorization': 'Bearer lowercase'};
        expect(
          AuthService.extractTokenFromHeaders(headers),
          null,
        ); // Should be null as we look for 'Authorization'
      },
    );
  });
}
