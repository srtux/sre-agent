"""Tests for dashboard service."""

import pytest

from sre_agent.services.dashboard_service import (
    DashboardService,
    _dashboard_store,
    get_dashboard_service,
)


@pytest.fixture(autouse=True)
def _clear_store() -> None:
    """Clear the dashboard store before each test."""
    _dashboard_store.clear()


class TestDashboardService:
    @pytest.fixture()
    def service(self) -> DashboardService:
        return DashboardService()

    @pytest.mark.asyncio()
    async def test_list_dashboards_empty_returns_empty(
        self, service: DashboardService
    ) -> None:
        result = await service.list_dashboards(include_cloud=False)
        assert result["dashboards"] == []
        assert result["total_count"] == 0

    @pytest.mark.asyncio()
    async def test_create_dashboard_returns_valid_dashboard(
        self, service: DashboardService
    ) -> None:
        dash = await service.create_dashboard(
            display_name="Test Dashboard",
            description="A test dashboard",
        )
        assert dash["display_name"] == "Test Dashboard"
        assert dash["description"] == "A test dashboard"
        assert "id" in dash
        assert "metadata" in dash
        assert dash["metadata"]["version"] == 1

    @pytest.mark.asyncio()
    async def test_create_dashboard_with_panels(
        self, service: DashboardService
    ) -> None:
        panels = [
            {"title": "Panel 1", "type": "time_series"},
            {"title": "Panel 2", "type": "gauge"},
        ]
        dash = await service.create_dashboard(display_name="With Panels", panels=panels)
        assert len(dash["panels"]) == 2

    @pytest.mark.asyncio()
    async def test_get_dashboard_existing_returns_dashboard(
        self, service: DashboardService
    ) -> None:
        created = await service.create_dashboard(display_name="Get Test")
        result = await service.get_dashboard(created["id"])
        assert result is not None
        assert result["display_name"] == "Get Test"

    @pytest.mark.asyncio()
    async def test_get_dashboard_nonexistent_returns_none(
        self, service: DashboardService
    ) -> None:
        result = await service.get_dashboard("nonexistent")
        assert result is None

    @pytest.mark.asyncio()
    async def test_list_dashboards_returns_all_local(
        self, service: DashboardService
    ) -> None:
        await service.create_dashboard(display_name="Dash 1")
        await service.create_dashboard(display_name="Dash 2")
        result = await service.list_dashboards(include_cloud=False)
        assert result["total_count"] == 2

    @pytest.mark.asyncio()
    async def test_update_dashboard_updates_fields(
        self, service: DashboardService
    ) -> None:
        created = await service.create_dashboard(display_name="Original")
        updated = await service.update_dashboard(
            created["id"], {"display_name": "Updated"}
        )
        assert updated is not None
        assert updated["display_name"] == "Updated"
        assert updated["metadata"]["version"] == 2

    @pytest.mark.asyncio()
    async def test_update_dashboard_nonexistent_returns_none(
        self, service: DashboardService
    ) -> None:
        result = await service.update_dashboard("bad-id", {"display_name": "X"})
        assert result is None

    @pytest.mark.asyncio()
    async def test_update_dashboard_preserves_id(
        self, service: DashboardService
    ) -> None:
        created = await service.create_dashboard(display_name="Keep ID")
        original_id = created["id"]
        updated = await service.update_dashboard(
            original_id, {"id": "hacked", "display_name": "New"}
        )
        assert updated is not None
        assert updated["id"] == original_id

    @pytest.mark.asyncio()
    async def test_delete_dashboard_existing_returns_true(
        self, service: DashboardService
    ) -> None:
        created = await service.create_dashboard(display_name="Delete Me")
        result = await service.delete_dashboard(created["id"])
        assert result is True

    @pytest.mark.asyncio()
    async def test_delete_dashboard_removes_from_store(
        self, service: DashboardService
    ) -> None:
        created = await service.create_dashboard(display_name="Gone")
        await service.delete_dashboard(created["id"])
        result = await service.get_dashboard(created["id"])
        assert result is None

    @pytest.mark.asyncio()
    async def test_delete_dashboard_nonexistent_returns_false(
        self, service: DashboardService
    ) -> None:
        result = await service.delete_dashboard("nonexistent")
        assert result is False

    @pytest.mark.asyncio()
    async def test_add_panel_to_dashboard(self, service: DashboardService) -> None:
        created = await service.create_dashboard(display_name="Panel Test")
        result = await service.add_panel(
            created["id"], {"title": "New Panel", "type": "time_series"}
        )
        assert result is not None
        assert len(result["panels"]) == 1
        assert result["panels"][0]["title"] == "New Panel"

    @pytest.mark.asyncio()
    async def test_add_panel_assigns_id(self, service: DashboardService) -> None:
        created = await service.create_dashboard(display_name="Auto ID")
        result = await service.add_panel(created["id"], {"title": "No ID Panel"})
        assert result is not None
        assert "id" in result["panels"][0]
        assert result["panels"][0]["id"].startswith("panel-")

    @pytest.mark.asyncio()
    async def test_add_panel_auto_positions(self, service: DashboardService) -> None:
        created = await service.create_dashboard(display_name="Position Test")
        result = await service.add_panel(created["id"], {"title": "Auto Position"})
        assert result is not None
        pos = result["panels"][0]["grid_position"]
        assert pos["x"] == 0
        assert pos["y"] == 0
        assert pos["width"] == 12

    @pytest.mark.asyncio()
    async def test_add_panel_nonexistent_dashboard_returns_none(
        self, service: DashboardService
    ) -> None:
        result = await service.add_panel("bad-id", {"title": "Orphan"})
        assert result is None

    @pytest.mark.asyncio()
    async def test_remove_panel_from_dashboard(self, service: DashboardService) -> None:
        created = await service.create_dashboard(display_name="Remove Test")
        await service.add_panel(created["id"], {"id": "p1", "title": "Remove Me"})
        result = await service.remove_panel(created["id"], "p1")
        assert result is not None
        assert len(result["panels"]) == 0

    @pytest.mark.asyncio()
    async def test_remove_panel_nonexistent_dashboard_returns_none(
        self, service: DashboardService
    ) -> None:
        result = await service.remove_panel("bad-id", "p1")
        assert result is None

    @pytest.mark.asyncio()
    async def test_update_panel_position(self, service: DashboardService) -> None:
        created = await service.create_dashboard(display_name="Move Test")
        await service.add_panel(created["id"], {"id": "p1", "title": "Move Me"})
        new_pos = {"x": 6, "y": 4, "width": 12, "height": 6}
        result = await service.update_panel_position(created["id"], "p1", new_pos)
        assert result is not None
        panel = next(p for p in result["panels"] if p["id"] == "p1")
        assert panel["grid_position"] == new_pos

    def test_find_next_position_empty(self) -> None:
        service = DashboardService()
        pos = service._find_next_position([])
        assert pos == {"x": 0, "y": 0, "width": 12, "height": 4}

    def test_find_next_position_after_existing(self) -> None:
        service = DashboardService()
        panels = [{"grid_position": {"x": 0, "y": 0, "width": 12, "height": 4}}]
        pos = service._find_next_position(panels)
        assert pos["y"] == 4

    def test_get_dashboard_service_singleton(self) -> None:
        import sre_agent.services.dashboard_service as mod

        mod._service_instance = None
        s1 = get_dashboard_service()
        s2 = get_dashboard_service()
        assert s1 is s2
        mod._service_instance = None


