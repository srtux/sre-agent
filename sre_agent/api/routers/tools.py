"""Tool configuration, testing, and direct query endpoints.

Provides direct API access to GCP telemetry data for the dashboard explorer.
These endpoints bypass the agent orchestrator for structured queries (logs,
traces, metrics, alerts, SQL) and only route through the LLM for natural
language query translation.
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from sre_agent.api.dependencies import get_tool_context
from sre_agent.auth import is_guest_mode
from sre_agent.exceptions import ToolExecutionError, UserFacingError
from sre_agent.schema import BaseToolResponse
from sre_agent.tools import (
    extract_log_patterns,
    fetch_trace,
    list_alerts,
    list_gcp_projects,
    list_log_entries,
    list_logs,
    list_resource_keys,
    list_time_series,
    list_traces,
    query_promql,
)
from sre_agent.tools.analysis import genui_adapter
from sre_agent.tools.bigquery.client import BigQueryClient
from sre_agent.tools.config import (
    ToolCategory,
    get_tool_config_manager,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tools", tags=["tools"])


def _unwrap_tool_result(result: Any) -> Any:
    """Unwrap BaseToolResponse envelope to raw result dict/list.

    Raises ToolExecutionError if the tool reported an error.
    """
    if isinstance(result, BaseToolResponse):
        if result.error:
            logger.error(f"Tool execution failed: {result.error}")
            raise ToolExecutionError(f"Internal tool error: {result.error}")
        return result.result
    return result


class ToolConfigUpdate(BaseModel):
    """Request model for updating tool configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    enabled: bool


class ToolTestRequest(BaseModel):
    """Request model for testing a tool."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tool_name: str


class LogAnalyzeRequest(BaseModel):
    """Request model for log analysis endpoint."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    filter: str | None = None
    project_id: str | None = None


class TracesQueryRequest(BaseModel):
    """Request model for traces query endpoint."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    filter: str | None = None
    minutes_ago: int = 60
    project_id: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


class MetricsQueryRequest(BaseModel):
    """Request model for metrics query endpoint."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    filter: str = ""
    minutes_ago: int = 60
    project_id: str | None = None


class PromQLQueryRequest(BaseModel):
    """Request model for PromQL query endpoint."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str = ""
    minutes_ago: int = 60
    project_id: str | None = None


class AlertsQueryRequest(BaseModel):
    """Request model for alerts query endpoint."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    filter: str | None = None
    minutes_ago: int | None = None
    project_id: str | None = None


class LogsQueryRequest(BaseModel):
    """Request model for logs query endpoint."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    filter: str | None = None
    minutes_ago: int | None = None
    limit: int = 50
    project_id: str | None = None
    cursor_timestamp: str | None = None
    cursor_insert_id: str | None = None


class LogsHistogramRequest(BaseModel):
    """Request model for logs histogram endpoint."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    filter: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    minutes_ago: int | None = None
    bucket_count: int = Field(default=40, ge=5, le=200)
    project_id: str | None = None


class NLQueryRequest(BaseModel):
    """Request model for natural language query endpoint."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    query: str
    domain: str
    natural_language: bool = True
    minutes_ago: int = 60
    project_id: str | None = None


class BigQueryQueryRequest(BaseModel):
    """Request model for BigQuery SQL execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sql: str
    project_id: str | None = None


# =============================================================================
# TOOL EXECUTION ENDPOINTS
# =============================================================================


@router.get("/trace/{trace_id}")
async def get_trace(trace_id: str, project_id: str | None = None) -> Any:
    """Fetch and summarize a trace."""
    try:
        result = await fetch_trace(
            trace_id=trace_id,
            project_id=project_id,
        )
        raw = _unwrap_tool_result(result)
        return genui_adapter.transform_trace(raw)
    except (HTTPException, UserFacingError):
        raise
    except Exception as e:
        logger.exception("Error fetching trace %s", trace_id)
        raise UserFacingError(f"Internal server error: {e}") from e


@router.post("/traces/query")
async def query_traces_endpoint(payload: TracesQueryRequest) -> Any:
    """Query traces by filter."""
    import asyncio

    try:
        # First get a list of traces matching the filter
        result_list = await list_traces(
            project_id=payload.project_id,
            limit=payload.limit,
            filter_str=payload.filter or "",
        )

        traces_summary = _unwrap_tool_result(result_list)
        if not traces_summary:
            return []

        tasks = []
        for summary in traces_summary:
            if isinstance(summary, dict) and "trace_id" in summary:
                tasks.append(
                    fetch_trace(
                        trace_id=summary["trace_id"], project_id=payload.project_id
                    )
                )

        full_traces_responses = await asyncio.gather(*tasks)

        full_traces = []
        for r in full_traces_responses:
            try:
                raw_trace = _unwrap_tool_result(r)
                if isinstance(raw_trace, dict) and "error" not in raw_trace:
                    full_traces.append(genui_adapter.transform_trace(raw_trace))
            except Exception as e:
                logger.warning("Error fetching full trace details: %s", e)

        return full_traces
    except (HTTPException, UserFacingError):
        raise
    except Exception as e:
        logger.exception("Error querying traces")
        raise UserFacingError(f"Internal server error: {e}") from e


