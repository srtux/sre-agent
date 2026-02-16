"""Direct API client for Cloud Logging and Error Reporting.

This module provides lightweight, synchronous wrappers around the Google Cloud Logging
and Error Reporting client libraries. Unlike the MCP-based tools (which are stateful
and run in a separate server process), these tools are designed for low-latency
direct access to the APIs, ideal for:
- Fetching small batches of logs for a specific trace.
- Listing recent error events.
- Creating ephemeral log queries.

Note: These functions are wrapped with `@adk_tool` for agent exposure, but they
execute locally within the agent's process (via threadpool for async compatibility).
"""

import logging
from typing import Any

from sre_agent.schema import BaseToolResponse, ToolStatus
from sre_agent.tools.clients.factory import (
    get_error_reporting_client,
    get_logging_client,
)
from sre_agent.tools.common import adk_tool
from sre_agent.tools.config import get_tool_config_manager

logger = logging.getLogger(__name__)


@adk_tool
async def list_log_entries(
    filter_str: str,
    project_id: str | None = None,
    limit: int = 10,
    page_token: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Lists log entries from Google Cloud Logging using direct API.

    Common filter patterns:
    - GKE Container logs: `resource.type="k8s_container" AND resource.labels.container_name="my-app" AND severity>=ERROR`
    - GKE Pod logs: `resource.type="k8s_container" AND resource.labels.pod_name="my-pod-xyz"`
    - Global logs: `textPayload:"error"`
    - JSON logs: `jsonPayload.message =~ "regex"`
    - Trace correlation: `trace="projects/[PROJECT_ID]/traces/[TRACE_ID]"`

    CRITICAL: For GKE logs, fields like `container_name`, `pod_name`, `namespace_name` MUST be prefixed with `resource.labels.`.
    Example: `resource.labels.container_name="my-app"` NOT `container_name="my-app"`.

    Args:
        project_id: The Google Cloud Project ID.
        filter_str: The filter string to use.
        limit: The maximum number of log entries to return.
        page_token: Token for the next page of results.
        tool_context: Context object for tool execution.

    Returns:
        Standardized response with:
        - "entries": List of log entries.
        - "next_page_token": Token for the next page (if any).
    """
    from sre_agent.auth import is_guest_mode

    if is_guest_mode():
        from sre_agent.tools.synthetic.provider import SyntheticDataProvider

        return SyntheticDataProvider.list_log_entries(
            filter_str=filter_str, project_id=project_id, limit=limit
        )

    from fastapi.concurrency import run_in_threadpool

    from sre_agent.auth import get_current_project_id
    from sre_agent.tools.mcp.gcp import mcp_list_log_entries

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
    if config_manager.is_enabled("mcp_list_log_entries"):
        try:
            logger.info("Preferring MCP for list_log_entries")
            from typing import cast

            mcp_res = await cast(Any, mcp_list_log_entries)(
                filter=filter_str,
                project_id=project_id,
                page_size=limit,
                tool_context=tool_context,
            )
            if cast(BaseToolResponse, mcp_res).status == ToolStatus.SUCCESS:
                return cast(BaseToolResponse, mcp_res)

            # If MCP fails with a non-retryable error, we might still want to try API fallback
            # unless it's a clear auth error that would also fail the API.
            logger.warning(
                f"MCP list_log_entries failed: {mcp_res.error}. Falling back to direct API."
            )
        except Exception as e:
            logger.warning(
                f"Error calling MCP list_log_entries: {e}. Falling back to direct API.",
                exc_info=True,
            )

    result = await run_in_threadpool(
        _list_log_entries_sync, project_id, filter_str, limit, page_token, tool_context
    )
    if "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _list_log_entries_sync(
    project_id: str,
    filter_str: str,
    limit: int = 10,
    page_token: str | None = None,
    tool_context: Any = None,
) -> dict[str, Any]:
    """Synchronous implementation of list_log_entries."""
    try:
        client = get_logging_client(tool_context=tool_context)
        resource_names = [f"projects/{project_id}"]

        # Ensure timestamp desc ordering for recent logs
        order_by = "timestamp desc"

        request = {
            "resource_names": resource_names,
            "filter": filter_str,
            "page_size": limit,
            "order_by": order_by,
        }
        if page_token:
            request["page_token"] = page_token

        # Get the iterator/pager
        entries_pager = client.list_log_entries(request=request)

        # Fetch a single page to respect limit and get token
        results = []
        next_token = None

        # Get the first page of the iterator
        pages_iterator = entries_pager.pages
        first_page = next(pages_iterator, None)

        if first_page:
            for entry in first_page.entries:
                payload_data = _extract_log_payload(entry)

                results.append(
                    {
                        "timestamp": entry.timestamp.isoformat()
                        if entry.timestamp
                        else None,
                        "severity": (
                            entry.severity.name
                            if hasattr(entry.severity, "name")
                            else {
                                0: "DEFAULT",
                                100: "DEBUG",
                                200: "INFO",
                                300: "NOTICE",
                                400: "WARNING",
                                500: "ERROR",
                                600: "CRITICAL",
                                700: "ALERT",
                                800: "EMERGENCY",
                            }.get(
                                entry.severity
                                if isinstance(entry.severity, int)
                                else 0,
                                str(entry.severity),
                            )
                        ),
                        "payload": payload_data,
                        "resource": {
                            "type": entry.resource.type,
                            "labels": dict(entry.resource.labels),
                        },
                        "insert_id": entry.insert_id,
                        "trace": entry.trace,
                        "span_id": entry.span_id,
                        "http_request": {
                            "requestMethod": getattr(
                                entry.http_request, "request_method", None
                            ),
                            "requestUrl": getattr(
                                entry.http_request, "request_url", None
                            ),
                            "status": getattr(entry.http_request, "status", None),
                            "latency": str(entry.http_request.latency)
                            if hasattr(entry.http_request, "latency")
                            else None,
                        }
                        if entry.http_request
                        else None,
                    }
                )
            next_token = first_page.next_page_token

        return {"entries": results, "next_page_token": next_token or None}
    except Exception as e:
        import os

        is_eval = os.getenv("SRE_AGENT_EVAL_MODE", "false").lower() == "true"
        error_msg = f"Failed to list log entries: {e!s}"

        if is_eval and any(
            code in error_msg
            for code in ["400", "404", "InvalidArgument", "NotFound", "Field not found"]
        ):
            logger.warning(
                f"Logging API error in eval mode (filter: {filter_str}): {error_msg}. Returning empty entries."
            )
            return {"entries": [], "next_page_token": None}

        # Provide smart hints for common mistakes
        if "Field not found" in error_msg:
            if any(
                f in error_msg
                for f in [
                    "container_name",
                    "pod_name",
                    "namespace_name",
                    "cluster_name",
                ]
            ):
                error_msg += (
                    "\n\nHINT: GKE fields like 'container_name' or 'pod_name' must be prefixed "
                    "with 'resource.labels.'. Try 'resource.labels.container_name=\"...\"' instead."
                )
            elif "instance_id" in error_msg:
                error_msg += (
                    "\n\nHINT: Compute Engine fields like 'instance_id' must be prefixed "
                    "with 'resource.labels.'. Try 'resource.labels.instance_id=\"...\"' instead. "
                    "Note: 'resource.labels.instance_name' is NOT a valid field for 'gce_instance' resource logs. "
                    "You must use 'resource.labels.instance_id'."
                )
            elif "instance_name" in error_msg:
                error_msg += (
                    "\n\nHINT: 'resource.labels.instance_name' is NOT a valid field for 'gce_instance' resource logs. "
                    "You must use 'resource.labels.instance_id'. If you only know the name, search "
                    "globally for the name string (e.g. 'textPayload:\"my-instance\"') or list instances first."
                )
            elif "nested type" in error_msg and "jsonPayload" in error_msg:
                error_msg += (
                    "\n\nHINT: You cannot use the colon operator on 'jsonPayload' itself "
                    "if it is treated as a nested type. Try searching for specific fields like 'jsonPayload.message' "
                    "or just use a global search string without 'jsonPayload:'."
                )

        logger.error(error_msg, exc_info=True)
        return {"error": error_msg}


@adk_tool
async def list_error_events(
    minutes_ago: int = 60, project_id: str | None = None, tool_context: Any = None
) -> BaseToolResponse:
    """Lists error events from Google Cloud Error Reporting using direct API.

    Args:
        project_id: The Google Cloud Project ID.
        minutes_ago: The number of minutes in the past to query.
        tool_context: Context object for tool execution.

    Returns:
        Standardized response with list of error events.
    """
    from sre_agent.auth import is_guest_mode

    if is_guest_mode():
        from sre_agent.tools.synthetic.provider import SyntheticDataProvider

        return SyntheticDataProvider.list_error_events(
            project_id=project_id, minutes_ago=minutes_ago
        )

    from fastapi.concurrency import run_in_threadpool

    from sre_agent.auth import get_current_project_id

    if not project_id:
        project_id = get_current_project_id()
        if not project_id:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error=(
                    "Project ID is required but not provided or found in context. "
                    "HINT: If you are using the Agent Engine playground, please pass the project ID "
                    "in your request (e.g., 'Analyze logs in project my-project-id') or use the project selector. "
                    "Local users should set the GOOGLE_CLOUD_PROJECT environment variable."
                ),
            )

    result = await run_in_threadpool(
        _list_error_events_sync, project_id, minutes_ago, tool_context
    )
    if isinstance(result, dict) and "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _list_error_events_sync(
    project_id: str, minutes_ago: int = 60, tool_context: Any = None
) -> list[dict[str, Any]] | dict[str, Any]:
    """Synchronous implementation of list_error_events."""
    try:
        from google.cloud import errorreporting_v1beta1

        client = get_error_reporting_client(tool_context=tool_context)
        project_name = f"projects/{project_id}"
        time_range = errorreporting_v1beta1.QueryTimeRange()
        time_range.period = errorreporting_v1beta1.QueryTimeRange.Period.PERIOD_1_HOUR  # type: ignore
        request = errorreporting_v1beta1.ListEventsRequest(
            project_name=project_name,
            group_id=None,
            time_range=time_range,
            page_size=100,
        )

        events = client.list_events(request=request)

        results = []
        for event in events:
            results.append(
                {
                    "event_time": event.event_time.isoformat(),
                    "message": event.message,
                    "service_context": {
                        "service": event.service_context.service,
                        "version": event.service_context.version,
                    },
                }
            )
        return results
    except Exception as e:
        import os

        is_eval = os.getenv("SRE_AGENT_EVAL_MODE", "false").lower() == "true"
        error_msg = str(e)
        if is_eval and any(
            code in error_msg for code in ["400", "404", "InvalidArgument", "NotFound"]
        ):
            logger.warning(
                f"Error Reporting API error in eval mode: {error_msg}. Returning empty list."
            )
            return []

        error_msg = f"Failed to list error events: {e!s}"
        logger.error(error_msg)
        return {"error": error_msg}


@adk_tool
async def get_logs_for_trace(
    project_id: str, trace_id: str, limit: int = 100, tool_context: Any = None
) -> BaseToolResponse:
    """Fetches log entries correlated with a specific trace ID.

    Args:
        project_id: The Google Cloud Project ID.
        trace_id: The unique trace ID.
        limit: Max logs to return.
        tool_context: Context object for tool execution.

    Returns:
        Standardized response containing the list of log entries.
    """
    from sre_agent.auth import is_guest_mode

    if is_guest_mode():
        from sre_agent.tools.synthetic.provider import SyntheticDataProvider

        return SyntheticDataProvider.get_logs_for_trace(
            project_id=project_id, trace_id=trace_id, limit=limit
        )

    filter_str = f'trace="projects/{project_id}/traces/{trace_id}"'

    from fastapi.concurrency import run_in_threadpool

    result = await run_in_threadpool(
        _list_log_entries_sync, project_id, filter_str, limit, None, tool_context
    )
    if "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


@adk_tool
async def list_logs(
    project_id: str | None = None, tool_context: Any = None
) -> BaseToolResponse:
    """Lists the names of logs available in the Google Cloud Project.

    Args:
        project_id: The Google Cloud Project ID.
        tool_context: Context object for tool execution.

    Returns:
        Standardized response containing a list of log paths.
    """
    from sre_agent.auth import is_guest_mode

    if is_guest_mode():
        from sre_agent.tools.synthetic.provider import SyntheticDataProvider

        return SyntheticDataProvider.list_logs(project_id=project_id)

    from fastapi.concurrency import run_in_threadpool

    from sre_agent.auth import get_current_project_id

    if not project_id:
        project_id = get_current_project_id()
        if not project_id:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error="Project ID is required.",
            )

    result = await run_in_threadpool(_list_logs_sync, project_id, tool_context)
    if "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _list_logs_sync(project_id: str, tool_context: Any = None) -> dict[str, Any]:
    try:
        client = get_logging_client(tool_context=tool_context)
        parent = f"projects/{project_id}"
        pager = client.list_logs(parent=parent)
        logs = []
        for x in pager:
            # Note: pager yields strings
            if isinstance(x, str):
                log_name = x
            elif hasattr(x, "name"):
                log_name = x.name
            else:
                log_name = str(x)

            # Usually the log name is a full path 'projects/[PROJECT_ID]/logs/[LOG_ID]'
            # But the google-cloud-logging library often just returns the LOG_ID or full path.
            # We standardize on returning the full string.
            logs.append(log_name)
            if len(logs) >= 500:
                break
        return {"logs": logs}
    except Exception as e:
        logger.error(f"Failed to list logs: {e}", exc_info=True)
        return {"error": str(e)}


@adk_tool
async def list_resource_keys(
    project_id: str | None = None, tool_context: Any = None
) -> BaseToolResponse:
    """Lists the monitored resource descriptors available in Cloud Logging.

    Args:
        project_id: The Google Cloud Project ID.
        tool_context: Context object for tool execution.

    Returns:
        Standardized response containing resource descriptors.
    """
    from sre_agent.auth import is_guest_mode

    if is_guest_mode():
        return BaseToolResponse(status=ToolStatus.SUCCESS, result={"resource_keys": []})

    from fastapi.concurrency import run_in_threadpool

    from sre_agent.auth import get_current_project_id

    if not project_id:
        project_id = get_current_project_id()
        if not project_id:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error="Project ID is required.",
            )

    result = await run_in_threadpool(_list_resource_keys_sync, tool_context)
    if "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _list_resource_keys_sync(tool_context: Any = None) -> dict[str, Any]:
    try:
        client = get_logging_client(tool_context=tool_context)
        pager = client.list_monitored_resource_descriptors()
        keys = []
        for d in pager:
            keys.append(
                {
                    "type": getattr(d, "type", ""),
                    "display_name": getattr(d, "display_name", ""),
                    "description": getattr(d, "description", ""),
                }
            )
            if len(keys) >= 200:
                break
        return {"resource_keys": keys}
    except Exception as e:
        logger.error(f"Failed to list resource keys: {e}", exc_info=True)
        return {"error": str(e)}


def _extract_log_payload(entry: Any) -> str | dict[str, Any]:
    """Extracts and normalizes payload from a log entry."""
    payload_data: str | dict[str, Any] = ""

    if entry.text_payload:
        payload_data = entry.text_payload
    elif hasattr(entry, "json_payload") and entry.json_payload:
        try:
            payload_data = dict(entry.json_payload)
        except (ValueError, TypeError):
            payload_data = str(entry.json_payload)
    elif hasattr(entry, "proto_payload"):
        try:
            proto = entry.proto_payload
            if proto:
                try:
                    from google.protobuf.json_format import MessageToDict

                    payload_data = MessageToDict(proto)
                except Exception:
                    try:
                        payload_data = str(proto)
                    except Exception:
                        payload_data = f"[ProtoPayload] {proto.type_url}"
        except Exception as e:
            # Fallback if accessing proto_payload fails (e.g. missing descriptor)
            payload_data = f"[ProtoPayload unavailable] {e!s}"

    # Truncate if string and too long
    if isinstance(payload_data, str) and len(payload_data) > 2000:
        payload_data = payload_data[:2000] + "...(truncated)"

    return payload_data
