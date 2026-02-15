/// Query helpers, templates, and autocomplete data for each dashboard panel.
///
/// Provides:
/// - [QuerySnippet]: Insertable code snippet (keyword, operator, or template).
/// - [QueryTemplate]: Full pre-built query with title and description.
/// - Per-panel helper catalogs used by autocomplete and the snippet picker.
library;

import 'package:flutter/material.dart';

import '../../services/data_utils.dart';
import '../../theme/app_theme.dart';

export '../../services/data_utils.dart';

// =============================================================================
// Data models
// =============================================================================

/// A single autocomplete/keyword suggestion shown while typing.
class QuerySnippet {
  /// Short label shown in the dropdown (e.g. `severity>=`).
  final String label;

  /// Text inserted into the query bar when selected.
  final String insertText;

  /// One-line description shown to the right of the label.
  final String description;

  /// Category for grouping (e.g. "Keyword", "Operator", "Function").
  final String category;

  /// Icon shown next to the label.
  final IconData icon;

  /// Accent color for the icon.
  final Color color;

  const QuerySnippet({
    required this.label,
    required this.insertText,
    required this.description,
    this.category = 'Keyword',
    this.icon = Icons.code_rounded,
    this.color = AppColors.primaryCyan,
  });
}

/// A complete pre-built query the user can pick from a helper menu.
class QueryTemplate {
  /// Human-readable title (e.g. "Error logs in the last hour").
  final String title;

  /// Brief explanation.
  final String description;

  /// The full query string inserted on selection.
  final String query;

  /// Category grouping (e.g. "Common", "Advanced", "SLO").
  final String category;

  /// Icon for the category.
  final IconData icon;

  const QueryTemplate({
    required this.title,
    required this.description,
    required this.query,
    this.category = 'Common',
    this.icon = Icons.lightbulb_outline_rounded,
  });
}

// =============================================================================
// Cloud Trace helpers
// =============================================================================

const traceSnippets = <QuerySnippet>[
  QuerySnippet(
    label: '+span:name:',
    insertText: '+span:name:',
    description: 'Filter spans by name',
    category: 'Filter',
    icon: Icons.filter_alt_rounded,
    color: AppColors.primaryCyan,
  ),
  QuerySnippet(
    label: 'RootSpan:',
    insertText: 'RootSpan:',
    description: 'Filter by root span path',
    category: 'Filter',
    icon: Icons.account_tree_rounded,
    color: AppColors.primaryCyan,
  ),
  QuerySnippet(
    label: 'SpanName:',
    insertText: 'SpanName:',
    description: 'Match span name substring',
    category: 'Filter',
    icon: Icons.label_outline_rounded,
    color: AppColors.primaryCyan,
  ),
  QuerySnippet(
    label: 'MinDuration:',
    insertText: 'MinDuration:',
    description: 'Minimum span duration (e.g. 100ms, 1s)',
    category: 'Performance',
    icon: Icons.timer_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'MaxDuration:',
    insertText: 'MaxDuration:',
    description: 'Maximum span duration',
    category: 'Performance',
    icon: Icons.timer_off_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'HasLabel:',
    insertText: 'HasLabel:',
    description: 'Spans with a specific label key',
    category: 'Label',
    icon: Icons.label_rounded,
    color: AppColors.success,
  ),
  QuerySnippet(
    label: '+label:',
    insertText: '+label:',
    description: 'Filter by label key:value pair',
    category: 'Label',
    icon: Icons.label_important_rounded,
    color: AppColors.success,
  ),
  QuerySnippet(
    label: 'Status:',
    insertText: 'Status:',
    description: 'Filter by span status (OK, ERROR, UNSET)',
    category: 'Filter',
    icon: Icons.check_circle_outline_rounded,
    color: AppColors.error,
  ),
];

