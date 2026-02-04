"""Tool Configuration Management for SRE Agent.

This module provides the ability to enable/disable tools and test their connectivity.
Configuration is stored in memory with persistence via a JSON file.
"""

import asyncio
import json
import logging
import os
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Configuration file path (can be overridden via environment variable)
CONFIG_FILE_PATH = Path(os.getenv("TOOL_CONFIG_PATH", ".tool_config.json"))


class ToolCategory(str, Enum):
    """Categories of tools based on their functionality and signal type."""

    # Discovery & Global
    DISCOVERY = "discovery"  # Find data sources, projects, etc.
    ORCHESTRATION = "orchestration"  # High-level flow control (Stage 0, 1, 2)

    # Trace Signal
    TRACE_FETCH = "trace_fetch"  # Retrieve raw spans/traces
    TRACE_ANALYZE = "trace_analyze"  # Process spans, critical path, patterns

    # Log Signal
    LOG_FETCH = "log_fetch"  # Retrieve log entries/events
    LOG_ANALYZE = "log_analyze"  # Pattern mining, anomaly detection

    # Metric Signal
    METRIC_FETCH = "metric_fetch"  # Retrieve time series/exemplars
    METRIC_ANALYZE = "metric_analyze"  # Trends, stats, anomaly detection

    # Incident & Health
    ALERT = "alert"  # Alert policies, active incidents
    SLO = "slo"  # Service Level Objectives & status
    GKE = "gke"  # Kubernetes health & events

    # Remediation
    REMEDIATION = "remediation"  # Suggestions, gcloud commands, risk

    # Cross-Signal
    CORRELATION = "correlation"  # Cross-pillar analysis (Trace + Log + Metric)

    # Legacy/Infrastructure
    API_CLIENT = "api_client"  # Generic direct API tools
    MCP = "mcp"  # Generic MCP tools
    ANALYSIS = "analysis"  # Generic analysis tools
    MEMORY = "memory"  # Memory and context tools


class ToolTestStatus(str, Enum):
    """Status of tool connectivity test."""

    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    NOT_TESTED = "not_tested"
    NOT_TESTABLE = "not_testable"


@dataclass
class ToolTestResult:
    """Result of a tool connectivity test."""

    status: ToolTestStatus
    message: str
    latency_ms: float | None = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolConfig:
    """Configuration for a single tool."""

    name: str
    display_name: str
    description: str
    category: ToolCategory
    enabled: bool = True
    testable: bool = False  # Whether the tool can be tested for connectivity
    last_test_result: ToolTestResult | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "display_name": self.display_name,
            "description": self.description,
            "category": self.category.value,
            "enabled": self.enabled,
            "testable": self.testable,
            "last_test_result": {
                "status": self.last_test_result.status.value,
                "message": self.last_test_result.message,
                "latency_ms": self.last_test_result.latency_ms,
                "timestamp": self.last_test_result.timestamp,
                "details": self.last_test_result.details,
            }
            if self.last_test_result
            else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ToolConfig":
        """Create from dictionary."""
        last_test = None
        if data.get("last_test_result"):
            test_data = data["last_test_result"]
            last_test = ToolTestResult(
                status=ToolTestStatus(test_data["status"]),
                message=test_data["message"],
                latency_ms=test_data.get("latency_ms"),
                timestamp=test_data.get("timestamp", ""),
                details=test_data.get("details", {}),
            )

        return cls(
            name=data["name"],
            display_name=data["display_name"],
            description=data["description"],
            category=ToolCategory(data["category"]),
            enabled=data.get("enabled", True),
            testable=data.get("testable", False),
            last_test_result=last_test,
        )


# ============================================================================
# Tool Registry - Define all available tools
# ============================================================================

