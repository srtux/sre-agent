import 'package:flutter/material.dart';
import '../theme/app_theme.dart';

class GlowActionChip extends StatefulWidget {
  final String label;
  final VoidCallback onTap;
  final IconData? icon;
  final bool compact;

  const GlowActionChip({
    super.key,
    required this.label,
    required this.onTap,
    this.icon,
    this.compact = false,
  });

  @override
  State<GlowActionChip> createState() => _GlowActionChipState();
}

class _GlowActionChipState extends State<GlowActionChip>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _glowAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 200),
      vsync: this,
    );
    _glowAnimation = Tween<double>(
      begin: 0.0,
      end: 1.0,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeInOut));
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _handleHover(bool isHovered) {
    if (isHovered) {
      _controller.forward();
    } else {
      _controller.reverse();
    }
  }

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => _handleHover(true),
      onExit: (_) => _handleHover(false),
      cursor: SystemMouseCursors.click,
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedBuilder(
          animation: _glowAnimation,
          builder: (context, child) {
            return Transform.scale(
              scale: 1.0 + (0.02 * _glowAnimation.value),
              child: Container(
                padding: EdgeInsets.symmetric(
                  horizontal: widget.compact ? 14 : 20,
                  vertical: widget.compact ? 6 : 10,
                ),
                decoration: BoxDecoration(
                  color: Color.lerp(
                    AppColors.backgroundCard.withValues(alpha: 0.7),
                    AppColors.primaryTeal.withValues(alpha: 0.2),
                    _glowAnimation.value,
                  ),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: Color.lerp(
                      AppColors.primaryTeal.withValues(alpha: 0.2),
                      AppColors.primaryTeal.withValues(alpha: 0.9),
                      _glowAnimation.value,
                    )!,
                    width: 1.0 + (0.5 * _glowAnimation.value),
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: AppColors.primaryTeal.withValues(
                        alpha: 0.4 * _glowAnimation.value,
                      ),
                      blurRadius: 16 * _glowAnimation.value,
                      spreadRadius: 2 * _glowAnimation.value,
                    ),
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.3),
                      blurRadius: 8,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (widget.icon != null) ...[
                      Icon(
                        widget.icon,
                        size: widget.compact ? 14 : 16,
                        color: Color.lerp(
                          AppColors.primaryTeal,
                          Colors.white,
                          _glowAnimation.value * 0.5,
                        ),
                      ),
                      const SizedBox(width: 8),
                    ],
                    Text(
                      widget.label,
                      style: TextStyle(
                        color: Color.lerp(
                          AppColors.primaryTeal,
                          Colors.white,
                          _glowAnimation.value * 0.5,
                        ),
                        fontSize: widget.compact ? 12 : 14,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}
