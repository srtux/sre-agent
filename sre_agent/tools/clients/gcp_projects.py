"""Tool to list GCP projects accessible to the current user."""

import logging
from typing import Any

import google.auth
import google.auth.transport.requests
import httpx

from ...auth import get_credentials_from_tool_context
from ...schema import BaseToolResponse, ToolStatus
from ..common import adk_tool

logger = logging.getLogger(__name__)


@adk_tool
async def list_gcp_projects(
    query: str | None = None, tool_context: Any = None
) -> BaseToolResponse:
    """List or search GCP projects that the user has access to.

    This tool calls the Cloud Resource Manager API v3 to search projects.
    It supports server-side filtering for users with area-wide access.

    Args:
        query: Optional search string to filter by project ID or display name.
        tool_context: ADK ToolContext for credential propagation.

    Returns:
        Dictionary containing a list of projects:
        {
            "projects": [{"project_id": "project-id", "display_name": "Project Name"}, ...]
        }
    """
    try:
        logger.info(f"list_gcp_projects called with query='{query}'")
        # Use Any to avoid type mismatch between oauth2.credentials and google.auth.credentials
        auth_creds: Any = get_credentials_from_tool_context(tool_context)

        # Strict EUC Enforcement: No fallback to Default Credentials (ADC)
        if not auth_creds:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error="Authentication required. EUC not found and ADC fallback is disabled for this tool.",
                result={"projects": []},
            )

        if auth_creds and not getattr(auth_creds, "token", None):
            # Refresh credentials if needed
            try:
                auth_request = google.auth.transport.requests.Request()
                auth_creds.refresh(auth_request)
            except Exception as e:
                logger.warning(f"Credential refresh failed: {e}")
                pass

        async with httpx.AsyncClient(timeout=10.0) as client:
            token = getattr(auth_creds, "token", None)
            if not token:
                return BaseToolResponse(
                    status=ToolStatus.ERROR,
                    error="No valid authentication token found",
                    result={"projects": []},
                )

            headers = {"Authorization": f"Bearer {token}"}

            # Use CRM v3 SearchProjects API
            url = "https://cloudresourcemanager.googleapis.com/v3/projects:search"

            params: dict[str, Any] = {"pageSize": 50}

            if query:
                safe_query = query.replace('"', "").replace("'", "").strip()
                params["query"] = (
                    f'projectId:{safe_query}* OR displayName:"{safe_query}*"'
                )

            response = await client.get(
                url,
                headers=headers,
                params=params,
            )

            if response.status_code != 200:
                logger.error(f"Failed to search projects: {response.text}")
                return BaseToolResponse(
                    status=ToolStatus.ERROR,
                    error=f"API error: {response.status_code}",
                    result={"projects": []},
                )

            try:
                data = response.json()
            except Exception:
                logger.error(f"Failed to parse JSON response: {response.text[:200]}")
                return BaseToolResponse(
                    status=ToolStatus.ERROR,
                    error="Invalid API response",
                    result={"projects": []},
                )

            projects = []
            for p in data.get("projects", []):
                pid = p.get("projectId")
                if not pid:
                    name = p.get("name", "")
                    if "/" in name:
                        pid = name.split("/")[-1]

                projects.append(
                    {"project_id": pid, "display_name": p.get("displayName", pid)}
                )

            return BaseToolResponse(
                status=ToolStatus.SUCCESS, result={"projects": projects}
            )

    except Exception as e:
        logger.error(f"Error listing projects: {e}", exc_info=True)
        return BaseToolResponse(
            status=ToolStatus.ERROR, error=str(e), result={"projects": []}
        )
