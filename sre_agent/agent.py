"""SRE Agent - Google Cloud Observability Analysis Agent.

This is the main orchestration agent for SRE tasks, designed to analyze telemetry data
from Google Cloud Observability (Traces, Logs, Metrics) to identify root causes of
production issues.

## Architecture: "Core Squad"

The agent uses a "Core Squad" orchestration pattern (simplified from the previous
"Council of Experts") where a central **SRE Agent** delegates to high-level analysts.

### The 3-Stage Analysis Pipeline

1.  **Stage 0: Aggregate Analysis (Data Analyst)**
    -   **Sub-Agent**: `aggregate_analyzer`
    -   **Goal**: Analyze traces at scale in BigQuery.

2.  **Stage 1: Triage (Trace Analyst)**
    -   **Sub-Agent**: `trace_analyst`
    -   **Goal**: Analyze individual traces for latency, errors, structure, and resiliency patterns.
    -   **Efficiency**: Uses `analyze_trace_comprehensive` "Mega-Tool" to reduce tool calls.

3.  **Stage 2: Deep Dive (Root Cause Analyst)**
    -   **Sub-Agent**: `root_cause_analyst`
    -   **Goal**: Synthesize findings to determine causality, impact, and trigger (deployment/config).

## Capabilities

-   **Trace Analysis**: Comprehensive timing, error, structure, and critical path analysis.
-   **Log Analysis**: Pattern extraction (Drain3) and correlation.
-   **Metrics Analysis**: PromQL querying and cross-signal correlation.
-   **SLO/SLI Support**: Error budget tracking and prediction.
-   **Kubernetes/GKE**: Cluster health and workload debugging.
"""

# ruff: noqa: E402
# Enable JSON Schema for function declarations to fix Vertex AI API compatibility
# This ensures tool schemas use camelCase (additionalProperties) instead of snake_case
# Must be done BEFORE importing any ADK tools to ensure tools are registered correctly
from google.adk.features import FeatureName, override_feature_enabled

override_feature_enabled(FeatureName.JSON_SCHEMA_FOR_FUNC_DECL, True)

import asyncio
import functools
import logging
import os
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Any

# Determine environment settings for Agent initialization
import google.auth
import vertexai
from google.adk.agents import LlmAgent
from google.adk.tools import AgentTool  # type: ignore[attr-defined]
from google.adk.tools.base_toolset import BaseToolset

from .prompt import SRE_AGENT_PROMPT

