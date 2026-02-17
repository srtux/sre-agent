"""Google Cloud Platform tools for SRE Agent.

This module provides tools for interacting with GCP Observability services:
- BigQuery MCP for SQL-based analysis
- Cloud Logging MCP for log queries
- Cloud Monitoring MCP for metrics queries
- Direct API clients as fallback
- Analysis tools for Traces, Logs, Metrics, GKE, SLOs, and Remediation

All public symbols are lazy-loaded via PEP 562 __getattr__ to avoid
importing ~30 heavy submodules (and transitively vertexai, google-adk,
pandas, etc.) when only a subset is needed.  This reduces test-collection
time from ~60 s to < 2 s.
"""

from __future__ import annotations

import importlib
from typing import Any

# ---------------------------------------------------------------------------
# Lazy-import registry: symbol name → (relative module path, attribute name)
# ---------------------------------------------------------------------------
_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # Agent Trace Analysis
    "analyze_agent_token_usage": (
        ".analysis.agent_trace.tools",
        "analyze_agent_token_usage",
    ),
    "detect_agent_anti_patterns": (
        ".analysis.agent_trace.tools",
        "detect_agent_anti_patterns",
    ),
    "list_agent_traces": (".analysis.agent_trace.tools", "list_agent_traces"),
    "reconstruct_agent_interaction": (
        ".analysis.agent_trace.tools",
        "reconstruct_agent_interaction",
    ),
    # BigQuery Analysis
    "analyze_bigquery_log_patterns": (
        ".analysis.bigquery.logs",
        "analyze_bigquery_log_patterns",
    ),
    "analyze_aggregate_metrics": (
        ".analysis.bigquery.otel",
        "analyze_aggregate_metrics",
    ),
    "compare_time_periods": (".analysis.bigquery.otel", "compare_time_periods"),
    "correlate_logs_with_trace": (
        ".analysis.bigquery.otel",
        "correlate_logs_with_trace",
    ),
    "detect_trend_changes": (".analysis.bigquery.otel", "detect_trend_changes"),
    "find_exemplar_traces": (".analysis.bigquery.otel", "find_exemplar_traces"),
    # Change Correlation
    "correlate_changes_with_incident": (
        ".analysis.correlation.change_correlation",
        "correlate_changes_with_incident",
    ),
    # Critical Path
    "analyze_critical_path": (
        ".analysis.correlation.critical_path",
        "analyze_critical_path",
    ),
    "calculate_critical_path_contribution": (
        ".analysis.correlation.critical_path",
        "calculate_critical_path_contribution",
    ),
    "find_bottleneck_services": (
        ".analysis.correlation.critical_path",
        "find_bottleneck_services",
    ),
    # Cross-signal Correlation
    "analyze_signal_correlation_strength": (
        ".analysis.correlation.cross_signal",
        "analyze_signal_correlation_strength",
    ),
    "build_cross_signal_timeline": (
        ".analysis.correlation.cross_signal",
        "build_cross_signal_timeline",
    ),
    "correlate_metrics_with_traces_via_exemplars": (
        ".analysis.correlation.cross_signal",
        "correlate_metrics_with_traces_via_exemplars",
    ),
    "correlate_trace_with_metrics": (
        ".analysis.correlation.cross_signal",
        "correlate_trace_with_metrics",
    ),
    # Dependencies
    "analyze_upstream_downstream_impact": (
        ".analysis.correlation.dependencies",
        "analyze_upstream_downstream_impact",
    ),
    "build_service_dependency_graph": (
        ".analysis.correlation.dependencies",
        "build_service_dependency_graph",
    ),
    "detect_circular_dependencies": (
        ".analysis.correlation.dependencies",
        "detect_circular_dependencies",
    ),
    "find_hidden_dependencies": (
        ".analysis.correlation.dependencies",
        "find_hidden_dependencies",
    ),
    # Log Patterns
    "analyze_log_anomalies": (".analysis.logs.patterns", "analyze_log_anomalies"),
    "compare_log_patterns": (".analysis.logs.patterns", "compare_log_patterns"),
    "extract_log_patterns": (".analysis.logs.patterns", "extract_log_patterns"),
    # Metrics
    "compare_metric_windows": (
        ".analysis.metrics.anomaly_detection",
        "compare_metric_windows",
    ),
    "detect_metric_anomalies": (
        ".analysis.metrics.anomaly_detection",
        "detect_metric_anomalies",
    ),
    "calculate_series_stats": (
        ".analysis.metrics.statistics",
        "calculate_series_stats",
    ),
    # Remediation
    "generate_postmortem": (".analysis.remediation.postmortem", "generate_postmortem"),
    "estimate_remediation_risk": (
        ".analysis.remediation.suggestions",
        "estimate_remediation_risk",
    ),
    "find_similar_past_incidents": (
        ".analysis.remediation.suggestions",
        "find_similar_past_incidents",
    ),
    "generate_remediation_suggestions": (
        ".analysis.remediation.suggestions",
        "generate_remediation_suggestions",
    ),
    "get_gcloud_commands": (".analysis.remediation.suggestions", "get_gcloud_commands"),
    # SLO
    "analyze_multi_window_burn_rate": (
        ".analysis.slo.burn_rate",
        "analyze_multi_window_burn_rate",
    ),
    # Trace Analysis
    "build_call_graph": (".analysis.trace.analysis", "build_call_graph"),
    "calculate_span_durations": (
        ".analysis.trace.analysis",
        "calculate_span_durations",
    ),
    "extract_errors": (".analysis.trace.analysis", "extract_errors"),
    "summarize_trace": (".analysis.trace.analysis", "summarize_trace"),
    "validate_trace_quality": (".analysis.trace.analysis", "validate_trace_quality"),
    # Trace Comparison
    "compare_span_timings": (".analysis.trace.comparison", "compare_span_timings"),
    "find_structural_differences": (
        ".analysis.trace.comparison",
        "find_structural_differences",
    ),
    # Trace Filters
    "select_traces_from_statistical_outliers": (
        ".analysis.trace.filters",
        "select_traces_from_statistical_outliers",
    ),
    "select_traces_manually": (".analysis.trace.filters", "select_traces_manually"),
    # Trace Patterns
    "detect_all_sre_patterns": (".analysis.trace.patterns", "detect_all_sre_patterns"),
    "detect_cascading_timeout": (
        ".analysis.trace.patterns",
        "detect_cascading_timeout",
    ),
    "detect_connection_pool_issues": (
        ".analysis.trace.patterns",
        "detect_connection_pool_issues",
    ),
    "detect_retry_storm": (".analysis.trace.patterns", "detect_retry_storm"),
    # Trace Statistical Analysis
    "analyze_trace_patterns": (
        ".analysis.trace.statistical_analysis",
        "analyze_trace_patterns",
    ),
    "compute_latency_statistics": (
        ".analysis.trace.statistical_analysis",
        "compute_latency_statistics",
    ),
    "detect_latency_anomalies": (
        ".analysis.trace.statistical_analysis",
        "detect_latency_anomalies",
    ),
    "perform_causal_analysis": (
        ".analysis.trace.statistical_analysis",
        "perform_causal_analysis",
    ),
    # Trace Comprehensive
    "analyze_trace_comprehensive": (
        ".analysis.trace_comprehensive",
        "analyze_trace_comprehensive",
    ),
    # BigQuery CA Data Agent
    "query_data_agent": (".bigquery.ca_data_agent", "query_data_agent"),
    # Clients - Alerts
    "get_alert": (".clients.alerts", "get_alert"),
    "list_alert_policies": (".clients.alerts", "list_alert_policies"),
    "list_alerts": (".clients.alerts", "list_alerts"),
    # Clients - GCP Projects
    "list_gcp_projects": (".clients.gcp_projects", "list_gcp_projects"),
    # Clients - GKE
    "analyze_hpa_events": (".clients.gke", "analyze_hpa_events"),
    "analyze_node_conditions": (".clients.gke", "analyze_node_conditions"),
    "correlate_trace_with_kubernetes": (
        ".clients.gke",
        "correlate_trace_with_kubernetes",
    ),
    "get_container_oom_events": (".clients.gke", "get_container_oom_events"),
    "get_gke_cluster_health": (".clients.gke", "get_gke_cluster_health"),
    "get_pod_restart_events": (".clients.gke", "get_pod_restart_events"),
    "get_workload_health_summary": (".clients.gke", "get_workload_health_summary"),
    # Clients - Logging
    "get_logs_for_trace": (".clients.logging", "get_logs_for_trace"),
    "list_error_events": (".clients.logging", "list_error_events"),
    "list_log_entries": (".clients.logging", "list_log_entries"),
    "list_logs": (".clients.logging", "list_logs"),
    "list_resource_keys": (".clients.logging", "list_resource_keys"),
    # Clients - Monitoring
    "list_metric_descriptors": (".clients.monitoring", "list_metric_descriptors"),
    "list_time_series": (".clients.monitoring", "list_time_series"),
    "query_promql": (".clients.monitoring", "query_promql"),
    # Clients - SLO
    "analyze_error_budget_burn": (".clients.slo", "analyze_error_budget_burn"),
    "correlate_incident_with_slo_impact": (
        ".clients.slo",
        "correlate_incident_with_slo_impact",
    ),
    "get_golden_signals": (".clients.slo", "get_golden_signals"),
    "get_slo_status": (".clients.slo", "get_slo_status"),
    "list_slos": (".clients.slo", "list_slos"),
    "predict_slo_violation": (".clients.slo", "predict_slo_violation"),
    # Clients - Trace
    "fetch_trace": (".clients.trace", "fetch_trace"),
    "find_example_traces": (".clients.trace", "find_example_traces"),
    "get_current_time": (".clients.trace", "get_current_time"),
    "get_trace_by_url": (".clients.trace", "get_trace_by_url"),
    "list_traces": (".clients.trace", "list_traces"),
    # Configuration
    "ToolCategory": (".config", "ToolCategory"),
    "ToolConfig": (".config", "ToolConfig"),
    "ToolConfigManager": (".config", "ToolConfigManager"),
    "ToolTestResult": (".config", "ToolTestResult"),
    "ToolTestStatus": (".config", "ToolTestStatus"),
    "get_tool_config_manager": (".config", "get_tool_config_manager"),
    # Discovery
    "discover_telemetry_sources": (
        ".discovery.discovery_tool",
        "discover_telemetry_sources",
    ),
    # Exploration
    "explore_project_health": (".exploration", "explore_project_health"),
    # Investigation
    "get_investigation_summary": (".investigation", "get_investigation_summary"),
    "update_investigation_state": (".investigation", "update_investigation_state"),
    # MCP
    "call_mcp_tool_with_retry": (".mcp.gcp", "call_mcp_tool_with_retry"),
    "create_bigquery_mcp_toolset": (".mcp.gcp", "create_bigquery_mcp_toolset"),
    "create_logging_mcp_toolset": (".mcp.gcp", "create_logging_mcp_toolset"),
    "create_monitoring_mcp_toolset": (".mcp.gcp", "create_monitoring_mcp_toolset"),
    "get_project_id_with_fallback": (".mcp.gcp", "get_project_id_with_fallback"),
    "mcp_execute_sql": (".mcp.gcp", "mcp_execute_sql"),
    "mcp_list_log_entries": (".mcp.gcp", "mcp_list_log_entries"),
    "mcp_list_timeseries": (".mcp.gcp", "mcp_list_timeseries"),
    "mcp_query_range": (".mcp.gcp", "mcp_query_range"),
    # Memory
    "add_finding_to_memory": (".memory", "add_finding_to_memory"),
    "analyze_and_learn_from_traces": (".memory", "analyze_and_learn_from_traces"),
    "complete_investigation": (".memory", "complete_investigation"),
    "get_recommended_investigation_strategy": (
        ".memory",
        "get_recommended_investigation_strategy",
    ),
    "search_memory": (".memory", "search_memory"),
    # Proactive
    "suggest_next_steps": (".proactive", "suggest_next_steps"),
    # Research (Online)
    "fetch_web_page": (".research", "fetch_web_page"),
    # GitHub (Self-Healing)
    "github_read_file": (".github.tools", "github_read_file"),
    "github_search_code": (".github.tools", "github_search_code"),
    "github_list_recent_commits": (".github.tools", "github_list_recent_commits"),
    "github_create_pull_request": (".github.tools", "github_create_pull_request"),
    # Reporting
    "synthesize_report": (".reporting", "synthesize_report"),
    # Sandbox
    "LocalCodeExecutor": (".sandbox", "LocalCodeExecutor"),
    "execute_custom_analysis_in_sandbox": (
        ".sandbox",
        "execute_custom_analysis_in_sandbox",
    ),
    "get_code_executor": (".sandbox", "get_code_executor"),
    "get_sandbox_status": (".sandbox", "get_sandbox_status"),
    "is_local_execution_enabled": (".sandbox", "is_local_execution_enabled"),
    "is_remote_mode": (".sandbox", "is_remote_mode"),
    "is_sandbox_enabled": (".sandbox", "is_sandbox_enabled"),
    "summarize_log_entries_in_sandbox": (
        ".sandbox",
        "summarize_log_entries_in_sandbox",
    ),
    "summarize_metric_descriptors_in_sandbox": (
        ".sandbox",
        "summarize_metric_descriptors_in_sandbox",
    ),
    "summarize_time_series_in_sandbox": (
        ".sandbox",
        "summarize_time_series_in_sandbox",
    ),
    "summarize_traces_in_sandbox": (".sandbox", "summarize_traces_in_sandbox"),
}


def __getattr__(name: str) -> Any:
    """Lazy-load tool symbols on first access (PEP 562).

    Avoids importing ~30 heavy submodules at package init time, which
    transitively pulls in vertexai (~40 s), google-adk, pandas, etc.
    """
    if name in _LAZY_IMPORTS:
        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path, __package__)
        value = getattr(module, attr_name)
        # Cache in module dict so __getattr__ is not called again
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = sorted(_LAZY_IMPORTS.keys())
