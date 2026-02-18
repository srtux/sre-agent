import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../utils/isolate_helper.dart';
import 'auth_service.dart';
import 'service_config.dart';

Map<String, dynamic> _parseJsonMap(String json) =>
    jsonDecode(json) as Map<String, dynamic>;

/// A single recent or saved query entry.
class QueryEntry {
  final String? id;
  final String query;
  final String panelType;
  final String language;
  final String? name;
  final String? timestamp;
  final String? createdAt;

  const QueryEntry({
    this.id,
    required this.query,
    required this.panelType,
    this.language = '',
    this.name,
    this.timestamp,
    this.createdAt,
  });

  factory QueryEntry.fromJson(Map<String, dynamic> json) {
    return QueryEntry(
      id: json['id'] as String?,
      query: json['query'] as String? ?? '',
      panelType: json['panel_type'] as String? ?? '',
      language: json['language'] as String? ?? '',
      name: json['name'] as String?,
      timestamp: json['timestamp'] as String?,
      createdAt: json['created_at'] as String?,
    );
  }

  Map<String, dynamic> toJson() => {
        if (id != null) 'id': id,
        'query': query,
        'panel_type': panelType,
        'language': language,
        if (name != null) 'name': name,
        if (timestamp != null) 'timestamp': timestamp,
        if (createdAt != null) 'created_at': createdAt,
      };
}

/// Service for managing recent and saved explorer queries via the backend API.
///
/// Provides caching so the UI can render instantly while background refreshes
/// keep data up to date.
class SavedQueryService extends ChangeNotifier {
  static SavedQueryService? _mockInstance;
  static SavedQueryService get instance =>
      _mockInstance ?? _internalInstance;
  static final SavedQueryService _internalInstance =
      SavedQueryService._internal();

  @visibleForTesting
  static set mockInstance(SavedQueryService? mock) => _mockInstance = mock;

  factory SavedQueryService() => instance;

  SavedQueryService._internal();

  final String _baseUrl = ServiceConfig.baseUrl;

  /// In-memory cache keyed by panel type. null = not yet loaded.
  final Map<String, List<QueryEntry>> _recentCache = {};
  final Map<String, List<QueryEntry>> _savedCache = {};

  // ---------------------------------------------------------------------------
  // Recent queries
  // ---------------------------------------------------------------------------

  /// Get recent queries for a panel, returning cached data immediately.
  List<QueryEntry> getRecentQueries(String panelType) {
    return _recentCache[panelType] ?? [];
  }

  /// Fetch recent queries from the backend and update cache.
  Future<List<QueryEntry>> fetchRecentQueries(String panelType) async {
    try {
      final uri = Uri.parse(
        '$_baseUrl/api/preferences/queries/recent?panel_type=$panelType',
      );
      final response = await _authedGet(uri);
      if (response.statusCode == 200) {
        final data = await AppIsolate.run(_parseJsonMap, response.body);
        final list = (data['queries'] as List? ?? [])
            .map((e) => QueryEntry.fromJson(e as Map<String, dynamic>))
            .toList();
        _recentCache[panelType] = list;
        notifyListeners();
        return list;
      }
    } catch (e) {
      debugPrint('SavedQueryService.fetchRecentQueries error: $e');
    }
    return _recentCache[panelType] ?? [];
  }

  /// Record a query execution (fire-and-forget for the UI).
  Future<void> addRecentQuery({
    required String query,
    required String panelType,
    String language = '',
  }) async {
    if (query.trim().isEmpty) return;

    // Optimistic local update
    final entry = QueryEntry(
      query: query,
      panelType: panelType,
      language: language,
      timestamp: DateTime.now().toUtc().toIso8601String(),
    );

    final cached = _recentCache[panelType] ?? [];
    cached.removeWhere((e) => e.query == query);
    cached.insert(0, entry);
    if (cached.length > 1000) {
      _recentCache[panelType] = cached.sublist(0, 1000);
    } else {
      _recentCache[panelType] = cached;
    }
    notifyListeners();

    // Persist to backend
    try {
      final uri = Uri.parse('$_baseUrl/api/preferences/queries/recent');
      await _authedPost(uri, {
        'query': query,
        'panel_type': panelType,
        'language': language,
      });
    } catch (e) {
      debugPrint('SavedQueryService.addRecentQuery error: $e');
    }
  }

