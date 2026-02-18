import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../utils/isolate_helper.dart';
import 'auth_service.dart';
import 'service_config.dart';

Map<String, dynamic> _parseJsonMap(String json) =>
    jsonDecode(json) as Map<String, dynamic>;

/// Model representing a GCP project.
class GcpProject {
  final String projectId;
  final String? displayName;
  final String? projectNumber;

  const GcpProject({
    required this.projectId,
    this.displayName,
    this.projectNumber,
  });

  factory GcpProject.fromJson(Map<String, dynamic> json) {
    return GcpProject(
      projectId: json['project_id'] as String,
      displayName: json['display_name'] as String?,
      projectNumber: json['project_number'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
    'project_id': projectId,
    if (displayName != null) 'display_name': displayName,
    if (projectNumber != null) 'project_number': projectNumber,
  };

  /// Returns display name if available, otherwise project ID.
  String get name => displayName ?? projectId;

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is GcpProject && other.projectId == projectId;
  }

  @override
  int get hashCode => projectId.hashCode;
}

/// Factory for creating authenticated HTTP clients.
typedef ClientFactory = Future<http.Client> Function();

/// Service for managing GCP project selection and fetching.
class ProjectService {
  static ProjectService? _mockInstance;
  static ProjectService get instance => _mockInstance ?? _internalInstance;
  static final ProjectService _internalInstance = ProjectService._internal();

  @visibleForTesting
  static set mockInstance(ProjectService? mock) => _mockInstance = mock;

  /// Default factory returns the shared singleton.
  factory ProjectService() => instance;

  /// Creates a new, non-singleton instance.
  ///
  /// Use this in tests or short-lived contexts where you want an
  /// isolated instance that can be safely disposed without affecting
  /// the global singleton.
  ProjectService.newInstance({ClientFactory? clientFactory})
    : this._internal(clientFactory: clientFactory);

  ProjectService._internal({ClientFactory? clientFactory})
    : _clientFactory =
          clientFactory ??
          (() async => await AuthService.instance.getAuthenticatedClient());

  final ClientFactory _clientFactory;

  /// Returns the base API URL from centralized config.
  String get _baseUrl => ServiceConfig.baseUrl;

  /// Returns the projects API URL based on the runtime environment.
  String get _projectsUrl => '$_baseUrl/api/tools/projects/list';

  /// Returns the preferences API URL.
  String get _preferencesUrl => '$_baseUrl/api/preferences/project';

  /// Returns the recent projects API URL.
  String get _recentProjectsUrl => '$_baseUrl/api/preferences/projects/recent';

  /// Returns the starred projects API URL.
  String get _starredProjectsUrl =>
      '$_baseUrl/api/preferences/projects/starred';

  /// Returns the starred toggle API URL.
  String get _starredToggleUrl =>
      '$_baseUrl/api/preferences/projects/starred/toggle';

  final ValueNotifier<List<GcpProject>> _projects = ValueNotifier([]);
  final ValueNotifier<List<GcpProject>> _recentProjects = ValueNotifier([]);
  final ValueNotifier<List<GcpProject>> _starredProjects = ValueNotifier([]);

  final ValueNotifier<GcpProject?> _selectedProject = ValueNotifier(null);
  final ValueNotifier<bool> _isLoading = ValueNotifier(false);
  final ValueNotifier<String?> _error = ValueNotifier(null);

  /// Signals that no previously-saved project was found and the user
  /// should select one.
  final ValueNotifier<bool> _needsProjectSelection = ValueNotifier(false);

  /// List of available projects.
  ValueListenable<List<GcpProject>> get projects => _projects;

  /// List of recent projects.
  ValueListenable<List<GcpProject>> get recentProjects => _recentProjects;

  /// List of starred (pinned) projects.
  ValueListenable<List<GcpProject>> get starredProjects => _starredProjects;

  /// Currently selected project.
  ValueListenable<GcpProject?> get selectedProject => _selectedProject;

  /// Whether projects are currently being loaded.
  ValueListenable<bool> get isLoading => _isLoading;

  /// Error message if project fetch failed.
  ValueListenable<String?> get error => _error;

  /// Whether the user needs to select a project (no saved project found).
  ValueListenable<bool> get needsProjectSelection => _needsProjectSelection;

  /// The selected project ID, or null if none selected.
  String? get selectedProjectId => _selectedProject.value?.projectId;

