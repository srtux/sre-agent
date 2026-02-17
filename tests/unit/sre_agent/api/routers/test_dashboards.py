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
    # Template methods
    service.list_templates.return_value = [
        {
            "id": "ootb-gke",
            "display_name": "GKE Overview",
            "description": "GKE dashboard",
            "service": "gke",
            "panel_count": 12,
            "labels": {"service": "gke"},
        },
    ]
    service.get_template.return_value = {
        "id": "ootb-gke",
        "display_name": "GKE Overview",
        "description": "GKE dashboard",
        "service": "gke",
        "panels": [{"title": "CPU", "type": "time_series"}],
    }
    service.provision_template.return_value = {
        "id": "new-dash-id",
        "display_name": "GKE Overview",
        "panels": [{"id": "p1", "title": "CPU"}],
        "labels": {"template_id": "ootb-gke"},
    }
    # Custom panel methods
    _dash_with_panel = {
        "id": "d1",
        "display_name": "Test",
        "panels": [{"id": "p1", "title": "Custom Panel"}],
    }
    service.add_custom_metric_panel.return_value = _dash_with_panel
    service.add_custom_log_panel.return_value = _dash_with_panel
    service.add_custom_trace_panel.return_value = _dash_with_panel
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


class TestTemplateRouter:
    """Tests for OOTB template endpoints."""

    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_list_templates_returns_200(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_get_service.return_value = mock_service
        response = client.get("/api/dashboards/templates/list")
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert "total_count" in data
        assert data["total_count"] == 1

    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_get_template_returns_200(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_get_service.return_value = mock_service
        response = client.get("/api/dashboards/templates/ootb-gke")
        assert response.status_code == 200
        data = response.json()
        assert data["display_name"] == "GKE Overview"

    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_get_template_not_found_returns_404(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_service.get_template.return_value = None
        mock_get_service.return_value = mock_service
        response = client.get("/api/dashboards/templates/nonexistent")
        assert response.status_code == 404

    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_provision_template_returns_201(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_get_service.return_value = mock_service
        response = client.post(
            "/api/dashboards/templates/ootb-gke/provision",
            json={"project_id": "my-project"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["display_name"] == "GKE Overview"

    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_provision_template_no_body_returns_201(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_get_service.return_value = mock_service
        response = client.post("/api/dashboards/templates/ootb-gke/provision")
        assert response.status_code == 201

    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_provision_template_not_found_returns_404(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_service.provision_template.return_value = None
        mock_get_service.return_value = mock_service
        response = client.post(
            "/api/dashboards/templates/nonexistent/provision",
        )
        assert response.status_code == 404


class TestCustomPanelRouter:
    """Tests for custom panel endpoints."""

    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_add_metric_panel_returns_200(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_get_service.return_value = mock_service
        response = client.post(
            "/api/dashboards/d1/panels/metric",
            json={
                "title": "CPU Usage",
                "metric_type": "compute.googleapis.com/instance/cpu/utilization",
                "resource_type": "gce_instance",
            },
        )
        assert response.status_code == 200

    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_add_metric_panel_not_found_returns_404(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_service.add_custom_metric_panel.return_value = None
        mock_get_service.return_value = mock_service
        response = client.post(
            "/api/dashboards/bad-id/panels/metric",
            json={
                "title": "CPU",
                "metric_type": "some/metric",
            },
        )
        assert response.status_code == 404

    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_add_log_panel_returns_200(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_get_service.return_value = mock_service
        response = client.post(
            "/api/dashboards/d1/panels/log",
            json={
                "title": "Error Logs",
                "log_filter": "severity>=ERROR",
            },
        )
        assert response.status_code == 200

    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_add_log_panel_not_found_returns_404(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_service.add_custom_log_panel.return_value = None
        mock_get_service.return_value = mock_service
        response = client.post(
            "/api/dashboards/bad-id/panels/log",
            json={
                "title": "Logs",
                "log_filter": "severity>=ERROR",
            },
        )
        assert response.status_code == 404

    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_add_trace_panel_returns_200(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_get_service.return_value = mock_service
        response = client.post(
            "/api/dashboards/d1/panels/trace",
            json={
                "title": "Request Traces",
                "trace_filter": '+resource.type:"cloud_run_revision"',
            },
        )
        assert response.status_code == 200

    @patch("sre_agent.api.routers.dashboards.get_dashboard_service")
    def test_add_trace_panel_not_found_returns_404(
        self, mock_get_service: Any, client: TestClient, mock_service: AsyncMock
    ) -> None:
        mock_service.add_custom_trace_panel.return_value = None
        mock_get_service.return_value = mock_service
        response = client.post(
            "/api/dashboards/bad-id/panels/trace",
            json={
                "title": "Traces",
                "trace_filter": "some filter",
            },
        )
        assert response.status_code == 404