@router.get("/projects/list")
async def list_projects(query: str | None = None) -> Any:
    """List accessible GCP projects using the caller's EUC.

    Returns ``{"projects": [{"project_id": "...", "display_name": "..."}, ...]}``
    """
    try:
        result = await list_gcp_projects(query=query)
        return _unwrap_tool_result(result)
    except (HTTPException, UserFacingError):
        raise
    except Exception as e:
        logger.exception("Error listing projects")
        raise UserFacingError(f"Internal server error: {e}") from e


@router.post("/logs/analyze")
async def analyze_logs(payload: LogAnalyzeRequest) -> Any:
    """Fetch logs and extract patterns."""
    try:
        # 1. Fetch logs from Cloud Logging
        result = await list_log_entries(
            filter_str=payload.filter,
            project_id=payload.project_id,
        )
        entries_data = _unwrap_tool_result(result)

        # entries_data is a dict with "entries" key
        if not isinstance(entries_data, dict):
            entries_data = {
                "entries": entries_data if isinstance(entries_data, list) else []
            }

        log_entries = entries_data.get("entries", [])

        # 2. Extract patterns from the fetched entries
        pattern_result = await extract_log_patterns(
            log_entries=log_entries,
        )
        return _unwrap_tool_result(pattern_result)
    except (HTTPException, UserFacingError):
        raise
    except Exception as e:
        logger.exception("Error analyzing logs")
        raise UserFacingError(f"Internal server error: {e}") from e


@router.post("/metrics/query")
async def query_metrics_endpoint(payload: MetricsQueryRequest) -> Any:
    """Query time series metrics for the explorer.

    Returns data in MetricSeries-compatible format (metric_name, points, labels).
    """
    try:
        result = await list_time_series(
            filter_str=payload.filter,
            minutes_ago=payload.minutes_ago,
            project_id=payload.project_id,
        )
        raw = _unwrap_tool_result(result)
        return genui_adapter.transform_metrics(raw)
    except (HTTPException, UserFacingError):
        raise
    except Exception as e:
        logger.exception("Error querying metrics")
        raise UserFacingError(f"Internal server error: {e}") from e


@router.post("/metrics/promql")
async def query_promql_endpoint(payload: PromQLQueryRequest) -> Any:
    """Execute a PromQL query for the explorer.

    Returns data in MetricSeries-compatible format (metric_name, points, labels).
    """
    try:
        from datetime import datetime, timedelta, timezone

        end = datetime.now(timezone.utc)
        start = end - timedelta(minutes=payload.minutes_ago)

        result = await query_promql(
            query=payload.query,
            start=start.isoformat(),
            end=end.isoformat(),
            project_id=payload.project_id,
        )
        raw = _unwrap_tool_result(result)
        return genui_adapter.transform_metrics(raw)
    except (HTTPException, UserFacingError):
        raise
    except Exception as e:
        logger.exception("Error executing PromQL query")
        raise UserFacingError(f"Internal server error: {e}") from e


@router.post("/alerts/query")
async def query_alerts_endpoint(payload: AlertsQueryRequest) -> Any:
    """Query alerts/incidents for the explorer.

    Returns data in IncidentTimelineData-compatible format.
    """
    try:
        result = await list_alerts(
            project_id=payload.project_id,
            filter_str=payload.filter,
            minutes_ago=payload.minutes_ago,
        )
        raw = _unwrap_tool_result(result)
        return genui_adapter.transform_alerts_to_timeline(raw)
    except (HTTPException, UserFacingError):
        raise
    except Exception as e:
        logger.exception("Error querying alerts")
        raise UserFacingError(f"Internal server error: {e}") from e


# =============================================================================
# DEMO / GUEST MODE HELPERS FOR LOGS
# =============================================================================

