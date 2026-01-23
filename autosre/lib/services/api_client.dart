import 'package:http/http.dart' as http;
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

  ProjectInterceptorClient(this._inner, {ProjectService? projectService})
    : _projectService = projectService ?? ProjectService();

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final projectId = _projectService.selectedProjectId;

    if (projectId == null || projectId.isEmpty) {
      // Don't intercept health checks or project list requests
      if (request.url.path.contains('/health') ||
          request.url.path.contains('/api/config') ||
          request.url.path.contains('/agent') ||
          request.url.path.contains('/api/tools/projects/list')) {
        return _inner.send(request);
      }
      throw ProjectNotSelectedException();
    }

    // 1. Add as Header
    request.headers['X-GCP-Project-ID'] = projectId;

    // 2. Append as Query Parameter for GET requests or as fallback
    // 2. Append as Query Parameter for GET requests or as fallback
    // (Logic removed as we primarily use headers and modifying BaseRequest URL is complex)

    // Note: We can't easily change the URL of a BaseRequest once created if it's already "frozen"
    // but we can create a new request if needed. However, since we are using headers as preferred,
    // the query param is a secondary measure. Most ADK tools handle bodies/query params.

    return _inner.send(request);
  }

  @override
  void close() {
    _inner.close();
    super.close();
  }
}
