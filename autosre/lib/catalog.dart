import 'package:flutter/material.dart';
import 'package:genui/genui.dart';
import 'package:json_schema_builder/json_schema_builder.dart';

import 'models/adk_schema.dart';
import 'theme/app_theme.dart';
import 'widgets/error_placeholder.dart';
import 'widgets/log_entries_viewer.dart';
import 'widgets/log_pattern_viewer.dart';
import 'widgets/remediation_plan.dart';
import 'widgets/syncfusion_metric_chart.dart';
import 'widgets/syncfusion_trace_waterfall.dart';
import 'widgets/tool_log.dart';
// Canvas widgets
import 'widgets/canvas/agent_activity_canvas.dart';
import 'widgets/canvas/service_topology_canvas.dart';
import 'widgets/canvas/incident_timeline_canvas.dart';
import 'widgets/canvas/metrics_dashboard_canvas.dart';
import 'widgets/canvas/agent_graph_canvas.dart';
import 'widgets/canvas/agent_trace_canvas.dart';
import 'widgets/canvas/ai_reasoning_canvas.dart';

/// Registry for all SRE-specific UI components.
class CatalogRegistry {
  /// Unwraps component data from various A2UI formats to get the actual data.
  ///
  /// Handles these formats (in priority order):
  /// 1. Direct key match: `{"x-sre-foo": {...}}`
  /// 2. Component wrapper: `{"component": {"x-sre-foo": {...}}}`
  /// 3. Root type match: `{"type": "x-sre-foo", ...}`
  /// 4. Tool-log fallback: fields like `tool_name`, `args`, `status`
  static Map<String, dynamic> _unwrapComponentData(
    dynamic rawData,
    String componentName,
  ) {
    var data = _ensureMap(rawData);

    // 1. Direct key match (e.g. {"x-sre-tool-log": {...}})
    if (data.containsKey(componentName)) {
      final inner = data[componentName];
      if (inner is Map) return Map<String, dynamic>.from(inner);
      if (inner is List) return {componentName: inner};
    }

    // 2. Component wrapper (e.g. {"component": {"x-sre-tool-log": {...}}})
    if (data.containsKey('component') && data['component'] is Map) {
      final inner = data['component'] as Map;
      if (inner.containsKey(componentName)) {
        return Map<String, dynamic>.from(inner[componentName] as Map);
      }
      if (inner['type'] == componentName) {
        return Map<String, dynamic>.from(inner);
      }
    }

    // 3. Root type match (e.g. {"type": "x-sre-tool-log", ...})
    if (data['type'] == componentName) {
      if (data.containsKey(componentName) && data[componentName] is Map) {
        return Map<String, dynamic>.from(data[componentName] as Map);
      }
      return data;
    }

    return data;
  }