const traceTemplates = <QueryTemplate>[
  QueryTemplate(
    title: 'Slow API requests',
    description: 'Find traces with root spans slower than 1 second',
    query: 'RootSpan:/api/ MinDuration:1s',
    category: 'Performance',
    icon: Icons.speed_rounded,
  ),
  QueryTemplate(
    title: 'Error traces',
    description: 'Find traces containing spans with error status',
    query: 'Status:ERROR',
    category: 'Errors',
    icon: Icons.error_outline_rounded,
  ),
  QueryTemplate(
    title: 'Specific service spans',
    description: 'Find spans from a specific service',
    query: '+span:name:my-service',
    category: 'Service',
    icon: Icons.dns_rounded,
  ),
  QueryTemplate(
    title: 'Database queries over 500ms',
    description: 'Slow database operations',
    query: '+span:name:db MinDuration:500ms',
    category: 'Performance',
    icon: Icons.storage_rounded,
  ),
  QueryTemplate(
    title: 'Spans with HTTP errors',
    description: 'Find spans with HTTP status code labels',
    query: '+label:http.status_code:500',
    category: 'Errors',
    icon: Icons.http_rounded,
  ),
];

// =============================================================================
// Cloud Logging helpers
// =============================================================================

const loggingSnippets = <QuerySnippet>[
  QuerySnippet(
    label: 'severity>=',
    insertText: 'severity>=',
    description: 'Filter by minimum severity level',
    category: 'Severity',
    icon: Icons.warning_amber_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'severity=',
    insertText: 'severity=',
    description: 'Filter by exact severity',
    category: 'Severity',
    icon: Icons.warning_amber_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'resource.type=',
    insertText: 'resource.type=',
    description: 'Filter by GCP resource type',
    category: 'Resource',
    icon: Icons.cloud_rounded,
    color: AppColors.primaryCyan,
  ),
  QuerySnippet(
    label: 'resource.labels.',
    insertText: 'resource.labels.',
    description: 'Filter by resource label',
    category: 'Resource',
    icon: Icons.label_rounded,
    color: AppColors.primaryCyan,
  ),
  QuerySnippet(
    label: 'textPayload:',
    insertText: 'textPayload:',
    description: 'Search within text payload',
    category: 'Payload',
    icon: Icons.text_fields_rounded,
    color: AppColors.success,
  ),
  QuerySnippet(
    label: 'jsonPayload.',
    insertText: 'jsonPayload.',
    description: 'Filter by JSON payload field',
    category: 'Payload',
    icon: Icons.data_object_rounded,
    color: AppColors.success,
  ),
  QuerySnippet(
    label: 'logName=',
    insertText: 'logName=',
    description: 'Filter by log name',
    category: 'Filter',
    icon: Icons.article_rounded,
    color: AppColors.info,
  ),
  QuerySnippet(
    label: 'labels.',
    insertText: 'labels.',
    description: 'Filter by user-defined label',
    category: 'Label',
    icon: Icons.label_outline_rounded,
    color: AppColors.info,
  ),
  QuerySnippet(
    label: 'timestamp>=',
    insertText: 'timestamp>=',
    description: 'Filter by timestamp',
    category: 'Time',
    icon: Icons.schedule_rounded,
    color: AppColors.textMuted,
  ),
  QuerySnippet(
    label: 'AND',
    insertText: ' AND ',
    description: 'Boolean AND operator',
    category: 'Operator',
    icon: Icons.join_full_rounded,
    color: AppColors.secondaryPurple,
  ),
  QuerySnippet(
    label: 'OR',
    insertText: ' OR ',
    description: 'Boolean OR operator',
    category: 'Operator',
    icon: Icons.join_inner_rounded,
    color: AppColors.secondaryPurple,
  ),
  QuerySnippet(
    label: 'NOT',
    insertText: ' NOT ',
    description: 'Boolean NOT operator',
    category: 'Operator',
    icon: Icons.block_rounded,
    color: AppColors.secondaryPurple,
  ),
];

