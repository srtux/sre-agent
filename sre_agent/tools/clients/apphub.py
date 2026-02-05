"""AppHub Client for App-Centric Operations.

This module provides tools for interacting with Google Cloud AppHub,
enabling the SRE agent to be application-aware when querying telemetry
and troubleshooting issues.

AppHub organizes GCP resources into logical Applications, Services, and
Workloads, providing a business-centric view of infrastructure.

Reference: https://cloud.google.com/app-hub/docs/overview
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
async def list_applications(
    project_id: str | None = None,
    location: str = "global",
    tool_context: Any = None,
) -> BaseToolResponse:
    """List all applications registered in AppHub.

    Applications are the top-level governance boundary in AppHub,
    representing logical business functions composed of services and workloads.

    Args:
        project_id: Host project ID for AppHub. Uses current context if not provided.
        location: Location for the applications (default: global).
        tool_context: ADK ToolContext for credential propagation.

    Returns:
        BaseToolResponse with list of applications.

    Example:
        list_applications(project_id="my-host-project")
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
        _list_applications_sync,
        project_id,
        location,
        tool_context,
    )

    if isinstance(result, dict) and "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _list_applications_sync(
    project_id: str,
    location: str,
    tool_context: Any = None,
) -> dict[str, Any]:
    """Synchronous implementation of list_applications."""
    try:
        session = _get_authorized_session(tool_context)

        url = f"https://apphub.googleapis.com/v1/projects/{project_id}/locations/{location}/applications"

        response = session.get(url)
        response.raise_for_status()
        data = response.json()

        applications = data.get("applications", [])

        result: dict[str, Any] = {
            "project_id": project_id,
            "location": location,
            "application_count": len(applications),
            "applications": [],
        }

        for app in applications:
            app_info = {
                "name": app.get("name"),
                "display_name": app.get("displayName"),
                "description": app.get("description"),
                "uid": app.get("uid"),
                "state": app.get("state"),
                "create_time": app.get("createTime"),
                "update_time": app.get("updateTime"),
                "attributes": app.get("attributes", {}),
                "scope": app.get("scope", {}),
            }
            result["applications"].append(app_info)

        return result

    except Exception as e:
        error_msg = f"Failed to list applications: {e!s}"
        logger.error(error_msg)
        return {"error": error_msg}


@adk_tool
async def get_application(
    application_id: str,
    project_id: str | None = None,
    location: str = "global",
    tool_context: Any = None,
) -> BaseToolResponse:
    """Get details of a specific application.

    Args:
        application_id: ID of the application.
        project_id: Host project ID for AppHub.
        location: Location for the application (default: global).
        tool_context: ADK ToolContext for credential propagation.

    Returns:
        BaseToolResponse with application details.

    Example:
        get_application("my-app", project_id="my-host-project")
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
        _get_application_sync,
        project_id,
        location,
        application_id,
        tool_context,
    )

    if isinstance(result, dict) and "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _get_application_sync(
    project_id: str,
    location: str,
    application_id: str,
    tool_context: Any = None,
) -> dict[str, Any]:
    """Synchronous implementation of get_application."""
    try:
        session = _get_authorized_session(tool_context)

        url = f"https://apphub.googleapis.com/v1/projects/{project_id}/locations/{location}/applications/{application_id}"

        response = session.get(url)
        response.raise_for_status()
        app = response.json()

        result: dict[str, Any] = {
            "name": app.get("name"),
            "display_name": app.get("displayName"),
            "description": app.get("description"),
            "uid": app.get("uid"),
            "state": app.get("state"),
            "create_time": app.get("createTime"),
            "update_time": app.get("updateTime"),
            "attributes": app.get("attributes", {}),
            "scope": app.get("scope", {}),
        }

        return result

    except Exception as e:
        error_msg = f"Failed to get application: {e!s}"
        logger.error(error_msg)
        return {"error": error_msg}


@adk_tool
async def list_services(
    application_id: str,
    project_id: str | None = None,
    location: str = "global",
    tool_context: Any = None,
) -> BaseToolResponse:
    """List all services registered to an application.

    Services represent network or API interfaces that expose functionality
    to clients, such as Cloud Run services, load balancers, or databases.

    Args:
        application_id: ID of the application.
        project_id: Host project ID for AppHub.
        location: Location for the application (default: global).
        tool_context: ADK ToolContext for credential propagation.

    Returns:
        BaseToolResponse with list of services.

    Example:
        list_services("my-app", project_id="my-host-project")
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
        _list_services_sync,
        project_id,
        location,
        application_id,
        tool_context,
    )

    if isinstance(result, dict) and "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _list_services_sync(
    project_id: str,
    location: str,
    application_id: str,
    tool_context: Any = None,
) -> dict[str, Any]:
    """Synchronous implementation of list_services."""
    try:
        session = _get_authorized_session(tool_context)

        url = f"https://apphub.googleapis.com/v1/projects/{project_id}/locations/{location}/applications/{application_id}/services"

        response = session.get(url)
        response.raise_for_status()
        data = response.json()

        services = data.get("services", [])

        result: dict[str, Any] = {
            "application_id": application_id,
            "service_count": len(services),
            "services": [],
        }

        for svc in services:
            svc_info = {
                "name": svc.get("name"),
                "display_name": svc.get("displayName"),
                "description": svc.get("description"),
                "uid": svc.get("uid"),
                "state": svc.get("state"),
                "service_reference": svc.get("serviceReference", {}),
                "service_properties": svc.get("serviceProperties", {}),
                "attributes": svc.get("attributes", {}),
                "create_time": svc.get("createTime"),
                "update_time": svc.get("updateTime"),
            }
            result["services"].append(svc_info)

        return result

    except Exception as e:
        error_msg = f"Failed to list services: {e!s}"
        logger.error(error_msg)
        return {"error": error_msg}


