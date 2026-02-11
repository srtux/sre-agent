import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../services/auth_service.dart';

/// Web implementation of the Google Sign-In button.
///
/// Uses a custom button that calls [onSignIn] instead of GIS renderButton().
/// renderButton() only handles authentication (identity) but not authorization
/// (scopes), which causes a second popup when GCP scopes are requested later.
/// By calling [onSignIn], we trigger [AuthService.signIn] which uses
/// [GoogleSignIn.authenticate(scopeHint: scopes)] to request both identity
/// AND scopes in a single OAuth flow.
Widget buildGoogleSignInButton({required VoidCallback onSignIn}) {
  return Material(
    color: Colors.transparent,
    child: InkWell(
      onTap: onSignIn,
      borderRadius: BorderRadius.circular(50),
      child: Container(
        constraints: const BoxConstraints(minWidth: 280, minHeight: 54),
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
        decoration: BoxDecoration(
          color: Colors.indigoAccent,
          borderRadius: BorderRadius.circular(50),
          boxShadow: [
            BoxShadow(
              color: Colors.indigoAccent.withValues(alpha: 0.4),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        alignment: Alignment.center,
        child: Row(
          mainAxisSize: MainAxisSize.min,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(2),
              decoration: const BoxDecoration(
                color: Colors.white,
                shape: BoxShape.circle,
              ),
              child: _buildButtonIcon(),
            ),
            const SizedBox(width: 16),
            Text(
              'Sign in with Google',
              style: GoogleFonts.inter(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: Colors.white,
              ),
            ),
          ],
        ),
      ),
    ),
  );
}

Widget _buildButtonIcon() {
  // Use profile pic if available (e.g. from a previous successful lightweight auth)
  final user = AuthService.instance.currentUser;
  if (user?.photoUrl != null) {
    return ClipOval(
      child: Image.network(
        user!.photoUrl!,
        height: 24,
        width: 24,
        fit: BoxFit.cover,
        errorBuilder: (c, o, s) => _googleLogo(),
      ),
    );
  }
  return _googleLogo();
}

Widget _googleLogo() {
  return Image.network(
    'https://www.gstatic.com/images/branding/googleg/1x/googleg_standard_color_128dp.png',
    height: 20,
    width: 20,
    errorBuilder: (c, o, s) => const Icon(
      Icons.account_circle,
      size: 20,
      color: Colors.indigoAccent,
    ),
  );
}
