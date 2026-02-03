import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../services/dashboard_state.dart';
import '../../services/project_service.dart';
import '../../theme/app_theme.dart';
import '../trace_waterfall.dart';

/// Dashboard panel that displays all collected trace results.
///
/// Shows traces in a scrollable list with expandable waterfall views.
/// Each trace shows a summary header with span count and duration,
/// and can be expanded to reveal the full waterfall visualization.
class LiveTracePanel extends StatefulWidget {
  final List<DashboardItem> items;
  const LiveTracePanel({super.key, required this.items});

  @override
  State<LiveTracePanel> createState() => _LiveTracePanelState();
}

class _LiveTracePanelState extends State<LiveTracePanel> {
  int? _expandedIndex;

  @override
  Widget build(BuildContext context) {
    if (widget.items.isEmpty) return const SizedBox.shrink();

    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: widget.items.length,
      itemBuilder: (context, index) {
        final item = widget.items[index];
        final trace = item.traceData;
        if (trace == null) return const SizedBox.shrink();

        final isExpanded = _expandedIndex == index;
        final totalDuration = _calcTotalDuration(trace);

        return Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            decoration: BoxDecoration(
              color: isExpanded
                  ? AppColors.primaryCyan.withValues(alpha: 0.05)
                  : AppColors.backgroundCard,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: isExpanded
                    ? AppColors.primaryCyan.withValues(alpha: 0.3)
                    : AppColors.surfaceBorder,
              ),
            ),
            child: Column(
              children: [
                // Header
                InkWell(
                  onTap: () {
                    setState(() {
                      _expandedIndex = isExpanded ? null : index;
                    });
                  },
                  borderRadius: BorderRadius.circular(12),
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.all(6),
                          decoration: BoxDecoration(
                            color:
                                AppColors.primaryCyan.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: const Icon(
                            Icons.timeline_rounded,
                            size: 14,
                            color: AppColors.primaryCyan,
                          ),
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                trace.traceId.length > 16
                                    ? '${trace.traceId.substring(0, 16)}...'
                                    : trace.traceId,
                                style: GoogleFonts.jetBrainsMono(
                                  fontSize: 12,
                                  fontWeight: FontWeight.w500,
                                  color: AppColors.textPrimary,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                '${trace.spans.length} spans  |  ${totalDuration}ms  |  ${item.toolName}',
                                style: const TextStyle(
                                  fontSize: 11,
                                  color: AppColors.textMuted,
                                ),
                              ),
                            ],
                          ),
                        ),
                        _buildCloudTraceButton(trace.traceId),
                        const SizedBox(width: 4),
                        Icon(
                          isExpanded
                              ? Icons.keyboard_arrow_up
                              : Icons.keyboard_arrow_down,
                          size: 18,
                          color: AppColors.textMuted,
                        ),
                      ],
                    ),
                  ),
                ),
                // Expanded waterfall
                if (isExpanded)
                  Container(
                    padding: const EdgeInsets.fromLTRB(8, 0, 8, 8),
                    child: TraceWaterfall(trace: trace),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildCloudTraceButton(String traceId) {
    return Tooltip(
      message: 'Open in Cloud Trace',
      child: InkWell(
        borderRadius: BorderRadius.circular(4),
        onTap: () async {
          final projectId =
              ProjectService.instance.selectedProject.value?.projectId;
          if (projectId == null) return;
          final url = Uri.parse(
            'https://console.cloud.google.com/traces/list'
            '?tid=$traceId&project=$projectId',
          );
          if (await canLaunchUrl(url)) {
            await launchUrl(url, mode: LaunchMode.externalApplication);
          }
        },
        child: Padding(
          padding: const EdgeInsets.all(4),
          child: Icon(
            Icons.open_in_new_rounded,
            size: 14,
            color: AppColors.primaryCyan.withValues(alpha: 0.7),
          ),
        ),
      ),
    );
  }

  String _calcTotalDuration(dynamic trace) {
    if (trace.spans.isEmpty) return '0';
    try {
      DateTime? earliest;
      DateTime? latest;
      for (final span in trace.spans) {
        if (earliest == null || span.startTime.isBefore(earliest)) {
          earliest = span.startTime;
        }
        if (latest == null || span.endTime.isAfter(latest)) {
          latest = span.endTime;
        }
      }
      if (earliest != null && latest != null) {
        return latest.difference(earliest).inMilliseconds.toString();
      }
    } catch (_) {}
    return '?';
  }
}
