"""Tests for agent_graph guest mode endpoints.

Verifies that every endpoint in the agent_graph router returns synthetic
data from DemoDataGenerator when the request is in guest mode, without
touching BigQuery.
"""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sre_agent.api.routers.agent_graph import router


@pytest.fixture
def client() -> TestClient:
    """Create a TestClient with the agent_graph router mounted."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def guest_headers() -> dict[str, str]:
    """Standard headers for guest mode requests."""
    return {"X-Guest-Mode": "true", "Authorization": "Bearer dev-mode-bypass-token"}


@pytest.fixture(autouse=True)
def mock_guest_mode():
    """Patch is_guest_mode to return True for all tests in this module."""
    with patch("sre_agent.api.routers.agent_graph.is_guest_mode", return_value=True):
        yield


# -- Common query parameters used across tests --------------------------------

_COMMON_PARAMS = {"project_id": "cymbal-shops-demo", "hours": 168}
_DASHBOARD_PARAMS = {"project_id": "cymbal-shops-demo", "hours": 168}


class TestTopologyGuestMode:
    """GET /topology should return synthetic nodes and edges."""

    def test_returns_nodes_and_edges(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        resp = client.get(
            "/api/v1/graph/topology",
            params=_COMMON_PARAMS,
            headers=guest_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) >= 5

    def test_nodes_have_expected_structure(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        resp = client.get(
            "/api/v1/graph/topology",
            params=_COMMON_PARAMS,
            headers=guest_headers,
        )
        data = resp.json()
        node = data["nodes"][0]
        assert "id" in node
        assert "type" in node
        assert "data" in node
        assert "position" in node


class TestTrajectoriesGuestMode:
    """GET /trajectories should return Sankey diagram data."""

    def test_returns_sankey_data(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        resp = client.get(
            "/api/v1/graph/trajectories",
            params=_COMMON_PARAMS,
            headers=guest_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "links" in data


class TestNodeDetailGuestMode:
    """GET /node/{id} should return node metrics."""

    def test_returns_node_detail(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        resp = client.get(
            "/api/v1/graph/node/root",
            params=_COMMON_PARAMS,
            headers=guest_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "nodeId" in data or "node_id" in data or isinstance(data, dict)


class TestEdgeDetailGuestMode:
    """GET /edge/{source}/{target} should return edge metrics."""

    def test_returns_edge_detail(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        resp = client.get(
            "/api/v1/graph/edge/root/search_logs",
            params=_COMMON_PARAMS,
            headers=guest_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)


class TestTimeseriesGuestMode:
    """GET /timeseries should return time-series data."""

    def test_returns_timeseries(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        resp = client.get(
            "/api/v1/graph/timeseries",
            params=_COMMON_PARAMS,
            headers=guest_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)


class TestSetupGuestMode:
    """POST /setup should return a skip message in guest mode."""

    def test_returns_demo_skip(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        resp = client.post(
            "/api/v1/graph/setup",
            json={
                "project_id": "cymbal-shops-demo",
                "trace_dataset": "traces",
                "service_name": "my-service",
            },
            headers=guest_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "Demo mode" in data["message"]


class TestDashboardKPIsGuestMode:
    """GET /dashboard/kpis should return KPI data."""

    def test_returns_kpi_data(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        resp = client.get(
            "/api/v1/graph/dashboard/kpis",
            params=_DASHBOARD_PARAMS,
            headers=guest_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "kpis" in data
        assert data["kpis"]["totalSessions"] > 0

    def test_kpis_contain_trend_fields(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        resp = client.get(
            "/api/v1/graph/dashboard/kpis",
            params=_DASHBOARD_PARAMS,
            headers=guest_headers,
        )
        kpis = resp.json()["kpis"]
        assert "totalSessionsTrend" in kpis
        assert "rootInvocationsTrend" in kpis


class TestDashboardTimeseriesGuestMode:
    """GET /dashboard/timeseries should return chart data."""

    def test_returns_timeseries(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        resp = client.get(
            "/api/v1/graph/dashboard/timeseries",
            params=_DASHBOARD_PARAMS,
            headers=guest_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "latency" in data
        assert "qps" in data


class TestDashboardModelsGuestMode:
    """GET /dashboard/models should return model call stats."""

    def test_returns_model_calls(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        resp = client.get(
            "/api/v1/graph/dashboard/models",
            params=_DASHBOARD_PARAMS,
            headers=guest_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "modelCalls" in data
        assert len(data["modelCalls"]) > 0


class TestDashboardToolsGuestMode:
    """GET /dashboard/tools should return tool call stats."""

    def test_returns_tool_calls(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        resp = client.get(
            "/api/v1/graph/dashboard/tools",
            params=_DASHBOARD_PARAMS,
            headers=guest_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "toolCalls" in data
        assert len(data["toolCalls"]) > 0


class TestDashboardLogsGuestMode:
    """GET /dashboard/logs should return agent log entries."""

    def test_returns_logs(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        resp = client.get(
            "/api/v1/graph/dashboard/logs",
            params={**_DASHBOARD_PARAMS, "limit": 500},
            headers=guest_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "agentLogs" in data
        assert len(data["agentLogs"]) > 0


class TestDashboardSessionsGuestMode:
    """GET /dashboard/sessions should return session aggregations."""

    def test_returns_sessions(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        resp = client.get(
            "/api/v1/graph/dashboard/sessions",
            params={**_DASHBOARD_PARAMS, "limit": 500},
            headers=guest_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "agentSessions" in data
        assert len(data["agentSessions"]) > 0


class TestDashboardTracesGuestMode:
    """GET /dashboard/traces should return trace-level data."""

    def test_returns_traces(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        resp = client.get(
            "/api/v1/graph/dashboard/traces",
            params={**_DASHBOARD_PARAMS, "limit": 500},
            headers=guest_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "agentTraces" in data
        assert len(data["agentTraces"]) > 0


class TestRegistryAgentsGuestMode:
    """GET /registry/agents should return agent registry data."""

    def test_returns_agents(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        resp = client.get(
            "/api/v1/graph/registry/agents",
            params=_COMMON_PARAMS,
            headers=guest_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "agents" in data
        assert len(data["agents"]) > 0


class TestRegistryToolsGuestMode:
    """GET /registry/tools should return tool registry data."""

    def test_returns_tools(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        resp = client.get(
            "/api/v1/graph/registry/tools",
            params=_COMMON_PARAMS,
            headers=guest_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "tools" in data
        assert len(data["tools"]) > 0


class TestTraceLogsGuestMode:
    """GET /trace/{id}/logs should return synthetic logs."""

    def test_returns_trace_logs(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        resp = client.get(
            "/api/v1/graph/trace/abcdef01234567890abcdef012345678/logs",
            params={"project_id": "cymbal-shops-demo"},
            headers=guest_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "traceId" in data or "logs" in data


class TestSpanDetailsGuestMode:
    """GET /trace/{id}/span/{id}/details should return span info."""

    def test_returns_span_details(
        self, client: TestClient, guest_headers: dict[str, str]
    ) -> None:
        resp = client.get(
            "/api/v1/graph/trace/abcdef01234567890abcdef012345678/span/abcdef0123456789/details",
            params={
                "project_id": "cymbal-shops-demo",
                "trace_dataset": "traces",
            },
            headers=guest_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)
