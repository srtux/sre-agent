"""Direct API client for Cloud Monitoring Alerts.

This module allows the agent to interact with the Google Cloud Alerting API.
It allows the agent to:
- List active incidents (fires).
- Inspect alert policies (why the fire started).
- Retrieve full metadata about alert resources.

This is the primary toolset for the `alert_analyst` sub-agent.
"""

import logging
from typing import Any

from google.auth.transport.requests import AuthorizedSession
from google.cloud import monitoring_v3

from ...auth import get_credentials_from_tool_context, get_current_credentials
from ..common import adk_tool, json_dumps
from ..common.telemetry import get_tracer
from .factory import get_alert_policy_client

logger = logging.getLogger(__name__)
tracer = get_tracer(__name__)


def _get_authorized_session(tool_context: Any = None) -> AuthorizedSession:
    """Get an authorized session for REST API calls."""
    credentials = get_credentials_from_tool_context(tool_context)
    if not credentials:
        auth_obj: Any = get_current_credentials()
        credentials, _ = auth_obj
    return AuthorizedSession(credentials)  # type: ignore[no-untyped-call]


@adk_tool
async def list_alerts(
    project_id: str,
    filter_str: str | None = None,
    order_by: str | None = None,
    page_size: int = 100,
    tool_context: Any = None,
) -> str:
    """Lists alerts (incidents) using the Google Cloud Monitoring API.

    Args:
        project_id: The Google Cloud Project ID.
        filter_str: Optional filter string. Server-side filtering supports only 'state' and 'policy_name'.
                  Example: 'state="OPEN"' or 'state="CLOSED"'.
                  Warning: Time-based filtering is NOT supported server-side; use sorting instead.
        order_by: Optional sort order field. Supported fields: 'open_time', 'close_time'.
                  Example: 'open_time desc'. Default is 'open_time desc'.
        page_size: Number of results to return (default 100, max 1000).
        tool_context: Context object for tool execution.

    Returns:
        A JSON string containing the list of alerts (incidents).
    """
    from fastapi.concurrency import run_in_threadpool

    return await run_in_threadpool(
        _list_alerts_sync, project_id, filter_str, order_by, page_size, tool_context
    )


def _list_alerts_sync(
    project_id: str,
    filter_str: str | None = None,
    order_by: str | None = None,
    page_size: int = 100,
    tool_context: Any = None,
) -> str:
    """Synchronous implementation of list_alerts."""
    with tracer.start_as_current_span("list_alerts") as span:
        span.set_attribute("gcp.project_id", project_id)
        if filter_str:
            span.set_attribute("gcp.monitoring.filter", filter_str)

        try:
            # Get credentials
            session = _get_authorized_session(tool_context)

            # API Endpoint: projects.alerts.list
            # https://cloud.google.com/monitoring/api/ref_v3/rest/v3/projects.alerts/list
            url = f"https://monitoring.googleapis.com/v3/projects/{project_id}/alerts"

            params: dict[str, Any] = {"pageSize": page_size}
            if filter_str:
                params["filter"] = filter_str

            if order_by:
                # Map common aliases and camelCase fields back to canonical snake_case field names.
                # REST API orderBy supports: open_time, close_time.
                replacements = {
                    "start_time": "open_time",
                    "startTime": "open_time",
                    "openTime": "open_time",
                    "end_time": "close_time",
                    "endTime": "close_time",
                    "closeTime": "close_time",
                }
                mapped_order_by = order_by
                for k, v in replacements.items():
                    mapped_order_by = mapped_order_by.replace(k, v)
                params["orderBy"] = mapped_order_by

            # Include X-Goog-User-Project for quota/billing attribution
            headers = {"X-Goog-User-Project": project_id}
            response = session.get(url, params=params, headers=headers)

            if not response.ok:
                try:
                    error_json = response.json()
                    message = error_json.get("error", {}).get("message", response.text)
                except Exception:
                    message = response.text
                raise Exception(
                    f"{response.status_code} Client Error: {response.reason} for url: {response.url}\n"
                    f"Response: {message}"
                )

            data = response.json()
            alerts = data.get("alerts", [])

            span.set_attribute("gcp.monitoring.alerts_count", len(alerts))
            return json_dumps(alerts)

        except Exception as e:
            span.record_exception(e)
            error_msg = f"Failed to list alerts: {e!s}"
            logger.error(error_msg, exc_info=True)
            return json_dumps({"error": error_msg})


@adk_tool
async def get_alert(name: str, tool_context: Any = None) -> str:
    """Gets a specific alert by its resource name.

    Args:
        name: The full resource name of the alert
              (e.g., 'projects/{project_id}/alerts/{alert_id}').
        tool_context: Context object for tool execution.

    Returns:
        A JSON string containing the alert details.
    """
    from fastapi.concurrency import run_in_threadpool

    return await run_in_threadpool(_get_alert_sync, name, tool_context)


def _get_alert_sync(name: str, tool_context: Any = None) -> str:
    """Synchronous implementation of get_alert."""
    with tracer.start_as_current_span("get_alert") as span:
        span.set_attribute("gcp.monitoring.alert_name", name)

        try:
            # Get credentials
            session = _get_authorized_session(tool_context)

            # API Endpoint: projects.alerts.get
            url = f"https://monitoring.googleapis.com/v3/{name}"

            # Extract project ID from resource name for billing header
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

            return json_dumps(response.json())

        except Exception as e:
            span.record_exception(e)
            error_msg = f"Failed to get alert: {e!s}"
            logger.error(error_msg, exc_info=True)
            return json_dumps({"error": error_msg})


@adk_tool
async def list_alert_policies(
    project_id: str,
    filter_str: str | None = None,
    page_size: int = 100,
    tool_context: Any = None,
) -> str:
    """Lists alert policies from Google Cloud Monitoring.

    Args:
        project_id: The Google Cloud Project ID.
        filter_str: Optional filter string.
        page_size: Number of results to return.
        tool_context: Context object for tool execution.

    Returns:
        A JSON string containing the list of alert policies.
    """
    from fastapi.concurrency import run_in_threadpool

    return await run_in_threadpool(
        _list_alert_policies_sync, project_id, filter_str, page_size, tool_context
    )


def _list_alert_policies_sync(
    project_id: str,
    filter_str: str | None = None,
    page_size: int = 100,
    tool_context: Any = None,
) -> str:
    """Synchronous implementation of list_alert_policies."""
    with tracer.start_as_current_span("list_alert_policies") as span:
        span.set_attribute("gcp.project_id", project_id)

        try:
            client = get_alert_policy_client(tool_context)
            project_name = f"projects/{project_id}"

            request = monitoring_v3.ListAlertPoliciesRequest(
                name=project_name,
                filter=filter_str if filter_str else "",
                page_size=page_size,
            )

            results = client.list_alert_policies(request=request)

            # Convert protobuf results to list of dicts
            policies_data = []
            for policy in results:
                # Basic fields + user_labels
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

                # Extract simple condition info
                for condition in policy.conditions:
                    policy_dict["conditions"].append(
                        {
                            "name": condition.name,
                            "display_name": condition.display_name,
                        }
                    )

                policies_data.append(policy_dict)

            span.set_attribute("gcp.monitoring.policies_count", len(policies_data))
            return json_dumps(policies_data)

        except Exception as e:
            span.record_exception(e)
            error_msg = f"Failed to list alert policies: {e!s}"
            logger.error(error_msg, exc_info=True)
            return json_dumps({"error": error_msg})
