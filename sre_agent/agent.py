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

from .auth import (
    GLOBAL_CONTEXT_CREDENTIALS,
    get_credentials_from_session,
    get_current_project_id,
    get_project_id_from_session,
    set_current_credentials,
    set_current_project_id,
    set_current_user_id,
)
from .memory.factory import get_memory_manager
from .model_config import get_model_name
from .prompt import SRE_AGENT_PROMPT
from .schema import BaseToolResponse, InvestigationPhase, ToolStatus

# Import sub-agents
from .sub_agents import (
    # Trace analysis sub-agents
    aggregate_analyzer,
    # Alert analysis sub-agents
    alert_analyst,
    # Metrics analysis sub-agents
    get_metrics_analyzer,
    # Log analysis sub-agents
    log_analyst,
    metrics_analyzer,
    root_cause_analyst,
    trace_analyst,
)
from .tools import (
    add_finding_to_memory,
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
    list_metric_descriptors,
    # SLO listing
    list_slos,
    list_time_series,
    list_traces,
    perform_causal_analysis,
    # SLO prediction
    predict_slo_violation,
    query_promql,
    search_memory,
    suggest_next_steps,
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
            logger.info(f"🚀 Discovered project ID from credentials: {project_id}")
    except Exception as e:
        logger.debug(f"Could not discover project ID from credentials: {e}")

location = os.environ.get("GCP_LOCATION") or os.environ.get(
    "GOOGLE_CLOUD_LOCATION", "us-central1"
)
use_vertex = os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "true").lower() == "true"

# Ensure Environment is configured for SDKs
if project_id:
    os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
    os.environ["GCP_PROJECT_ID"] = project_id

# 1. Initialize Telemetry and Logging as early as possible
try:
    from .tools.common.telemetry import setup_telemetry

    setup_telemetry()
except Exception as e:
    # Use standard print as last resort if logging failed to initialize
    print(f"CRITICAL: Failed to initialize telemetry/logging: {e}")

# 2. Initialize Vertex AI if project and location are found
if project_id:
    try:
        vertexai.init(project=project_id, location=location)
        logger.info(f"✅ Initialized Vertex AI: {project_id} @ {location}")
    except Exception as e:
        logger.warning(f"Failed to initialize Vertex AI: {e}")


