"""Cloud Monitoring Dashboard API client.

Provides tools for managing Google Cloud Monitoring dashboards via the
Dashboard API. Supports listing, creating, getting, and deleting dashboards.
"""

import json
import logging
import os
import uuid
from typing import Any

from sre_agent.auth import (
    get_credentials_from_tool_context,
    get_current_project_id,
)
from sre_agent.schema import BaseToolResponse, ToolStatus
from sre_agent.tools.common import adk_tool

logger = logging.getLogger(__name__)


@adk_tool
async def list_cloud_dashboards(
    project_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Lists all Cloud Monitoring dashboards in a GCP project.

    Returns a list of dashboard summaries including name, display_name,
    and layout type. Useful for discovering existing dashboards before
    adding widgets or for displaying in the dashboard list view.

    Args:
        project_id: The Google Cloud Project ID. Defaults to current context.
        tool_context: Context object for tool execution.

    Returns:
        Standardized response with list of dashboard summaries.
    """
    from sre_agent.auth import is_guest_mode

    if is_guest_mode():
        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=_get_sample_dashboards(),
        )

    from fastapi.concurrency import run_in_threadpool

    if not project_id:
        project_id = get_current_project_id()
        if not project_id:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error="Project ID is required. Set GOOGLE_CLOUD_PROJECT or pass project_id.",
            )

    result = await run_in_threadpool(
        _list_dashboards_sync, project_id, tool_context
    )
    if isinstance(result, dict) and "error" in result:
        return BaseToolResponse(status=ToolStatus.ERROR, error=result["error"])
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _list_dashboards_sync(
    project_id: str,
    tool_context: Any = None,
) -> list[dict[str, Any]] | dict[str, Any]:
    """Synchronous implementation of list_dashboards."""
    try:
        from google.cloud.monitoring_dashboard_v1 import DashboardsServiceClient
        from google.cloud.monitoring_dashboard_v1.types import (
            ListDashboardsRequest,
        )

        credentials = get_credentials_from_tool_context(tool_context)
        client_kwargs: dict[str, Any] = {}
        if credentials:
            client_kwargs["credentials"] = credentials

        client = DashboardsServiceClient(**client_kwargs)
        parent = f"projects/{project_id}"

        request = ListDashboardsRequest(parent=parent)
        dashboards = []

        for dashboard in client.list_dashboards(request=request):
            layout_type = "unknown"
            if dashboard.grid_layout and dashboard.grid_layout.widgets:
                layout_type = "grid"
            elif dashboard.mosaic_layout and dashboard.mosaic_layout.tiles:
                layout_type = "mosaic"
            elif dashboard.row_layout and dashboard.row_layout.rows:
                layout_type = "row"
            elif dashboard.column_layout and dashboard.column_layout.columns:
                layout_type = "column"

            widget_count = _count_widgets(dashboard)

            dashboards.append(
                {
                    "name": dashboard.name,
                    "display_name": dashboard.display_name,
                    "etag": dashboard.etag,
                    "layout_type": layout_type,
                    "widget_count": widget_count,
                    "labels": (
                        dict(dashboard.labels) if dashboard.labels else {}
                    ),
                    "source": "cloud_monitoring",
                }
            )

        return dashboards

    except Exception as e:
        error_str = str(e)
        is_eval = (
            os.getenv("SRE_AGENT_EVAL_MODE", "false").lower() == "true"
        )
        if is_eval and any(
            code in error_str
            for code in ["403", "404", "PermissionDenied"]
        ):
            logger.warning(
                f"Dashboard API error in eval mode: {error_str}"
            )
            return []
        logger.error(
            f"Failed to list dashboards: {error_str}", exc_info=True
        )
        return {"error": f"Failed to list dashboards: {error_str}"}


def _count_widgets(dashboard: Any) -> int:
    """Count total widgets in a dashboard regardless of layout type."""
    count = 0
    if dashboard.grid_layout:
        count = len(dashboard.grid_layout.widgets)
    elif dashboard.mosaic_layout:
        count = len(dashboard.mosaic_layout.tiles)
    elif dashboard.row_layout:
        for row in dashboard.row_layout.rows:
            count += len(row.widgets)
    elif dashboard.column_layout:
        for col in dashboard.column_layout.columns:
            count += len(col.widgets)
    return count


@adk_tool
async def get_cloud_dashboard(
    dashboard_name: str,
    project_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Gets a specific Cloud Monitoring dashboard by name.

    Args:
        dashboard_name: Dashboard resource name or ID.
            Can be full path like 'projects/my-project/dashboards/abc123'
            or just the dashboard ID 'abc123'.
        project_id: The Google Cloud Project ID (used if dashboard_name is just an ID).
        tool_context: Context object for tool execution.

    Returns:
        Standardized response with dashboard details.
    """
    from sre_agent.auth import is_guest_mode

    if is_guest_mode():
        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=_get_sample_dashboard_detail(),
        )

    from fastapi.concurrency import run_in_threadpool

    if not dashboard_name.startswith("projects/"):
        if not project_id:
            project_id = get_current_project_id()
        if not project_id:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error="Project ID is required when passing a dashboard ID without full resource path.",
            )
        dashboard_name = (
            f"projects/{project_id}/dashboards/{dashboard_name}"
        )

    result = await run_in_threadpool(
        _get_dashboard_sync, dashboard_name, tool_context
    )
    if isinstance(result, dict) and "error" in result:
        return BaseToolResponse(
            status=ToolStatus.ERROR, error=result["error"]
        )
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _get_dashboard_sync(
    dashboard_name: str,
    tool_context: Any = None,
) -> dict[str, Any]:
    """Synchronous implementation of get_dashboard."""
    try:
        from google.cloud.monitoring_dashboard_v1 import (
            DashboardsServiceClient,
        )
        from google.cloud.monitoring_dashboard_v1.types import (
            GetDashboardRequest,
        )
        from google.protobuf.json_format import MessageToDict

        credentials = get_credentials_from_tool_context(tool_context)
        client_kwargs: dict[str, Any] = {}
        if credentials:
            client_kwargs["credentials"] = credentials

        client = DashboardsServiceClient(**client_kwargs)
        request = GetDashboardRequest(name=dashboard_name)
        dashboard = client.get_dashboard(request=request)

        # Convert protobuf to dict for JSON serialization
        dashboard_dict = MessageToDict(
            dashboard._pb,
            preserving_proto_field_name=True,
        )
        dashboard_dict["source"] = "cloud_monitoring"
        return dashboard_dict

    except Exception as e:
        error_str = str(e)
        logger.error(
            f"Failed to get dashboard: {error_str}", exc_info=True
        )
        return {
            "error": f"Failed to get dashboard {dashboard_name}: {error_str}"
        }


