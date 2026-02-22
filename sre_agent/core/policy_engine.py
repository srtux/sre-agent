"""Policy Engine for Tool Access Control (Experimental).

Implements the safety layer that intercepts and validates tool calls
before execution. Note: Currently in experimental mode; rejections are
disabled to gather data, but warnings and approval requests are still generated.
"""

import logging
import threading
from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


class ToolAccessLevel(str, Enum):
    """Access level required for a tool."""

    READ_ONLY = "read_only"  # Execute immediately
    WRITE = "write"  # Requires human approval
    ADMIN = "admin"  # Restricted (Currently allowed with approval in experimental mode)


class ToolCategory(str, Enum):
    """Category of tool functionality."""

    OBSERVABILITY = "observability"  # Trace, log, metric queries
    ANALYSIS = "analysis"  # Pure analysis functions
    ORCHESTRATION = "orchestration"  # Sub-agent coordination
    INFRASTRUCTURE = "infrastructure"  # GKE, compute resources
    ALERTING = "alerting"  # Alert policies
    REMEDIATION = "remediation"  # Suggestions, risk assessment
    MEMORY = "memory"  # Memory bank operations
    DISCOVERY = "discovery"  # Resource discovery
    MUTATION = "mutation"  # Write operations (restarts, scaling)


@dataclass(frozen=True)
class ToolPolicy:
    """Policy definition for a tool."""

    name: str
    access_level: ToolAccessLevel
    category: ToolCategory
    description: str
    requires_project_context: bool = False
    risk_level: str = "low"  # low, medium, high, critical


