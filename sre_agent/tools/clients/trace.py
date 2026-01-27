"""Cloud Trace API clients for fetching and listing traces.

This module provides direct access to the Google Cloud Trace API (v1/v2).
It includes optimization features such as:
- **In-Memory Caching**: Prevents redundant API calls for the same trace ID.
- **Trace Validation**: Ensures fetched traces meet quality standards (e.g., have duration).
- **Advanced Filtering**: Simplifies the complex Cloud Trace filter syntax.
- **Anomaly Scoring**: Helper logic to identify interesting traces.

Usage:
These tools are primarily used by the "Squad" (Stage 1 sub-agents) to fetch
and inspect individual traces during triage.
"""

import asyncio
import contextvars
import json
import logging
import os
import re
import statistics
from collections.abc import Coroutine
from datetime import datetime, timezone
from typing import Any, cast

from fastapi.concurrency import run_in_threadpool
from google.cloud import trace_v1
from google.protobuf.timestamp_pb2 import Timestamp

from sre_agent.auth import (
    GLOBAL_CONTEXT_CREDENTIALS,
    get_credentials_from_tool_context,
    get_current_project_id,
)
from sre_agent.schema import BaseToolResponse, ToolStatus
from sre_agent.tools.common import adk_tool
from sre_agent.tools.common.cache import get_data_cache
from sre_agent.tools.common.telemetry import get_meter, get_tracer

__all__ = [
    "_clear_thread_credentials",
    "_set_thread_credentials",
    "fetch_trace",
    "fetch_trace_data",
    "find_example_traces",
    "get_credentials_from_tool_context",
    "get_trace_client",
    "list_traces",
    "validate_trace",
]

# Context variable for credentials to pass to sync functions running in threadpool
_thread_credentials: contextvars.ContextVar[Any | None] = contextvars.ContextVar(
    "thread_credentials", default=None
)


def _set_thread_credentials(creds: Any) -> None:
    """Set credentials for use in threadpool sync functions."""
    _thread_credentials.set(creds)


def _get_thread_credentials() -> Any:
    """Get credentials from thread storage."""
    return _thread_credentials.get()


def _clear_thread_credentials() -> None:
    """Clear thread credentials after use."""
    _thread_credentials.set(None)


logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)
meter = get_meter(__name__)


class TraceFilterBuilder:
    """Helper to construct Cloud Trace filter strings.

    Encapsulates the complex [^][+]key:value syntax of Cloud Trace.
    """

    def __init__(self) -> None:
        """Initialize the builder with empty terms."""
        self.terms: list[str] = []

    def add_latency(self, duration_ms: int) -> "TraceFilterBuilder":
        """Filter by minimum latency."""
        self.terms.append(f"latency:{duration_ms}ms")
        return self

    def add_root_span_name(
        self, name: str, exact: bool = False
    ) -> "TraceFilterBuilder":
        """Filter by root span name."""
        term = f"root:{name}"
        if exact:
            term = f"+{term}"
        self.terms.append(term)
        return self

    def add_span_name(
        self, name: str, exact: bool = False, root_only: bool = False
    ) -> "TraceFilterBuilder":
        """Filter by span name."""
        prefix = "^" if root_only else ""
        op = "+" if exact else ""
        term = f"{op}{prefix}span:{name}"
        self.terms.append(term)
        return self

    def add_attribute(
        self, key: str, value: Any, exact: bool = False, root_only: bool = False
    ) -> "TraceFilterBuilder":
        """Add an attribute filter.

        Args:
            key: The attribute key (e.g. '/http/status_code').
            value: The value to match.
            exact: If True, uses exact match (+).
            root_only: If True, restricts to root span (^).
        """
        str_val = str(value)
        # Quote value if it contains special characters
        if not re.match(r"^[a-zA-Z0-9./_-]+$", str_val):
            escaped_val = str_val.replace("\\", "\\\\").replace('"', '\\"')
            str_val = f'"{escaped_val}"'

        prefix = "^" if root_only else ""
        op = "+" if exact else ""

        term = f"{op}{prefix}{key}:{str_val}"
        self.terms.append(term)
        return self

    def build(self) -> str:
        """Returns the final filter string."""
        return " ".join(self.terms)


