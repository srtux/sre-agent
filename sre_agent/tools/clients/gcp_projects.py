"""Tool to list GCP projects accessible to the current user."""

import logging
from typing import Any

import google.auth
import google.auth.transport.requests
import httpx

from ...auth import get_credentials_from_tool_context
from ..common import adk_tool

logger = logging.getLogger(__name__)


@adk_tool
async def list_gcp_projects(
    query: str | None = None, tool_context: Any = None
) -> dict[str, Any]:
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
        credentials = get_credentials_from_tool_context(tool_context)

        # Fallback to default credentials if no user credentials found in tool_context/ContextVar
        if not credentials:
            credentials, _ = google.auth.default()

        if not credentials.token:
            # Refresh credentials if needed
            try:
                auth_request = google.auth.transport.requests.Request()
                credentials.refresh(auth_request)  # type: ignore[no-untyped-call]
            except Exception as e:
                logger.warning(f"Credential refresh failed: {e}")
                pass

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {credentials.token}"}

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
                return {"projects": [], "error": f"API error: {response.status_code}"}

            try:
                data = response.json()
            except Exception:
                logger.error(f"Failed to parse JSON response: {response.text[:200]}")
                return {"projects": [], "error": "Invalid API response"}

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

            return {"projects": projects}

    except Exception as e:
        logger.error(f"Error listing projects: {e}", exc_info=True)
        return {"projects": [], "error": str(e)}