class TestTemplateProvisioning:
    """Tests for OOTB template provisioning."""

    @pytest.fixture()
    def service(self) -> DashboardService:
        return DashboardService()

    @pytest.mark.asyncio()
    async def test_list_templates_returns_all(self, service: DashboardService) -> None:
        templates = await service.list_templates()
        assert len(templates) == 4
        ids = {t["id"] for t in templates}
        assert "ootb-gke" in ids
        assert "ootb-cloud-run" in ids
        assert "ootb-bigquery" in ids
        assert "ootb-vertex-agent-engine" in ids

    @pytest.mark.asyncio()
    async def test_get_template_existing(self, service: DashboardService) -> None:
        template = await service.get_template("ootb-gke")
        assert template is not None
        assert template["display_name"] == "GKE Overview"

    @pytest.mark.asyncio()
    async def test_get_template_nonexistent(self, service: DashboardService) -> None:
        template = await service.get_template("nonexistent")
        assert template is None

    @pytest.mark.asyncio()
    async def test_provision_template_creates_dashboard(
        self, service: DashboardService
    ) -> None:
        result = await service.provision_template("ootb-gke")
        assert result is not None
        assert result["display_name"] == "GKE Overview"
        assert "id" in result
        assert len(result["panels"]) > 0
        assert result["labels"]["template_id"] == "ootb-gke"
        assert result["source"] == "template"

    @pytest.mark.asyncio()
    async def test_provision_template_assigns_unique_panel_ids(
        self, service: DashboardService
    ) -> None:
        result = await service.provision_template("ootb-cloud-run")
        assert result is not None
        panel_ids = [p["id"] for p in result["panels"]]
        # All IDs should be unique
        assert len(panel_ids) == len(set(panel_ids))
        # All IDs should start with "panel-"
        for pid in panel_ids:
            assert pid.startswith("panel-")

    @pytest.mark.asyncio()
    async def test_provision_template_nonexistent_returns_none(
        self, service: DashboardService
    ) -> None:
        result = await service.provision_template("nonexistent")
        assert result is None

    @pytest.mark.asyncio()
    async def test_provision_template_with_project_id(
        self, service: DashboardService
    ) -> None:
        result = await service.provision_template(
            "ootb-bigquery", project_id="my-project"
        )
        assert result is not None
        assert result["project_id"] == "my-project"

    @pytest.mark.asyncio()
    async def test_provisioned_dashboard_listed(
        self, service: DashboardService
    ) -> None:
        await service.provision_template("ootb-gke")
        listing = await service.list_dashboards(include_cloud=False)
        assert listing["total_count"] == 1
        assert listing["dashboards"][0]["display_name"] == "GKE Overview"

    @pytest.mark.asyncio()
    async def test_provision_multiple_templates(
        self, service: DashboardService
    ) -> None:
        await service.provision_template("ootb-gke")
        await service.provision_template("ootb-cloud-run")
        listing = await service.list_dashboards(include_cloud=False)
        assert listing["total_count"] == 2


