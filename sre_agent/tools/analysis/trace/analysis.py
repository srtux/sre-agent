"""Span-level Trace Analysis Tools.

This module contains the core logic for inspecting the internal structure of traces.
These tools are "pure functions" that take a trace ID, fetch the data, and return
derived insights. They are heavily used by the Stage 1 Triage Agents.

Key Functions:
- `calculate_span_durations`: The raw timing data (Statement of Facts).
- `extract_errors`: The forensics report (What broke?).
- `build_call_graph`: The structural blueprint (Who called whom?).
- `validate_trace_quality`: The quality assurance check (Is this data junk?).
"""

import logging
import time
from datetime import datetime
from typing import Any, cast

from sre_agent.schema import BaseToolResponse, ToolStatus

from ...clients.trace import fetch_trace_data
from ...common import adk_tool
from ...common.telemetry import log_tool_call

logger = logging.getLogger(__name__)

# Type aliases
TraceData = dict[str, Any]
SpanData = dict[str, Any]


def _calculate_span_durations_impl(trace: TraceData) -> list[SpanData]:
    """Internal implementation of calculate_span_durations using pre-fetched data."""
    if "error" in trace:
        return [{"error": str(trace["error"])}]

    spans = trace.get("spans", [])

    timing_info = []

    for s in spans:
        s_start = s.get("start_time")
        s_end = s.get("end_time")
        s_start_unix = s.get("start_time_unix")
        s_end_unix = s.get("end_time_unix")

        duration_ms = None
        if s_start_unix is not None and s_end_unix is not None:
            # Optimized path: Use pre-calculated unix timestamps to avoid datetime parsing overhead
            duration_ms = (s_end_unix - s_start_unix) * 1000
        elif s_start and s_end:
            try:
                start_dt = datetime.fromisoformat(s_start.replace("Z", "+00:00"))
                end_dt = datetime.fromisoformat(s_end.replace("Z", "+00:00"))
                duration_ms = (end_dt - start_dt).total_seconds() * 1000
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Failed to parse timestamps for span {s.get('span_id')}: {e}"
                )

        timing_info.append(
            {
                "span_id": s.get("span_id"),
                "name": s.get("name"),
                "duration_ms": duration_ms,
                "start_time": s_start,
                "end_time": s_end,
                "parent_span_id": s.get("parent_span_id"),
                "labels": s.get("labels", {}),
            }
        )

    # Sort by duration (descending) for easy analysis
    timing_info.sort(key=lambda x: x.get("duration_ms") or 0, reverse=True)

    return timing_info


