import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:google_sign_in/google_sign_in.dart' as gsi_lib;
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'api_client.dart';
import 'project_service.dart';
import 'service_config.dart';

/// Service to handle authentication with Google Sign-In.
///
/// Flow:
/// 1. [init] fetches backend config, initialises GoogleSignIn, and attempts
///    silent re-authentication.
/// 2. On web, the user clicks the GIS-rendered button (via [renderButton])
///    which triggers authentication. On mobile, [signIn] calls [authenticate].
/// 3. After authentication, [_ensureAccessToken] authorizes GCP scopes to
///    obtain an access token for calling Google Cloud APIs (EUC).
/// 4. The access token is sent as a Bearer header on every API request.
class AuthService extends ChangeNotifier {
  static AuthService? _mockInstance;
  static AuthService get instance => _mockInstance ?? _internalInstance;
  static final AuthService _internalInstance = AuthService._internal();

  @visibleForTesting
  static set mockInstance(AuthService? mock) => _mockInstance = mock;

  factory AuthService() => instance;

  AuthService._internal();

  /// OAuth 2.0 scopes needed for GCP access.
  static final List<String> _scopes = [
    'email',
    'https://www.googleapis.com/auth/cloud-platform',
  ];

  /// SharedPreferences keys for token persistence across page refreshes.
  static const String _prefKeyAccessToken = 'auth_access_token';
  static const String _prefKeyAccessTokenExpiry = 'auth_access_token_expiry';

  static const String _buildTimeClientId = String.fromEnvironment(
    'GOOGLE_CLIENT_ID',
  );

  late final gsi_lib.GoogleSignIn _googleSignIn;
  bool _initialized = false;
  StreamSubscription<gsi_lib.GoogleSignInAuthenticationEvent>?
  _authEventSubscription;

  gsi_lib.GoogleSignInAccount? _currentUser;
  String? _accessToken;
  DateTime? _accessTokenExpiry;
  bool _isLoading = true;
  bool _isAuthEnabled = true;
  bool _isGuestMode = false;
  bool _isGuestModeEnabled = false;

  @visibleForTesting
  set currentUser(gsi_lib.GoogleSignInAccount? user) => _currentUser = user;

  @visibleForTesting
  void reset() {
    _accessToken = null;
    _accessTokenExpiry = null;
    _currentUser = null;
  }

  gsi_lib.GoogleSignInAccount? get currentUser => _currentUser;
  bool get isAuthenticated => !_isAuthEnabled || _currentUser != null;
  bool get isLoading => _isLoading;
  bool get isAuthEnabled => _isAuthEnabled;
  bool get isGuestMode => _isGuestMode;
  bool get isGuestModeEnabled => _isGuestModeEnabled;
  String? get accessToken => _accessToken;

  /// Whether GoogleSignIn has been initialized (safe to call renderButton).
  bool get isInitialized => _initialized;

  /// The GoogleSignIn instance, exposed for web's renderButton().
  gsi_lib.GoogleSignIn get googleSignIn => _googleSignIn;

  // ---------------------------------------------------------------------------
  // Initialization
  // ---------------------------------------------------------------------------

  Future<void> init() async {
    String? runtimeClientId;

    // 1. Fetch runtime config from backend
    try {
      final response = await http
          .get(Uri.parse('${ServiceConfig.baseUrl}/api/config'))
          .timeout(ServiceConfig.healthCheckTimeout);
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        if (data.containsKey('auth_enabled')) {
          _isAuthEnabled = data['auth_enabled'] as bool;
        }
        if (data.containsKey('guest_mode_enabled')) {
          _isGuestModeEnabled = data['guest_mode_enabled'] as bool;
        }
        runtimeClientId = data['google_client_id'] as String?;
      }
    } catch (e) {
      debugPrint('AuthService: Failed to fetch runtime config: $e');
    }

    if (!_isAuthEnabled) {
      debugPrint('AuthService: Auth disabled by backend config.');
      _isLoading = false;
      notifyListeners();
      return;
    }

    final effectiveClientId =
        (runtimeClientId != null && runtimeClientId.isNotEmpty)
        ? runtimeClientId
        : _buildTimeClientId;

