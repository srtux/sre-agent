import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../theme/app_theme.dart';

/// A reusable wrapper for dashboard cards that provides collapse and close functionality.
///
/// Used by sub-panels (Metrics, Traces, etc.) to ensure a consistent look and feel
/// and workspace management capabilities.
class DashboardCardWrapper extends StatefulWidget {
  final Widget child;
  final Widget header;
  final VoidCallback onClose;
  final String? dataToCopy;
  final bool initiallyExpanded;

  const DashboardCardWrapper({
    super.key,
    required this.child,
    required this.header,
    required this.onClose,
    this.dataToCopy,
    this.initiallyExpanded = true,
  });

  @override
  State<DashboardCardWrapper> createState() => _DashboardCardWrapperState();
}

class _DashboardCardWrapperState extends State<DashboardCardWrapper> {
  late bool _isExpanded;

  @override
  void initState() {
    super.initState();
    _isExpanded = widget.initiallyExpanded;
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: AppColors.backgroundCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: _isExpanded
              ? AppColors.surfaceBorder
              : AppColors.surfaceBorder.withValues(alpha: 0.5),
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildHeader(),
          AnimatedSize(
            duration: const Duration(milliseconds: 250),
            curve: Curves.easeInOut,
            alignment: Alignment.topCenter,
            child: ConstrainedBox(
              constraints: const BoxConstraints(minWidth: double.infinity),
              child: _isExpanded ? widget.child : const SizedBox.shrink(),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildHeader() {
    return Semantics(
      button: true,
      label: _isExpanded ? 'Collapse dashboard card' : 'Expand dashboard card',
      child: Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () => setState(() => _isExpanded = !_isExpanded),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 8, 8),
          child: Row(
            children: [
              Expanded(child: widget.header),
              const SizedBox(width: 8),
              // Copy Icon
              if (widget.dataToCopy != null)
                IconButton(
                  icon: const Icon(Icons.copy, size: 16),
                  color: AppColors.textMuted,
                  onPressed: () {
                    Clipboard.setData(ClipboardData(text: widget.dataToCopy!));
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Copied to clipboard'),
                        duration: Duration(seconds: 1),
                        behavior: SnackBarBehavior.floating,
                        width: 200,
                      ),
                    );
                  },
                  style: IconButton.styleFrom(
                    padding: const EdgeInsets.all(4),
                    minimumSize: const Size(28, 28),
                  ),
                  tooltip: 'Copy Data',
                ),
              if (widget.dataToCopy != null) const SizedBox(width: 4),
              // Collapse Icon
              IconButton(
                icon: Icon(
                  _isExpanded ? Icons.expand_less : Icons.expand_more,
                  size: 20,
                ),
                color: AppColors.textMuted,
                onPressed: () => setState(() => _isExpanded = !_isExpanded),
                style: IconButton.styleFrom(
                  backgroundColor: Colors.transparent,
                  padding: const EdgeInsets.all(4),
                  minimumSize: const Size(28, 28),
                ),
                tooltip: _isExpanded ? 'Collapse' : 'Expand',
              ),
              const SizedBox(width: 4),
              // Close Icon
              IconButton(
                icon: const Icon(
                  Icons.close,
                  size: 18,
                ),
                color: AppColors.textMuted,
                onPressed: widget.onClose,
                style: IconButton.styleFrom(
                  backgroundColor: Colors.transparent,
                  padding: const EdgeInsets.all(4),
                  minimumSize: const Size(28, 28),
                ),
                tooltip: 'Remove',
              ),
            ],
          ),
        ),
      ),
    ),
    );
  }
}
