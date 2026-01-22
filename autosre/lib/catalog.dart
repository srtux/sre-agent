import 'package:flutter/material.dart';
import 'package:genui/genui.dart';
import 'package:json_schema_builder/json_schema_builder.dart';

import 'models/adk_schema.dart';
import 'theme/app_theme.dart';
import 'widgets/error_placeholder.dart';
import 'widgets/log_entries_viewer.dart';
import 'widgets/log_pattern_viewer.dart';
import 'widgets/metric_chart.dart';
import 'widgets/remediation_plan.dart';
import 'widgets/tool_log.dart';
import 'widgets/trace_waterfall.dart';
// Canvas widgets
import 'widgets/canvas/agent_activity_canvas.dart';
import 'widgets/canvas/service_topology_canvas.dart';
import 'widgets/canvas/incident_timeline_canvas.dart';
import 'widgets/canvas/metrics_dashboard_canvas.dart';
import 'widgets/canvas/ai_reasoning_canvas.dart';

/// Registry for all SRE-specific UI components.
class CatalogRegistry {
  static Catalog createSreCatalog() {
    return Catalog([
      CatalogItem(
        name: "x-sre-trace-waterfall",
        dataSchema: S.object(),
        widgetBuilder: (context) {
          try {
            var data = _ensureMap(context.data);

            // Handle case where data might be wrapped in component name
            // (e.g., {"x-sre-trace-waterfall": {...actual data...}})
            if (data.containsKey('x-sre-trace-waterfall') &&
                data['x-sre-trace-waterfall'] is Map) {
              data = Map<String, dynamic>.from(
                data['x-sre-trace-waterfall'] as Map,
              );
            }

            final trace = Trace.fromJson(data);
            if (trace.spans.isEmpty) return const SizedBox.shrink();

            return _buildWidgetContainer(
              child: TraceWaterfall(trace: trace),
              height: 380,
            );
          } catch (e) {
            return ErrorPlaceholder(error: e);
          }
        },
      ),
      CatalogItem(
        name: "x-sre-metric-chart",
        dataSchema: S.object(),
        widgetBuilder: (context) {
          try {
            final data = _ensureMap(context.data);
            final series = MetricSeries.fromJson(data);
            if (series.points.isEmpty) return const SizedBox.shrink();

            return _buildWidgetContainer(
              child: MetricCorrelationChart(series: series),
              height: 380,
            );
          } catch (e) {
            return ErrorPlaceholder(error: e);
          }
        },
      ),
      CatalogItem(
        name: "x-sre-remediation-plan",
        dataSchema: S.object(),
        widgetBuilder: (context) {
          try {
            final data = _ensureMap(context.data);
            final plan = RemediationPlan.fromJson(data);
            if (plan.steps.isEmpty) return const SizedBox.shrink();

            return _buildWidgetContainer(
              child: RemediationPlanWidget(plan: plan),
              height: null, // Auto height based on content
              minHeight: 200,
            );
          } catch (e) {
            return ErrorPlaceholder(error: e);
          }
        },
      ),
      CatalogItem(
        name: "x-sre-log-pattern-viewer",
        dataSchema: S.object(),
        widgetBuilder: (context) {
          try {
            List<dynamic> rawList;
            final data = context.data;

            if (data is List) {
              rawList = data;
            } else if (data is Map) {
              // Handle case where list is wrapped in a map
              rawList = data['patterns'] ?? data['data'] ?? data['items'] ?? [];
            } else {
              throw Exception(
                "Expected List or Map with patterns, got ${data.runtimeType}",
              );
            }

            final patterns = rawList
                .map(
                  (item) =>
                      LogPattern.fromJson(Map<String, dynamic>.from(item)),
                )
                .toList();

            if (patterns.isEmpty) return const SizedBox.shrink();

            return _buildWidgetContainer(
              child: LogPatternViewer(patterns: patterns),
              height: 450,
            );
          } catch (e) {
            return ErrorPlaceholder(error: e);
          }
        },
      ),
      CatalogItem(
        name: "x-sre-log-entries-viewer",
        dataSchema: S.object(),
        widgetBuilder: (context) {
          try {
            final data = _ensureMap(context.data);
            final logData = LogEntriesData.fromJson(data);
            if (logData.entries.isEmpty) return const SizedBox.shrink();

            return _buildWidgetContainer(
              child: LogEntriesViewer(data: logData),
              height: 500,
            );
          } catch (e) {
            return ErrorPlaceholder(error: e);
          }
        },
      ),
      CatalogItem(
        name: "x-sre-tool-log",
        dataSchema: S.object(),
        widgetBuilder: (context) {
          try {
            final data = _ensureMap(context.data);
            final log = ToolLog.fromJson(data);
            if (log.toolName.isEmpty && log.status == 'unknown') return const SizedBox.shrink();
            return ToolLogWidget(log: log);
          } catch (e) {
            return ErrorPlaceholder(error: e);
          }
        },
      ),
      // Canvas Widgets
      CatalogItem(
        name: "x-sre-agent-activity",
        dataSchema: S.object(),
        widgetBuilder: (context) {
          try {
            final data = _ensureMap(context.data);
            final activityData = AgentActivityData.fromJson(data);
            if (activityData.nodes.isEmpty) return const SizedBox.shrink();

            return _buildWidgetContainer(
              child: AgentActivityCanvas(data: activityData),
              height: 450,
            );
          } catch (e) {
            return ErrorPlaceholder(error: e);
          }
        },
      ),
      CatalogItem(
        name: "x-sre-service-topology",
        dataSchema: S.object(),
        widgetBuilder: (context) {
          try {
            final data = _ensureMap(context.data);
            final topologyData = ServiceTopologyData.fromJson(data);
            if (topologyData.services.isEmpty) return const SizedBox.shrink();

            return _buildWidgetContainer(
              child: ServiceTopologyCanvas(data: topologyData),
              height: 500,
            );
          } catch (e) {
            return ErrorPlaceholder(error: e);
          }
        },
      ),
      CatalogItem(
        name: "x-sre-incident-timeline",
        dataSchema: S.object(),
        widgetBuilder: (context) {
          try {
            final data = _ensureMap(context.data);
            final timelineData = IncidentTimelineData.fromJson(data);
            if (timelineData.events.isEmpty) return const SizedBox.shrink();

            return _buildWidgetContainer(
              child: IncidentTimelineCanvas(data: timelineData),
              height: 420,
            );
          } catch (e) {
            return ErrorPlaceholder(error: e);
          }
        },
      ),
      CatalogItem(
        name: "x-sre-metrics-dashboard",
        dataSchema: S.object(),
        widgetBuilder: (context) {
          try {
            final data = _ensureMap(context.data);
            final dashboardData = MetricsDashboardData.fromJson(data);
            if (dashboardData.metrics.isEmpty) return const SizedBox.shrink();

            return _buildWidgetContainer(
              child: MetricsDashboardCanvas(data: dashboardData),
              height: 400,
            );
          } catch (e) {
            return ErrorPlaceholder(error: e);
          }
        },
      ),
      CatalogItem(
        name: "x-sre-ai-reasoning",
        dataSchema: S.object(),
        widgetBuilder: (context) {
          try {
            final data = _ensureMap(context.data);
            final reasoningData = AIReasoningData.fromJson(data);
            if (reasoningData.steps.isEmpty && (reasoningData.conclusion == null || reasoningData.conclusion!.isEmpty)) {
              return const SizedBox.shrink();
            }

            return _buildWidgetContainer(
              child: AIReasoningCanvas(data: reasoningData),
              height: 480,
            );
          } catch (e) {
            return ErrorPlaceholder(error: e);
          }
        },
      ),
    ], catalogId: "sre-catalog");
  }

  /// Helper to safely cast dynamic data to a Map, throwing a clear error if mismatch
  static Map<String, dynamic> _ensureMap(dynamic data) {
    if (data == null) return {};
    if (data is Map) {
      return Map<String, dynamic>.from(data);
    }
    throw Exception(
      "Expected Map<String, dynamic>, got ${data.runtimeType}: $data",
    );
  }

  /// Builds a styled container for widgets with consistent theming
  static Widget _buildWidgetContainer({
    required Widget child,
    double? height,
    double? minHeight,
  }) {
    return Container(
      height: height,
      constraints: minHeight != null
          ? BoxConstraints(minHeight: minHeight)
          : null,
      decoration: BoxDecoration(
        color: AppColors.backgroundCard,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.surfaceBorder, width: 1),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.2),
            blurRadius: 16,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: child,
    );
  }
}