const loggingTemplates = <QueryTemplate>[
  QueryTemplate(
    title: 'All errors',
    description: 'Show ERROR and higher severity logs',
    query: 'severity>=ERROR',
    category: 'Common',
    icon: Icons.error_outline_rounded,
  ),
  QueryTemplate(
    title: 'GCE instance errors',
    description: 'Errors from Compute Engine instances',
    query: 'severity>=ERROR AND resource.type="gce_instance"',
    category: 'Compute',
    icon: Icons.computer_rounded,
  ),
  QueryTemplate(
    title: 'Cloud Run request logs',
    description: 'HTTP request logs from Cloud Run services',
    query:
        'resource.type="cloud_run_revision" AND httpRequest.status>=400',
    category: 'Cloud Run',
    icon: Icons.cloud_rounded,
  ),
  QueryTemplate(
    title: 'GKE container errors',
    description: 'Error logs from GKE containers',
    query: 'resource.type="k8s_container" AND severity>=ERROR',
    category: 'GKE',
    icon: Icons.view_in_ar_rounded,
  ),
  QueryTemplate(
    title: 'Specific text search',
    description: 'Search for a phrase in text payloads',
    query: 'textPayload:"connection refused"',
    category: 'Search',
    icon: Icons.search_rounded,
  ),
  QueryTemplate(
    title: 'JSON payload field',
    description: 'Filter by a JSON payload field value',
    query: 'jsonPayload.status=500',
    category: 'Search',
    icon: Icons.data_object_rounded,
  ),
  QueryTemplate(
    title: 'Audit logs',
    description: 'Admin activity audit logs',
    query: 'logName:"cloudaudit.googleapis.com%2Factivity"',
    category: 'Security',
    icon: Icons.security_rounded,
  ),
];

// =============================================================================
// Metrics helpers (MQL / ListTimeSeries)
// =============================================================================

const mqlSnippets = <QuerySnippet>[
  QuerySnippet(
    label: 'metric.type=',
    insertText: 'metric.type=',
    description: 'Filter by metric type (required)',
    category: 'Metric',
    icon: Icons.show_chart_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'metric.labels.',
    insertText: 'metric.labels.',
    description: 'Filter by metric label',
    category: 'Label',
    icon: Icons.label_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'resource.type=',
    insertText: 'resource.type=',
    description: 'Filter by monitored resource type',
    category: 'Resource',
    icon: Icons.cloud_rounded,
    color: AppColors.primaryCyan,
  ),
  QuerySnippet(
    label: 'resource.labels.',
    insertText: 'resource.labels.',
    description: 'Filter by resource label (zone, project, etc.)',
    category: 'Resource',
    icon: Icons.label_outline_rounded,
    color: AppColors.primaryCyan,
  ),

  // Common GCP Metrics Autocomplete
  QuerySnippet(
    label: 'metric.type="compute.googleapis.com/instance/cpu/utilization"',
    insertText: 'metric.type="compute.googleapis.com/instance/cpu/utilization"',
    description: 'CPU utilization',
    category: 'Metric',
    icon: Icons.show_chart_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'metric.type="compute.googleapis.com/instance/network/received_bytes_count"',
    insertText: 'metric.type="compute.googleapis.com/instance/network/received_bytes_count"',
    description: 'Received bytes count',
    category: 'Metric',
    icon: Icons.show_chart_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'metric.type="compute.googleapis.com/instance/network/sent_bytes_count"',
    insertText: 'metric.type="compute.googleapis.com/instance/network/sent_bytes_count"',
    description: 'Sent bytes count',
    category: 'Metric',
    icon: Icons.show_chart_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'metric.type="kubernetes.io/container/cpu/core_usage_time"',
    insertText: 'metric.type="kubernetes.io/container/cpu/core_usage_time"',
    description: 'Container CPU usage',
    category: 'Metric',
    icon: Icons.show_chart_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'metric.type="kubernetes.io/container/memory/used_bytes"',
    insertText: 'metric.type="kubernetes.io/container/memory/used_bytes"',
    description: 'Memory used bytes',
    category: 'Metric',
    icon: Icons.show_chart_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'metric.type="kubernetes.io/container/restart_count"',
    insertText: 'metric.type="kubernetes.io/container/restart_count"',
    description: 'Container restart count',
    category: 'Metric',
    icon: Icons.show_chart_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'metric.type="run.googleapis.com/request_count"',
    insertText: 'metric.type="run.googleapis.com/request_count"',
    description: 'Cloud Run Request count',
    category: 'Metric',
    icon: Icons.show_chart_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'metric.type="run.googleapis.com/request_latencies"',
    insertText: 'metric.type="run.googleapis.com/request_latencies"',
    description: 'Cloud Run Request latencies',
    category: 'Metric',
    icon: Icons.show_chart_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'metric.type="run.googleapis.com/container/cpu/utilizations"',
    insertText: 'metric.type="run.googleapis.com/container/cpu/utilizations"',
    description: 'Cloud Run CPU utilization',
    category: 'Metric',
    icon: Icons.show_chart_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'metric.type="cloudsql.googleapis.com/database/cpu/utilization"',
    insertText: 'metric.type="cloudsql.googleapis.com/database/cpu/utilization"',
    description: 'Cloud SQL CPU utilization',
    category: 'Metric',
    icon: Icons.show_chart_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'metric.type="cloudsql.googleapis.com/database/memory/utilization"',
    insertText: 'metric.type="cloudsql.googleapis.com/database/memory/utilization"',
    description: 'Cloud SQL Memory utilization',
    category: 'Metric',
    icon: Icons.show_chart_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'metric.type="pubsub.googleapis.com/subscription/num_undelivered_messages"',
    insertText: 'metric.type="pubsub.googleapis.com/subscription/num_undelivered_messages"',
    description: 'Pub/Sub Unacked messages',
    category: 'Metric',
    icon: Icons.show_chart_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'metric.type="pubsub.googleapis.com/subscription/oldest_unacked_message_age"',
    insertText: 'metric.type="pubsub.googleapis.com/subscription/oldest_unacked_message_age"',
    description: 'Oldest unacked message age',
    category: 'Metric',
    icon: Icons.show_chart_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'metric.type="loadbalancing.googleapis.com/https/backend_latencies"',
    insertText: 'metric.type="loadbalancing.googleapis.com/https/backend_latencies"',
    description: 'LB Backend latencies',
    category: 'Metric',
    icon: Icons.show_chart_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'metric.type="loadbalancing.googleapis.com/https/request_count"',
    insertText: 'metric.type="loadbalancing.googleapis.com/https/request_count"',
    description: 'LB Request count',
    category: 'Metric',
    icon: Icons.show_chart_rounded,
    color: AppColors.warning,
  ),
];

