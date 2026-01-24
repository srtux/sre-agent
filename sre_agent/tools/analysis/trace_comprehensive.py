"""Comprehensive Trace Analysis Tool (Mega-Tool).

This module consolidates multiple granular trace analysis functions into a single
comprehensive tool. This reduces the number of tool calls the LLM needs to make,
improving latency and context usage.
"""

import asyncio
import logging
import time
from typing import Any

from fastapi.concurrency import run_in_threadpool

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
    _detect_latency_anomalies_impl,
    compute_latency_statistics_impl,
)

# Telemetry setup
tracer = get_tracer(__name__)
meter = get_meter(__name__)
logger = logging.getLogger(__name__)


@adk_tool
async def analyze_trace_comprehensive(
    trace_id: str,
    project_id: str | None = None,
    include_call_graph: bool = True,
    baseline_trace_id: str | None = None,
    tool_context: Any = None,
) -> dict[str, Any]:
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
        tool_context: ADK ToolContext for credential propagation.

    Returns:
        A dictionary containing all analysis results.
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

    async def _fetch_wrapper(tid_or_json: str) -> dict[str, Any]:
        """Async wrapper for fetch_trace_data with credential propagation."""
        if user_creds:
            _set_thread_credentials(user_creds)
        try:
            return await run_in_threadpool(fetch_trace_data, tid_or_json, project_id)
        finally:
            if user_creds:
                _clear_thread_credentials()

    try:
        # Fetch trace data (and optional baseline) concurrently
        tasks = [_fetch_wrapper(trace_id)]
        if baseline_trace_id:
            tasks.append(_fetch_wrapper(baseline_trace_id))

        fetched_results = await asyncio.gather(*tasks)
        trace_data = fetched_results[0]
        baseline_data = fetched_results[1] if baseline_trace_id else None

        # Update trace_id to the actual ID from data (relevant if input was a JSON string)
        if "trace_id" in trace_data:
            result["trace_id"] = trace_data["trace_id"]

        # If fetching failed, return error immediately
        if "error" in trace_data:
            result["status"] = "error"
            result["error"] = trace_data["error"]
            return result

        # 1. Validation
        validation = _validate_trace_quality_impl(trace_data)
        result["quality_check"] = validation
        if not validation.get("valid", False):
            result["status"] = "invalid_trace"
            return result

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
        if baseline_data:
            # We must compute baseline stats first using the pre-fetched data
            # Note: compute_latency_statistics_impl expects a list of trace data
            baseline_stats = compute_latency_statistics_impl([baseline_data])

            # Then use our pre-fetched target data
            anomaly = _detect_latency_anomalies_impl(
                baseline_stats,
                trace_data,
            )
            result["anomaly_analysis"] = anomaly

        result["status"] = "success"
        return result

    except Exception as e:
        logger.error(f"Comprehensive trace analysis failed: {e}", exc_info=True)
        result["status"] = "error"
        result["error"] = str(e)
        return result