# Import sub-agents
from .sub_agents import (
    # Trace analysis sub-agents
    aggregate_analyzer,
    # Alert analysis sub-agents
    alert_analyst,
    # Log analysis sub-agents
    log_analyst,
    # Metrics analysis sub-agents
    metrics_analyzer,
    root_cause_analyst,
    trace_analyst,
)
from .tools import (
    # BigQuery tools
    analyze_aggregate_metrics,
    # Additional BQ tools
    analyze_bigquery_log_patterns,
    # Critical path analysis tools
    analyze_critical_path,
    # SLO/SLI tools
    analyze_error_budget_burn,
    # GKE tools
    analyze_hpa_events,
    analyze_log_anomalies,
    analyze_node_conditions,
    analyze_signal_correlation_strength,
    analyze_trace_comprehensive,
    analyze_trace_patterns,
    analyze_upstream_downstream_impact,
    build_call_graph,
    build_cross_signal_timeline,
    # Service dependency tools
    build_service_dependency_graph,
    calculate_critical_path_contribution,
    calculate_series_stats,
    calculate_span_durations,
    compare_log_patterns,
    compare_metric_windows,
    compare_span_timings,
    compare_time_periods,
    compute_latency_statistics,
    # SLO correlation
    correlate_incident_with_slo_impact,
    correlate_logs_with_trace,
    correlate_metrics_with_traces_via_exemplars,
    # Cross-signal correlation tools
    correlate_trace_with_kubernetes,
    correlate_trace_with_metrics,
    detect_all_sre_patterns,
    detect_cascading_timeout,
    detect_circular_dependencies,
    detect_connection_pool_issues,
    detect_latency_anomalies,
    # Metrics analysis tools
    detect_metric_anomalies,
    detect_retry_storm,
    detect_trend_changes,
    # Discovery tools
    discover_telemetry_sources,
    # Remediation tools
    estimate_remediation_risk,
    extract_errors,
    # Log pattern analysis tools
    extract_log_patterns,
    # Trace tools
    fetch_trace,
    find_bottleneck_services,
    find_example_traces,
    find_exemplar_traces,
    find_hidden_dependencies,
    find_similar_past_incidents,
    find_structural_differences,
    # Remediation
    generate_remediation_suggestions,
    get_alert,
    # GKE tools
    get_container_oom_events,
    get_current_time,
    get_gcloud_commands,
    get_gke_cluster_health,
    # SLO Golden Signals
    get_golden_signals,
    get_investigation_summary,
    get_logs_for_trace,
    get_pod_restart_events,
    get_slo_status,
    get_trace_by_url,
    get_workload_health_summary,
    list_alert_policies,
    # Alerting tools
    list_alerts,
    list_error_events,
    # GCP direct API tools
    list_gcp_projects,
    list_log_entries,
    # SLO listing
    list_slos,
    list_time_series,
    list_traces,
    perform_causal_analysis,
    # SLO prediction
    predict_slo_violation,
    query_promql,
    summarize_trace,
    update_investigation_state,
    validate_trace_quality,
)
from .tools.common import adk_tool
from .tools.config import get_tool_config_manager
from .tools.mcp.gcp import (
    create_bigquery_mcp_toolset,
    create_logging_mcp_toolset,
    create_monitoring_mcp_toolset,
    get_project_id_with_fallback,
    mcp_execute_sql,
    mcp_list_log_entries,
    mcp_list_timeseries,
    mcp_query_range,
)
from .tools.reporting import synthesize_report

# Initialize logger for this module
logger = logging.getLogger(__name__)

# Determine environment settings for Agent initialization
project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT_ID")

# Fallback: Try to get project from Application Default Credentials
if not project_id:
    try:
        _, project_id = google.auth.default()
        if project_id:
            print(f"🚀 Discovered project ID from credentials: {project_id}")
    except Exception as e:
        print(f"⚠️ Could not discover project ID from credentials: {e}")

location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "true").lower() == "true"

# Ensure Environment is configured for SDKs
if project_id:
    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
    os.environ["GCP_PROJECT_ID"] = project_id

if use_vertex and project_id:
    try:
        vertexai.init(project=project_id, location=location)
        print(f"✅ Initialized Vertex AI: {project_id} @ {location}")
    except Exception as e:
        print(f"⚠️ Failed to initialize Vertex AI: {e}")