def _get_project_id() -> str:
    """Get the GCP project ID from context or environment."""
    project_id = (
        get_current_project_id()
        or os.environ.get("TRACE_PROJECT_ID")
        or os.environ.get("GOOGLE_CLOUD_PROJECT")
    )
    if not project_id:
        raise ValueError(
            "Project ID not found in context or environment variables (TRACE_PROJECT_ID, GOOGLE_CLOUD_PROJECT). "
            "HINT: If you are using the Agent Engine playground, please pass the project ID "
            "in your request (e.g., 'Analyze traces in project my-project-id') or use the project selector."
        )
    return project_id


def get_current_time() -> str:
    """Returns the current UTC time in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def get_trace_client(credentials: Any = None) -> trace_v1.TraceServiceClient:
    """Gets a Cloud Trace API client."""
    return trace_v1.TraceServiceClient(credentials=credentials)


def fetch_trace_data(
    trace_id_or_json: str | dict[str, Any],
    project_id: str | None = None,
    tool_context: Any = None,
) -> dict[str, Any]:
    """Helper to fetch trace data by ID or from JSON/dict."""
    if isinstance(trace_id_or_json, dict):
        if (
            "trace_id" in trace_id_or_json
            or "spans" in trace_id_or_json
            or "error" in trace_id_or_json
        ):
            return trace_id_or_json
        return {"error": "Invalid trace dictionary provided."}

    if isinstance(trace_id_or_json, str) and trace_id_or_json.strip().startswith("{"):
        try:
            data = json.loads(trace_id_or_json)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            return {"error": "Failed to parse trace JSON"}

    if not project_id:
        try:
            project_id = _get_project_id()
        except ValueError:
            pass

    if not project_id:
        return {
            "error": (
                "Project ID required to fetch trace. "
                "HINT: If you are using the Agent Engine playground, please pass the project ID "
                "in your request (e.g., 'Analyze traces in project my-project-id') or use the project selector."
            )
        }

    user_creds = get_credentials_from_tool_context(tool_context)
    try:
        # Fallback to GLOBAL_CONTEXT_CREDENTIALS for local/ADC execution
        creds = user_creds or GLOBAL_CONTEXT_CREDENTIALS
        _set_thread_credentials(creds)
        trace_json = _fetch_trace_sync(project_id, trace_id_or_json)
        try:
            if isinstance(trace_json, dict):
                return trace_json
            data = json.loads(trace_json)
            return cast(dict[str, Any], data)
        except json.JSONDecodeError:
            return {"error": "Invalid trace JSON"}
    finally:
        if user_creds:
            _clear_thread_credentials()


@adk_tool
async def fetch_trace(
    trace_id: str,
    project_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Fetches a specific trace by ID from Cloud Trace API."""
    from fastapi.concurrency import run_in_threadpool

    if not project_id:
        try:
            project_id = _get_project_id()
        except ValueError as e:
            return BaseToolResponse(status=ToolStatus.ERROR, error=str(e))

    user_creds = get_credentials_from_tool_context(tool_context)
    try:
        # Fallback to GLOBAL_CONTEXT_CREDENTIALS for local/ADC execution
        creds = user_creds or GLOBAL_CONTEXT_CREDENTIALS
        _set_thread_credentials(creds)
        result = await run_in_threadpool(_fetch_trace_sync, project_id, trace_id)
        if isinstance(result, dict) and "error" in result:
            return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
        return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)
    finally:
        _clear_thread_credentials()