    // 2. Initialize GoogleSignIn
    _googleSignIn = gsi_lib.GoogleSignIn.instance;

    // 3. Listen to auth state changes
    _authEventSubscription = _googleSignIn.authenticationEvents.listen(
      _handleAuthEvent,
      onError: (e) => debugPrint('Auth stream error: $e'),
    );

    try {
      await _googleSignIn.initialize(clientId: effectiveClientId);
      _initialized = true;

      // 4. Attempt silent sign-in (restores session from browser)
      await _googleSignIn.attemptLightweightAuthentication();

      // Give the event listener a short window to fire
      if (_currentUser == null) {
        await Future.delayed(const Duration(milliseconds: 300));
      }

      // If user was restored, try to get access token silently
      if (_currentUser != null) {
        final restored = await _restoreCachedTokens();
        if (!restored) {
          await _ensureAccessToken(interactive: false);
        }
      }
    } catch (e) {
      debugPrint('AuthService: Init error: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  // ---------------------------------------------------------------------------
  // Auth event handling
  // ---------------------------------------------------------------------------

  Future<void> _handleAuthEvent(
    gsi_lib.GoogleSignInAuthenticationEvent event,
  ) async {
    try {
      if (event is gsi_lib.GoogleSignInAuthenticationEventSignIn) {
        debugPrint('AuthService: User signed in: ${event.user.email}');
        _currentUser = event.user;

        // Authorize GCP scopes to get an access token.
        // Interactive=true because the user just signed in and expects a
        // consent screen if needed.
        await _ensureAccessToken(interactive: true);
        notifyListeners();
      } else if (event is gsi_lib.GoogleSignInAuthenticationEventSignOut) {
        debugPrint('AuthService: User signed out');
        _currentUser = null;
        _accessToken = null;
        _accessTokenExpiry = null;
        await _clearCachedTokens();
        notifyListeners();
      }
    } catch (e, stack) {
      debugPrint('AuthService: Error handling auth event: $e\n$stack');
      notifyListeners();
    }
  }

  // ---------------------------------------------------------------------------
  // Token management
  // ---------------------------------------------------------------------------

  /// Ensure we have a valid access token with the required GCP scopes.
  ///
  /// Tries silent authorization first. If [interactive] is true, falls back
  /// to an interactive consent popup if silent auth fails.
  Future<void> _ensureAccessToken({bool interactive = false}) async {
    if (_currentUser == null) return;

    // Already have a valid token?
    if (_accessToken != null && _accessTokenExpiry != null) {
      final buffer = _accessTokenExpiry!.subtract(
        ServiceConfig.tokenRefreshBuffer,
      );
      if (DateTime.now().isBefore(buffer)) {
        return;
      }
    }

    try {
      debugPrint(
        'AuthService: Authorizing GCP scopes (interactive: $interactive)...',
      );
      final authzClient = _currentUser!.authorizationClient;

      // Try silent first
      var authz = await authzClient.authorizationForScopes(_scopes);

      // Fall back to interactive if needed
      if (authz == null && interactive) {
        debugPrint('AuthService: Silent auth failed, trying interactive...');
        authz = await authzClient.authorizeScopes(_scopes);
      }

      if (authz != null) {
        _accessToken = authz.accessToken;
        _accessTokenExpiry = DateTime.now().add(ServiceConfig.tokenLifetime);
        debugPrint('AuthService: Access token obtained successfully');
        await _cacheTokens();
      } else {
        debugPrint('AuthService: Could not obtain access token');
      }
    } catch (e) {
      debugPrint('AuthService: Error authorizing scopes: $e');
    }
  }

  /// Cache access token in SharedPreferences for page-refresh persistence.
  Future<void> _cacheTokens() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      if (_accessToken != null) {
        await prefs.setString(_prefKeyAccessToken, _accessToken!);
      }
      if (_accessTokenExpiry != null) {
        await prefs.setString(
          _prefKeyAccessTokenExpiry,
          _accessTokenExpiry!.toIso8601String(),
        );
      }
    } catch (e) {
      debugPrint('AuthService: Error caching tokens: $e');
    }
  }

