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
  /// Debug counter for unwrap operations
  static int _unwrapCount = 0;

  /// Unwraps component data from various A2UI formats to get the actual data.
  ///
  /// Handles these formats (in order of processing):
  /// 1. A2UI v0.8: `{"id": "...", "component": {"x-sre-foo": {...}}}`
  /// 2. Legacy component wrapper: `{"component": {"x-sre-foo": {...}}}`
  /// 3. Component-name wrapped: `{"x-sre-foo": {...}}`
  /// 4. Direct data: `{...actual data...}`
  static Map<String, dynamic> _unwrapComponentData(
    dynamic rawData,
    String componentName,
  ) {
    _unwrapCount++;
    final callId = _unwrapCount;

    debugPrint('🔓 [UNWRAP #$callId] ===== _unwrapComponentData START =====');
    debugPrint('🔓 [UNWRAP #$callId] componentName: $componentName');
    debugPrint('🔓 [UNWRAP #$callId] rawData type: ${rawData.runtimeType}');
    debugPrint('🔓 [UNWRAP #$callId] rawData: ${rawData.toString().length > 500 ? "${rawData.toString().substring(0, 500)}..." : rawData}');

    var data = _ensureMap(rawData);

    debugPrint('🔓 [UNWRAP #$callId] After _ensureMap, keys: ${data.keys.toList()}');

    // 1. Direct match (e.g. {"x-sre-tool-log": {...}})
    if (data.containsKey(componentName)) {
      debugPrint('🔓 [UNWRAP #$callId] ✅ Strategy 1: Direct match found for key "$componentName"');
      final inner = data[componentName];
      debugPrint('🔓 [UNWRAP #$callId] Inner type: ${inner.runtimeType}');
      if (inner is Map) {
        final result = Map<String, dynamic>.from(inner);
        debugPrint('🔓 [UNWRAP #$callId] Returning Map with keys: ${result.keys.toList()}');
        debugPrint('🔓 [UNWRAP #$callId] ===== _unwrapComponentData END (Strategy 1 - Map) =====');
        return result;
      }
      if (inner is List) {
        // Return a map wrapping the list if found directly under the key
        final result = {componentName: inner};
        debugPrint('🔓 [UNWRAP #$callId] Returning wrapped List, length: ${inner.length}');
        debugPrint('🔓 [UNWRAP #$callId] ===== _unwrapComponentData END (Strategy 1 - List) =====');
        return result;
      }
      debugPrint('🔓 [UNWRAP #$callId] ⚠️ Inner is neither Map nor List: ${inner.runtimeType}');
    } else {
      debugPrint('🔓 [UNWRAP #$callId] Strategy 1: No direct match for key "$componentName"');
    }

    // 2. Component wrapper (e.g. {"component": {"x-sre-tool-log": {...}}})
    if (data.containsKey('component') && data['component'] is Map) {
      debugPrint('🔓 [UNWRAP #$callId] Strategy 2: Found "component" wrapper');
      final inner = data['component'] as Map;
      debugPrint('🔓 [UNWRAP #$callId] Component wrapper keys: ${inner.keys.toList()}');
      if (inner.containsKey(componentName)) {
        debugPrint('🔓 [UNWRAP #$callId] ✅ Found "$componentName" inside component wrapper');
        final result = Map<String, dynamic>.from(inner[componentName] as Map);
        debugPrint('🔓 [UNWRAP #$callId] Returning with keys: ${result.keys.toList()}');
        debugPrint('🔓 [UNWRAP #$callId] ===== _unwrapComponentData END (Strategy 2a) =====');
        return result;
      }
      // If component wrapper exists but doesn't have the named key, maybe it IS the data?
      if (inner['type'] == componentName) {
        debugPrint('🔓 [UNWRAP #$callId] ✅ Component wrapper type matches: ${inner['type']}');
        final result = Map<String, dynamic>.from(inner);
        debugPrint('🔓 [UNWRAP #$callId] Returning component wrapper as data, keys: ${result.keys.toList()}');
        debugPrint('🔓 [UNWRAP #$callId] ===== _unwrapComponentData END (Strategy 2b) =====');
        return result;
      }
      debugPrint('🔓 [UNWRAP #$callId] Strategy 2: Component wrapper does not contain "$componentName" or matching type');
    } else {
      debugPrint('🔓 [UNWRAP #$callId] Strategy 2: No "component" wrapper found');
    }

    // 3. Root Level Match (e.g. {"type": "x-sre-tool-log", ...})
    debugPrint('🔓 [UNWRAP #$callId] Strategy 3: Checking root type. data["type"] = ${data['type']}');
    if (data['type'] == componentName) {
      debugPrint('🔓 [UNWRAP #$callId] ✅ Root type matches: ${data['type']}');
      // If it's a v0.8 component wrapper, unwrap the named key if present
      if (data.containsKey(componentName) && data[componentName] is Map) {
        debugPrint('🔓 [UNWRAP #$callId] Found nested $componentName key, unwrapping');
        final result = Map<String, dynamic>.from(data[componentName] as Map);
        debugPrint('🔓 [UNWRAP #$callId] Returning nested data, keys: ${result.keys.toList()}');
        debugPrint('🔓 [UNWRAP #$callId] ===== _unwrapComponentData END (Strategy 3a) =====');
        return result;
      }
      debugPrint('🔓 [UNWRAP #$callId] Returning root data as-is, keys: ${data.keys.toList()}');
      debugPrint('🔓 [UNWRAP #$callId] ===== _unwrapComponentData END (Strategy 3b) =====');
      return data;
    }

    // 4. Fallback: If we are specifically looking for tool log, try to find ANY log-like shape
    if (componentName == 'x-sre-tool-log' || componentName == 'tool-log') {
      debugPrint('🔓 [UNWRAP #$callId] Strategy 4: Fallback for tool-log');
      // Check for common tool log fields at root or under a generic 'component' key
      if (data.containsKey('toolName') ||
          data.containsKey('tool_name') ||
          (data.containsKey('args') && data.containsKey('status'))) {
        debugPrint('🔓 [UNWRAP #$callId] ✅ Found tool-log-like fields in data');
        debugPrint('🔓 [UNWRAP #$callId] ===== _unwrapComponentData END (Strategy 4) =====');
        return data;
      }
      debugPrint('🔓 [UNWRAP #$callId] Strategy 4: No tool-log-like fields found');
    }

    debugPrint('🔓 [UNWRAP #$callId] ⚠️ No strategy matched, returning raw data');
    debugPrint('🔓 [UNWRAP #$callId] Final data keys: ${data.keys.toList()}');
    debugPrint('🔓 [UNWRAP #$callId] ===== _unwrapComponentData END (Fallback) =====');
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
              child: TraceWaterfall(trace: trace),
              height: 380,
            );
          } catch (e) {
            return ErrorPlaceholder(error: e);
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
              child: MetricCorrelationChart(series: series),
              height: 380,
            );
          } catch (e) {
            return ErrorPlaceholder(error: e);
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
            return ErrorPlaceholder(error: e);
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
            return ErrorPlaceholder(error: e);
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
            return ErrorPlaceholder(error: e);
          }
        },
      ),
      CatalogItem(
        name: 'tool-log', // Alias for matching
        dataSchema: S.any(),
        widgetBuilder: (context) {
          debugPrint('🔧 tool-log widgetBuilder called');
          debugPrint('🔧 tool-log context.data: ${context.data}');
          try {
            final raw = context.data;
            final data = _unwrapComponentData(raw, 'tool-log');
            debugPrint('🔧 tool-log unwrapped data: $data');
            if (data.isEmpty) {
              return ErrorPlaceholder(
                error: 'tool-log: data is empty after unwrap.\nRaw: $raw',
              );
            }
            final log = ToolLog.fromJson(data);
            return ToolLogWidget(log: log);
          } catch (e, st) {
            debugPrint('🔧 tool-log error: $e\n$st');
            return ErrorPlaceholder(error: e);
          }
        },
      ),
      CatalogItem(
        name: 'x-sre-tool-log',
        dataSchema: S.any(),
        widgetBuilder: (context) {
          debugPrint('🔧 x-sre-tool-log widgetBuilder called');
          debugPrint('🔧 x-sre-tool-log context.data: ${context.data}');
          try {
            final raw = context.data;

            final data = _unwrapComponentData(raw, 'x-sre-tool-log');
            debugPrint('🔧 x-sre-tool-log unwrapped data: $data');

            if (data.isEmpty) {
              return ErrorPlaceholder(
                error: 'x-sre-tool-log: data is empty after unwrap.\nRaw: $raw',
              );
            }

            if (!data.containsKey('tool_name') &&
                !data.containsKey('toolName')) {
              return ErrorPlaceholder(
                error: 'x-sre-tool-log: Missing tool_name.\nData keys: ${data.keys.toList()}\nRaw: $raw',
              );
            }

            final log = ToolLog.fromJson(data);
            return ToolLogWidget(log: log);
          } catch (e, st) {
            debugPrint('🔧 x-sre-tool-log error: $e\n$st');
            return ErrorPlaceholder(error: e);
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
            return ErrorPlaceholder(error: e);
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
            return ErrorPlaceholder(error: e);
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
            return ErrorPlaceholder(error: e);
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
            return ErrorPlaceholder(error: e);
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
            return ErrorPlaceholder(error: e);
          }
        },
      ),
    ], catalogId: 'sre-catalog');
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