  // ---------------------------------------------------------------------------
  // Saved queries
  // ---------------------------------------------------------------------------

  /// Get saved queries for a panel from cache.
  List<QueryEntry> getSavedQueries(String panelType) {
    return _savedCache[panelType] ?? [];
  }

  /// Fetch saved queries from the backend.
  Future<List<QueryEntry>> fetchSavedQueries(String panelType) async {
    try {
      final uri = Uri.parse(
        '$_baseUrl/api/preferences/queries/saved?panel_type=$panelType',
      );
      final response = await _authedGet(uri);
      if (response.statusCode == 200) {
        final data = await AppIsolate.run(_parseJsonMap, response.body);
        final list = (data['queries'] as List? ?? [])
            .map((e) => QueryEntry.fromJson(e as Map<String, dynamic>))
            .toList();
        _savedCache[panelType] = list;
        notifyListeners();
        return list;
      }
    } catch (e) {
      debugPrint('SavedQueryService.fetchSavedQueries error: $e');
    }
    return _savedCache[panelType] ?? [];
  }

  /// Save a named query.
  Future<QueryEntry?> saveQuery({
    required String name,
    required String query,
    required String panelType,
    String language = '',
  }) async {
    try {
      final uri = Uri.parse('$_baseUrl/api/preferences/queries/saved');
      final response = await _authedPost(uri, {
        'name': name,
        'query': query,
        'panel_type': panelType,
        'language': language,
      });
      if (response.statusCode == 200) {
        final data = await AppIsolate.run(_parseJsonMap, response.body);
        final entry =
            QueryEntry.fromJson(data['query'] as Map<String, dynamic>);
        // Update local cache
        final cached = _savedCache[panelType] ?? [];
        cached.insert(0, entry);
        _savedCache[panelType] = cached;
        notifyListeners();
        return entry;
      }
    } catch (e) {
      debugPrint('SavedQueryService.saveQuery error: $e');
    }
    return null;
  }

  /// Delete a saved query.
  Future<void> deleteSavedQuery(String queryId, String panelType) async {
    // Optimistic removal
    final cached = _savedCache[panelType] ?? [];
    cached.removeWhere((e) => e.id == queryId);
    _savedCache[panelType] = cached;
    notifyListeners();

    try {
      final uri =
          Uri.parse('$_baseUrl/api/preferences/queries/saved/$queryId');
      await _authedDelete(uri);
    } catch (e) {
      debugPrint('SavedQueryService.deleteSavedQuery error: $e');
      // Re-fetch to restore consistent state
      await fetchSavedQueries(panelType);
    }
  }

  // ---------------------------------------------------------------------------
  // HTTP helpers
  // ---------------------------------------------------------------------------

  Future<http.Response> _authedGet(Uri uri) async {
    final headers = await AuthService.instance.getAuthHeaders();
    return http.get(uri, headers: headers).timeout(ServiceConfig.defaultTimeout);
  }

  Future<http.Response> _authedPost(
      Uri uri, Map<String, dynamic> body) async {
    final headers = await AuthService.instance.getAuthHeaders();
    headers['Content-Type'] = 'application/json';
    return http
        .post(uri, headers: headers, body: jsonEncode(body))
        .timeout(ServiceConfig.defaultTimeout);
  }

  Future<http.Response> _authedDelete(Uri uri) async {
    final headers = await AuthService.instance.getAuthHeaders();
    return http
        .delete(uri, headers: headers)
        .timeout(ServiceConfig.defaultTimeout);
  }
}
