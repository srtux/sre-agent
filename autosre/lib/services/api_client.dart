import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:uuid/uuid.dart';
import 'auth_service.dart';
import 'project_service.dart';
import 'service_config.dart';

/// Exception thrown when an API request is made without a selected project.
class ProjectNotSelectedException implements Exception {
  final String message;
  ProjectNotSelectedException([
    this.message =
        'No GCP Project selected. Please select a project to continue.',
  ]);
  @override
  String toString() => 'ProjectNotSelectedException: $message';
}

/// A custom HTTP client that intercepts requests to inject the selected GCP Project ID.
class ProjectInterceptorClient extends http.BaseClient {
  final http.Client _inner;
  final ProjectService _projectService;
  static const _uuid = Uuid();

  ProjectInterceptorClient(
    this._inner, {
    ProjectService? projectService,
  }) : _projectService = projectService ?? ProjectService();

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    // 1. Fetch fresh auth headers from AuthService
    // We ALWAYS want to send the Authorization header if we have a token,
    // even for project list / health check endpoints, to ensure the backend
    // can identify the user and skip ADC fallback.
    final authHeaders = await AuthService.instance.getAuthHeaders();
    request.headers.addAll(authHeaders);

    if (kDebugMode && authHeaders.containsKey('Authorization')) {
       debugPrint('ProjectInterceptorClient: Injected Auth header');
    }

    // 2. Add User ID hint for better backend session lookup
    final userEmail = AuthService.instance.currentUser?.email;
    if (userEmail != null) {
      request.headers['X-User-ID'] = userEmail;
    }

    final projectId = _projectService.selectedProjectId;
    if (kDebugMode) {
      debugPrint('ProjectInterceptorClient: Request to ${request.url.path}, ProjectID: $projectId');
    }

    // 3. Add as Header
    if (projectId != null && projectId.isNotEmpty) {
      request.headers['X-GCP-Project-ID'] = projectId;
    }

    // 4. Correlation ID for Cross-Service Tracing
    final correlationId = request.headers['X-Correlation-ID'] ?? _uuid.v4();
    request.headers['X-Correlation-ID'] = correlationId;

    if (kDebugMode) {
      debugPrint('🌐 [API Request] ${request.method} ${request.url.path} | CorrID: $correlationId');
    }

    final stopwatch = Stopwatch()..start();
    try {
      final response = await _inner.send(request).timeout(
        ServiceConfig.defaultTimeout,
      );
      final duration = stopwatch.elapsedMilliseconds;

      if (kDebugMode) {
        debugPrint('🌐 [API Response] ${request.method} ${request.url.path} | Status: ${response.statusCode} | Duration: ${duration}ms | CorrID: $correlationId');
      }

      return response;
    } catch (e) {
      final duration = stopwatch.elapsedMilliseconds;
      if (kDebugMode) {
        debugPrint('❌ [API Error] ${request.method} ${request.url.path} | Error: $e | Duration: ${duration}ms | CorrID: $correlationId');
      }
      rethrow;
    }
  }

  @override
  void close() {
    _inner.close();
    super.close();
  }
}