  /// Loads the previously selected project from backend storage.
  Future<void> loadSavedProject() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final savedProjectId = prefs.getString('selected_project_id');

      if (savedProjectId != null && savedProjectId.isNotEmpty) {
        // Find in projects list or create new
        final project = _projects.value.firstWhere(
          (p) => p.projectId == savedProjectId,
          orElse: () => GcpProject(projectId: savedProjectId),
        );
        _selectedProject.value = project;
        return;
      }

      // Fallback to backend preference if local not found (optional, depending on migration)
      final client = await _clientFactory();
      try {
        final response = await client
            .get(Uri.parse(_preferencesUrl))
            .timeout(ServiceConfig.defaultTimeout);

        if (response.statusCode == 200) {
          final data = await AppIsolate.run(_parseJsonMap, response.body);
          final backendProjectId = data['project_id'] as String?;

          if (backendProjectId != null && backendProjectId.isNotEmpty) {
            // Find in projects list or create new
            final project = _projects.value.firstWhere(
              (p) => p.projectId == backendProjectId,
              orElse: () => GcpProject(projectId: backendProjectId),
            );
            _selectedProject.value = project;
          }
        }
      } finally {
        client.close();
      }
    } on TimeoutException catch (_) {
      _error.value = 'Request timed out while loading project preferences';
      debugPrint('Timeout loading saved project');
    } catch (e) {
      _error.value = 'Error loading saved project: $e';
      debugPrint('Error loading saved project: $e');
    }
  }

  /// Saves the selected project to backend storage.
  Future<void> _saveSelectedProject(String projectId) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('selected_project_id', projectId);

      // Also try to save to backend
      final client = await _clientFactory();
      try {
        await client
            .post(
              Uri.parse(_preferencesUrl),
              headers: {'Content-Type': 'application/json'},
              body: jsonEncode({'project_id': projectId}),
            )
            .timeout(ServiceConfig.defaultTimeout);
      } finally {
        client.close();
      }
    } catch (e) {
      debugPrint('Error saving project selection: $e');
    }
  }

  /// Loads recent projects from backend storage.
  Future<void> _loadRecentProjects() async {
    try {
      final client = await _clientFactory();
      try {
        final response = await client
            .get(Uri.parse(_recentProjectsUrl))
            .timeout(ServiceConfig.defaultTimeout);

        if (response.statusCode == 200) {
          final data = await AppIsolate.run(_parseJsonMap, response.body);
          if (data['projects'] != null) {
            final list = (data['projects'] as List)
                .map((p) => GcpProject.fromJson(p as Map<String, dynamic>))
                .toList();
            _recentProjects.value = list;
          }
        }
      } finally {
        client.close();
      }
    } catch (e) {
      debugPrint('Error loading recent projects: $e');
    }
  }

  /// Saves recent projects list to backend storage.
  Future<void> _saveRecentProjects() async {
    try {
      final client = await _clientFactory();
      try {
        await client
            .post(
              Uri.parse(_recentProjectsUrl),
              headers: {'Content-Type': 'application/json'},
              body: jsonEncode({
                'projects': _recentProjects.value
                    .map((p) => p.toJson())
                    .toList(),
              }),
            )
            .timeout(ServiceConfig.defaultTimeout);
      } finally {
        client.close();
      }
    } catch (e) {
      debugPrint('Error saving recent projects: $e');
    }
  }

  /// Loads starred projects from backend storage.
  Future<void> _loadStarredProjects() async {
    try {
      final client = await _clientFactory();
      try {
        final response = await client
            .get(Uri.parse(_starredProjectsUrl))
            .timeout(ServiceConfig.defaultTimeout);

        if (response.statusCode == 200) {
          final data = await AppIsolate.run(_parseJsonMap, response.body);
          if (data['projects'] != null) {
            final list = (data['projects'] as List)
                .map((p) => GcpProject.fromJson(p as Map<String, dynamic>))
                .toList();
            _starredProjects.value = list;
          }
        }
      } finally {
        client.close();
      }
    } catch (e) {
      debugPrint('Error loading starred projects: $e');
    }
  }

  /// Returns true if the given project is starred.
  bool isStarred(String projectId) {
    return _starredProjects.value.any((p) => p.projectId == projectId);
  }

  /// Toggles the starred state of a project.
  Future<void> toggleStar(GcpProject project) async {
    final wasStarred = isStarred(project.projectId);

    // Optimistic local update
    if (wasStarred) {
      _starredProjects.value = _starredProjects.value
          .where((p) => p.projectId != project.projectId)
          .toList();
    } else {
      _starredProjects.value = [..._starredProjects.value, project];
    }

    // Persist to backend
    try {
      final client = await _clientFactory();
      try {
        await client
            .post(
              Uri.parse(_starredToggleUrl),
              headers: {'Content-Type': 'application/json'},
              body: jsonEncode({
                'project_id': project.projectId,
                'display_name': project.displayName ?? project.projectId,
                'starred': !wasStarred,
              }),
            )
            .timeout(ServiceConfig.defaultTimeout);
      } finally {
        client.close();
      }
    } catch (e) {
      debugPrint('Error toggling star: $e');
      // Revert on failure
      await _loadStarredProjects();
    }
  }

  /// Fetches the list of available GCP projects from the backend.
  Future<void> fetchProjects({String? query}) async {
    _isLoading.value = true;
    _error.value = null;

    try {
      final client = await _clientFactory();
      try {
        final uri = query != null && query.isNotEmpty
            ? Uri.parse('$_projectsUrl?query=${Uri.encodeComponent(query)}')
            : Uri.parse(_projectsUrl);

        final response = await client
            .get(uri)
            .timeout(ServiceConfig.defaultTimeout);

        if (response.statusCode == 200) {
          final data = await AppIsolate.run(_parseJsonMap, response.body);

          // Handle different response formats:
          // 1. Plain list: [{"project_id": ...}, ...]
          // 2. Wrapped: {"projects": [...]}
          // 3. BaseToolResponse envelope
          List<dynamic> projectList;
          if (data['projects'] != null) {
            projectList = data['projects'] as List;
          } else if (data['result'] is Map &&
              data['result']['projects'] != null) {
            projectList = data['result']['projects'] as List;
          } else {
            projectList = [];
          }

          final projects = projectList
              .map((p) => GcpProject.fromJson(p as Map<String, dynamic>))
              .toList();

          _projects.value = projects;

          // Load saved project preference first
          await loadSavedProject();

          // Load recent and starred projects
          await _loadRecentProjects();
          await _loadStarredProjects();

          // Signal that user needs to select a project if none was saved
          if (_selectedProject.value == null) {
            _needsProjectSelection.value = true;
          }
        } else {
          _error.value = 'Failed to fetch projects: ${response.statusCode}';
        }
      } finally {
        client.close();
      }
    } catch (e, stack) {
      _error.value = 'Error fetching projects: $e';
      debugPrint('ProjectService error: $e\n$stack');
    } finally {
      _isLoading.value = false;
    }
  }

  /// Selects a project by its ID.
  void selectProject(String projectId) {
    final project = _projects.value.firstWhere(
      (p) => p.projectId == projectId,
      orElse: () => GcpProject(projectId: projectId),
    );
    selectProjectInstance(project);
  }

  /// Selects a project directly.
  void selectProjectInstance(GcpProject? project) {
    _selectedProject.value = project;
    // Clear the "needs selection" flag once a project is chosen
    _needsProjectSelection.value = false;
    // Persist selection
    if (project != null) {
      _saveSelectedProject(project.projectId);

      // Update recent projects
      final currentRecent = List<GcpProject>.from(_recentProjects.value);
      // Remove if exists to move to top
      currentRecent.removeWhere((p) => p.projectId == project.projectId);
      // Insert at top
      currentRecent.insert(0, project);
      // Limit to 10
      if (currentRecent.length > 10) {
        currentRecent.removeRange(10, currentRecent.length);
      }
      _recentProjects.value = currentRecent;
      _saveRecentProjects();
    }
  }

  /// Clears the current selection.
  void clearSelection() {
    _selectedProject.value = null;
  }

  void dispose() {
    // Only allow disposal for non-singleton instances to avoid disposing
    // global notifiers that may still be in use elsewhere.
    if (identical(this, _internalInstance)) {
      debugPrint('ProjectService.dispose() called on singleton; ignoring.');
      return;
    }

    _projects.dispose();
    _recentProjects.dispose();
    _starredProjects.dispose();
    _selectedProject.dispose();
    _needsProjectSelection.dispose();
    _isLoading.dispose();
    _error.dispose();
  }
}
