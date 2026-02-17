import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../models/adk_schema.dart';
import '../theme/app_theme.dart';
import '../utils/ansi_parser.dart';
import '../utils/isolate_helper.dart';
import 'package:google_fonts/google_fonts.dart';
import 'tool_log_helpers.dart';

class ToolLogWidget extends StatefulWidget {
  final ToolLog log;

  const ToolLogWidget({super.key, required this.log});

  @override
  State<ToolLogWidget> createState() => _ToolLogWidgetState();
}

class _ToolLogWidgetState extends State<ToolLogWidget>
    with SingleTickerProviderStateMixin {
  bool _isExpanded = false;
  late AnimationController _animationController;
  late Animation<double> _expandAnimation;
  late Animation<double> _rotateAnimation;

  bool _isError = false;
  String? _errorMessage;

  @override
  void initState() {
    super.initState();
    _animationController = AnimationController(
      duration: const Duration(milliseconds: 200),
      vsync: this,
    );
    _expandAnimation = CurvedAnimation(
      parent: _animationController,
      curve: Curves.easeOutCubic,
    );
    _rotateAnimation = Tween<double>(begin: 0, end: 0.5).animate(
      CurvedAnimation(parent: _animationController, curve: Curves.easeOutCubic),
    );

    _processLogData();
  }

  Future<void> _processLogData() async {
    final isRunning = widget.log.status == 'running';

    // Run error checking in background
    final result = await AppIsolate.run(_analyzeLogForError, widget.log);

    if (!mounted) return;

    setState(() {
      _isError = result.$1;
      _errorMessage = result.$2;

      // Initial State Logic
      if (isRunning || _isError) {
        _isExpanded = true;
        _animationController.value = 1.0;
      } else {
        _isExpanded = false;
        _animationController.value = 0.0;
      }
    });
  }

  @override
  void didUpdateWidget(ToolLogWidget oldWidget) {
    super.didUpdateWidget(oldWidget);

    if (oldWidget.log.status != widget.log.status ||
        oldWidget.log.result != widget.log.result) {
      // Re-run background analysis if log state changed significantly
      _updateLogStateAsync(oldWidget);
    }
  }

  Future<void> _updateLogStateAsync(ToolLogWidget oldWidget) async {
    final result = await AppIsolate.run(_analyzeLogForError, widget.log);

    if (!mounted) return;

    final newIsError = result.$1;
    final newErrorMessage = result.$2;
    final newIsCompleted = widget.log.status == 'completed';
    final wasCompleted = oldWidget.log.status == 'completed';

    // Check transitions
    if (newIsError && !_isError) {
      // Became error -> Expand
      if (!_isExpanded) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) _toggleExpand();
        });
      }
    } else if (newIsCompleted && !wasCompleted && !newIsError) {
      // Became completed (success) -> Collapse
      if (_isExpanded) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (mounted) _toggleExpand();
        });
      }
    }

    setState(() {
      _isError = newIsError;
      _errorMessage = newErrorMessage;
    });
  }

  void _toggleExpand() {
    setState(() {
      _isExpanded = !_isExpanded;
      if (_isExpanded) {
        _animationController.forward();
      } else {
        _animationController.reverse();
      }
    });
  }

  void _copyToClipboard(String content, String label) {
    Clipboard.setData(ClipboardData(text: content));
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.check_circle, color: AppColors.success, size: 18),
            const SizedBox(width: 8),
            Text('$label copied to clipboard'),
          ],
        ),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        backgroundColor: AppColors.backgroundElevated,
        duration: const Duration(seconds: 2),
      ),
    );
  }

  @override
  void dispose() {
    _animationController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isRunning = widget.log.status == 'running';
    final isError = _isError;
    final completed = widget.log.status == 'completed';
    final errorMessage = _errorMessage;

    // Compact collapsed view vs expanded view
    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      curve: Curves.easeInOut,
      margin: EdgeInsets.symmetric(
        vertical: _isExpanded ? 4 : 0,
      ), // Tighter margin when collapsed
      constraints: BoxConstraints(
        minHeight: _isExpanded ? 56.0 : 36.0,
      ), // STRICT 36px when collapsed

      decoration: BoxDecoration(
        color: isError
            ? AppColors.error.withValues(alpha: 0.1)
            : AppColors.backgroundElevated.withValues(
                alpha: _isExpanded ? 0.8 : 0.4,
              ), // Less opaque when collapsed
        borderRadius: BorderRadius.circular(_isExpanded ? 10 : 6),
        border: Border.all(
          color: isError
              ? AppColors.error.withValues(alpha: 0.3)
              : Colors.white.withValues(alpha: _isExpanded ? 0.08 : 0.04),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Status Card Header
          Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: _toggleExpand,
              borderRadius: BorderRadius.circular(_isExpanded ? 10 : 6),
              child: Padding(
                padding: EdgeInsets.symmetric(
                  horizontal: 12, // Slightly reduced horizontal padding
                  vertical: _isExpanded
                      ? 12
                      : 0, // NO vertical padding when collapsed to enforce 36px
                ),
                child: _isExpanded
                    ? _buildExpandedHeader(
                        isRunning,
                        isError,
                        completed,
                        errorMessage,
                      )
                    : _buildCollapsedHeader(isRunning, isError, completed),
              ),
            ),
          ),
          // Expanded Content
          SizeTransition(
            sizeFactor: _expandAnimation,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  height: 1,
                  color: AppColors.surfaceBorder.withValues(alpha: 0.5),
                ),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(10),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Input section
                      _buildSection(
                        title: 'Input',
                        icon: Icons.input,
                        content: _formatJson(widget.log.args),
                        onCopy: () => _copyToClipboard(
                          _formatJson(widget.log.args),
                          'Input',
                        ),
                      ),
                      // Output section (only if not an error)
                      if (completed &&
                          widget.log.result != null &&
                          !isError) ...[
                        const SizedBox(height: 10),
                        _buildSection(
                          title: 'Output',
                          icon: Icons.output,
                          content: widget.log.result!,
                          onCopy: () =>
                              _copyToClipboard(widget.log.result!, 'Output'),
                          isSuccess: true,
                        ),
                      ],
                      // Error section
                      if (isError && widget.log.result != null) ...[
                        const SizedBox(height: 10),
                        _buildErrorSection(errorMessage ?? widget.log.result!),
                      ],
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }


  Widget _buildCollapsedHeader(bool isRunning, bool isError, bool isCompleted) {
    final toolIcon = _getToolIcon(widget.log.toolName);

    var iconColor = AppColors.textPrimary;
    if (isCompleted) iconColor = AppColors.success;
    if (isError) iconColor = AppColors.error;
    if (isRunning) iconColor = AppColors.warning;

    return SizedBox(
      height: 36.0, // STRICT 36px height
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center, // Vertically centered
        children: [
          // 1. Dynamic Icon
          Icon(toolIcon, size: 16, color: iconColor),
          const SizedBox(width: 8),

          // 2. Step Title
          ConstrainedBox(
            constraints: const BoxConstraints(
              maxWidth: 160,
            ), // Prevent taking too much space
            child: Text(
              _getSmartTitle(),
              style: TextStyle(
                fontWeight: FontWeight.w500,
                fontSize: 12, // 12px
                color: AppColors.textPrimary.withValues(alpha: 0.9),
                height: 1.0,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),

          // Spacer pushes everything else to the right
          const Spacer(),

          // 3. Stopwatch + Duration (Far right)
          if (widget.log.duration != null || isRunning) ...[
            const SizedBox(width: 8), // Gap before time
            Icon(
              Icons.timer_outlined,
              size: 12,
              color: AppColors.textSecondary.withValues(alpha: 0.5),
            ),
            const SizedBox(width: 4),
            Text(
              isRunning ? 'Running' : widget.log.duration ?? '',
              style: const TextStyle(
                fontSize: 11,
                color: AppColors.textSecondary,
                fontFamily: 'monospace',
                fontWeight: FontWeight.w500,
              ),
            ),
          ],

          const SizedBox(width: 8),

          // 4. Chevron
          Icon(
            _isExpanded ? Icons.keyboard_arrow_up : Icons.keyboard_arrow_down,
            size: 16,
            color: AppColors.textMuted,
          ),
        ],
      ),
    );
  }

  Widget _buildExpandedHeader(
    bool isRunning,
    bool isError,
    bool isCompleted,
    String? errorMessage,
  ) {
    return Row(
      children: [
        // Status Badge
        _buildStatusIcon(isRunning, isError, isCompleted),
        const SizedBox(width: 12),

        // Title, Error Preview, and Time
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Flexible(
                    child: Text(
                      _getSmartTitle(),
                      style: const TextStyle(
                        fontWeight: FontWeight.w600,
                        fontSize: 14,
                        color: AppColors.textPrimary,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                  if (isRunning) ...[
                    const SizedBox(width: 8),
                    _buildPulsingRunningBadge(),
                  ],
                ],
              ),
              // Error Preview or Duration
              if (isError && errorMessage != null)
                Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Text(
                    errorMessage,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 12,
                      color: AppColors.error.withValues(alpha: 0.8),
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                )
              else if (widget.log.duration != null || isRunning)
                Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Row(
                    children: [
                      if (!isRunning) ...[
                        const Icon(
                          Icons.timer_outlined,
                          size: 12,
                          color: AppColors.textSecondary,
                        ),
                        const SizedBox(width: 4),
                      ],
                      Text(
                        isRunning ? 'Processing...' : widget.log.duration ?? '',
                        style: const TextStyle(
                          fontSize: 12,
                          color: AppColors.textSecondary,
                          fontFamily: 'monospace',
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),

        // Expand icon
        RotationTransition(
          turns: _rotateAnimation,
          child: const Icon(
            Icons.keyboard_arrow_down,
            color: AppColors.textMuted,
            size: 20,
          ),
        ),
      ],
    );
  }

  String _getSmartTitle() => getSmartToolTitle(widget.log.toolName);

  Widget _buildStatusIcon(
    bool isRunning,
    bool isError,
    bool isCompleted, {
    bool compact = false,
  }) {
    // Reduce size for compact mode if needed, effectively already small enough
    // but we can adjust padding.
    final padding = compact ? const EdgeInsets.all(6) : const EdgeInsets.all(8);
    final size = compact ? 16.0 : 18.0;

    if (isRunning) {
      return Container(
        padding: padding,
        decoration: BoxDecoration(
          color: AppColors.warning.withValues(
            alpha: 0.1,
          ), // Amber background like prompt
          borderRadius: BorderRadius.circular(8),
        ),
        child: Icon(
          Icons.bolt,
          size: size,
          color: AppColors.warning,
        ), // Spark/Bolt icon
      );
    }
    if (isError) {
      return Container(
        padding: padding,
        decoration: BoxDecoration(
          color: AppColors.error.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Icon(Icons.error_outline, size: size, color: AppColors.error),
      );
    }
    // Completed
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: AppColors.success.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Icon(Icons.check, size: size, color: AppColors.success),
    );
  }

  Widget _buildPulsingRunningBadge() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: AppColors.warning.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: AppColors.warning.withValues(alpha: 0.5)),
      ),
      child: const Text(
        'Running',
        style: TextStyle(
          fontSize: 9,
          fontWeight: FontWeight.bold,
          color: AppColors.warning,
          letterSpacing: 0.5,
        ),
      ),
    );
  }

  Widget _buildSection({
    required String title,
    required IconData icon,
    required String content,
    required VoidCallback onCopy,
    bool isSuccess = false,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(
              icon,
              size: 12,
              color: isSuccess ? AppColors.success : AppColors.textMuted,
            ),
            const SizedBox(width: 6),
            Text(
              title,
              style: const TextStyle(
                color: AppColors.textMuted,
                fontSize: 11,
                fontWeight: FontWeight.w500,
              ),
            ),
            const Spacer(),
            Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: onCopy,
                borderRadius: BorderRadius.circular(4),
                child: const Padding(
                  padding: EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.copy, size: 11, color: AppColors.textMuted),
                      SizedBox(width: 3),
                      Text(
                        'Copy',
                        style: TextStyle(
                          fontSize: 10,
                          color: AppColors.textMuted,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        _buildCodeBlock(content),
      ],
    );
  }

  Widget _buildErrorSection(String errorMessage) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.error.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: AppColors.error.withValues(alpha: 0.2)),
      ),
      padding: const EdgeInsets.all(8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.warning_amber_rounded,
                size: 12,
                color: AppColors.error,
              ),
              const SizedBox(width: 6),
              const Text(
                'Error',
                style: TextStyle(
                  color: AppColors.error,
                  fontSize: 11,
                  fontWeight: FontWeight.w500,
                ),
              ),
              const Spacer(),
              Material(
                color: Colors.transparent,
                child: InkWell(
                  onTap: () => _copyToClipboard(errorMessage, 'Error'),
                  borderRadius: BorderRadius.circular(4),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 6,
                      vertical: 2,
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.copy,
                          size: 11,
                          color: AppColors.error.withValues(alpha: 0.7),
                        ),
                        const SizedBox(width: 3),
                        Text(
                          'Copy',
                          style: TextStyle(
                            fontSize: 10,
                            color: AppColors.error.withValues(alpha: 0.7),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Container(
            width: double.infinity,
            constraints: const BoxConstraints(maxHeight: 120),
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.3),
              borderRadius: BorderRadius.circular(4),
            ),
            child: SingleChildScrollView(
              child: SelectableText.rich(
                AnsiParser.parse(
                  errorMessage,
                  baseStyle: GoogleFonts.jetBrainsMono(
                    fontSize: 11,
                    color: AppColors.error.withValues(alpha: 0.9),
                    height: 1.4,
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCodeBlock(String content) => ToolCodeBlock(content: content);

  String _formatJson(Map<String, dynamic> json) => formatToolJson(json);

  IconData _getToolIcon(String toolName) => getToolIcon(toolName);
}

// Top-level function for background isolate processing
(bool, String?) _analyzeLogForError(ToolLog log) {
  var isError = false;
  String? errorMessage;

  if (log.status == 'error') {
    isError = true;
  } else if (log.status == 'completed' && log.result != null) {
    final result = log.result!;
    if (result.contains('"error"') || result.contains('"status"')) {
      try {
        final decoded = jsonDecode(result);
        if (decoded is Map) {
          if (decoded.containsKey('error') && decoded['error'] != null) {
            isError = true;
            errorMessage = decoded['error'].toString();
          } else {
            final status = decoded['status']?.toString().toLowerCase();
            if (status != null &&
                (status == 'error' ||
                    status == 'failed' ||
                    status == 'failure')) {
              isError = true;
              errorMessage = 'Task failed with status: ${decoded['status']}';
            }
          }
        }
      } catch (_) {
        if (result.contains('"error": "') ||
            result.contains('"status": "error"')) {
          isError = true;
        }
      }
    }
  }

  if (isError && errorMessage == null && log.result != null) {
    errorMessage = 'Output contains error';
  }

  return (isError, errorMessage);
}
