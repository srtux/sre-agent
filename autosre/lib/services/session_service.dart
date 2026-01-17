import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

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
      timestamp: json['timestamp'] as String,
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
  final String? title;
  final String? projectId;
  final String createdAt;
  final String updatedAt;
  final int messageCount;
  final String? preview;

  const SessionSummary({
    required this.id,
    this.title,
    this.projectId,
    required this.createdAt,
    required this.updatedAt,
    required this.messageCount,
    this.preview,
  });

  factory SessionSummary.fromJson(Map<String, dynamic> json) {
    return SessionSummary(
      id: json['id'] as String,
      title: json['title'] as String?,
      projectId: json['project_id'] as String?,
      createdAt: json['created_at'] as String,
      updatedAt: json['updated_at'] as String,
      messageCount: json['message_count'] as int? ?? 0,
      preview: json['preview'] as String?,
    );
  }

  /// Get display title (title or preview or "New Session")
  String get displayTitle => title ?? preview ?? 'New Session';
}

/// Model representing a full session.
class Session {
  final String id;
  final String userId;
  final String? title;
  final String? projectId;
  final String createdAt;
  final String updatedAt;
  final List<SessionMessage> messages;

  const Session({
    required this.id,
    required this.userId,
    this.title,
    this.projectId,
    required this.createdAt,
    required this.updatedAt,
    required this.messages,
  });

  factory Session.fromJson(Map<String, dynamic> json) {
    return Session(
      id: json['id'] as String,
      userId: json['user_id'] as String,
      title: json['title'] as String?,
      projectId: json['project_id'] as String?,
      createdAt: json['created_at'] as String,
      updatedAt: json['updated_at'] as String,
      messages: (json['messages'] as List<dynamic>?)
          ?.map((m) => SessionMessage.fromJson(m as Map<String, dynamic>))
          .toList() ?? [],
    );
  }

  String get displayTitle => title ?? (messages.isNotEmpty ? messages.first.content.substring(0, messages.first.content.length.clamp(0, 50)) : 'New Session');
}

/// Service for managing conversation sessions.
class SessionService {
  static final SessionService _instance = SessionService._internal();
  factory SessionService() => _instance;
  SessionService._internal();

  /// HTTP request timeout duration.
  static const Duration _requestTimeout = Duration(seconds: 30);

  /// Returns the base API URL based on the runtime environment.
  String get _baseUrl {
    if (kDebugMode) {
      return 'http://127.0.0.1:8001';
    }
    return '';
  }

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
  Future<void> fetchSessions({String userId = 'default'}) async {
    if (_isLoading.value) return;

    _isLoading.value = true;
    _error.value = null;

    try {
      final response = await http.get(
        Uri.parse('$_baseUrl/api/sessions?user_id=$userId'),
      ).timeout(_requestTimeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final sessionList = data['sessions'] as List<dynamic>? ?? [];

        _sessions.value = sessionList
            .map((s) => SessionSummary.fromJson(s as Map<String, dynamic>))
            .toList();
      } else {
        _error.value = 'Failed to fetch sessions: ${response.statusCode}';
      }
    } catch (e) {
      _error.value = 'Error fetching sessions: $e';
      debugPrint('SessionService error: $e');
    } finally {
      _isLoading.value = false;
    }
  }

  /// Creates a new session.
  Future<Session?> createSession({
    String userId = 'default',
    String? title,
    String? projectId,
  }) async {
    try {
      final response = await http.post(
        Uri.parse('$_baseUrl/api/sessions'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'user_id': userId,
          if (title != null) 'title': title,
          if (projectId != null) 'project_id': projectId,
        }),
      ).timeout(_requestTimeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final session = Session.fromJson(data);

        // Set as current session
        _currentSessionId.value = session.id;

        // Refresh sessions list
        await fetchSessions(userId: userId);

        return session;
      } else {
        _error.value = 'Failed to create session: ${response.statusCode}';
        return null;
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
      final response = await http.get(
        Uri.parse('$_baseUrl/api/sessions/$sessionId'),
      ).timeout(_requestTimeout);

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        return Session.fromJson(data);
      } else {
        _error.value = 'Failed to get session: ${response.statusCode}';
        return null;
      }
    } catch (e) {
      _error.value = 'Error getting session: $e';
      debugPrint('SessionService error: $e');
      return null;
    }
  }

  /// Deletes a session.
  Future<bool> deleteSession(String sessionId) async {
    try {
      final response = await http.delete(
        Uri.parse('$_baseUrl/api/sessions/$sessionId'),
      ).timeout(_requestTimeout);

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
    } catch (e) {
      _error.value = 'Error deleting session: $e';
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
