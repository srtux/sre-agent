import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Mobile implementation of the Google Sign-In button.
///
/// Uses a custom-styled button that calls [onSignIn], which triggers
/// [AuthService.signIn] → [GoogleSignIn.authenticate(scopeHint: scopes)].
/// This requests both identity AND GCP scopes in a single OAuth flow.
Widget buildGoogleSignInButton({required VoidCallback onSignIn}) {
  return Semantics(
    button: true,
    label: 'Sign in with Google',
    child: Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onSignIn,
        borderRadius: BorderRadius.circular(50),
        child: Container(
          constraints: const BoxConstraints(minWidth: 200, minHeight: 44),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
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
                child: const Icon(
                  Icons.account_circle,
                  size: 20,
                  color: Colors.indigoAccent,
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
    ),
  );
}
