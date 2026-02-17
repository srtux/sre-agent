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
