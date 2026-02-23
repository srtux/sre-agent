"""Tests for dashboards and preferences guest mode."""

from typing import Any
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sre_agent.api.routers.dashboards import router as dashboards_router
from sre_agent.api.routers.preferences import router as preferences_router


@pytest.fixture()
def app() -> FastAPI:
    """Create a test FastAPI app with dashboard and preferences routers."""
    app = FastAPI()
    app.include_router(dashboards_router)
    app.include_router(preferences_router)
    return app


@pytest.fixture()
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture()
def guest_headers() -> dict[str, str]:
    """Headers that simulate guest mode."""
    return {"X-Guest-Mode": "true", "Authorization": "Bearer dev-mode-bypass-token"}


class TestDashboardsGuestMode:
    """Tests for dashboard endpoints in guest mode."""

    def test_list_dashboards_returns_demo_data(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.dashboards.is_guest_mode", return_value=True
        ):
            resp = client.get(
                "/api/dashboards",
                headers=guest_headers,
                params={"project_id": "cymbal-shops-demo"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "dashboards" in data
        assert len(data["dashboards"]) > 0
        assert data["dashboards"][0]["id"] == "demo-dashboard-001"
        assert data["dashboards"][0]["project_id"] == "cymbal-shops-demo"

    def test_get_dashboard_returns_demo_data(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.dashboards.is_guest_mode", return_value=True
        ):
            resp = client.get(
                "/api/dashboards/demo-dashboard-001", headers=guest_headers
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "demo-dashboard-001"
        assert len(data["panels"]) == 4

    def test_get_dashboard_any_id_returns_demo(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        """Any dashboard ID returns the demo dashboard in guest mode."""
        with patch(
            "sre_agent.api.routers.dashboards.is_guest_mode", return_value=True
        ):
            resp = client.get(
                "/api/dashboards/nonexistent-id", headers=guest_headers
            )
        assert resp.status_code == 200
        assert resp.json()["id"] == "demo-dashboard-001"

    def test_create_dashboard_returns_demo_response(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.dashboards.is_guest_mode", return_value=True
        ):
            resp = client.post(
                "/api/dashboards",
                headers=guest_headers,
                json={"display_name": "My Dashboard"},
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == "demo-dashboard-new"
        assert data["name"] == "My Dashboard"
        assert "demo mode" in data["status"]

    def test_update_dashboard_returns_demo_response(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.dashboards.is_guest_mode", return_value=True
        ):
            resp = client.patch(
                "/api/dashboards/d1",
                headers=guest_headers,
                json={"display_name": "Updated"},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "d1"
        assert "demo mode" in data["status"]

    def test_delete_dashboard_returns_204(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.dashboards.is_guest_mode", return_value=True
        ):
            resp = client.delete("/api/dashboards/d1", headers=guest_headers)
        assert resp.status_code == 204

    def test_add_panel_returns_demo_response(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.dashboards.is_guest_mode", return_value=True
        ):
            resp = client.post(
                "/api/dashboards/d1/panels",
                headers=guest_headers,
                json={"title": "New Panel"},
            )
        assert resp.status_code == 200
        assert "demo mode" in resp.json()["status"]

    def test_remove_panel_returns_demo_response(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.dashboards.is_guest_mode", return_value=True
        ):
            resp = client.delete(
                "/api/dashboards/d1/panels/p1", headers=guest_headers
            )
        assert resp.status_code == 200
        assert "demo mode" in resp.json()["status"]

    def test_update_panel_position_returns_demo_response(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.dashboards.is_guest_mode", return_value=True
        ):
            resp = client.patch(
                "/api/dashboards/d1/panels/p1/position",
                headers=guest_headers,
                json={"x": 0, "y": 0, "width": 6, "height": 4},
            )
        assert resp.status_code == 200
        assert "demo mode" in resp.json()["status"]


class TestTemplatesGuestMode:
    """Tests for template endpoints in guest mode."""

    def test_list_templates_returns_demo_data(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.dashboards.is_guest_mode", return_value=True
        ):
            resp = client.get(
                "/api/dashboards/templates/list", headers=guest_headers
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "templates" in data
        assert len(data["templates"]) == 2
        assert data["templates"][0]["id"] == "ai-agent-monitoring"
        assert data["templates"][1]["id"] == "mcp-server-health"

    def test_get_template_returns_demo_data(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.dashboards.is_guest_mode", return_value=True
        ):
            resp = client.get(
                "/api/dashboards/templates/ai-agent-monitoring",
                headers=guest_headers,
            )
        assert resp.status_code == 200
        assert resp.json()["id"] == "ai-agent-monitoring"

    def test_provision_template_returns_demo_response(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.dashboards.is_guest_mode", return_value=True
        ):
            resp = client.post(
                "/api/dashboards/templates/ai-agent-monitoring/provision",
                headers=guest_headers,
                json={"project_id": "cymbal-shops-demo"},
            )
        assert resp.status_code == 201
        data = resp.json()
        assert "demo mode" in data["status"]

    def test_add_metric_panel_returns_demo_response(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.dashboards.is_guest_mode", return_value=True
        ):
            resp = client.post(
                "/api/dashboards/d1/panels/metric",
                headers=guest_headers,
                json={
                    "title": "CPU",
                    "metric_type": "compute.googleapis.com/instance/cpu/utilization",
                },
            )
        assert resp.status_code == 200
        assert "demo mode" in resp.json()["status"]

    def test_add_log_panel_returns_demo_response(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.dashboards.is_guest_mode", return_value=True
        ):
            resp = client.post(
                "/api/dashboards/d1/panels/log",
                headers=guest_headers,
                json={"title": "Errors", "log_filter": "severity>=ERROR"},
            )
        assert resp.status_code == 200
        assert "demo mode" in resp.json()["status"]

    def test_add_trace_panel_returns_demo_response(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.dashboards.is_guest_mode", return_value=True
        ):
            resp = client.post(
                "/api/dashboards/d1/panels/trace",
                headers=guest_headers,
                json={"title": "Traces", "trace_filter": "some filter"},
            )
        assert resp.status_code == 200
        assert "demo mode" in resp.json()["status"]


class TestPreferencesGuestMode:
    """Tests for preferences endpoints in guest mode."""

    def test_get_project_returns_demo(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.preferences.is_guest_mode", return_value=True
        ):
            resp = client.get(
                "/api/preferences/project",
                headers=guest_headers,
                params={"user_id": "guest"},
            )
        assert resp.status_code == 200
        assert resp.json()["project_id"] == "cymbal-shops-demo"

    def test_set_project_noop(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.preferences.is_guest_mode", return_value=True
        ):
            resp = client.post(
                "/api/preferences/project",
                headers=guest_headers,
                json={"project_id": "my-project"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_get_tool_preferences_returns_empty(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.preferences.is_guest_mode", return_value=True
        ):
            resp = client.get("/api/preferences/tools", headers=guest_headers)
        assert resp.status_code == 200
        assert resp.json()["enabled_tools"] == {}

    def test_set_tool_preferences_noop(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.preferences.is_guest_mode", return_value=True
        ):
            resp = client.post(
                "/api/preferences/tools",
                headers=guest_headers,
                json={"enabled_tools": {"tool1": True}},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_get_recent_projects_returns_demo(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.preferences.is_guest_mode", return_value=True
        ):
            resp = client.get(
                "/api/preferences/projects/recent", headers=guest_headers
            )
        assert resp.status_code == 200
        assert resp.json()["projects"] == ["cymbal-shops-demo"]

    def test_set_recent_projects_noop(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.preferences.is_guest_mode", return_value=True
        ):
            resp = client.post(
                "/api/preferences/projects/recent",
                headers=guest_headers,
                json={"projects": [{"project_id": "p1", "display_name": "P1"}]},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_get_starred_projects_returns_demo(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.preferences.is_guest_mode", return_value=True
        ):
            resp = client.get(
                "/api/preferences/projects/starred", headers=guest_headers
            )
        assert resp.status_code == 200
        assert resp.json()["projects"] == ["cymbal-shops-demo"]

    def test_set_starred_projects_noop(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.preferences.is_guest_mode", return_value=True
        ):
            resp = client.post(
                "/api/preferences/projects/starred",
                headers=guest_headers,
                json={"projects": [{"project_id": "p1", "display_name": "P1"}]},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_toggle_starred_noop(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.preferences.is_guest_mode", return_value=True
        ):
            resp = client.post(
                "/api/preferences/projects/starred/toggle",
                headers=guest_headers,
                json={"project_id": "cymbal-shops-demo", "starred": True},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_get_recent_queries_returns_empty(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.preferences.is_guest_mode", return_value=True
        ):
            resp = client.get(
                "/api/preferences/queries/recent", headers=guest_headers
            )
        assert resp.status_code == 200
        assert resp.json()["queries"] == []

    def test_add_recent_query_noop(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.preferences.is_guest_mode", return_value=True
        ):
            resp = client.post(
                "/api/preferences/queries/recent",
                headers=guest_headers,
                json={
                    "query": "SELECT 1",
                    "panel_type": "analytics",
                    "language": "SQL",
                },
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_get_saved_queries_returns_empty(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.preferences.is_guest_mode", return_value=True
        ):
            resp = client.get(
                "/api/preferences/queries/saved", headers=guest_headers
            )
        assert resp.status_code == 200
        assert resp.json()["queries"] == []

    def test_save_query_noop(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.preferences.is_guest_mode", return_value=True
        ):
            resp = client.post(
                "/api/preferences/queries/saved",
                headers=guest_headers,
                json={
                    "name": "My Query",
                    "query": "SELECT 1",
                    "panel_type": "analytics",
                },
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_update_saved_query_noop(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.preferences.is_guest_mode", return_value=True
        ):
            resp = client.put(
                "/api/preferences/queries/saved/q1",
                headers=guest_headers,
                json={"name": "Updated Query"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_delete_saved_query_noop(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        with patch(
            "sre_agent.api.routers.preferences.is_guest_mode", return_value=True
        ):
            resp = client.delete(
                "/api/preferences/queries/saved/q1", headers=guest_headers
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
