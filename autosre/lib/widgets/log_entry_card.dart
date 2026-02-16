import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../models/adk_schema.dart';
import '../theme/app_theme.dart';
import '../theme/design_tokens.dart';
import '../utils/ansi_parser.dart';
import 'package:google_fonts/google_fonts.dart';

/// An expandable log entry card with severity indicator and detail sections.
class LogEntryCard extends StatefulWidget {
  final LogEntry entry;
  final double animationValue;

  const LogEntryCard({
    super.key,
    required this.entry,
    required this.animationValue,
  });

  @override
  State<LogEntryCard> createState() => _LogEntryCardState();
}

class _LogEntryCardState extends State<LogEntryCard> {
  bool _isExpanded = false;

  Color _getSeverityColor(String severity) {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
      case 'EMERGENCY':
      case 'ALERT':
        return SeverityColors.critical;
      case 'ERROR':
        return AppColors.error;
      case 'WARNING':
        return AppColors.warning;
      case 'INFO':
      case 'NOTICE':
        return AppColors.info;
      case 'DEBUG':
        return AppColors.textMuted;
      default:
        return AppColors.textSecondary;
    }
  }

  IconData _getSeverityIcon(String severity) {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
      case 'EMERGENCY':
      case 'ALERT':
        return Icons.crisis_alert;
      case 'ERROR':
        return Icons.error;
      case 'WARNING':
        return Icons.warning_amber;
      case 'INFO':
      case 'NOTICE':
        return Icons.info_outline;
      case 'DEBUG':
        return Icons.bug_report_outlined;
      default:
        return Icons.circle_outlined;
    }
  }

  @override
  Widget build(BuildContext context) {
    final severityColor = _getSeverityColor(widget.entry.severity);

    return AnimatedOpacity(
      duration: const Duration(milliseconds: 200),
      opacity: widget.animationValue,
      child: Container(
        margin: const EdgeInsets.only(bottom: 6),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.02),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: _isExpanded
                ? severityColor.withValues(alpha: 0.3)
                : AppColors.surfaceBorder,
          ),
        ),
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header row (always visible)
            InkWell(
              onTap: () => setState(() => _isExpanded = !_isExpanded),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Severity indicator
                    Container(
                      width: 4,
                      height: 40,
                      decoration: BoxDecoration(
                        color: severityColor,
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                    const SizedBox(width: 10),
                    // Severity icon
                    Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: severityColor.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Icon(
                        _getSeverityIcon(widget.entry.severity),
                        size: 14,
                        color: severityColor,
                      ),
                    ),
                    const SizedBox(width: 10),
                    // Content
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          // Timestamp and severity badge
                          Row(
                            children: [
                              Text(
                                _formatTimestamp(widget.entry.timestamp),
                                style: const TextStyle(
                                  fontSize: 10,
                                  color: AppColors.textMuted,
                                  fontFamily: 'monospace',
                                ),
                              ),
                              const SizedBox(width: 8),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 5,
                                  vertical: 2,
                                ),
                                decoration: BoxDecoration(
                                  color: severityColor.withValues(alpha: 0.15),
                                  borderRadius: BorderRadius.circular(3),
                                ),
                                child: Text(
                                  widget.entry.severity,
                                  style: TextStyle(
                                    fontSize: 9,
                                    fontWeight: FontWeight.w600,
                                    color: severityColor,
                                  ),
                                ),
                              ),
                              const SizedBox(width: 8),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 5,
                                  vertical: 2,
                                ),
                                decoration: BoxDecoration(
                                  color: AppColors.primaryTeal.withValues(
                                    alpha: 0.1,
                                  ),
                                  borderRadius: BorderRadius.circular(3),
                                ),
                                child: Text(
                                  widget.entry.resourceType,
                                  style: const TextStyle(
                                    fontSize: 9,
                                    color: AppColors.primaryTeal,
                                  ),
                                ),
                              ),
                              if (widget.entry.isJsonPayload) ...[
                                const SizedBox(width: 8),
                                const Icon(
                                  Icons.data_object,
                                  size: 12,
                                  color: AppColors.primaryCyan,
                                ),
                              ],
                            ],
                          ),
                          const SizedBox(height: 6),
                          // Message preview
                          RichText(
                            text: AnsiParser.parse(
                              widget.entry.payloadPreview,
                              baseStyle: GoogleFonts.jetBrainsMono(
                                fontSize: 11,
                                color: AppColors.textPrimary,
                                height: 1.4,
                              ),
                            ),
                            maxLines: _isExpanded ? null : 2,
                            overflow: _isExpanded
                                ? TextOverflow.visible
                                : TextOverflow.ellipsis,
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 8),
                    // Expand icon
                    AnimatedRotation(
                      duration: const Duration(milliseconds: 200),
                      turns: _isExpanded ? 0.5 : 0,
                      child: const Icon(
                        Icons.keyboard_arrow_down,
                        size: 20,
                        color: AppColors.textMuted,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            // Expanded details
            if (_isExpanded) _buildExpandedDetails(),
          ],
        ),
      ),
    );
  }

  Widget _buildExpandedDetails() {
    final entry = widget.entry;
    return Container(
      decoration: BoxDecoration(
        color: Colors.black.withValues(alpha: 0.2),
        border: const Border(top: BorderSide(color: AppColors.surfaceBorder)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Resource labels
          if (entry.resourceLabels.isNotEmpty)
            _buildDetailSection(
              'Resource Labels',
              Icons.label_outline,
              entry.resourceLabels.entries
                  .map((e) => _buildLabelChip(e.key, e.value))
                  .toList(),
            ),
          // Trace info
          if (entry.traceId != null || entry.spanId != null)
            _buildDetailSection('Trace Info', Icons.account_tree_outlined, [
              if (entry.traceId != null)
                _buildLabelChip('trace_id', entry.traceId!),
              if (entry.spanId != null)
                _buildLabelChip('span_id', entry.spanId!),
            ]),
          // HTTP Request
          if (entry.httpRequest != null)
            _buildDetailSection('HTTP Request', Icons.http, [
              if (entry.httpRequest!['requestMethod'] != null)
                _buildLabelChip(
                  'method',
                  entry.httpRequest!['requestMethod'].toString(),
                ),
              if (entry.httpRequest!['status'] != null)
                _buildLabelChip(
                  'status',
                  entry.httpRequest!['status'].toString(),
                ),
              if (entry.httpRequest!['latency'] != null)
                _buildLabelChip(
                  'latency',
                  entry.httpRequest!['latency'].toString(),
                ),
            ]),
          // Full JSON payload
          if (entry.isJsonPayload)
            _buildJsonPayloadSection(entry.payload as Map<String, dynamic>),
          // Actions
          Padding(
            padding: const EdgeInsets.all(12),
            child: Row(
              children: [
                _buildActionButton('Copy Log', Icons.copy, () {
                  _copyToClipboard(context, _formatFullLog(entry));
                }),
                const SizedBox(width: 8),
                if (entry.isJsonPayload)
                  _buildActionButton('Copy JSON', Icons.data_object, () {
                    _copyToClipboard(
                      context,
                      const JsonEncoder.withIndent('  ').convert(entry.payload),
                    );
                  }),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildDetailSection(
    String title,
    IconData icon,
    List<Widget> children,
  ) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 12, color: AppColors.textMuted),
              const SizedBox(width: 6),
              Text(
                title,
                style: const TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textMuted,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Wrap(spacing: 6, runSpacing: 6, children: children),
        ],
      ),
    );
  }

  Widget _buildLabelChip(String key, String value) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: AppColors.primaryTeal.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(
          color: AppColors.primaryTeal.withValues(alpha: 0.15),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '$key:',
            style: const TextStyle(
              fontSize: 10,
              color: AppColors.textMuted,
              fontFamily: 'monospace',
            ),
          ),
          const SizedBox(width: 4),
          Flexible(
            child: Text(
              value,
              style: const TextStyle(
                fontSize: 10,
                color: AppColors.primaryTeal,
                fontFamily: 'monospace',
                fontWeight: FontWeight.w500,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildJsonPayloadSection(Map<String, dynamic> payload) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.data_object, size: 12, color: AppColors.primaryCyan),
              SizedBox(width: 6),
              Text(
                'JSON Payload',
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w600,
                  color: AppColors.textMuted,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: Colors.black.withValues(alpha: 0.4),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: AppColors.surfaceBorder.withValues(alpha: 0.5),
              ),
            ),
            child: SelectableText(
              const JsonEncoder.withIndent('  ').convert(payload),
              style: const TextStyle(
                fontSize: 11,
                color: AppColors.textSecondary,
                fontFamily: 'monospace',
                height: 1.5,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionButton(String label, IconData icon, VoidCallback onTap) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(6),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: AppColors.primaryTeal.withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: AppColors.primaryTeal.withValues(alpha: 0.2),
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 12, color: AppColors.primaryTeal),
            const SizedBox(width: 6),
            Text(
              label,
              style: const TextStyle(
                fontSize: 10,
                color: AppColors.primaryTeal,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }

  String _formatTimestamp(DateTime timestamp) {
    final now = DateTime.now();
    final diff = now.difference(timestamp);

    String timeStr;
    if (diff.inDays > 0) {
      timeStr =
          '${timestamp.month}/${timestamp.day} ${timestamp.hour.toString().padLeft(2, '0')}:${timestamp.minute.toString().padLeft(2, '0')}:${timestamp.second.toString().padLeft(2, '0')}';
    } else {
      timeStr =
          '${timestamp.hour.toString().padLeft(2, '0')}:${timestamp.minute.toString().padLeft(2, '0')}:${timestamp.second.toString().padLeft(2, '0')}.${timestamp.millisecond.toString().padLeft(3, '0')}';
    }
    return timeStr;
  }

  String _formatFullLog(LogEntry entry) {
    final buffer = StringBuffer();
    buffer.writeln('Timestamp: ${entry.timestamp.toIso8601String()}');
    buffer.writeln('Severity: ${entry.severity}');
    buffer.writeln('Resource: ${entry.resourceType}');
    buffer.writeln('Labels: ${entry.resourceLabels}');
    if (entry.traceId != null) buffer.writeln('Trace ID: ${entry.traceId}');
    if (entry.spanId != null) buffer.writeln('Span ID: ${entry.spanId}');
    buffer.writeln('---');
    if (entry.isJsonPayload) {
      buffer.writeln(const JsonEncoder.withIndent('  ').convert(entry.payload));
    } else {
      buffer.writeln(entry.payload?.toString() ?? '');
    }
    return buffer.toString();
  }

  void _copyToClipboard(BuildContext context, String text) {
    Clipboard.setData(ClipboardData(text: text));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Row(
          children: [
            Icon(Icons.check_circle, color: AppColors.success, size: 16),
            SizedBox(width: 8),
            Text('Copied to clipboard'),
          ],
        ),
        backgroundColor: AppColors.backgroundElevated,
        duration: Duration(seconds: 2),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }
}
