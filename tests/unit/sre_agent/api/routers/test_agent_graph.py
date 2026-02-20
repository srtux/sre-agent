"""Tests for the agent graph topology and trajectory endpoints."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sre_agent.api.routers.agent_graph import (
    _get_node_color,
    _node_type_to_rf_type,
    _validate_identifier,
    router,
)


@pytest.fixture
def client() -> TestClient:
    """Create a TestClient with the agent_graph router mounted."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _make_row(**kwargs: Any) -> MagicMock:
    """Create a mock BigQuery Row with attribute access."""
    row = MagicMock()
    for key, value in kwargs.items():
        setattr(row, key, value)
    return row


def _mock_query_result(rows: list[MagicMock]) -> MagicMock:
    """Wrap rows in a mock query result that is iterable."""
    result = MagicMock()
    result.result.return_value = iter(rows)
    return result


class TestHelpers:
    """Tests for module-level helper functions."""

    def test_get_node_color_agent(self) -> None:
        assert _get_node_color("Agent") == "#26A69A"

    def test_get_node_color_tool(self) -> None:
        assert _get_node_color("Tool") == "#FFA726"

    def test_get_node_color_llm(self) -> None:
        assert _get_node_color("LLM") == "#AB47BC"

    def test_get_node_color_user(self) -> None:
        assert _get_node_color("User") == "#42A5F5"

    def test_get_node_color_unknown_returns_grey(self) -> None:
        assert _get_node_color("Unknown") == "#78909C"

    def test_node_type_to_rf_type_agent(self) -> None:
        assert _node_type_to_rf_type("Agent") == "agent"

    def test_node_type_to_rf_type_tool(self) -> None:
        assert _node_type_to_rf_type("Tool") == "tool"

    def test_node_type_to_rf_type_llm(self) -> None:
        assert _node_type_to_rf_type("LLM") == "llm"

    def test_node_type_to_rf_type_unknown_falls_back_to_agent(self) -> None:
        assert _node_type_to_rf_type("SubAgent") == "agent"

    def test_node_type_to_rf_type_none_falls_back(self) -> None:
        assert _node_type_to_rf_type(None) == "agent"

    def test_validate_identifier_accepts_valid(self) -> None:
        assert _validate_identifier("my-project_1.0", "test") == "my-project_1.0"

    def test_validate_identifier_rejects_semicolon(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_identifier("proj; DROP TABLE", "test")
        assert exc_info.value.status_code == 400

    def test_validate_identifier_rejects_backtick(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_identifier("proj`--", "test")
        assert exc_info.value.status_code == 400

    def test_validate_identifier_rejects_empty(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_identifier("", "test")
        assert exc_info.value.status_code == 400


class TestTopologyEndpoint:
    """Tests for GET /api/v1/graph/topology."""

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_returns_200_with_hourly_path(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Topology endpoint should return 200 for hours >= 1."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        node_row = _make_row(
            node_id="Agent::root",
            node_type="Agent",
            execution_count=5,
            total_tokens=1200,
            error_count=0,
            avg_duration_ms=150.0,
        )
        edge_row = _make_row(
            source_id="Agent::root",
            target_id="Tool::search",
            call_count=10,
            avg_duration_ms=50.5,
            error_count=0,
            total_tokens=800,
        )
        bq.query.side_effect = [
            _mock_query_result([node_row]),
            _mock_query_result([edge_row]),
        ]

        resp = client.get(
            "/api/v1/graph/topology",
            params={"project_id": "test-project", "hours": 6},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 1
        assert len(data["edges"]) == 1

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_node_format_react_flow(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Each node should have id, type, data, and position keys."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        node_row = _make_row(
            node_id="Tool::fetch_logs",
            node_type="Tool",
            execution_count=3,
            total_tokens=500,
            error_count=1,
            avg_duration_ms=200.0,
        )
        bq.query.side_effect = [
            _mock_query_result([node_row]),
            _mock_query_result([]),
        ]

        data = client.get(
            "/api/v1/graph/topology",
            params={"project_id": "test-project", "hours": 24},
        ).json()

        node = data["nodes"][0]
        assert node["id"] == "Tool::fetch_logs"
        assert node["type"] == "tool"
        assert node["data"]["label"] == "fetch_logs"
        assert node["data"]["nodeType"] == "Tool"
        assert node["position"] == {"x": 0, "y": 0}

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_edge_format_react_flow(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Each edge should have id, source, target, and data keys."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        edge_row = _make_row(
            source_id="Agent::root",
            target_id="LLM::gemini",
            call_count=7,
            avg_duration_ms=120.3,
            error_count=2,
            total_tokens=3000,
        )
        bq.query.side_effect = [
            _mock_query_result([]),
            _mock_query_result([edge_row]),
        ]

        data = client.get(
            "/api/v1/graph/topology",
            params={"project_id": "test-project", "hours": 1},
        ).json()

        edge = data["edges"][0]
        assert edge["id"] == "Agent::root->LLM::gemini"
        assert edge["source"] == "Agent::root"
        assert edge["target"] == "LLM::gemini"
        assert edge["data"]["callCount"] == 7
        assert edge["data"]["avgDurationMs"] == 120.3

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_sub_hour_uses_live_views(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Hours < 1 should query agent_topology_nodes/edges views."""
        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query.side_effect = [
            _mock_query_result([]),
            _mock_query_result([]),
        ]

        client.get(
            "/api/v1/graph/topology",
            params={"project_id": "test-project", "dataset": "my_ds", "hours": 0},
        )

        # Verify the live view tables are queried, not hourly
        calls = bq.query.call_args_list
        assert "agent_topology_nodes" in calls[0][0][0]
        assert "agent_topology_edges" in calls[1][0][0]

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_bq_error_returns_500(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """BigQuery errors should return HTTP 500."""
        mock_client_fn.side_effect = Exception("Connection refused")

        resp = client.get(
            "/api/v1/graph/topology",
            params={"project_id": "test-project"},
        )
        assert resp.status_code == 500

    def test_missing_project_id_returns_422(self, client: TestClient) -> None:
        """Missing required project_id should return 422."""
        resp = client.get("/api/v1/graph/topology")
        assert resp.status_code == 422

    def test_invalid_project_id_returns_400(self, client: TestClient) -> None:
        """SQL-injection-style project_id should be rejected."""
        resp = client.get(
            "/api/v1/graph/topology",
            params={"project_id": "proj; DROP TABLE x--"},
        )
        assert resp.status_code == 400


class TestTrajectoriesEndpoint:
    """Tests for GET /api/v1/graph/trajectories."""

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_returns_200_with_sankey_format(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Trajectories endpoint should return nodes and links."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        row = _make_row(
            source_node="Agent::root",
            source_type="Agent",
            target_node="Tool::search",
            target_type="Tool",
            trace_count=42,
        )
        bq.query.return_value = _mock_query_result([row])

        resp = client.get(
            "/api/v1/graph/trajectories",
            params={"project_id": "test-project", "hours": 6},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "links" in data

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_nodes_have_colors(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Sankey nodes should include nodeColor from the type mapping."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        row = _make_row(
            source_node="Agent::root",
            source_type="Agent",
            target_node="LLM::gemini",
            target_type="LLM",
            trace_count=10,
        )
        bq.query.return_value = _mock_query_result([row])

        data = client.get(
            "/api/v1/graph/trajectories",
            params={"project_id": "test-project"},
        ).json()

        node_map = {n["id"]: n["nodeColor"] for n in data["nodes"]}
        assert node_map["Agent::root"] == "#26A69A"
        assert node_map["LLM::gemini"] == "#AB47BC"

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_link_value_is_trace_count(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Link value should be the trace_count."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        row = _make_row(
            source_node="Agent::root",
            source_type="Agent",
            target_node="Tool::fetch",
            target_type="Tool",
            trace_count=99,
        )
        bq.query.return_value = _mock_query_result([row])

        data = client.get(
            "/api/v1/graph/trajectories",
            params={"project_id": "test-project"},
        ).json()

        assert data["links"][0]["value"] == 99

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_empty_result_returns_empty_lists(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Empty BigQuery result should return empty nodes and links."""
        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query.return_value = _mock_query_result([])

        data = client.get(
            "/api/v1/graph/trajectories",
            params={"project_id": "test-project"},
        ).json()

        assert data["nodes"] == []
        assert data["links"] == []

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_bq_error_returns_500(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """BigQuery errors should return HTTP 500."""
        mock_client_fn.side_effect = Exception("Quota exceeded")

        resp = client.get(
            "/api/v1/graph/trajectories",
            params={"project_id": "test-project"},
        )
        assert resp.status_code == 500

    def test_missing_project_id_returns_422(self, client: TestClient) -> None:
        """Missing required project_id should return 422."""
        resp = client.get("/api/v1/graph/trajectories")
        assert resp.status_code == 422


class TestRouterConfiguration:
    """Tests for the router object itself."""

    def test_router_tags(self) -> None:
        """Router should be tagged with 'agent_graph'."""
        assert "agent_graph" in router.tags

    def test_router_prefix(self) -> None:
        """Router prefix should be /api/v1/graph."""
        assert router.prefix == "/api/v1/graph"

    def test_topology_route_exists(self) -> None:
        """The /topology route should be registered."""
        paths = [route.path for route in router.routes]
        assert "/api/v1/graph/topology" in paths

    def test_trajectories_route_exists(self) -> None:
        """The /trajectories route should be registered."""
        paths = [route.path for route in router.routes]
        assert "/api/v1/graph/trajectories" in paths