# Tool definitions with metadata
TOOL_DEFINITIONS: list[ToolConfig] = [
    # -------------------------------------------------------------------------
    # Orchestration & State Tools
    # -------------------------------------------------------------------------
    ToolConfig(
        name="update_investigation_state",
        display_name="Update Investigation State",
        description="Update the current phase, findings, and hypotheses of an investigation",
        category=ToolCategory.ORCHESTRATION,
        testable=False,
    ),
    ToolConfig(
        name="get_investigation_summary",
        display_name="Get Investigation Summary",
        description="Get a summary of current findings and investigation progress",
        category=ToolCategory.ORCHESTRATION,
        testable=False,
    ),
    # -------------------------------------------------------------------------
    # Memory Tools
    # -------------------------------------------------------------------------
    ToolConfig(
        name="add_finding_to_memory",
        display_name="Add Finding to Memory",
        description="Explicitly add a finding to the agent's memory",
        category=ToolCategory.MEMORY,
        testable=False,
    ),
    ToolConfig(
        name="search_memory",
        display_name="Search Memory",
        description="Search the agent's memory for relevant findings",
        category=ToolCategory.MEMORY,
        testable=False,
    ),
    ToolConfig(
        name="suggest_next_steps",
        display_name="Suggest Next Steps",
        description="Suggest the next best steps based on investigation state",
        category=ToolCategory.ORCHESTRATION,
        testable=False,
    ),
    # -------------------------------------------------------------------------
    # API Client Tools (Direct GCP APIs) - TESTABLE
    # -------------------------------------------------------------------------
    ToolConfig(
        name="fetch_trace",
        display_name="Fetch Trace",
        description="Fetch a trace from Cloud Trace API",
        category=ToolCategory.TRACE_FETCH,
        testable=True,
    ),
    ToolConfig(
        name="list_traces",
        display_name="List Traces",
        description="List traces from Cloud Trace API",
        category=ToolCategory.TRACE_FETCH,
        testable=True,
    ),
    ToolConfig(
        name="find_example_traces",
        display_name="Find Example Traces",
        description="Find example traces for comparison",
        category=ToolCategory.API_CLIENT,
        testable=True,
    ),
    ToolConfig(
        name="get_trace_by_url",
        display_name="Get Trace by URL",
        description="Fetch a trace using its Cloud Console URL",
        category=ToolCategory.API_CLIENT,
        testable=False,
    ),
    ToolConfig(
        name="list_log_entries",
        display_name="List Log Entries",
        description="List log entries from Cloud Logging API",
        category=ToolCategory.LOG_FETCH,
        testable=True,
    ),
    ToolConfig(
        name="get_logs_for_trace",
        display_name="Get Logs for Trace",
        description="Get log entries correlated with a specific trace",
        category=ToolCategory.LOG_FETCH,
        testable=True,
    ),
    ToolConfig(
        name="list_error_events",
        display_name="List Error Events",
        description="List error events from Cloud Logging",
        category=ToolCategory.API_CLIENT,
        testable=True,
    ),
    ToolConfig(
        name="list_time_series",
        display_name="List Time Series",
        description="List metrics time series from Cloud Monitoring",
        category=ToolCategory.METRIC_FETCH,
        testable=True,
    ),
    ToolConfig(
        name="query_promql",
        display_name="Query PromQL",
        description="Execute PromQL queries against Cloud Monitoring",
        category=ToolCategory.METRIC_FETCH,
        testable=True,
    ),
    ToolConfig(
        name="list_alerts",
        display_name="List Alerts",
        description="List active alerts from Cloud Monitoring",
        category=ToolCategory.ALERT,
        testable=True,
    ),
    ToolConfig(
        name="get_alert",
        display_name="Get Alert",
        description="Get details of a specific alert",
        category=ToolCategory.API_CLIENT,
        testable=True,
    ),
    ToolConfig(
        name="list_alert_policies",
        display_name="List Alert Policies",
        description="List alert policies from Cloud Monitoring",
        category=ToolCategory.API_CLIENT,
        testable=True,
    ),
    ToolConfig(
        name="get_current_time",
        display_name="Get Current Time",
        description="Get current time in various formats",
        category=ToolCategory.API_CLIENT,
        testable=False,
    ),
    # -------------------------------------------------------------------------
    # MCP Tools - TESTABLE
    # -------------------------------------------------------------------------
    ToolConfig(
        name="mcp_list_log_entries",
        display_name="MCP List Log Entries",
        description="List log entries via MCP Cloud Logging server",
        category=ToolCategory.MCP,
        testable=True,
        enabled=True,  # Enabled by default
    ),
    ToolConfig(
        name="mcp_list_timeseries",
        display_name="MCP List Time Series",
        description="List metrics via MCP Cloud Monitoring server",
        category=ToolCategory.MCP,
        testable=True,
        enabled=True,  # Enabled by default
    ),
    ToolConfig(
        name="mcp_query_range",
        display_name="MCP Query Range (PromQL)",
        description="Execute PromQL queries via MCP Cloud Monitoring server",
        category=ToolCategory.MCP,
        testable=True,
        enabled=True,  # Enabled by default
    ),
    ToolConfig(
        name="mcp_execute_sql",
        display_name="MCP Execute SQL",
        description="Execute SQL queries via MCP BigQuery server",
        category=ToolCategory.MCP,
        testable=True,
        enabled=True,  # Enabled by default for aggregate analysis
    ),
    ToolConfig(
        name="mcp_list_dataset_ids",
        display_name="MCP List BigQuery Datasets",
        description="List BigQuery datasets using MCP",
        category=ToolCategory.DISCOVERY,
        testable=False,
        enabled=True,
    ),
    ToolConfig(
        name="mcp_list_table_ids",
        display_name="MCP List BigQuery Tables",
        description="List BigQuery tables using MCP",
        category=ToolCategory.DISCOVERY,
        testable=False,
        enabled=True,
    ),
    ToolConfig(
        name="mcp_get_table_info",
        display_name="MCP Get BigQuery Table Info",
        description="Get BigQuery table schema and info using MCP",
        category=ToolCategory.DISCOVERY,
        testable=False,
        enabled=True,
    ),
    # -------------------------------------------------------------------------
    # BigQuery/OTel Tools
    # -------------------------------------------------------------------------
    ToolConfig(
        name="analyze_aggregate_metrics",
        display_name="Analyze Aggregate Metrics",
        description="Analyze aggregate metrics from BigQuery OpenTelemetry tables",
        category=ToolCategory.METRIC_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="find_exemplar_traces",
        display_name="Find Exemplar Traces",
        description="Find exemplar traces (baseline and anomaly) from BigQuery",
        category=ToolCategory.TRACE_FETCH,
        testable=False,
    ),
    ToolConfig(
        name="compare_time_periods",
        display_name="Compare Time Periods",
        description="Compare metrics between two time periods",
        category=ToolCategory.METRIC_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="detect_trend_changes",
        display_name="Detect Trend Changes",
        description="Detect trend changes in metrics over time",
        category=ToolCategory.METRIC_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="correlate_logs_with_trace",
        display_name="Correlate Logs with Trace",
        description="Correlate log entries with a specific trace",
        category=ToolCategory.CORRELATION,
        testable=False,
    ),
    # -------------------------------------------------------------------------
    # Trace Analysis Tools
    # -------------------------------------------------------------------------
    ToolConfig(
        name="calculate_span_durations",
        display_name="Calculate Span Durations",
        description="Calculate durations for all spans in a trace",
        category=ToolCategory.TRACE_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="extract_errors",
        display_name="Extract Errors",
        description="Extract error information from trace spans",
        category=ToolCategory.TRACE_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="build_call_graph",
        display_name="Build Call Graph",
        description="Build a call graph from trace data",
        category=ToolCategory.TRACE_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="summarize_trace",
        display_name="Summarize Trace",
        description="Generate a summary of trace data",
        category=ToolCategory.TRACE_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="validate_trace_quality",
        display_name="Validate Trace Quality",
        description="Validate the quality and completeness of trace data",
        category=ToolCategory.TRACE_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="compare_span_timings",
        display_name="Compare Span Timings",
        description="Compare span timings between two traces",
        category=ToolCategory.TRACE_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="find_structural_differences",
        display_name="Find Structural Differences",
        description="Find structural differences between two traces",
        category=ToolCategory.TRACE_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="analyze_trace_comprehensive",
        display_name="Analyze Trace Comprehensive",
        description="Comprehensive trace analysis (mega-tool) combining validation, durations, errors, critical path, and structure",
        category=ToolCategory.TRACE_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="analyze_trace_patterns",
        display_name="Analyze Trace Patterns",
        description="Analyze trace patterns for statistical anomalies",
        category=ToolCategory.ANALYSIS,
        testable=False,
    ),
    ToolConfig(
        name="compute_latency_statistics",
        display_name="Compute Latency Statistics",
        description="Compute latency statistics for traces",
        category=ToolCategory.ANALYSIS,
        testable=False,
    ),
    ToolConfig(
        name="select_traces_from_statistical_outliers",
        display_name="Select Statistical Outliers",
        description="Select traces that are statistical outliers",
        category=ToolCategory.ANALYSIS,
        testable=False,
    ),
    ToolConfig(
        name="select_traces_manually",
        display_name="Select Traces Manually",
        description="Manually select traces for analysis",
        category=ToolCategory.ANALYSIS,
        testable=False,
    ),
    # -------------------------------------------------------------------------
    # SRE Pattern Detection Tools
    # -------------------------------------------------------------------------
    ToolConfig(
        name="detect_retry_storm",
        display_name="Detect Retry Storm",
        description="Identify excessive retries and exponential backoff patterns",
        category=ToolCategory.TRACE_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="detect_cascading_timeout",
        display_name="Detect Cascading Timeout",
        description="Trace timeout propagation through the call chain",
        category=ToolCategory.TRACE_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="detect_connection_pool_issues",
        display_name="Detect Connection Pool Issues",
        description="Detect waits for database or HTTP connections",
        category=ToolCategory.TRACE_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="detect_all_sre_patterns",
        display_name="Detect All SRE Patterns",
        description="Comprehensive scan for multiple SRE anti-patterns",
        category=ToolCategory.TRACE_ANALYZE,
        testable=False,
    ),
    # -------------------------------------------------------------------------
    # Log Analysis Tools
    # -------------------------------------------------------------------------
    ToolConfig(
        name="extract_log_patterns",
        display_name="Extract Log Patterns",
        description="Extract patterns from log entries using Drain3",
        category=ToolCategory.LOG_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="compare_log_patterns",
        display_name="Compare Log Patterns",
        description="Compare log patterns between two time periods",
        category=ToolCategory.LOG_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="analyze_log_anomalies",
        display_name="Analyze Log Anomalies",
        description="Analyze log anomalies and detect issues",
        category=ToolCategory.LOG_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="analyze_bigquery_log_patterns",
        display_name="Analyze BigQuery Log Patterns",
        description="Analyze log patterns using BigQuery for large-scale analysis",
        category=ToolCategory.LOG_ANALYZE,
        testable=False,
    ),
    # -------------------------------------------------------------------------
    # Metrics Analysis Tools
    # -------------------------------------------------------------------------
    ToolConfig(
        name="detect_metric_anomalies",
        display_name="Detect Metric Anomalies",
        description="Detect anomalies in metric time series",
        category=ToolCategory.METRIC_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="compare_metric_windows",
        display_name="Compare Metric Windows",
        description="Compare metrics between two time windows",
        category=ToolCategory.METRIC_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="calculate_series_stats",
        display_name="Calculate Series Stats",
        description="Calculate statistical metrics for time series",
        category=ToolCategory.METRIC_ANALYZE,
        testable=False,
    ),
    # -------------------------------------------------------------------------
    # Cross-Signal Correlation Tools
    # -------------------------------------------------------------------------
    ToolConfig(
        name="correlate_trace_with_metrics",
        display_name="Correlate Trace with Metrics",
        description="Correlate trace data with metrics",
        category=ToolCategory.CORRELATION,
        testable=False,
    ),
    ToolConfig(
        name="correlate_metrics_with_traces_via_exemplars",
        display_name="Correlate Metrics via Exemplars",
        description="Correlate metrics with traces using exemplars",
        category=ToolCategory.CORRELATION,
        testable=False,
    ),
    ToolConfig(
        name="build_cross_signal_timeline",
        display_name="Build Cross-Signal Timeline",
        description="Build a unified timeline from multiple signal sources",
        category=ToolCategory.CORRELATION,
        testable=False,
    ),
    ToolConfig(
        name="analyze_signal_correlation_strength",
        display_name="Analyze Signal Correlation",
        description="Analyze the correlation strength between signals",
        category=ToolCategory.CORRELATION,
        testable=False,
    ),
    # -------------------------------------------------------------------------
    # Critical Path & Dependency Tools
    # -------------------------------------------------------------------------
    ToolConfig(
        name="analyze_critical_path",
        display_name="Analyze Critical Path",
        description="Analyze the critical path in a trace",
        category=ToolCategory.TRACE_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="find_bottleneck_services",
        display_name="Find Bottleneck Services",
        description="Find services that are bottlenecks in the request path",
        category=ToolCategory.TRACE_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="calculate_critical_path_contribution",
        display_name="Calculate Critical Path Contribution",
        description="Calculate each service's contribution to critical path",
        category=ToolCategory.TRACE_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="perform_causal_analysis",
        display_name="Perform Causal Analysis",
        description="Perform causal analysis on trace data to identify root cause",
        category=ToolCategory.TRACE_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="detect_latency_anomalies",
        display_name="Detect Latency Anomalies",
        description="Detect statistical latency anomalies in traces",
        category=ToolCategory.TRACE_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="build_service_dependency_graph",
        display_name="Build Service Dependency Graph",
        description="Build a graph of service dependencies",
        category=ToolCategory.DISCOVERY,
        testable=False,
    ),
    ToolConfig(
        name="analyze_upstream_downstream_impact",
        display_name="Analyze Impact",
        description="Analyze upstream and downstream service impact",
        category=ToolCategory.TRACE_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="detect_circular_dependencies",
        display_name="Detect Circular Dependencies",
        description="Detect circular dependencies in service graph",
        category=ToolCategory.TRACE_ANALYZE,
        testable=False,
    ),
    ToolConfig(
        name="find_hidden_dependencies",
        display_name="Find Hidden Dependencies",
        description="Find hidden or implicit service dependencies",
        category=ToolCategory.TRACE_ANALYZE,
        testable=False,
    ),
    # -------------------------------------------------------------------------
    # SLO/SLI Tools
    # -------------------------------------------------------------------------
    ToolConfig(
        name="list_slos",
        display_name="List SLOs",
        description="List Service Level Objectives",
        category=ToolCategory.SLO,
        testable=True,
    ),
    ToolConfig(
        name="get_slo_status",
        display_name="Get SLO Status",
        description="Get current status of an SLO",
        category=ToolCategory.SLO,
        testable=True,
    ),
    ToolConfig(
        name="analyze_error_budget_burn",
        display_name="Analyze Error Budget Burn",
        description="Analyze error budget burn rate",
        category=ToolCategory.SLO,
        testable=False,
    ),
    ToolConfig(
        name="get_golden_signals",
        display_name="Get Golden Signals",
        description="Get SRE golden signals for a service",
        category=ToolCategory.SLO,
        testable=False,
    ),
    ToolConfig(
        name="correlate_incident_with_slo_impact",
        display_name="Correlate Incident with SLO",
        description="Correlate an incident with SLO impact",
        category=ToolCategory.SLO,
        testable=False,
    ),
    ToolConfig(
        name="predict_slo_violation",
        display_name="Predict SLO Violation",
        description="Predict potential SLO violations",
        category=ToolCategory.SLO,
        testable=False,
    ),
    # -------------------------------------------------------------------------
    # GKE/Kubernetes Tools
    # -------------------------------------------------------------------------
    ToolConfig(
        name="get_gke_cluster_health",
        display_name="Get GKE Cluster Health",
        description="Get health status of a GKE cluster",
        category=ToolCategory.GKE,
        testable=True,
    ),
    ToolConfig(
        name="analyze_node_conditions",
        display_name="Analyze Node Conditions",
        description="Analyze GKE node conditions",
        category=ToolCategory.GKE,
        testable=True,
    ),
    ToolConfig(
        name="get_pod_restart_events",
        display_name="Get Pod Restart Events",
        description="Get pod restart events from GKE",
        category=ToolCategory.GKE,
        testable=True,
    ),
    ToolConfig(
        name="analyze_hpa_events",
        display_name="Analyze HPA Events",
        description="Analyze Horizontal Pod Autoscaler events",
        category=ToolCategory.GKE,
        testable=True,
    ),
    ToolConfig(
        name="get_container_oom_events",
        display_name="Get Container OOM Events",
        description="Get container Out-of-Memory events",
        category=ToolCategory.GKE,
        testable=True,
    ),
    ToolConfig(
        name="correlate_trace_with_kubernetes",
        display_name="Correlate Trace with K8s",
        description="Correlate trace data with Kubernetes events",
        category=ToolCategory.CORRELATION,
        testable=False,
    ),
    ToolConfig(
        name="get_workload_health_summary",
        display_name="Get Workload Health",
        description="Get health summary of GKE workloads",
        category=ToolCategory.GKE,
        testable=True,
    ),
    # -------------------------------------------------------------------------
    # Remediation Tools
    # -------------------------------------------------------------------------
    ToolConfig(
        name="generate_remediation_suggestions",
        display_name="Generate Remediation Suggestions",
        description="Generate remediation suggestions for issues",
        category=ToolCategory.REMEDIATION,
        testable=False,
    ),
    ToolConfig(
        name="get_gcloud_commands",
        display_name="Get gcloud Commands",
        description="Get gcloud commands for remediation",
        category=ToolCategory.REMEDIATION,
        testable=False,
    ),
    ToolConfig(
        name="estimate_remediation_risk",
        display_name="Estimate Remediation Risk",
        description="Estimate the risk of remediation actions",
        category=ToolCategory.REMEDIATION,
        testable=False,
    ),
    ToolConfig(
        name="find_similar_past_incidents",
        display_name="Find Similar Incidents",
        description="Find similar past incidents",
        category=ToolCategory.REMEDIATION,
        testable=False,
    ),
    ToolConfig(
        name="generate_postmortem",
        display_name="Generate Postmortem",
        description="Generate a structured blameless postmortem report following Google SRE practices",
        category=ToolCategory.REMEDIATION,
        testable=False,
    ),
    ToolConfig(
        name="analyze_multi_window_burn_rate",
        display_name="Multi-Window SLO Burn Rate",
        description="Analyze SLO burn rate using Google's multi-window alerting strategy",
        category=ToolCategory.ANALYSIS,
        testable=False,
    ),
    ToolConfig(
        name="correlate_changes_with_incident",
        display_name="Correlate Changes with Incident",
        description="Find recent deployments and config changes correlated with an incident",
        category=ToolCategory.ANALYSIS,
        testable=False,
    ),
    # -------------------------------------------------------------------------
    # Discovery Tools
    # -------------------------------------------------------------------------
    ToolConfig(
        name="discover_telemetry_sources",
        display_name="Discover Telemetry Sources",
        description="Discover available telemetry sources",
        category=ToolCategory.DISCOVERY,
        testable=False,
    ),
    ToolConfig(
        name="list_gcp_projects",
        display_name="List GCP Projects",
        description="List accessible GCP projects",
        category=ToolCategory.DISCOVERY,
        testable=True,
    ),
    ToolConfig(
        name="explore_project_health",
        display_name="Explore Project Health",
        description="Broad project health exploration across all signals",
        category=ToolCategory.DISCOVERY,
        testable=False,
    ),
    # -------------------------------------------------------------------------
    # Agent Debugging Tools
    # -------------------------------------------------------------------------
    ToolConfig(
        name="list_agent_traces",
        display_name="List Agent Traces",
        description="List traces of agent execution for debugging",
        category=ToolCategory.ANALYSIS,
        testable=False,
    ),
    ToolConfig(
        name="analyze_agent_token_usage",
        display_name="Analyze Agent Token Usage",
        description="Analyze token usage patterns for the agent",
        category=ToolCategory.ANALYSIS,
        testable=False,
    ),
    ToolConfig(
        name="detect_agent_anti_patterns",
        display_name="Detect Agent Anti-Patterns",
        description="Detect common anti-patterns in agent execution",
        category=ToolCategory.ANALYSIS,
        testable=False,
    ),
    ToolConfig(
        name="reconstruct_agent_interaction",
        display_name="Reconstruct Agent Interaction",
        description="Reconstruct the interaction history of the agent",
        category=ToolCategory.ANALYSIS,
        testable=False,
    ),
    # -------------------------------------------------------------------------
    # Orchestration Tools
    # -------------------------------------------------------------------------
    ToolConfig(
        name="run_aggregate_analysis",
        display_name="Run Aggregate Analysis",
        description="Run Stage 0: Aggregate analysis using BigQuery",
        category=ToolCategory.ORCHESTRATION,
        testable=False,
    ),
    ToolConfig(
        name="run_triage_analysis",
        display_name="Run Triage Analysis",
        description="Run Stage 1: Parallel triage analysis with sub-agents",
        category=ToolCategory.ORCHESTRATION,
        testable=False,
    ),
    ToolConfig(
        name="run_log_pattern_analysis",
        display_name="Run Log Pattern Analysis",
        description="Run log pattern analysis to find emergent issues",
        category=ToolCategory.ORCHESTRATION,
        testable=False,
    ),
    ToolConfig(
        name="run_deep_dive_analysis",
        display_name="Run Deep Dive Analysis",
        description="Run Stage 2: Deep dive root cause analysis",
        category=ToolCategory.ORCHESTRATION,
        testable=False,
    ),
    ToolConfig(
        name="list_metric_descriptors",
        display_name="List Metric Descriptors",
        description="List and filter GCP metric descriptors",
        category=ToolCategory.METRIC_FETCH,
        testable=True,
    ),
    # -------------------------------------------------------------------------
    # Reporting Tools
    # -------------------------------------------------------------------------
    ToolConfig(
        name="synthesize_report",
        display_name="Synthesize Report",
        description="Synthesize a comprehensive incident report",
        category=ToolCategory.ORCHESTRATION,
        testable=False,
    ),
    # Mutation tools (restart_pod, scale_deployment, rollback_deployment) are
    # currently unimplemented placeholders and have been removed.
]


