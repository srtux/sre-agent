"""Direct API client for Cloud Monitoring Alerts.

This module allows the agent to interact with the Google Cloud Alerting API.
It allows the agent to:
- List active incidents (fires).
- Inspect alert policies (why the fire started).
- Retrieve full metadata about alert resources.

This is the primary toolset for the `alert_analyst` sub-agent.
"""

import logging
from typing import Any, cast

from google.auth.transport.requests import AuthorizedSession
from google.cloud import monitoring_v3

from sre_agent.auth import (
    get_credentials_from_tool_context,
    get_current_credentials,
)
from sre_agent.schema import BaseToolResponse, ToolStatus
from sre_agent.tools.clients.factory import get_alert_policy_client
from sre_agent.tools.common import adk_tool

logger = logging.getLogger(__name__)


def _get_authorized_session(tool_context: Any = None) -> AuthorizedSession:
    """Get an authorized session for REST API calls."""
    credentials = get_credentials_from_tool_context(tool_context)
    if not credentials:
        auth_obj: Any = get_current_credentials()
        if isinstance(auth_obj, tuple):
            credentials, _ = auth_obj
        else:
            credentials = auth_obj
    return AuthorizedSession(credentials)  # type: ignore[no-untyped-call]


@adk_tool
async def list_alerts(
    project_id: str | None = None,
    filter_str: str | None = None,
    minutes_ago: int | None = None,
    order_by: str | None = None,
    page_size: int = 100,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Lists alerts (incidents) using the Google Cloud Monitoring API.

    Args:
        project_id: The Google Cloud Project ID.
        filter_str: Monitoring filter string (e.g. 'state="OPEN"').
        minutes_ago: Only return alerts created in the last N minutes.
        order_by: Sort order (e.g. 'start_time desc').
        page_size: Max results per page.
        tool_context: Context object for tool execution.
    """
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
        _list_alerts_sync,
        project_id,
        filter_str,
        minutes_ago,
        order_by,
        page_size,
        tool_context,
    )
    if isinstance(result, dict) and "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _list_alerts_sync(
    project_id: str,
    filter_str: str | None = None,
    minutes_ago: int | None = None,
    order_by: str | None = None,
    page_size: int = 100,
    tool_context: Any = None,
) -> list[dict[str, Any]] | dict[str, Any]:
    """Synchronous implementation of list_alerts."""
    try:
        session = _get_authorized_session(tool_context)
        url = f"https://monitoring.googleapis.com/v3/projects/{project_id}/alerts"
        params: dict[str, Any] = {"pageSize": page_size}

        # Build filter
        filters = []
        if filter_str:
            # Ensure it's a string, in case something structured was passed
            if not isinstance(filter_str, str):
                filter_str = str(filter_str)
            filters.append(filter_str)

        if minutes_ago:
            import time

            start_time = int(time.time() - (minutes_ago * 60))
            filters.append(f"create_time > {start_time}")

        if filters:
            params["filter"] = " AND ".join(filters)

        if order_by:
            mapped_order_by = order_by
            replacements = {
                "start_time": "open_time",
                "startTime": "open_time",
                "openTime": "open_time",
                "end_time": "close_time",
                "endTime": "close_time",
                "closeTime": "close_time",
            }
            for k, v in replacements.items():
                mapped_order_by = mapped_order_by.replace(k, v)
            params["orderBy"] = mapped_order_by

        headers = {"X-Goog-User-Project": project_id}
        response = session.get(url, params=params, headers=headers)

        if not response.ok:
            try:
                error_json = response.json()
                message = error_json.get("error", {}).get("message", response.text)
            except Exception:
                message = response.text
            raise Exception(f"{response.status_code} {response.reason}: {message}")

        data = response.json()
        alerts = data.get("alerts", [])
        return cast(list[dict[str, Any]], alerts)

    except Exception as e:
        error_msg = f"Failed to list alerts: {e!s}"

        # Provide smart hints for common mistakes
        if (
            "Restriction must have a left-hand side" in error_msg
            or "Field filter had an invalid value" in error_msg
        ):
            error_msg += (
                "\n\nHINT: Google Cloud Monitoring filters must follow the syntax 'field=\"value\"'. "
                "Ensure you are not passing raw proto-style filters or complex objects. "
                "Example: 'state=\"OPEN\"'. Also ensure timestamps are integers or use the 'minutes_ago' parameter."
            )

        if "comparator:" in error_msg:
            error_msg += (
                "\n\nCRITICAL HINT: The filter you passed looks like a raw proto debug string. "
                "This usually happens when an object is passed instead of a simple string. "
                "Always use simple string filters like 'state=\"OPEN\"' or 'create_time > 123456789'."
            )

        logger.error(error_msg, exc_info=True)
        return {"error": error_msg}


@adk_tool
async def get_alert(name: str, tool_context: Any = None) -> BaseToolResponse:
    """Gets a specific alert by its resource name."""
    from fastapi.concurrency import run_in_threadpool

    result = await run_in_threadpool(_get_alert_sync, name, tool_context)
    if isinstance(result, dict) and "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _get_alert_sync(name: str, tool_context: Any = None) -> dict[str, Any]:
    """Synchronous implementation of get_alert."""
    try:
        session = _get_authorized_session(tool_context)
        url = f"https://monitoring.googleapis.com/v3/{name}"
        headers = {}
        if name.startswith("projects/"):
            proj_id = name.split("/")[1]
            headers["X-Goog-User-Project"] = proj_id

        response = session.get(url, headers=headers)
        if not response.ok:
            try:
                error_json = response.json()
                message = error_json.get("error", {}).get("message", response.text)
            except Exception:
                message = response.text
            raise Exception(f"{response.status_code}: {message}")

        return cast(dict[str, Any], response.json())
    except Exception as e:
        error_msg = f"Failed to get alert: {e!s}"
        logger.error(error_msg, exc_info=True)
        return {"error": error_msg}


@adk_tool
async def list_alert_policies(
    project_id: str | None = None,
    filter_str: str | None = None,
    page_size: int = 100,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Lists alert policies from Google Cloud Monitoring."""
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
        _list_alert_policies_sync, project_id, filter_str, page_size, tool_context
    )
    if isinstance(result, dict) and "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _list_alert_policies_sync(
    project_id: str,
    filter_str: str | None = None,
    page_size: int = 100,
    tool_context: Any = None,
) -> list[dict[str, Any]] | dict[str, Any]:
    """Synchronous implementation of list_alert_policies."""
    try:
        client = get_alert_policy_client(tool_context)
        project_name = f"projects/{project_id}"
        request = monitoring_v3.ListAlertPoliciesRequest(
            name=project_name,
            filter=filter_str if filter_str else "",
            page_size=page_size,
        )
        results = client.list_alert_policies(request=request)
        policies_data = []
        for policy in results:
            policy_dict = {
                "name": policy.name,
                "display_name": policy.display_name,
                "documentation": {
                    "content": policy.documentation.content,
                    "mime_type": policy.documentation.mime_type,
                },
                "user_labels": dict(policy.user_labels),
                "conditions": [],
                "enabled": policy.enabled,
            }
            for condition in policy.conditions:
                policy_dict["conditions"].append(
                    {
                        "name": condition.name,
                        "display_name": condition.display_name,
                    }
                )
            policies_data.append(policy_dict)
        return policies_data
    except Exception as e:
        error_msg = f"Failed to list alert policies: {e!s}"
        logger.error(error_msg, exc_info=True)
        return {"error": error_msg}
