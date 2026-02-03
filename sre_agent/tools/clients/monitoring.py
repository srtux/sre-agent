"""Direct API client for Cloud Monitoring.

This module provides tools for fetching metrics via the Cloud Monitoring API.
It allows the agent to:
- List time series data (raw metrics).
- Execute PromQL queries (Managed Prometheus).

It is used primarily by the `metrics_analyzer` sub-agent to correlate metric spikes
with trace data using Exemplars.
"""

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, cast

from google.api import metric_pb2
from google.auth.transport.requests import AuthorizedSession
from google.cloud import monitoring_v3

from sre_agent.auth import (
    get_credentials_from_tool_context,
    get_current_credentials,
    get_current_project_id,
)
from sre_agent.schema import BaseToolResponse, ToolStatus
from sre_agent.tools.clients.factory import get_monitoring_client
from sre_agent.tools.common import adk_tool
from sre_agent.tools.config import get_tool_config_manager

logger = logging.getLogger(__name__)


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
    from sre_agent.auth import is_guest_mode

    if is_guest_mode():
        from sre_agent.tools.synthetic.provider import SyntheticDataProvider

        return SyntheticDataProvider.list_time_series(
            filter_str=filter_str, minutes_ago=minutes_ago, project_id=project_id
        )

    from fastapi.concurrency import run_in_threadpool

    from sre_agent.tools.mcp.gcp import mcp_list_timeseries

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

    # Prefer MCP if enabled
    config_manager = get_tool_config_manager()
    if config_manager.is_enabled("mcp_list_timeseries"):
        try:
            logger.info("Preferring MCP for list_time_series")
            from typing import cast

            mcp_res = await cast(Any, mcp_list_timeseries)(
                filter=filter_str,
                project_id=project_id,
                minutes_ago=minutes_ago,
                tool_context=tool_context,
            )
            if cast(BaseToolResponse, mcp_res).status == ToolStatus.SUCCESS:
                return cast(BaseToolResponse, mcp_res)
            logger.warning(
                f"MCP list_timeseries failed: {mcp_res.error}. Falling back to direct API."
            )
        except Exception as e:
            logger.warning(
                f"Error calling MCP list_timeseries: {e}. Falling back to direct API.",
                exc_info=True,
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
        if "starts_with" in filter_str.lower() or "has_substring" in filter_str.lower():
            logger.warning(f"Broad filter detected in list_time_series: {filter_str}")

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
                        # datetime is already imported at module level
                        ts_str = datetime.fromtimestamp(
                            ts.seconds + ts.nanos / 1e9, tz=timezone.utc
                        ).isoformat()
                except Exception:
                    ts_str = str(point.interval.end_time)

                # Robust value extraction
                val_proto = point.value
                value: Any = None

                # Optimization: Use protobuf reflection if available (2x faster than str check)
                if hasattr(val_proto, "_pb"):
                    kind = val_proto._pb.WhichOneof("value")
                    if kind == "double_value":
                        value = val_proto.double_value
                    elif kind == "int64_value":
                        value = val_proto.int64_value
                    elif kind == "bool_value":
                        value = val_proto.bool_value
                    elif kind == "string_value":
                        value = val_proto.string_value
                    else:
                        value = 0.0
                elif hasattr(val_proto, "double_value") and "double_value" in str(
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
        return time_series_data
    except Exception as e:
        is_eval = os.getenv("SRE_AGENT_EVAL_MODE", "false").lower() == "true"
        error_str = str(e)
        is_common_error = any(
            code in error_str for code in ["400", "404", "InvalidArgument", "NotFound"]
        )

        if is_eval and is_common_error:
            logger.warning(
                f"Monitoring API error in eval mode (filter: {filter_str}): {error_str}. Returning empty list."
            )
            return []

        # Suggest fixes for common filter errors
        suggestion = ""
        if "400" in error_str and "service" in filter_str and "compute" in filter_str:
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
            "matches more than one metric" in error_str or "starts_with" in filter_str
        ):
            suggestion = (
                ". HINT: 'list_time_series' only supports querying ONE metric at a time. "
                "Your filter uses 'starts_with' or matches multiple metrics. "
                'Please specify an exact metric type (e.g., metric.type="...").'
            )
        elif "400" in error_str and "OR" in error_str and "metric.type" in filter_str:
            suggestion = ". HINT: 'list_time_series' does not support OR between metric types. Specify one metric or use query_promql()."
        elif "400" in error_str and "resource.type" not in filter_str:
            suggestion = ". HINT: You MUST specify 'resource.type' in the filter string for most metrics (e.g. resource.type=\"gce_instance\")."
        elif (
            "400" in error_str
            and "gce_instance" in filter_str
            and ("instance_name" in filter_str or "resource.labels.name" in filter_str)
        ):
            suggestion = ". HINT: GCE instance metrics (resource.type=\"gce_instance\") require 'resource.labels.instance_id', NOT 'instance_name'. You can find the instance ID by listing logs for the resource or using 'gcloud compute instances list'."
        elif "400" in error_str and "gke_container" in filter_str:
            suggestion = ". HINT: For GKE metrics, try using 'resource.type=\"k8s_container\"' instead of 'gke_container'."

        error_msg = f"Failed to list time series: {error_str}{suggestion}"
        logger.error(error_msg, exc_info=True)
        return {"error": error_msg}


@adk_tool
async def list_metric_descriptors(
    filter_str: str | None = None,
    project_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Lists metric descriptors in the project."""
    from sre_agent.auth import is_guest_mode

    if is_guest_mode():
        from sre_agent.tools.synthetic.provider import SyntheticDataProvider

        return SyntheticDataProvider.list_metric_descriptors(
            filter_str=filter_str, project_id=project_id
        )

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
    try:
        client = get_monitoring_client(tool_context=tool_context)
        project_name = f"projects/{project_id}"
        request = {"name": project_name}
        if filter_str:
            request["filter"] = filter_str

        # Cloud Monitoring API restriction: OR cannot be used between metric.type restrictions.
        # We attempt to split simple ORed filters to avoid 400 errors from the API.
        if filter_str and " OR " in filter_str and "metric.type" in filter_str:
            parts = [p.strip() for p in filter_str.split(" OR ")]
            raw_results = []
            seen_types = set()
            for part in parts:
                if not part:
                    continue
                part_request = {"name": project_name, "filter": part}
                # Iterate through results of each part and merge by metric type
                for descriptor in client.list_metric_descriptors(request=part_request):
                    if descriptor.type not in seen_types:
                        raw_results.append(descriptor)
                        seen_types.add(descriptor.type)
            results = raw_results
        else:
            results = list(client.list_metric_descriptors(request=request))

        descriptors = []
        for descriptor in results:
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
        is_eval = os.getenv("SRE_AGENT_EVAL_MODE", "false").lower() == "true"
        error_str = str(e)
        if is_eval and any(
            code in error_str for code in ["400", "404", "InvalidArgument", "NotFound"]
        ):
            logger.warning(
                f"Metric descriptor API error in eval mode (filter: {filter_str}): {error_str}. Returning empty list."
            )
            return []

        suggestion = ""
        if (
            "400" in error_str
            and "OR" in error_str
            and "metric.type" in (filter_str or "")
        ):
            suggestion = ". HINT: Cloud Monitoring does not support OR between metric.type filters. Use multiple searches or a single prefix."

        error_msg = f"Failed to list metric descriptors: {error_str}{suggestion}"
        logger.error(error_msg, exc_info=True)
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
    """Executes a PromQL query using the Cloud Monitoring Prometheus API."""
    from sre_agent.auth import is_guest_mode

    if is_guest_mode():
        from sre_agent.tools.synthetic.provider import SyntheticDataProvider

        return SyntheticDataProvider.query_promql(query=query, project_id=project_id)

    from fastapi.concurrency import run_in_threadpool

    from sre_agent.tools.mcp.gcp import mcp_query_range

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

    # Prefer MCP if enabled
    config_manager = get_tool_config_manager()
    if config_manager.is_enabled("mcp_query_range"):
        try:
            logger.info("Preferring MCP for query_promql")
            from typing import cast

            mcp_res = await cast(Any, mcp_query_range)(
                query=query,
                project_id=project_id,
                start_time=start,
                end_time=end,
                step=step,
                tool_context=tool_context,
            )
            if cast(BaseToolResponse, mcp_res).status == ToolStatus.SUCCESS:
                return cast(BaseToolResponse, mcp_res)
            logger.warning(
                f"MCP query_range failed: {mcp_res.error}. Falling back to direct API."
            )
        except Exception as e:
            logger.warning(
                f"Error calling MCP query_range: {e}. Falling back to direct API.",
                exc_info=True,
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
    try:
        credentials = get_credentials_from_tool_context(tool_context)

        # Fallback to current context
        if not credentials:
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
                error_json = response.json()
                error_msg = "Unknown error"
                if isinstance(error_json, dict):
                    if "error" in error_json and isinstance(error_json["error"], dict):
                        error_msg = error_json["error"].get("message", str(error_json))
                    else:
                        error_msg = error_json.get("message", str(error_json))
                else:
                    error_msg = str(error_json)
                logger.error(f"PromQL API Error ({response.status_code}): {error_msg}")
                raise Exception(error_msg)
            except Exception as e:
                if "raise Exception(error_msg)" in str(e):
                    raise
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
            if "fetch_gcp_metric" in query or "::" in query:
                suggestion += (
                    " Note: Your query looks like MQL. This tool ONLY supports PromQL."
                )
            elif "instance_name" in query and "gce_instance" in query:
                suggestion += " Note: For GCE instance metrics, use 'instance_id' instead of 'instance_name'."
            elif "histogram_quantile" in query:
                suggestion += " Note: histogram_quantile requires sum by (le, ...)."

        error_msg = f"Failed to execute PromQL query: {e!s}{suggestion}"
        logger.error(error_msg, exc_info=True)
        return {"error": error_msg}
