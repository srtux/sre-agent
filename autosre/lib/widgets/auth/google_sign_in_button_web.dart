import 'package:flutter/material.dart';
import 'package:google_sign_in_platform_interface/google_sign_in_platform_interface.dart';
import 'package:google_sign_in_web/google_sign_in_web.dart';

/// Web implementation of the Google Sign-In button.
///
/// Uses the GIS (Google Identity Services) SDK-rendered button, which is the
/// ONLY supported way to trigger interactive sign-in on web with
/// google_sign_in v7. The [authenticate()] method is not available on web.
///
/// After the user clicks this button and signs in, the [authenticationEvents]
/// stream fires, and [AuthService] handles scope authorization to get an
/// access token for GCP APIs.
Widget buildGoogleSignInButton({required VoidCallback onSignIn}) {
  // The GIS SDK requires its own rendered button for web sign-in.
  // GoogleSignInPlatform.instance is set to GoogleSignInPlugin on web
  // by Flutter's plugin registration system.
  final webPlugin = GoogleSignInPlatform.instance as GoogleSignInPlugin;

  return SizedBox(
    height: 44, // Match GSI large button height approximately
    child: webPlugin.renderButton(
      configuration: GSIButtonConfiguration(
        shape: GSIButtonShape.pill,
        theme: GSIButtonTheme.filledBlack,
        size: GSIButtonSize.large,
      ),
    ),
  );
}
