"""Comprehensive Trace Analysis Tool (Mega-Tool).

This module consolidates multiple granular trace analysis functions into a single
comprehensive tool. This reduces the number of tool calls the LLM needs to make,
improving latency and context usage.
"""

import logging
import time
from typing import Any

from ..common import adk_tool
from ..common.telemetry import get_meter, get_tracer, log_tool_call
from .trace.analysis import (
    build_call_graph,
    calculate_span_durations,
    extract_errors,
    validate_trace_quality,
)
from .trace.statistical_analysis import analyze_critical_path, detect_latency_anomalies

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

    Returns:
        A dictionary containing all analysis results.
    """
    start_time = time.time()
    log_tool_call(logger, "analyze_trace_comprehensive", trace_id=trace_id)

    result: dict[str, Any] = {
        "trace_id": trace_id,
        "analysis_timestamp": time.time(),
    }

    try:
        # 1. Validation
        validation = validate_trace_quality(trace_id, project_id)
        result["quality_check"] = validation
        if not validation.get("valid", False):
            result["status"] = "invalid_trace"
            return result

        # 2. Timing & Errors (Parallel execution not strictly needed as underlying calls often fetch trace)
        # Note: Optimization opportunity - Underlying tools fetches trace individually.
        # Ideally, we should fetch once and pass data, but the current tool signatures take ID.
        # For now, we rely on caching in the underlying client if it exists, or accept the overhead.

        # Durations
        durations = calculate_span_durations(trace_id, project_id)
        if isinstance(durations, list):
            result["span_count"] = len(durations)
            if durations:
                result["total_duration_ms"] = durations[0].get("duration_ms") # Root span usually first or longest

        result["spans"] = durations # Raw spans with durations

        # Errors
        errors = extract_errors(trace_id, project_id)
        result["errors"] = errors
        result["error_count"] = len(errors)

        # 3. Critical Path
        critical_path = analyze_critical_path(trace_id, project_id)
        result["critical_path_analysis"] = critical_path

        # 4. Structure (Call Graph)
        if include_call_graph:
            call_graph = build_call_graph(trace_id, project_id)
            result["structure"] = call_graph

        # 5. Anomaly Detection (if baseline provided)
        if baseline_trace_id:
            anomaly = detect_latency_anomalies(
                baseline_trace_ids=[baseline_trace_id],
                target_trace_id=trace_id,
                project_id=project_id
            )
            result["anomaly_analysis"] = anomaly

        result["status"] = "success"
        return result

    except Exception as e:
        logger.error(f"Comprehensive trace analysis failed: {e}", exc_info=True)
        result["status"] = "error"
        result["error"] = str(e)
        return result
    finally:
        # Telemetry recording could go here
        pass