def emojify_agent(agent: LlmAgent) -> LlmAgent:
    """Wraps an LlmAgent to add emojis to prompts and responses in logs."""
    original_run_async = agent.run_async

    @functools.wraps(original_run_async)
    async def wrapped_run_async(context: Any) -> AsyncGenerator[Any, None]:
        # 1. Log Prompt
        user_msg = "Unknown"
        try:
            if hasattr(context, "user_content") and context.user_content:
                parts = getattr(context.user_content, "parts", [])
                if parts:
                    # Try to get text from the first part
                    p = parts[0]
                    if hasattr(p, "text"):
                        user_msg = p.text
                    elif isinstance(p, dict) and "text" in p:
                        user_msg = p["text"]
                    else:
                        user_msg = str(p)
            elif hasattr(context, "message") and context.message:
                user_msg = str(context.message)
        except Exception as e:
            logger.warning(f"Failed to extract user message for logging: {e}")

        # Determine project and session
        project_id = os.environ.get(
            "GOOGLE_CLOUD_PROJECT", os.environ.get("GCP_PROJECT_ID", "unknown")
        )
        session_id = (
            getattr(context.session, "id", "unknown")
            if hasattr(context, "session")
            else "unknown"
        )

        user_id = (
            getattr(context, "user_id", "unknown")
            if hasattr(context, "user_id")
            else "unknown"
        )
        logger.info(f"💬 User Prompt: '{user_msg}'")
        logger.info(
            f"📍 Context: Project={project_id}, Session={session_id}, User={user_id}"
        )

        from .tools.common import using_arize_session

        # 2. Run Original with Arize session context
        full_response_parts = []
        try:
            with using_arize_session(session_id=session_id, user_id=user_id):
                async for event in original_run_async(context):
                    if (
                        hasattr(event, "content")
                        and event.content
                        and event.content.parts
                    ):
                        for part in event.content.parts:
                            if hasattr(part, "text") and part.text:
                                full_response_parts.append(part.text)
                    yield event
        except Exception as e:
            logging.error(f"🔥 Agent Execution Failed: {e}", exc_info=True)
            raise e

        # 3. Log Response
        final_response = "".join(full_response_parts)
        if final_response:
            preview = (
                final_response[:500] + "..."
                if len(final_response) > 500
                else final_response
            )
            logging.info(f"🏁 Final Response to User: '{preview}'")

    object.__setattr__(agent, "run_async", wrapped_run_async)
    return agent


# ============================================================================
# MCP Toolset Management
# ============================================================================

# Lazy-loaded MCP toolsets (created on first use in async context)
_bigquery_mcp_toolset: BaseToolset | None = None
_logging_mcp_toolset: BaseToolset | None = None
_monitoring_mcp_toolset: BaseToolset | None = None


async def _get_bigquery_mcp_toolset() -> BaseToolset | None:
    """Lazily create BigQuery MCP toolset in async context."""
    global _bigquery_mcp_toolset
    if _bigquery_mcp_toolset is None:
        _bigquery_mcp_toolset = create_bigquery_mcp_toolset()
    return _bigquery_mcp_toolset


async def _get_logging_mcp_toolset() -> BaseToolset | None:
    """Lazily create Cloud Logging MCP toolset in async context."""
    global _logging_mcp_toolset
    if _logging_mcp_toolset is None:
        _logging_mcp_toolset = create_logging_mcp_toolset()
    return _logging_mcp_toolset


async def _get_monitoring_mcp_toolset() -> BaseToolset | None:
    """Lazily create Cloud Monitoring MCP toolset in async context."""
    global _monitoring_mcp_toolset
    if _monitoring_mcp_toolset is None:
        _monitoring_mcp_toolset = create_monitoring_mcp_toolset()
    return _monitoring_mcp_toolset


# ============================================================================
# Orchestration Functions
# ============================================================================


