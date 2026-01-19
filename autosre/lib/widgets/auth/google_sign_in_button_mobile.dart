import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

Widget buildGoogleSignInButton({required VoidCallback onMobileSignIn}) {
  return Material(
    color: Colors.transparent,
    child: InkWell(
      onTap: onMobileSignIn,
      borderRadius: BorderRadius.circular(50), // Fully rounded pill
      child: Container(
        constraints: const BoxConstraints(minWidth: 280),
        padding: const EdgeInsets.symmetric(
          horizontal: 32,
          vertical: 16,
        ),
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
                errorBuilder: (c, o, s) => const Icon(Icons.login, size: 20, color: Colors.indigoAccent),
              ),
            ),
            const SizedBox(width: 16),
            Text(
              'Sign in with Google',
              style: GoogleFonts.inter( // Matching font
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
