"""Cloud Asset Inventory Client.

This module provides tools for querying GCP resource configurations using
the Cloud Asset Inventory API. It enables the SRE agent to:

- List and search assets across projects, folders, and organizations
- Query asset configurations and relationships
- Get asset change history for troubleshooting
- Export assets to BigQuery for analysis

Reference: https://cloud.google.com/asset-inventory/docs/overview
"""

import logging
from typing import Any

from google.auth.transport.requests import AuthorizedSession

from ...auth import (
    get_credentials_from_tool_context,
    get_current_credentials,
    get_current_project_id,
)
from ...schema import BaseToolResponse, ToolStatus
from ..common import adk_tool

logger = logging.getLogger(__name__)


def _get_authorized_session(tool_context: Any = None) -> AuthorizedSession:
    """Get an authorized session for REST API calls."""
    credentials = get_credentials_from_tool_context(tool_context)
    if not credentials:
        auth_obj: Any = get_current_credentials()
        credentials, _ = auth_obj
    return AuthorizedSession(credentials)  # type: ignore[no-untyped-call]


@adk_tool
async def search_assets(
    query: str,
    asset_types: list[str] | None = None,
    scope: str | None = None,
    project_id: str | None = None,
    page_size: int = 100,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Search for GCP assets matching a query.

    This tool searches across all assets in the specified scope using
    Cloud Asset Inventory's search capabilities.

    Args:
        query: Search query string. Supports field filters like:
            - name:*my-instance* (name contains)
            - labels.env:prod (label value)
            - state:RUNNING (resource state)
            - createTime>2024-01-01 (creation time)
        asset_types: List of asset types to search (e.g., ["compute.googleapis.com/Instance"]).
        scope: Scope to search (projects/PROJECT_ID, folders/FOLDER_ID, organizations/ORG_ID).
            Defaults to current project.
        project_id: Project ID for default scope. Uses current context if not provided.
        page_size: Maximum results to return (default 100, max 500).
        tool_context: ADK ToolContext for credential propagation.

    Returns:
        BaseToolResponse with list of matching assets.

    Example:
        search_assets("state:RUNNING AND labels.env:prod", asset_types=["compute.googleapis.com/Instance"])
    """
    from fastapi.concurrency import run_in_threadpool

    if not project_id:
        project_id = get_current_project_id()

    if not project_id and not scope:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="Either project_id or scope is required.",
        )

    if not scope:
        scope = f"projects/{project_id}"

    result = await run_in_threadpool(
        _search_assets_sync,
        query,
        asset_types,
        scope,
        page_size,
        tool_context,
    )

    if isinstance(result, dict) and "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _search_assets_sync(
    query: str,
    asset_types: list[str] | None,
    scope: str,
    page_size: int,
    tool_context: Any = None,
) -> dict[str, Any]:
    """Synchronous implementation of search_assets."""
    try:
        session = _get_authorized_session(tool_context)

        url = f"https://cloudasset.googleapis.com/v1/{scope}:searchAllResources"

        params: dict[str, Any] = {
            "query": query,
            "pageSize": min(page_size, 500),
        }

        if asset_types:
            params["assetTypes"] = asset_types

        response = session.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        assets = data.get("results", [])

        result: dict[str, Any] = {
            "scope": scope,
            "query": query,
            "asset_count": len(assets),
            "assets": [],
        }

        for asset in assets:
            result["assets"].append(
                {
                    "name": asset.get("name"),
                    "asset_type": asset.get("assetType"),
                    "display_name": asset.get("displayName"),
                    "description": asset.get("description"),
                    "location": asset.get("location"),
                    "labels": asset.get("labels", {}),
                    "state": asset.get("state"),
                    "create_time": asset.get("createTime"),
                    "update_time": asset.get("updateTime"),
                    "project": asset.get("project"),
                    "folders": asset.get("folders", []),
                    "organization": asset.get("organization"),
                }
            )

        return result

    except Exception as e:
        error_msg = f"Failed to search assets: {e!s}"
        logger.error(error_msg)
        return {"error": error_msg}


@adk_tool
async def list_assets(
    asset_types: list[str] | None = None,
    content_type: str = "RESOURCE",
    project_id: str | None = None,
    page_size: int = 100,
    tool_context: Any = None,
) -> BaseToolResponse:
    """List assets in a project with their configurations.

    This tool lists all assets of specified types in a project,
    including their full resource configurations.

    Args:
        asset_types: List of asset types to list. If not specified, lists all types.
            Common types:
            - compute.googleapis.com/Instance
            - compute.googleapis.com/Disk
            - storage.googleapis.com/Bucket
            - container.googleapis.com/Cluster
            - sqladmin.googleapis.com/Instance
            - run.googleapis.com/Service
        content_type: Type of content to return:
            - RESOURCE: Full resource configuration
            - IAM_POLICY: IAM policies
            - ORG_POLICY: Organization policies
            - ACCESS_POLICY: Access context manager policies
        project_id: Project ID to list assets from. Uses current context if not provided.
        page_size: Maximum results to return (default 100).
        tool_context: ADK ToolContext for credential propagation.

    Returns:
        BaseToolResponse with list of assets and their configurations.

    Example:
        list_assets(asset_types=["compute.googleapis.com/Instance"])
    """
    from fastapi.concurrency import run_in_threadpool

    if not project_id:
        project_id = get_current_project_id()

    if not project_id:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="Project ID is required.",
        )

    result = await run_in_threadpool(
        _list_assets_sync,
        project_id,
        asset_types,
        content_type,
        page_size,
        tool_context,
    )

    if isinstance(result, dict) and "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _list_assets_sync(
    project_id: str,
    asset_types: list[str] | None,
    content_type: str,
    page_size: int,
    tool_context: Any = None,
) -> dict[str, Any]:
    """Synchronous implementation of list_assets."""
    try:
        session = _get_authorized_session(tool_context)

        url = f"https://cloudasset.googleapis.com/v1/projects/{project_id}/assets"

        params: dict[str, Any] = {
            "contentType": content_type,
            "pageSize": min(page_size, 1000),
        }

        if asset_types:
            params["assetTypes"] = asset_types

        response = session.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        assets = data.get("assets", [])

        result: dict[str, Any] = {
            "project_id": project_id,
            "content_type": content_type,
            "asset_count": len(assets),
            "assets": [],
        }

        for asset in assets:
            asset_info: dict[str, Any] = {
                "name": asset.get("name"),
                "asset_type": asset.get("assetType"),
                "update_time": asset.get("updateTime"),
                "ancestors": asset.get("ancestors", []),
            }

            # Include resource data if available
            resource = asset.get("resource")
            if resource:
                asset_info["resource"] = {
                    "version": resource.get("version"),
                    "discovery_document_uri": resource.get("discoveryDocumentUri"),
                    "discovery_name": resource.get("discoveryName"),
                    "resource_url": resource.get("resourceUrl"),
                    "parent": resource.get("parent"),
                    "data": resource.get("data", {}),
                    "location": resource.get("location"),
                }

            # Include IAM policy if available
            iam_policy = asset.get("iamPolicy")
            if iam_policy:
                asset_info["iam_policy"] = {
                    "version": iam_policy.get("version"),
                    "bindings": iam_policy.get("bindings", []),
                }

            result["assets"].append(asset_info)

        return result

    except Exception as e:
        error_msg = f"Failed to list assets: {e!s}"
        logger.error(error_msg)
        return {"error": error_msg}


@adk_tool
async def get_asset_history(
    asset_names: list[str],
    content_type: str = "RESOURCE",
    start_time: str | None = None,
    end_time: str | None = None,
    project_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Get the change history of specific assets.

    This tool retrieves the historical states of assets, useful for
    understanding when configurations changed and troubleshooting issues.

    Args:
        asset_names: Full asset names to get history for.
            Format: //service.googleapis.com/projects/PROJECT/...
            Example: //compute.googleapis.com/projects/my-project/zones/us-central1-a/instances/my-instance
        content_type: Type of content to return (RESOURCE, IAM_POLICY, etc.)
        start_time: Start of time window (RFC3339 format). Defaults to 7 days ago.
        end_time: End of time window (RFC3339 format). Defaults to now.
        project_id: Project ID. Uses current context if not provided.
        tool_context: ADK ToolContext for credential propagation.

    Returns:
        BaseToolResponse with asset change history.

    Example:
        get_asset_history(["//compute.googleapis.com/projects/my-project/zones/us-central1-a/instances/my-vm"])
    """
    from fastapi.concurrency import run_in_threadpool

    if not project_id:
        project_id = get_current_project_id()

    if not project_id:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="Project ID is required.",
        )

    if not asset_names:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="At least one asset name is required.",
        )

    result = await run_in_threadpool(
        _get_asset_history_sync,
        project_id,
        asset_names,
        content_type,
        start_time,
        end_time,
        tool_context,
    )

    if isinstance(result, dict) and "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _get_asset_history_sync(
    project_id: str,
    asset_names: list[str],
    content_type: str,
    start_time: str | None,
    end_time: str | None,
    tool_context: Any = None,
) -> dict[str, Any]:
    """Synchronous implementation of get_asset_history."""
    try:
        from datetime import datetime, timedelta, timezone

        session = _get_authorized_session(tool_context)

        # Default time window: last 7 days
        if not end_time:
            end_time = datetime.now(timezone.utc).isoformat()
        if not start_time:
            start_dt = datetime.now(timezone.utc) - timedelta(days=7)
            start_time = start_dt.isoformat()

        url = f"https://cloudasset.googleapis.com/v1/projects/{project_id}:batchGetAssetsHistory"

        params: dict[str, Any] = {
            "contentType": content_type,
            "readTimeWindow.startTime": start_time,
            "readTimeWindow.endTime": end_time,
            "assetNames": asset_names,
        }

        response = session.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        assets = data.get("assets", [])

        result: dict[str, Any] = {
            "project_id": project_id,
            "time_window": {
                "start": start_time,
                "end": end_time,
            },
            "asset_count": len(assets),
            "assets": [],
        }

        for asset in assets:
            asset_history: dict[str, Any] = {
                "asset_name": asset.get("asset", {}).get("name"),
                "asset_type": asset.get("asset", {}).get("assetType"),
                "windows": [],
            }

            # Each asset can have multiple windows showing state at different times
            windows = asset.get("windows", [])
            for window in windows:
                window_info = {
                    "start_time": window.get("startTime"),
                    "end_time": window.get("endTime"),
                    "deleted": window.get("deleted", False),
                }

                asset_data = window.get("asset", {})
                if asset_data:
                    window_info["resource"] = asset_data.get("resource", {}).get("data")

                asset_history["windows"].append(window_info)

            result["assets"].append(asset_history)

        return result

    except Exception as e:
        error_msg = f"Failed to get asset history: {e!s}"
        logger.error(error_msg)
        return {"error": error_msg}


