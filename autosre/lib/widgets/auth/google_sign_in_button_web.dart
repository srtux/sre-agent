import 'package:flutter/material.dart';

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
          color: const Color(0xFF4285F4), // Google Blue
          borderRadius: BorderRadius.circular(50),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.2),
              blurRadius: 10,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Container(
              padding: const EdgeInsets.all(4),
              decoration: const BoxDecoration(
                color: Colors.white,
                shape: BoxShape.circle,
              ),
              child: Image.network(
                'https://www.gstatic.com/images/branding/product/1x/g_32dp.png',
                height: 20,
                width: 20,
              ),
            ),
            const SizedBox(width: 16),
            const Text(
              'Sign in with Google',
              style: TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
                color: Colors.white,
                fontFamily: 'Inter',
              ),
            ),
          ],
        ),
      ),
    ),
  );
}
