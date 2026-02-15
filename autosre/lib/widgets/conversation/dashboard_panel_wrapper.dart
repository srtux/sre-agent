import 'package:flutter/material.dart';

import '../../services/dashboard_state.dart';
import '../../theme/app_theme.dart';
import '../dashboard/dashboard_panel.dart';

/// Wraps the dashboard panel with resize and maximize functionality.
///
/// Manages its own resize state (width factor, maximize toggle, hover)
/// so the parent page doesn't need to track this UI-level state.
class DashboardPanelWrapper extends StatefulWidget {
  final DashboardState dashboardState;
  final double totalWidth;
  final ValueChanged<String> onPromptRequest;

  const DashboardPanelWrapper({
    super.key,
    required this.dashboardState,
    required this.totalWidth,
    required this.onPromptRequest,
  });

  @override
  State<DashboardPanelWrapper> createState() => _DashboardPanelWrapperState();
}

class _DashboardPanelWrapperState extends State<DashboardPanelWrapper> {
  double _dashboardWidthFactor = 0.6;
  bool _isDashboardMaximized = false;
  double _lastDashboardWidth = 0.6;
  bool _isResizeHovered = false;

  void _toggleDashboardMaximize() {
    setState(() {
      if (_isDashboardMaximized) {
        _isDashboardMaximized = false;
        _dashboardWidthFactor = _lastDashboardWidth;
      } else {
        _lastDashboardWidth = _dashboardWidthFactor;
        _isDashboardMaximized = true;
        _dashboardWidthFactor = 0.95;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: widget.dashboardState,
      builder: (context, _) {
        final isOpen = widget.dashboardState.isOpen;
        if (!isOpen) return const SizedBox.shrink();

        final targetWidth = widget.totalWidth * _dashboardWidthFactor;

        return Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Dashboard Content
            AnimatedContainer(
              duration: const Duration(milliseconds: 300),
              curve: Curves.easeInOutCubic,
              width: targetWidth,
              child: DashboardPanel(
                state: widget.dashboardState,
                onClose: widget.dashboardState.closeDashboard,
                onToggleMaximize: _toggleDashboardMaximize,
                isMaximized: _isDashboardMaximized,
                onPromptRequest: widget.onPromptRequest,
              ),
            ),
            // Resize Handle
            GestureDetector(
              key: const Key('dashboard_resize_handle'),
              behavior: HitTestBehavior.translucent,
              onHorizontalDragUpdate: (details) {
                setState(() {
                  final deltaFraction =
                      details.delta.dx / widget.totalWidth;
                  _dashboardWidthFactor += deltaFraction;
                  _dashboardWidthFactor =
                      _dashboardWidthFactor.clamp(0.2, 0.95);

                  if (_isDashboardMaximized &&
                      _dashboardWidthFactor < 0.9) {
                    _isDashboardMaximized = false;
                  }
                });
              },
              child: MouseRegion(
                cursor: SystemMouseCursors.resizeColumn,
                onEnter: (_) =>
                    setState(() => _isResizeHovered = true),
                onExit: (_) =>
                    setState(() => _isResizeHovered = false),
                child: Container(
                  width: 12,
                  color: Colors.transparent,
                  alignment: Alignment.center,
                  child: Container(
                    width: 4,
                    height: 48,
                    decoration: BoxDecoration(
                      color: _isResizeHovered
                          ? AppColors.primaryCyan
                          : AppColors.surfaceBorder,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}