  /// Restore cached tokens from SharedPreferences.
  /// Returns true if valid (non-expired) tokens were restored.
  Future<bool> _restoreCachedTokens() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final cachedToken = prefs.getString(_prefKeyAccessToken);
      final cachedExpiry = prefs.getString(_prefKeyAccessTokenExpiry);

      if (cachedToken != null && cachedExpiry != null) {
        final expiry = DateTime.parse(cachedExpiry);
        final buffer = expiry.subtract(ServiceConfig.tokenRefreshBuffer);
        if (DateTime.now().isBefore(buffer)) {
          _accessToken = cachedToken;
          _accessTokenExpiry = expiry;
          debugPrint('AuthService: Restored cached token (expires $expiry)');
          return true;
        }
      }
    } catch (e) {
      debugPrint('AuthService: Error restoring cached tokens: $e');
    }
    return false;
  }

  /// Clear cached tokens on sign-out.
  Future<void> _clearCachedTokens() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_prefKeyAccessToken);
      await prefs.remove(_prefKeyAccessTokenExpiry);
    } catch (e) {
      debugPrint('AuthService: Error clearing cached tokens: $e');
    }
  }

  // ---------------------------------------------------------------------------
  // Auth headers (injected by ProjectInterceptorClient on every API request)
  // ---------------------------------------------------------------------------

  /// Get auth headers with a valid access token.
  ///
  /// Refreshes the token if expired (silent first, then interactive).
  Future<Map<String, String>> getAuthHeaders() async {
    if (!_isAuthEnabled) {
      final headers = {'Authorization': 'Bearer dev-mode-bypass-token'};
      if (_isGuestMode) {
        headers['X-Guest-Mode'] = 'true';
      }
      return headers;
    }

    if (_currentUser == null) return {};

    // Refresh token if needed
    await _ensureAccessToken(interactive: true);

    if (_accessToken == null) return {};

    return {'Authorization': 'Bearer $_accessToken'};
  }

  // ---------------------------------------------------------------------------
  // Sign in / Sign out
  // ---------------------------------------------------------------------------

  /// Sign in with Google.
  ///
  /// On web, interactive sign-in is handled by the GIS-rendered button
  /// (see [google_sign_in_button_web.dart]). This method only does silent auth.
  /// On mobile, calls [authenticate] with scopes for a single consent screen.
  Future<void> signIn() async {
    try {
      if (kIsWeb) {
        // On web, authenticate() is not supported.
        // Interactive sign-in is handled by renderButton() in the UI.
        // This path is only reached as a fallback for silent re-auth.
        await _googleSignIn.attemptLightweightAuthentication();
      } else {
        await _googleSignIn.authenticate(scopeHint: _scopes);
      }
    } catch (e) {
      debugPrint('AuthService: Error in signIn: $e');
      rethrow;
    }
  }

  /// Bypass SSO and log in as a guest with synthetic demo data.
  void loginAsGuest() {
    debugPrint('AuthService: Logging in as Guest (Demo Mode)');
    _isAuthEnabled = false;
    _isGuestMode = true;
    _isLoading = false;
    _currentUser = null;
    notifyListeners();
  }

  /// Sign out and clear all cached state.
  Future<void> signOut() async {
    await _clearCachedTokens();
    await _googleSignIn.signOut();
    _currentUser = null;
    _accessToken = null;
    _accessTokenExpiry = null;
    notifyListeners();
  }

  // ---------------------------------------------------------------------------
  // HTTP client factory
  // ---------------------------------------------------------------------------

  /// Get authenticated HTTP client with project ID injection.
  Future<http.Client> getAuthenticatedClient() async {
    final client = http.Client();
    if (kIsWeb) {
      try {
        (client as dynamic).withCredentials = true;
      } catch (e) {
        debugPrint(
          'AuthService: could not set withCredentials on authenticated client',
        );
      }
    }

    return ProjectInterceptorClient(
      client,
      projectService: ProjectService.instance,
    );
  }

  /// Helper to extract token from headers (Exposed for testing).
  static String? extractTokenFromHeaders(Map<String, String> headers) {
    final authHeader = headers['Authorization'];
    return authHeader != null && authHeader.startsWith('Bearer ')
        ? authHeader.substring(7)
        : authHeader;
  }

  @override
  void dispose() {
    _authEventSubscription?.cancel();
    super.dispose();
  }
}
