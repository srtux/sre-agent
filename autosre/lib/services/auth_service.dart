import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:google_sign_in/google_sign_in.dart' as gsi_lib;
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'api_client.dart';
import 'project_service.dart';

/// Service to handle authentication with Google Sign-In.
///
/// SSO flow:
/// 1. [init] fetches backend config, initialises GoogleSignIn, and attempts
///    silent re-authentication (lightweight authentication).
/// 2. If the user is already signed in (or silent auth succeeds), we
///    immediately authorize the required GCP scopes so the first API call
///    doesn't trigger a second popup.
/// 3. On fresh sign-in, the [authenticationEvents] listener picks up the
///    event, authorizes scopes, and caches the access token.
/// 4. Access tokens are cached in [SharedPreferences] so page refreshes can
///    restore them without any popup.
class AuthService extends ChangeNotifier {
  static AuthService? _mockInstance;
  static AuthService get instance => _mockInstance ?? _internalInstance;
  static final AuthService _internalInstance = AuthService._internal();

  @visibleForTesting
  static set mockInstance(AuthService? mock) => _mockInstance = mock;

  factory AuthService() => instance;

  AuthService._internal();

  /// OAuth 2.0 scopes requested upfront so the user only sees ONE consent
  /// screen that includes the GCP cloud-platform permission.
  static final List<String> _scopes = [
    'email',
    'https://www.googleapis.com/auth/cloud-platform',
  ];

  /// SharedPreferences keys for token persistence across page refreshes.
  static const String _prefKeyAccessToken = 'auth_access_token';
  static const String _prefKeyAccessTokenExpiry = 'auth_access_token_expiry';
  static const String _prefKeyIdToken = 'auth_id_token';

  static const String _buildTimeClientId = String.fromEnvironment('GOOGLE_CLIENT_ID');
  late final gsi_lib.GoogleSignIn _googleSignIn;

  gsi_lib.GoogleSignInAccount? _currentUser;
  String? _idToken;
  String? _accessToken;
  DateTime? _accessTokenExpiry;
  bool _isLoading = true;
  bool _isAuthEnabled = true; // Default to true until config says otherwise
  bool _isGuestMode = false;
  bool _isGuestModeEnabled = false; // Controlled by backend ENABLE_GUEST_MODE

  @visibleForTesting
  set currentUser(gsi_lib.GoogleSignInAccount? user) => _currentUser = user;

  @visibleForTesting
  void reset() {
    _accessToken = null;
    _accessTokenExpiry = null;
    _idToken = null;
    _currentUser = null;
    _authzCompleter = null;
  }

  gsi_lib.GoogleSignInAccount? get currentUser => _currentUser;
  bool get isAuthenticated => !_isAuthEnabled || _currentUser != null;
  bool get isLoading => _isLoading;
  bool get isAuthEnabled => _isAuthEnabled;
  bool get isGuestMode => _isGuestMode;
  bool get isGuestModeEnabled => _isGuestModeEnabled;
  String? get idToken => _idToken;
  String? get accessToken => _accessToken;

  String get _baseUrl {
    if (kDebugMode) {
      return 'http://127.0.0.1:8001';
    }
    return '';
  }

  // ---------------------------------------------------------------------------
  // Initialization
  // ---------------------------------------------------------------------------

