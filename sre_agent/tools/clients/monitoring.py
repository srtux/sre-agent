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

from google.api import metric_pb2
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

    CRITICAL RULES:
    1.  **EXACT Metric Type**: You MUST specify EXACTLY ONE metric type using the equality operator (e.g., `metric.type="my.metric/type"`).
    2.  **NO `starts_with` for metrics**: You CANNOT use `starts_with` or regex on `metric.type` for time series queries. If you need to search for metrics, use `list_metric_descriptors` first.
    3.  **Monitored Resource**: You MUST specify `resource.type` for most queries (e.g., `resource.type="gce_instance"`).

    Common monitored resource labels:
    - GCE Instances (`gce_instance`): `instance_id`, `zone`, `project_id`.
    - GKE Containers (`k8s_container`): `namespace_name`, `pod_name`, `container_name`, `cluster_name`.

    To filter by arbitrary service labels, use `query_promql` instead.

    Args:
        filter_str: The filter string to use. Exactly one metric type required.
        minutes_ago: The number of minutes in the past to query.
        project_id: The Google Cloud Project ID. Defaults to current context.
        tool_context: Context object for tool execution.

    Returns:
        Standardized response with list of time series data.

    Example filter_str: 'metric.type="compute.googleapis.com/instance/cpu/utilization" AND resource.type="gce_instance" AND resource.labels.instance_id="123456789"'
    """
    from fastapi.concurrency import run_in_threadpool

    if not project_id:
        project_id = get_current_project_id()
        if not project_id:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error=(
                    "Project ID is required but not provided or found in context. "
                    "HINT: If you are using the Agent Engine playground, please pass the project ID "
                    "in request (e.g., 'Analyze logs in project my-project-id') or use the project selector. "
                    "Local users should set the GOOGLE_CLOUD_PROJECT environment variable."
                ),
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
            # Detection for broad filters that cause common 400 errors
            if (
                "starts_with" in filter_str.lower()
                or "has_substring" in filter_str.lower()
            ):
                logger.warning(
                    f"Broad filter detected in list_time_series: {filter_str}"
                )
                # We don't block it, but we prepare for the error

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
            elif "404" in error_str and "kubernetes.io" in filter_str:
                suggestion = (
                    ". HINT: For GKE container CPU usage, use 'kubernetes.io/container/cpu/core_usage_time' "
                    "instead of 'usage_time'. For memory use 'kubernetes.io/container/memory/used_bytes'."
                )
            elif (
                "404" in error_str
                and "compute.googleapis.com" in filter_str
                and "memory" in filter_str
            ):
                suggestion = (
                    ". HINT: Direct GCE infrastructure metrics for memory are limited. "
                    "If the Ops Agent is installed, use 'guest/memory/bytes_used'. "
                    "Otherwise, use 'compute.googleapis.com/instance/memory/balloon/ram_used'."
                )
            elif "400" in error_str and (
                "matches more than one metric" in error_str
                or "starts_with" in filter_str
            ):
                suggestion = (
                    ". HINT: 'list_time_series' only supports querying ONE metric at a time. "
                    "Your filter uses 'starts_with' or matches multiple metrics. "
                    'Please specify an exact metric type (e.g., metric.type="...").'
                )
            elif "400" in error_str and "resource.type" not in filter_str:
                suggestion = ". HINT: You MUST specify 'resource.type' in the filter string for most metrics (e.g. resource.type=\"gce_instance\")."
            elif (
                "400" in error_str
                and "gce_instance" in filter_str
                and (
                    "instance_name" in filter_str
                    or "resource.labels.name" in filter_str
                )
            ):
                suggestion = ". HINT: GCE instance metrics (resource.type=\"gce_instance\") require 'resource.labels.instance_id', NOT 'instance_name'. You can find the instance ID by listing logs for the resource or using 'gcloud compute instances list'."
            elif "400" in error_str and "gke_container" in filter_str:
                suggestion = ". HINT: For GKE metrics, try using 'resource.type=\"k8s_container\"' instead of 'gke_container'."

            error_msg = f"Failed to list time series: {error_str}{suggestion}"
            logger.error(error_msg, exc_info=True)
            span.set_status(Status(StatusCode.ERROR, error_msg))
            return {"error": error_msg}


@adk_tool
async def list_metric_descriptors(
    filter_str: str | None = None,
    project_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Lists metric descriptors in the project.

    Use this tool to discover available metrics or verify if a metric exists.

    Args:
        filter_str: Optional filter for metric descriptors (e.g., 'metric.type = starts_with("kubernetes.io")').
        project_id: The Google Cloud Project ID. Defaults to current context.
        tool_context: Context object for tool execution.

    Returns:
        Standardized response with list of metric descriptors.
    """
    from fastapi.concurrency import run_in_threadpool

    if not project_id:
        project_id = get_current_project_id()
        if not project_id:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error=(
                    "Project ID is required but not provided or found in context. "
                    "HINT: If you are using the Agent Engine playground, please pass the project ID "
                    "in request (e.g., 'Analyze logs in project my-project-id') or use the project selector. "
                    "Local users should set the GOOGLE_CLOUD_PROJECT environment variable."
                ),
            )

    result = await run_in_threadpool(
        _list_metric_descriptors_sync, project_id, filter_str, tool_context
    )
    if isinstance(result, dict) and "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _list_metric_descriptors_sync(
    project_id: str,
    filter_str: str | None = None,
    tool_context: Any = None,
) -> list[dict[str, Any]] | dict[str, Any]:
    """Synchronous implementation of list_metric_descriptors."""
    with tracer.start_as_current_span("list_metric_descriptors") as span:
        span.set_attribute("gcp.project_id", project_id)
        if filter_str:
            span.set_attribute("gcp.monitoring.filter", filter_str)

        try:
            client = get_monitoring_client(tool_context=tool_context)
            project_name = f"projects/{project_id}"
            request = {"name": project_name}
            if filter_str:
                request["filter"] = filter_str

            results = client.list_metric_descriptors(request=request)

            descriptors = []
            for descriptor in results:
                # Use robust enum access as these can be ints depending on protobuf version
                kind_name = str(descriptor.metric_kind)
                if hasattr(descriptor.metric_kind, "name"):
                    kind_name = descriptor.metric_kind.name
                else:
                    try:
                        kind_name = metric_pb2.MetricDescriptor.MetricKind.Name(
                            descriptor.metric_kind
                        )
                    except (ValueError, AttributeError):
                        pass

                type_name = str(descriptor.value_type)
                if hasattr(descriptor.value_type, "name"):
                    type_name = descriptor.value_type.name
                else:
                    try:
                        type_name = metric_pb2.MetricDescriptor.ValueType.Name(
                            descriptor.value_type
                        )
                    except (ValueError, AttributeError):
                        pass

                descriptors.append(
                    {
                        "name": descriptor.name,
                        "type": descriptor.type,
                        "metric_kind": kind_name,
                        "value_type": type_name,
                        "unit": descriptor.unit,
                        "description": descriptor.description,
                        "display_name": descriptor.display_name,
                        "labels": [
                            {"key": label.key, "description": label.description}
                            for label in descriptor.labels
                        ],
                    }
                )
            return descriptors
        except Exception as e:
            error_msg = f"Failed to list metric descriptors: {e!s}"
            logger.error(error_msg, exc_info=True)
            span.record_exception(e)
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
                error=(
                    "Project ID is required but not provided or found in context. "
                    "HINT: If you are using the Agent Engine playground, please pass the project ID "
                    "in request (e.g., 'Analyze logs in project my-project-id') or use the project selector. "
                    "Local users should set the GOOGLE_CLOUD_PROJECT environment variable."
                ),
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
            if response.status_code != 200:
                try:
                    error_details = response.json()
                    error_msg = error_details.get("error", {}).get(
                        "message", str(error_details)
                    )
                    logger.error(
                        f"PromQL API Error ({response.status_code}): {error_msg}"
                    )
                    raise Exception(error_msg)
                except Exception:
                    response.raise_for_status()

            return cast(dict[str, Any], response.json())

        except Exception as e:
            suggestion = ""
            if "400" in str(e):
                suggestion = (
                    ". HINT: Your PromQL query might be invalid or unsupported. "
                    "Ensure you use valid label matchers and that the metric exists. "
                    "Try a simpler query first like '{__name__=\"metric_name\"}'."
                )
                if (
                    "fetch_gcp_metric" in query
                    or "fetch gce_instance" in query
                    or "::" in query
                ):
                    suggestion += " Note: Your query looks like MQL (Monitoring Query Language). This tool ONLY supports PromQL. Convert your query to PromQL, for example: 'compute_googleapis_com:instance_cpu_utilization'."
                elif "instance_name" in query and "gce_instance" in query:
                    suggestion += " Note: For GCE instance metrics in PromQL, you usually need to filter by 'instance_id' instead of 'instance_name' when using resource labels (e.g., '{instance_id=\"...\"}')."
                elif "histogram_quantile" in query:
                    suggestion += " Note: histogram_quantile requires exactly two arguments: a scalar (e.g. 0.99) and a vector of buckets. Ensure your aggregation (sum by) includes the 'le' label, as in 'sum by (le, ...) (rate(...))'."
                elif "__name__" in query:
                    suggestion += " Note: When using '__name__' with regex, ensure the regex is valid and matches actual metrics in your project. Try a simpler query like '{__name__=\"metric_name\"}' first to verify the metric exists."
                elif "by (" in query:
                    suggestion += " Note: If you are aggregating by labels (e.g., 'sum by (label_name)'), ensure those labels exist on the underlying metric. Use a raw query like 'metric_name' to see available labels."

            error_msg = f"Failed to execute PromQL query: {e!s}{suggestion}"
            logger.error(error_msg, exc_info=True)
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, error_msg))
            return {"error": error_msg}
