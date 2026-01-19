import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../widgets/auth/google_sign_in_button.dart';
import '../services/auth_service.dart';
import '../theme/app_theme.dart';
import '../widgets/tech_grid_painter.dart';

class LoginPage extends StatelessWidget {
  const LoginPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(
        children: [
          // 1. The Background (Deep Space Theme)
          Positioned.fill(
            child: Container(
              decoration: const BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: [
                    Color(0xFF0F172A), // Deep Slate Blue
                    Color(0xFF1E1B4B), // Darker Indigo
                  ],
                ),
              ),
              child: CustomPaint(
                painter: const TechGridPainter(),
              ),
            ),
          ),

          // Optional: Subtle Mesh/Alive Effect (Blurred Orbs)
          Positioned(
            top: -100,
            left: -100,
            child: Container(
              width: 300,
              height: 300,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.indigoAccent.withOpacity(0.15),
              ),
              child: BackdropFilter(
                filter: ImageFilter.blur(sigmaX: 80, sigmaY: 80),
                child: Container(color: Colors.transparent),
              ),
            ),
          ),
          Positioned(
            bottom: -50,
            right: -50,
            child: Container(
              width: 400,
              height: 400,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.cyan.withOpacity(0.1),
              ),
              child: BackdropFilter(
                filter: ImageFilter.blur(sigmaX: 100, sigmaY: 100),
                child: Container(color: Colors.transparent),
              ),
            ),
          ),

          // 2. The Centerpiece (Glassmorphic Card)
          Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(24),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(24),
                child: BackdropFilter(
                  filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
                  child: Container(
                    padding: const EdgeInsets.all(48),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.05),
                      borderRadius: BorderRadius.circular(24),
                      border: Border.all(
                        color: Colors.white.withOpacity(0.1),
                        width: 1,
                      ),
                    ),
                    constraints: const BoxConstraints(maxWidth: 700), // Widen content
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        // Element A: The Brand Hero
                        Container(
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            boxShadow: [
                              BoxShadow(
                                color: Colors.indigoAccent.withOpacity(0.5),
                                blurRadius: 40, // Increased blur for "glow"
                                spreadRadius: -5,
                              ),
                            ],
                          ),
                          child: const Icon(
                            Icons.smart_toy, // Robot Icon
                            size: 96,
                            color: Colors.white,
                          ),
                        ),
                        const SizedBox(height: 16),

                        // Master Logo Text (Gradient + Glow)
                        Stack(
                          children: [
                            // 1. Blue Glow Shadow
                            Text(
                              'AutoSRE',
                              style: GoogleFonts.inter(
                                fontSize: 32,
                                fontWeight: FontWeight.w700,
                                color: Colors.transparent, // Invisible, just for shadow
                                shadows: [
                                  const Shadow(
                                    color: Colors.blueAccent,
                                    blurRadius: 20,
                                    offset: Offset(0, 0),
                                  ),
                                ],
                              ),
                            ),
                            // 2. Gradient Text Mask
                            ShaderMask(
                              shaderCallback: (bounds) => const LinearGradient(
                                colors: [Colors.white, AppColors.primaryCyan],
                                begin: Alignment.topCenter,
                                end: Alignment.bottomCenter,
                              ).createShader(bounds),
                              child: Text(
                                'AutoSRE',
                                style: GoogleFonts.inter(
                                  fontSize: 32,
                                  fontWeight: FontWeight.w700,
                                  color: Colors.white,
                                ),
                              ),
                            ),
                          ],
                        ),

                        const SizedBox(height: 32), // Increased spacing to headline

                        // Element B: The Headline
                        Text(
                          'Observability, Solved.',
                          style: GoogleFonts.inter(
                            fontSize: 56,
                            fontWeight: FontWeight.w800, // ExtraBold
                            color: Colors.white,
                            height: 1.1,
                          ),
                          textAlign: TextAlign.center,
                        ),

                        const SizedBox(height: 24), // Increased spacing

                        // Element C: The Sub-Headline
                        ConstrainedBox(
                          constraints: const BoxConstraints(maxWidth: 600), // Allow wider text
                          child: Text(
                            'Your AI co-pilot for logs, traces, and metrics. Automate investigation and resolve GCP infrastructure issues faster.',
                            style: GoogleFonts.inter(
                              fontSize: 18, // Slightly larger for readability
                              fontWeight: FontWeight.w400,
                              color: Colors.white70,
                              height: 1.5,
                            ),
                            textAlign: TextAlign.center,
                          ),
                        ),

                        const SizedBox(height: 48),

                        // Element D: The Action
                        Consumer<AuthService>(
                          builder: (context, auth, _) {
                            if (auth.isLoading) {
                              return const CircularProgressIndicator(
                                color: Colors.indigoAccent,
                              );
                            }

                            return GoogleSignInButton(
                              onMobileSignIn: () async {
                                try {
                                  await auth.signIn();
                                } catch (e) {
                                  if (context.mounted) {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(
                                        content: Text('Login failed: $e'),
                                        backgroundColor: AppColors.error,
                                      ),
                                    );
                                  }
                                }
                              },
                            );
                          },
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),

           // Footer (Optional but nice to keep)
          Positioned(
            bottom: 24,
            left: 0,
            right: 0,
            child: Center(
              child: Text(
                'By continuing, you verify that you are an authorized user.',
                style: GoogleFonts.inter(
                  fontSize: 12,
                  color: Colors.white.withOpacity(0.3),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
