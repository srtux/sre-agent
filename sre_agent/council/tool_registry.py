"""Tool registry for council panel agents and sub-agents.

Defines which tools each specialist receives, keeping tool sets focused
and non-overlapping to maximize LLM tool selection accuracy.

OPT-4: This module is the **single source of truth** for domain-specific
tool sets. Both council panels (council/panels.py) and sub-agents
(sub_agents/*.py) import from here to avoid tool set drift.

Tool assignments are organized by signal domain (trace, metrics, logs,
alerts, data) with shared cross-cutting tools (state, discovery).
"""

from typing import Any

from sre_agent.tools import (
    analyze_aggregate_metrics,
    analyze_bigquery_log_patterns,
    analyze_critical_path,
    # Trace panel tools
    analyze_trace_comprehensive,
    analyze_upstream_downstream_impact,
    build_cross_signal_timeline,
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
    fetch_web_page,
    find_bottleneck_services,
    find_exemplar_traces,
    # Aggregate / BigQuery tools (shared with trace panel)
    gcp_execute_sql,
    generate_remediation_suggestions,
    get_alert,
    get_gcloud_commands,
    # Cross-cutting tools
    get_investigation_summary,
    # GitHub Self-Healing tools
    github_create_pull_request,
    github_list_recent_commits,
    github_read_file,
    github_search_code,
    list_alert_policies,
    # Alerts panel tools
    list_alerts,
    # Logs panel tools
    list_log_entries,
    list_metric_descriptors,
    # Metrics panel tools
    list_time_series,
    list_traces,
    mcp_list_timeseries,
    mcp_query_range,
    # Root cause / causal analysis
    perform_causal_analysis,
    query_promql,
    update_investigation_state,
)
from sre_agent.tools.bigquery.ca_data_agent import query_data_agent

# =============================================================================
# Cross-cutting tools (shared by ALL panels and sub-agents)
# =============================================================================

SHARED_STATE_TOOLS: list[Any] = [
    get_investigation_summary,
    update_investigation_state,
]

SHARED_RESEARCH_TOOLS: list[Any] = [
    fetch_web_page,
]

SHARED_GITHUB_TOOLS: list[Any] = [
    github_read_file,
    github_search_code,
    github_list_recent_commits,
    github_create_pull_request,
]

SHARED_REMEDIATION_TOOLS: list[Any] = [
    generate_remediation_suggestions,
    estimate_remediation_risk,
    get_gcloud_commands,
]

# =============================================================================
# Panel Tool Sets (used by council/panels.py)
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
    gcp_execute_sql,
    analyze_aggregate_metrics,
    find_exemplar_traces,
    correlate_metrics_with_traces_via_exemplars,
    build_service_dependency_graph,
    discover_telemetry_sources,
    list_traces,
    # State
    *SHARED_STATE_TOOLS,
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
    *SHARED_STATE_TOOLS,
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
    *SHARED_STATE_TOOLS,
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
    *SHARED_REMEDIATION_TOOLS,
    # State
    *SHARED_STATE_TOOLS,
]

DATA_PANEL_TOOLS: list[Any] = [
    # CA Data Agent (primary)
    query_data_agent,
    # Fallback: direct BigQuery
    gcp_execute_sql,
    discover_telemetry_sources,
    # Context
    list_time_series,
    # State
    *SHARED_STATE_TOOLS,
]

# =============================================================================
# Sub-Agent Tool Sets (OPT-4: shared source of truth)
# Used by sub_agents/*.py to keep tools aligned with panels.
# Sub-agents may have ADDITIONAL tools beyond what panels have.
# =============================================================================

TRACE_ANALYST_TOOLS: list[Any] = [
    # Core trace tools (superset of trace panel)
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
    # Cross-signal correlation
    correlate_logs_with_trace,
    correlate_metrics_with_traces_via_exemplars,
    query_promql,
    # State
    *SHARED_STATE_TOOLS,
]

AGGREGATE_ANALYZER_TOOLS: list[Any] = [
    # BigQuery fleet analysis
    gcp_execute_sql,
    analyze_aggregate_metrics,
    find_exemplar_traces,
    discover_telemetry_sources,
    # Trace selection
    list_traces,
    find_bottleneck_services,
    build_service_dependency_graph,
    # Context
    list_log_entries,
    list_time_series,
    query_promql,
    detect_trend_changes,
    correlate_metrics_with_traces_via_exemplars,
    # State
    *SHARED_STATE_TOOLS,
]

LOG_ANALYST_TOOLS: list[Any] = [
    # Core log tools
    list_log_entries,
    analyze_bigquery_log_patterns,
    extract_log_patterns,
    gcp_execute_sql,
    discover_telemetry_sources,
    # Context
    list_time_series,
    compare_time_periods,
    # Remediation
    *SHARED_REMEDIATION_TOOLS,
    # State
    *SHARED_STATE_TOOLS,
]

ALERT_ANALYST_TOOLS: list[Any] = [
    # Core alert tools
    list_alerts,
    list_alert_policies,
    get_alert,
    # Context
    list_log_entries,
    list_time_series,
    discover_telemetry_sources,
    # Remediation
    *SHARED_REMEDIATION_TOOLS,
    # State
    *SHARED_STATE_TOOLS,
]

METRICS_ANALYZER_TOOLS: list[Any] = [
    # Primary metrics (same as METRICS_PANEL_TOOLS with MCP fallbacks)
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
    *SHARED_STATE_TOOLS,
]

ROOT_CAUSE_ANALYST_TOOLS: list[Any] = [
    # Causal analysis
    perform_causal_analysis,
    build_cross_signal_timeline,
    # Correlation
    correlate_logs_with_trace,
    correlate_trace_with_metrics,
    # Impact & dependencies
    analyze_upstream_downstream_impact,
    build_service_dependency_graph,
    # Change detection
    detect_trend_changes,
    compare_time_periods,
    # Data retrieval
    list_log_entries,
    list_time_series,
    query_promql,
    fetch_trace,
    # Remediation
    *SHARED_REMEDIATION_TOOLS,
    # Online Research
    *SHARED_RESEARCH_TOOLS,
    # GitHub Self-Healing
    *SHARED_GITHUB_TOOLS,
    # State
    *SHARED_STATE_TOOLS,
]

# Orchestrator-level tools (for slim root agent — OPT-3)
# Direct-retrieval tools the root agent needs for DIRECT routing tier.
# Mirrors the direct-retrieval subset of slim_tools in agent.py.
ORCHESTRATOR_TOOLS: list[Any] = [
    # Direct-retrieval (DIRECT routing tier)
    fetch_trace,
    list_traces,
    list_log_entries,
    list_time_series,
    list_metric_descriptors,
    query_promql,
    list_alerts,
    list_alert_policies,
    get_alert,
    # Discovery
    discover_telemetry_sources,
    # Online Research
    *SHARED_RESEARCH_TOOLS,
    # State
    *SHARED_STATE_TOOLS,
]
