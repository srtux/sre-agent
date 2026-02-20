import 'dart:ui';

import 'package:flutter/material.dart';

import '../../../theme/app_theme.dart';

/// A translucent frosted-glass card with backdrop blur, suited for the
/// deep-space dark theme.
///
/// When [isSelected] is true, the card gains a stronger border and a
/// cyan glow shadow. A custom [glowColor] adds a matching colored shadow.
class GlassmorphismCard extends StatelessWidget {
  /// The card's content.
  final Widget child;

  /// Optional border color override (defaults to subtle white).
  final Color? borderColor;

  /// Border stroke width.
  final double borderWidth;

  /// Corner radius of the card.
  final BorderRadius borderRadius;

  /// Inner padding.
  final EdgeInsets padding;

  /// Whether the card is in a selected state (stronger border + glow).
  final bool isSelected;

  /// Optional glow color for the outer shadow.
  final Color? glowColor;

  const GlassmorphismCard({
    super.key,
    required this.child,
    this.borderColor,
    this.borderWidth = 1.0,
    this.borderRadius = const BorderRadius.all(Radius.circular(12)),
    this.padding = const EdgeInsets.all(12),
    this.isSelected = false,
    this.glowColor,
  });

  @override
  Widget build(BuildContext context) {
    final effectiveBorderColor = isSelected
        ? AppColors.primaryCyan
        : (borderColor ?? Colors.white.withValues(alpha: 0.08));
    final effectiveBorderWidth = isSelected ? 2.0 : borderWidth;

    return ClipRRect(
      borderRadius: borderRadius,
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 8, sigmaY: 8),
        child: Container(
          padding: padding,
          decoration: BoxDecoration(
            color: const Color(0xFF0D1B2A).withValues(alpha: 0.85),
            borderRadius: borderRadius,
            border: Border.all(
              color: effectiveBorderColor,
              width: effectiveBorderWidth,
            ),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: [
                Colors.white.withValues(alpha: 0.03),
                Colors.transparent,
              ],
            ),
            boxShadow: [
              if (isSelected)
                BoxShadow(
                  color: AppColors.primaryCyan.withValues(alpha: 0.2),
                  blurRadius: 16,
                  spreadRadius: -2,
                ),
              if (glowColor != null)
                BoxShadow(
                  color: glowColor!.withValues(alpha: 0.2),
                  blurRadius: 16,
                  spreadRadius: -2,
                ),
            ],
          ),
          child: child,
        ),
      ),
    );
  }
}
