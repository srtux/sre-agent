import 'package:flutter/material.dart';
import 'package:genui/genui.dart';
import 'package:json_schema_builder/json_schema_builder.dart';

import 'models/adk_schema.dart';
import 'widgets/error_placeholder.dart';
import 'widgets/log_pattern_viewer.dart';
import 'widgets/metric_chart.dart';
import 'widgets/remediation_plan.dart';
import 'widgets/trace_waterfall.dart';

/// Registry for all SRE-specific UI components.
class CatalogRegistry {
  static Catalog createSreCatalog() {
    return Catalog(
      [
        CatalogItem(
          name: "x-sre-trace-waterfall",
          dataSchema: S.object(),
          widgetBuilder: (context) {
            try {
              final data = context.data as Map<String, dynamic>;
              final trace = Trace.fromJson(Map<String, dynamic>.from(data));
              return Container(
                height: 300,
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.white10),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: TraceWaterfall(trace: trace),
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
              final data = context.data as Map<String, dynamic>;
              final series = MetricSeries.fromJson(Map<String, dynamic>.from(data));
              return Container(
                height: 300,
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.white10),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: MetricCorrelationChart(series: series),
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
              final data = context.data as Map<String, dynamic>;
              final plan = RemediationPlan.fromJson(Map<String, dynamic>.from(data));
              return RemediationPlanWidget(plan: plan);
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
              final data = context.data as List<dynamic>;
              final patterns = data
                  .map((item) => LogPattern.fromJson(Map<String, dynamic>.from(item)))
                  .toList();
              return Container(
                height: 400,
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.white10),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: LogPatternViewer(patterns: patterns),
              );
            } catch (e) {
              return ErrorPlaceholder(error: e);
            }
          },
        ),
      ],
      catalogId: "sre-catalog",
    );
  }
}