class TestCustomPanels:
    """Tests for custom panel creation."""

    @pytest.fixture()
    def service(self) -> DashboardService:
        return DashboardService()

    @pytest.mark.asyncio()
    async def test_add_custom_metric_panel(self, service: DashboardService) -> None:
        dash = await service.create_dashboard(display_name="Custom Test")
        result = await service.add_custom_metric_panel(
            dash["id"],
            title="CPU Usage",
            metric_type="compute.googleapis.com/instance/cpu/utilization",
            resource_type="gce_instance",
        )
        assert result is not None
        assert len(result["panels"]) == 1
        panel = result["panels"][0]
        assert panel["title"] == "CPU Usage"
        assert panel["type"] == "time_series"
        assert len(panel["queries"]) == 1
        query = panel["queries"][0]
        assert "cloud_monitoring" in query
        assert "filter_str" in query["cloud_monitoring"]
        assert "cpu/utilization" in query["cloud_monitoring"]["filter_str"]

    @pytest.mark.asyncio()
    async def test_add_custom_metric_panel_with_group_by(
        self, service: DashboardService
    ) -> None:
        dash = await service.create_dashboard(display_name="GroupBy Test")
        result = await service.add_custom_metric_panel(
            dash["id"],
            title="Network Rx",
            metric_type="kubernetes.io/pod/network/received_bytes_count",
            group_by=["resource.label.pod_name"],
        )
        assert result is not None
        query = result["panels"][0]["queries"][0]
        assert query["cloud_monitoring"]["group_by_fields"] == [
            "resource.label.pod_name"
        ]

    @pytest.mark.asyncio()
    async def test_add_custom_metric_panel_nonexistent_dashboard(
        self, service: DashboardService
    ) -> None:
        result = await service.add_custom_metric_panel(
            "bad-id",
            title="Orphan",
            metric_type="some/metric",
        )
        assert result is None

    @pytest.mark.asyncio()
    async def test_add_custom_log_panel(self, service: DashboardService) -> None:
        dash = await service.create_dashboard(display_name="Log Test")
        result = await service.add_custom_log_panel(
            dash["id"],
            title="K8s Logs",
            log_filter='resource.type="k8s_container"',
            severity_levels=["ERROR", "CRITICAL"],
        )
        assert result is not None
        panel = result["panels"][0]
        assert panel["title"] == "K8s Logs"
        assert panel["type"] == "logs"
        query = panel["queries"][0]
        assert query["logs"]["filter_str"] == 'resource.type="k8s_container"'
        assert query["logs"]["severity_levels"] == ["ERROR", "CRITICAL"]

    @pytest.mark.asyncio()
    async def test_add_custom_log_panel_nonexistent_dashboard(
        self, service: DashboardService
    ) -> None:
        result = await service.add_custom_log_panel(
            "bad-id",
            title="Orphan",
            log_filter="severity>=ERROR",
        )
        assert result is None

    @pytest.mark.asyncio()
    async def test_add_custom_trace_panel(self, service: DashboardService) -> None:
        dash = await service.create_dashboard(display_name="Trace Test")
        result = await service.add_custom_trace_panel(
            dash["id"],
            title="Cloud Run Traces",
            trace_filter='+resource.type:"cloud_run_revision"',
        )
        assert result is not None
        panel = result["panels"][0]
        assert panel["title"] == "Cloud Run Traces"
        assert panel["type"] == "traces"

    @pytest.mark.asyncio()
    async def test_add_custom_trace_panel_nonexistent_dashboard(
        self, service: DashboardService
    ) -> None:
        result = await service.add_custom_trace_panel(
            "bad-id",
            title="Orphan",
            trace_filter="some filter",
        )
        assert result is None

    @pytest.mark.asyncio()
    async def test_add_multiple_panel_types(self, service: DashboardService) -> None:
        dash = await service.create_dashboard(display_name="Multi Panel")
        await service.add_custom_metric_panel(
            dash["id"],
            title="Metric",
            metric_type="some/metric",
        )
        await service.add_custom_log_panel(
            dash["id"],
            title="Logs",
            log_filter="severity>=ERROR",
        )
        result = await service.add_custom_trace_panel(
            dash["id"],
            title="Traces",
            trace_filter="some filter",
        )
        assert result is not None
        assert len(result["panels"]) == 3
        types = {p["type"] for p in result["panels"]}
        assert types == {"time_series", "logs", "traces"}

    @pytest.mark.asyncio()
    async def test_custom_metric_panel_with_thresholds(
        self, service: DashboardService
    ) -> None:
        dash = await service.create_dashboard(display_name="Threshold Test")
        thresholds = [
            {"value": 0.8, "color": "yellow", "label": "Warning"},
            {"value": 0.95, "color": "red", "label": "Critical"},
        ]
        result = await service.add_custom_metric_panel(
            dash["id"],
            title="CPU",
            metric_type="some/cpu",
            thresholds=thresholds,
        )
        assert result is not None
        assert result["panels"][0]["thresholds"] == thresholds

    @pytest.mark.asyncio()
    async def test_custom_metric_panel_gauge_type(
        self, service: DashboardService
    ) -> None:
        dash = await service.create_dashboard(display_name="Gauge Test")
        result = await service.add_custom_metric_panel(
            dash["id"],
            title="Memory",
            metric_type="some/memory",
            panel_type="gauge",
        )
        assert result is not None
        assert result["panels"][0]["type"] == "gauge"
