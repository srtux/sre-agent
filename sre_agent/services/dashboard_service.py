"""Dashboard management service.

Provides CRUD operations for dashboards with local persistence and
Cloud Monitoring integration. Dashboards follow the Perses-compatible
spec defined in sre_agent.models.dashboard.

Includes support for:
- OOTB (out-of-the-box) dashboard templates for cloud services
- Custom panel creation (metric charts, log panels, trace lists)
"""

import copy
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sre_agent.models.dashboard import DashboardSource

logger = logging.getLogger(__name__)

# In-memory dashboard store (replaced by DB in production)
_dashboard_store: dict[str, dict[str, Any]] = {}


class DashboardService:
    """Service for managing dashboards."""

    def __init__(self) -> None:
        """Initialize the dashboard service."""
        self._store = _dashboard_store

    async def list_dashboards(
        self,
        project_id: str | None = None,
        include_cloud: bool = True,
        page_size: int = 50,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """List all dashboards (local + Cloud Monitoring).

        Args:
            project_id: GCP project ID for cloud dashboards.
            include_cloud: Whether to include Cloud Monitoring dashboards.
            page_size: Maximum number of results.
            page_token: Pagination token.

        Returns:
            Dict with dashboards list and pagination info.
        """
        dashboards: list[dict[str, Any]] = []

        # Local dashboards
        for dash_id, dash_data in self._store.items():
            dashboards.append(
                {
                    "id": dash_id,
                    "display_name": dash_data.get("display_name", "Untitled"),
                    "description": dash_data.get("description", ""),
                    "source": dash_data.get("source", DashboardSource.LOCAL.value),
                    "panel_count": len(dash_data.get("panels", [])),
                    "metadata": dash_data.get("metadata", {}),
                    "labels": dash_data.get("labels", {}),
                }
            )

        # Cloud Monitoring dashboards
        if include_cloud and project_id:
            try:
                cloud_dashboards = await self._list_cloud_dashboards(project_id)
                dashboards.extend(cloud_dashboards)
            except Exception as e:
                logger.warning(f"Failed to fetch cloud dashboards: {e}")

        # Sort by updated_at descending
        dashboards.sort(
            key=lambda d: d.get("metadata", {}).get("updated_at", ""),
            reverse=True,
        )

        return {
            "dashboards": dashboards[:page_size],
            "total_count": len(dashboards),
            "next_page_token": None,
        }

    async def get_dashboard(self, dashboard_id: str) -> dict[str, Any] | None:
        """Get a dashboard by ID.

        Args:
            dashboard_id: Dashboard identifier.

        Returns:
            Dashboard data dict or None if not found.
        """
        return self._store.get(dashboard_id)

    async def create_dashboard(
        self,
        display_name: str,
        description: str = "",
        panels: list[dict[str, Any]] | None = None,
        variables: list[dict[str, Any]] | None = None,
        filters: list[dict[str, Any]] | None = None,
        time_range: dict[str, Any] | None = None,
        labels: dict[str, str] | None = None,
        project_id: str | None = None,
        source: str = "local",
    ) -> dict[str, Any]:
        """Create a new dashboard.

        Args:
            display_name: Dashboard title.
            description: Dashboard description.
            panels: Initial panel configurations.
            variables: Dashboard variables.
            filters: Dashboard filters.
            time_range: Default time range.
            labels: Dashboard labels.
            project_id: GCP project ID.
            source: Dashboard source type.

        Returns:
            Created dashboard data.
        """
        dashboard_id = uuid.uuid4().hex[:12]
        now = datetime.now(timezone.utc).isoformat()

        dashboard_data: dict[str, Any] = {
            "id": dashboard_id,
            "name": f"projects/{project_id or 'local'}/dashboards/{dashboard_id}",
            "display_name": display_name,
            "description": description,
            "source": source,
            "project_id": project_id,
            "panels": panels or [],
            "variables": variables or [],
            "filters": filters or [],
            "time_range": time_range or {"preset": "1h"},
            "labels": labels or {},
            "grid_columns": 24,
            "metadata": {
                "created_at": now,
                "updated_at": now,
                "version": 1,
                "tags": [],
                "starred": False,
            },
        }

        self._store[dashboard_id] = dashboard_data
        logger.info(f"Created dashboard '{display_name}' with ID {dashboard_id}")
        return dashboard_data

    async def update_dashboard(
        self,
        dashboard_id: str,
        updates: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Update an existing dashboard.

        Args:
            dashboard_id: Dashboard identifier.
            updates: Fields to update.

        Returns:
            Updated dashboard data or None if not found.
        """
        dashboard = self._store.get(dashboard_id)
        if not dashboard:
            return None

        now = datetime.now(timezone.utc).isoformat()

        # Apply updates
        for key, value in updates.items():
            if value is not None and key not in ("id", "name", "source"):
                dashboard[key] = value

        # Update metadata
        metadata = dashboard.get("metadata", {})
        metadata["updated_at"] = now
        metadata["version"] = metadata.get("version", 0) + 1
        dashboard["metadata"] = metadata

        self._store[dashboard_id] = dashboard
        logger.info(f"Updated dashboard {dashboard_id}")
        return dashboard

    async def delete_dashboard(self, dashboard_id: str) -> bool:
        """Delete a dashboard.

        Args:
            dashboard_id: Dashboard identifier.

        Returns:
            True if deleted, False if not found.
        """
        if dashboard_id in self._store:
            del self._store[dashboard_id]
            logger.info(f"Deleted dashboard {dashboard_id}")
            return True
        return False

    async def add_panel(
        self,
        dashboard_id: str,
        panel: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Add a panel to a dashboard.

        Args:
            dashboard_id: Target dashboard ID.
            panel: Panel configuration dict.

        Returns:
            Updated dashboard or None if not found.
        """
        dashboard = self._store.get(dashboard_id)
        if not dashboard:
            return None

        panels = list(dashboard.get("panels", []))

        # Auto-assign panel ID if not present
        if "id" not in panel:
            panel["id"] = f"panel-{uuid.uuid4().hex[:8]}"

        # Auto-position if grid_position not set
        if "grid_position" not in panel:
            panel["grid_position"] = self._find_next_position(panels)

        panels.append(panel)
        dashboard["panels"] = panels

        now = datetime.now(timezone.utc).isoformat()
        metadata = dashboard.get("metadata", {})
        metadata["updated_at"] = now
        dashboard["metadata"] = metadata

        self._store[dashboard_id] = dashboard
        return dashboard

    async def remove_panel(
        self,
        dashboard_id: str,
        panel_id: str,
    ) -> dict[str, Any] | None:
        """Remove a panel from a dashboard.

        Args:
            dashboard_id: Dashboard ID.
            panel_id: Panel ID to remove.

        Returns:
            Updated dashboard or None if not found.
        """
        dashboard = self._store.get(dashboard_id)
        if not dashboard:
            return None

        panels = [p for p in dashboard.get("panels", []) if p.get("id") != panel_id]
        dashboard["panels"] = panels

        now = datetime.now(timezone.utc).isoformat()
        metadata = dashboard.get("metadata", {})
        metadata["updated_at"] = now
        dashboard["metadata"] = metadata

        self._store[dashboard_id] = dashboard
        return dashboard

    async def update_panel_position(
        self,
        dashboard_id: str,
        panel_id: str,
        grid_position: dict[str, int],
    ) -> dict[str, Any] | None:
        """Update a panel's position in the grid.

        Args:
            dashboard_id: Dashboard ID.
            panel_id: Panel ID.
            grid_position: New position {x, y, width, height}.

        Returns:
            Updated dashboard or None if not found.
        """
        dashboard = self._store.get(dashboard_id)
        if not dashboard:
            return None

        panels = dashboard.get("panels", [])
        for panel in panels:
            if panel.get("id") == panel_id:
                panel["grid_position"] = grid_position
                break

        now = datetime.now(timezone.utc).isoformat()
        metadata = dashboard.get("metadata", {})
        metadata["updated_at"] = now
        dashboard["metadata"] = metadata

        self._store[dashboard_id] = dashboard
        return dashboard

    def _find_next_position(self, panels: list[dict[str, Any]]) -> dict[str, int]:
        """Find the next available position in the grid."""
        if not panels:
            return {"x": 0, "y": 0, "width": 12, "height": 4}

        max_y = 0
        max_bottom = 0
        for p in panels:
            pos = p.get("grid_position", {})
            bottom = pos.get("y", 0) + pos.get("height", 4)
            if bottom > max_bottom:
                max_bottom = bottom
                max_y = bottom

        return {"x": 0, "y": max_y, "width": 12, "height": 4}

    # -----------------------------------------------------------------
    # OOTB Template provisioning
    # -----------------------------------------------------------------

    async def list_templates(self) -> list[dict[str, Any]]:
        """List available OOTB dashboard templates.

        Returns:
            List of template summaries.
        """
        from sre_agent.services.dashboard_templates import list_templates

        return list_templates()

    async def get_template(self, template_id: str) -> dict[str, Any] | None:
        """Get a full template definition by ID.

        Args:
            template_id: Template identifier.

        Returns:
            Full template dict or None if not found.
        """
        from sre_agent.services.dashboard_templates import get_template

        return get_template(template_id)

    async def provision_template(
        self,
        template_id: str,
        project_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Provision an OOTB template as a local dashboard.

        Creates a new dashboard from a template definition, assigning
        unique IDs to each panel and recording the template source.

        Args:
            template_id: Template identifier (e.g. ``"ootb-gke"``).
            project_id: Optional GCP project ID.

        Returns:
            Created dashboard data, or None if template not found.
        """
        from sre_agent.services.dashboard_templates import get_template

        template = get_template(template_id)
        if template is None:
            return None

        # Deep copy panels so the template is not mutated
        panels = copy.deepcopy(template.get("panels", []))

        # Assign unique IDs to each panel
        for panel in panels:
            panel["id"] = f"panel-{uuid.uuid4().hex[:8]}"

        labels = dict(template.get("labels", {}))
        labels["template_id"] = template_id

        dashboard = await self.create_dashboard(
            display_name=template["display_name"],
            description=template.get("description", ""),
            panels=panels,
            variables=template.get("variables"),
            labels=labels,
            project_id=project_id,
            source="template",
        )

        logger.info(
            "Provisioned template '%s' as dashboard '%s'",
            template_id,
            dashboard["id"],
        )
        return dashboard

    # -----------------------------------------------------------------
    # Custom panel creation
    # -----------------------------------------------------------------

    async def add_custom_metric_panel(
        self,
        dashboard_id: str,
        title: str,
        metric_type: str,
        *,
        resource_type: str | None = None,
        aggregation: str = "ALIGN_MEAN",
        group_by: list[str] | None = None,
        description: str = "",
        unit: str | None = None,
        panel_type: str = "time_series",
        thresholds: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        """Add a metric chart panel to a dashboard.

        Args:
            dashboard_id: Target dashboard ID.
            title: Panel title.
            metric_type: Cloud Monitoring metric type
                (e.g. ``"compute.googleapis.com/instance/cpu/utilization"``).
            resource_type: Monitored resource type filter.
            aggregation: Alignment function.
            group_by: Fields to group by.
            description: Panel description.
            unit: Display unit.
            panel_type: Visualization type (``"time_series"``, ``"gauge"``, etc.).
            thresholds: Visual threshold markers.

        Returns:
            Updated dashboard or None if dashboard not found.
        """
        filter_parts = [f'metric.type="{metric_type}"']
        if resource_type:
            filter_parts.append(f'resource.type="{resource_type}"')
        filter_str = " AND ".join(filter_parts)

        query: dict[str, Any] = {
            "datasource": {"type": "cloud_monitoring"},
            "cloud_monitoring": {
                "filter_str": filter_str,
                "aggregation": aggregation,
            },
        }
        if group_by:
            query["cloud_monitoring"]["group_by_fields"] = group_by

        panel: dict[str, Any] = {
            "title": title,
            "type": panel_type,
            "description": description,
            "queries": [query],
        }
        if unit:
            panel["unit"] = unit
        if thresholds:
            panel["thresholds"] = thresholds

        return await self.add_panel(dashboard_id, panel)

    async def add_custom_log_panel(
        self,
        dashboard_id: str,
        title: str,
        log_filter: str,
        *,
        resource_type: str | None = None,
        severity_levels: list[str] | None = None,
        description: str = "",
    ) -> dict[str, Any] | None:
        """Add a log viewer panel to a dashboard.

        Args:
            dashboard_id: Target dashboard ID.
            title: Panel title.
            log_filter: Cloud Logging filter expression.
            resource_type: Monitored resource type.
            severity_levels: Severity levels to display.
            description: Panel description.

        Returns:
            Updated dashboard or None if dashboard not found.
        """
        query: dict[str, Any] = {
            "datasource": {"type": "loki"},
            "logs": {
                "filter_str": log_filter,
            },
        }
        if severity_levels:
            query["logs"]["severity_levels"] = severity_levels
        if resource_type:
            query["logs"]["resource_type"] = resource_type

        panel: dict[str, Any] = {
            "title": title,
            "type": "logs",
            "description": description,
            "queries": [query],
        }

        return await self.add_panel(dashboard_id, panel)

    async def add_custom_trace_panel(
        self,
        dashboard_id: str,
        title: str,
        trace_filter: str,
        *,
        description: str = "",
    ) -> dict[str, Any] | None:
        """Add a trace list panel to a dashboard.

        Args:
            dashboard_id: Target dashboard ID.
            title: Panel title.
            trace_filter: Trace query filter expression.
            description: Panel description.

        Returns:
            Updated dashboard or None if dashboard not found.
        """
        panel: dict[str, Any] = {
            "title": title,
            "type": "traces",
            "description": description,
            "queries": [
                {
                    "datasource": {"type": "tempo"},
                    "logs": {
                        "filter_str": trace_filter,
                    },
                }
            ],
        }

        return await self.add_panel(dashboard_id, panel)

    async def _list_cloud_dashboards(self, project_id: str) -> list[dict[str, Any]]:
        """Fetch dashboards from Cloud Monitoring API."""
        try:
            from fastapi.concurrency import run_in_threadpool

            from sre_agent.tools.clients.dashboard import (
                _list_dashboards_sync,
            )

            result = await run_in_threadpool(_list_dashboards_sync, project_id, None)
            if isinstance(result, list):
                return [
                    {
                        "id": (
                            d.get("name", "").split("/")[-1] if d.get("name") else ""
                        ),
                        "display_name": d.get("display_name", "Untitled"),
                        "description": "",
                        "source": "cloud_monitoring",
                        "panel_count": d.get("widget_count", 0),
                        "metadata": {
                            "tags": [],
                            "starred": False,
                        },
                        "labels": d.get("labels", {}),
                    }
                    for d in result
                ]
            return []
        except Exception as e:
            logger.warning(f"Failed to list cloud dashboards: {e}")
            return []


# Singleton instance
_service_instance: DashboardService | None = None


def get_dashboard_service() -> DashboardService:
    """Get the dashboard service singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = DashboardService()
    return _service_instance
