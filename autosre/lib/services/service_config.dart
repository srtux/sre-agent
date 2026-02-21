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
    // In local development, the frontend usually runs on port 8080
    // while the backend runs on port 8001.
    if (kDebugMode) {
      debugPrint(
        'ServiceConfig: Using local dev baseUrl: http://localhost:8001',
      );
      return 'http://localhost:8001';
    }

    debugPrint('ServiceConfig: Using production baseUrl (relative)');
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
