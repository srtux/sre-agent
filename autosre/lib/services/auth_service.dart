import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:google_sign_in/google_sign_in.dart' as gsi_lib;
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

  static const String _buildTimeClientId = String.fromEnvironment('GOOGLE_CLIENT_ID');
  late final gsi_lib.GoogleSignIn _googleSignIn;

  gsi_lib.GoogleSignInAccount? _currentUser;
  String? _idToken;
  String? _accessToken;
  DateTime? _accessTokenExpiry;
  bool _isLoading = true;
  bool _isAuthEnabled = true; // Default to true until config says otherwise

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
  String? get idToken => _idToken;
  String? get accessToken => _accessToken;

  String get _baseUrl {
    if (kDebugMode) {
      return 'http://127.0.0.1:8001';
    }
    return '';
  }

  /// Initialize auth state
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

    // 3. Listen to auth state changes via authenticationEvents
    _googleSignIn.authenticationEvents.listen(
      (gsi_lib.GoogleSignInAuthenticationEvent event) async {
        try {
          if (event is gsi_lib.GoogleSignInAuthenticationEventSignIn) {
            debugPrint('AuthService: User signed in: ${event.user.email}');
            _currentUser = event.user;
            await _refreshTokens();
          } else if (event is gsi_lib.GoogleSignInAuthenticationEventSignOut) {
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
        debugPrint('Auth stream error: $e');
      },
    );

    try {
      // Initialize configuration
      await _googleSignIn.initialize(
        clientId: effectiveClientId,
      );

      // Attempt silent sign-in
      await _googleSignIn.attemptLightweightAuthentication();
    } catch (e) {
      debugPrint('Silent sign-in failed: $e');
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  /// Refresh auth tokens
  Future<void> _refreshTokens() async {
    if (_currentUser == null) {
      debugPrint('AuthService: Skip _refreshTokens because _currentUser is null');
      return;
    }
    try {
      debugPrint('AuthService: Refreshing tokens for ${_currentUser!.email}');
      final auth = _currentUser!.authentication;
      _idToken = auth.idToken;

      // Note: accessToken is no longer on authentication property in this version.
      // Use getAuthHeaders() to obtain a fresh access token for API calls.
      debugPrint('AuthService: Successfully extracted idToken');

      // Note: We used to try to set _accessToken here, but it's better to
      // let getAuthHeaders() handle it via the authorizationClient to ensure
      // it's fresh and has the correct scopes.
    } catch (e, stack) {
      debugPrint('Error refreshing tokens: $e\n$stack');
    }
  }

  /// Call backend login endpoint to establish session cookie
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

  Completer<void>? _authzCompleter;

  /// Get current auth headers
  Future<Map<String, String>> getAuthHeaders() async {
    if (!_isAuthEnabled) {
      // In dev mode with auth disabled, we send a dummy token or no token.
      // The backend middleware is configured to accept this or bypass.
      // We send a header to be explicit.
      return {
        'Authorization': 'Bearer dev-mode-bypass-token',
      };
    }

    if (_currentUser == null) return {};

    // Check local cache first
    if (_accessToken != null && _accessTokenExpiry != null) {
      if (DateTime.now().isBefore(_accessTokenExpiry!.subtract(const Duration(minutes: 5)))) {
        debugPrint('AuthService: Using cached access token (expires at $_accessTokenExpiry)');
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

      // If null, we might need interaction (e.g. first time or expired)
      if (authz == null) {
        debugPrint('AuthService: Silent authorization failed, trying interactive...');
        authz = await authzClient.authorizeScopes(_scopes);
      }

      _accessToken = authz.accessToken;
      // Tokens usually last 1 hour; we'll assume 55 minutes for safety if not provided
      _accessTokenExpiry = DateTime.now().add(const Duration(minutes: 55));

      // Asynchronously let the backend know about the new token to update session state
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

  /// Bypasses SSO and logs in as a guest (for local development)
  void loginAsGuest() {
    debugPrint('AuthService: Logging in as Guest (Bypassing SSO)');
    _isAuthEnabled = false;
    _isLoading = false;
    _currentUser = null;
    notifyListeners();
  }

  /// Sign out
  Future<void> signOut() async {
    await _googleSignIn.signOut();
    // State clearing handled by event listener
    notifyListeners();
  }

  /// Get authenticated HTTP client
  Future<http.Client> getAuthenticatedClient() async {
    if (_currentUser == null && _isAuthEnabled) {
      debugPrint('AuthService: TESTING MODE - Creating non-authenticated client');
      // throw Exception('User not authenticated'); // DISABLED FOR TESTING
    }

    final client = http.Client();
    if (kIsWeb) {
      try {
        // On web, http.Client() is a BrowserClient
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

  /// Helper to extract token from headers (Exposed for testing)
  static String? extractTokenFromHeaders(Map<String, String> headers) {
    final authHeader = headers['Authorization'];
    return authHeader != null && authHeader.startsWith('Bearer ')
        ? authHeader.substring(7)
        : authHeader;
  }
}