const promqlSnippets = <QuerySnippet>[
  QuerySnippet(
    label: 'rate()',
    insertText: 'rate(',
    description: 'Per-second rate over time range',
    category: 'Function',
    icon: Icons.trending_up_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'sum()',
    insertText: 'sum(',
    description: 'Sum aggregation',
    category: 'Aggregation',
    icon: Icons.functions_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'avg()',
    insertText: 'avg(',
    description: 'Average aggregation',
    category: 'Aggregation',
    icon: Icons.functions_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'max()',
    insertText: 'max(',
    description: 'Maximum aggregation',
    category: 'Aggregation',
    icon: Icons.arrow_upward_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'min()',
    insertText: 'min(',
    description: 'Minimum aggregation',
    category: 'Aggregation',
    icon: Icons.arrow_downward_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'histogram_quantile()',
    insertText: 'histogram_quantile(',
    description: 'Quantile from histogram buckets',
    category: 'Function',
    icon: Icons.bar_chart_rounded,
    color: AppColors.success,
  ),
  QuerySnippet(
    label: 'by ()',
    insertText: ' by (',
    description: 'Group aggregation by labels',
    category: 'Modifier',
    icon: Icons.group_work_rounded,
    color: AppColors.primaryCyan,
  ),
  QuerySnippet(
    label: 'without ()',
    insertText: ' without (',
    description: 'Aggregate excluding labels',
    category: 'Modifier',
    icon: Icons.remove_circle_outline_rounded,
    color: AppColors.primaryCyan,
  ),
  QuerySnippet(
    label: '[5m]',
    insertText: '[5m]',
    description: 'Range vector: 5 minutes',
    category: 'Range',
    icon: Icons.schedule_rounded,
    color: AppColors.info,
  ),
  QuerySnippet(
    label: '[1h]',
    insertText: '[1h]',
    description: 'Range vector: 1 hour',
    category: 'Range',
    icon: Icons.schedule_rounded,
    color: AppColors.info,
  ),
];