@adk_tool
def calculate_span_durations(
    trace_id: str | dict[str, Any],
    project_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Extracts timing information for each span in a trace."""
    start_time = time.time()
    log_tool_call(logger, "calculate_span_durations", trace_id=trace_id)

    try:
        from ...clients.trace import (
            _clear_thread_credentials,
            _set_thread_credentials,
            get_credentials_from_tool_context,
        )

        user_creds = get_credentials_from_tool_context(tool_context)
        if user_creds:
            _set_thread_credentials(user_creds)

        trace = fetch_trace_data(trace_id, project_id, tool_context=tool_context)
        durations = _calculate_span_durations_impl(trace)

        if durations and isinstance(durations[0], dict) and "error" in durations[0]:
            return BaseToolResponse(
                status=ToolStatus.ERROR, error=str(durations[0]["error"])
            )

        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={"spans": durations, "total_spans": len(durations)},
            metadata={"duration_ms": (time.time() - start_time) * 1000},
        )

    except Exception as e:
        logger.error(f"calculate_span_durations failed: {e}")
        return BaseToolResponse(status=ToolStatus.ERROR, error=str(e))
    finally:
        from ...clients.trace import _clear_thread_credentials

        _clear_thread_credentials()


def _extract_errors_impl(trace: TraceData) -> list[dict[str, Any]]:
    """Internal implementation of extract_errors using pre-fetched data."""
    if "error" in trace:
        return [{"error": trace["error"]}]

    spans = trace.get("spans", [])
    errors = []

    error_indicators = ["error", "exception", "fault", "failure"]

    for s in spans:
        labels = s.get("labels", {})
        span_name = s.get("name", "")

        is_error = False
        error_info: dict[str, Any] = {
            "span_id": s.get("span_id"),
            "span_name": span_name,
            "error_type": None,
            "error_message": None,
            "status_code": None,
            "labels": labels,
        }

        for key, value in labels.items():
            key_lower = key.lower()
            value_str = str(value).lower() if value else ""

            # Check for gRPC error codes first (they have small numeric values)
            if "grpc" in key_lower and "status" in key_lower:
                if value_str not in ("ok", "0"):
                    is_error = True
                    error_info["error_type"] = "gRPC Error"
                    error_info["status_code"] = value
                continue

            # Check HTTP/gRPC status codes
            if "/http/status_code" in key_lower or "http.status_code" in key_lower:
                try:
                    code = int(value)
                    if code >= 400:
                        is_error = True
                        error_info["status_code"] = code
                        error_info["error_type"] = "http_error"
                except (ValueError, TypeError):
                    pass
                continue

            # Check for general status/code fields
            if "status" in key_lower or "code" in key_lower:
                try:
                    code = int(value)
                    if code >= 400:
                        is_error = True
                        error_info["status_code"] = code
                        error_info["error_type"] = "http_error"
                except (ValueError, TypeError):
                    pass
                continue

            # Check for error/exception labels
            if any(indicator in key_lower for indicator in error_indicators):
                if value_str and value_str not in ("false", "0", "none", "ok"):
                    is_error = True
                    error_info["error_type"] = key
                    error_info["error_message"] = str(value)

        if is_error:
            errors.append(error_info)

    return errors


@adk_tool
def extract_errors(
    trace_id: str | dict[str, Any],
    project_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Finds all spans that contain errors or error-related information."""
    start_time = time.time()
    log_tool_call(logger, "extract_errors", trace_id=trace_id)

    try:
        from ...clients.trace import (
            _clear_thread_credentials,
            _set_thread_credentials,
            get_credentials_from_tool_context,
        )

        user_creds = get_credentials_from_tool_context(tool_context)
        if user_creds:
            _set_thread_credentials(user_creds)

        trace = fetch_trace_data(trace_id, project_id, tool_context=tool_context)
        errors = _extract_errors_impl(trace)

        if errors and isinstance(errors[0], dict) and "error" in errors[0]:
            return BaseToolResponse(
                status=ToolStatus.ERROR, error=str(errors[0]["error"])
            )

        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={"errors": errors, "error_count": len(errors)},
            metadata={"duration_ms": (time.time() - start_time) * 1000},
        )
    except Exception as e:
        logger.error(f"extract_errors failed: {e}")
        return BaseToolResponse(status=ToolStatus.ERROR, error=str(e))
    finally:
        from ...clients.trace import _clear_thread_credentials

        _clear_thread_credentials()