@adk_tool
async def get_resource_config(
    resource_name: str,
    project_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Get the full configuration of a specific GCP resource.

    This tool retrieves the complete configuration of a resource using
    Cloud Asset Inventory, providing more detail than individual service APIs.

    Args:
        resource_name: Full resource name in Cloud Asset Inventory format.
            Format: //service.googleapis.com/projects/PROJECT/...
            Example values: //compute.googleapis.com/projects/my-project/zones/us-central1-a/instances/my-vm,
            //storage.googleapis.com/projects/my-project/buckets/my-bucket,
            //container.googleapis.com/projects/my-project/locations/us-central1/clusters/my-cluster
        project_id: Project ID. Uses current context if not provided.
        tool_context: ADK ToolContext for credential propagation.

    Returns:
        BaseToolResponse with full resource configuration.

    Example:
        get_resource_config("//compute.googleapis.com/projects/my-project/zones/us-central1-a/instances/my-vm")
    """
    from fastapi.concurrency import run_in_threadpool

    if not project_id:
        project_id = get_current_project_id()

    if not project_id:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="Project ID is required.",
        )

    result = await run_in_threadpool(
        _get_resource_config_sync,
        project_id,
        resource_name,
        tool_context,
    )

    if isinstance(result, dict) and "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _get_resource_config_sync(
    project_id: str,
    resource_name: str,
    tool_context: Any = None,
) -> dict[str, Any]:
    """Synchronous implementation of get_resource_config."""
    try:
        # Use batchGetAssetsHistory with current time to get latest state
        from datetime import datetime, timezone

        session = _get_authorized_session(tool_context)

        now = datetime.now(timezone.utc).isoformat()

        url = f"https://cloudasset.googleapis.com/v1/projects/{project_id}:batchGetAssetsHistory"

        params: dict[str, Any] = {
            "contentType": "RESOURCE",
            "readTimeWindow.startTime": now,
            "readTimeWindow.endTime": now,
            "assetNames": [resource_name],
        }

        response = session.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        assets = data.get("assets", [])

        if not assets:
            return {"error": f"Resource not found: {resource_name}"}

        asset = assets[0]
        asset_data = asset.get("asset", {})
        resource = asset_data.get("resource", {})

        result: dict[str, Any] = {
            "name": asset_data.get("name"),
            "asset_type": asset_data.get("assetType"),
            "update_time": asset_data.get("updateTime"),
            "ancestors": asset_data.get("ancestors", []),
            "resource": {
                "version": resource.get("version"),
                "discovery_name": resource.get("discoveryName"),
                "parent": resource.get("parent"),
                "location": resource.get("location"),
                "data": resource.get("data", {}),
            },
        }

        return result

    except Exception as e:
        error_msg = f"Failed to get resource config: {e!s}"
        logger.error(error_msg)
        return {"error": error_msg}


@adk_tool
async def search_iam_policies(
    query: str,
    scope: str | None = None,
    project_id: str | None = None,
    page_size: int = 100,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Search IAM policies across resources.

    This tool searches IAM policies to find resources where specific
    principals have access, useful for security investigations.

    Args:
        query: Search query for IAM policies. Supports:
            - policy:roles/editor (role granted)
            - policy:user@example.com (principal has access)
            - policy:serviceAccount:* (any service account)
        scope: Scope to search. Defaults to current project.
        project_id: Project ID for default scope.
        page_size: Maximum results to return.
        tool_context: ADK ToolContext for credential propagation.

    Returns:
        BaseToolResponse with matching IAM policies.

    Example:
        search_iam_policies("policy:roles/owner")
    """
    from fastapi.concurrency import run_in_threadpool

    if not project_id:
        project_id = get_current_project_id()

    if not project_id and not scope:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="Either project_id or scope is required.",
        )

    if not scope:
        scope = f"projects/{project_id}"

    result = await run_in_threadpool(
        _search_iam_policies_sync,
        query,
        scope,
        page_size,
        tool_context,
    )

    if isinstance(result, dict) and "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _search_iam_policies_sync(
    query: str,
    scope: str,
    page_size: int,
    tool_context: Any = None,
) -> dict[str, Any]:
    """Synchronous implementation of search_iam_policies."""
    try:
        session = _get_authorized_session(tool_context)

        url = f"https://cloudasset.googleapis.com/v1/{scope}:searchAllIamPolicies"

        params: dict[str, Any] = {
            "query": query,
            "pageSize": min(page_size, 500),
        }

        response = session.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        results = data.get("results", [])

        result: dict[str, Any] = {
            "scope": scope,
            "query": query,
            "policy_count": len(results),
            "policies": [],
        }

        for policy_result in results:
            policy_info = {
                "resource": policy_result.get("resource"),
                "asset_type": policy_result.get("assetType"),
                "project": policy_result.get("project"),
                "folders": policy_result.get("folders", []),
                "organization": policy_result.get("organization"),
                "policy": policy_result.get("policy", {}),
            }
            result["policies"].append(policy_info)

        return result

    except Exception as e:
        error_msg = f"Failed to search IAM policies: {e!s}"
        logger.error(error_msg)
        return {"error": error_msg}