@adk_tool
async def run_aggregate_analysis(
    dataset_id: str | None = None,
    table_name: str | None = None,
    time_window_hours: int = 24,
    service_name: str | None = None,
    tool_context: Any | None = None,
) -> dict[str, Any]:
    """Run Stage 0: Aggregate analysis using BigQuery."""
    logger.info(
        f"🎺 Running aggregate analysis (Dataset: {dataset_id}, Table: {table_name})"
    )

    if tool_context is None:
        raise ValueError("tool_context is required")

    try:
        # 1. Auto-Discovery if needed
        if not dataset_id or not table_name:
            logger.info("Dataset or table not provided. Running discovery...")
            discovery_result = await discover_telemetry_sources(
                tool_context=tool_context
            )

            trace_table_full = discovery_result.get("trace_table")
            if not trace_table_full:
                return {
                    "stage": "aggregate",
                    "status": "success",
                    "result": "Telemetry discovery completed but found no trace tables. Please ask the user to provide the 'dataset_id' manually.",
                }

            logger.info(f"Discovered trace table: {trace_table_full}")

            parts = trace_table_full.split(".")
            if len(parts) >= 3:
                dataset_id = f"{parts[0]}.{parts[1]}"
                table_name = parts[2]
            elif len(parts) == 2:
                dataset_id = parts[0]
                table_name = parts[1]
            else:
                dataset_id = trace_table_full
                table_name = "_AllSpans"

        result = await AgentTool(aggregate_analyzer).run_async(
            args={
                "request": f"""
Analyze trace data in BigQuery:
- Dataset: {dataset_id}
- Table: {table_name}
- Time window: {time_window_hours} hours
{f"- Service filter: {service_name}" if service_name else ""}

Please:
1. Get aggregate metrics for all services
2. Identify services with high error rates or latency
3. Find exemplar traces for comparison (baseline and outlier)
4. Report your findings
""",
            },
            tool_context=tool_context,
        )

        return {
            "stage": "aggregate",
            "status": "success",
            "result": result,
        }

    except Exception as e:
        logger.error(f"Aggregate analysis failed: {e}", exc_info=True)
        return {
            "stage": "aggregate",
            "status": "error",
            "error": str(e),
        }


@adk_tool
async def run_triage_analysis(
    baseline_trace_id: str,
    target_trace_id: str,
    project_id: str | None = None,
    tool_context: Any | None = None,
) -> dict[str, Any]:
    """Run Stage 1: Triage analysis with the Trace Analyst.

    This stage runs the Trace Analyst to check latency, errors, structure, and resiliency.
    It can also optionally run Log and Metrics analysis if useful.

    Args:
        baseline_trace_id: ID of a "good" trace (reference baseline).
        target_trace_id: ID of the "bad" trace (anomaly to investigate).
        project_id: GCP project ID.
        tool_context: ADK tool context (required).
    """
    if tool_context is None:
        raise ValueError("tool_context is required")

    if not project_id:
        project_id = get_project_id_with_fallback()

    logger.info(f"Running triage analysis: {baseline_trace_id} vs {target_trace_id}")

    prompt = f"""
Analyze the differences between these two traces:
- Baseline (good): {baseline_trace_id}
- Target (investigate): {target_trace_id}
- Project: {project_id}

Compare them and report your findings on Latency, Errors, and Structure.
"""

    # Run Trace Analyst and Log Analyst in parallel
    results = await asyncio.gather(
        AgentTool(trace_analyst).run_async(
            args={"request": prompt}, tool_context=tool_context
        ),
        AgentTool(log_analyst).run_async(
            args={"request": prompt}, tool_context=tool_context
        ),
        return_exceptions=True,
    )

    agent_names = ["trace", "log_analyst"]
    triage_results: dict[str, dict[str, Any]] = {}

    for name, result in zip(agent_names, results, strict=False):
        if isinstance(result, Exception):
            logger.error(f"{name}_analyzer failed: {result}")
            triage_results[name] = {"status": "error", "error": str(result)}
        else:
            triage_results[name] = {"status": "success", "result": result}

    return {
        "stage": "triage",
        "baseline_trace_id": baseline_trace_id,
        "target_trace_id": target_trace_id,
        "results": triage_results,
    }