# Realistic demo log messages by severity
_DEMO_LOG_MESSAGES: dict[str, list[str | dict[str, Any]]] = {
    "ERROR": [
        {
            "message": "Connection pool exhausted",
            "error_code": "POOL_EXHAUSTED",
            "pool_size": 100,
        },
        {
            "message": "Timeout waiting for upstream response",
            "service": "payment-api",
            "timeout_ms": 30000,
        },
        {
            "message": "Failed to parse response from dependency",
            "error": "JSONDecodeError",
            "status_code": 502,
        },
        {
            "message": "OOM killed container",
            "container": "order-service",
            "memory_limit": "512Mi",
        },
    ],
    "WARNING": [
        "High latency detected: 450ms > threshold 200ms",
        "Retry attempt 2/3 for request to inventory-service",
        "Certificate expiring in 7 days for *.example.com",
        "Disk usage at 85% on persistent volume pv-data-01",
    ],
    "INFO": [
        {
            "message": "Request processed",
            "method": "POST",
            "path": "/api/orders",
            "status": 200,
            "duration_ms": 125,
        },
        {
            "message": "Agent turn completed",
            "turn": 3,
            "tokens_used": 1250,
            "duration_ms": 890,
        },
        {
            "message": "Health check passed",
            "service": "order-service",
            "latency_ms": 12,
        },
        {"message": "Cache hit ratio", "ratio": 0.94, "window": "5m"},
    ],
    "CRITICAL": [
        {
            "message": "Database connection failed",
            "error": "ECONNREFUSED",
            "host": "order-db.internal",
            "port": 5432,
        },
        {
            "message": "Circuit breaker OPEN for payment-service",
            "failures": 15,
            "threshold": 10,
        },
    ],
    "DEBUG": [
        "Cache miss for key: order:12345",
        "Resolved DNS for payment-api.internal in 2ms",
        "GC pause 45ms (young generation)",
    ],
}

_DEMO_RESOURCE_TYPES = [
    "aiplatform.googleapis.com/ReasoningEngine",
    "k8s_container",
    "cloud_run_revision",
]

_DEMO_PODS = [
    "sre-agent-7d8f9c6b5-xk2p4",
    "sre-agent-7d8f9c6b5-abc12",
    "cymbal-assistant-6c7d8e9f0-mn34",
]


def _generate_demo_log_entries(
    *,
    cursor_timestamp: str | None = None,
    cursor_insert_id: str | None = None,
    limit: int = 50,
    minutes_ago: int | None = None,
) -> dict[str, Any]:
    """Generate deterministic demo log entries for guest mode."""
    import hashlib
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    window = timedelta(minutes=minutes_ago or 60)

    # Determine start point for this page
    if cursor_timestamp:
        try:
            page_end = datetime.fromisoformat(cursor_timestamp)
            if page_end.tzinfo is None:
                page_end = page_end.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            page_end = now
    else:
        page_end = now

    # Severity distribution: INFO 60%, WARNING 20%, ERROR 12%, DEBUG 5%, CRITICAL 3%
    sev_weights = (
        ["INFO"] * 60
        + ["WARNING"] * 20
        + ["ERROR"] * 12
        + ["DEBUG"] * 5
        + ["CRITICAL"] * 3
    )

    entries: list[dict[str, Any]] = []
    ts = page_end
    earliest = now - window if not cursor_timestamp else page_end - timedelta(hours=2)

    for i in range(limit):
        # Deterministic pseudo-random spacing (5-45 seconds between entries)
        seed = hashlib.md5(f"demo-log-{ts.isoformat()}-{i}".encode()).hexdigest()
        gap_seconds = 5 + int(seed[:2], 16) % 40
        ts = ts - timedelta(seconds=gap_seconds)

        if ts < earliest:
            break  # No more entries in this window

        # Pick severity deterministically
        sev_idx = int(seed[2:4], 16) % len(sev_weights)
        severity = sev_weights[sev_idx]

        # Pick message
        messages = _DEMO_LOG_MESSAGES[severity]
        msg_idx = int(seed[4:6], 16) % len(messages)
        payload = messages[msg_idx]

        # Pick resource
        res_idx = int(seed[6:8], 16) % len(_DEMO_RESOURCE_TYPES)
        pod_idx = int(seed[8:10], 16) % len(_DEMO_PODS)

        insert_id = f"demo-{seed[:12]}"

        entries.append(
            {
                "insert_id": insert_id,
                "timestamp": ts.isoformat(),
                "severity": severity,
                "payload": payload,
                "resource_type": _DEMO_RESOURCE_TYPES[res_idx],
                "resource_labels": {
                    "project_id": "cymbal-shops-demo",
                    "reasoning_engine_id": "cymbal-assistant" if res_idx == 0 else "",
                    "pod_name": _DEMO_PODS[pod_idx],
                },
                "trace_id": seed[:16] if severity in ("ERROR", "CRITICAL") else None,
                "span_id": seed[16:24] if severity in ("ERROR", "CRITICAL") else None,
                "http_request": None,
            }
        )

    return {"entries": entries}