const metricsTemplates = <QueryTemplate>[
  // MQL templates (index 0)
  QueryTemplate(
    title: 'CPU utilization',
    description: 'Compute Engine instance CPU usage',
    query:
        'metric.type="compute.googleapis.com/instance/cpu/utilization"',
    category: 'Compute',
    icon: Icons.memory_rounded,
  ),
  QueryTemplate(
    title: 'Cloud Run request count',
    description: 'Request count for Cloud Run services',
    query:
        'metric.type="run.googleapis.com/request_count"',
    category: 'Cloud Run',
    icon: Icons.cloud_rounded,
  ),
  QueryTemplate(
    title: 'Cloud SQL connections',
    description: 'Active database connections',
    query:
        'metric.type="cloudsql.googleapis.com/database/network/connections"',
    category: 'Database',
    icon: Icons.storage_rounded,
  ),
  QueryTemplate(
    title: 'Load balancer latency',
    description: 'HTTP load balancer backend latencies',
    query:
        'metric.type="loadbalancing.googleapis.com/https/backend_latencies"',
    category: 'Network',
    icon: Icons.network_check_rounded,
  ),
];

const promqlTemplates = <QueryTemplate>[
  QueryTemplate(
    title: 'Request rate (5m)',
    description: 'Per-second request rate over 5 minutes',
    query: 'rate(http_requests_total[5m])',
    category: 'Common',
    icon: Icons.trending_up_rounded,
  ),
  QueryTemplate(
    title: 'Error rate percentage',
    description: 'Percentage of requests resulting in errors',
    query:
        'sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) * 100',
    category: 'SLO',
    icon: Icons.percent_rounded,
  ),
  QueryTemplate(
    title: 'P95 latency',
    description: '95th percentile request latency',
    query: 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))',
    category: 'Latency',
    icon: Icons.speed_rounded,
  ),
  QueryTemplate(
    title: 'Memory usage by pod',
    description: 'Container memory usage grouped by pod',
    query:
        'sum by (pod) (container_memory_usage_bytes{container!=""})',
    category: 'Resources',
    icon: Icons.memory_rounded,
  ),
];

// =============================================================================
// BigQuery SQL helpers
// =============================================================================

const sqlSnippets = <QuerySnippet>[
  QuerySnippet(
    label: 'SELECT',
    insertText: 'SELECT ',
    description: 'Select columns',
    category: 'Clause',
    icon: Icons.view_column_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'FROM',
    insertText: 'FROM ',
    description: 'Specify source table',
    category: 'Clause',
    icon: Icons.table_chart_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'WHERE',
    insertText: 'WHERE ',
    description: 'Filter condition',
    category: 'Clause',
    icon: Icons.filter_list_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'GROUP BY',
    insertText: 'GROUP BY ',
    description: 'Group rows by column',
    category: 'Clause',
    icon: Icons.group_work_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'ORDER BY',
    insertText: 'ORDER BY ',
    description: 'Sort results',
    category: 'Clause',
    icon: Icons.sort_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'LIMIT',
    insertText: 'LIMIT ',
    description: 'Limit result rows',
    category: 'Clause',
    icon: Icons.vertical_align_bottom_rounded,
    color: AppColors.warning,
  ),
  QuerySnippet(
    label: 'JOIN',
    insertText: 'JOIN ',
    description: 'Join with another table',
    category: 'Clause',
    icon: Icons.join_full_rounded,
    color: AppColors.primaryCyan,
  ),
  QuerySnippet(
    label: 'COUNT()',
    insertText: 'COUNT(',
    description: 'Count rows',
    category: 'Function',
    icon: Icons.functions_rounded,
    color: AppColors.success,
  ),
  QuerySnippet(
    label: 'SUM()',
    insertText: 'SUM(',
    description: 'Sum values',
    category: 'Function',
    icon: Icons.functions_rounded,
    color: AppColors.success,
  ),
  QuerySnippet(
    label: 'AVG()',
    insertText: 'AVG(',
    description: 'Average value',
    category: 'Function',
    icon: Icons.functions_rounded,
    color: AppColors.success,
  ),
  QuerySnippet(
    label: 'TIMESTAMP_DIFF()',
    insertText: 'TIMESTAMP_DIFF(',
    description: 'Difference between timestamps',
    category: 'Function',
    icon: Icons.schedule_rounded,
    color: AppColors.info,
  ),
  QuerySnippet(
    label: 'UNNEST()',
    insertText: 'UNNEST(',
    description: 'Flatten array column',
    category: 'Function',
    icon: Icons.unfold_more_rounded,
    color: AppColors.info,
  ),
];