@adk_tool
async def run_deep_dive_analysis(
    baseline_trace_id: str,
    target_trace_id: str,
    triage_findings: dict[str, Any],
    project_id: str | None = None,
    tool_context: Any | None = None,
) -> dict[str, Any]:
    """Run Stage 2: Deep Dive analysis with Root Cause Analyst.

    Synthesizes findings to determine causality, impact, and root cause (changes).

    Args:
        baseline_trace_id: Good trace ID.
        target_trace_id: Bad trace ID.
        triage_findings: Findings from Stage 1 (Triage).
        project_id: GCP project ID.
        tool_context: ADK tool context.
    """
    if tool_context is None:
        raise ValueError("tool_context is required")

    if not project_id:
        project_id = get_project_id_with_fallback()

    logger.info(f"Running deep dive analysis for {target_trace_id}")

    prompt = f"""
Deep dive into the issue with target trace {target_trace_id}.
Baseline trace: {baseline_trace_id}
Triage findings: {triage_findings}
Project: {project_id}

Determine the root cause (causality), check for recent changes (deployments), and assess impact.
"""

    try:
        result = await AgentTool(root_cause_analyst).run_async(
            args={"request": prompt}, tool_context=tool_context
        )
        return {
            "stage": "deep_dive",
            "status": "success",
            "result": result,
        }
    except Exception as e:
        logger.error(f"Deep dive analysis failed: {e}", exc_info=True)
        return {
            "stage": "deep_dive",
            "status": "error",
            "error": str(e),
        }


@adk_tool
async def run_log_pattern_analysis(
    log_filter: str,
    baseline_start: str,
    baseline_end: str,
    comparison_start: str,
    comparison_end: str,
    project_id: str | None = None,
    tool_context: Any | None = None,
) -> dict[str, Any]:
    """Run log pattern analysis to find emergent issues."""
    if not project_id:
        project_id = get_project_id_with_fallback()

    logger.info(f"Running log pattern analysis for filter: {log_filter}")

    if tool_context is None:
        raise ValueError("tool_context is required")

    try:
        result = await AgentTool(log_analyst).run_async(
            args={
                "request": f"""
Analyze log patterns and find anomalies:

Filter: {log_filter}
Project: {project_id}

Baseline Period (before):
- Start: {baseline_start}
- End: {baseline_end}

Comparison Period (during/after):
- Start: {comparison_start}
- End: {comparison_end}

Please:
1. Fetch logs from both periods using the filter
2. Extract patterns from each period using extract_log_patterns
3. Compare the patterns to find NEW or INCREASED patterns
4. Focus on ERROR patterns as they are most likely to indicate issues
5. Report your findings with recommendations
""",
            },
            tool_context=tool_context,
        )

        return {
            "stage": "log_pattern",
            "status": "success",
            "result": result,
        }

    except Exception as e:
        logger.error(f"Log pattern analysis failed: {e}", exc_info=True)
        return {
            "stage": "log_pattern",
            "status": "error",
            "error": str(e),
        }


# ============================================================================
# Tool Registry for Configuration
# ============================================================================

