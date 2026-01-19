import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../models/adk_schema.dart';
import '../theme/app_theme.dart';

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

    // Auto-expand if running? User requested collapsed by default.
    // So we keep it false.
    // if (widget.log.status == 'running') {
    //   _isExpanded = true;
    //   _animationController.value = 1.0;
    // }
  }

  @override
  void didUpdateWidget(ToolLogWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    // Auto-expand when status changes to running? No, user wants compact default.
    // if (widget.log.status == 'running' && !_isExpanded) {
    //   _toggleExpand();
    // }
    // Auto-collapse when status changes to completed to reduce noise?
    // It's already collapsed by default, so we might not need this,
    // but if user expanded it, we might want to keep it expanded or collapse it.
    // Let's leave user control.
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
            Icon(Icons.check_circle, color: AppColors.success, size: 18),
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
    bool isError = widget.log.status == 'error'; // Mutable to upgrade to error on inspection
    final completed = widget.log.status == 'completed';

    Color statusColor;
    IconData statusIcon;
    String statusLabel;

    if (isRunning) {
      statusColor = AppColors.info;
      statusIcon = Icons.sync;
      statusLabel = 'Running';
    } else if (isError) {
      statusColor = AppColors.error;
      statusIcon = Icons.error_outline;
      statusLabel = 'Error';
    } else {
      statusColor = AppColors.success;
      statusIcon = Icons.check_circle_outline;
      statusLabel = 'Completed';
    }

    // Strict Error Handling: Check content for "error" key
    String? errorMessage;
    if (completed && widget.log.result != null) {
      final result = widget.log.result!;
      // Simple check for error key in JSON string
      if (result.contains('"error"')) {
         // Try to parse to confirm or extract
         try {
           final decoded = jsonDecode(result);
           if (decoded is Map && decoded.containsKey('error')) {
             isError = true;
             // Extract error message
             final errorVal = decoded['error'];
             errorMessage = errorVal.toString();
           }
         } catch (_) {
           // Fallback regex or simple check
           if (result.contains('"error":')) {
             isError = true;
             errorMessage = "Output contains error"; // Fallback
           }
         }
      }
    }

    // Re-evaluate styles if error detected
    if (isError) {
      statusColor = AppColors.error;
      statusIcon = Icons.error_outline;
      statusLabel = 'Error';
    }

    final toolIcon = _getToolIcon(widget.log.toolName);

    // Compact collapsed view vs expanded view
    return AnimatedContainer(
      duration: const Duration(milliseconds: 150),
      margin: EdgeInsets.symmetric(vertical: _isExpanded ? 4 : 2),
      constraints: const BoxConstraints(minHeight: 56.0),
      decoration: BoxDecoration(
        color: isError
           ? AppColors.error.withValues(alpha: 0.1)
           : AppColors.backgroundElevated.withValues(alpha: 0.8), // Premium Gray
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
           color: isError
               ? AppColors.error.withValues(alpha: 0.3)
               : Colors.white.withValues(alpha: 0.08),
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
              borderRadius: BorderRadius.circular(_isExpanded ? 10 : 8),
              child: Padding(
                padding: EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 12, // More padding for "Card" feel
                ),
                child: Row(
                  children: [
                    // Status Badge
                    _buildStatusIcon(isRunning, isError, completed),
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
                                    style: TextStyle(
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
                                ]
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
                                      Icon(Icons.timer_outlined, size: 12, color: AppColors.textSecondary),
                                      const SizedBox(width: 4),
                                    ],
                                    Text(
                                      isRunning ? 'Processing...' : widget.log.duration ?? '',
                                      style: TextStyle(
                                        fontSize: 12, // Slightly larger for readability
                                        color: AppColors.textSecondary,
                                        fontFamily: 'monospace', // Monospace for numbers
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
                      child: Icon(
                        Icons.keyboard_arrow_down,
                        color: AppColors.textMuted,
                        size: 20,
                      ),
                    ),
                  ],
                ),
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
                      // Output section
                      if (completed && widget.log.result != null) ...[
                        const SizedBox(height: 10),
                        _buildSection(
                          title: 'Output',
                          icon: Icons.output,
                          content: widget.log.result!,
                          onCopy: () => _copyToClipboard(
                            widget.log.result!,
                            'Output',
                          ),
                          isSuccess: true,
                        ),
                      ],
                      // Error section
                      if (isError && widget.log.result != null) ...[
                        const SizedBox(height: 10),
                        _buildErrorSection(errorMessage ?? widget.log.result!),
                      ],
                      // If strict error detection triggered but not original error status, show output as error
                      if (isError && !widget.log.status.contains('error') && widget.log.result != null) ...[
                         const SizedBox(height: 10),
                         _buildErrorSection(widget.log.result!),
                      ]
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

  String _getSmartTitle() {
      final name = widget.log.toolName;
      if (name == 'run_log_pattern_analysis') return 'Analyzing Log Patterns';
      if (name == 'list_traces') return 'Scanning System Traces';
      if (name == 'query_promql') return 'Querying Performance Metrics';
      if (name == 'mcp_execute_sql') return 'Executing SQL Query';
      if (name == 'list_active_incidents') return 'Fetching Active Incidents';
      if (name == 'run_query') return 'Executing Data Query';
      if (name == 'list_log_entries') return 'Scanning Cloud Logs';
      if (name == 'get_service_health') return 'Checking Service Health';
      if (name == 'list_time_series') return 'Fetching Time Series Data';
      if (name == 'extract_log_patterns') return 'Extracting Log Patterns';
      if (name == 'fetch_trace') return 'Fetching Trace Details';

      // Fallback: sentence case with replacements
      return name.replaceAll('_', ' ').split(' ').map((word) => word.isEmpty ? '' : word[0].toUpperCase() + word.substring(1)).join(' ');
  }

  Widget _buildStatusIcon(bool isRunning, bool isError, bool isCompleted) {
       if (isRunning) {
         return Container(
           padding: const EdgeInsets.all(8),
           decoration: BoxDecoration(
             color: AppColors.warning.withValues(alpha: 0.1), // Amber background like prompt
             borderRadius: BorderRadius.circular(8),
           ),
           child: const Icon(Icons.bolt, size: 18, color: AppColors.warning), // Spark/Bolt icon
         );
       }
       if (isError) {
          return Container(
           padding: const EdgeInsets.all(8),
           decoration: BoxDecoration(
             color: AppColors.error.withValues(alpha: 0.1),
             borderRadius: BorderRadius.circular(8),
           ),
           child: const Icon(Icons.error_outline, size: 18, color: AppColors.error),
         );
       }
       // Completed
       return Container(
           padding: const EdgeInsets.all(8),
           decoration: BoxDecoration(
             color: AppColors.success.withValues(alpha: 0.1),
             borderRadius: BorderRadius.circular(8),
           ),
           child: const Icon(Icons.check, size: 18, color: AppColors.success),
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
          child: Text(
            'Running',
            style: TextStyle(
              fontSize: 9,
              fontWeight: FontWeight.bold,
              color: AppColors.warning,
              letterSpacing: 0.5,
            )
          )
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
              style: TextStyle(
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
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.copy,
                        size: 11,
                        color: AppColors.textMuted,
                      ),
                      const SizedBox(width: 3),
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
        border: Border.all(
          color: AppColors.error.withValues(alpha: 0.2),
        ),
      ),
      padding: const EdgeInsets.all(8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.warning_amber_rounded,
                size: 12,
                color: AppColors.error,
              ),
              const SizedBox(width: 6),
              Text(
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
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
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
              child: SelectableText(
                errorMessage,
                style: TextStyle(
                  fontFamily: 'monospace',
                  fontSize: 11,
                  color: AppColors.error.withValues(alpha: 0.9),
                  height: 1.4,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildCodeBlock(String content) {
    return Container(
      width: double.infinity,
      constraints: const BoxConstraints(maxHeight: 160),
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.3),
        borderRadius: BorderRadius.circular(6),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(6),
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(8),
          child: SelectableText(
            content,
            style: const TextStyle(
              fontFamily: 'monospace',
              fontSize: 11,
              color: AppColors.textSecondary,
              height: 1.4,
            ),
          ),
        ),
      ),
    );
  }

  String _formatJson(Map<String, dynamic> json) {
    if (json.isEmpty) return '(No arguments)';
    try {
      const encoder = JsonEncoder.withIndent('  ');
      return encoder.convert(json);
    } catch (e) {
      return jsonEncode(json);
    }
  }

  IconData _getToolIcon(String toolName) {
    if (toolName.contains('trace') || toolName.contains('span')) return Icons.timeline;
    if (toolName.contains('metric') || toolName.contains('promql') || toolName.contains('time_series')) return Icons.show_chart;
    if (toolName.contains('log')) return Icons.article_outlined;
    if (toolName.contains('remediation')) return Icons.medical_services_outlined;
    if (toolName.contains('project')) return Icons.cloud_outlined;
    if (toolName.contains('deploy')) return Icons.rocket_launch_outlined;
    return Icons.construction; // Default
  }

  String _formatTimestamp(String? timestamp) {
    if (timestamp == null) return '';
    try {
      // Handle standard float timestamp (seconds since epoch)
      final double ts = double.parse(timestamp);
      final dt = DateTime.fromMillisecondsSinceEpoch((ts * 1000).toInt());
      return '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}:${dt.second.toString().padLeft(2, '0')}';
    } catch (e) {
      // Fallback for legacy generic timestamps or UUID-time
      if (RegExp(r'^\d{13,}$').hasMatch(timestamp)) {
         try {
           // ... (legacy logic if needed, but likely fine to just return raw if parse fails)
           return timestamp;
         } catch (_) {}
      }
      return timestamp;
    }
  }
}
