import 'package:flutter/foundation.dart';

/// Centralized configuration for all backend service communication.
///
/// Eliminates hardcoded URLs, timeouts, and magic numbers scattered
/// across the services layer.
class ServiceConfig {
  ServiceConfig._();

  /// Base URL for all API requests.
  ///
  /// In debug mode, points to local dev server. In release, uses
  /// relative paths (same-origin on Cloud Run).
  static String get baseUrl {
    // Check if we are running on localhost/127.0.0.1
    final isLocal =
        Uri.base.host == 'localhost' ||
        Uri.base.host == '127.0.0.1' ||
        Uri.base.host == '0.0.0.0';

    if (kDebugMode && isLocal) {
      debugPrint(
        'ServiceConfig: Using local dev baseUrl: http://localhost:8001',
      );
      return 'http://localhost:8001';
    }

    debugPrint('ServiceConfig: Using production baseUrl (relative)');
    return '';
  }

  /// Base URL for the Agent Graph iframe.
  ///
  /// In local development, the React UI usually runs on port 5174.
  static String get agentGraphBaseUrl {
    final isLocal =
        Uri.base.host == 'localhost' ||
        Uri.base.host == '127.0.0.1' ||
        Uri.base.host == '0.0.0.0';

    if (kDebugMode && isLocal) {
      return 'http://localhost:5174';
    }
    return '';
  }

  /// Default timeout for standard API requests (CRUD, config, etc.).
  static const Duration defaultTimeout = Duration(seconds: 30);

  /// Timeout for long-running queries (BigQuery, trace search, etc.).
  static const Duration queryTimeout = Duration(seconds: 60);

  /// Timeout for lightweight health/config checks.
  static const Duration healthCheckTimeout = Duration(seconds: 10);

  /// Access token validity window (matches Google OAuth2 ~60min tokens).
  static const Duration tokenLifetime = Duration(minutes: 55);

  /// Buffer before token expiry to trigger proactive refresh.
  static const Duration tokenRefreshBuffer = Duration(minutes: 5);
}
