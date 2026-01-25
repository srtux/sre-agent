"""Direct API client for Cloud Monitoring.

This module provides tools for fetching metrics via the Cloud Monitoring API.
It allows the agent to:
- List time series data (raw metrics).
- Execute PromQL queries (Managed Prometheus).

It is used primarily by the `metrics_analyzer` sub-agent to correlate metric spikes
with trace data using Exemplars.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, cast

from google.auth.transport.requests import AuthorizedSession
from google.cloud import monitoring_v3
from opentelemetry.trace import Status, StatusCode

from sre_agent.auth import (
    get_credentials_from_tool_context,
    get_current_credentials,
    get_current_project_id,
)
from sre_agent.schema import BaseToolResponse, ToolStatus
from sre_agent.tools.clients.factory import get_monitoring_client
from sre_agent.tools.common import adk_tool
from sre_agent.tools.common.telemetry import get_tracer

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


@adk_tool
async def list_time_series(
    filter_str: str,
    minutes_ago: int = 60,
    project_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Lists time series data from Google Cloud Monitoring using direct API.

    IMPORTANT: You must use valid combinations of metric and monitored resource labels.
    - For GCE Instances (`gce_instance`), valid labels are `instance_id`, `zone`, `project_id`.
      DO NOT use `service_name` or `service` with GCE metrics.
    - For GKE Containers (`k8s_container`), valid labels are `namespace_name`, `pod_name`, `container_name`, `cluster_name`.
    - To filter by service, use `query_promql` instead with a PromQL query like `metric{service="service-name"}`.

    Args:
        filter_str: The filter string to use.
        minutes_ago: The number of minutes in the past to query.
        project_id: The Google Cloud Project ID. Defaults to current context.
        tool_context: Context object for tool execution.

    Returns:
        Standardized response with list of time series data.

    Example filter_str: 'metric.type="compute.googleapis.com/instance/cpu/utilization" AND resource.labels.instance_id="123456789"'
    """
    from fastapi.concurrency import run_in_threadpool

    if not project_id:
        project_id = get_current_project_id()
        if not project_id:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error="Project ID is required but not provided or found in context.",
            )

    result = await run_in_threadpool(
        _list_time_series_sync, project_id, filter_str, minutes_ago, tool_context
    )
    if isinstance(result, dict) and "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _list_time_series_sync(
    project_id: str,
    filter_str: str,
    minutes_ago: int = 60,
    tool_context: Any = None,
) -> list[dict[str, Any]] | dict[str, Any]:
    """Synchronous implementation of list_time_series."""
    with tracer.start_as_current_span("list_time_series") as span:
        span.set_attribute("gcp.project_id", project_id)
        span.set_attribute("gcp.monitoring.filter", filter_str)
        span.set_attribute("rpc.system", "google_cloud")
        span.set_attribute("rpc.service", "cloud_monitoring")
        span.set_attribute("rpc.method", "list_time_series")

        try:
            client = get_monitoring_client(tool_context=tool_context)
            project_name = f"projects/{project_id}"
            now = time.time()
            seconds = int(now)
            nanos = int((now - seconds) * 10**9)
            interval = monitoring_v3.TimeInterval(
                {
                    "end_time": {"seconds": seconds, "nanos": nanos},
                    "start_time": {
                        "seconds": seconds - (minutes_ago * 60),
                        "nanos": nanos,
                    },
                }
            )
            results = client.list_time_series(
                name=project_name,
                filter=filter_str,
                interval=interval,
                view=monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,  # type: ignore
            )
            time_series_data = []
            for result in results:
                metric_type = getattr(result.metric, "type", "unknown")
                metric_labels = dict(getattr(result.metric, "labels", {}))
                resource_type = getattr(result.resource, "type", "unknown")
                resource_labels = dict(getattr(result.resource, "labels", {}))

                points = []
                for point in result.points:
                    # Robust timestamp extraction
                    try:
                        ts = point.interval.end_time
                        if hasattr(ts, "isoformat"):
                            ts_str = ts.isoformat()
                        else:
                            # Fallback for native protobuf Timestamp
                            from datetime import datetime

                            ts_str = datetime.fromtimestamp(
                                ts.seconds + ts.nanos / 1e9, tz=timezone.utc
                            ).isoformat()
                    except Exception:
                        ts_str = str(point.interval.end_time)

                    # Robust value extraction (TypedValue is a oneof)
                    val_proto = point.value
                    value: Any = None
                    if hasattr(val_proto, "double_value") and "double_value" in str(
                        val_proto
                    ):
                        value = val_proto.double_value
                    elif hasattr(val_proto, "int64_value") and "int64_value" in str(
                        val_proto
                    ):
                        value = val_proto.int64_value
                    elif hasattr(val_proto, "bool_value") and "bool_value" in str(
                        val_proto
                    ):
                        value = val_proto.bool_value
                    elif hasattr(val_proto, "string_value") and "string_value" in str(
                        val_proto
                    ):
                        value = val_proto.string_value
                    else:
                        # Fallback try-all
                        value = (
                            getattr(val_proto, "double_value", None)
                            or getattr(val_proto, "int64_value", None)
                            or 0.0
                        )

                    points.append({"timestamp": ts_str, "value": value})

                time_series_data.append(
                    {
                        "metric": {"type": metric_type, "labels": metric_labels},
                        "resource": {"type": resource_type, "labels": resource_labels},
                        "points": points,
                    }
                )
            span.set_attribute("gcp.monitoring.series_count", len(time_series_data))
            return time_series_data
        except Exception as e:
            span.record_exception(e)
            error_str = str(e)

            # Suggest fixes for common filter errors
            suggestion = ""
            if (
                "400" in error_str
                and "service" in filter_str
                and "compute" in filter_str
            ):
                suggestion = (
                    ". HINT: 'resource.labels.service_name' is NOT valid for GCE metrics. "
                    "Use 'resource.labels.instance_id' or use query_promql() to filter/aggregate by service."
                )

            error_msg = f"Failed to list time series: {error_str}{suggestion}"
            logger.error(error_msg, exc_info=True)
            span.set_status(Status(StatusCode.ERROR, error_msg))
            return {"error": error_msg}