def _generate_demo_log_histogram(
    *,
    minutes_ago: int | None = None,
    bucket_count: int = 40,
) -> dict[str, Any]:
    """Generate deterministic demo histogram buckets for guest mode."""
    import hashlib
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    window_minutes = minutes_ago or 60
    start = now - timedelta(minutes=window_minutes)
    bucket_seconds = (window_minutes * 60) / bucket_count

    buckets: list[dict[str, Any]] = []
    total_count = 0

    for i in range(bucket_count):
        bucket_start = start + timedelta(seconds=i * bucket_seconds)
        bucket_end = start + timedelta(seconds=(i + 1) * bucket_seconds)
        if i == bucket_count - 1:
            bucket_end = now

        # Deterministic counts per severity
        seed = hashlib.md5(f"demo-histo-{i}-{window_minutes}".encode()).hexdigest()
        info_count = 5 + int(seed[:2], 16) % 20
        warning_count = int(seed[2:4], 16) % 8
        error_count = int(seed[4:6], 16) % 5
        debug_count = int(seed[6:8], 16) % 4
        critical_count = 1 if int(seed[8:10], 16) % 10 == 0 else 0

        bucket_total = (
            info_count + warning_count + error_count + debug_count + critical_count
        )
        total_count += bucket_total

        buckets.append(
            {
                "start": bucket_start.isoformat(),
                "end": bucket_end.isoformat(),
                "debug": debug_count,
                "info": info_count,
                "warning": warning_count,
                "error": error_count,
                "critical": critical_count,
            }
        )

    return {
        "buckets": buckets,
        "total_count": total_count,
        "scanned_entries": total_count,
        "start_time": start.isoformat(),
        "end_time": now.isoformat(),
    }


@router.post("/logs/query")
async def query_logs_endpoint(payload: LogsQueryRequest) -> Any:
    """Fetch raw log entries without pattern extraction (faster for explorer).

    Returns data in LogEntriesData-compatible format.

    Pagination: when ``cursor_timestamp`` is provided the query returns
    entries strictly before that timestamp (optionally refined by
    ``cursor_insert_id`` for same-timestamp ties).  ``minutes_ago`` is
    intentionally ignored for cursor pages so the caller can scroll back
    beyond the initial time window.
    """
    if is_guest_mode():
        return _generate_demo_log_entries(
            cursor_timestamp=payload.cursor_timestamp,
            cursor_insert_id=payload.cursor_insert_id,
            limit=payload.limit,
            minutes_ago=payload.minutes_ago,
        )

    try:
        from datetime import datetime, timedelta, timezone

        filter_str = payload.filter or ""

        if payload.cursor_timestamp:
            # Cursor-based pagination: fetch entries older than the cursor.
            # For the same-timestamp boundary we use insertId to avoid
            # re-returning the last entry already visible in the buffer.
            if payload.cursor_insert_id:
                cursor_filter = (
                    f'(timestamp<"{payload.cursor_timestamp}" OR '
                    f'(timestamp="{payload.cursor_timestamp}" AND '
                    f'insertId>"{payload.cursor_insert_id}"))'
                )
            else:
                cursor_filter = f'timestamp<"{payload.cursor_timestamp}"'
            filter_str = (
                f"({filter_str}) AND {cursor_filter}" if filter_str else cursor_filter
            )
            # Do NOT apply minutes_ago when paginating — the cursor IS the
            # upper bound; applying a lower time-bound would conflict.
        elif payload.minutes_ago is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=payload.minutes_ago)
            time_filter = f'timestamp>="{cutoff.isoformat()}"'
            filter_str = (
                f"{filter_str} AND {time_filter}" if filter_str else time_filter
            )

        result = await list_log_entries(
            filter_str=filter_str,
            project_id=payload.project_id,
            limit=payload.limit,
        )
        raw = _unwrap_tool_result(result)
        return genui_adapter.transform_log_entries(raw)
    except (HTTPException, UserFacingError):
        raise
    except Exception as e:
        logger.exception("Error querying logs")
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {e}"
        ) from e


