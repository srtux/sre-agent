import 'package:flutter/material.dart';
import 'package:google_sign_in_web/google_sign_in_web.dart';
import 'package:google_sign_in_platform_interface/google_sign_in_platform_interface.dart';

Widget buildGoogleSignInButton({required VoidCallback onMobileSignIn}) {
  return Container(
    constraints: const BoxConstraints(maxWidth: 400, minHeight: 50),
    child: (GoogleSignInPlatform.instance as GoogleSignInPlugin).renderButton(
      configuration: GSIButtonConfiguration(
        type: GSIButtonType.standard,
        theme: GSIButtonTheme.filledBlue,
        size: GSIButtonSize.large,
        text: GSIButtonText.signinWith,
        shape: GSIButtonShape.pill,
      ),
    ),
  );
}
