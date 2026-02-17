"""Dashboard API router.

Provides REST endpoints for dashboard CRUD operations,
panel management, and Cloud Monitoring integration.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sre_agent.services.dashboard_service import get_dashboard_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboards", tags=["dashboards"])


class CreateDashboardBody(BaseModel):
    """Request body for creating a dashboard."""

    display_name: str
    description: str = ""
    panels: list[dict[str, Any]] | None = None
    variables: list[dict[str, Any]] | None = None
    filters: list[dict[str, Any]] | None = None
    time_range: dict[str, Any] | None = None
    labels: dict[str, str] | None = None
    project_id: str | None = None


class UpdateDashboardBody(BaseModel):
    """Request body for updating a dashboard."""

    display_name: str | None = None
    description: str | None = None
    panels: list[dict[str, Any]] | None = None
    variables: list[dict[str, Any]] | None = None
    filters: list[dict[str, Any]] | None = None
    time_range: dict[str, Any] | None = None
    labels: dict[str, str] | None = None


class AddPanelBody(BaseModel):
    """Request body for adding a panel."""

    title: str
    type: str = "time_series"
    description: str = ""
    grid_position: dict[str, int] | None = None
    queries: list[dict[str, Any]] | None = None
    thresholds: list[dict[str, Any]] | None = None
    datasource: dict[str, Any] | None = None
    text_content: dict[str, Any] | None = None


class UpdatePanelPositionBody(BaseModel):
    """Request body for updating panel position."""

    x: int
    y: int
    width: int
    height: int


@router.get("")
async def list_dashboards(
    project_id: str | None = None,
    include_cloud: bool = True,
    page_size: int = 50,
) -> dict[str, Any]:
    """List all dashboards."""
    service = get_dashboard_service()
    return await service.list_dashboards(
        project_id=project_id,
        include_cloud=include_cloud,
        page_size=page_size,
    )


@router.get("/{dashboard_id}")
async def get_dashboard(dashboard_id: str) -> dict[str, Any]:
    """Get a specific dashboard."""
    service = get_dashboard_service()
    dashboard = await service.get_dashboard(dashboard_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return dashboard


@router.post("", status_code=201)
async def create_dashboard(body: CreateDashboardBody) -> dict[str, Any]:
    """Create a new dashboard."""
    service = get_dashboard_service()
    return await service.create_dashboard(
        display_name=body.display_name,
        description=body.description,
        panels=body.panels,
        variables=body.variables,
        filters=body.filters,
        time_range=body.time_range,
        labels=body.labels,
        project_id=body.project_id,
    )


@router.patch("/{dashboard_id}")
async def update_dashboard(
    dashboard_id: str,
    body: UpdateDashboardBody,
) -> dict[str, Any]:
    """Update a dashboard."""
    service = get_dashboard_service()
    updates = body.model_dump(exclude_none=True)
    result = await service.update_dashboard(dashboard_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return result


@router.delete("/{dashboard_id}", status_code=204)
async def delete_dashboard(dashboard_id: str) -> None:
    """Delete a dashboard."""
    service = get_dashboard_service()
    deleted = await service.delete_dashboard(dashboard_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Dashboard not found")


@router.post("/{dashboard_id}/panels")
async def add_panel(
    dashboard_id: str,
    body: AddPanelBody,
) -> dict[str, Any]:
    """Add a panel to a dashboard."""
    service = get_dashboard_service()
    panel_data = body.model_dump(exclude_none=True)
    result = await service.add_panel(dashboard_id, panel_data)
    if not result:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return result


@router.delete("/{dashboard_id}/panels/{panel_id}")
async def remove_panel(
    dashboard_id: str,
    panel_id: str,
) -> dict[str, Any]:
    """Remove a panel from a dashboard."""
    service = get_dashboard_service()
    result = await service.remove_panel(dashboard_id, panel_id)
    if not result:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return result


@router.patch("/{dashboard_id}/panels/{panel_id}/position")
async def update_panel_position(
    dashboard_id: str,
    panel_id: str,
    body: UpdatePanelPositionBody,
) -> dict[str, Any]:
    """Update a panel's grid position."""
    service = get_dashboard_service()
    grid_position = {
        "x": body.x,
        "y": body.y,
        "width": body.width,
        "height": body.height,
    }
    result = await service.update_panel_position(
        dashboard_id, panel_id, grid_position
    )
    if not result:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return result