@router.post("/logs/histogram")
async def query_logs_histogram_endpoint(payload: LogsHistogramRequest) -> Any:
    """Return time-bucketed log counts across the full time range.

    Unlike ``/logs/query`` which returns individual entries (limited to a page
    size), this endpoint scans up to 5 000 entries and returns aggregated
    counts per time bucket, broken down by severity.  This powers the timeline
    histogram in the Logs Explorer.
    """
    if is_guest_mode():
        return _generate_demo_log_histogram(
            minutes_ago=payload.minutes_ago,
            bucket_count=payload.bucket_count,
        )

    try:
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)

        if payload.start_time and payload.end_time:
            start = datetime.fromisoformat(payload.start_time)
            end = datetime.fromisoformat(payload.end_time)
        elif payload.minutes_ago is not None:
            end = now
            start = end - timedelta(minutes=payload.minutes_ago)
        else:
            end = now
            start = end - timedelta(minutes=15)

        # Ensure UTC
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)

        # Build filter with time bounds
        filter_str = payload.filter or ""
        time_filter = (
            f'timestamp>="{start.isoformat()}" AND timestamp<="{end.isoformat()}"'
        )
        filter_str = f"({filter_str}) AND {time_filter}" if filter_str else time_filter

        # Fetch up to 5000 entries for histogram aggregation.
        # We only need timestamps + severity, but the API returns full entries.
        result = await list_log_entries(
            filter_str=filter_str,
            project_id=payload.project_id,
            limit=5000,
        )
        raw = _unwrap_tool_result(result)
        entries = raw.get("entries", []) if isinstance(raw, dict) else []

        # Compute bucket boundaries
        total_duration = (end - start).total_seconds()
        bucket_count = min(payload.bucket_count, max(5, int(total_duration / 60)))
        bucket_seconds = total_duration / bucket_count if bucket_count > 0 else 1

        # Initialize severity count arrays (parallel arrays for O(1) access)
        sev_debug = [0] * bucket_count
        sev_info = [0] * bucket_count
        sev_warning = [0] * bucket_count
        sev_error = [0] * bucket_count
        sev_critical = [0] * bucket_count

        bucket_starts: list[str] = []
        bucket_ends: list[str] = []
        for i in range(bucket_count):
            bucket_start = start + timedelta(seconds=i * bucket_seconds)
            bucket_end = start + timedelta(seconds=(i + 1) * bucket_seconds)
            if i == bucket_count - 1:
                bucket_end = end  # Ensure last bucket covers to the end
            bucket_starts.append(bucket_start.isoformat())
            bucket_ends.append(bucket_end.isoformat())

        # Bucket entries by timestamp and severity
        _SEVERITY_MAP: dict[str, str] = {
            "DEBUG": "debug",
            "DEFAULT": "debug",
            "INFO": "info",
            "NOTICE": "info",
            "WARNING": "warning",
            "ERROR": "error",
            "CRITICAL": "critical",
            "ALERT": "critical",
            "EMERGENCY": "critical",
        }

        for entry in entries:
            ts_str = entry.get("timestamp")
            if not ts_str:
                continue
            try:
                ts = datetime.fromisoformat(ts_str)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue

            # Find bucket index by offset
            offset = (ts - start).total_seconds()
            if offset < 0 or offset > total_duration:
                continue
            idx = int(offset / bucket_seconds)
            if idx >= bucket_count:
                idx = bucket_count - 1

            severity = entry.get("severity", "INFO")
            if isinstance(severity, str):
                sev_key = _SEVERITY_MAP.get(severity.upper(), "info")
            else:
                sev_key = "info"

            if sev_key == "debug":
                sev_debug[idx] += 1
            elif sev_key == "info":
                sev_info[idx] += 1
            elif sev_key == "warning":
                sev_warning[idx] += 1
            elif sev_key == "error":
                sev_error[idx] += 1
            else:
                sev_critical[idx] += 1

        # Build response buckets
        buckets: list[dict[str, Any]] = []
        total_count = 0
        for i in range(bucket_count):
            d = sev_debug[i]
            inf = sev_info[i]
            w = sev_warning[i]
            e = sev_error[i]
            c = sev_critical[i]
            total_count += d + inf + w + e + c
            buckets.append(
                {
                    "start": bucket_starts[i],
                    "end": bucket_ends[i],
                    "debug": d,
                    "info": inf,
                    "warning": w,
                    "error": e,
                    "critical": c,
                }
            )

        return {
            "buckets": buckets,
            "total_count": total_count,
            "scanned_entries": len(entries),
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        }
    except (HTTPException, UserFacingError):
        raise
    except Exception as e:
        logger.exception("Error building log histogram")
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {e}"
        ) from e


@router.get("/logs/names")
async def get_logs_names(project_id: str | None = None) -> Any:
    """Lists the names of logs available in the Google Cloud Project."""
    try:
        result = await list_logs(project_id=project_id)
        raw = _unwrap_tool_result(result)
        return raw
    except (HTTPException, UserFacingError):
        raise
    except Exception as e:
        logger.exception("Error getting log names")
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {e}"
        ) from e


@router.get("/logs/resource_keys")
async def get_logs_resource_keys(project_id: str | None = None) -> Any:
    """Lists the monitored resource descriptors available in Cloud Logging."""
    try:
        result = await list_resource_keys(project_id=project_id)
        raw = _unwrap_tool_result(result)
        return raw
    except (HTTPException, UserFacingError):
        raise
    except Exception as e:
        logger.exception("Error getting resource keys")
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {e}"
        ) from e


@router.post("/bigquery/query")
async def query_bigquery_endpoint(payload: BigQueryQueryRequest) -> Any:
    """Execute a BigQuery SQL query and return tabular results.

    Returns data in BigQueryQueryResponse-compatible format (columns, rows).
    """
    if is_guest_mode():
        from sre_agent.tools.synthetic.demo_bigquery import execute_demo_query

        return execute_demo_query(payload.sql)

    try:
        ctx = await get_tool_context()
        client = BigQueryClient(project_id=payload.project_id, tool_context=ctx)
        rows = await client.execute_query(payload.sql)
        # Transform rows to columns + rows list format
        columns = list(rows[0].keys()) if rows else []
        return {"columns": columns, "rows": rows}
    except Exception as e:
        logger.exception("Error querying BigQuery")
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {e}"
        ) from e