@adk_tool
async def create_cloud_dashboard(
    display_name: str,
    widgets_json: str | None = None,
    project_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Creates a new Cloud Monitoring dashboard.

    Creates a dashboard with a MosaicLayout (most flexible layout type).

    Args:
        display_name: Human-readable name for the dashboard.
        widgets_json: Optional JSON string with widget definitions.
            If not provided, creates an empty dashboard.
        project_id: The Google Cloud Project ID.
        tool_context: Context object for tool execution.

    Returns:
        Standardized response with the created dashboard details.
    """
    from sre_agent.auth import is_guest_mode

    if is_guest_mode():
        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={
                "name": f"projects/demo-project/dashboards/{uuid.uuid4().hex[:12]}",
                "display_name": display_name,
                "message": "Dashboard created (demo mode)",
            },
        )

    from fastapi.concurrency import run_in_threadpool

    if not project_id:
        project_id = get_current_project_id()
        if not project_id:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error="Project ID is required.",
            )

    result = await run_in_threadpool(
        _create_dashboard_sync,
        project_id,
        display_name,
        widgets_json,
        tool_context,
    )
    if isinstance(result, dict) and "error" in result:
        return BaseToolResponse(
            status=ToolStatus.ERROR, error=result["error"]
        )
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _create_dashboard_sync(
    project_id: str,
    display_name: str,
    widgets_json: str | None = None,
    tool_context: Any = None,
) -> dict[str, Any]:
    """Synchronous implementation of create_dashboard."""
    try:
        from google.cloud.monitoring_dashboard_v1 import (
            DashboardsServiceClient,
        )
        from google.cloud.monitoring_dashboard_v1.types import (
            CreateDashboardRequest,
            Dashboard,
        )
        from google.protobuf.json_format import MessageToDict, ParseDict

        credentials = get_credentials_from_tool_context(tool_context)
        client_kwargs: dict[str, Any] = {}
        if credentials:
            client_kwargs["credentials"] = credentials

        client = DashboardsServiceClient(**client_kwargs)
        parent = f"projects/{project_id}"

        dashboard_dict: dict[str, Any] = {
            "display_name": display_name,
            "mosaic_layout": {
                "columns": 48,
                "tiles": [],
            },
        }

        if widgets_json:
            try:
                tiles = json.loads(widgets_json)
                if isinstance(tiles, list):
                    dashboard_dict["mosaic_layout"]["tiles"] = tiles
            except json.JSONDecodeError:
                logger.warning(
                    "Invalid widgets_json, creating empty dashboard"
                )

        dashboard = Dashboard()
        ParseDict(dashboard_dict, dashboard._pb)

        request = CreateDashboardRequest(
            parent=parent, dashboard=dashboard
        )
        created = client.create_dashboard(request=request)

        result = MessageToDict(
            created._pb, preserving_proto_field_name=True
        )
        result["source"] = "cloud_monitoring"
        return result

    except Exception as e:
        error_str = str(e)
        logger.error(
            f"Failed to create dashboard: {error_str}", exc_info=True
        )
        return {"error": f"Failed to create dashboard: {error_str}"}


@adk_tool
async def delete_cloud_dashboard(
    dashboard_name: str,
    project_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Deletes a Cloud Monitoring dashboard.

    Args:
        dashboard_name: Dashboard resource name or ID.
        project_id: The Google Cloud Project ID (used if dashboard_name is just an ID).
        tool_context: Context object for tool execution.

    Returns:
        Standardized response confirming deletion.
    """
    from sre_agent.auth import is_guest_mode

    if is_guest_mode():
        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={
                "message": f"Dashboard {dashboard_name} deleted (demo mode)"
            },
        )

    from fastapi.concurrency import run_in_threadpool

    if not dashboard_name.startswith("projects/"):
        if not project_id:
            project_id = get_current_project_id()
        if not project_id:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error="Project ID is required when passing a dashboard ID without full resource path.",
            )
        dashboard_name = (
            f"projects/{project_id}/dashboards/{dashboard_name}"
        )

    result = await run_in_threadpool(
        _delete_dashboard_sync, dashboard_name, tool_context
    )
    if isinstance(result, dict) and "error" in result:
        return BaseToolResponse(
            status=ToolStatus.ERROR, error=result["error"]
        )
    return BaseToolResponse(status=ToolStatus.SUCCESS, result=result)


