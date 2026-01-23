import 'dart:math';
import 'package:flutter/foundation.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:googleapis_auth/googleapis_auth.dart';
import 'package:http/http.dart' as http;
import 'api_client.dart';
import 'project_service.dart';

/// Service to handle authentication with Google Sign-In
class AuthService extends ChangeNotifier {
  static AuthService? _mockInstance;
  static AuthService get instance => _mockInstance ?? _internalInstance;
  static final AuthService _internalInstance = AuthService._internal();

  @visibleForTesting
  static set mockInstance(AuthService? mock) => _mockInstance = mock;

  factory AuthService() => instance;

  AuthService._internal();

  static final List<String> _scopes = [
    'email',
    'https://www.googleapis.com/auth/cloud-platform',
  ];

  final GoogleSignIn _googleSignIn = GoogleSignIn.instance;

  GoogleSignInAccount? _currentUser;
  String? _idToken;
  String? _accessToken;
  bool _isLoading = true;

  GoogleSignInAccount? get currentUser => _currentUser;
  bool get isAuthenticated => _currentUser != null;
  bool get isLoading => _isLoading;
  String? get idToken => _idToken;
  String? get accessToken => _accessToken;

  /// Initialize auth state
  Future<void> init() async {
    // Listen to auth events
    _googleSignIn.authenticationEvents.listen(
      (event) async {
        try {
          debugPrint('AuthService: Received auth event: ${event.runtimeType}');
          if (event is GoogleSignInAuthenticationEventSignIn) {
            _currentUser = event.user;
            debugPrint('AuthService: User signed in: ${_currentUser?.email}');
            await _refreshTokens();
          } else if (event is GoogleSignInAuthenticationEventSignOut) {
            debugPrint('AuthService: User signed out');
            _currentUser = null;
            _idToken = null;
            _accessToken = null;
          }
          notifyListeners();
        } catch (e, stack) {
          debugPrint('Error handling auth event: $e\n$stack');
        }
      },
      onError: (e) {
        debugPrint('Stream error in authenticationEvents: $e');
      },
    );

    try {
      // Initialize configuration (REQUIRED for Web to setup Client ID)
      await _googleSignIn.initialize();

      // Attempt silent sign-in
      // Note: On web, attemptLightweightAuthentication might fail or not be appropriate immediately
      // if not configured, but we wrap it.
      await _googleSignIn.attemptLightweightAuthentication();
    } catch (e) {
      // Ignore cancellation errors during silent sign-in
      // GoogleSignInExceptionCode.canceled is common when not logged in or FedCM is dismissed
      final message = e.toString();
      if (message.contains('canceled') || message.contains('cancelled')) {
        debugPrint('Silent sign-in canceled/skipped: $message');
      } else {
        // Log but don't rethrow to avoid crashing the app
        debugPrint('⚠️ Error initializing auth (silent sign-in): $e');
      }
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Sign in with Google
  Future<void> signIn() async {
    try {
      debugPrint('AuthService: Starting sign in flow (signIn())...');
      if (kIsWeb) {
        debugPrint('AuthService: On web, the GIS button handles the flow via renderButton.');
        return;
      }
      final account = await _googleSignIn.authenticate(scopeHint: _scopes);
      debugPrint('AuthService: Sign in successful for ${account.email}');
    } catch (e) {
      debugPrint('Error signing in: $e');
      rethrow;
    }
  }

  /// Sign out
  Future<void> signOut() async {
    await _googleSignIn.signOut();
    // State clearing handled by event listener
    notifyListeners();
  }

  /// Refresh auth tokens
  Future<void> _refreshTokens() async {
    if (_currentUser == null) {
      debugPrint('AuthService: Skip _refreshTokens because _currentUser is null');
      return;
    }
    try {
      debugPrint('AuthService: Refreshing tokens for ${_currentUser!.email}');

      // Use dynamic to avoid compiler errors during version mismatch/minification
      // but wrap in checks to avoid crashes.
      final dynamic account = _currentUser;
      final dynamic auth = await account.authentication;

      if (auth == null) {
        debugPrint('AuthService: Warning - authentication property returned null');
        return;
      }

      try {
        _idToken = auth.idToken as String?;
        debugPrint('AuthService: Successfully extracted idToken');
      } catch (e) {
        debugPrint('AuthService: Failed to extract idToken: $e');
      }

      try {
        // Use dynamic access with catch to handle potential name mangling in production
        _accessToken = auth.accessToken as String?;
        if (_accessToken != null) {
          debugPrint('AuthService: Successfully extracted accessToken from authentication');
        }
      } catch (e) {
        debugPrint('AuthService: accessToken not found on authentication object (expected on some platforms if ID token only): $e');
      }
    } catch (e, stack) {
      debugPrint('Error refreshing tokens: $e\n$stack');
    }
  }

  /// Get authenticated HTTP client
  Future<http.Client> getAuthenticatedClient() async {
    if (_currentUser == null) {
      debugPrint('AuthService: getAuthenticatedClient failed - user not authenticated');
      throw Exception('User not authenticated');
    }

    try {
      debugPrint('AuthService: Getting auth headers for ${_currentUser!.email}');

      // Attempt to get auth headers. This is the modern way to get an access token.
      Map<String, String>? headers;
      try {
        // Use dynamic to safely access authHeaders which might be problematic in minified web builds
        final dynamic account = _currentUser;
        final dynamic headersFuture = account.authHeaders;
        headers = await headersFuture as Map<String, String>?;
      } catch (e, stack) {
        debugPrint('AuthService: Error accessing authHeaders property: $e\n$stack');
      }

      if (headers == null || headers.isEmpty) {
        debugPrint('AuthService: Warning - authHeaders is null or empty');
      } else {
        debugPrint('AuthService: Successfully obtained ${headers.length} auth headers');
      }

      final String? token = headers != null ? extractTokenFromHeaders(headers) : _accessToken;

      if (token == null) {
        debugPrint('AuthService: Failed to obtain access token (Headers=${headers != null}, _accessToken=${_accessToken != null})');
        throw Exception('Failed to obtain access token. Please ensure you are logged in and have granted necessary permissions.');
      }

      debugPrint('AuthService: Creating authenticated client with token (prefix: ${token.substring(0, min(token.length, 10))}...)');

      return ProjectInterceptorClient(
        authenticatedClient(
          http.Client(),
          AccessCredentials(
            AccessToken(
              'Bearer',
              token,
              DateTime.now().add(const Duration(hours: 1)).toUtc(),
            ),
            null, // refreshToken
            _scopes,
          ),
        ),
        projectService: ProjectService.instance,
      );
    } catch (e, stack) {
      debugPrint('AuthService: Exception in getAuthenticatedClient: $e\n$stack');
      rethrow;
    }
  }

  /// Helper to extract token from headers (Exposed for testing)
  static String? extractTokenFromHeaders(Map<String, String> headers) {
    final authHeader = headers['Authorization'];
    return authHeader != null && authHeader.startsWith('Bearer ')
        ? authHeader.substring(7)
        : authHeader;
  }
}
