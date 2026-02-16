import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'auth_service.dart';
import 'service_config.dart';

/// Model for a help topic fetched from the backend docs repository.
class HelpTopic {
  final String id;
  final String title;
  final String description;
  final IconData icon;
  final List<String> categories;
  final String contentFile;
  String? expandedContent;

  HelpTopic({
    required this.id,
    required this.title,
    required this.description,
    required this.icon,
    required this.categories,
    required this.contentFile,
    this.expandedContent,
  });

  factory HelpTopic.fromJson(Map<String, dynamic> json) {
    return HelpTopic(
      id: json['id'] as String,
      title: json['title'] as String,
      description: json['description'] as String,
      icon: _mapIcon(json['icon'] as String),
      categories: List<String>.from(json['categories'] ?? []),
      contentFile: json['content_file'] as String,
    );
  }

  static IconData _mapIcon(String iconName) {
    switch (iconName) {
      case 'timeline':
        return Icons.timeline;
      case 'article':
        return Icons.article;
      case 'bar_chart':
        return Icons.bar_chart;
      case 'history':
        return Icons.history;
      case 'psychology':
        return Icons.psychology;
      case 'electric_bolt':
        return Icons.electric_bolt;
      case 'assignment':
        return Icons.assignment;
      case 'build':
        return Icons.build;
      case 'security':
        return Icons.security;
      case 'play_arrow':
        return Icons.play_arrow;
      case 'save':
        return Icons.save;
      default:
        return Icons.help_outline;
    }
  }
}

/// Service to fetch help documentation from the central docs repository via backend API.
class HelpService {
  static HelpService? _mockInstance;
  static HelpService get instance => _mockInstance ?? _internalInstance;
  static final HelpService _internalInstance = HelpService._internal();

  @visibleForTesting
  static set mockInstance(HelpService? mock) => _mockInstance = mock;

  final Future<http.Client> Function() _clientFactory;

  HelpService._internal({Future<http.Client> Function()? clientFactory})
    : _clientFactory =
          clientFactory ??
          (() async => await AuthService.instance.getAuthenticatedClient());

  /// Creates a new, non-singleton instance for testing.
  HelpService.newInstance({Future<http.Client> Function()? clientFactory})
    : _clientFactory =
          clientFactory ??
          (() async => await AuthService.instance.getAuthenticatedClient());

  String get _baseUrl => ServiceConfig.baseUrl;

  final Map<String, String> _contentCache = {};

  /// Fetches the manifest of help topics from the backend.
  Future<List<HelpTopic>> fetchTopics() async {
    try {
      final client = await _clientFactory();
      try {
        final response = await client
            .get(Uri.parse('$_baseUrl/api/help/manifest'))
            .timeout(ServiceConfig.defaultTimeout);

        if (response.statusCode == 200) {
          final List<dynamic> data = jsonDecode(response.body);
          return data
              .map((item) => HelpTopic.fromJson(item as Map<String, dynamic>))
              .toList();
        } else {
          throw Exception(
            'Failed to load help manifest: ${response.statusCode}',
          );
        }
      } finally {
        client.close();
      }
    } catch (e) {
      debugPrint('Error fetching help topics: $e');
      rethrow;
    }
  }

  /// Fetches the markdown content for a specific topic.
  Future<String> fetchContent(String topicId) async {
    if (_contentCache.containsKey(topicId)) {
      return _contentCache[topicId]!;
    }

    try {
      final client = await _clientFactory();
      try {
        final response = await client
            .get(Uri.parse('$_baseUrl/api/help/content/$topicId'))
            .timeout(ServiceConfig.defaultTimeout);

        if (response.statusCode == 200) {
          final content = response.body;
          _contentCache[topicId] = content;
          return content;
        } else {
          throw Exception(
            'Failed to load help content: ${response.statusCode}',
          );
        }
      } finally {
        client.close();
      }
    } catch (e) {
      debugPrint('Error fetching help content for $topicId: $e');
      rethrow;
    }
  }
}
