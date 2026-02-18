import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import '../utils/isolate_helper.dart';
import 'auth_service.dart';
import 'service_config.dart';

Map<String, dynamic> _parseJsonMap(String json) =>
    jsonDecode(json) as Map<String, dynamic>;

/// Model representing a session message.
class SessionMessage {
  final String role;
  final String content;
  final String timestamp;
  final Map<String, dynamic>? metadata;

  const SessionMessage({
    required this.role,
    required this.content,
    required this.timestamp,
    this.metadata,
  });

  factory SessionMessage.fromJson(Map<String, dynamic> json) {
    return SessionMessage(
      role: json['role'] as String,
      content: json['content'] as String,
      // Robustly handle timestamp (can be double from python or string)
      timestamp: json['timestamp']?.toString() ?? '',
      metadata: json['metadata'] as Map<String, dynamic>?,
    );
  }

  Map<String, dynamic> toJson() => {
    'role': role,
    'content': content,
    'timestamp': timestamp,
    if (metadata != null) 'metadata': metadata,
  };
}

/// Model representing a session summary (for listing).
class SessionSummary {
  final String id;
  final String userId;
  final String appName;
  final String? title;
  final String? projectId;
  final double? createdAt;
  final double? updatedAt;
  final int messageCount;
  final String? preview;

  const SessionSummary({
    required this.id,
    required this.userId,
    required this.appName,
    this.title,
    this.projectId,
    this.createdAt,
    this.updatedAt,
    required this.messageCount,
    this.preview,
  });

  factory SessionSummary.fromJson(Map<String, dynamic> json) {
    return SessionSummary(
      id: json['id'] as String,
      userId: json['user_id'] as String? ?? 'default',
      appName: json['app_name'] as String? ?? 'sre_agent',
      title: json['title'] as String?,
      projectId: json['project_id'] as String?,
      createdAt: (json['created_at'] as num?)?.toDouble(),
      updatedAt: (json['updated_at'] as num?)?.toDouble(),
      messageCount: json['message_count'] as int? ?? 0,
      preview: json['preview'] as String?,
    );
  }

  /// Get display title (title or preview or "New Session")
  String get displayTitle => title ?? preview ?? 'New Investigation';

  /// Get formatted date string
  String get formattedDate {
    if (updatedAt == null) return '';
    try {
      final date = DateTime.fromMillisecondsSinceEpoch(
        (updatedAt! * 1000).toInt(),
      );
      final now = DateTime.now();
      final diff = now.difference(date);
      if (diff.inDays == 0) {
        return '${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';
      } else if (diff.inDays == 1) {
        return 'Yesterday';
      } else if (diff.inDays < 7) {
        return '${diff.inDays} days ago';
      } else {
        return '${date.month}/${date.day}/${date.year}';
      }
    } catch (e) {
      return '';
    }
  }
}

/// Model representing a full session.
class Session {
  final String id;
  final String userId;
  final Map<String, dynamic>? state;
  final double? lastUpdateTime;
  final List<SessionMessage> messages;

  const Session({
    required this.id,
    required this.userId,
    this.state,
    this.lastUpdateTime,
    required this.messages,
  });

  factory Session.fromJson(Map<String, dynamic> json) {
    return Session(
      id: json['id'] as String,
      userId: json['user_id'] as String? ?? 'default',
      state: json['state'] as Map<String, dynamic>?,
      lastUpdateTime: (json['last_update_time'] as num?)?.toDouble(),
      messages:
          (json['messages'] as List<dynamic>?)
              ?.map((m) => SessionMessage.fromJson(m as Map<String, dynamic>))
              .toList() ??
          [],
    );
  }

  String? get title => state?['title'] as String?;
  String? get projectId => state?['project_id'] as String?;

  String get displayTitle {
    if (title != null && title!.isNotEmpty) return title!;
    if (messages.isNotEmpty) {
      final firstMsg = messages.first.content;
      return firstMsg.length > 50
          ? '${firstMsg.substring(0, 50)}...'
          : firstMsg;
    }
    return 'New Investigation';
  }
}

/// Service for managing conversation sessions.
class SessionService {
  static SessionService? _mockInstance;
  static SessionService get instance => _mockInstance ?? _internalInstance;
  static final SessionService _internalInstance = SessionService._internal();

  factory SessionService() => instance;

  @visibleForTesting
  static set mockInstance(SessionService? mock) => _mockInstance = mock;

  SessionService._internal();

  /// Returns the base API URL based on the runtime environment.
  String get _baseUrl => ServiceConfig.baseUrl;

  final ValueNotifier<List<SessionSummary>> _sessions = ValueNotifier([]);
  final ValueNotifier<String?> _currentSessionId = ValueNotifier(null);
  final ValueNotifier<bool> _isLoading = ValueNotifier(false);
  final ValueNotifier<String?> _error = ValueNotifier(null);

  /// List of session summaries.
  ValueListenable<List<SessionSummary>> get sessions => _sessions;

  /// Current session ID.
  ValueListenable<String?> get currentSessionId => _currentSessionId;

  /// Whether sessions are currently being loaded.
  ValueListenable<bool> get isLoading => _isLoading;

  /// Error message if session fetch failed.
  ValueListenable<String?> get error => _error;

  /// Fetches the list of sessions from the backend.
  Future<void> fetchHistory({bool force = false, String? userId}) async {
    if (_isLoading.value && !force) return;
    await fetchSessions(userId: userId);
  }

