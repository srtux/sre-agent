import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'auth_service.dart';

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

  /// HTTP request timeout duration.
  static const Duration _requestTimeout = Duration(seconds: 30);

  /// Returns the base API URL based on the runtime environment.
  String get _baseUrl {
    if (kDebugMode) {
      return 'http://127.0.0.1:8001';
    }
    return '';
  }

  /// Returns the projects API URL based on the runtime environment.
  String get _projectsUrl => '$_baseUrl/api/tools/projects/list';

  /// Returns the preferences API URL.
  String get _preferencesUrl => '$_baseUrl/api/preferences/project';

  /// Returns the recent projects API URL.
  String get _recentProjectsUrl => '$_baseUrl/api/preferences/projects/recent';

  final ValueNotifier<List<GcpProject>> _projects = ValueNotifier([]);
  final ValueNotifier<List<GcpProject>> _recentProjects = ValueNotifier([]);

  final ValueNotifier<GcpProject?> _selectedProject = ValueNotifier(null);
  final ValueNotifier<bool> _isLoading = ValueNotifier(false);
  final ValueNotifier<String?> _error = ValueNotifier(null);

  /// List of available projects.
  ValueListenable<List<GcpProject>> get projects => _projects;

  /// List of recent projects.
  ValueListenable<List<GcpProject>> get recentProjects => _recentProjects;

  /// Currently selected project.
  ValueListenable<GcpProject?> get selectedProject => _selectedProject;

  /// Whether projects are currently being loaded.
  ValueListenable<bool> get isLoading => _isLoading;

  /// Error message if project fetch failed.
  ValueListenable<String?> get error => _error;

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
      final response = await client
          .get(Uri.parse(_preferencesUrl))
          .timeout(_requestTimeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
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
      await client
          .post(
            Uri.parse(_preferencesUrl),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'project_id': projectId}),
          )
          .timeout(_requestTimeout);
    } catch (e) {
      debugPrint('Error saving project selection: $e');
    }
  }

  /// Loads recent projects from backend storage.
  Future<void> _loadRecentProjects() async {
    try {
      final client = await _clientFactory();
      final response = await client
          .get(Uri.parse(_recentProjectsUrl))
          .timeout(_requestTimeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data is Map && data['projects'] != null) {
          final list = (data['projects'] as List)
              .map((p) => GcpProject.fromJson(p as Map<String, dynamic>))
              .toList();
          _recentProjects.value = list;
        }
      }
    } catch (e) {
      debugPrint('Error loading recent projects: $e');
      // Non-critical, just log
    }
  }

  /// Saves recent projects list to backend storage.
  Future<void> _saveRecentProjects() async {
    try {
      final client = await _clientFactory();
      await client
          .post(
            Uri.parse(_recentProjectsUrl),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({
              'projects': _recentProjects.value.map((p) => p.toJson()).toList(),
            }),
          )
          .timeout(_requestTimeout);
    } catch (e) {
      debugPrint('Error saving recent projects: $e');
    }
  }

  /// Fetches the list of available GCP projects from the backend.
  Future<void> fetchProjects({String? query}) async {
    debugPrint('🔄 ProjectService: Fetching projects... query=$query');
    // If we are searching (query != null), we shouldn't block on existing loading state
    // because user might be typing fast. But for initial load we might want to debounce.
    // Actually, simple way: cancel previous request? Dart http doesn't easily support cancellation tokens.
    // For now we just let it race, but we update URL.

    // Note: If you want to cancel, you'd need a new client per request or use a package like dio.
    // For simplicity, we just set loading true.

    _isLoading.value = true;
    _error.value = null;

    try {
      debugPrint('🔑 ProjectService: Getting authenticated client...');
      final client = await _clientFactory();

      final uri = query != null && query.isNotEmpty
          ? Uri.parse('$_projectsUrl?query=${Uri.encodeComponent(query)}')
          : Uri.parse(_projectsUrl);

      debugPrint('📡 ProjectService: Sending request to $uri');
      final response = await client.get(uri).timeout(_requestTimeout);

      debugPrint('📥 ProjectService: Response status ${response.statusCode}');
      if (response.statusCode != 200) {
        debugPrint('❌ ProjectService: Error body: ${response.body}');
      }

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        debugPrint('📦 ProjectService: Parsed data: $data');

        // Handle different response formats
        List<dynamic> projectList;
        if (data is List) {
          projectList = data;
        } else if (data is Map && data['projects'] != null) {
          projectList = data['projects'] as List;
        } else {
          projectList = [];
        }

        final projects = projectList
            .map((p) => GcpProject.fromJson(p as Map<String, dynamic>))
            .toList();

        _projects.value = projects;
        debugPrint('✅ ProjectService: Loaded ${projects.length} projects');

        // Load saved project preference first
        await loadSavedProject();

        // Load recent projects
        await _loadRecentProjects();

        // Auto-select first project if still none selected
        if (_selectedProject.value == null && projects.isNotEmpty) {
          selectProjectInstance(projects.first);
        }
      } else {
        _error.value = 'Failed to fetch projects: ${response.statusCode}';
      }
    } catch (e, stack) {
      _error.value = 'Error fetching projects: $e';
      debugPrint('ProjectService error: $e\n$stack');
      debugPrint('🔥 ProjectService Exception: $e');
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
    _selectedProject.dispose();
    _isLoading.dispose();
    _error.dispose();
  }
}
