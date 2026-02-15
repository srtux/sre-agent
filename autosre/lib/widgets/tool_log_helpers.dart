import 'dart:convert';
import 'package:flutter/material.dart';
import '../theme/app_theme.dart';
import '../utils/ansi_parser.dart';
import 'package:google_fonts/google_fonts.dart';

/// Map tool names to user-friendly titles.
String getSmartToolTitle(String name) {
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
  return name
      .replaceAll('_', ' ')
      .split(' ')
      .map(
        (word) =>
            word.isEmpty ? '' : word[0].toUpperCase() + word.substring(1),
      )
      .join(' ');
}

/// Map tool names to appropriate icons.
IconData getToolIcon(String toolName) {
  final lower = toolName.toLowerCase();

  // Analysis / Brain
  if (lower.contains('analysis') ||
      lower.contains('reasoning') ||
      lower.contains('incident') ||
      lower.contains('diagnose')) {
    return Icons.psychology;
  }

  // Radar / Search
  if (lower.contains('promql') ||
      lower.contains('time_series') ||
      lower.contains('log_entries') ||
      lower.contains('sql') ||
      lower.contains('scan') ||
      lower.contains('search')) {
    return Icons.radar;
  }

  // Data / Metrics
  if (lower.contains('metric') || lower.contains('chart')) {
    return Icons.show_chart;
  }

  // Logs
  if (lower.contains('log')) {
    return Icons.article_outlined;
  }

  // Trace
  if (lower.contains('trace') || lower.contains('span')) {
    return Icons.timeline;
  }

  // Cloud / Project
  if (lower.contains('project') ||
      lower.contains('gcp') ||
      lower.contains('cloud')) {
    return Icons.cloud_outlined;
  }

  // Action / Deploy
  if (lower.contains('deploy') ||
      lower.contains('run') ||
      lower.contains('execute')) {
    return Icons.rocket_launch_outlined;
  }

  // Default
  return Icons.construction;
}

/// Format a JSON map for display.
String formatToolJson(Map<String, dynamic> json) {
  if (json.isEmpty) return '(No arguments)';
  try {
    const encoder = JsonEncoder.withIndent('  ');
    return encoder.convert(json);
  } catch (e) {
    return jsonEncode(json);
  }
}

/// A styled code block for displaying tool input/output.
class ToolCodeBlock extends StatelessWidget {
  final String content;

  const ToolCodeBlock({super.key, required this.content});

  @override
  Widget build(BuildContext context) {
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
          child: SelectableText.rich(
            AnsiParser.parse(
              content,
              baseStyle: GoogleFonts.jetBrainsMono(
                fontSize: 11,
                color: AppColors.textSecondary,
                height: 1.4,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