TOOL_NAME_MAP = {
    # Observability
    "fetch_trace": fetch_trace,
    "list_log_entries": list_log_entries,
    "query_promql": query_promql,
    "list_slos": list_slos,
    "list_traces": list_traces,
    "get_logs_for_trace": get_logs_for_trace,
    "get_trace_by_url": get_trace_by_url,
    "summarize_trace": summarize_trace,
    "get_golden_signals": get_golden_signals,
    "list_gcp_projects": list_gcp_projects,
    # Analysis
    "calculate_span_durations": calculate_span_durations,
    "find_bottleneck_services": find_bottleneck_services,
    "correlate_logs_with_trace": correlate_logs_with_trace,
    "analyze_critical_path": analyze_critical_path,
    "build_call_graph": build_call_graph,
    "build_service_dependency_graph": build_service_dependency_graph,
    "build_cross_signal_timeline": build_cross_signal_timeline,
    "analyze_trace_patterns": analyze_trace_patterns,
    "find_structural_differences": find_structural_differences,
    "find_hidden_dependencies": find_hidden_dependencies,
    # Metrics
    "detect_metric_anomalies": detect_metric_anomalies,
    "list_time_series": list_time_series,
    "compare_metric_windows": compare_metric_windows,
    "analyze_signal_correlation_strength": analyze_signal_correlation_strength,
    "analyze_error_budget_burn": analyze_error_budget_burn,
    "predict_slo_violation": predict_slo_violation,
    # GKE / Infrastructure
    "get_gke_cluster_health": get_gke_cluster_health,
    "analyze_node_conditions": analyze_node_conditions,
    "analyze_hpa_events": analyze_hpa_events,
    "get_pod_restart_events": get_pod_restart_events,
    "get_container_oom_events": get_container_oom_events,
    "get_workload_health_summary": get_workload_health_summary,
    # Alerts
    "list_alerts": list_alerts,
    "list_alert_policies": list_alert_policies,
    "get_alert": get_alert,
    # Advanced Diagnostics
    "perform_causal_analysis": perform_causal_analysis,
    "analyze_upstream_downstream_impact": analyze_upstream_downstream_impact,
    "correlate_trace_with_kubernetes": correlate_trace_with_kubernetes,
    "correlate_trace_with_metrics": correlate_trace_with_metrics,
    "calculate_series_stats": calculate_series_stats,
    "detect_trend_changes": detect_trend_changes,
    # Pattern Analysis
    "extract_log_patterns": extract_log_patterns,
    "compare_log_patterns": compare_log_patterns,
    "detect_all_sre_patterns": detect_all_sre_patterns,
    "analyze_log_anomalies": analyze_log_anomalies,
    "analyze_bigquery_log_patterns": analyze_bigquery_log_patterns,
    # Root Cause
    "detect_cascading_timeout": detect_cascading_timeout,
    "detect_retry_storm": detect_retry_storm,
    "detect_connection_pool_issues": detect_connection_pool_issues,
    "detect_circular_dependencies": detect_circular_dependencies,
    "find_similar_past_incidents": find_similar_past_incidents,
    # Remediation
    "generate_remediation_suggestions": generate_remediation_suggestions,
    "estimate_remediation_risk": estimate_remediation_risk,
    "get_gcloud_commands": get_gcloud_commands,
    # Specialized Analysis
    "analyze_aggregate_metrics": analyze_aggregate_metrics,
    "calculate_critical_path_contribution": calculate_critical_path_contribution,
    "compare_span_timings": compare_span_timings,
    "compare_time_periods": compare_time_periods,
    "compute_latency_statistics": compute_latency_statistics,
    "correlate_incident_with_slo_impact": correlate_incident_with_slo_impact,
    "correlate_metrics_with_traces_via_exemplars": correlate_metrics_with_traces_via_exemplars,
    "detect_latency_anomalies": detect_latency_anomalies,
    "extract_errors": extract_errors,
    "find_example_traces": find_example_traces,
    "find_exemplar_traces": find_exemplar_traces,
    "get_current_time": get_current_time,
    "get_slo_status": get_slo_status,
    "list_error_events": list_error_events,
    "validate_trace_quality": validate_trace_quality,
    "analyze_trace_comprehensive": analyze_trace_comprehensive,
    # MCP Tools
    "mcp_execute_sql": mcp_execute_sql,
    "mcp_list_log_entries": mcp_list_log_entries,
    "mcp_list_timeseries": mcp_list_timeseries,
    "mcp_query_range": mcp_query_range,
    # Discovery
    "discover_telemetry_sources": discover_telemetry_sources,
    # Reporting
    "synthesize_report": synthesize_report,
    # Orchestration
    "run_aggregate_analysis": run_aggregate_analysis,
    "run_triage_analysis": run_triage_analysis,
    "run_deep_dive_analysis": run_deep_dive_analysis,
    "run_log_pattern_analysis": run_log_pattern_analysis,
    # Investigation
    "update_investigation_state": update_investigation_state,
    "get_investigation_summary": get_investigation_summary,
}