def _validate_trace_quality_impl(trace: TraceData) -> dict[str, Any]:
    """Internal implementation of validate_trace_quality using pre-fetched data."""
    if "error" in trace:
        return {
            "valid": False,
            "issue_count": 1,
            "issues": [{"type": "fetch_error", "message": trace["error"]}],
            "error": trace["error"],
        }

    spans = trace.get("spans", [])
    issues: list[dict[str, Any]] = []

    # Build parent-child map
    span_map = {s["span_id"]: s for s in spans if "span_id" in s}

    for span in spans:
        span_id = span.get("span_id")
        if not span_id:
            issues.append({"type": "missing_span_id", "message": "Span missing ID"})
            continue

        # Check for orphaned spans
        parent_id = span.get("parent_span_id")
        if parent_id and parent_id not in span_map:
            issues.append(
                {
                    "type": "orphaned_span",
                    "span_id": span_id,
                    "message": f"Parent span {parent_id} not found",
                }
            )

        # Check for negative durations and clock skew
        try:
            start_ts = span.get("start_time_unix")
            end_ts = span.get("end_time_unix")

            if start_ts is None or end_ts is None:
                start_str = span.get("start_time")
                end_str = span.get("end_time")
                if start_str and end_str:
                    start_ts = datetime.fromisoformat(
                        start_str.replace("Z", "+00:00")
                    ).timestamp()
                    end_ts = datetime.fromisoformat(
                        end_str.replace("Z", "+00:00")
                    ).timestamp()

            if start_ts is not None and end_ts is not None:
                duration = end_ts - start_ts

                if duration < 0:
                    issues.append(
                        {
                            "type": "negative_duration",
                            "span_id": span_id,
                            "duration_s": duration,
                        }
                    )

                # Check clock skew
                if parent_id and parent_id in span_map:
                    parent = span_map[parent_id]
                    p_start_ts = parent.get("start_time_unix")
                    p_end_ts = parent.get("end_time_unix")

                    if p_start_ts is None or p_end_ts is None:
                        p_start_str = parent.get("start_time")
                        p_end_str = parent.get("end_time")
                        if p_start_str and p_end_str:
                            p_start_ts = datetime.fromisoformat(
                                p_start_str.replace("Z", "+00:00")
                            ).timestamp()
                            p_end_ts = datetime.fromisoformat(
                                p_end_str.replace("Z", "+00:00")
                            ).timestamp()

                    if p_start_ts is not None and p_end_ts is not None:
                        if start_ts < p_start_ts or end_ts > p_end_ts:
                            issues.append(
                                {
                                    "type": "clock_skew",
                                    "span_id": span_id,
                                    "message": "Child span outside parent timespan",
                                }
                            )
        except (ValueError, TypeError, KeyError) as e:
            issues.append(
                {"type": "timestamp_error", "span_id": span_id, "error": str(e)}
            )

    return {"valid": len(issues) == 0, "issue_count": len(issues), "issues": issues}


