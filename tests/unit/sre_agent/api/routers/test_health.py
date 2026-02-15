"""Tests for the health and debug API endpoints."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sre_agent.api.routers.health import debug_info, health_check, router


@pytest.fixture
def client() -> TestClient:
    """Create a TestClient with the health router mounted."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestHealthCheckEndpoint:
    """Tests for GET /health."""

    def test_returns_200(self, client: TestClient) -> None:
        """Health endpoint should return HTTP 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_response_contains_status_ok(self, client: TestClient) -> None:
        """Response body must include status='ok'."""
        data = client.get("/health").json()
        assert data["status"] == "ok"

    def test_response_contains_version(self, client: TestClient) -> None:
        """Response body must include a 'version' key."""
        data = client.get("/health").json()
        assert "version" in data
        assert isinstance(data["version"], str)

    @pytest.mark.asyncio
    async def test_health_check_direct_call(self) -> None:
        """Calling the handler directly should return the expected dict."""
        result = await health_check()
        assert result["status"] == "ok"
        assert "version" in result


class TestDebugInfoEndpoint:
    """Tests for GET /api/debug."""

    @patch("sre_agent.api.routers.health.get_debug_summary")
    @patch("sre_agent.api.routers.health.log_auth_state")
    @patch("sre_agent.api.routers.health.log_telemetry_state")
    def test_returns_200(
        self,
        mock_telemetry: MagicMock,
        mock_auth: MagicMock,
        mock_summary: MagicMock,
        client: TestClient,
    ) -> None:
        """Debug endpoint should return HTTP 200."""
        mock_telemetry.return_value = {"telemetry": "state"}
        mock_auth.return_value = {"auth": "state"}
        mock_summary.return_value = {"summary": "data"}
        response = client.get("/api/debug")
        assert response.status_code == 200

    @patch("sre_agent.api.routers.health.get_debug_summary")
    @patch("sre_agent.api.routers.health.log_auth_state")
    @patch("sre_agent.api.routers.health.log_telemetry_state")
    def test_response_structure(
        self,
        mock_telemetry: MagicMock,
        mock_auth: MagicMock,
        mock_summary: MagicMock,
        client: TestClient,
    ) -> None:
        """Response must contain telemetry, auth, summary, and instructions."""
        mock_telemetry.return_value = {"env": "info"}
        mock_auth.return_value = {"creds": "info"}
        mock_summary.return_value = {"overview": "ok"}
        data = client.get("/api/debug").json()
        assert "telemetry" in data
        assert "auth" in data
        assert "summary" in data
        assert "instructions" in data

    @patch("sre_agent.api.routers.health.get_debug_summary")
    @patch("sre_agent.api.routers.health.log_auth_state")
    @patch("sre_agent.api.routers.health.log_telemetry_state")
    def test_instructions_keys(
        self,
        mock_telemetry: MagicMock,
        mock_auth: MagicMock,
        mock_summary: MagicMock,
        client: TestClient,
    ) -> None:
        """Instructions should contain guidance for debug logging and tracing."""
        mock_telemetry.return_value = {}
        mock_auth.return_value = {}
        mock_summary.return_value = {}
        data = client.get("/api/debug").json()
        instructions = data["instructions"]
        assert "enable_debug_logging" in instructions
        assert "enable_agent_engine_telemetry" in instructions
        assert "view_traces" in instructions

    @patch("sre_agent.api.routers.health.get_debug_summary")
    @patch("sre_agent.api.routers.health.log_auth_state")
    @patch("sre_agent.api.routers.health.log_telemetry_state")
    def test_telemetry_state_called_with_debug_endpoint(
        self,
        mock_telemetry: MagicMock,
        mock_auth: MagicMock,
        mock_summary: MagicMock,
        client: TestClient,
    ) -> None:
        """log_telemetry_state should be called with 'debug_endpoint' label."""
        mock_telemetry.return_value = {}
        mock_auth.return_value = {}
        mock_summary.return_value = {}
        client.get("/api/debug")
        mock_telemetry.assert_called_once_with("debug_endpoint")

    @patch("sre_agent.api.routers.health.get_debug_summary")
    @patch("sre_agent.api.routers.health.log_auth_state")
    @patch("sre_agent.api.routers.health.log_telemetry_state")
    def test_auth_state_called_with_none_and_label(
        self,
        mock_telemetry: MagicMock,
        mock_auth: MagicMock,
        mock_summary: MagicMock,
        client: TestClient,
    ) -> None:
        """log_auth_state should be called with (None, 'debug_endpoint')."""
        mock_telemetry.return_value = {}
        mock_auth.return_value = {}
        mock_summary.return_value = {}
        client.get("/api/debug")
        mock_auth.assert_called_once_with(None, "debug_endpoint")

    @pytest.mark.asyncio
    @patch("sre_agent.api.routers.health.get_debug_summary")
    @patch("sre_agent.api.routers.health.log_auth_state")
    @patch("sre_agent.api.routers.health.log_telemetry_state")
    async def test_debug_info_direct_call(
        self,
        mock_telemetry: MagicMock,
        mock_auth: MagicMock,
        mock_summary: MagicMock,
    ) -> None:
        """Calling the handler directly should return the expected structure."""
        mock_telemetry.return_value = {"t": 1}
        mock_auth.return_value = {"a": 2}
        mock_summary.return_value = {"s": 3}
        result = await debug_info()
        assert result["telemetry"] == {"t": 1}
        assert result["auth"] == {"a": 2}
        assert result["summary"] == {"s": 3}
        assert "instructions" in result


class TestRouterConfiguration:
    """Tests for the router object itself."""

    def test_router_tags(self) -> None:
        """Router should be tagged with 'health'."""
        assert "health" in router.tags

    def test_health_route_exists(self) -> None:
        """The /health route should be registered."""
        paths = [route.path for route in router.routes]
        assert "/health" in paths

    def test_debug_route_exists(self) -> None:
        """The /api/debug route should be registered."""
        paths = [route.path for route in router.routes]
        assert "/api/debug" in paths