# Common tools for all agents
base_tools: list[Any] = [
    # Observability
    fetch_trace,
    list_traces,
    list_log_entries,
    get_logs_for_trace,
    get_current_time,
    query_promql,
    list_slos,
    get_golden_signals,
    # Analysis
    calculate_span_durations,
    find_bottleneck_services,
    correlate_logs_with_trace,
    analyze_critical_path,
    analyze_signal_correlation_strength,
    analyze_trace_comprehensive,
    summarize_trace,
    # GKE / Infrastructure
    get_gke_cluster_health,
    # Alerts
    list_alerts,
    get_alert,
    # Metrics
    detect_metric_anomalies,
    detect_trend_changes,
    list_time_series,
    # Log pattern tools
    extract_log_patterns,
    compare_log_patterns,
    analyze_log_anomalies,
    # Discovery
    discover_telemetry_sources,
    # MCP Tools
    mcp_execute_sql,
    mcp_list_log_entries,
    mcp_list_timeseries,
    mcp_query_range,
    # BigQuery Analysis Tools
    analyze_aggregate_metrics,
    find_exemplar_traces,
    analyze_bigquery_log_patterns,
    # Orchestration tools
    run_aggregate_analysis,
    run_triage_analysis,
    run_deep_dive_analysis,
    run_log_pattern_analysis,
    synthesize_report,
    list_gcp_projects,
    # Investigation tools
    update_investigation_state,
    get_investigation_summary,
]


def get_enabled_tools() -> list[Any]:
    """Get list of enabled tools based on configuration.

    Returns:
        List of tool functions that are currently enabled.
    """
    manager = get_tool_config_manager()
    enabled_tool_names = set(manager.get_enabled_tools())

    enabled_tools = []
    for tool_name in TOOL_NAME_MAP:
        if tool_name in enabled_tool_names:
            enabled_tools.append(TOOL_NAME_MAP[tool_name])

    logger.info(
        f"Loaded {len(enabled_tools)} enabled tools out of {len(TOOL_NAME_MAP)} total"
    )
    return enabled_tools


def get_enabled_base_tools() -> list[Any]:
    """Get base_tools filtered by configuration.

    Returns a subset of base_tools that are currently enabled.
    This function maintains the same tool selection as base_tools but respects
    the enable/disable configuration.

    Returns:
        List of enabled base tools.
    """
    manager = get_tool_config_manager()
    enabled_tool_names = set(manager.get_enabled_tools())

    # Reverse lookup: tool function -> tool name
    tool_to_name: dict[Any, str] = {v: k for k, v in TOOL_NAME_MAP.items()}

    enabled_base_tools = []
    for tool in base_tools:
        tool_name = tool_to_name.get(tool)
        # Include tool if:
        # 1. It's in the enabled list, OR
        # 2. It's not in TOOL_NAME_MAP (orchestration tools like run_aggregate_analysis)
        if tool_name is None or tool_name in enabled_tool_names:
            enabled_base_tools.append(tool)
        else:
            logger.debug(f"Filtering out disabled tool: {tool_name}")

    logger.info(
        f"Filtered base_tools: {len(enabled_base_tools)}/{len(base_tools)} tools enabled"
    )
    return enabled_base_tools


def is_tool_enabled(tool_name: str) -> bool:
    """Check if a specific tool is enabled.

    Args:
        tool_name: Name of the tool to check.

    Returns:
        True if the tool is enabled, False otherwise.
    """
    manager = get_tool_config_manager()
    return manager.is_enabled(tool_name)


# ============================================================================
# Main Agent Definition
# ============================================================================


