// Shared helper functions for log pattern analysis widgets.

import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../models/adk_schema.dart';
import '../theme/app_theme.dart';

/// Get the color associated with a log severity level.
Color getLogSeverityColor(String severity) {
  switch (severity.toUpperCase()) {
    case 'ERROR':
      return AppColors.error;
    case 'WARNING':
      return AppColors.warning;
    case 'INFO':
      return AppColors.info;
    case 'DEBUG':
      return AppColors.textMuted;
    default:
      return AppColors.textSecondary;
  }
}

/// Get the icon associated with a log severity level.
IconData getLogSeverityIcon(String severity) {
  switch (severity.toUpperCase()) {
    case 'ERROR':
      return Icons.error;
    case 'WARNING':
      return Icons.warning_amber;
    case 'INFO':
      return Icons.info;
    case 'DEBUG':
      return Icons.bug_report;
    default:
      return Icons.circle;
  }
}

/// Get the dominant severity for a log pattern based on highest count.
String getDominantSeverity(LogPattern pattern) {
  var dominantSeverity = 'INFO';
  var max = 0;
  pattern.severityCounts.forEach((k, v) {
    if (v > max) {
      max = v;
      dominantSeverity = k;
    }
  });
  return dominantSeverity;
}

/// Get sort priority for a severity level (higher = more severe).
int getSeverityPriority(String severity) {
  switch (severity.toUpperCase()) {
    case 'ERROR':
      return 4;
    case 'WARNING':
      return 3;
    case 'INFO':
      return 2;
    case 'DEBUG':
      return 1;
    default:
      return 0;
  }
}

/// Generate a simulated frequency distribution for sparkline visualization.
List<double> generateFrequencyDistribution(int count) {
  final random = math.Random(count);
  var distribution = <double>[];
  for (var i = 0; i < 12; i++) {
    var base = count / 12.0;
    var variance = base * (random.nextDouble() * 0.6 + 0.7);
    distribution.add(variance);
  }
  return distribution;
}

/// Calculate trend indicator based on frequency distribution.
String getFrequencyTrend(List<double> distribution) {
  if (distribution.length < 4) return 'stable';
  var firstHalf = distribution
      .sublist(0, distribution.length ~/ 2)
      .reduce((a, b) => a + b);
  var secondHalf = distribution
      .sublist(distribution.length ~/ 2)
      .reduce((a, b) => a + b);
  var changePercent = ((secondHalf - firstHalf) / firstHalf) * 100;
  if (changePercent > 15) return 'up';
  if (changePercent < -15) return 'down';
  return 'stable';
}

/// Format a count for compact display (e.g., 1.5K, 2.3M).
String formatLogCount(int count) {
  if (count >= 1000000) return '${(count / 1000000).toStringAsFixed(1)}M';
  if (count >= 1000) return '${(count / 1000).toStringAsFixed(1)}K';
  return count.toString();
}