def emojify_agent(agent: LlmAgent | Any) -> LlmAgent | Any:
    """Wraps an LlmAgent to add emojis to prompts and responses in logs.

    If a callable is passed, it assumes it's a factory (lazy loader) and
    wraps the factory to return emojified agents.
    """
    if callable(agent) and not isinstance(agent, LlmAgent):

        @functools.wraps(agent)
        def wrapped_factory(*args: Any, **kwargs: Any) -> Any:
            instance = agent(*args, **kwargs)
            return emojify_agent(instance)

        return wrapped_factory

    # Check if we should skip manual logging (let OTel/ADK handle it)
    # This avoids redundant logs when OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT is true
    skip_manual_logging = (
        os.environ.get(
            "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "false"
        ).lower()
        == "true"
        or os.environ.get("RUNNING_IN_AGENT_ENGINE", "").lower() == "true"
    )

    original_run_async = agent.run_async

    @functools.wraps(original_run_async)
    async def wrapped_run_async(context: Any) -> AsyncGenerator[Any, None]:
        # 1. Log Prompt (only if not skipping manual logging)
        user_msg = "Unknown"
        if not skip_manual_logging:
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
        project_id = get_current_project_id() or "unknown"
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

        if not skip_manual_logging:
            border = "⎯" * 80
            logger.info(border)
            logger.info("  📥 INCOMING USER REQUEST 📥")
            logger.info(border)
            logger.info(f"💬 User Prompt:\n{user_msg}")
            logger.info(border)
            logger.info(
                f"📍 Context: Project={project_id}, Session={session_id}, User={user_id}"
            )
            logger.info(border)

        from .tools.common import using_arize_session

        # 1a. Safety: Ensure model is context-aware for THIS request
        # We use temporary swapping to avoid poisoning the global agent object
        # with unpickleable model clients, which would break deployment/deepcopy.
        model_obj = _inject_global_credentials(agent, force=True)
        old_model = agent.model
        should_swap = model_obj is not None and model_obj is not old_model

        if should_swap:
            object.__setattr__(agent, "model", model_obj)
            logger.debug(f"Emojify: Temporarily swapped model for {agent.name}")

        # 2. Propagation: Ensure user credentials from session are in ContextVar
        # This protects both tool calls and LLM calls (via GLOBAL_CONTEXT_CREDENTIALS).
        session_state = None
        token = (
            None  # Initialize token here to avoid UnboundLocalError in finally block
        )
        if hasattr(context, "session") and context.session:
            session_state = getattr(context.session, "state", None)
            if session_state is None and isinstance(context.session, dict):
                session_state = context.session.get("state")

        if session_state:
            user_creds = get_credentials_from_session(session_state)
            if user_creds:
                set_current_credentials(user_creds)

            sess_project_id = get_project_id_from_session(session_state)
            if sess_project_id:
                set_current_project_id(sess_project_id)

            user_email = session_state.get("user_email")
            if user_email:
                set_current_user_id(user_email)

            # Import OTel components here to ensure they are available in this scope
            from opentelemetry import context as otel_context
            from opentelemetry import trace
            from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags

            from .auth import (
                SESSION_STATE_SPAN_ID_KEY,
                SESSION_STATE_TRACE_FLAGS_KEY,
                SESSION_STATE_TRACE_ID_KEY,
                set_trace_id,
            )

            remote_trace_id = session_state.get(SESSION_STATE_TRACE_ID_KEY)
            remote_span_id = session_state.get(SESSION_STATE_SPAN_ID_KEY)
            remote_flags = session_state.get(SESSION_STATE_TRACE_FLAGS_KEY)

            token = None
            if remote_trace_id:
                set_trace_id(remote_trace_id)
                try:
                    # Link local operations to the global trace!
                    # CRITICAL: span_id MUST be non-zero for the context to be valid.
                    # We use the propagated span_id if available, or fall back to
                    # a deterministic non-zero ID derived from the trace ID.
                    s_id = 0
                    if remote_span_id:
                        try:
                            s_id = int(remote_span_id, 16)
                        except (ValueError, TypeError):
                            pass

                    if s_id == 0:
                        # Deterministic fallback: use first 8 bytes of trace_id
                        s_id = int(remote_trace_id[:16], 16)

                    # Trace flags (e.g. sampled)
                    flags = TraceFlags.SAMPLED
                    if remote_flags:
                        try:
                            flags = TraceFlags(int(remote_flags, 16))
                        except (ValueError, TypeError):
                            pass

                    span_context = SpanContext(
                        trace_id=int(remote_trace_id, 16),
                        span_id=s_id,
                        is_remote=True,
                        trace_flags=TraceFlags(flags),
                    )
                    parent_ctx = trace.set_span_in_context(
                        NonRecordingSpan(span_context)
                    )
                    token = otel_context.attach(parent_ctx)
                    logger.debug(
                        f"📍 Restored OTel Context: trace_id={remote_trace_id}, span_id={s_id:016x}, flags={flags:02x}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to restore OTel context: {e}")
                    pass

        # 3. Run Original with Arize session context
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
            logger.error(f"🔥 Agent Execution Failed: {e}", exc_info=True)
            raise e
        finally:
            # Restore model to avoid breaking deepcopy for deployment
            if should_swap:
                object.__setattr__(agent, "model", old_model)
                logger.debug(f"Emojify: Restored model for {agent.name}")

            # Detach OTel context if attached
            if token is not None:
                otel_context.detach(token)

        # 4. Log Response
        final_response = "".join(full_response_parts)
        if final_response and not skip_manual_logging:
            preview = (
                final_response[:500] + "..."
                if len(final_response) > 500
                else final_response
            )
            border = "⎯" * 80
            logger.info(border)
            logger.info("  🏁 FINAL RESPONSE TO USER 🏁")
            logger.info(border)
            logger.info(f"{preview}")
            logger.info(border)

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
) -> BaseToolResponse:
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
                return BaseToolResponse(
                    status=ToolStatus.SUCCESS,
                    result="Telemetry discovery completed but found no trace tables. Please ask the user to provide the 'dataset_id' manually.",
                    metadata={"stage": "aggregate"},
                )

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

        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=result,
            metadata={"stage": "aggregate"},
        )

    except Exception as e:
        logger.error(f"Aggregate analysis failed: {e}", exc_info=True)
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=str(e),
            metadata={"stage": "aggregate"},
        )


@adk_tool
async def run_triage_analysis(
    baseline_trace_id: str,
    target_trace_id: str,
    project_id: str | None = None,
    tool_context: Any | None = None,
) -> BaseToolResponse:
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

    # Update state to TRIAGE
    try:
        inv_ctx = getattr(tool_context, "invocation_context", None)
        session = getattr(inv_ctx, "session", None) if inv_ctx else None
        session_id = getattr(session, "id", None) if session else None

        manager = get_memory_manager()
        await manager.update_state(InvestigationPhase.TRIAGE, session_id=session_id)
    except Exception as e:
        logger.warning(f"Failed to update investigation state: {e}")

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

    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result={
            "baseline_trace_id": baseline_trace_id,
            "target_trace_id": target_trace_id,
            "results": triage_results,
        },
        metadata={"stage": "triage"},
    )


@adk_tool
async def run_deep_dive_analysis(
    baseline_trace_id: str,
    target_trace_id: str,
    triage_findings: dict[str, Any],
    project_id: str | None = None,
    tool_context: Any | None = None,
) -> BaseToolResponse:
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

    # Update state to DEEP_DIVE
    try:
        inv_ctx = getattr(tool_context, "invocation_context", None)
        session = getattr(inv_ctx, "session", None) if inv_ctx else None
        session_id = getattr(session, "id", None) if session else None

        manager = get_memory_manager()
        await manager.update_state(InvestigationPhase.DEEP_DIVE, session_id=session_id)
    except Exception as e:
        logger.warning(f"Failed to update investigation state: {e}")

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
        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=result,
            metadata={"stage": "deep_dive"},
        )
    except Exception as e:
        logger.error(f"Deep dive analysis failed: {e}", exc_info=True)
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=str(e),
            metadata={"stage": "deep_dive"},
        )