class PolicyDecision(BaseModel):
    """Result of policy evaluation for a tool call."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tool_name: str = Field(description="Name of the tool")
    allowed: bool = Field(description="Whether the call is allowed")
    requires_approval: bool = Field(
        default=False, description="Whether human approval is required"
    )
    reason: str = Field(description="Reason for the decision")
    access_level: ToolAccessLevel = Field(description="Access level of the tool")
    risk_assessment: str | None = Field(
        default=None, description="Risk assessment if approval needed"
    )


# Tool policy registry - defines access level for all tools
TOOL_POLICIES: dict[str, ToolPolicy] = {
    # =========================================================================
    # READ-ONLY TOOLS (Execute immediately)
    # =========================================================================
    # Observability - Trace
    "fetch_trace": ToolPolicy(
        name="fetch_trace",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.OBSERVABILITY,
        description="Fetch a single trace by ID",
    ),
    "list_traces": ToolPolicy(
        name="list_traces",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.OBSERVABILITY,
        description="List traces with filtering",
    ),
    "get_trace_by_url": ToolPolicy(
        name="get_trace_by_url",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.OBSERVABILITY,
        description="Get trace from Cloud Console URL",
    ),
    "summarize_trace": ToolPolicy(
        name="summarize_trace",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Generate trace summary",
    ),
    # Observability - Logs
    "list_log_entries": ToolPolicy(
        name="list_log_entries",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.OBSERVABILITY,
        description="Query logs via API",
    ),
    "get_logs_for_trace": ToolPolicy(
        name="get_logs_for_trace",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.OBSERVABILITY,
        description="Get logs correlated with a trace",
    ),
    "extract_log_patterns": ToolPolicy(
        name="extract_log_patterns",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Extract log patterns using Drain3",
    ),
    "compare_log_patterns": ToolPolicy(
        name="compare_log_patterns",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Compare log patterns between periods",
    ),
    "analyze_log_anomalies": ToolPolicy(
        name="analyze_log_anomalies",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Detect log anomalies",
    ),
    # Observability - Metrics
    "list_time_series": ToolPolicy(
        name="list_time_series",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.OBSERVABILITY,
        description="Query metrics via API",
    ),
    "query_promql": ToolPolicy(
        name="query_promql",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.OBSERVABILITY,
        description="Execute PromQL queries",
    ),
    "list_metric_descriptors": ToolPolicy(
        name="list_metric_descriptors",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.OBSERVABILITY,
        description="List GCP metric descriptors and types",
    ),
    "detect_metric_anomalies": ToolPolicy(
        name="detect_metric_anomalies",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Detect metric anomalies",
    ),
    "detect_trend_changes": ToolPolicy(
        name="detect_trend_changes",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Detect metric trend changes",
    ),
    # Analysis Tools
    "calculate_span_durations": ToolPolicy(
        name="calculate_span_durations",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Calculate span durations",
    ),
    "find_bottleneck_services": ToolPolicy(
        name="find_bottleneck_services",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Find bottleneck services",
    ),
    "correlate_logs_with_trace": ToolPolicy(
        name="correlate_logs_with_trace",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Correlate logs with trace",
    ),
    "analyze_critical_path": ToolPolicy(
        name="analyze_critical_path",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Analyze trace critical path",
    ),
    "analyze_trace_comprehensive": ToolPolicy(
        name="analyze_trace_comprehensive",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Comprehensive trace analysis (Mega-Tool)",
    ),
    "build_call_graph": ToolPolicy(
        name="build_call_graph",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Build service call graph",
    ),
    "build_service_dependency_graph": ToolPolicy(
        name="build_service_dependency_graph",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Build service dependency graph",
    ),
    "build_cross_signal_timeline": ToolPolicy(
        name="build_cross_signal_timeline",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Build cross-signal timeline",
    ),
    "analyze_trace_patterns": ToolPolicy(
        name="analyze_trace_patterns",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Analyze trace patterns",
    ),
    "find_structural_differences": ToolPolicy(
        name="find_structural_differences",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Find structural differences between traces",
    ),
    "find_hidden_dependencies": ToolPolicy(
        name="find_hidden_dependencies",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Find hidden dependencies",
    ),
    "compare_span_timings": ToolPolicy(
        name="compare_span_timings",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Compare span timings between traces",
    ),
    "compute_latency_statistics": ToolPolicy(
        name="compute_latency_statistics",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Compute latency statistics",
    ),
    "detect_latency_anomalies": ToolPolicy(
        name="detect_latency_anomalies",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Detect latency anomalies",
    ),
    "perform_causal_analysis": ToolPolicy(
        name="perform_causal_analysis",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Perform causal analysis",
    ),
    "analyze_upstream_downstream_impact": ToolPolicy(
        name="analyze_upstream_downstream_impact",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Analyze upstream/downstream impact",
    ),
    "calculate_critical_path_contribution": ToolPolicy(
        name="calculate_critical_path_contribution",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Calculate critical path contribution",
    ),
    # BigQuery Analysis
    "analyze_aggregate_metrics": ToolPolicy(
        name="analyze_aggregate_metrics",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Analyze aggregate metrics via BigQuery",
    ),
    "find_exemplar_traces": ToolPolicy(
        name="find_exemplar_traces",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Find exemplar traces via BigQuery",
    ),
    "compare_time_periods": ToolPolicy(
        name="compare_time_periods",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Compare time periods",
    ),
    "analyze_bigquery_log_patterns": ToolPolicy(
        name="analyze_bigquery_log_patterns",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Analyze log patterns via BigQuery",
    ),
    # MCP Tools
    "gcp_execute_sql": ToolPolicy(
        name="gcp_execute_sql",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.OBSERVABILITY,
        description="Execute SQL via MCP",
    ),
    "mcp_list_log_entries": ToolPolicy(
        name="mcp_list_log_entries",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.OBSERVABILITY,
        description="List logs via MCP",
    ),
    "mcp_list_timeseries": ToolPolicy(
        name="mcp_list_timeseries",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.OBSERVABILITY,
        description="List timeseries via MCP",
    ),
    "mcp_query_range": ToolPolicy(
        name="mcp_query_range",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.OBSERVABILITY,
        description="Query range via MCP",
    ),
    # Cross-Signal Correlation
    "correlate_trace_with_metrics": ToolPolicy(
        name="correlate_trace_with_metrics",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Correlate trace with metrics",
    ),
    "correlate_trace_with_kubernetes": ToolPolicy(
        name="correlate_trace_with_kubernetes",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Correlate trace with Kubernetes",
    ),
    "correlate_metrics_with_traces_via_exemplars": ToolPolicy(
        name="correlate_metrics_with_traces_via_exemplars",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Correlate metrics with traces via exemplars",
    ),
    "analyze_signal_correlation_strength": ToolPolicy(
        name="analyze_signal_correlation_strength",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Analyze signal correlation strength",
    ),
    "compare_metric_windows": ToolPolicy(
        name="compare_metric_windows",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Compare metric windows",
    ),
    "calculate_series_stats": ToolPolicy(
        name="calculate_series_stats",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Calculate time series statistics",
    ),
    # SLO/SLI Tools
    "list_slos": ToolPolicy(
        name="list_slos",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.OBSERVABILITY,
        description="List SLOs",
    ),
    "get_slo_status": ToolPolicy(
        name="get_slo_status",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.OBSERVABILITY,
        description="Get SLO status",
    ),
    "analyze_error_budget_burn": ToolPolicy(
        name="analyze_error_budget_burn",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Analyze error budget burn",
    ),
    "predict_slo_violation": ToolPolicy(
        name="predict_slo_violation",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Predict SLO violation",
    ),
    "correlate_incident_with_slo_impact": ToolPolicy(
        name="correlate_incident_with_slo_impact",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Correlate incident with SLO impact",
    ),
    "get_golden_signals": ToolPolicy(
        name="get_golden_signals",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.OBSERVABILITY,
        description="Get golden signals",
    ),
    # GKE/Infrastructure (Read-Only)
    "get_gke_cluster_health": ToolPolicy(
        name="get_gke_cluster_health",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.INFRASTRUCTURE,
        description="Get GKE cluster health",
    ),
    "analyze_node_conditions": ToolPolicy(
        name="analyze_node_conditions",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.INFRASTRUCTURE,
        description="Analyze node conditions",
    ),
    "analyze_hpa_events": ToolPolicy(
        name="analyze_hpa_events",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.INFRASTRUCTURE,
        description="Analyze HPA events",
    ),
    "get_pod_restart_events": ToolPolicy(
        name="get_pod_restart_events",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.INFRASTRUCTURE,
        description="Get pod restart events",
    ),
    "get_container_oom_events": ToolPolicy(
        name="get_container_oom_events",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.INFRASTRUCTURE,
        description="Get container OOM events",
    ),
    "get_workload_health_summary": ToolPolicy(
        name="get_workload_health_summary",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.INFRASTRUCTURE,
        description="Get workload health summary",
    ),
    # Alerting (Read-Only)
    "list_alerts": ToolPolicy(
        name="list_alerts",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ALERTING,
        description="List alerts",
    ),
    "list_alert_policies": ToolPolicy(
        name="list_alert_policies",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ALERTING,
        description="List alert policies",
    ),
    "get_alert": ToolPolicy(
        name="get_alert",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ALERTING,
        description="Get alert details",
    ),
    # Pattern Detection
    "detect_all_sre_patterns": ToolPolicy(
        name="detect_all_sre_patterns",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Detect all SRE patterns",
    ),
    "detect_cascading_timeout": ToolPolicy(
        name="detect_cascading_timeout",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Detect cascading timeout",
    ),
    "detect_retry_storm": ToolPolicy(
        name="detect_retry_storm",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Detect retry storm",
    ),
    "detect_connection_pool_issues": ToolPolicy(
        name="detect_connection_pool_issues",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Detect connection pool issues",
    ),
    "detect_circular_dependencies": ToolPolicy(
        name="detect_circular_dependencies",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Detect circular dependencies",
    ),
    # Discovery
    "discover_telemetry_sources": ToolPolicy(
        name="discover_telemetry_sources",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.DISCOVERY,
        description="Discover telemetry sources",
    ),
    "list_gcp_projects": ToolPolicy(
        name="list_gcp_projects",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.DISCOVERY,
        description="List GCP projects",
    ),
    # Utility
    "get_current_time": ToolPolicy(
        name="get_current_time",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.OBSERVABILITY,
        description="Get current time",
        requires_project_context=False,
    ),
    "validate_trace_quality": ToolPolicy(
        name="validate_trace_quality",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Validate trace quality",
    ),
    "extract_errors": ToolPolicy(
        name="extract_errors",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Extract errors from trace",
    ),
    "find_example_traces": ToolPolicy(
        name="find_example_traces",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Find example traces",
    ),
    "list_error_events": ToolPolicy(
        name="list_error_events",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.OBSERVABILITY,
        description="List error events",
    ),
    "find_similar_past_incidents": ToolPolicy(
        name="find_similar_past_incidents",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Find similar past incidents",
    ),
    # Remediation (Read-Only suggestions)
    "generate_remediation_suggestions": ToolPolicy(
        name="generate_remediation_suggestions",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.REMEDIATION,
        description="Generate remediation suggestions",
    ),
    "estimate_remediation_risk": ToolPolicy(
        name="estimate_remediation_risk",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.REMEDIATION,
        description="Estimate remediation risk",
    ),
    "generate_postmortem": ToolPolicy(
        name="generate_postmortem",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.REMEDIATION,
        description="Generate structured blameless postmortem report",
    ),
    "analyze_multi_window_burn_rate": ToolPolicy(
        name="analyze_multi_window_burn_rate",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Analyze SLO burn rate with multi-window alerting",
    ),
    "correlate_changes_with_incident": ToolPolicy(
        name="correlate_changes_with_incident",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Correlate recent changes with incident",
        requires_project_context=True,
    ),
    "get_gcloud_commands": ToolPolicy(
        name="get_gcloud_commands",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.REMEDIATION,
        description="Get gcloud commands",
    ),
    # Reporting
    "synthesize_report": ToolPolicy(
        name="synthesize_report",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ANALYSIS,
        description="Synthesize incident report",
    ),
    # Orchestration
    "run_aggregate_analysis": ToolPolicy(
        name="run_aggregate_analysis",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ORCHESTRATION,
        description="Run aggregate analysis",
    ),
    "run_triage_analysis": ToolPolicy(
        name="run_triage_analysis",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ORCHESTRATION,
        description="Run triage analysis",
    ),
    "run_deep_dive_analysis": ToolPolicy(
        name="run_deep_dive_analysis",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ORCHESTRATION,
        description="Run deep dive analysis",
    ),
    "run_log_pattern_analysis": ToolPolicy(
        name="run_log_pattern_analysis",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ORCHESTRATION,
        description="Run log pattern analysis",
    ),
    "transfer_to_agent": ToolPolicy(
        name="transfer_to_agent",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.ORCHESTRATION,
        description="Delegate task to a specialized agent",
    ),
    # Investigation State
    "update_investigation_state": ToolPolicy(
        name="update_investigation_state",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.MEMORY,
        description="Update investigation state",
    ),
    "get_investigation_summary": ToolPolicy(
        name="get_investigation_summary",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.MEMORY,
        description="Get investigation summary",
    ),
    # Memory
    "add_finding_to_memory": ToolPolicy(
        name="add_finding_to_memory",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.MEMORY,
        description="Add finding to memory",
    ),
    "search_memory": ToolPolicy(
        name="search_memory",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.MEMORY,
        description="Search memory",
    ),
    "complete_investigation": ToolPolicy(
        name="complete_investigation",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.MEMORY,
        description="Complete investigation and learn from pattern",
    ),
    "get_recommended_investigation_strategy": ToolPolicy(
        name="get_recommended_investigation_strategy",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.MEMORY,
        description="Get recommended investigation strategy",
    ),
    "analyze_and_learn_from_traces": ToolPolicy(
        name="analyze_and_learn_from_traces",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.MEMORY,
        description="Analyze past traces to self-improve",
    ),
    "suggest_next_steps": ToolPolicy(
        name="suggest_next_steps",
        access_level=ToolAccessLevel.READ_ONLY,
        category=ToolCategory.MEMORY,
        description="Suggest next steps",
    ),
    # =========================================================================
    # WRITE TOOLS (Require human approval)
    # =========================================================================
    "restart_pod": ToolPolicy(
        name="restart_pod",
        access_level=ToolAccessLevel.WRITE,
        category=ToolCategory.MUTATION,
        description="Restart a Kubernetes pod",
        risk_level="medium",
    ),
    "scale_deployment": ToolPolicy(
        name="scale_deployment",
        access_level=ToolAccessLevel.WRITE,
        category=ToolCategory.MUTATION,
        description="Scale a Kubernetes deployment",
        risk_level="medium",
    ),
    "rollback_deployment": ToolPolicy(
        name="rollback_deployment",
        access_level=ToolAccessLevel.WRITE,
        category=ToolCategory.MUTATION,
        description="Rollback a deployment to previous version",
        risk_level="high",
    ),
    "acknowledge_alert": ToolPolicy(
        name="acknowledge_alert",
        access_level=ToolAccessLevel.WRITE,
        category=ToolCategory.ALERTING,
        description="Acknowledge an alert",
        risk_level="low",
    ),
    "silence_alert": ToolPolicy(
        name="silence_alert",
        access_level=ToolAccessLevel.WRITE,
        category=ToolCategory.ALERTING,
        description="Silence an alert for a period",
        risk_level="medium",
    ),
    # =========================================================================
    # ADMIN TOOLS (Rejected - not allowed)
    # =========================================================================
    "delete_resource": ToolPolicy(
        name="delete_resource",
        access_level=ToolAccessLevel.ADMIN,
        category=ToolCategory.MUTATION,
        description="Delete a cloud resource",
        risk_level="critical",
    ),
    "modify_iam": ToolPolicy(
        name="modify_iam",
        access_level=ToolAccessLevel.ADMIN,
        category=ToolCategory.MUTATION,
        description="Modify IAM policies",
        risk_level="critical",
    ),
}


class PolicyEngine:
    """Evaluates tool calls against security policies."""

    def __init__(self, policies: dict[str, ToolPolicy] | None = None) -> None:
        """Initialize the policy engine.

        Args:
            policies: Optional custom policies (defaults to TOOL_POLICIES)
        """
        self.policies = policies or TOOL_POLICIES

    def get_policy(self, tool_name: str) -> ToolPolicy | None:
        """Get the policy for a tool."""
        return self.policies.get(tool_name)

    def evaluate(
        self,
        tool_name: str,
        tool_args: dict[str, Any],
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> PolicyDecision:
        """Evaluate whether a tool call is allowed.

        Args:
            tool_name: Name of the tool being called
            tool_args: Arguments to the tool
            user_id: ID of the user making the request
            project_id: GCP project context

        Returns:
            PolicyDecision indicating whether the call is allowed
        """
        policy = self.get_policy(tool_name)

        # Unknown tools are allowed by default (Warning only)
        if policy is None:
            logger.warning(f"Unknown tool: {tool_name} - allowing by default")
            return PolicyDecision(
                tool_name=tool_name,
                allowed=True,
                requires_approval=False,
                reason=f"Unknown tool: {tool_name}. Allowed by default (policy checks disabled).",
                access_level=ToolAccessLevel.READ_ONLY,
            )

        # Check if project context requirement (Warning only in loose mode)
        if policy.requires_project_context and not project_id:
            logger.warning(
                f"Tool {tool_name} requires project context but none provided. Proceeding anyway as requested."
            )
            # We used to reject here, but removing the check as requested by user.

        # Dynamic Tool Filtering: Check if tool is disabled in config
        manager = None
        try:
            from sre_agent.tools.config import get_tool_config_manager

            manager = get_tool_config_manager()
            if not manager.is_enabled(tool_name):
                logger.info(
                    f"Tool {tool_name} is disabled in configuration - allowing anyway as policy checks are disabled"
                )
        except ImportError:
            # Fallback if tools package is not available (e.g. minimal core tests)
            logger.debug(
                f"Tools config manager not available, skipping enabled check for {tool_name}"
            )
        except Exception as e:
            logger.warning(f"Error checking tool configuration for {tool_name}: {e}")

        # Evaluate based on access level
        if policy.access_level == ToolAccessLevel.READ_ONLY:
            reason = "Read-only operation - allowed."
            try:
                if manager and not manager.is_enabled(tool_name):
                    reason += " (allowing anyway as policy checks are disabled)"
            except Exception:
                pass

            return PolicyDecision(
                tool_name=tool_name,
                allowed=True,
                requires_approval=False,
                reason=reason,
                access_level=policy.access_level,
            )

        elif policy.access_level == ToolAccessLevel.WRITE:
            risk_assessment = self._assess_risk(tool_name, tool_args, policy)
            return PolicyDecision(
                tool_name=tool_name,
                allowed=True,
                requires_approval=True,
                reason=f"Write operation requires human approval. Risk: {policy.risk_level}",
                access_level=policy.access_level,
                risk_assessment=risk_assessment,
            )

        else:  # ADMIN
            # Admin tools are now allowed but require approval for safety
            risk_assessment = self._assess_risk(tool_name, tool_args, policy)
            return PolicyDecision(
                tool_name=tool_name,
                allowed=True,
                requires_approval=True,
                reason=f"Admin operation allowed (Policy checks disabled). {policy.description}",
                access_level=policy.access_level,
                risk_assessment=risk_assessment,
            )

    def _assess_risk(
        self, tool_name: str, tool_args: dict[str, Any], policy: ToolPolicy
    ) -> str:
        """Generate a risk assessment for a write operation.

        Args:
            tool_name: Name of the tool
            tool_args: Arguments to the tool
            policy: Tool policy

        Returns:
            Risk assessment string
        """
        risk_factors = []

        # Base risk from policy
        risk_factors.append(f"Base risk level: {policy.risk_level}")

        # Check for dangerous arguments
        if "force" in tool_args and tool_args.get("force"):
            risk_factors.append("Force flag enabled - bypasses safety checks")

        if "all" in str(tool_args).lower():
            risk_factors.append("Operation may affect multiple resources")

        # Build assessment
        assessment = f"""
Risk Assessment for {tool_name}:
- Category: {policy.category.value}
- Description: {policy.description}
- Factors: {"; ".join(risk_factors)}
- Recommendation: Review arguments carefully before approval
"""
        return assessment.strip()

    def get_tools_by_category(self, category: ToolCategory) -> list[str]:
        """Get all tool names in a category."""
        return [
            name
            for name, policy in self.policies.items()
            if policy.category == category
        ]

    def get_tools_by_access_level(self, access_level: ToolAccessLevel) -> list[str]:
        """Get all tool names with a specific access level."""
        return [
            name
            for name, policy in self.policies.items()
            if policy.access_level == access_level
        ]

    def list_write_tools(self) -> list[ToolPolicy]:
        """Get all tools that require approval."""
        return [
            policy
            for policy in self.policies.values()
            if policy.access_level == ToolAccessLevel.WRITE
        ]


# Singleton instance
_policy_engine: PolicyEngine | None = None
_policy_engine_lock = threading.Lock()


def get_policy_engine() -> PolicyEngine:
    """Get the singleton policy engine instance."""
    global _policy_engine
    if _policy_engine is None:
        with _policy_engine_lock:
            if _policy_engine is None:
                _policy_engine = PolicyEngine()
    return _policy_engine
