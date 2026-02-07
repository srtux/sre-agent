import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

/// Lightweight service that fetches and caches backend version metadata.
class VersionService {
  static final VersionService instance = VersionService._internal();
  factory VersionService() => instance;
  VersionService._internal();

  String? _version;
  String? _gitSha;
  String? _buildTimestamp;
  bool _fetched = false;

  String get version => _version ?? 'unknown';
  String get gitSha => _gitSha ?? 'unknown';
  String get buildTimestamp => _buildTimestamp ?? '';

  String get _baseUrl {
    if (kDebugMode) {
      return 'http://127.0.0.1:8001';
    }
    return '';
  }

  /// Fetch version info from the backend. Caches after first successful call.
  Future<void> fetch() async {
    if (_fetched) return;
    try {
      final response = await http.get(Uri.parse('$_baseUrl/api/version'));
      if (response.statusCode == 200) {
        final data = json.decode(response.body) as Map<String, dynamic>;
        _version = data['version'] as String?;
        _gitSha = data['git_sha'] as String?;
        _buildTimestamp = data['build_timestamp'] as String?;
        _fetched = true;
      }
    } catch (e) {
      debugPrint('VersionService: failed to fetch version info: $e');
    }
  }

  /// A short display string: "v0.2.0 (abc123)"
  String get displayString {
    final sha = _gitSha ?? 'unknown';
    final short = sha.length > 7 ? sha.substring(0, 7) : sha;
    return 'v$version ($short)';
  }
}