@adk_tool
async def run_log_pattern_analysis(
    log_filter: str,
    baseline_start: str,
    baseline_end: str,
    comparison_start: str,
    comparison_end: str,
    project_id: str | None = None,
    tool_context: Any | None = None,
) -> BaseToolResponse:
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

Note: If using `list_log_entries`, ensure GKE fields are prefixed with `resource.labels.`.
""",
            },
            tool_context=tool_context,
        )

        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=result,
            metadata={"stage": "log_pattern"},
        )

    except Exception as e:
        logger.error(f"Log pattern analysis failed: {e}", exc_info=True)
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=str(e),
            metadata={"stage": "log_pattern"},
        )


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
    "list_metric_descriptors": list_metric_descriptors,
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
    # Memory
    "add_finding_to_memory": add_finding_to_memory,
    "search_memory": search_memory,
    "suggest_next_steps": suggest_next_steps,
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
    list_metric_descriptors,
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
    # Memory tools
    add_finding_to_memory,
    search_memory,
    suggest_next_steps,
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
    model=get_model_name("fast"),
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
    tools=get_enabled_base_tools(),
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
get_metrics_analyzer = emojify_agent(get_metrics_analyzer)  # type: ignore[assignment]
alert_analyst = emojify_agent(alert_analyst)

root_cause_analyst = emojify_agent(root_cause_analyst)


# ============================================================================
# Global Credential Injection
# ============================================================================


def _inject_global_credentials(agent_to_patch: Any, force: bool = False) -> Any:
    """Inject GLOBAL_CONTEXT_CREDENTIALS into an agent's model.

    This ensures that the underlying LLM client uses context-aware credentials
    that dynamically pick up the user's token from the request context.

    Args:
        agent_to_patch: The agent (or lazy loader factory) to patch.
        force: If True, forces instantiation of the model if it's currently a string.
               This should be set to True at runtime (in run_async) but False at
               module level to avoid deepcopy failures during deployment.

    Returns:
        The instantiated/patched model object, or None if injection was skipped.
    """
    # If it's a lazy loader factory, we can't easily patch it here
    # unless we wrap the factory itself.
    if callable(agent_to_patch) and not isinstance(agent_to_patch, LlmAgent):
        return None

    try:
        if not hasattr(agent_to_patch, "model"):
            return None

        model_obj = agent_to_patch.model

        if isinstance(model_obj, str):
            if not force:
                logger.debug(
                    f"Skipping model injection for {getattr(agent_to_patch, 'name', 'unknown')} (model is string and force=False)"
                )
                return None

            from google.adk.models import LLMRegistry

            # Ensure environment is ready for google-genai discovery
            curr_project = get_current_project_id() or project_id
            curr_location = location or "us-central1"
            if curr_project:
                os.environ["GOOGLE_CLOUD_PROJECT"] = curr_project
            if curr_location:
                os.environ["GOOGLE_CLOUD_LOCATION"] = curr_location

            # Use Vertex AI by default for these models
            os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"

            try:
                model_obj = LLMRegistry.new_llm(model_obj)
            except Exception as e:
                logger.warning(
                    f"LLMRegistry.new_llm failed: {e}. Trying direct Gemini instantiation."
                )
                from google.adk.models import Gemini

                model_obj = Gemini(
                    model=model_obj,
                    vertexai=True,
                    project=curr_project,
                    location=curr_location,
                )  # type: ignore[call-arg]

        # Check for google-genai client structure (used by ADK's GoogleLLM/Gemini)
        if hasattr(model_obj, "api_client"):
            # Older google-genai versions
            if hasattr(model_obj.api_client, "config"):
                model_obj.api_client.config.credentials = GLOBAL_CONTEXT_CREDENTIALS

            # Newer google-genai versions (like 1.59.0+)
            if hasattr(model_obj.api_client, "_api_client"):
                model_obj.api_client._api_client._credentials = (
                    GLOBAL_CONTEXT_CREDENTIALS
                )

        return model_obj
    except Exception as e:
        logger.warning(f"Failed to inject credentials into agent: {e}")
        return None


# Apply injection to main agent and all sub-agents
_inject_global_credentials(sre_agent)
for _sa in [
    aggregate_analyzer,
    trace_analyst,
    log_analyst,
    metrics_analyzer,
    alert_analyst,
    root_cause_analyst,
]:
    _inject_global_credentials(_sa)


# ============================================================================
# Dynamic Tool Loading
# ============================================================================


def create_configured_agent(
    use_mcp: bool = False,
    respect_config: bool = True,
    model: str = "gemini-3-flash-preview",
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
