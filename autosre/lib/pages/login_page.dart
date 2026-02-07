import 'dart:ui';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:provider/provider.dart';
import '../widgets/auth/google_sign_in_button.dart';
import '../services/auth_service.dart';
import '../theme/app_theme.dart';
import '../widgets/tech_grid_painter.dart';
import 'package:flutter/scheduler.dart'; // For Ticker
import 'package:flutter/services.dart'; // For PointerHoverEvent
import '../widgets/status_toast.dart';

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
              child: const CustomPaint(painter: TechGridPainter()),
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
                color: Colors.indigoAccent.withValues(alpha: 0.15),
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
                color: Colors.cyan.withValues(alpha: 0.1),
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
                      color: Colors.white.withValues(alpha: 0.05),
                      borderRadius: BorderRadius.circular(24),
                      border: Border.all(
                        color: Colors.white.withValues(alpha: 0.1),
                        width: 1,
                      ),
                    ),
                    constraints: const BoxConstraints(
                      maxWidth: 700,
                    ), // Widen content
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        // Element A: The Brand Hero
                        const _AnimatedPhysicsRobot(),
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
                                color: Colors
                                    .transparent, // Invisible, just for shadow
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

                        const SizedBox(
                          height: 32,
                        ), // Increased spacing to headline
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
                          constraints: const BoxConstraints(
                            maxWidth: 600,
                          ), // Allow wider text
                          child: Text(
                            'Your AI co-pilot for logs, traces, and metrics. Automate investigation and resolve GCP issues faster.',
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

                            return Wrap(
                              spacing: 24,
                              runSpacing: 16,
                              alignment: WrapAlignment.center,
                              crossAxisAlignment: WrapCrossAlignment.center,
                              children: [
                                if (auth.isGuestModeEnabled)
                                  _GuestLoginButton(
                                    onPressed: () => auth.loginAsGuest(),
                                  ),
                                GoogleSignInButton(
                                  onSignIn: () async {
                                    try {
                                      await auth.signIn();
                                    } catch (e) {
                                      if (context.mounted) {
                                        StatusToast.show(
                                          context,
                                          'Login failed: $e',
                                          isError: true,
                                        );
                                      }
                                    }
                                  },
                                ),
                              ],
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
                  color: Colors.white.withValues(alpha: 0.3),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _AnimatedPhysicsRobot extends StatefulWidget {
  const _AnimatedPhysicsRobot();

  @override
  State<_AnimatedPhysicsRobot> createState() => _AnimatedPhysicsRobotState();
}

class _AnimatedPhysicsRobotState extends State<_AnimatedPhysicsRobot>
    with TickerProviderStateMixin {
  late final Ticker _ticker;
  late final AnimationController _entranceController;
  late final Animation<double> _scaleAnimation;
  late final Animation<double> _rotationAnimation;
  late final Animation<Offset> _slideAnimation;

  // Physics State
  Offset _position = Offset.zero;
  Offset _velocity = Offset.zero; // Pixels per second

  // Constants
  static const double _k = 120.0; // Spring stiffness
  static const double _d = 12.0; // Damping
  static const double _mass = 1.0;
  static const double _sensitivity =
      15.0; // How much mouse delta pushes the robot

  Duration _lastElapsed = Duration.zero;

  @override
  void initState() {
    super.initState();
    // Physics Ticker
    _ticker = createTicker(_onTick)..start();

    // Entrance Animation
    _entranceController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1000),
    );

    _slideAnimation = Tween<Offset>(
      begin: const Offset(-5.0, 0.0), // Fly in from the left
      end: Offset.zero,
    ).animate(CurvedAnimation(
      parent: _entranceController,
      curve: Curves.easeOutBack, // Gives a nice settle/overshoot
    ));

    _scaleAnimation = CurvedAnimation(
      parent: _entranceController,
      curve: Curves.elasticOut, // Overshoot and vibrate
    );

    _rotationAnimation = Tween<double>(begin: 3.0, end: 0.0).animate(
      CurvedAnimation(
        parent: _entranceController,
        curve: Curves.easeOutCubic, // Fast spiral in, then slow down
      ),
    );

    _entranceController.forward();
  }

  @override
  void dispose() {
    _ticker.dispose();
    _entranceController.dispose();
    super.dispose();
  }

  void _onTick(Duration elapsed) {
    if (_lastElapsed == Duration.zero) {
      _lastElapsed = elapsed;
      return;
    }
    final dt = (elapsed - _lastElapsed).inMicroseconds / 1000000.0;
    _lastElapsed = elapsed;

    if (dt <= 0) return;
    if (dt > 0.1) return; // Prevent huge jumps on lag spikes

    // F_spring = -k * x
    final springForce = -_position * _k;

    // F_damping = -d * v
    final dampingForce = -_velocity * _d;

    final totalForce = springForce + dampingForce;
    final acceleration = totalForce / _mass;

    final nextVelocity = _velocity + acceleration * dt;
    final nextPosition = _position + nextVelocity * dt;

    // Only update state if there's meaningful movement
    // and use an epsilon to allow settling
    const epsilon = 0.05;
    if (nextPosition.distance < epsilon && nextVelocity.distance < epsilon) {
      if (_position != Offset.zero || _velocity != Offset.zero) {
        setState(() {
          _position = Offset.zero;
          _velocity = Offset.zero;
        });
      }
      _ticker.stop();
      _lastElapsed = Duration.zero;
      return;
    }

    setState(() {
      _velocity = nextVelocity;
      _position = nextPosition;
    });
  }

  void _onHover(PointerEvent event) {
    if (event is PointerHoverEvent) {
      // Add 'kick' from mouse delta
      setState(() {
        _velocity += event.delta.scale(_sensitivity, _sensitivity);
      });
      // Restart ticker if it's not running
      if (!_ticker.isActive) {
        _ticker.start();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onHover: _onHover,
      child: SlideTransition(
        position: _slideAnimation,
        child: ScaleTransition(
          scale: _scaleAnimation,
          child: RotationTransition(
            turns: _rotationAnimation,
            child: Transform.translate(
              offset: _position,
              child: Container(
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: Colors.indigoAccent.withValues(alpha: 0.5),
                      blurRadius: 40,
                      spreadRadius: -5,
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.smart_toy, // Original Robot Icon
                  size: 96,
                  color: Colors.white,
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _GuestLoginButton extends StatefulWidget {
  final VoidCallback onPressed;

  const _GuestLoginButton({required this.onPressed});

  @override
  State<_GuestLoginButton> createState() => _GuestLoginButtonState();
}

class _GuestLoginButtonState extends State<_GuestLoginButton> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _isHovered = true),
      onExit: (_) => setState(() => _isHovered = false),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        child: OutlinedButton(
          onPressed: widget.onPressed,
          style: OutlinedButton.styleFrom(
            padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
            minimumSize: const Size(200, 54),
            side: BorderSide(
              color: _isHovered ? AppColors.primaryCyan : Colors.white24,
              width: 1.5,
            ),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(50),
            ),
            backgroundColor: _isHovered
                ? Colors.white.withValues(alpha: 0.05)
                : Colors.transparent,
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.person_outline,
                color: _isHovered ? AppColors.primaryCyan : Colors.white70,
                size: 20,
              ),
              const SizedBox(width: 8),
              Text(
                'Guest',
                style: GoogleFonts.inter(
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                  color: _isHovered ? Colors.white : Colors.white70,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
