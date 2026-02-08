import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:syncfusion_flutter_datepicker/datepicker.dart';

import '../../models/time_range.dart';
import '../../services/dashboard_state.dart';
import '../../theme/app_theme.dart';

/// GCP-style toolbar with time range selector, refresh, and auto-refresh toggle.
///
/// Layout: [Observability Explorer icon+label] | [1H] [6H] [1D] [1W] [Custom]
///         | [Refresh] [Auto-refresh toggle]
class SreToolbar extends StatelessWidget {
  final DashboardState dashboardState;
  final VoidCallback? onRefresh;

  const SreToolbar({
    super.key,
    required this.dashboardState,
    this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: dashboardState,
      builder: (context, _) {
        return Container(
          height: 44,
          decoration: BoxDecoration(
            color: AppColors.backgroundCard,
            border: Border(
              bottom: BorderSide(
                color: AppColors.surfaceBorder.withValues(alpha: 0.5),
                width: 1,
              ),
            ),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 12),
          child: Row(
            children: [
              _buildBrandLabel(),
              _buildSeparator(),
              _buildTimeRangeChips(context),
              _buildSeparator(),
              _buildRefreshButton(),
              const SizedBox(width: 8),
              _buildAutoRefreshToggle(),
            ],
          ),
        );
      },
    );
  }