@router.get("/bigquery/datasets")
async def list_bigquery_datasets(project_id: str | None = None) -> Any:
    """List datasets in the BigQuery project."""
    if is_guest_mode():
        from sre_agent.tools.synthetic.demo_bigquery import get_demo_datasets

        return get_demo_datasets()

    try:
        ctx = await get_tool_context()
        client = BigQueryClient(project_id=project_id, tool_context=ctx)
        datasets = await client.list_datasets()
        return {"datasets": datasets}
    except Exception as e:
        logger.exception("Error listing BigQuery datasets")
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {e}"
        ) from e


@router.get("/bigquery/datasets/{dataset_id}/tables")
async def list_bigquery_tables(dataset_id: str, project_id: str | None = None) -> Any:
    """List tables in a BigQuery dataset."""
    if is_guest_mode():
        from sre_agent.tools.synthetic.demo_bigquery import get_demo_tables

        return get_demo_tables(dataset_id)

    try:
        ctx = await get_tool_context()
        client = BigQueryClient(project_id=project_id, tool_context=ctx)
        tables = await client.list_tables(dataset_id)
        return {"tables": tables}
    except Exception as e:
        logger.exception(f"Error listing tables for dataset {dataset_id}")
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {e}"
        ) from e


@router.get("/bigquery/datasets/{dataset_id}/tables/{table_id}/schema")
async def get_bigquery_table_schema(
    dataset_id: str, table_id: str, project_id: str | None = None
) -> Any:
    """Get the schema of a BigQuery table."""
    if is_guest_mode():
        from sre_agent.tools.synthetic.demo_bigquery import get_demo_table_schema

        return get_demo_table_schema(dataset_id, table_id)

    try:
        ctx = await get_tool_context()
        client = BigQueryClient(project_id=project_id, tool_context=ctx)
        schema = await client.get_table_schema(dataset_id, table_id)
        return {"schema": schema}
    except Exception as e:
        logger.exception(f"Error getting schema for table {dataset_id}.{table_id}")
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {e}"
        ) from e


@router.get(
    "/bigquery/datasets/{dataset_id}/tables/{table_id}/columns/{column_name}/json-keys"
)
async def get_bigquery_json_keys(
    dataset_id: str,
    table_id: str,
    column_name: str,
    project_id: str | None = None,
) -> Any:
    """Infer JSON keys for a BigQuery JSON column."""
    if is_guest_mode():
        from sre_agent.tools.synthetic.demo_bigquery import get_demo_json_keys

        return get_demo_json_keys(dataset_id, table_id, column_name)

    try:
        ctx = await get_tool_context()
        client = BigQueryClient(project_id=project_id, tool_context=ctx)
        keys = await client.get_json_keys(dataset_id, table_id, column_name)
        return {"keys": keys}
    except Exception as e:
        logger.exception(
            f"Error getting JSON keys for {dataset_id}.{table_id}.{column_name}"
        )
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {e}"
        ) from e


# =============================================================================
# NATURAL LANGUAGE QUERY ENDPOINT
# =============================================================================

# Domain → structured query translation prompts
_NL_DOMAIN_PROMPTS: dict[str, str] = {
    "traces": (
        "Translate the following natural language request into a Cloud Trace "
        "filter expression. Return ONLY valid JSON with keys: "
        '"filter" (string, Cloud Trace filter syntax), '
        '"minutes_ago" (integer, time window).\n'
        "User request: {query}"
    ),
    "logs": (
        "Translate the following natural language request into a Cloud Logging "
        "filter expression. Return ONLY valid JSON with keys: "
        '"filter" (string, Cloud Logging filter syntax), '
        '"limit" (integer, max entries to return).\n'
        "User request: {query}"
    ),
    "metrics": (
        "Translate the following natural language request into a Cloud Monitoring "
        "ListTimeSeries filter or PromQL query. Return ONLY valid JSON with keys: "
        '"language" (string, "mql" or "promql"), '
        '"filter" or "query" (string, the filter/query expression), '
        '"minutes_ago" (integer, time window).\n'
        "User request: {query}"
    ),
    "bigquery": (
        "Translate the following natural language request into a BigQuery SQL "
        "query. Return ONLY valid JSON with key: "
        '"sql" (string, the SQL query).\n'
        "User request: {query}"
    ),
}