def _fetch_trace_sync(project_id: str, trace_id: str) -> dict[str, Any]:
    """Synchronous implementation of fetch_trace."""
    thread_creds = _get_thread_credentials() or GLOBAL_CONTEXT_CREDENTIALS
    cache = get_data_cache()

    cached = cache.get(f"trace:{trace_id}")
    if cached:
        logger.debug(f"Cache hit for trace {trace_id}, skipping API call")
        if isinstance(cached, str):
            try:
                return cast(dict[str, Any], json.loads(cached))
            except json.JSONDecodeError:
                pass
        return cast(dict[str, Any], cached)

    with tracer.start_as_current_span("fetch_trace") as span:
        span.set_attribute("gcp.project_id", project_id)
        span.set_attribute("gcp.trace_id", trace_id)
        span.set_attribute("rpc.system", "google_cloud")
        span.set_attribute("rpc.service", "cloud_trace")
        span.set_attribute("rpc.method", "get_trace")

        try:
            if thread_creds:
                client = get_trace_client(credentials=thread_creds)
            else:
                # This should not be hit with GLOBAL_CONTEXT_CREDENTIALS fallback
                error_msg = (
                    "Authentication failed: No credentials found in context or ADC. "
                    "Ensure GOOGLE_APPLICATION_CREDENTIALS is set."
                )
                logger.error(error_msg)
                return {"error": error_msg}

            trace_obj = client.get_trace(project_id=project_id, trace_id=trace_id)

            spans = []
            trace_start = None
            trace_end = None

            for span_proto in trace_obj.spans:

                def get_ts_val(ts_proto: Any) -> float:
                    if hasattr(ts_proto, "timestamp"):
                        return cast(float, ts_proto.timestamp())
                    return cast(float, ts_proto.seconds + ts_proto.nanos / 1e9)

                def get_ts_str(ts_proto: Any) -> str:
                    if hasattr(ts_proto, "isoformat"):
                        return cast(str, ts_proto.isoformat())
                    return datetime.fromtimestamp(
                        get_ts_val(ts_proto), tz=timezone.utc
                    ).isoformat()

                s_start = get_ts_val(span_proto.start_time)
                s_end = get_ts_val(span_proto.end_time)

                if trace_start is None or s_start < trace_start:
                    trace_start = s_start
                if trace_end is None or s_end > trace_end:
                    trace_end = s_end

                spans.append(
                    {
                        "span_id": span_proto.span_id,
                        "name": span_proto.name,
                        "start_time": get_ts_str(span_proto.start_time),
                        "end_time": get_ts_str(span_proto.end_time),
                        "start_time_unix": s_start,
                        "end_time_unix": s_end,
                        "parent_span_id": span_proto.parent_span_id,
                        "labels": dict(span_proto.labels),
                    }
                )

            dur_ms = (
                (trace_end - trace_start) * 1000 if trace_start and trace_end else 0
            )
            span.set_attribute("gcp.trace.duration_ms", dur_ms)
            span.set_attribute("gcp.trace.span_count", len(spans))

            result = {
                "trace_id": trace_obj.trace_id,
                "project_id": trace_obj.project_id,
                "spans": spans,
                "span_count": len(spans),
                "duration_ms": dur_ms,
            }

            cache.put(f"trace:{trace_id}", result)
            return result

        except Exception as e:
            span.record_exception(e)
            error_msg = f"Failed to fetch trace: {e!s}"
            if "404" in error_msg or "NotFound" in error_msg:
                error_msg += (
                    "\n\nHINT: Trace not found. "
                    "Ensure the trace ID is correct. If you found this ID in a log, "
                    "make sure it's the full 32-character hex string. "
                    "Try listing recent traces with 'list_traces' to find valid IDs."
                )
            logger.error(error_msg, exc_info=True)
            return {"error": error_msg}