def _delete_dashboard_sync(
    dashboard_name: str,
    tool_context: Any = None,
) -> dict[str, Any]:
    """Synchronous implementation of delete_dashboard."""
    try:
        from google.cloud.monitoring_dashboard_v1 import (
            DashboardsServiceClient,
        )
        from google.cloud.monitoring_dashboard_v1.types import (
            DeleteDashboardRequest,
        )

        credentials = get_credentials_from_tool_context(tool_context)
        client_kwargs: dict[str, Any] = {}
        if credentials:
            client_kwargs["credentials"] = credentials

        client = DashboardsServiceClient(**client_kwargs)
        request = DeleteDashboardRequest(name=dashboard_name)
        client.delete_dashboard(request=request)

        return {
            "message": f"Dashboard {dashboard_name} deleted successfully"
        }

    except Exception as e:
        error_str = str(e)
        logger.error(
            f"Failed to delete dashboard: {error_str}", exc_info=True
        )
        return {
            "error": f"Failed to delete dashboard {dashboard_name}: {error_str}"
        }


# --- Sample data for guest/demo mode ---


def _get_sample_dashboards() -> list[dict[str, Any]]:
    """Return sample dashboards for guest mode."""
    return [
        {
            "name": "projects/demo-project/dashboards/sample-infra",
            "display_name": "Infrastructure Overview",
            "layout_type": "mosaic",
            "widget_count": 8,
            "labels": {"environment": "production"},
            "source": "cloud_monitoring",
        },
        {
            "name": "projects/demo-project/dashboards/sample-gke",
            "display_name": "GKE Cluster Health",
            "layout_type": "grid",
            "widget_count": 12,
            "labels": {"service": "kubernetes"},
            "source": "cloud_monitoring",
        },
        {
            "name": "projects/demo-project/dashboards/sample-slo",
            "display_name": "Service Level Objectives",
            "layout_type": "mosaic",
            "widget_count": 6,
            "labels": {"type": "slo"},
            "source": "cloud_monitoring",
        },
    ]


def _get_sample_dashboard_detail() -> dict[str, Any]:
    """Return sample dashboard detail for guest mode."""
    return {
        "name": "projects/demo-project/dashboards/sample-infra",
        "display_name": "Infrastructure Overview",
        "etag": "sample-etag-123",
        "mosaic_layout": {
            "columns": 48,
            "tiles": [
                {
                    "x_pos": 0,
                    "y_pos": 0,
                    "width": 24,
                    "height": 8,
                    "widget": {
                        "title": "CPU Utilization",
                        "xy_chart": {
                            "data_sets": [
                                {
                                    "time_series_query": {
                                        "time_series_filter": {
                                            "filter": 'metric.type="compute.googleapis.com/instance/cpu/utilization"',
                                            "aggregation": {
                                                "per_series_aligner": "ALIGN_MEAN",
                                                "alignment_period": "60s",
                                            },
                                        },
                                    },
                                    "plot_type": "LINE",
                                }
                            ],
                        },
                    },
                },
            ],
        },
        "source": "cloud_monitoring",
    }
