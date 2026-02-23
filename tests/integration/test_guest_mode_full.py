"""Full guest mode integration test — ensures every feature works.

Hits every major endpoint with guest mode headers and verifies non-empty,
schema-valid responses. This is the smoke test to confirm that the entire
demo mode pipeline (synthetic data generation → API response) is functional.
"""

import json

import pytest
from fastapi.testclient import TestClient

from sre_agent.api import create_app

app = create_app()


@pytest.fixture
def guest_client():
    client = TestClient(app)
    client.headers.update(
        {
            "X-Guest-Mode": "true",
            "Authorization": "Bearer dev-mode-bypass-token",
        }
    )
    return client


GRAPH_BASE = "/api/v1/graph"
GRAPH_PARAMS = {"project_id": "cymbal-shops-demo", "hours": 168}


class TestGuestModeAgentGraph:
    """Test all agent graph endpoints in guest mode."""

    def test_topology(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/topology", params=GRAPH_PARAMS)
        assert r.status_code == 200
        data = r.json()
        assert len(data["nodes"]) > 0
        assert len(data["edges"]) > 0

    def test_trajectories(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/trajectories", params=GRAPH_PARAMS)
        assert r.status_code == 200
        data = r.json()
        assert len(data["nodes"]) > 0
        assert len(data["links"]) > 0

    def test_timeseries(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/timeseries", params=GRAPH_PARAMS)
        assert r.status_code == 200
        data = r.json()
        assert "series" in data
        assert len(data["series"]) > 0
        # Each node's series should have TimeSeriesPoint entries
        for _node_id, points in data["series"].items():
            assert len(points) > 0
            assert "bucket" in points[0]
            assert "callCount" in points[0]
            assert "errorCount" in points[0]
            assert "avgDurationMs" in points[0]

    def test_node_detail(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/node/cymbal-assistant", params=GRAPH_PARAMS)
        assert r.status_code == 200

    def test_setup_returns_ok(self, guest_client):
        r = guest_client.post(
            f"{GRAPH_BASE}/setup",
            json={
                "project_id": "cymbal-shops-demo",
                "trace_dataset": "demo_traces",
                "service_name": "cymbal-assistant",
            },
        )
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestGuestModeDashboard:
    """Test all AgentOps dashboard endpoints in guest mode."""

    def test_dashboard_kpis(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/dashboard/kpis", params=GRAPH_PARAMS)
        assert r.status_code == 200
        kpis = r.json()["kpis"]
        assert kpis["totalSessions"] > 0
        assert kpis["rootInvocations"] > 0

    def test_dashboard_timeseries(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/dashboard/timeseries", params=GRAPH_PARAMS)
        assert r.status_code == 200

    def test_dashboard_models(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/dashboard/models", params=GRAPH_PARAMS)
        assert r.status_code == 200
        assert len(r.json()["modelCalls"]) > 0

    def test_dashboard_tools(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/dashboard/tools", params=GRAPH_PARAMS)
        assert r.status_code == 200
        assert len(r.json()["toolCalls"]) > 0

    def test_dashboard_logs(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/dashboard/logs", params=GRAPH_PARAMS)
        assert r.status_code == 200

    def test_dashboard_sessions(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/dashboard/sessions", params=GRAPH_PARAMS)
        assert r.status_code == 200

    def test_dashboard_traces(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/dashboard/traces", params=GRAPH_PARAMS)
        assert r.status_code == 200


class TestGuestModeRegistry:
    """Test registry endpoints in guest mode."""

    def test_registry_agents(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/registry/agents", params=GRAPH_PARAMS)
        assert r.status_code == 200
        assert len(r.json()["agents"]) > 0

    def test_registry_tools(self, guest_client):
        r = guest_client.get(f"{GRAPH_BASE}/registry/tools", params=GRAPH_PARAMS)
        assert r.status_code == 200
        assert len(r.json()["tools"]) > 0


class TestGuestModeChat:
    """Test chat endpoint in guest mode."""

    def test_chat_returns_streaming_ndjson(self, guest_client):
        r = guest_client.post(
            "/api/genui/chat",
            json={"messages": [{"role": "user", "text": "investigate latency"}]},
        )
        assert r.status_code == 200
        assert "application/x-ndjson" in r.headers.get("content-type", "")

    def test_chat_first_event_is_session(self, guest_client):
        r = guest_client.post(
            "/api/genui/chat",
            json={"messages": [{"role": "user", "text": "hello"}]},
        )
        lines = [line for line in r.text.strip().split("\n") if line.strip()]
        first = json.loads(lines[0])
        assert first["type"] == "session"

    def test_chat_has_text_and_dashboard_events(self, guest_client):
        r = guest_client.post(
            "/api/genui/chat",
            json={"messages": [{"role": "user", "text": "hello"}]},
        )
        lines = [line for line in r.text.strip().split("\n") if line.strip()]
        events = [json.loads(line) for line in lines]
        types = {e["type"] for e in events}
        assert "text" in types
        assert "dashboard" in types

    def test_chat_ends_with_suggestions(self, guest_client):
        r = guest_client.post(
            "/api/genui/chat",
            json={"messages": [{"role": "user", "text": "hello"}]},
        )
        lines = [line for line in r.text.strip().split("\n") if line.strip()]
        last = json.loads(lines[-1])
        assert last["type"] == "suggestions"
        assert len(last["suggestions"]) > 0


class TestGuestModeDashboards:
    """Test custom dashboards endpoints in guest mode."""

    def test_list_dashboards(self, guest_client):
        r = guest_client.get("/api/dashboards")
        assert r.status_code == 200
        data = r.json()
        assert "dashboards" in data

    def test_create_dashboard_returns_demo(self, guest_client):
        r = guest_client.post(
            "/api/dashboards",
            json={"display_name": "Test Dashboard"},
        )
        # In guest mode, create should return a demo dashboard (status 201 or 200)
        assert r.status_code in (200, 201)


class TestGuestModeConfig:
    """Test system config endpoint in guest mode."""

    def test_config_shows_guest_mode(self, guest_client):
        r = guest_client.get("/api/config")
        assert r.status_code == 200
        assert r.json()["guest_mode_enabled"] is True
