import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:autosre/services/api_client.dart';
import 'package:autosre/services/auth_service.dart';
import 'package:autosre/services/project_service.dart';
import 'package:autosre/services/service_config.dart';
import '../test_helper.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('ProjectNotSelectedException', () {
    test('has default message', () {
      final ex = ProjectNotSelectedException();
      expect(ex.message, contains('No GCP Project'));
      expect(ex.toString(), contains('ProjectNotSelectedException'));
    });

    test('accepts custom message', () {
      final ex = ProjectNotSelectedException('Custom error');
      expect(ex.message, 'Custom error');
      expect(ex.toString(), contains('Custom error'));
    });
  });

  group('ProjectInterceptorClient', () {
    late MockAuthService mockAuth;
    late MockProjectService mockProject;

    setUp(() {
      mockAuth = MockAuthService();
      AuthService.mockInstance = mockAuth;
      mockProject = MockProjectService();
    });

    tearDown(() {
      AuthService.mockInstance = null;
      ProjectService.mockInstance = null;
    });

    test('injects X-Correlation-ID header', () async {
      String? correlationId;
      final inner = MockClient((req) async {
        correlationId = req.headers['X-Correlation-ID'];
        return http.Response('{}', 200);
      });

      final client = ProjectInterceptorClient(inner,
          projectService: mockProject);
      await client.get(Uri.parse('http://localhost/test'));

      expect(correlationId, isNotNull);
      expect(correlationId!.length, greaterThan(0));
      client.close();
    });

    test('preserves existing X-Correlation-ID header', () async {
      String? correlationId;
      final inner = MockClient((req) async {
        correlationId = req.headers['X-Correlation-ID'];
        return http.Response('{}', 200);
      });

      final client = ProjectInterceptorClient(inner,
          projectService: mockProject);
      await client.get(
        Uri.parse('http://localhost/test'),
        headers: {'X-Correlation-ID': 'existing-id'},
      );

      expect(correlationId, 'existing-id');
      client.close();
    });

    test('does not inject project ID when none selected', () async {
      String? projectHeader;
      final inner = MockClient((req) async {
        projectHeader = req.headers['X-GCP-Project-ID'];
        return http.Response('{}', 200);
      });

      final client = ProjectInterceptorClient(inner,
          projectService: mockProject);
      await client.get(Uri.parse('http://localhost/test'));

      expect(projectHeader, isNull);
      client.close();
    });

    test('rethrows on network error', () async {
      final inner = MockClient((req) async {
        throw http.ClientException('Connection refused');
      });

      final client = ProjectInterceptorClient(inner,
          projectService: mockProject);

      expect(
        () => client.get(Uri.parse('http://localhost/test')),
        throwsA(isA<http.ClientException>()),
      );
      client.close();
    });
  });

  group('ServiceConfig', () {
    test('has correct default timeout', () {
      expect(ServiceConfig.defaultTimeout, const Duration(seconds: 30));
    });

    test('has correct query timeout', () {
      expect(ServiceConfig.queryTimeout, const Duration(seconds: 60));
    });

    test('has correct health check timeout', () {
      expect(ServiceConfig.healthCheckTimeout, const Duration(seconds: 10));
    });

    test('has correct token lifetime', () {
      expect(ServiceConfig.tokenLifetime, const Duration(minutes: 55));
    });

    test('has correct token refresh buffer', () {
      expect(ServiceConfig.tokenRefreshBuffer, const Duration(minutes: 5));
    });
  });
}
