import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:syncfusion_flutter_datepicker/datepicker.dart';

import '../../models/time_range.dart';
import '../../theme/app_theme.dart';
import '../../theme/design_tokens.dart';

/// Section definition for grouping presets in the dropdown menu.
class _PresetSection {
  final String label;
  final List<TimeRangePreset> presets;

  const _PresetSection({required this.label, required this.presets});
}

const _sections = [
  _PresetSection(
    label: 'QUICK',
    presets: [
      TimeRangePreset.fiveMinutes,
      TimeRangePreset.fifteenMinutes,
      TimeRangePreset.thirtyMinutes,
    ],
  ),
  _PresetSection(
    label: 'HOURS',
    presets: [
      TimeRangePreset.oneHour,
      TimeRangePreset.threeHours,
      TimeRangePreset.sixHours,
      TimeRangePreset.twelveHours,
    ],
  ),
  _PresetSection(
    label: 'DAYS',
    presets: [
      TimeRangePreset.oneDay,
      TimeRangePreset.twoDays,
      TimeRangePreset.oneWeek,
      TimeRangePreset.fourteenDays,
      TimeRangePreset.thirtyDays,
    ],
  ),
];

/// A dropdown-based time range selector that replaces chip-based selection.
///
/// Renders as a compact row: `[TimePicker dropdown] [Refresh] [Auto-refresh]`.
/// The dropdown menu groups presets into Quick / Hours / Days / Custom sections
/// with the active selection highlighted.
class UnifiedTimePicker extends StatefulWidget {
  final TimeRange currentRange;
  final ValueChanged<TimeRange> onChanged;
  final VoidCallback? onRefresh;
  final bool showRefreshButton;
  final bool showAutoRefresh;
  final bool autoRefresh;
  final VoidCallback? onAutoRefreshToggle;

  const UnifiedTimePicker({
    super.key,
    required this.currentRange,
    required this.onChanged,
    this.onRefresh,
    this.showRefreshButton = true,
    this.showAutoRefresh = false,
    this.autoRefresh = false,
    this.onAutoRefreshToggle,
  });

  @override
  State<UnifiedTimePicker> createState() => _UnifiedTimePickerState();
}