  static Catalog createSreCatalog() {
    return Catalog([
      CatalogItem(
        name: 'x-sre-trace-waterfall',
        dataSchema: S.any(),
        widgetBuilder: (context) {
          try {
            final data = _unwrapComponentData(
              context.data,
              'x-sre-trace-waterfall',
            );

            final trace = Trace.fromJson(data);
            if (trace.spans.isEmpty) return const SizedBox.shrink();

            return _buildWidgetContainer(
              child: SyncfusionTraceWaterfall(trace: trace),
              height: null,
            );
          } catch (e) {
            return _logAndBuildError('x-sre-trace-waterfall', e);
          }
        },
      ),
      CatalogItem(
        name: 'x-sre-metric-chart',
        dataSchema: S.any(),
        widgetBuilder: (context) {
          try {
            final data = _unwrapComponentData(
              context.data,
              'x-sre-metric-chart',
            );

            final series = MetricSeries.fromJson(data);
            if (series.points.isEmpty) return const SizedBox.shrink();

            return _buildWidgetContainer(
              child: SyncfusionMetricChart(series: series),
              height: 380,
            );
          } catch (e) {
            return _logAndBuildError('x-sre-metric-chart', e);
          }
        },
      ),
      CatalogItem(
        name: 'x-sre-remediation-plan',
        dataSchema: S.any(),
        widgetBuilder: (context) {
          try {
            final data = _unwrapComponentData(
              context.data,
              'x-sre-remediation-plan',
            );

            final plan = RemediationPlan.fromJson(data);
            if (plan.steps.isEmpty) return const SizedBox.shrink();

            return _buildWidgetContainer(
              child: RemediationPlanWidget(plan: plan),
              height: null, // Auto height based on content
              minHeight: 200,
            );
          } catch (e) {
            return _logAndBuildError('x-sre-remediation-plan', e);
          }
        },
      ),
      CatalogItem(
        name: 'x-sre-log-pattern-viewer',
        dataSchema: S.any(),
        widgetBuilder: (context) {
          try {
            final dataRaw = context.data;
            var rawList = <dynamic>[];

            if (dataRaw is List) {
              rawList = dataRaw;
            } else if (dataRaw is Map) {
              var data = _unwrapComponentData(
                dataRaw,
                'x-sre-log-pattern-viewer',
              );

              // Prefer "patterns" key, then try other common keys
              if (data.containsKey('patterns') && data['patterns'] is List) {
                rawList = data['patterns'] as List;
              } else if (data.containsKey('x-sre-log-pattern-viewer') &&
                  data['x-sre-log-pattern-viewer'] is List) {
                rawList = data['x-sre-log-pattern-viewer'] as List;
              } else {
                rawList =
                    data['data'] ?? data['items'] ?? data['anomalies'] ?? [];
              }
            } else {
              throw Exception(
                'LogPatternViewer: Expected List or Map, got ${dataRaw.runtimeType}',
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
            return _logAndBuildError('x-sre-log-pattern-viewer', e);
          }
        },
      ),
      CatalogItem(
        name: 'x-sre-log-entries-viewer',
        dataSchema: S.any(),
        widgetBuilder: (context) {
          try {
            final data = _unwrapComponentData(
              context.data,
              'x-sre-log-entries-viewer',
            );

            final logData = LogEntriesData.fromJson(data);
            if (logData.entries.isEmpty) return const SizedBox.shrink();

            return _buildWidgetContainer(
              child: LogEntriesViewer(data: logData),
              height: 500,
            );
          } catch (e) {
            return _logAndBuildError('x-sre-log-entries-viewer', e);
          }
        },
      ),
      // Canvas Widgets
      CatalogItem(
        name: 'x-sre-agent-activity',
        dataSchema: S.any(),
        widgetBuilder: (context) {
          try {
            final data = _unwrapComponentData(
              context.data,
              'x-sre-agent-activity',
            );

            final activityData = AgentActivityData.fromJson(data);
            if (activityData.nodes.isEmpty) return const SizedBox.shrink();

            return _buildWidgetContainer(
              child: AgentActivityCanvas(data: activityData),
              height: 450,
            );
          } catch (e) {
            return _logAndBuildError('x-sre-agent-activity', e);
          }
        },
      ),
      CatalogItem(
        name: 'x-sre-service-topology',
        dataSchema: S.any(),
        widgetBuilder: (context) {
          try {
            final data = _unwrapComponentData(
              context.data,
              'x-sre-service-topology',
            );

            final topologyData = ServiceTopologyData.fromJson(data);
            if (topologyData.services.isEmpty) return const SizedBox.shrink();

            return _buildWidgetContainer(
              child: ServiceTopologyCanvas(data: topologyData),
              height: 500,
            );
          } catch (e) {
            return _logAndBuildError('x-sre-service-topology', e);
          }
        },
      ),
      CatalogItem(
        name: 'x-sre-incident-timeline',
        dataSchema: S.any(),
        widgetBuilder: (context) {
          try {
            final data = _unwrapComponentData(
              context.data,
              'x-sre-incident-timeline',
            );

            final timelineData = IncidentTimelineData.fromJson(data);
            if (timelineData.events.isEmpty) return const SizedBox.shrink();

            return _buildWidgetContainer(
              child: IncidentTimelineCanvas(data: timelineData),
              height: 420,
            );
          } catch (e) {
            return _logAndBuildError('x-sre-incident-timeline', e);
          }
        },
      ),
      CatalogItem(
        name: 'x-sre-metrics-dashboard',
        dataSchema: S.any(),
        widgetBuilder: (context) {
          try {
            final data = _unwrapComponentData(
              context.data,
              'x-sre-metrics-dashboard',
            );

            final dashboardData = MetricsDashboardData.fromJson(data);
            if (dashboardData.metrics.isEmpty) return const SizedBox.shrink();

            return _buildWidgetContainer(
              child: MetricsDashboardCanvas(data: dashboardData),
              height: 400,
            );
          } catch (e) {
            return _logAndBuildError('x-sre-metrics-dashboard', e);
          }
        },
      ),
      CatalogItem(
        name: 'x-sre-ai-reasoning',
        dataSchema: S.any(),
        widgetBuilder: (context) {
          try {
            final data = _unwrapComponentData(
              context.data,
              'x-sre-ai-reasoning',
            );

            final reasoningData = AIReasoningData.fromJson(data);
            if (reasoningData.steps.isEmpty &&
                (reasoningData.conclusion == null ||
                    reasoningData.conclusion!.isEmpty)) {
              return const SizedBox.shrink();
            }

            return _buildWidgetContainer(
              child: AIReasoningCanvas(data: reasoningData),
              height: 480,
            );
          } catch (e) {
            return _logAndBuildError('x-sre-ai-reasoning', e);
          }
        },
      ),
      CatalogItem(
        name: 'x-sre-agent-trace',
        dataSchema: S.any(),
        widgetBuilder: (context) {
          try {
            final data = _unwrapComponentData(
              context.data,
              'x-sre-agent-trace',
            );

            final traceData = AgentTraceData.fromJson(data);
            if (traceData.nodes.isEmpty) return const SizedBox.shrink();

            return _buildWidgetContainer(
              child: AgentTraceCanvas(data: traceData),
              height: 550,
            );
          } catch (e) {
            return _logAndBuildError('x-sre-agent-trace', e);
          }
        },
      ),
      CatalogItem(
        name: 'x-sre-agent-graph',
        dataSchema: S.any(),
        widgetBuilder: (context) {
          try {
            final data = _unwrapComponentData(
              context.data,
              'x-sre-agent-graph',
            );

            final graphData = AgentGraphData.fromJson(data);
            if (graphData.nodes.isEmpty) return const SizedBox.shrink();

            return _buildWidgetContainer(
              child: AgentGraphCanvas(data: graphData),
              height: 500,
            );
          } catch (e) {
            return _logAndBuildError('x-sre-agent-graph', e);
          }
        },
      ),
      CatalogItem(
        name: 'x-sre-tool-log',
        dataSchema: S.any(),
        widgetBuilder: (context) {
          try {
            final data = _unwrapComponentData(
              context.data,
              'x-sre-tool-log',
            );

            final log = ToolLog.fromJson(data);
            return ToolLogWidget(log: log);
          } catch (e) {
            return _logAndBuildError('x-sre-tool-log', e);
          }
        },
      ),
    ], catalogId: 'sre-catalog');
  }

  /// Logs a component render error and returns an [ErrorPlaceholder].
  static Widget _logAndBuildError(String componentName, Object error) {
    debugPrint('[CATALOG] $componentName render error: $error');
    return ErrorPlaceholder(error: error);
  }

  /// Helper to safely cast dynamic data to a Map, throwing a clear error if mismatch
  static Map<String, dynamic> _ensureMap(dynamic data) {
    if (data == null) return {};
    if (data is Map) {
      return Map<String, dynamic>.from(data);
    }
    throw Exception(
      'Expected Map<String, dynamic>, got ${data.runtimeType}: $data',
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