const sqlTemplates = <QueryTemplate>[
  QueryTemplate(
    title: 'Recent OTel spans',
    description: 'Latest spans from the OpenTelemetry export table',
    query:
        'SELECT span_id, trace_id, span_name, duration_ms\n'
        'FROM `project.dataset.otel_spans`\n'
        'WHERE start_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)\n'
        'ORDER BY start_time DESC\n'
        'LIMIT 100',
    category: 'OTel',
    icon: Icons.timeline_rounded,
  ),
  QueryTemplate(
    title: 'Error log count by service',
    description: 'Count of error logs grouped by service',
    query:
        'SELECT resource.labels.service_name AS service, COUNT(*) AS error_count\n'
        'FROM `project.dataset.logs`\n'
        'WHERE severity >= "ERROR"\n'
        '  AND timestamp > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)\n'
        'GROUP BY service\n'
        'ORDER BY error_count DESC',
    category: 'Logs',
    icon: Icons.article_rounded,
  ),
  QueryTemplate(
    title: 'P95 latency by endpoint',
    description: '95th percentile latency grouped by endpoint',
    query:
        'SELECT span_name AS endpoint,\n'
        '       APPROX_QUANTILES(duration_ms, 100)[OFFSET(95)] AS p95_ms,\n'
        '       COUNT(*) AS request_count\n'
        'FROM `project.dataset.otel_spans`\n'
        'WHERE start_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 6 HOUR)\n'
        'GROUP BY endpoint\n'
        'ORDER BY p95_ms DESC\n'
        'LIMIT 20',
    category: 'Performance',
    icon: Icons.speed_rounded,
  ),
  QueryTemplate(
    title: 'Slowest traces',
    description: 'Top 10 slowest traces in the last hour',
    query:
        'SELECT trace_id, MAX(duration_ms) AS total_duration_ms, COUNT(*) AS span_count\n'
        'FROM `project.dataset.otel_spans`\n'
        'WHERE start_time > TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)\n'
        'GROUP BY trace_id\n'
        'ORDER BY total_duration_ms DESC\n'
        'LIMIT 10',
    category: 'Performance',
    icon: Icons.timer_rounded,
  ),
  QueryTemplate(
    title: 'Custom query',
    description: 'Start with a blank query',
    query: 'SELECT *\nFROM `project.dataset.table`\nLIMIT 100',
    category: 'General',
    icon: Icons.edit_rounded,
  ),
];

// =============================================================================
// Natural language example prompts
// =============================================================================

const traceNaturalLanguageExamples = <String>[
  'Show me the slowest API calls in the last hour',
  'Find traces with errors in the checkout service',
  'Which database queries are taking more than 500ms?',
  'Show traces where the /api/users endpoint is slow',
];

const loggingNaturalLanguageExamples = <String>[
  'Show me all errors from the payment service',
  'Find crash logs from the last 30 minutes',
  'Are there any OOM errors in GKE containers?',
  'Show authentication failures from Cloud Run',
];

const metricsNaturalLanguageExamples = <String>[
  'What is the CPU utilization across all instances?',
  'Show request error rate for the frontend service',
  'Is there a latency spike in the load balancer?',
  'How much memory are my Cloud Run services using?',
];

const sqlNaturalLanguageExamples = <String>[
  'Show me the top 10 slowest endpoints today',
  'How many errors occurred per service in the last hour?',
  'Compare request latency between prod and staging',
  'Which users triggered the most 500 errors?',
];