@router.post("/nl/query")
async def query_natural_language_endpoint(payload: NLQueryRequest) -> Any:
    """Translate a natural language query into a structured query and execute it.

    Uses the LLM to translate the user's natural language request into the
    appropriate structured query language (Cloud Trace filter, Cloud Logging
    filter, MQL/PromQL, or BigQuery SQL), then executes the structured query
    directly against the GCP API.

    This is the only explorer endpoint that involves the LLM. All other
    explorer endpoints execute structured queries directly.
    """
    if payload.domain not in _NL_DOMAIN_PROMPTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported domain: {payload.domain}. "
            f"Valid domains: {list(_NL_DOMAIN_PROMPTS.keys())}",
        )

    if is_guest_mode() and payload.domain == "bigquery":
        from sre_agent.tools.synthetic.demo_bigquery import execute_demo_query

        # In guest mode, skip LLM translation and return a sample query result.
        sample_sql = "SELECT name, COUNT(*) as cnt FROM traces._AllSpans GROUP BY name ORDER BY cnt DESC LIMIT 20"
        return execute_demo_query(sample_sql)

    try:
        # 1. Translate NL → structured query via LLM
        structured = await _translate_nl_query(
            payload.query, payload.domain, payload.project_id
        )

        # 2. Execute the structured query using the appropriate direct endpoint
        return await _execute_structured_query(
            domain=payload.domain,
            structured=structured,
            project_id=payload.project_id,
            minutes_ago=payload.minutes_ago,
        )
    except (HTTPException, UserFacingError):
        raise
    except Exception as e:
        logger.exception("Error processing natural language query")
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {e}"
        ) from e


async def _translate_nl_query(
    query: str, domain: str, project_id: str | None
) -> dict[str, Any]:
    """Use LLM to translate natural language into a structured query."""
    from google import genai

    from sre_agent.model_config import get_model_name

    prompt_template = _NL_DOMAIN_PROMPTS[domain]
    prompt = prompt_template.format(query=query)
    if project_id:
        prompt += f"\nGCP Project: {project_id}"

    client = genai.Client()
    response = await client.aio.models.generate_content(
        model=get_model_name("fast"),
        contents=prompt,
    )

    text = response.text or ""
    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        return json.loads(text)  # type: ignore[no-any-return]
    except json.JSONDecodeError as e:
        logger.warning("LLM returned non-JSON for NL query: %s", text[:200])
        raise HTTPException(
            status_code=502,
            detail=f"Failed to parse LLM translation: {e}",
        ) from e


async def _execute_structured_query(
    domain: str,
    structured: dict[str, Any],
    project_id: str | None,
    minutes_ago: int,
) -> Any:
    """Execute a structured query produced by the NL translator."""
    if domain == "traces":
        filter_str = structured.get("filter", "")
        mins = structured.get("minutes_ago", minutes_ago)
        return await query_traces_endpoint(
            TracesQueryRequest(
                filter=filter_str,
                minutes_ago=mins,
                project_id=project_id,
            )
        )
    elif domain == "logs":
        filter_str = structured.get("filter", "")
        limit = structured.get("limit", 50)
        return await query_logs_endpoint(
            LogsQueryRequest(
                filter=filter_str,
                limit=limit,
                project_id=project_id,
            )
        )
    elif domain == "metrics":
        language = structured.get("language", "mql")
        mins = structured.get("minutes_ago", minutes_ago)
        if language == "promql":
            return await query_promql_endpoint(
                PromQLQueryRequest(
                    query=structured.get("query", ""),
                    minutes_ago=mins,
                    project_id=project_id,
                )
            )
        else:
            return await query_metrics_endpoint(
                MetricsQueryRequest(
                    filter=structured.get("filter", ""),
                    minutes_ago=mins,
                    project_id=project_id,
                )
            )
    elif domain == "bigquery":
        sql = structured.get("sql", "")
        if not sql:
            raise HTTPException(
                status_code=400, detail="LLM did not produce a SQL query"
            )
        return await query_bigquery_endpoint(
            BigQueryQueryRequest(sql=sql, project_id=project_id)
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown domain: {domain}")


# =============================================================================
# TOOL CONFIGURATION ENDPOINTS
# =============================================================================


@router.get("/config")
async def get_tool_configs(
    category: str | None = None,
    enabled_only: bool = False,
) -> Any:
    """Get all tool configurations.

    Args:
        category: Optional filter by category (api_client, mcp, analysis, etc.)
        enabled_only: If True, only return enabled tools

    Returns:
        List of tool configurations grouped by category.
    """
    try:
        manager = get_tool_config_manager()
        configs = manager.get_all_configs()

        # Filter by category if specified
        if category:
            try:
                cat = ToolCategory(category)
                configs = [c for c in configs if c.category == cat]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid category: {category}. "
                    f"Valid categories: {[c.value for c in ToolCategory]}",
                ) from None

        # Filter by enabled status if specified
        if enabled_only:
            configs = [c for c in configs if c.enabled]

        # Group by category for better UI organization
        grouped: dict[str, list[dict[str, Any]]] = {}
        for config in configs:
            cat_name = config.category.value
            if cat_name not in grouped:
                grouped[cat_name] = []
            grouped[cat_name].append(config.to_dict())

        # Calculate summary stats
        total = len(configs)
        enabled = len([c for c in configs if c.enabled])
        testable = len([c for c in configs if c.testable])

        return {
            "tools": grouped,
            "summary": {
                "total": total,
                "enabled": enabled,
                "disabled": total - enabled,
                "testable": testable,
            },
            "categories": [c.value for c in ToolCategory],
        }
    except (HTTPException, UserFacingError):
        raise
    except Exception as e:
        logger.error(f"Error getting tool configs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/config/{tool_name}")
