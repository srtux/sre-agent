import 'package:freezed_annotation/freezed_annotation.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:google_sign_in/google_sign_in.dart';
import '../../../services/auth_service.dart';

part 'auth_controller.freezed.dart';
part 'auth_controller.g.dart';

@freezed
class AuthState with _$AuthState {
  const factory AuthState({
    GoogleSignInAccount? user,
    @Default(true) bool isLoading,
    @Default(false) bool isGuestMode,
    String? error,
  }) = _AuthState;
}

@riverpod
class AuthController extends _$AuthController {
  late final AuthService _authService;

  @override
  AuthState build() {
    _authService = AuthService.instance;

    // Listen to legacy AuthService changes
    _authService.addListener(_onAuthServiceChanged);

    ref.onDispose(() {
      _authService.removeListener(_onAuthServiceChanged);
    });

    return AuthState(
      user: _authService.currentUser,
      isLoading: _authService.isLoading,
      isGuestMode: _authService.isGuestMode,
    );
  }

  void _onAuthServiceChanged() {
    state = state.copyWith(
      user: _authService.currentUser,
      isLoading: _authService.isLoading,
      isGuestMode: _authService.isGuestMode,
    );
  }

  Future<void> signIn() async {
    try {
      state = state.copyWith(isLoading: true, error: null);
      await _authService.signIn();
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> signOut() async {
    state = state.copyWith(isLoading: true);
    await _authService.signOut();
  }

  void loginAsGuest() {
    _authService.loginAsGuest();
  }
}
