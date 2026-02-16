import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:shimmer/shimmer.dart';

import '../../theme/app_theme.dart';

/// Shimmer loading placeholder for dashboard panels.
///
/// Displays either a chart-shaped shimmer (with a wavy top edge simulating
/// a chart area) or a list-shaped shimmer (horizontal bars of varying width).
class ShimmerLoading extends StatelessWidget {
  /// If true, shows a chart-shaped shimmer; otherwise shows list-shaped lines.
  final bool showChart;

  /// Number of shimmer lines for list mode (ignored in chart mode).
  final int lineCount;

  const ShimmerLoading({super.key, this.showChart = false, this.lineCount = 5});

  @override
  Widget build(BuildContext context) {
    return Shimmer.fromColors(
      baseColor: AppColors.backgroundCard,
      highlightColor: AppColors.backgroundElevated,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: showChart ? _buildChartShimmer() : _buildListShimmer(),
      ),
    );
  }

  Widget _buildChartShimmer() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Title bar placeholder
        Container(
          width: 180,
          height: 12,
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(4),
          ),
        ),
        const SizedBox(height: 8),
        // Subtitle placeholder
        Container(
          width: 120,
          height: 10,
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(4),
          ),
        ),
        const SizedBox(height: 16),
        // Chart area with wavy top edge
        Expanded(
          child: ClipPath(
            clipper: _WavyTopClipper(),
            child: Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(4),
              ),
            ),
          ),
        ),
        const SizedBox(height: 12),
        // X-axis label placeholders
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: List.generate(5, (index) {
            return Container(
              width: 32,
              height: 8,
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(3),
              ),
            );
          }),
        ),
      ],
    );
  }

  Widget _buildListShimmer() {
    // Predefined width ratios for visual variety
    const widthRatios = [0.95, 0.70, 0.85, 0.60, 0.78, 0.50, 0.90, 0.65];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: List.generate(lineCount, (index) {
        final ratio = widthRatios[index % widthRatios.length];
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Row(
            children: [
              // Leading dot indicator
              Container(
                width: 6,
                height: 6,
                decoration: const BoxDecoration(
                  color: Colors.white,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 10),
              // Line bar
              Expanded(
                child: FractionallySizedBox(
                  alignment: Alignment.centerLeft,
                  widthFactor: ratio,
                  child: Container(
                    height: 12,
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      }),
    );
  }
}

/// Custom clipper that creates a wavy top edge to simulate a chart area.
class _WavyTopClipper extends CustomClipper<Path> {
  @override
  Path getClip(Size size) {
    final path = Path();
    final waveHeight = size.height * 0.35;
    final baseY = size.height * 0.3;

    path.moveTo(0, baseY);

    // Create a smooth wavy top edge using cubic bezier curves
    final segmentWidth = size.width / 4;
    for (var i = 0; i < 4; i++) {
      final startX = segmentWidth * i;
      final endX = segmentWidth * (i + 1);
      final midX = (startX + endX) / 2;

      // Alternate wave direction for natural chart look
      final peakOffset = (i.isEven ? -1 : 1) * waveHeight * 0.5;
      final variation = math.sin(i * 1.5) * waveHeight * 0.3;

      path.cubicTo(
        midX - segmentWidth * 0.15,
        baseY + peakOffset + variation,
        midX + segmentWidth * 0.15,
        baseY - peakOffset - variation,
        endX,
        baseY + (i == 3 ? waveHeight * 0.2 : 0),
      );
    }

    // Close the path along the bottom
    path.lineTo(size.width, size.height);
    path.lineTo(0, size.height);
    path.close();

    return path;
  }

  @override
  bool shouldReclip(covariant CustomClipper<Path> oldClipper) => false;
}
