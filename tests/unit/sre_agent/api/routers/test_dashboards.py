"""Tests for dashboard API router."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sre_agent.api.routers.dashboards import router


@pytest.fixture()
def app() -> FastAPI:
    """Create a test FastAPI app with the dashboard router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture()
def mock_service() -> AsyncMock:
    """Create a mock dashboard service."""
    service = AsyncMock()
    service.list_dashboards.return_value = {
        "dashboards": [
            {
                "id": "d1",
                "display_name": "Test",
                "source": "local",
                "panel_count": 0,
            }
        ],
        "total_count": 1,
        "next_page_token": None,
    }
    service.get_dashboard.return_value = {
        "id": "d1",
        "display_name": "Test",
        "panels": [],
    }
    service.create_dashboard.return_value = {
        "id": "new-id",
        "display_name": "New Dashboard",
        "panels": [],
        "metadata": {"version": 1},
    }
    service.update_dashboard.return_value = {
        "id": "d1",
        "display_name": "Updated",
        "panels": [],
    }
    service.delete_dashboard.return_value = True
    service.add_panel.return_value = {
        "id": "d1",
        "display_name": "Test",
        "panels": [{"id": "p1", "title": "New Panel"}],
    }
    service.remove_panel.return_value = {
        "id": "d1",
        "display_name": "Test",
        "panels": [],
    }
    service.update_panel_position.return_value = {
        "id": "d1",
        "display_name": "Test",
        "panels": [
            {"id": "p1", "grid_position": {"x": 0, "y": 0, "width": 6, "height": 4}}
        ],
    }
    return service


class TestDashboardRouter:
    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_list_dashboards_returns_200(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_get_service.return_value = mock_service
        response = client.get("/api/dashboards")
        assert response.status_code == 200
        data = response.json()
        assert "dashboards" in data

    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_get_dashboard_returns_200(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_get_service.return_value = mock_service
        response = client.get("/api/dashboards/d1")
        assert response.status_code == 200

    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_get_dashboard_not_found_returns_404(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_service.get_dashboard.return_value = None
        mock_get_service.return_value = mock_service
        response = client.get("/api/dashboards/nonexistent")
        assert response.status_code == 404

    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_create_dashboard_returns_201(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_get_service.return_value = mock_service
        response = client.post(
            "/api/dashboards",
            json={"display_name": "New Dashboard"},
        )
        assert response.status_code == 201

    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_create_dashboard_with_panels(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_get_service.return_value = mock_service
        response = client.post(
            "/api/dashboards",
            json={
                "display_name": "With Panels",
                "panels": [{"title": "P1", "type": "time_series"}],
            },
        )
        assert response.status_code == 201

    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_update_dashboard_returns_200(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_get_service.return_value = mock_service
        response = client.patch(
            "/api/dashboards/d1",
            json={"display_name": "Updated"},
        )
        assert response.status_code == 200

    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_update_dashboard_not_found_returns_404(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_service.update_dashboard.return_value = None
        mock_get_service.return_value = mock_service
        response = client.patch(
            "/api/dashboards/bad-id",
            json={"display_name": "X"},
        )
        assert response.status_code == 404

    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_delete_dashboard_returns_204(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_get_service.return_value = mock_service
        response = client.delete("/api/dashboards/d1")
        assert response.status_code == 204

    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_delete_dashboard_not_found_returns_404(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_service.delete_dashboard.return_value = False
        mock_get_service.return_value = mock_service
        response = client.delete("/api/dashboards/bad-id")
        assert response.status_code == 404

    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_add_panel_returns_200(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_get_service.return_value = mock_service
        response = client.post(
            "/api/dashboards/d1/panels",
            json={"title": "New Panel"},
        )
        assert response.status_code == 200

    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_remove_panel_returns_200(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_get_service.return_value = mock_service
        response = client.delete("/api/dashboards/d1/panels/p1")
        assert response.status_code == 200

    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_update_panel_position_returns_200(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_get_service.return_value = mock_service
        response = client.patch(
            "/api/dashboards/d1/panels/p1/position",
            json={"x": 0, "y": 0, "width": 6, "height": 4},
        )
        assert response.status_code == 200
