import 'package:flutter/material.dart';

import '../../../theme/app_theme.dart';

/// A widget that wraps its [child] with an animated pulsing red border
/// when [hasError] is true.
///
/// The pulse speed scales with [errorRate]: low error rates produce a
/// slow, subtle pulse while high error rates produce a rapid, intense pulse.
class ErrorPulseWrapper extends StatefulWidget {
  /// The child widget to wrap.
  final Widget child;

  /// Whether the error pulse animation is active.
  final bool hasError;

  /// Error rate percentage (0–100) controlling pulse intensity and speed.
  final double errorRate;

  /// Border radius of the pulsing border decoration.
  final BorderRadius borderRadius;

  const ErrorPulseWrapper({
    super.key,
    required this.child,
    required this.hasError,
    this.errorRate = 50.0,
    this.borderRadius = const BorderRadius.all(Radius.circular(12)),
  });

  @override
  State<ErrorPulseWrapper> createState() => _ErrorPulseWrapperState();
}

class _ErrorPulseWrapperState extends State<ErrorPulseWrapper>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _animation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: _pulseDuration,
      vsync: this,
    );
    _animation = Tween<double>(begin: 0.3, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
    if (widget.hasError) {
      _controller.repeat(reverse: true);
    }
  }

  Duration get _pulseDuration {
    // Clamp error rate and interpolate: 0% → 1500ms, 100% → 600ms
    final t = widget.errorRate.clamp(0.0, 100.0) / 100.0;
    final ms = 1500 - (t * 900).toInt();
    return Duration(milliseconds: ms);
  }

  @override
  void didUpdateWidget(covariant ErrorPulseWrapper oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.hasError != oldWidget.hasError ||
        widget.errorRate != oldWidget.errorRate) {
      _controller.duration = _pulseDuration;
      if (widget.hasError) {
        if (!_controller.isAnimating) {
          _controller.repeat(reverse: true);
        }
      } else {
        _controller.stop();
        _controller.reset();
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.hasError) {
      return widget.child;
    }

    return AnimatedBuilder(
      animation: _animation,
      builder: (context, child) {
        final opacity = _animation.value;
        return DecoratedBox(
          decoration: BoxDecoration(
            borderRadius: widget.borderRadius,
            border: Border.all(
              color: AppColors.error.withValues(alpha: opacity),
              width: 1.5,
            ),
            boxShadow: [
              BoxShadow(
                color: AppColors.error.withValues(alpha: opacity * 0.25),
                blurRadius: 12,
                spreadRadius: 1,
              ),
            ],
          ),
          child: child!,
        );
      },
      child: widget.child,
    );
  }
}