@adk_tool
async def list_workloads(
    application_id: str,
    project_id: str | None = None,
    location: str = "global",
    tool_context: Any = None,
) -> BaseToolResponse:
    """List all workloads registered to an application.

    Workloads represent binary deployments like Managed Instance Groups,
    GKE deployments, or Cloud Run jobs that perform business logic.

    Args:
        application_id: ID of the application.
        project_id: Host project ID for AppHub.
        location: Location for the application (default: global).
        tool_context: ADK ToolContext for credential propagation.

    Returns:
        BaseToolResponse with list of workloads.

    Example:
        list_workloads("my-app", project_id="my-host-project")
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
        _list_workloads_sync,
        project_id,
        location,
        application_id,
        tool_context,
    )

    if isinstance(result, dict) and "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _list_workloads_sync(
    project_id: str,
    location: str,
    application_id: str,
    tool_context: Any = None,
) -> dict[str, Any]:
    """Synchronous implementation of list_workloads."""
    try:
        session = _get_authorized_session(tool_context)

        url = f"https://apphub.googleapis.com/v1/projects/{project_id}/locations/{location}/applications/{application_id}/workloads"

        response = session.get(url)
        response.raise_for_status()
        data = response.json()

        workloads = data.get("workloads", [])

        result: dict[str, Any] = {
            "application_id": application_id,
            "workload_count": len(workloads),
            "workloads": [],
        }

        for wl in workloads:
            wl_info = {
                "name": wl.get("name"),
                "display_name": wl.get("displayName"),
                "description": wl.get("description"),
                "uid": wl.get("uid"),
                "state": wl.get("state"),
                "workload_reference": wl.get("workloadReference", {}),
                "workload_properties": wl.get("workloadProperties", {}),
                "attributes": wl.get("attributes", {}),
                "create_time": wl.get("createTime"),
                "update_time": wl.get("updateTime"),
            }
            result["workloads"].append(wl_info)

        return result

    except Exception as e:
        error_msg = f"Failed to list workloads: {e!s}"
        logger.error(error_msg)
        return {"error": error_msg}


@adk_tool
async def list_discovered_services(
    project_id: str | None = None,
    location: str = "global",
    tool_context: Any = None,
) -> BaseToolResponse:
    """List services discovered but not yet registered to an application.

    Discovered services are infrastructure resources that could be
    registered as services in AppHub applications.

    Args:
        project_id: Host project ID for AppHub.
        location: Location to search (default: global).
        tool_context: ADK ToolContext for credential propagation.

    Returns:
        BaseToolResponse with list of discovered services.

    Example:
        list_discovered_services(project_id="my-host-project")
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
        _list_discovered_services_sync,
        project_id,
        location,
        tool_context,
    )

    if isinstance(result, dict) and "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _list_discovered_services_sync(
    project_id: str,
    location: str,
    tool_context: Any = None,
) -> dict[str, Any]:
    """Synchronous implementation of list_discovered_services."""
    try:
        session = _get_authorized_session(tool_context)

        url = f"https://apphub.googleapis.com/v1/projects/{project_id}/locations/{location}/discoveredServices"

        response = session.get(url)
        response.raise_for_status()
        data = response.json()

        services = data.get("discoveredServices", [])

        result: dict[str, Any] = {
            "project_id": project_id,
            "location": location,
            "discovered_count": len(services),
            "discovered_services": [],
        }

        for svc in services:
            svc_info = {
                "name": svc.get("name"),
                "service_reference": svc.get("serviceReference", {}),
                "service_properties": svc.get("serviceProperties", {}),
            }
            result["discovered_services"].append(svc_info)

        return result

    except Exception as e:
        error_msg = f"Failed to list discovered services: {e!s}"
        logger.error(error_msg)
        return {"error": error_msg}


