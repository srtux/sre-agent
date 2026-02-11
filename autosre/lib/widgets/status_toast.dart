import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

/// A utility class for displaying high-fidelity, animated toast notifications.
///
/// Toasts use an [OverlayEntry] to support custom animations (elastic entrance,
/// quick shake, and fly-away exit) and are right-aligned by default.
class StatusToast {
  /// Displays a toast notification with the given [message].
  ///
  /// * [isError]: If true, displays an error icon and color.
  /// * [duration]: How long to wait before starting the shake and exit animation.
  static void show(
    BuildContext context,
    String message, {
    bool isError = false,
    Duration duration = const Duration(seconds: 2),
  }) {
    final overlay = Overlay.of(context);
    late OverlayEntry entry;

    entry = OverlayEntry(
      builder: (context) => _AnimatedToast(
        message: message,
        isError: isError,
        duration: duration,
        onDismissed: () => entry.remove(),
      ),
    );

    overlay.insert(entry);
  }
}

class _AnimatedToast extends StatefulWidget {
  final String message;
  final bool isError;
  final Duration duration;
  final VoidCallback onDismissed;

  const _AnimatedToast({
    required this.message,
    required this.isError,
    required this.duration,
    required this.onDismissed,
  });

  @override
  State<_AnimatedToast> createState() => _AnimatedToastState();
}

class _AnimatedToastState extends State<_AnimatedToast>
    with TickerProviderStateMixin {
  late AnimationController _entranceController;
  late AnimationController _shakeController;
  late AnimationController _exitController;

  late Animation<Offset> _entranceAnimation;
  late Animation<double> _shakeAnimation;
  late Animation<Offset> _exitAnimation;

  @override
  void initState() {
    super.initState();

    _entranceController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    );

    _shakeController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
    );

    _exitController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 500),
    );

    _entranceAnimation =
        Tween<Offset>(begin: const Offset(0, 2.0), end: Offset.zero).animate(
          CurvedAnimation(
            parent: _entranceController,
            curve: Curves.elasticOut,
          ),
        );

    _shakeAnimation = TweenSequence<double>([
      TweenSequenceItem(tween: Tween<double>(begin: 0, end: 8), weight: 1),
      TweenSequenceItem(tween: Tween<double>(begin: 8, end: -8), weight: 1),
      TweenSequenceItem(tween: Tween<double>(begin: -8, end: 8), weight: 1),
      TweenSequenceItem(tween: Tween<double>(begin: 8, end: -8), weight: 1),
      TweenSequenceItem(tween: Tween<double>(begin: -8, end: 5), weight: 1),
      TweenSequenceItem(tween: Tween<double>(begin: 5, end: 0), weight: 1),
    ]).animate(CurvedAnimation(parent: _shakeController, curve: Curves.linear));

    _exitAnimation =
        Tween<Offset>(begin: Offset.zero, end: const Offset(2.0, 0)).animate(
          CurvedAnimation(parent: _exitController, curve: Curves.easeInBack),
        );

    _runSequence();
  }

  Future<void> _runSequence() async {
    if (!mounted) return;
    await _entranceController.forward();
    await Future.delayed(widget.duration);
    if (!mounted) return;
    await _shakeController.forward();
    await _exitController.forward();
    if (mounted) {
      widget.onDismissed();
    }
  }

  @override
  void dispose() {
    _entranceController.dispose();
    _shakeController.dispose();
    _exitController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Positioned(
      bottom: 48,
      left: 16,
      right: 16,
      child: Align(
        alignment: Alignment.bottomRight,
        child: SlideTransition(
          position: _exitAnimation,
          child: SlideTransition(
            position: _entranceAnimation,
            child: AnimatedBuilder(
              animation: _shakeAnimation,
              builder: (context, child) {
                return Transform.translate(
                  offset: Offset(_shakeAnimation.value, 0),
                  child: child,
                );
              },
              child: Material(
                color: Colors.transparent,
                child: Container(
                  constraints: const BoxConstraints(maxWidth: 600),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 12,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.backgroundCard.withValues(
                      alpha: 0.9,
                    ), // High opacity for readability
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: AppColors.surfaceBorder.withValues(alpha: 0.5),
                      width: 1,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withValues(alpha: 0.3),
                        blurRadius: 20,
                        offset: const Offset(0, 10),
                      ),
                    ],
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        widget.isError
                            ? Icons.error_outline
                            : Icons.check_circle_outline,
                        color: widget.isError
                            ? AppColors.error
                            : AppColors.primaryCyan,
                        size: 18,
                      ),
                      const SizedBox(width: 12),
                      Flexible(
                        child: Text(
                          widget.message,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 13,
                            fontWeight: FontWeight.w400,
                            decoration: TextDecoration.none,
                          ),
                          softWrap: true,
                          maxLines: null,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Material(
                        color: Colors.transparent,
                        child: InkWell(
                          onTap: () {
                            _exitController.forward().then(
                                  (_) => widget.onDismissed(),
                                );
                          },
                          borderRadius: BorderRadius.circular(4),
                          child: const Padding(
                            padding: EdgeInsets.all(4.0),
                            child: Icon(
                              Icons.close,
                              color: Colors.white54,
                              size: 16,
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
