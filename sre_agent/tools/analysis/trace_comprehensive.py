"""Comprehensive Trace Analysis Tool (Mega-Tool).

This module consolidates multiple granular trace analysis functions into a single
comprehensive tool. This reduces the number of tool calls the LLM needs to make,
improving latency and context usage.
"""

import logging
import time
from typing import Any, cast

from sre_agent.schema import BaseToolResponse, ToolStatus

from ..common import adk_tool
from ..common.telemetry import get_meter, get_tracer, log_tool_call
from .trace.analysis import (
    _build_call_graph_impl,
    _calculate_span_durations_impl,
    _extract_errors_impl,
    _validate_trace_quality_impl,
)
from .trace.statistical_analysis import (
    _analyze_critical_path_impl,
    _compute_latency_statistics_impl,
    _detect_latency_anomalies_impl,
)

# Telemetry setup
tracer = get_tracer(__name__)
meter = get_meter(__name__)
logger = logging.getLogger(__name__)


@adk_tool
def analyze_trace_comprehensive(
    trace_id: str,
    project_id: str | None = None,
    include_call_graph: bool = True,
    baseline_trace_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Performs a comprehensive analysis of a single trace.

    Combines:
    1. Validation (Quality check)
    2. Duration calculation (Timing)
    3. Error extraction (Forensics)
    4. Critical Path analysis (Bottlenecks)
    5. Call Graph construction (Structure) - Optional
    6. Anomaly detection (if baseline_trace_id is provided)

    Args:
        trace_id: The ID of the trace to analyze.
        project_id: GCP Project ID.
        include_call_graph: Whether to include the full call graph tree (can be large).
        baseline_trace_id: Optional ID of a baseline trace to compare against.
        tool_context: Context object for tool execution.

    Returns:
        All analysis results in BaseToolResponse.
    """
    log_tool_call(logger, "analyze_trace_comprehensive", trace_id=trace_id)

    result: dict[str, Any] = {
        "trace_id": trace_id,
        "analysis_timestamp": time.time(),
    }

    # Setup credentials for fetching the trace once
    from ..clients.trace import (
        _clear_thread_credentials,
        _set_thread_credentials,
        fetch_trace_data,
        get_credentials_from_tool_context,
    )

    user_creds = get_credentials_from_tool_context(tool_context)
    if user_creds:
        _set_thread_credentials(user_creds)

    try:
        # Fetch trace data ONCE
        trace_data = fetch_trace_data(trace_id, project_id, tool_context=tool_context)

        # Update trace_id to the actual ID from data (relevant if input was a JSON string)
        if "trace_id" in trace_data:
            result["trace_id"] = trace_data["trace_id"]

        # If fetching failed, return error immediately
        if "error" in trace_data:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error=trace_data["error"],
                result={"trace_id": trace_id},
            )

        # 1. Validation
        validation = _validate_trace_quality_impl(trace_data)
        result["quality_check"] = validation
        if not validation.get("valid", False):
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error=f"Trace {trace_id} failed quality check: {validation.get('issues', 'unknown')}",
                result=result,
            )

        # 2. Timing & Errors
        # Durations
        durations = _calculate_span_durations_impl(trace_data)
        if isinstance(durations, list):
            result["span_count"] = len(durations)
            if durations:
                # Find root or longest span
                result["total_duration_ms"] = durations[0].get("duration_ms")

        result["spans"] = durations

        # Errors
        errors = _extract_errors_impl(trace_data)
        result["errors"] = errors
        result["error_count"] = len(errors)

        # 3. Critical Path
        critical_path = _analyze_critical_path_impl(trace_data)
        result["critical_path_analysis"] = critical_path

        # 4. Structure (Call Graph)
        if include_call_graph:
            call_graph = _build_call_graph_impl(trace_data)
            result["structure"] = call_graph

        # 5. Anomaly Detection (if baseline provided)
        if baseline_trace_id:
            # We must compute baseline stats first (this still requires fetching baselines)
            baseline_stats_response = _compute_latency_statistics_impl(
                [baseline_trace_id], project_id, tool_context=tool_context
            )
            # Then use our pre-fetched target data
            if baseline_stats_response.status == ToolStatus.SUCCESS:
                anomaly = _detect_latency_anomalies_impl(
                    cast(dict[str, Any], baseline_stats_response.result),
                    trace_data,
                )
                result["anomaly_analysis"] = anomaly

        return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)

    except Exception as e:
        logger.error(f"Comprehensive trace analysis failed: {e}", exc_info=True)
        return BaseToolResponse(status=ToolStatus.ERROR, error=str(e), result=result)
    finally:
        if user_creds:
            _clear_thread_credentials()