@adk_tool
async def list_traces(
    project_id: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    limit: int = 10,
    filter_str: str = "",
    min_latency_ms: int | None = None,
    error_only: bool = False,
    attributes_json: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Lists recent traces with advanced filtering capabilities."""
    from fastapi.concurrency import run_in_threadpool

    if not project_id:
        try:
            project_id = _get_project_id()
        except ValueError as e:
            return BaseToolResponse(status=ToolStatus.ERROR, error=str(e))

    user_creds = get_credentials_from_tool_context(tool_context)
    try:
        # Fallback to GLOBAL_CONTEXT_CREDENTIALS for local/ADC execution
        creds = user_creds or GLOBAL_CONTEXT_CREDENTIALS
        _set_thread_credentials(creds)
        result = await run_in_threadpool(
            _list_traces_sync,
            project_id,
            limit,
            min_latency_ms,
            error_only,
            start_time,
            end_time,
            attributes_json,
        )
        if isinstance(result, dict) and "error" in result:
            return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
        return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)
    finally:
        _clear_thread_credentials()


def _list_traces_sync(
    project_id: str,
    limit: int = 10,
    min_latency_ms: int | None = None,
    error_only: bool = False,
    start_time: str | None = None,
    end_time: str | None = None,
    attributes_json: str | None = None,
) -> list[dict[str, Any]] | dict[str, Any]:
    """Synchronous implementation of list_traces."""
    with tracer.start_as_current_span("list_traces"):
        thread_creds = _get_thread_credentials() or GLOBAL_CONTEXT_CREDENTIALS
        try:
            if thread_creds:
                client = get_trace_client(credentials=thread_creds)
            else:
                error_msg = (
                    "Authentication failed: No credentials found in context or ADC. "
                    "Ensure GOOGLE_APPLICATION_CREDENTIALS is set."
                )
                logger.error(error_msg)
                return {"error": error_msg}

            filters = []
            if min_latency_ms:
                filters.append(f"latency:{min_latency_ms}ms")
            if error_only:
                filters.append("error:true")
            filter_str = " ".join(filters)

            start_timestamp = None
            end_timestamp = None

            if start_time:
                try:
                    dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    start_timestamp = Timestamp()
                    start_timestamp.FromDatetime(dt)
                except Exception:
                    logger.warning(f"Invalid start_time format: {start_time}")

            if end_time:
                try:
                    dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                    end_timestamp = Timestamp()
                    end_timestamp.FromDatetime(dt)
                except Exception:
                    logger.warning(f"Invalid end_time format: {end_time}")

            request_kwargs: dict[str, Any] = {
                "project_id": project_id,
                "page_size": limit,
                "filter": filter_str,
                "view": trace_v1.ListTracesRequest.ViewType.ROOTSPAN,
            }

            if start_timestamp:
                request_kwargs["start_time"] = start_timestamp
            if end_timestamp:
                request_kwargs["end_time"] = end_timestamp

            response = client.list_traces(
                request=trace_v1.ListTracesRequest(**request_kwargs)
            )

            traces = []
            for trace in response:
                summary: dict[str, Any] = {
                    "trace_id": trace.trace_id,
                    "project_id": trace.project_id,
                }
                if trace.spans:
                    root_span = trace.spans[0]
                    summary["name"] = root_span.name

                    def get_ts_val(ts_proto: Any) -> float:
                        if hasattr(ts_proto, "timestamp"):
                            return cast(float, ts_proto.timestamp())
                        return cast(float, ts_proto.seconds + ts_proto.nanos / 1e9)

                    start_ts = get_ts_val(root_span.start_time)
                    end_ts = get_ts_val(root_span.end_time)
                    duration_ms = (end_ts - start_ts) * 1000

                    if hasattr(root_span.start_time, "isoformat"):
                        summary["start_time"] = root_span.start_time.isoformat()
                    else:
                        summary["start_time"] = datetime.fromtimestamp(
                            start_ts, tz=timezone.utc
                        ).isoformat()
                    summary["duration_ms_str"] = str(round(duration_ms, 2))
                    summary["duration_ms"] = round(duration_ms, 2)
                    labels = root_span.labels or {}
                    summary["status"] = labels.get("/http/status_code", "0")
                    summary["url"] = labels.get("/http/url", "")

                traces.append(summary)
                if len(traces) >= limit:
                    break

            return traces

        except Exception as e:
            error_msg = f"Failed to list traces: {e!s}"
            logger.error(error_msg, exc_info=True)
            return {"error": error_msg}


def _calculate_anomaly_score(
    trace: dict[str, Any],
    mean_latency: float,
    stdev_latency: float,
    has_error: bool = False,
) -> float:
    """Calculate a composite anomaly score for a trace."""
    score = 0.0
    duration = trace.get("duration_ms", 0)
    if stdev_latency > 0:
        z_score = (duration - mean_latency) / stdev_latency
        score += max(0, z_score)
    elif duration > mean_latency:
        score += 3.0

    if has_error:
        score += 5.0

    if mean_latency > 0 and duration > mean_latency * 3:
        score += 2.0
    return score


def validate_trace(trace_data: str | dict[str, Any]) -> dict[str, Any]:
    """Validates trace data for completeness and quality."""
    issues = []
    if isinstance(trace_data, str):
        try:
            data = json.loads(trace_data)
        except json.JSONDecodeError as e:
            return {"valid": False, "issues": [f"Invalid JSON: {e!s}"]}
    else:
        data = trace_data

    if "error" in data:
        return {"valid": False, "issues": [data["error"]]}

    if not data.get("trace_id"):
        issues.append("Missing trace_id")

    spans = data.get("spans", [])
    if not spans:
        issues.append("No spans in trace")
    else:
        for i, span in enumerate(spans):
            if not span.get("span_id"):
                issues.append(f"Span {i} missing span_id")
            if not span.get("name"):
                issues.append(f"Span {i} missing name")
            if not span.get("start_time"):
                issues.append(f"Span {i} missing start_time")
            if not span.get("end_time"):
                issues.append(f"Span {i} missing end_time")
        if len(spans) > 1000:
            issues.append(f"Unusually large trace with {len(spans)} spans")

    duration = data.get("duration_ms", 0)
    if duration <= 0:
        issues.append("Invalid or missing duration")
    elif duration > 300000:
        issues.append(f"Unusually long duration: {duration}ms")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "span_count": len(spans),
        "duration_ms": duration,
    }


@adk_tool
async def find_example_traces(
    project_id: str | None = None,
    prefer_errors: bool = True,
    min_sample_size: int = 20,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Intelligently discovers representative baseline and anomaly traces."""
    try:
        try:
            if not project_id:
                project_id = _get_project_id()
        except ValueError:
            return BaseToolResponse(
                status=ToolStatus.ERROR, error="GOOGLE_CLOUD_PROJECT not set"
            )

        tasks: list[Coroutine[Any, Any, Any]] = []
        slow_filter = TraceFilterBuilder().add_latency(1000).build()
        tasks.append(
            list_traces(
                project_id, limit=20, filter_str=slow_filter, tool_context=tool_context
            )
        )
        tasks.append(list_traces(project_id, limit=50, tool_context=tool_context))
        if prefer_errors:
            tasks.append(
                list_traces(
                    project_id, limit=10, error_only=True, tool_context=tool_context
                )
            )

        results = await asyncio.gather(*tasks)

        # Helper to extract from normalized dict response (from adk_tool)
        def extract(resp: dict[str, Any] | Any) -> list[dict[str, Any]]:
            if isinstance(resp, dict) and "status" in resp:
                return (
                    cast(list[dict[str, Any]], resp.get("result"))
                    if resp.get("status") == "success"
                    and isinstance(resp.get("result"), list)
                    else []
                )
            return cast(list[dict[str, Any]], resp if isinstance(resp, list) else [])

        slow_traces = extract(results[0])
        traces = extract(results[1])
        error_traces = extract(results[2]) if prefer_errors else []

        if not traces:
            # Check if traces_resp exists and has error
            if isinstance(results[1], dict) and results[1].get("status") == "error":
                return BaseToolResponse(
                    status=ToolStatus.ERROR, error=results[1].get("error")
                )
            return BaseToolResponse(
                status=ToolStatus.ERROR, error="No traces found in the last hour."
            )

        # Inject slow traces
        existing_ids = {
            t["trace_id"] for t in traces if isinstance(t, dict) and "trace_id" in t
        }
        for st in slow_traces:
            if isinstance(st, dict) and st.get("trace_id") not in existing_ids:
                traces.append(st)

        # Process error traces
        error_trace_ids = set()
        if prefer_errors:
            for et in error_traces:
                if isinstance(et, dict) and et.get("trace_id"):
                    tid = et["trace_id"]
                    error_trace_ids.add(tid)
                    if tid not in existing_ids:
                        et["has_error"] = True
                        traces.append(et)

        def _calculate_example_traces() -> dict[str, Any]:
            valid_traces = [
                t for t in traces if isinstance(t, dict) and t.get("duration_ms", 0) > 0
            ]
            if not valid_traces:
                return {"error": "No traces with valid duration found."}

            latencies = [t["duration_ms"] for t in valid_traces]
            latencies.sort()
            p50 = statistics.median(latencies)
            mean = statistics.mean(latencies)
            stdev = statistics.stdev(latencies) if len(latencies) > 1 else 0

            for trace in valid_traces:
                has_err = (
                    trace.get("has_error", False)
                    or trace.get("trace_id") in error_trace_ids
                )
                trace["_anomaly_score"] = _calculate_anomaly_score(
                    trace, mean, stdev, has_err
                )
                trace["_has_error"] = has_err

            anomaly = max(valid_traces, key=lambda x: x.get("_anomaly_score", 0))
            baseline_candidates = [
                t for t in valid_traces if not t.get("_has_error", False)
            ]
            if not baseline_candidates:
                baseline_candidates = valid_traces
            baseline = min(
                baseline_candidates, key=lambda x: abs(x["duration_ms"] - p50)
            )

            baseline["_selection_reason"] = f"Closest to P50 ({p50:.1f}ms)"
            anomaly_score = anomaly.get("_anomaly_score", 0)
            if anomaly.get("_has_error"):
                anomaly["_selection_reason"] = f"Error trace ({anomaly_score:.2f})"
            else:
                anomaly["_selection_reason"] = f"Latency anomaly ({anomaly_score:.2f})"

            return {
                "stats": {
                    "count": len(valid_traces),
                    "p50_ms": round(p50, 2),
                    "mean_ms": round(mean, 2),
                    "stdev_ms": round(stdev, 2) if stdev else 0,
                    "error_traces_found": len(error_trace_ids),
                },
                "baseline": baseline,
                "anomaly": anomaly,
                "validation": {
                    "baseline_valid": baseline.get("trace_id") is not None,
                    "anomaly_valid": anomaly.get("trace_id") is not None,
                    "sample_adequate": len(valid_traces) >= 20,
                    "latency_variance_detected": stdev > 0,
                },
                "selection_method": "hybrid_multi_signal",
            }

        results_final = await run_in_threadpool(_calculate_example_traces)
        if "error" in results_final:
            return BaseToolResponse(
                status=ToolStatus.ERROR, error=results_final["error"]
            )

        return BaseToolResponse(status=ToolStatus.SUCCESS, result=results_final)

    except Exception as e:
        logger.error(f"Failed to find example traces: {e!s}", exc_info=True)
        return BaseToolResponse(status=ToolStatus.ERROR, error=str(e))


@adk_tool
async def get_trace_by_url(url: str) -> BaseToolResponse:
    """Parses a Cloud Console URL and fetches the trace details."""
    try:
        from urllib.parse import parse_qs, urlparse

        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        project_id = params.get("project", [None])[0]
        trace_id = None
        if "tid" in params:
            trace_id = params["tid"][0]
        elif "details" in parsed.path:
            parts = parsed.path.split("/")
            for i, part in enumerate(parts):
                if "details" in part and i + 1 < len(parts):
                    trace_id = parts[i + 1]
                    break
        if not trace_id:
            for part in reversed(parsed.path.split("/")):
                if (
                    part
                    and all(c in "0123456789abcdefABCDEF" for c in part)
                    and len(part) >= 32
                ):
                    trace_id = part
                    break
        if not project_id or not trace_id:
            return BaseToolResponse(
                status=ToolStatus.ERROR, error="Could not parse URL"
            )
        return cast(BaseToolResponse, await fetch_trace(trace_id, project_id))
    except Exception as e:
        return BaseToolResponse(status=ToolStatus.ERROR, error=str(e))
