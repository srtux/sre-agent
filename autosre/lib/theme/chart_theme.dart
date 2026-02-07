import 'package:flutter/material.dart';
import 'package:syncfusion_flutter_charts/charts.dart';
import 'package:intl/intl.dart';
import 'app_theme.dart';

/// Centralized Syncfusion chart theming using Deep Space colors.
///
/// Provides reusable axis, trackball, zoom, and legend configurations
/// that match the AutoSRE dark theme aesthetic.
class ChartTheme {
  /// Series color palette for multi-series charts.
  static const List<Color> seriesColors = [
    AppColors.primaryCyan,
    AppColors.primaryTeal,
    AppColors.primaryBlue,
    AppColors.secondaryPurple,
    AppColors.success,
    AppColors.warning,
    Color(0xFFFF6B9D),
    Color(0xFFFF7043),
  ];

  /// Builds a themed [DateTimeAxis] for time-series X-axis.
  ///
  /// Set [showLabel] to false to hide axis labels while preserving grid lines.
  static DateTimeAxis buildDateTimeAxis({bool showLabel = true}) {
    return DateTimeAxis(
      dateFormat: DateFormat.Hm(),
      majorGridLines: MajorGridLines(
        color: AppColors.surfaceBorder.withValues(alpha: 0.2),
        dashArray: const <double>[4, 4],
      ),
      minorGridLines: const MinorGridLines(width: 0),
      labelStyle: TextStyle(
        color: showLabel ? AppColors.textMuted : Colors.transparent,
        fontSize: 10,
      ),
      axisLine: AxisLine(color: AppColors.surfaceBorder.withValues(alpha: 0.3)),
    );
  }

  /// Builds a themed [NumericAxis] for value Y-axis.
  ///
  /// Set [showLabel] to false to hide axis labels while preserving grid lines.
  static NumericAxis buildNumericAxis({bool showLabel = true}) {
    return NumericAxis(
      numberFormat: NumberFormat.compact(),
      majorGridLines: MajorGridLines(
        color: AppColors.surfaceBorder.withValues(alpha: 0.15),
        dashArray: const <double>[4, 4],
      ),
      minorGridLines: const MinorGridLines(width: 0),
      labelStyle: TextStyle(
        color: showLabel ? AppColors.textMuted : Colors.transparent,
        fontSize: 10,
      ),
      axisLine: const AxisLine(width: 0),
    );
  }

  /// Builds a themed [TrackballBehavior] for hover/tap tooltips.
  static TrackballBehavior buildTrackball() {
    return TrackballBehavior(
      enable: true,
      activationMode: ActivationMode.singleTap,
      tooltipSettings: const InteractiveTooltip(
        format: 'point.x : point.y',
        color: AppColors.backgroundCard,
        textStyle: TextStyle(color: AppColors.textPrimary, fontSize: 11),
        borderColor: AppColors.primaryCyan,
        borderWidth: 1,
      ),
      lineColor: AppColors.primaryCyan.withValues(alpha: 0.5),
      lineWidth: 1,
      lineDashArray: const <double>[4, 4],
    );
  }

  /// Builds a themed [ZoomPanBehavior] with pinch, pan, and mouse wheel support.
  static ZoomPanBehavior buildZoomPan() {
    return ZoomPanBehavior(
      enablePinching: true,
      enablePanning: true,
      enableMouseWheelZooming: true,
      zoomMode: ZoomMode.x,
    );
  }

  /// Builds a themed [Legend] positioned at the top of the chart.
  static Legend buildLegend() {
    return const Legend(
      isVisible: true,
      position: LegendPosition.top,
      textStyle: TextStyle(color: AppColors.textSecondary, fontSize: 11),
      iconHeight: 10,
      iconWidth: 10,
    );
  }
}