  /// Initialize auth state.
  ///
  /// 1. Fetches runtime config from the backend (client ID, auth/guest flags).
  /// 2. Initialises the GoogleSignIn plugin.
  /// 3. Attempts silent (lightweight) authentication.
  /// 4. If the user was restored silently, proactively authorizes GCP scopes
  ///    so no second popup appears when the first API call is made.
  Future<void> init() async {
    String? runtimeClientId;

    // 1. Fetch runtime config from backend
    try {
      final response = await http.get(Uri.parse('$_baseUrl/api/config'));
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);

        if (data.containsKey('auth_enabled')) {
          _isAuthEnabled = data['auth_enabled'] as bool;
        }
        if (data.containsKey('guest_mode_enabled')) {
          _isGuestModeEnabled = data['guest_mode_enabled'] as bool;
        }

        runtimeClientId = data['google_client_id'] as String?;
        if (runtimeClientId != null && runtimeClientId.isNotEmpty) {
          debugPrint('AuthService: Obtained runtime Client ID from backend');
        }
      }
    } catch (e) {
      debugPrint('AuthService: Failed to fetch runtime config: $e');
    }

    if (!_isAuthEnabled) {
      debugPrint('AuthService: Auth disabled by backend config. Skipping Google Sign-In init.');
      _isLoading = false;
      notifyListeners();
      return;
    }

    final effectiveClientId = (runtimeClientId != null && runtimeClientId.isNotEmpty)
        ? runtimeClientId
        : _buildTimeClientId;

    // 2. Initialize GoogleSignIn using singleton
    _googleSignIn = gsi_lib.GoogleSignIn.instance;

    // 3. Listen to auth state changes via authenticationEvents.
    //    This fires for interactive sign-in, NOT for silent/lightweight auth.
    _googleSignIn.authenticationEvents.listen(
      (gsi_lib.GoogleSignInAuthenticationEvent event) async {
        try {
          if (event is gsi_lib.GoogleSignInAuthenticationEventSignIn) {
            debugPrint('AuthService: User signed in: ${event.user.email}');
            _currentUser = event.user;
            await _refreshTokens();

            // Proactively authorize GCP scopes right after sign-in.
            // On web, renderButton() only handles authentication (identity),
            // not authorization (scopes). We must request scopes interactively
            // here so the user sees one combined flow while still on the login
            // page, rather than a second surprise popup after navigation.
            await _proactivelyAuthorizeScopes(interactive: true);

            notifyListeners();
          } else if (event is gsi_lib.GoogleSignInAuthenticationEventSignOut) {
            debugPrint('AuthService: User signed out');
            _currentUser = null;
            _idToken = null;
            _accessToken = null;
            _accessTokenExpiry = null;
            await _clearCachedTokens();
            notifyListeners();
          }
        } catch (e, stack) {
          debugPrint('Error handling auth event: $e\n$stack');
          notifyListeners();
        }
      },
      onError: (e) {
        debugPrint('Auth stream error: $e');
      },
    );

    try {
      // Initialize configuration with required scopes upfront
      await _googleSignIn.initialize(
        clientId: effectiveClientId,
      );

      // Attempt silent sign-in (restores session from browser credentials)
      await _googleSignIn.attemptLightweightAuthentication();

      // If silent auth succeeded, _currentUser is set via the event listener.
      // However, the event listener is asynchronous and may not have fired yet.
      // Give it a short window to settle, then check.
      if (_currentUser == null) {
        // Wait briefly for the event listener to fire
        await Future.delayed(const Duration(milliseconds: 300));
      }

      // If user was restored, try to load cached tokens first to avoid any popup
      if (_currentUser != null) {
        final restored = await _restoreCachedTokens();
        if (!restored) {
          // Cached tokens expired or missing — authorize scopes SILENTLY.
          // Never trigger a popup automatically on page load.
          await _proactivelyAuthorizeScopes(interactive: false);
        }
      }
    } catch (e) {
      debugPrint('Silent sign-in failed: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  // ---------------------------------------------------------------------------
  // Token management
  // ---------------------------------------------------------------------------

  @visibleForTesting
  Future<void> refreshTokensForTesting() async => _refreshTokens();

  /// Refresh ID token from the GoogleSignIn authentication object.
  Future<void> _refreshTokens() async {
    if (_currentUser == null) {
      debugPrint('AuthService: Skip _refreshTokens because _currentUser is null');
      return;
    }
    try {
      debugPrint('AuthService: Refreshing tokens for ${_currentUser!.email}');
      final auth = _currentUser!.authentication;
      _idToken = auth.idToken;
      debugPrint('AuthService: Successfully extracted idToken');
    } catch (e, stack) {
      debugPrint('Error refreshing tokens: $e\n$stack');
    }
  }

  /// Proactively authorize GCP scopes after sign-in to avoid a second popup.
  ///
  /// This consolidates the two-step flow (sign-in + scope authorization) into
  /// one seamless experience. If [interactive] is true, it will trigger a popup
  /// if silent authorization fails.
  Future<void> _proactivelyAuthorizeScopes({bool interactive = true}) async {
    if (_currentUser == null) return;

    // 1. If we already have a valid access token (e.g. from _refreshTokens), skip this.
    if (_accessToken != null && _accessTokenExpiry != null) {
      if (DateTime.now().isBefore(_accessTokenExpiry!.subtract(const Duration(minutes: 5)))) {
        debugPrint('AuthService: Already have a valid access token, skipping redundant authorization.');
        return;
      }
    }

    try {
      debugPrint('AuthService: Proactively authorizing GCP scopes (interactive: $interactive)...');
      final authzClient = _currentUser!.authorizationClient;

      // Try silent first
      var authz = await authzClient.authorizationForScopes(_scopes);

      // If silent fails, request interactive authorization ONLY if requested.
      // In the initial sign-in flow, we want this to be silent because the
      // signIn() call should have already handled the interactive part.
      if (authz == null) {
        if (interactive) {
          debugPrint('AuthService: Silent scope authorization failed, trying interactive...');
          authz = await authzClient.authorizeScopes(_scopes);
        } else {
          debugPrint('AuthService: Silent scope authorization failed, skipping interactive to avoid annoying the user.');
          return;
        }
      }

      _accessToken = authz.accessToken;
      _accessTokenExpiry = DateTime.now().add(const Duration(minutes: 55));
      debugPrint('AuthService: GCP scopes authorized successfully');

      // Cache tokens for page-refresh persistence
      await _cacheTokens();

      // Establish backend session cookie
      await _loginToBackend(_accessToken!, _idToken);
    } catch (e) {
      debugPrint('AuthService: Error proactively authorizing scopes: $e');
    }
  }

  /// Cache access and ID tokens in SharedPreferences for cross-refresh persistence.
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
      if (_idToken != null) {
        await prefs.setString(_prefKeyIdToken, _idToken!);
      }
    } catch (e) {
      debugPrint('AuthService: Error caching tokens: $e');
    }
  }

  /// Attempt to restore cached tokens from SharedPreferences.
  ///
  /// Returns true if valid (non-expired) tokens were restored.
  Future<bool> _restoreCachedTokens() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final cachedToken = prefs.getString(_prefKeyAccessToken);
      final cachedExpiry = prefs.getString(_prefKeyAccessTokenExpiry);
      final cachedIdToken = prefs.getString(_prefKeyIdToken);

      if (cachedToken != null && cachedExpiry != null) {
        final expiry = DateTime.parse(cachedExpiry);
        // Only use cached token if it expires more than 5 minutes from now
        if (DateTime.now().isBefore(expiry.subtract(const Duration(minutes: 5)))) {
          _accessToken = cachedToken;
          _accessTokenExpiry = expiry;
          _idToken = cachedIdToken ?? _idToken;
          debugPrint('AuthService: Restored cached access token (expires at $expiry)');
          return true;
        } else {
          debugPrint('AuthService: Cached token expired, will re-authorize');
        }
      }
    } catch (e) {
      debugPrint('AuthService: Error restoring cached tokens: $e');
    }
    return false;
  }

  /// Clear cached tokens (on sign-out).
  Future<void> _clearCachedTokens() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove(_prefKeyAccessToken);
      await prefs.remove(_prefKeyAccessTokenExpiry);
      await prefs.remove(_prefKeyIdToken);
    } catch (e) {
      debugPrint('AuthService: Error clearing cached tokens: $e');
    }
  }

  // ---------------------------------------------------------------------------
  // Backend session
  // ---------------------------------------------------------------------------

  /// Call backend login endpoint to establish session cookie.
  Future<void> _loginToBackend(String accessToken, String? idToken) async {
    try {
      debugPrint('AuthService: Logging in to backend...');
      final client = http.Client();
      if (kIsWeb) {
        try {
          // On web, http.Client() is a BrowserClient
          (client as dynamic).withCredentials = true;
        } catch (e) {
          debugPrint('AuthService: could not set withCredentials (not a BrowserClient?)');
        }
      }
      final response = await client.post(
        Uri.parse('$_baseUrl/api/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'access_token': accessToken,
          'id_token': idToken,
          'project_id': ProjectService.instance.selectedProjectId,
        }),
      );

      if (response.statusCode == 200) {
        debugPrint('AuthService: Successfully logged in to backend and established session cookie');
      } else {
        debugPrint('AuthService: Backend login failed with status ${response.statusCode}: ${response.body}');
      }
      client.close();
    } catch (e) {
      debugPrint('AuthService: Error calling backend login: $e');
    }
  }

  // ---------------------------------------------------------------------------
  // Auth headers (used by ProjectInterceptorClient for every API request)
  // ---------------------------------------------------------------------------

  Completer<void>? _authzCompleter;

  /// Get current auth headers with a valid access token.
  ///
  /// This method:
  /// 1. Returns cached token if still valid.
  /// 2. Tries silent scope authorization.
  /// 3. Falls back to interactive authorization if silent fails.
  /// 4. Caches the new token for future use and page refreshes.
  Future<Map<String, String>> getAuthHeaders() async {
    if (!_isAuthEnabled) {
      final headers = {
        'Authorization': 'Bearer dev-mode-bypass-token',
      };
      if (_isGuestMode) {
        headers['X-Guest-Mode'] = 'true';
      }
      return headers;
    }

    if (_currentUser == null) return {};

    // Check local cache first
    if (_accessToken != null && _accessTokenExpiry != null) {
      if (DateTime.now().isBefore(_accessTokenExpiry!.subtract(const Duration(minutes: 5)))) {
        final headers = {
          'Authorization': 'Bearer $_accessToken',
        };
        if (_idToken != null) {
          headers['X-ID-Token'] = _idToken!;
        }
        return headers;
      }
    }

    // If another authorization is already in progress, wait for it
    if (_authzCompleter != null) {
      debugPrint('AuthService: Authorization already in progress, waiting...');
      await _authzCompleter!.future;
      // After waiting, retry recursively to use the now-cached token
      return getAuthHeaders();
    }

    _authzCompleter = Completer<void>();

    try {
      debugPrint('AuthService: Requesting authorization for GCP scopes...');
      final authzClient = _currentUser!.authorizationClient;

      // Try to get tokens silently first
      var authz = await authzClient.authorizationForScopes(_scopes);

      // If null, we need interaction (e.g. first time or expired)
      if (authz == null) {
        debugPrint('AuthService: Silent authorization failed, trying interactive...');
        authz = await authzClient.authorizeScopes(_scopes);
      }

      _accessToken = authz.accessToken;
      _accessTokenExpiry = DateTime.now().add(const Duration(minutes: 55));

      // Cache for page-refresh persistence
      await _cacheTokens();

      // Establish backend session
      await _loginToBackend(_accessToken!, _idToken);

      final headers = {
        'Authorization': 'Bearer $_accessToken',
      };
      if (_idToken != null) {
        headers['X-ID-Token'] = _idToken!;
      }

      _authzCompleter!.complete();
      _authzCompleter = null;

      return headers;
    } catch (e) {
      debugPrint('AuthService: Error getting auth headers: $e');
      _authzCompleter!.completeError(e);
      _authzCompleter = null;
      return {};
    }
  }

  // ---------------------------------------------------------------------------
  // Sign in / Sign out
  // ---------------------------------------------------------------------------

  /// Sign in with Google.
  ///
  /// On web, the GIS renderButton handles the flow. On mobile, we call
  /// [authenticate] with a [scopeHint] so the consent screen shows all
  /// required permissions upfront.
  Future<void> signIn() async {
    try {
      debugPrint('AuthService: Starting sign in flow (signIn())...');
      // On web and mobile, calling authenticate with scopes handles the flow.
      await _googleSignIn.authenticate(scopeHint: _scopes);
      debugPrint('AuthService: Sign in successful');
    } catch (e) {
      debugPrint('Error signing in: $e');
      rethrow;
    }
  }

  /// Bypasses SSO and logs in as a guest with synthetic demo data.
  void loginAsGuest() {
    debugPrint('AuthService: Logging in as Guest (Demo Mode with synthetic data)');
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
    // State clearing handled by event listener
    notifyListeners();
  }

  // ---------------------------------------------------------------------------
  // HTTP client factory
  // ---------------------------------------------------------------------------

  /// Get authenticated HTTP client with project ID injection.
  Future<http.Client> getAuthenticatedClient() async {
    if (_currentUser == null && _isAuthEnabled) {
      debugPrint('AuthService: TESTING MODE - Creating non-authenticated client');
    }

    final client = http.Client();
    if (kIsWeb) {
      try {
        (client as dynamic).withCredentials = true;
      } catch (e) {
        debugPrint('AuthService: could not set withCredentials on authenticated client');
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
}