@adk_tool
def validate_trace_quality(
    trace_id: str | dict[str, Any],
    project_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Validate trace data quality and detect issues."""
    start_time = time.time()
    log_tool_call(logger, "validate_trace_quality", trace_id=trace_id)

    from ...clients.trace import (
        _clear_thread_credentials,
        _set_thread_credentials,
        get_credentials_from_tool_context,
    )

    user_creds = get_credentials_from_tool_context(tool_context)
    try:
        if user_creds:
            _set_thread_credentials(user_creds)

        trace = fetch_trace_data(trace_id, project_id, tool_context=tool_context)
        result = _validate_trace_quality_impl(trace)

        if "error" in result and result.get("valid") is False:
            # Handle special case where result itself contains an error key from fetch_trace_data
            if result.get("issues") and result["issues"][0]["type"] == "fetch_error":
                return BaseToolResponse(
                    status=ToolStatus.ERROR, error=str(result["error"])
                )

        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=result,
            metadata={"duration_ms": (time.time() - start_time) * 1000},
        )

    except Exception as e:
        logger.error(f"Trace validation failed: {e}")
        return BaseToolResponse(status=ToolStatus.ERROR, error=str(e))
    finally:
        _clear_thread_credentials()


def _build_call_graph_impl(trace: TraceData) -> dict[str, Any]:
    """Internal implementation of build_call_graph using pre-fetched data."""
    if "error" in trace:
        return {"error": trace["error"]}

    spans = trace.get("spans", [])

    # Create lookup maps
    span_by_id = {}
    children_by_parent: dict[str, list[str]] = {}
    root_spans = []
    span_names: set[str] = set()

    for s in spans:
        span_id = s.get("span_id")
        parent_id = s.get("parent_span_id")
        span_name = s.get("name", "unknown")

        if span_id:
            span_by_id[span_id] = s

        span_names.add(span_name)

        if parent_id:
            if parent_id not in children_by_parent:
                children_by_parent[parent_id] = []
            children_by_parent[parent_id].append(span_id)
        else:
            root_spans.append(span_id)

    def build_subtree(span_id: str, depth: int = 0) -> dict[str, Any]:
        s = span_by_id.get(span_id, {})
        children_ids = children_by_parent.get(span_id, [])

        return {
            "span_id": span_id,
            "name": s.get("name", "unknown"),
            "depth": depth,
            "children": [
                build_subtree(child_id, depth + 1) for child_id in children_ids
            ],
            "labels": s.get("labels", {}),
        }

    span_tree = [build_subtree(root_id) for root_id in root_spans]

    def get_max_depth(node: dict[str, Any]) -> int:
        if not node.get("children"):
            return cast(int, node.get("depth", 0))
        return max(get_max_depth(child) for child in node["children"])

    max_depth = max((get_max_depth(tree) for tree in span_tree), default=0)

    result = {
        "trace_id": trace.get("trace_id"),
        "root_spans": root_spans,
        "span_tree": span_tree,
        "span_names": list(span_names),
        "total_spans": len(spans),
        "max_depth": max_depth,
    }
    return result


@adk_tool
def build_call_graph(
    trace_id: str | dict[str, Any],
    project_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Builds a hierarchical call graph from the trace spans."""
    start_time = time.time()
    log_tool_call(logger, "build_call_graph", trace_id=trace_id)

    try:
        from ...clients.trace import (
            _clear_thread_credentials,
            _set_thread_credentials,
            get_credentials_from_tool_context,
        )

        user_creds = get_credentials_from_tool_context(tool_context)
        if user_creds:
            _set_thread_credentials(user_creds)

        trace = fetch_trace_data(trace_id, project_id, tool_context=tool_context)
        result = _build_call_graph_impl(trace)

        if "error" in result:
            return BaseToolResponse(status=ToolStatus.ERROR, error=str(result["error"]))

        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=result,
            metadata={"duration_ms": (time.time() - start_time) * 1000},
        )
    except Exception as e:
        logger.error(f"build_call_graph failed: {e}")
        return BaseToolResponse(status=ToolStatus.ERROR, error=str(e))
    finally:
        _clear_thread_credentials()


@adk_tool
def summarize_trace(
    trace_id: str | dict[str, Any],
    project_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Creates a summary of a trace to save context window tokens."""
    start_time = time.time()
    log_tool_call(logger, "summarize_trace", trace_id=trace_id)

    from ...clients.trace import (
        _clear_thread_credentials,
        _set_thread_credentials,
        get_credentials_from_tool_context,
    )

    user_creds = get_credentials_from_tool_context(tool_context)
    try:
        if user_creds:
            _set_thread_credentials(user_creds)
        trace_data = fetch_trace_data(trace_id, project_id, tool_context=tool_context)

        if "error" in trace_data:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error=str(trace_data["error"]),
                result={"trace_id": trace_id},
            )

        spans = trace_data.get("spans", [])
        duration_ms = trace_data.get("duration_ms", 0)

        # Extract errors using internal impl to avoid tool overhead
        errors = _extract_errors_impl(trace_data)

        # Extract slow spans using optimized internal impl
        durations = _calculate_span_durations_impl(trace_data)

        # Map to expected format (name, duration_ms) and take top 5
        # _calculate_span_durations_impl already sorts by duration descending
        top_slowest = [
            {"name": s.get("name"), "duration_ms": s.get("duration_ms", 0.0)}
            for s in durations[:5]
        ]

        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={
                "trace_id": trace_data.get("trace_id"),
                "total_spans": len(spans),
                "duration_ms": duration_ms,
                "error_count": len(errors),
                "errors": errors[:5],
                "slowest_spans": top_slowest,
            },
            metadata={"duration_ms": (time.time() - start_time) * 1000},
        )
    except Exception as e:
        logger.error(f"summarize_trace failed: {e}")
        return BaseToolResponse(status=ToolStatus.ERROR, error=str(e))
    finally:
        _clear_thread_credentials()
