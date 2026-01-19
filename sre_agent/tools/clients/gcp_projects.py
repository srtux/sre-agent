"""Tool to list GCP projects accessible to the current user."""

import logging
from typing import Any

import google.auth
import google.auth.transport.requests
import httpx

from ...auth import get_current_credentials
from ..common import adk_tool

logger = logging.getLogger(__name__)


@adk_tool
async def list_gcp_projects(query: str | None = None) -> dict[str, Any]:
    """List or search GCP projects that the user has access to.

    This tool calls the Cloud Resource Manager API v3 to search projects.
    It supports server-side filtering for users with access to many projects.

    Args:
        query: Optional search string to filter by project ID or display name.

    Returns:
        Dictionary containing a list of projects:
        {
            "projects": [{"id": "project-id", "name": "Project Name"}, ...]
        }
    """
    try:
        print(f"🔄 list_gcp_projects called with query='{query}'")
        credentials, _ = get_current_credentials()

        if not credentials.token:
            # Refresh credentials if needed
            try:
                auth_request = google.auth.transport.requests.Request()
                credentials.refresh(auth_request)  # type: ignore[no-untyped-call]
                print("✅ Credentials refreshed")
            except Exception as e:
                print(f"⚠️ Credential refresh failed: {e}")
                pass

        async with httpx.AsyncClient() as client:
            headers = {"Authorization": f"Bearer {credentials.token}"}

            # Use CRM v3 SearchProjects API
            url = "https://cloudresourcemanager.googleapis.com/v3/projects:search"

            params = {
                "pageSize": 50  # Limit to 50 for performance
            }

            if query:
                # Sanitize query to prevent syntax errors
                safe_query = query.replace('"', "").replace("'", "").strip()
                # V3 Syntax: projectId:val* OR displayName:"val*"
                # Note: Wildcards only allowed at END of string
                params["query"] = (
                    f'projectId:{safe_query}* OR displayName:"{safe_query}*"'
                )
                print(f"🔍 Searching with filter: {params['query']}")

            print(f"📡 Sending request to {url}")
            response = await client.get(
                url,
                headers=headers,
                params=params,
            )

            print(f"📥 Response status: {response.status_code}")

            if response.status_code != 200:
                print(f"❌ API Error: {response.text}")
                logger.error(f"Failed to search projects: {response.text}")
                return {"projects": [], "error": f"API error: {response.status_code}"}

            try:
                data = response.json()
            except Exception as e:
                print(f"❌ Failed to parse JSON: {e}")
                logger.error(f"Failed to parse JSON response: {response.text[:200]}")
                return {"projects": [], "error": "Invalid API response"}

            projects = []
            for p in data.get("projects", []):
                # V3 returns 'projectId' and 'displayName'
                # fallback to 'name' which might be resource name 'projects/123' if projectId missing (unlikely)
                pid = p.get("projectId")
                if not pid:
                    # Parse from resource name if needed
                    name = p.get("name", "")
                    if "/" in name:
                        pid = name.split("/")[-1]

                projects.append(
                    {"project_id": pid, "display_name": p.get("displayName", pid)}
                )

            print(f"✅ Found {len(projects)} projects")
            return {"projects": projects}

    except Exception as e:
        import traceback

        traceback.print_exc()
        logger.error(f"Error listing projects: {e}")
        return {"projects": [], "error": str(e)}