@adk_tool
async def list_discovered_workloads(
    project_id: str | None = None,
    location: str = "global",
    tool_context: Any = None,
) -> BaseToolResponse:
    """List workloads discovered but not yet registered to an application.

    Discovered workloads are infrastructure resources that could be
    registered as workloads in AppHub applications.

    Args:
        project_id: Host project ID for AppHub.
        location: Location to search (default: global).
        tool_context: ADK ToolContext for credential propagation.

    Returns:
        BaseToolResponse with list of discovered workloads.

    Example:
        list_discovered_workloads(project_id="my-host-project")
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
        _list_discovered_workloads_sync,
        project_id,
        location,
        tool_context,
    )

    if isinstance(result, dict) and "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _list_discovered_workloads_sync(
    project_id: str,
    location: str,
    tool_context: Any = None,
) -> dict[str, Any]:
    """Synchronous implementation of list_discovered_workloads."""
    try:
        session = _get_authorized_session(tool_context)

        url = f"https://apphub.googleapis.com/v1/projects/{project_id}/locations/{location}/discoveredWorkloads"

        response = session.get(url)
        response.raise_for_status()
        data = response.json()

        workloads = data.get("discoveredWorkloads", [])

        result: dict[str, Any] = {
            "project_id": project_id,
            "location": location,
            "discovered_count": len(workloads),
            "discovered_workloads": [],
        }

        for wl in workloads:
            wl_info = {
                "name": wl.get("name"),
                "workload_reference": wl.get("workloadReference", {}),
                "workload_properties": wl.get("workloadProperties", {}),
            }
            result["discovered_workloads"].append(wl_info)

        return result

    except Exception as e:
        error_msg = f"Failed to list discovered workloads: {e!s}"
        logger.error(error_msg)
        return {"error": error_msg}


@adk_tool
async def get_application_topology(
    application_id: str,
    project_id: str | None = None,
    location: str = "global",
    tool_context: Any = None,
) -> BaseToolResponse:
    """Get the complete topology of an application.

    This tool retrieves all services and workloads in an application,
    providing a complete view of the application's infrastructure.

    Args:
        application_id: ID of the application.
        project_id: Host project ID for AppHub.
        location: Location for the application (default: global).
        tool_context: ADK ToolContext for credential propagation.

    Returns:
        BaseToolResponse with application topology including all services and workloads.

    Example:
        get_application_topology("my-app", project_id="my-host-project")
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
        _get_application_topology_sync,
        project_id,
        location,
        application_id,
        tool_context,
    )

    if isinstance(result, dict) and "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _get_application_topology_sync(
    project_id: str,
    location: str,
    application_id: str,
    tool_context: Any = None,
) -> dict[str, Any]:
    """Synchronous implementation of get_application_topology."""
    try:
        # Get the application details
        app_result = _get_application_sync(
            project_id, location, application_id, tool_context
        )
        if "error" in app_result:
            return app_result

        # Get services
        services_result = _list_services_sync(
            project_id, location, application_id, tool_context
        )
        services = (
            services_result.get("services", [])
            if "error" not in services_result
            else []
        )

        # Get workloads
        workloads_result = _list_workloads_sync(
            project_id, location, application_id, tool_context
        )
        workloads = (
            workloads_result.get("workloads", [])
            if "error" not in workloads_result
            else []
        )

        result: dict[str, Any] = {
            "application": {
                "id": application_id,
                "display_name": app_result.get("display_name"),
                "description": app_result.get("description"),
                "state": app_result.get("state"),
                "attributes": app_result.get("attributes", {}),
            },
            "topology": {
                "service_count": len(services),
                "workload_count": len(workloads),
                "services": services,
                "workloads": workloads,
            },
            "summary": {
                "total_components": len(services) + len(workloads),
                "criticality": app_result.get("attributes", {})
                .get("criticality", {})
                .get("type", "UNSPECIFIED"),
                "environment": app_result.get("attributes", {})
                .get("environment", {})
                .get("type", "UNSPECIFIED"),
            },
        }

        return result

    except Exception as e:
        error_msg = f"Failed to get application topology: {e!s}"
        logger.error(error_msg)
        return {"error": error_msg}
