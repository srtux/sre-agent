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
  bool _isLoading = true;

  gsi_lib.GoogleSignInAccount? get currentUser => _currentUser;
  bool get isAuthenticated => _currentUser != null;
  bool get isLoading => _isLoading;
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
        runtimeClientId = data['google_client_id'] as String?;
        if (runtimeClientId != null && runtimeClientId.isNotEmpty) {
          debugPrint('AuthService: Obtained runtime Client ID from backend');
        }
      }
    } catch (e) {
      debugPrint('AuthService: Failed to fetch runtime config: $e');
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
    } catch (e, stack) {
      debugPrint('Error refreshing tokens: $e\n$stack');
    }
  }

  /// Get current auth headers
  Future<Map<String, String>> getAuthHeaders() async {
    if (_currentUser == null) return {};
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

      final token = authz.accessToken;

      return {
        'Authorization': 'Bearer $token',
      };
    } catch (e) {
      debugPrint('AuthService: Error getting auth headers: $e');
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

  /// Sign out
  Future<void> signOut() async {
    await _googleSignIn.signOut();
    // State clearing handled by event listener
    notifyListeners();
  }

  /// Get authenticated HTTP client
  Future<http.Client> getAuthenticatedClient() async {
    if (_currentUser == null) {
      debugPrint('AuthService: getAuthenticatedClient failed - user not authenticated');
      throw Exception('User not authenticated');
    }

    return ProjectInterceptorClient(
      http.Client(),
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