# Create the main SRE Agent
sre_agent = LlmAgent(
    name="sre_agent",
    model="gemini-2.5-pro",
    description="""SRE Agent - Google Cloud Observability & Reliability Expert.

Capabilities:
- Orchestrates a "Core Squad" for multi-stage incident analysis (Aggregate -> Triage -> Deep Dive)
- Performs cross-signal correlation (Traces + Logs + Metrics) to find root causes
- Analyzes SLO/SLI status, error budgets, and predicts violations
- Debugs Kubernetes/GKE clusters (Node pressure, Pod crash loops, OOMs)
- Provides automated remediation suggestions with risk assessment

Structure:
- Stage 0 (Aggregate): Analyze fleet-wide trends using BigQuery
- Stage 1 (Triage): Analyze traces using the consolidated Trace Analyst.
- Stage 2 (Deep Dive): Find root cause and changes using Root Cause Analyst.

Direct Tools:
- Observability: fetch_trace, list_log_entries, query_promql, list_time_series, list_slos
- Analysis: analyze_trace_comprehensive, find_bottleneck_services, correlate_logs_with_trace
- Platform: get_gke_cluster_health, list_alerts, detect_metric_anomalies""",
    instruction=f"{SRE_AGENT_PROMPT}\n\n## 📅 Current Time\nThe current time is: {datetime.now(timezone.utc).isoformat()}",
    tools=base_tools,
    # Sub-agents for specialized analysis (automatically invoked based on task)
    sub_agents=[
        # Trace analysis sub-agents
        aggregate_analyzer,
        trace_analyst,
        # Log analysis sub-agents
        log_analyst,
        # Metrics analysis sub-agents
        metrics_analyzer,
        alert_analyst,
        # Deep Dive
        root_cause_analyst,
    ],
)

# Export as root_agent for ADK CLI compatibility
root_agent = emojify_agent(sre_agent)

# Emojify all sub-agents as well
aggregate_analyzer = emojify_agent(aggregate_analyzer)
trace_analyst = emojify_agent(trace_analyst)
log_analyst = emojify_agent(log_analyst)
metrics_analyzer = emojify_agent(metrics_analyzer)
alert_analyst = emojify_agent(alert_analyst)
root_cause_analyst = emojify_agent(root_cause_analyst)

# ============================================================================
# Dynamic Tool Loading
# ============================================================================


def create_configured_agent(
    use_mcp: bool = False,
    respect_config: bool = True,
    model: str = "gemini-2.5-pro",
) -> LlmAgent:
    """Get the SRE agent, optionally with filtered tools based on configuration.

    Note: Due to ADK's design, sub-agents can only be bound to one parent agent.
    This function returns the existing root_agent which already has all sub-agents
    configured. The tool configuration is applied at runtime through get_enabled_tools()
    and get_enabled_base_tools() functions.

    For truly dynamic agent creation with different tool configurations, use
    get_agent_with_mcp_tools() which creates a fresh agent instance.

    Args:
        use_mcp: Ignored (for API compatibility). Use get_agent_with_mcp_tools() instead.
        respect_config: Ignored (for API compatibility). Tool config is applied at runtime.
        model: Ignored (for API compatibility). Model is set at agent creation time.

    Returns:
        The configured root_agent instance.
    """
    # Return the existing root_agent since sub-agents are already bound to it.
    # Tool filtering is applied at runtime through get_enabled_base_tools().
    return root_agent


async def get_agent_with_mcp_tools(use_enabled_tools: bool = True) -> LlmAgent:
    """Get the SRE agent with MCP toolsets initialized.

    Note: Due to ADK's design, sub-agents can only be bound to one parent agent.
    This function initializes MCP toolsets but returns the existing root_agent.
    The MCP tools (mcp_execute_sql, mcp_list_log_entries, etc.) are already
    included in the agent's tool set as wrapper functions.

    Args:
        use_enabled_tools: If True, log which tools are currently enabled.
                          If False, skip the logging.

    Returns:
        The configured root_agent instance.
    """
    # Initialize MCP toolsets (these are used by the mcp_* wrapper functions)
    await _get_bigquery_mcp_toolset()
    await _get_logging_mcp_toolset()
    await _get_monitoring_mcp_toolset()

    if use_enabled_tools:
        # Log the current tool configuration for debugging
        enabled_tools = get_enabled_base_tools()
        logger.info(f"Agent initialized with {len(enabled_tools)} enabled tools")

    # Return the existing root_agent since sub-agents are already bound to it
    return root_agent