class ToolConfigManager:
    """Manager for tool configuration with persistence."""

    _instance: "ToolConfigManager | None" = None
    _initialized: bool = False

    def __new__(cls) -> "ToolConfigManager":
        """Create singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize tool configuration manager."""
        if self._initialized:
            return

        self._configs: dict[str, ToolConfig] = {}
        self._test_functions: dict[
            str, Callable[[], Coroutine[Any, Any, ToolTestResult]]
        ] = {}
        self._initialized = True

        # Initialize with default configs
        self._initialize_defaults()

        # Load persisted config
        self._load_config()

    def _initialize_defaults(self) -> None:
        """Initialize with default tool configurations."""
        for tool_def in TOOL_DEFINITIONS:
            self._configs[tool_def.name] = ToolConfig(
                name=tool_def.name,
                display_name=tool_def.display_name,
                description=tool_def.description,
                category=tool_def.category,
                enabled=tool_def.enabled,
                testable=tool_def.testable,
            )

    def _load_config(self) -> None:
        """Load configuration from file if exists."""
        if not CONFIG_FILE_PATH.exists():
            return

        try:
            with open(CONFIG_FILE_PATH) as f:
                data = json.load(f)

            for tool_data in data.get("tools", []):
                name = tool_data.get("name")
                if name and name in self._configs:
                    # Only update enabled status from persisted config
                    self._configs[name].enabled = tool_data.get("enabled", True)

                    # Restore last test result if present
                    if tool_data.get("last_test_result"):
                        test_data = tool_data["last_test_result"]
                        self._configs[name].last_test_result = ToolTestResult(
                            status=ToolTestStatus(test_data["status"]),
                            message=test_data["message"],
                            latency_ms=test_data.get("latency_ms"),
                            timestamp=test_data.get("timestamp", ""),
                            details=test_data.get("details", {}),
                        )

            logger.info(f"Loaded tool configuration from {CONFIG_FILE_PATH}")
        except Exception as e:
            logger.warning(f"Failed to load tool configuration: {e}")

    def _save_config(self) -> None:
        """Save configuration to file."""
        # Don't save to the default config file during tests to avoid workspace pollution
        if (
            os.getenv("PYTEST_CURRENT_TEST")
            and str(CONFIG_FILE_PATH) == ".tool_config.json"
        ):
            logger.debug(f"Skipping save to {CONFIG_FILE_PATH} during test run")
            return

        try:
            data = {
                "tools": [config.to_dict() for config in self._configs.values()],
                "version": "1.0",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }

            with open(CONFIG_FILE_PATH, "w") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved tool configuration to {CONFIG_FILE_PATH}")
        except Exception as e:
            logger.error(f"Failed to save tool configuration: {e}")

    def get_all_configs(self) -> list[ToolConfig]:
        """Get all tool configurations."""
        return list(self._configs.values())

    def get_config(self, tool_name: str) -> ToolConfig | None:
        """Get configuration for a specific tool."""
        return self._configs.get(tool_name)

    def get_configs_by_category(self, category: ToolCategory) -> list[ToolConfig]:
        """Get all tool configurations in a category."""
        return [c for c in self._configs.values() if c.category == category]

    def set_enabled(self, tool_name: str, enabled: bool) -> bool:
        """Enable or disable a tool. Returns True if successful."""
        if tool_name not in self._configs:
            return False

        self._configs[tool_name].enabled = enabled
        self._save_config()
        logger.info(f"Tool '{tool_name}' {'enabled' if enabled else 'disabled'}")
        return True

    def is_enabled(self, tool_name: str) -> bool:
        """Check if a tool is enabled."""
        config = self._configs.get(tool_name)
        return config.enabled if config else False

    def get_enabled_tools(self) -> list[str]:
        """Get list of enabled tool names."""
        return [name for name, config in self._configs.items() if config.enabled]

    def get_disabled_tools(self) -> list[str]:
        """Get list of disabled tool names."""
        return [name for name, config in self._configs.items() if not config.enabled]

    def register_test_function(
        self, tool_name: str, test_fn: Callable[[], Coroutine[Any, Any, ToolTestResult]]
    ) -> None:
        """Register a test function for a tool."""
        self._test_functions[tool_name] = test_fn

    async def test_tool(self, tool_name: str) -> ToolTestResult:
        """Test a tool's connectivity/functionality."""
        config = self._configs.get(tool_name)

        if not config:
            return ToolTestResult(
                status=ToolTestStatus.FAILED,
                message=f"Tool '{tool_name}' not found",
            )

        if not config.testable:
            return ToolTestResult(
                status=ToolTestStatus.NOT_TESTABLE,
                message=f"Tool '{tool_name}' is not testable",
            )

        test_fn = self._test_functions.get(tool_name)

        if not test_fn:
            return ToolTestResult(
                status=ToolTestStatus.NOT_TESTABLE,
                message=f"No test function registered for '{tool_name}'",
            )

        try:
            start_time = asyncio.get_event_loop().time()
            result = await asyncio.wait_for(test_fn(), timeout=30.0)
            latency = (asyncio.get_event_loop().time() - start_time) * 1000
            result.latency_ms = latency

            # Store result
            config.last_test_result = result
            self._save_config()

            return result
        except asyncio.TimeoutError:
            result = ToolTestResult(
                status=ToolTestStatus.TIMEOUT,
                message="Tool test timed out after 30 seconds",
            )
            config.last_test_result = result
            self._save_config()
            return result
        except Exception as e:
            logger.error(f"Error testing tool '{tool_name}': {e}", exc_info=True)
            result = ToolTestResult(
                status=ToolTestStatus.FAILED,
                message=str(e),
            )
            config.last_test_result = result
            self._save_config()
            return result

    async def test_all_testable_tools(self) -> dict[str, ToolTestResult]:
        """Test all testable tools and return results."""
        results: dict[str, ToolTestResult] = {}

        testable_tools = [
            name
            for name, config in self._configs.items()
            if config.testable and name in self._test_functions
        ]

        # Run tests in parallel with a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(5)

        async def test_with_semaphore(name: str) -> tuple[str, ToolTestResult]:
            async with semaphore:
                result = await self.test_tool(name)
                return name, result

        tasks = [test_with_semaphore(name) for name in testable_tools]
        test_results = await asyncio.gather(*tasks, return_exceptions=True)

        for item in test_results:
            if isinstance(item, tuple):
                name, result = item
                results[name] = result
            elif isinstance(item, Exception):
                logger.error(f"Error in batch test: {item}")

        return results


# Create singleton instance
_tool_config_manager: ToolConfigManager | None = None


def get_tool_config_manager() -> ToolConfigManager:
    """Get the singleton ToolConfigManager instance."""
    global _tool_config_manager
    if _tool_config_manager is None:
        _tool_config_manager = ToolConfigManager()
    return _tool_config_manager
