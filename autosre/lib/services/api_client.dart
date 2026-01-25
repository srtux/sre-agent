import 'dart:math';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'auth_service.dart';
import 'project_service.dart';

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
       final token = authHeaders['Authorization']!;
       debugPrint('ProjectInterceptorClient: Injected Auth header (prefix: ${token.substring(0, min(token.length, 15))}...)');
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

    return _inner.send(request);
  }

  @override
  void close() {
    _inner.close();
    super.close();
  }
}