  Widget _buildBrandLabel() {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          padding: const EdgeInsets.all(4),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              colors: [
                AppColors.primaryCyan.withValues(alpha: 0.2),
                AppColors.primaryTeal.withValues(alpha: 0.2),
              ],
            ),
            borderRadius: BorderRadius.circular(6),
          ),
          child: const Icon(
            Icons.explore_rounded,
            size: 14,
            color: AppColors.primaryCyan,
          ),
        ),
        const SizedBox(width: 8),
        Text(
          'Observability Explorer',
          style: GoogleFonts.inter(
            fontSize: 12,
            fontWeight: FontWeight.w600,
            color: AppColors.textPrimary,
            letterSpacing: -0.2,
          ),
        ),
      ],
    );
  }

  Widget _buildSeparator() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 10),
      child: Container(
        width: 1,
        height: 20,
        color: AppColors.surfaceBorder.withValues(alpha: 0.5),
      ),
    );
  }

  Widget _buildTimeRangeChips(BuildContext context) {
    final currentPreset = dashboardState.timeRange.preset;
    final presets = [
      (TimeRangePreset.oneHour, '1H'),
      (TimeRangePreset.sixHours, '6H'),
      (TimeRangePreset.oneDay, '1D'),
      (TimeRangePreset.oneWeek, '1W'),
    ];

    return Expanded(
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            ...presets.map((entry) {
              final (preset, label) = entry;
              final isSelected = currentPreset == preset;
              return Padding(
                padding: const EdgeInsets.only(right: 4),
                child: ChoiceChip(
                  label: Text(label),
                  selected: isSelected,
                  onSelected: (_) {
                    dashboardState
                        .setTimeRange(TimeRange.fromPreset(preset));
                    onRefresh?.call();
                  },
                  labelStyle: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: isSelected
                        ? AppColors.backgroundDark
                        : AppColors.textSecondary,
                  ),
                  selectedColor: AppColors.primaryCyan,
                  backgroundColor:
                      Colors.white.withValues(alpha: 0.05),
                  side: BorderSide(
                    color: isSelected
                        ? AppColors.primaryCyan
                        : AppColors.surfaceBorder,
                  ),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                  visualDensity: VisualDensity.compact,
                  materialTapTargetSize:
                      MaterialTapTargetSize.shrinkWrap,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 8),
                ),
              );
            }),
            // Custom range button
            Padding(
              padding: const EdgeInsets.only(right: 4),
              child: ChoiceChip(
                label: Text(
                  currentPreset == TimeRangePreset.custom
                      ? dashboardState.timeRange.displayLabel
                      : 'Custom',
                ),
                selected: currentPreset == TimeRangePreset.custom,
                onSelected: (_) => _showCustomRangePicker(context),
                labelStyle: TextStyle(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: currentPreset == TimeRangePreset.custom
                      ? AppColors.backgroundDark
                      : AppColors.textSecondary,
                ),
                selectedColor: AppColors.primaryCyan,
                backgroundColor:
                    Colors.white.withValues(alpha: 0.05),
                side: BorderSide(
                  color: currentPreset == TimeRangePreset.custom
                      ? AppColors.primaryCyan
                      : AppColors.surfaceBorder,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
                visualDensity: VisualDensity.compact,
                materialTapTargetSize:
                    MaterialTapTargetSize.shrinkWrap,
                padding: const EdgeInsets.symmetric(horizontal: 8),
                avatar: currentPreset != TimeRangePreset.custom
                    ? const Icon(
                        Icons.date_range_rounded,
                        size: 14,
                        color: AppColors.textSecondary,
                      )
                    : null,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRefreshButton() {
    return SizedBox(
      width: 30,
      height: 30,
      child: IconButton(
        icon: const Icon(Icons.refresh, size: 16),
        color: AppColors.textSecondary,
        onPressed: () {
          dashboardState
              .setTimeRange(dashboardState.timeRange.refresh());
          onRefresh?.call();
        },
        style: IconButton.styleFrom(
          padding: EdgeInsets.zero,
          minimumSize: const Size(30, 30),
          backgroundColor: Colors.white.withValues(alpha: 0.05),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
        tooltip: 'Refresh',
      ),
    );
  }

  Widget _buildAutoRefreshToggle() {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          'Auto',
          style: TextStyle(
            fontSize: 10,
            color: dashboardState.autoRefresh
                ? AppColors.primaryCyan
                : AppColors.textMuted,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(width: 4),
        SizedBox(
          height: 20,
          width: 34,
          child: FittedBox(
            fit: BoxFit.contain,
            child: Switch(
              value: dashboardState.autoRefresh,
              onChanged: (_) => dashboardState.toggleAutoRefresh(),
              activeThumbColor: AppColors.primaryCyan,
              activeTrackColor:
                  AppColors.primaryCyan.withValues(alpha: 0.3),
              inactiveThumbColor: AppColors.textMuted,
              inactiveTrackColor:
                  Colors.white.withValues(alpha: 0.1),
            ),
          ),
        ),
      ],
    );
  }

  void _showCustomRangePicker(BuildContext context) {
    DateTime? startDate;
    DateTime? endDate;

    showDialog(
      context: context,
      builder: (dialogContext) {
        return Dialog(
          backgroundColor: AppColors.backgroundCard,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
            side: const BorderSide(color: AppColors.surfaceBorder),
          ),
          child: SizedBox(
            width: 360,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Header
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.date_range_rounded,
                        size: 18,
                        color: AppColors.primaryCyan,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        'Custom Time Range',
                        style: GoogleFonts.inter(
                          fontSize: 14,
                          fontWeight: FontWeight.w600,
                          color: AppColors.textPrimary,
                        ),
                      ),
                    ],
                  ),
                ),
                // Date picker
                SizedBox(
                  height: 320,
                  child: SfDateRangePicker(
                    selectionMode:
                        DateRangePickerSelectionMode.range,
                    backgroundColor: Colors.transparent,
                    headerStyle: DateRangePickerHeaderStyle(
                      backgroundColor: Colors.transparent,
                      textStyle: GoogleFonts.inter(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                        color: AppColors.textPrimary,
                      ),
                    ),
                    monthCellStyle: DateRangePickerMonthCellStyle(
                      textStyle: const TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 13,
                      ),
                      todayTextStyle: const TextStyle(
                        color: AppColors.primaryCyan,
                        fontSize: 13,
                      ),
                      disabledDatesTextStyle: TextStyle(
                        color:
                            AppColors.textMuted.withValues(alpha: 0.4),
                        fontSize: 13,
                      ),
                      todayCellDecoration: BoxDecoration(
                        border: Border.all(
                          color: AppColors.primaryCyan,
                        ),
                        shape: BoxShape.circle,
                      ),
                    ),
                    yearCellStyle: const DateRangePickerYearCellStyle(
                      textStyle: TextStyle(
                        color: AppColors.textPrimary,
                        fontSize: 13,
                      ),
                      todayTextStyle: TextStyle(
                        color: AppColors.primaryCyan,
                        fontSize: 13,
                      ),
                    ),
                    selectionColor: AppColors.primaryCyan,
                    startRangeSelectionColor: AppColors.primaryCyan,
                    endRangeSelectionColor: AppColors.primaryCyan,
                    rangeSelectionColor:
                        AppColors.primaryCyan.withValues(alpha: 0.2),
                    todayHighlightColor: AppColors.primaryCyan,
                    maxDate: DateTime.now(),
                    onSelectionChanged:
                        (DateRangePickerSelectionChangedArgs args) {
                      if (args.value is PickerDateRange) {
                        final range = args.value as PickerDateRange;
                        startDate = range.startDate;
                        endDate = range.endDate;
                      }
                    },
                  ),
                ),
                // Actions
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      TextButton(
                        onPressed: () =>
                            Navigator.of(dialogContext).pop(),
                        child: const Text(
                          'Cancel',
                          style: TextStyle(
                            color: AppColors.textSecondary,
                            fontSize: 13,
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      ElevatedButton(
                        onPressed: () {
                          if (startDate != null) {
                            final effectiveEnd =
                                endDate ?? startDate!;
                            dashboardState.setTimeRange(TimeRange(
                              start: startDate!,
                              end: effectiveEnd,
                              preset: TimeRangePreset.custom,
                            ));
                            onRefresh?.call();
                          }
                          Navigator.of(dialogContext).pop();
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.primaryCyan,
                          foregroundColor: AppColors.backgroundDark,
                          padding: const EdgeInsets.symmetric(
                            horizontal: 20,
                            vertical: 10,
                          ),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(8),
                          ),
                          textStyle: const TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        child: const Text('Apply'),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