class _UnifiedTimePickerState extends State<UnifiedTimePicker> {
  bool _isHovered = false;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        _buildTriggerButton(),
        if (widget.showRefreshButton) ...[
          const SizedBox(width: Spacing.xs),
          _buildRefreshButton(),
        ],
        if (widget.showAutoRefresh) ...[
          const SizedBox(width: Spacing.sm),
          _buildAutoRefreshToggle(),
        ],
      ],
    );
  }

  Widget _buildTriggerButton() {
    return PopupMenuButton<_MenuAction>(
      tooltip: 'Select time range',
      offset: const Offset(0, 36),
      color: AppColors.backgroundCard,
      surfaceTintColor: Colors.transparent,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(Radii.md),
        side: const BorderSide(color: AppColors.surfaceBorder),
      ),
      constraints: const BoxConstraints(minWidth: 260, maxWidth: 260),
      onSelected: (action) => action.execute(),
      itemBuilder: _buildMenuItems,
      child: MouseRegion(
        onEnter: (_) => setState(() => _isHovered = true),
        onExit: (_) => setState(() => _isHovered = false),
        child: Container(
          height: 32,
          padding: const EdgeInsets.symmetric(horizontal: Spacing.sm),
          decoration: BoxDecoration(
            color: _isHovered
                ? Colors.white.withValues(alpha: 0.08)
                : Colors.white.withValues(alpha: 0.05),
            borderRadius: BorderRadius.circular(Radii.md),
            border: Border.all(color: AppColors.surfaceBorder),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.schedule,
                size: 14,
                color: AppColors.textSecondary,
              ),
              const SizedBox(width: Spacing.xs),
              Text(
                widget.currentRange.displayLabel,
                style: GoogleFonts.inter(
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(width: Spacing.xs),
              const Icon(
                Icons.keyboard_arrow_down_rounded,
                size: 16,
                color: AppColors.textMuted,
              ),
            ],
          ),
        ),
      ),
    );
  }

  List<PopupMenuEntry<_MenuAction>> _buildMenuItems(BuildContext context) {
    final items = <PopupMenuEntry<_MenuAction>>[];
    final activePreset = widget.currentRange.preset;

    for (var i = 0; i < _sections.length; i++) {
      final section = _sections[i];

      // Section header
      items.add(_SectionHeader(label: section.label));

      // Preset items
      for (final preset in section.presets) {
        final range = TimeRange.fromPreset(preset);
        final isActive = activePreset == preset;
        items.add(PopupMenuItem<_MenuAction>(
          height: 32,
          value: _MenuAction(() => widget.onChanged(range)),
          child: _PresetMenuItem(
            label: range.displayLabel,
            isActive: isActive,
          ),
        ));
      }

      // Separator between sections
      if (i < _sections.length - 1) {
        items.add(const _ThinDivider());
      }
    }

    // Custom section
    items.add(const _ThinDivider());
    items.add(const _SectionHeader(label: 'CUSTOM'));
    items.add(PopupMenuItem<_MenuAction>(
      height: 32,
      value: _MenuAction(() => _showCustomRangePicker(context)),
      child: _PresetMenuItem(
        label: 'Custom range...',
        isActive: activePreset == TimeRangePreset.custom,
        icon: Icons.date_range_rounded,
      ),
    ));
    items.add(PopupMenuItem<_MenuAction>(
      height: 32,
      value: _MenuAction(() => _showJumpToTimePicker(context)),
      child: const _PresetMenuItem(
        label: 'Jump to time...',
        isActive: false,
        icon: Icons.access_time_rounded,
      ),
    ));

    return items;
  }

  Widget _buildRefreshButton() {
    return SizedBox(
      width: 28,
      height: 28,
      child: IconButton(
        icon: const Icon(Icons.refresh, size: 14),
        color: AppColors.textSecondary,
        onPressed: widget.onRefresh,
        style: IconButton.styleFrom(
          padding: EdgeInsets.zero,
          minimumSize: const Size(28, 28),
          backgroundColor: Colors.transparent,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(Radii.sm),
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
            color: widget.autoRefresh
                ? AppColors.primaryCyan
                : AppColors.textMuted,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(width: Spacing.xs),
        SizedBox(
          height: 16,
          width: 28,
          child: FittedBox(
            fit: BoxFit.contain,
            child: Switch(
              value: widget.autoRefresh,
              onChanged: (_) => widget.onAutoRefreshToggle?.call(),
              activeThumbColor: AppColors.primaryCyan,
              activeTrackColor: AppColors.primaryCyan.withValues(alpha: 0.3),
              inactiveThumbColor: AppColors.textMuted,
              inactiveTrackColor: Colors.white.withValues(alpha: 0.1),
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
            borderRadius: BorderRadius.circular(Radii.xxl),
            side: const BorderSide(color: AppColors.surfaceBorder),
          ),
          child: SizedBox(
            width: 360,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(
                    Spacing.lg,
                    Spacing.lg,
                    Spacing.lg,
                    Spacing.sm,
                  ),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.date_range_rounded,
                        size: 18,
                        color: AppColors.primaryCyan,
                      ),
                      const SizedBox(width: Spacing.sm),
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
                SizedBox(
                  height: 320,
                  child: SfDateRangePicker(
                    selectionMode: DateRangePickerSelectionMode.range,
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
                        color: AppColors.textMuted.withValues(alpha: 0.4),
                        fontSize: 13,
                      ),
                      todayCellDecoration: BoxDecoration(
                        border: Border.all(color: AppColors.primaryCyan),
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
                Padding(
                  padding: const EdgeInsets.fromLTRB(
                    Spacing.lg,
                    0,
                    Spacing.lg,
                    Spacing.lg,
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      TextButton(
                        onPressed: () => Navigator.of(dialogContext).pop(),
                        child: const Text(
                          'Cancel',
                          style: TextStyle(
                            color: AppColors.textSecondary,
                            fontSize: 13,
                          ),
                        ),
                      ),
                      const SizedBox(width: Spacing.sm),
                      ElevatedButton(
                        onPressed: () {
                          if (startDate != null) {
                            final effectiveEnd = endDate ?? startDate!;
                            widget.onChanged(TimeRange(
                              start: startDate!,
                              end: effectiveEnd,
                              preset: TimeRangePreset.custom,
                            ));
                          }
                          Navigator.of(dialogContext).pop();
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: AppColors.primaryCyan,
                          foregroundColor: AppColors.backgroundDark,
                          padding: const EdgeInsets.symmetric(
                            horizontal: Spacing.xl,
                            vertical: Spacing.md,
                          ),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(Radii.md),
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

  void _showJumpToTimePicker(BuildContext context) {
    final dateController = TextEditingController();
    final timeController = TextEditingController();
    final now = DateTime.now();
    var selectedDate = now;
    var selectedTime = TimeOfDay.fromDateTime(now);

    showDialog(
      context: context,
      builder: (dialogContext) {
        return StatefulBuilder(
          builder: (context, setDialogState) {
            return Dialog(
              backgroundColor: AppColors.backgroundCard,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(Radii.xxl),
                side: const BorderSide(color: AppColors.surfaceBorder),
              ),
              child: SizedBox(
                width: 320,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Padding(
                      padding: const EdgeInsets.fromLTRB(
                        Spacing.lg,
                        Spacing.lg,
                        Spacing.lg,
                        Spacing.md,
                      ),
                      child: Row(
                        children: [
                          const Icon(
                            Icons.access_time_rounded,
                            size: 18,
                            color: AppColors.primaryCyan,
                          ),
                          const SizedBox(width: Spacing.sm),
                          Text(
                            'Jump to Time',
                            style: GoogleFonts.inter(
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                              color: AppColors.textPrimary,
                            ),
                          ),
                        ],
                      ),
                    ),
                    Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: Spacing.lg,
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Date',
                            style: GoogleFonts.inter(
                              fontSize: 11,
                              fontWeight: FontWeight.w500,
                              color: AppColors.textMuted,
                            ),
                          ),
                          const SizedBox(height: Spacing.xs),
                          GestureDetector(
                            onTap: () async {
                              final picked = await showDatePicker(
                                context: dialogContext,
                                initialDate: selectedDate,
                                firstDate: now.subtract(
                                  const Duration(days: 365),
                                ),
                                lastDate: now,
                                builder: (context, child) {
                                  return Theme(
                                    data: Theme.of(context).copyWith(
                                      colorScheme:
                                          Theme.of(context).colorScheme
                                              .copyWith(
                                                primary: AppColors.primaryCyan,
                                                surface:
                                                    AppColors.backgroundCard,
                                                onSurface:
                                                    AppColors.textPrimary,
                                              ),
                                      dialogTheme: const DialogThemeData(
                                        backgroundColor:
                                            AppColors.backgroundCard,
                                      ),
                                    ),
                                    child: child!,
                                  );
                                },
                              );
                              if (picked != null) {
                                setDialogState(() {
                                  selectedDate = picked;
                                  dateController.text =
                                      '${picked.year}-${picked.month.toString().padLeft(2, '0')}-${picked.day.toString().padLeft(2, '0')}';
                                });
                              }
                            },
                            child: Container(
                              height: 36,
                              padding: const EdgeInsets.symmetric(
                                horizontal: Spacing.md,
                              ),
                              decoration: BoxDecoration(
                                color: Colors.white.withValues(alpha: 0.05),
                                borderRadius: BorderRadius.circular(Radii.md),
                                border: Border.all(
                                  color: AppColors.surfaceBorder,
                                ),
                              ),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                      dateController.text.isEmpty
                                          ? 'Select date'
                                          : dateController.text,
                                      style: GoogleFonts.inter(
                                        fontSize: 12,
                                        color: dateController.text.isEmpty
                                            ? AppColors.textMuted
                                            : AppColors.textPrimary,
                                      ),
                                    ),
                                  ),
                                  const Icon(
                                    Icons.calendar_today_rounded,
                                    size: 14,
                                    color: AppColors.textMuted,
                                  ),
                                ],
                              ),
                            ),
                          ),
                          const SizedBox(height: Spacing.md),
                          Text(
                            'Time',
                            style: GoogleFonts.inter(
                              fontSize: 11,
                              fontWeight: FontWeight.w500,
                              color: AppColors.textMuted,
                            ),
                          ),
                          const SizedBox(height: Spacing.xs),
                          GestureDetector(
                            onTap: () async {
                              final picked = await showTimePicker(
                                context: dialogContext,
                                initialTime: selectedTime,
                                builder: (context, child) {
                                  return Theme(
                                    data: Theme.of(context).copyWith(
                                      colorScheme:
                                          Theme.of(context).colorScheme
                                              .copyWith(
                                                primary: AppColors.primaryCyan,
                                                surface:
                                                    AppColors.backgroundCard,
                                                onSurface:
                                                    AppColors.textPrimary,
                                              ),
                                      dialogTheme: const DialogThemeData(
                                        backgroundColor:
                                            AppColors.backgroundCard,
                                      ),
                                    ),
                                    child: child!,
                                  );
                                },
                              );
                              if (picked != null) {
                                setDialogState(() {
                                  selectedTime = picked;
                                  timeController.text =
                                      '${picked.hour.toString().padLeft(2, '0')}:${picked.minute.toString().padLeft(2, '0')}';
                                });
                              }
                            },
                            child: Container(
                              height: 36,
                              padding: const EdgeInsets.symmetric(
                                horizontal: Spacing.md,
                              ),
                              decoration: BoxDecoration(
                                color: Colors.white.withValues(alpha: 0.05),
                                borderRadius: BorderRadius.circular(Radii.md),
                                border: Border.all(
                                  color: AppColors.surfaceBorder,
                                ),
                              ),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                      timeController.text.isEmpty
                                          ? 'Select time'
                                          : timeController.text,
                                      style: GoogleFonts.inter(
                                        fontSize: 12,
                                        color: timeController.text.isEmpty
                                            ? AppColors.textMuted
                                            : AppColors.textPrimary,
                                      ),
                                    ),
                                  ),
                                  const Icon(
                                    Icons.access_time_rounded,
                                    size: 14,
                                    color: AppColors.textMuted,
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: Spacing.lg),
                    Padding(
                      padding: const EdgeInsets.fromLTRB(
                        Spacing.lg,
                        0,
                        Spacing.lg,
                        Spacing.lg,
                      ),
                      child: Row(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          TextButton(
                            onPressed: () => Navigator.of(dialogContext).pop(),
                            child: const Text(
                              'Cancel',
                              style: TextStyle(
                                color: AppColors.textSecondary,
                                fontSize: 13,
                              ),
                            ),
                          ),
                          const SizedBox(width: Spacing.sm),
                          ElevatedButton(
                            onPressed: () {
                              final target = DateTime(
                                selectedDate.year,
                                selectedDate.month,
                                selectedDate.day,
                                selectedTime.hour,
                                selectedTime.minute,
                              );
                              // Center a 1-hour window around the target
                              widget.onChanged(TimeRange(
                                start: target.subtract(
                                  const Duration(minutes: 30),
                                ),
                                end: target.add(const Duration(minutes: 30)),
                                preset: TimeRangePreset.custom,
                              ));
                              Navigator.of(dialogContext).pop();
                            },
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AppColors.primaryCyan,
                              foregroundColor: AppColors.backgroundDark,
                              padding: const EdgeInsets.symmetric(
                                horizontal: Spacing.xl,
                                vertical: Spacing.md,
                              ),
                              shape: RoundedRectangleBorder(
                                borderRadius:
                                    BorderRadius.circular(Radii.md),
                              ),
                              textStyle: const TextStyle(
                                fontSize: 13,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            child: const Text('Jump'),
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
      },
    );
  }
}

/// Wraps a void callback so it can be used as a PopupMenuItem value.
class _MenuAction {
  final VoidCallback _callback;
  const _MenuAction(this._callback);
  void execute() => _callback();
}

/// Non-interactive section header inside the popup menu.
class _SectionHeader extends PopupMenuEntry<_MenuAction> {
  final String label;

  const _SectionHeader({required this.label});

  @override
  double get height => 24;

  @override
  bool represents(_MenuAction? value) => false;

  @override
  State<_SectionHeader> createState() => _SectionHeaderState();
}

class _SectionHeaderState extends State<_SectionHeader> {
  @override
  Widget build(BuildContext context) {
    return Container(
      height: 24,
      alignment: Alignment.centerLeft,
      padding: const EdgeInsets.symmetric(horizontal: Spacing.md),
      child: Text(
        widget.label,
        style: GoogleFonts.inter(
          fontSize: 9,
          fontWeight: FontWeight.w600,
          color: AppColors.textMuted,
          letterSpacing: 1.2,
        ),
      ),
    );
  }
}

/// Thin separator line between sections.
class _ThinDivider extends PopupMenuEntry<_MenuAction> {
  const _ThinDivider();

  @override
  double get height => 9;

  @override
  bool represents(_MenuAction? value) => false;

  @override
  State<_ThinDivider> createState() => _ThinDividerState();
}

class _ThinDividerState extends State<_ThinDivider> {
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: Spacing.xs),
      child: Container(
        height: 1,
        color: AppColors.surfaceBorder.withValues(alpha: 0.3),
      ),
    );
  }
}

/// A single menu item row with optional check icon for active state.
class _PresetMenuItem extends StatelessWidget {
  final String label;
  final bool isActive;
  final IconData? icon;

  const _PresetMenuItem({
    required this.label,
    required this.isActive,
    this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: isActive
          ? BoxDecoration(
              color: AppColors.primaryCyan.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(Radii.sm),
            )
          : null,
      padding: const EdgeInsets.symmetric(
        horizontal: Spacing.sm,
        vertical: Spacing.xs,
      ),
      child: Row(
        children: [
          if (icon != null) ...[
            Icon(icon, size: 14, color: AppColors.textMuted),
            const SizedBox(width: Spacing.sm),
          ],
          Expanded(
            child: Text(
              label,
              style: GoogleFonts.inter(
                fontSize: 12,
                color: isActive ? AppColors.primaryCyan : AppColors.textPrimary,
                fontWeight: isActive ? FontWeight.w600 : FontWeight.w400,
              ),
            ),
          ),
          if (isActive)
            const Icon(
              Icons.check_rounded,
              size: 14,
              color: AppColors.primaryCyan,
            ),
        ],
      ),
    );
  }
}