  /// Fetches the list of sessions from the backend.
  Future<void> fetchSessions({String? userId}) async {
    _isLoading.value = true;
    _error.value = null;

    try {
      final effectiveUserId =
          userId ?? AuthService().currentUser?.email ?? 'default';

      final client = await AuthService().getAuthenticatedClient();
      try {
        final response = await client
            .get(Uri.parse('$_baseUrl/api/sessions?user_id=$effectiveUserId'))
            .timeout(ServiceConfig.defaultTimeout);

        if (response.statusCode == 200) {
          final data = await AppIsolate.run(_parseJsonMap, response.body);
          final sessionList = data['sessions'] as List<dynamic>? ?? [];

          _sessions.value = sessionList
              .map((s) => SessionSummary.fromJson(s as Map<String, dynamic>))
              .toList();
        } else {
          _error.value = 'Failed to fetch sessions: ${response.statusCode}';
        }
      } finally {
        client.close();
      }
    } catch (e, stack) {
      _error.value = 'Error fetching sessions: $e';
      debugPrint('SessionService error: $e\n$stack');
    } finally {
      _isLoading.value = false;
    }
  }

  /// Creates a new session.
  Future<Session?> createSession({
    String? userId,
    String? title,
    String? projectId,
  }) async {
    try {
      final effectiveUserId =
          userId ?? AuthService().currentUser?.email ?? 'default';

      final client = await AuthService().getAuthenticatedClient();
      try {
        final response = await client
            .post(
              Uri.parse('$_baseUrl/api/sessions'),
              headers: {'Content-Type': 'application/json'},
              body: jsonEncode({
                'user_id': effectiveUserId,
                // ignore: use_null_aware_elements
                if (title != null) 'title': title,
                // ignore: use_null_aware_elements
                if (projectId != null) 'project_id': projectId,
              }),
            )
            .timeout(ServiceConfig.defaultTimeout);

        if (response.statusCode == 200) {
          final data = await AppIsolate.run(_parseJsonMap, response.body);
          final session = Session.fromJson(data);

          // Set as current session
          _currentSessionId.value = session.id;

          // Refresh sessions list
          await fetchHistory(userId: effectiveUserId, force: true);

          return session;
        } else {
          _error.value = 'Failed to create session: ${response.statusCode}';
          return null;
        }
      } finally {
        client.close();
      }
    } catch (e) {
      _error.value = 'Error creating session: $e';
      debugPrint('SessionService error: $e');
      return null;
    }
  }

  /// Gets a session by ID.
  Future<Session?> getSession(String sessionId) async {
    try {
      final client = await AuthService().getAuthenticatedClient();
      try {
        final effectiveUserId = AuthService().currentUser?.email ?? 'default';

        final response = await client
            .get(
              Uri.parse(
                '$_baseUrl/api/sessions/$sessionId?user_id=$effectiveUserId',
              ),
            )
            .timeout(ServiceConfig.defaultTimeout);

        if (response.statusCode == 200) {
          final data = await AppIsolate.run(_parseJsonMap, response.body);
          return Session.fromJson(data);
        } else {
          _error.value = 'Failed to get session: ${response.statusCode}';
          return null;
        }
      } finally {
        client.close();
      }
    } catch (e) {
      debugPrint('Error getting session details: $e');
      return null;
    }
  }

  /// Deletes a session.
  Future<bool> deleteSession(String sessionId) async {
    try {
      final effectiveUserId = AuthService().currentUser?.email ?? 'default';

      final client = await AuthService().getAuthenticatedClient();
      try {
        final response = await client
            .delete(
              Uri.parse(
                '$_baseUrl/api/sessions/$sessionId?user_id=$effectiveUserId',
              ),
            )
            .timeout(ServiceConfig.defaultTimeout);

        if (response.statusCode == 200) {
          // Remove from list
          _sessions.value = _sessions.value
              .where((s) => s.id != sessionId)
              .toList();

          // Clear current session if deleted
          if (_currentSessionId.value == sessionId) {
            _currentSessionId.value = null;
          }

          return true;
        } else {
          _error.value = 'Failed to delete session: ${response.statusCode}';
          return false;
        }
      } finally {
        client.close();
      }
    } catch (e) {
      _error.value = 'Error deleting session: $e';
      debugPrint('SessionService error: $e');
      return false;
    }
  }

  /// Renames a session.
  Future<bool> renameSession(String sessionId, String newTitle) async {
    try {
      final client = await AuthService().getAuthenticatedClient();
      try {
        final response = await client
            .patch(
              Uri.parse('$_baseUrl/api/sessions/$sessionId'),
              headers: {'Content-Type': 'application/json'},
              body: jsonEncode({'title': newTitle}),
            )
            .timeout(ServiceConfig.defaultTimeout);

        if (response.statusCode == 200) {
          // Update list locally
          final updatedSessions = _sessions.value.map((s) {
            if (s.id == sessionId) {
              return SessionSummary(
                id: s.id,
                userId: s.userId,
                appName: s.appName,
                title: newTitle,
                projectId: s.projectId,
                createdAt: s.createdAt,
                updatedAt: s.updatedAt,
                messageCount: s.messageCount,
                preview: s.preview,
              );
            }
            return s;
          }).toList();

          _sessions.value = updatedSessions;
          return true;
        } else {
          _error.value = 'Failed to rename session: ${response.statusCode}';
          return false;
        }
      } finally {
        client.close();
      }
    } catch (e) {
      _error.value = 'Error renaming session: $e';
      debugPrint('SessionService error: $e');
      return false;
    }
  }

  /// Sets the current session ID.
  void setCurrentSession(String? sessionId) {
    _currentSessionId.value = sessionId;
  }

  /// Starts a new session (clears current).
  Future<void> startNewSession() async {
    _currentSessionId.value = null;
  }

  void dispose() {
    _sessions.dispose();
    _currentSessionId.dispose();
    _isLoading.dispose();
    _error.dispose();
  }
}