async def get_tool_config(tool_name: str) -> Any:
    """Get configuration for a specific tool."""
    try:
        manager = get_tool_config_manager()
        config = manager.get_config(tool_name)

        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found",
            )

        return config.to_dict()
    except (HTTPException, UserFacingError):
        raise
    except Exception as e:
        logger.error(f"Error getting tool config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.put("/config/{tool_name}")
async def update_tool_config(tool_name: str, update: ToolConfigUpdate) -> Any:
    """Update configuration for a specific tool (enable/disable)."""
    try:
        manager = get_tool_config_manager()
        config = manager.get_config(tool_name)

        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found",
            )

        success = manager.set_enabled(tool_name, update.enabled)

        if not success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update tool '{tool_name}'",
            )

        # Return updated config
        updated_config = manager.get_config(tool_name)
        return {
            "message": f"Tool '{tool_name}' "
            f"{'enabled' if update.enabled else 'disabled'} successfully",
            "tool": updated_config.to_dict() if updated_config else None,
        }
    except (HTTPException, UserFacingError):
        raise
    except Exception as e:
        logger.error(f"Error updating tool config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/config/bulk")
async def bulk_update_tool_configs(updates: dict[str, bool]) -> Any:
    """Bulk update tool configurations.

    Args:
        updates: Dictionary of tool_name -> enabled (bool)

    Returns:
        Summary of updates performed.
    """
    try:
        manager = get_tool_config_manager()
        results: dict[str, Any] = {
            "updated": {},
            "failed": {},
            "not_found": [],
        }

        for tool_name, enabled in updates.items():
            config = manager.get_config(tool_name)
            if not config:
                results["not_found"].append(tool_name)
                continue

            success = manager.set_enabled(tool_name, enabled)
            if success:
                results["updated"][tool_name] = enabled
            else:
                results["failed"][tool_name] = "Update failed"

        return {
            "message": f"Bulk update completed: {len(results['updated'])} updated, "
            f"{len(results['failed'])} failed, {len(results['not_found'])} not found",
            "results": results,
        }
    except Exception:
        logger.error("Error in bulk update", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from None


# =============================================================================
# TOOL TESTING ENDPOINTS
# =============================================================================


@router.post("/test/{tool_name}")
async def test_tool(tool_name: str) -> Any:
    """Test a specific tool's connectivity/functionality.

    This performs a lightweight connectivity test to verify the tool is working.
    """
    try:
        manager = get_tool_config_manager()
        config = manager.get_config(tool_name)

        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found",
            )

        if not config.testable:
            return {
                "tool_name": tool_name,
                "testable": False,
                "message": f"Tool '{tool_name}' is not testable",
            }

        result = await manager.test_tool(tool_name)

        return {
            "tool_name": tool_name,
            "testable": True,
            "result": {
                "status": result.status.value,
                "message": result.message,
                "latency_ms": result.latency_ms,
                "timestamp": result.timestamp,
                "details": result.details,
            },
        }
    except (HTTPException, UserFacingError):
        raise
    except Exception as e:
        logger.error(f"Error testing tool: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/test-all")
async def test_all_tools(category: str | None = None) -> Any:
    """Test all testable tools and return results.

    Args:
        category: Optional filter to test only tools in a specific category
    """
    try:
        manager = get_tool_config_manager()
        configs = manager.get_all_configs()

        # Filter by category if specified
        if category:
            try:
                cat = ToolCategory(category)
                configs = [c for c in configs if c.category == cat]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid category: {category}",
                ) from None

        # Filter to testable tools only
        testable_configs = [c for c in configs if c.testable]

        results = []
        for config in testable_configs:
            try:
                result = await manager.test_tool(config.name)
                results.append(
                    {
                        "tool_name": config.name,
                        "category": config.category.value,
                        "status": result.status.value,
                        "message": result.message,
                        "latency_ms": result.latency_ms,
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "tool_name": config.name,
                        "category": config.category.value,
                        "status": "error",
                        "message": str(e),
                        "latency_ms": None,
                    }
                )

        # Calculate summary
        passed = len([r for r in results if r["status"] == "success"])
        failed = len([r for r in results if r["status"] != "success"])

        return {
            "summary": {
                "total": len(results),
                "passed": passed,
                "failed": failed,
            },
            "results": results,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing all tools: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e
