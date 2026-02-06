"""Tool registry for council panel agents.

Defines which tools each specialist panel receives, keeping tool sets
focused and non-overlapping to maximize LLM tool selection accuracy.

Tool assignments are sourced from the existing sub-agent definitions
in sre_agent/sub_agents/ but reorganized into 4 panels + orchestrator.
"""

from typing import Any

from sre_agent.tools import (
    analyze_aggregate_metrics,
    analyze_bigquery_log_patterns,
    analyze_critical_path,
    # Trace panel tools
    analyze_trace_comprehensive,
    build_service_dependency_graph,
    calculate_critical_path_contribution,
    calculate_series_stats,
    compare_metric_windows,
    compare_span_timings,
    compare_time_periods,
    correlate_logs_with_trace,
    correlate_metrics_with_traces_via_exemplars,
    correlate_trace_with_metrics,
    detect_all_sre_patterns,
    detect_cascading_timeout,
    detect_connection_pool_issues,
    detect_latency_anomalies,
    detect_metric_anomalies,
    detect_retry_storm,
    detect_trend_changes,
    discover_telemetry_sources,
    estimate_remediation_risk,
    extract_log_patterns,
    fetch_trace,
    find_bottleneck_services,
    find_exemplar_traces,
    generate_remediation_suggestions,
    get_alert,
    get_gcloud_commands,
    # Cross-cutting tools
    get_investigation_summary,
    list_alert_policies,
    # Alerts panel tools
    list_alerts,
    # Logs panel tools
    list_log_entries,
    list_metric_descriptors,
    # Metrics panel tools
    list_time_series,
    list_traces,
    # Aggregate / BigQuery tools (shared with trace panel)
    mcp_execute_sql,
    mcp_list_timeseries,
    mcp_query_range,
    query_promql,
    update_investigation_state,
)
from sre_agent.tools.bigquery.ca_data_agent import query_data_agent

# =============================================================================
# Panel Tool Sets
# =============================================================================

TRACE_PANEL_TOOLS: list[Any] = [
    # Primary analysis
    analyze_trace_comprehensive,
    compare_span_timings,
    analyze_critical_path,
    calculate_critical_path_contribution,
    find_bottleneck_services,
    fetch_trace,
    # Anomaly detection
    detect_latency_anomalies,
    detect_all_sre_patterns,
    detect_retry_storm,
    detect_cascading_timeout,
    detect_connection_pool_issues,
    # Context
    compare_time_periods,
    detect_trend_changes,
    correlate_logs_with_trace,
    # Aggregate (BigQuery)
    mcp_execute_sql,
    analyze_aggregate_metrics,
    find_exemplar_traces,
    correlate_metrics_with_traces_via_exemplars,
    build_service_dependency_graph,
    discover_telemetry_sources,
    list_traces,
    # State
    get_investigation_summary,
    update_investigation_state,
]

METRICS_PANEL_TOOLS: list[Any] = [
    # Primary metrics
    list_time_series,
    list_metric_descriptors,
    query_promql,
    # MCP metrics
    mcp_list_timeseries,
    mcp_query_range,
    # Analysis
    detect_metric_anomalies,
    compare_metric_windows,
    calculate_series_stats,
    # Correlation
    correlate_trace_with_metrics,
    correlate_metrics_with_traces_via_exemplars,
    # Context
    list_log_entries,
    # State
    get_investigation_summary,
    update_investigation_state,
]

LOGS_PANEL_TOOLS: list[Any] = [
    # Log analysis
    list_log_entries,
    analyze_bigquery_log_patterns,
    extract_log_patterns,
    # Context
    list_time_series,
    compare_time_periods,
    discover_telemetry_sources,
    # State
    get_investigation_summary,
    update_investigation_state,
]

ALERTS_PANEL_TOOLS: list[Any] = [
    # Alert analysis
    list_alerts,
    list_alert_policies,
    get_alert,
    # Context
    list_time_series,
    compare_time_periods,
    discover_telemetry_sources,
    # Remediation
    generate_remediation_suggestions,
    estimate_remediation_risk,
    get_gcloud_commands,
    # State
    get_investigation_summary,
    update_investigation_state,
]

DATA_PANEL_TOOLS: list[Any] = [
    # CA Data Agent (primary)
    query_data_agent,
    # Fallback: direct BigQuery
    mcp_execute_sql,
    discover_telemetry_sources,
    # Context
    list_time_series,
    # State
    get_investigation_summary,
    update_investigation_state,
]

# Orchestrator-level tools (for slim root agent - Phase 4)
# These are the only tools the root agent needs when council is active.
# Populated in Phase 4 when the slim tool set is implemented.
ORCHESTRATOR_TOOLS: list[Any] = []
