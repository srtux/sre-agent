import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

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
              child: Image.network(
                'https://upload.wikimedia.org/wikipedia/commons/5/53/Google_%22G%22_Logo.svg',
                height: 20,
                width: 20,
                errorBuilder: (c, o, s) => const Icon(
                  Icons.login,
                  size: 20,
                  color: Colors.indigoAccent,
                ),
              ),
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
