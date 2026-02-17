"""Dashboard API router.

Provides REST endpoints for dashboard CRUD operations,
panel management, OOTB template provisioning, custom panel
creation, and Cloud Monitoring integration.
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from sre_agent.services.dashboard_service import get_dashboard_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboards", tags=["dashboards"])


# ---------------------------------------------------------------------------
# Request Bodies
# ---------------------------------------------------------------------------


class CreateDashboardBody(BaseModel):
    """Request body for creating a dashboard."""

    model_config = ConfigDict(frozen=True, extra="forbid")

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

    model_config = ConfigDict(frozen=True, extra="forbid")

    display_name: str | None = None
    description: str | None = None
    panels: list[dict[str, Any]] | None = None
    variables: list[dict[str, Any]] | None = None
    filters: list[dict[str, Any]] | None = None
    time_range: dict[str, Any] | None = None
    labels: dict[str, str] | None = None


class AddPanelBody(BaseModel):
    """Request body for adding a panel."""

    model_config = ConfigDict(frozen=True, extra="forbid")

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

    model_config = ConfigDict(frozen=True, extra="forbid")

    x: int
    y: int
    width: int
    height: int


class ProvisionTemplateBody(BaseModel):
    """Request body for provisioning an OOTB template."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    project_id: str | None = None


class AddMetricPanelBody(BaseModel):
    """Request body for adding a custom metric chart panel."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str = Field(description="Panel display title")
    metric_type: str = Field(
        description="Cloud Monitoring metric type, e.g. "
        '"compute.googleapis.com/instance/cpu/utilization"'
    )
    resource_type: str | None = Field(
        default=None, description="Monitored resource type filter"
    )
    aggregation: str = Field(default="ALIGN_MEAN", description="Alignment function")
    group_by: list[str] | None = Field(default=None, description="Fields to group by")
    description: str = ""
    unit: str | None = None
    panel_type: str = Field(
        default="time_series",
        description="Visualization type (time_series, gauge, stat, bar)",
    )
    thresholds: list[dict[str, Any]] | None = None


class AddLogPanelBody(BaseModel):
    """Request body for adding a custom log panel."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str = Field(description="Panel display title")
    log_filter: str = Field(
        description='Cloud Logging filter, e.g. "resource.type=\\"k8s_container\\""'
    )
    resource_type: str | None = None
    severity_levels: list[str] | None = Field(
        default=None, description="Severity levels to display"
    )
    description: str = ""


class AddTracePanelBody(BaseModel):
    """Request body for adding a custom trace list panel."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    title: str = Field(description="Panel display title")
    trace_filter: str = Field(description="Trace query filter expression")
    description: str = ""


# ---------------------------------------------------------------------------
# Dashboard CRUD Endpoints
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Panel Management Endpoints
# ---------------------------------------------------------------------------


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
    result = await service.update_panel_position(dashboard_id, panel_id, grid_position)
    if not result:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return result


# ---------------------------------------------------------------------------
# OOTB Dashboard Template Endpoints
# ---------------------------------------------------------------------------


@router.get("/templates/list")
async def list_templates() -> dict[str, Any]:
    """List available OOTB dashboard templates.

    Returns summary info for each template including service type,
    panel count, and description.
    """
    service = get_dashboard_service()
    templates = await service.list_templates()
    return {"templates": templates, "total_count": len(templates)}


@router.get("/templates/{template_id}")
async def get_template(template_id: str) -> dict[str, Any]:
    """Get a full OOTB dashboard template definition."""
    service = get_dashboard_service()
    template = await service.get_template(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/templates/{template_id}/provision", status_code=201)
async def provision_template(
    template_id: str,
    body: ProvisionTemplateBody | None = None,
) -> dict[str, Any]:
    """Provision an OOTB template as a new local dashboard.

    Creates a dashboard instance from the template with all panels
    pre-configured. The dashboard can be customized after creation.
    """
    service = get_dashboard_service()
    project_id = body.project_id if body else None
    result = await service.provision_template(template_id, project_id=project_id)
    if not result:
        raise HTTPException(status_code=404, detail="Template not found")
    return result


# ---------------------------------------------------------------------------
# Custom Panel Endpoints (add metric/log/trace panels)
# ---------------------------------------------------------------------------


@router.post("/{dashboard_id}/panels/metric")
async def add_metric_panel(
    dashboard_id: str,
    body: AddMetricPanelBody,
) -> dict[str, Any]:
    """Add a custom metric chart panel to a dashboard.

    Creates a panel configured to query Cloud Monitoring for the
    specified metric type with optional resource filtering, aggregation,
    and threshold markers.
    """
    service = get_dashboard_service()
    result = await service.add_custom_metric_panel(
        dashboard_id,
        title=body.title,
        metric_type=body.metric_type,
        resource_type=body.resource_type,
        aggregation=body.aggregation,
        group_by=body.group_by,
        description=body.description,
        unit=body.unit,
        panel_type=body.panel_type,
        thresholds=body.thresholds,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return result


@router.post("/{dashboard_id}/panels/log")
async def add_log_panel(
    dashboard_id: str,
    body: AddLogPanelBody,
) -> dict[str, Any]:
    """Add a custom log viewer panel to a dashboard.

    Creates a panel configured to display Cloud Logging entries
    matching the specified filter with optional severity filtering.
    """
    service = get_dashboard_service()
    result = await service.add_custom_log_panel(
        dashboard_id,
        title=body.title,
        log_filter=body.log_filter,
        resource_type=body.resource_type,
        severity_levels=body.severity_levels,
        description=body.description,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return result


@router.post("/{dashboard_id}/panels/trace")
async def add_trace_panel(
    dashboard_id: str,
    body: AddTracePanelBody,
) -> dict[str, Any]:
    """Add a custom trace list panel to a dashboard.

    Creates a panel configured to display distributed traces
    matching the specified filter expression.
    """
    service = get_dashboard_service()
    result = await service.add_custom_trace_panel(
        dashboard_id,
        title=body.title,
        trace_filter=body.trace_filter,
        description=body.description,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    return result