@adk_tool
async def query_promql(
    query: str,
    start: str | None = None,
    end: str | None = None,
    step: str = "60s",
    project_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Executes a PromQL query using the Cloud Monitoring Prometheus API.

    Args:
        query: The PromQL query string.
        start: Start time in RFC3339 format (default: 1 hour ago).
        end: End time in RFC3339 format (default: now).
        step: Query resolution step (default: "60s").
        project_id: The Google Cloud Project ID. Defaults to current context.
        tool_context: Context object for tool execution.

    Returns:
        Standardized response with PromQL query results.
    """
    from fastapi.concurrency import run_in_threadpool

    if not project_id:
        project_id = get_current_project_id()
        if not project_id:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error="Project ID is required but not provided or found in context.",
            )

    result = await run_in_threadpool(
        _query_promql_sync, project_id, query, start, end, step, tool_context
    )
    if isinstance(result, dict) and "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _query_promql_sync(
    project_id: str,
    query: str,
    start: str | None = None,
    end: str | None = None,
    step: str = "60s",
    tool_context: Any = None,
) -> dict[str, Any]:
    """Synchronous implementation of query_promql."""
    with tracer.start_as_current_span("query_promql") as span:
        span.set_attribute("gcp.project_id", project_id)
        span.set_attribute("promql.query", query)

        try:
            credentials = get_credentials_from_tool_context(tool_context)

            # Fallback to current context (ContextVar or Default)
            if not credentials:
                # Use Any to avoid type mismatch
                auth_obj: Any = get_current_credentials()
                if isinstance(auth_obj, tuple):
                    credentials, _ = auth_obj
                else:
                    credentials = auth_obj

            session = AuthorizedSession(credentials)  # type: ignore[no-untyped-call]

            # Default time range if not provided
            if not end:
                end = datetime.now(timezone.utc).isoformat()
            if not start:
                # Default 1 hour ago
                end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
                start_dt = datetime.fromtimestamp(
                    end_dt.timestamp() - 3600, tz=timezone.utc
                )
                start = start_dt.isoformat()

            # Cloud Monitoring Prometheus API endpoint
            url = f"https://monitoring.googleapis.com/v1/projects/{project_id}/location/global/prometheus/api/v1/query_range"

            params = {"query": query, "start": start, "end": end, "step": step}

            response = session.get(url, params=params)
            response.raise_for_status()

            return cast(dict[str, Any], response.json())

        except Exception as e:
            error_msg = f"Failed to execute PromQL query: {e!s}"
            logger.error(error_msg)
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, error_msg))
            return {"error": error_msg}
