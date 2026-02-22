"""Tests for the agent graph topology and trajectory endpoints."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sre_agent.api.routers.agent_graph import (
    _build_time_filter,
    _detect_loops,
    _get_node_color,
    _node_type_to_rf_type,
    _validate_identifier,
    _validate_iso8601,
    _validate_logical_node_id,
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


def _mock_query_result(rows: list[MagicMock]) -> list[MagicMock]:
    """Wrap rows in a mock query result that is iterable."""
    return rows


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
        bq.query_and_wait.side_effect = [
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

        def mock_query(query, *args, **kwargs):
            if "agent_graph_hourly" in query and "source_id, source_type" in query:
                return _mock_query_result([node_row])
            return _mock_query_result([])

        bq.query_and_wait.side_effect = mock_query

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
        bq.query_and_wait.side_effect = [
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
        bq.query_and_wait.side_effect = [
            _mock_query_result([]),
            _mock_query_result([]),
        ]

        client.get(
            "/api/v1/graph/topology",
            params={"project_id": "test-project", "dataset": "my_ds", "hours": 0},
        )

        # Verify the live view tables are queried, not hourly
        calls = bq.query_and_wait.call_args_list
        queries = [call[0][0] for call in calls]
        assert any("agent_topology_nodes" in q for q in queries)
        assert any("agent_topology_edges" in q for q in queries)

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
        bq.query_and_wait.return_value = _mock_query_result([row])

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
        bq.query_and_wait.return_value = _mock_query_result([row])

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
        bq.query_and_wait.return_value = _mock_query_result([row])

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
        bq.query_and_wait.return_value = _mock_query_result([])

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


class TestValidateLogicalNodeId:
    """Tests for _validate_logical_node_id."""

    def test_accepts_valid_node_id(self) -> None:
        assert _validate_logical_node_id("Agent::root") == "Agent::root"

    def test_accepts_url_encoded_node_id(self) -> None:
        assert _validate_logical_node_id("Agent%3A%3Aroot") == "Agent::root"

    def test_accepts_node_id_with_slash(self) -> None:
        assert _validate_logical_node_id("Tool::search/logs") == "Tool::search/logs"

    def test_rejects_missing_double_colon(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_logical_node_id("AgentRoot")
        assert exc_info.value.status_code == 400

    def test_rejects_empty_string(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_logical_node_id("")
        assert exc_info.value.status_code == 400

    def test_rejects_sql_injection_attempt(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_logical_node_id("Agent::root'; DROP TABLE--")
        assert exc_info.value.status_code == 400


class TestValidateIso8601:
    """Tests for _validate_iso8601."""

    def test_accepts_utc_timestamp(self) -> None:
        assert (
            _validate_iso8601("2026-02-20T12:00:00Z", "start") == "2026-02-20T12:00:00Z"
        )

    def test_accepts_offset_timestamp(self) -> None:
        assert (
            _validate_iso8601("2026-02-20T12:00:00+05:30", "start")
            == "2026-02-20T12:00:00+05:30"
        )

    def test_accepts_fractional_seconds(self) -> None:
        assert (
            _validate_iso8601("2026-02-20T12:00:00.123Z", "start")
            == "2026-02-20T12:00:00.123Z"
        )

    def test_rejects_bare_date(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_iso8601("2026-02-20", "start")
        assert exc_info.value.status_code == 400

    def test_rejects_sql_injection(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_iso8601("2026'); DROP TABLE--", "start")
        assert exc_info.value.status_code == 400

    def test_rejects_empty_string(self) -> None:
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            _validate_iso8601("", "start")
        assert exc_info.value.status_code == 400


class TestBuildTimeFilter:
    """Tests for _build_time_filter."""

    def test_hours_only(self) -> None:
        result = _build_time_filter(
            timestamp_col="ts", hours=6.0, start_time=None, end_time=None
        )
        assert "INTERVAL 360 MINUTE" in result
        assert "CURRENT_TIMESTAMP()" in result

    def test_start_time_overrides_hours(self) -> None:
        result = _build_time_filter(
            timestamp_col="ts",
            hours=6,
            start_time="2026-02-20T00:00:00Z",
            end_time=None,
        )
        assert "2026-02-20T00:00:00Z" in result
        assert "INTERVAL" not in result

    def test_end_time_used_when_provided(self) -> None:
        result = _build_time_filter(
            timestamp_col="ts",
            hours=6,
            start_time=None,
            end_time="2026-02-20T23:59:59Z",
        )
        assert "2026-02-20T23:59:59Z" in result

    def test_both_start_and_end(self) -> None:
        result = _build_time_filter(
            timestamp_col="ts",
            hours=6,
            start_time="2026-02-20T00:00:00Z",
            end_time="2026-02-20T12:00:00Z",
        )
        assert "2026-02-20T00:00:00Z" in result
        assert "2026-02-20T12:00:00Z" in result


class TestTopologyFiltering:
    """Tests for Phase 2 filtering on topology endpoint."""

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_errors_only_adds_having_clause(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """errors_only=true should add HAVING clause to SQL."""
        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.side_effect = [
            _mock_query_result([]),
            _mock_query_result([]),
        ]

        client.get(
            "/api/v1/graph/topology",
            params={"project_id": "test-project", "hours": 6, "errors_only": "true"},
        )

        calls = bq.query_and_wait.call_args_list
        # First query (nodes CTE) should have HAVING
        assert "HAVING SUM(error_count) > 0" in calls[0][0][0]

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_start_time_param_accepted(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """start_time parameter should be used in the time filter."""
        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.side_effect = [
            _mock_query_result([]),
            _mock_query_result([]),
        ]

        resp = client.get(
            "/api/v1/graph/topology",
            params={
                "project_id": "test-project",
                "start_time": "2026-02-20T00:00:00Z",
            },
        )
        assert resp.status_code == 200

    def test_invalid_start_time_returns_400(self, client: TestClient) -> None:
        """Invalid start_time should be rejected."""
        resp = client.get(
            "/api/v1/graph/topology",
            params={
                "project_id": "test-project",
                "start_time": "not-a-timestamp",
            },
        )
        assert resp.status_code == 400

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_error_edges_have_animated_and_style(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Edges with errors should have animated=true and red stroke style."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        edge_row = _make_row(
            source_id="Agent::root",
            target_id="Tool::broken",
            call_count=5,
            avg_duration_ms=100.0,
            error_count=3,
            total_tokens=500,
        )

        def mock_query(query, *args, **kwargs):
            if "GROUP BY source_id, target_id" in query:
                return _mock_query_result([edge_row])
            return _mock_query_result([])

        bq.query_and_wait.side_effect = mock_query

        data = client.get(
            "/api/v1/graph/topology",
            params={"project_id": "test-project", "hours": 1},
        ).json()

        edge = data["edges"][0]
        assert edge["animated"] is True
        assert edge["style"]["stroke"] == "#f85149"

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_non_error_edges_no_animated(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Edges without errors should not have animated or style keys."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        edge_row = _make_row(
            source_id="Agent::root",
            target_id="Tool::ok",
            call_count=10,
            avg_duration_ms=80.0,
            error_count=0,
            total_tokens=400,
        )

        def mock_query(query, *args, **kwargs):
            if "GROUP BY source_id, target_id" in query:
                return _mock_query_result([edge_row])
            return _mock_query_result([])

        bq.query_and_wait.side_effect = mock_query

        data = client.get(
            "/api/v1/graph/topology",
            params={"project_id": "test-project", "hours": 2},
        ).json()

        edge = data["edges"][0]
        assert "animated" not in edge
        assert "style" not in edge

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_node_data_includes_avg_duration_ms(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Node data should include avgDurationMs field."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        node_row = _make_row(
            node_id="Agent::root",
            node_type="Agent",
            execution_count=10,
            total_tokens=2000,
            error_count=0,
            avg_duration_ms=345.6,
        )
        bq.query_and_wait.side_effect = [
            _mock_query_result([node_row]),
            _mock_query_result([]),
        ]

        data = client.get(
            "/api/v1/graph/topology",
            params={"project_id": "test-project", "hours": 6},
        ).json()

        assert data["nodes"][0]["data"]["avgDurationMs"] == 345.6


class TestNodeDetailEndpoint:
    """Tests for GET /api/v1/graph/node/{logical_node_id}."""

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_returns_200_with_metrics(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Node detail should return 200 with metrics for a valid node."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        metrics_row = _make_row(
            total_invocations=100,
            error_count=5,
            error_rate=0.05,
            input_tokens=50000,
            output_tokens=10000,
            estimated_cost=0.01234,
            p50=120.0,
            p95=450.0,
            p99=980.0,
        )
        error_row = _make_row(message="Connection timeout", count=3)

        bq.query_and_wait.side_effect = [
            _mock_query_result([metrics_row]),
            _mock_query_result([error_row]),
            _mock_query_result([]),  # payloads query
        ]

        resp = client.get(
            "/api/v1/graph/node/Agent%3A%3Aroot",
            params={"project_id": "test-project", "hours": 24},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["nodeId"] == "Agent::root"
        assert data["nodeType"] == "Agent"
        assert data["label"] == "root"
        assert data["totalInvocations"] == 100
        assert data["errorRate"] == 0.05
        assert data["errorCount"] == 5
        assert data["inputTokens"] == 50000
        assert data["outputTokens"] == 10000
        assert data["estimatedCost"] == 0.01234
        assert data["latency"]["p50"] == 120.0
        assert data["latency"]["p95"] == 450.0
        assert data["latency"]["p99"] == 980.0
        assert len(data["topErrors"]) == 1
        assert data["topErrors"][0]["message"] == "Connection timeout"
        assert data["topErrors"][0]["count"] == 3
        assert "recentPayloads" in data
        assert data["recentPayloads"] == []

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_returns_404_when_no_data(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Node detail should return 404 when no invocations found."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        empty_row = _make_row(total_invocations=0)
        bq.query_and_wait.return_value = _mock_query_result([empty_row])

        resp = client.get(
            "/api/v1/graph/node/Agent%3A%3Amissing",
            params={"project_id": "test-project"},
        )
        assert resp.status_code == 404

    def test_invalid_node_id_returns_400(self, client: TestClient) -> None:
        """Invalid node ID format should be rejected."""
        resp = client.get(
            "/api/v1/graph/node/invalid-no-double-colon",
            params={"project_id": "test-project"},
        )
        assert resp.status_code == 400

    def test_missing_project_id_returns_422(self, client: TestClient) -> None:
        """Missing project_id should return 422."""
        resp = client.get("/api/v1/graph/node/Agent%3A%3Aroot")
        assert resp.status_code == 422

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_uses_parameterized_query(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Node detail should use parameterized BQ query (not string interpolation)."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        metrics_row = _make_row(
            total_invocations=1,
            error_count=0,
            error_rate=0.0,
            input_tokens=100,
            output_tokens=50,
            estimated_cost=0.0001,
            p50=10.0,
            p95=20.0,
            p99=30.0,
        )
        bq.query_and_wait.side_effect = [
            _mock_query_result([metrics_row]),
            _mock_query_result([]),
            _mock_query_result([]),  # payloads query
        ]

        client.get(
            "/api/v1/graph/node/Tool%3A%3Asearch",
            params={"project_id": "test-project"},
        )

        # All 3 calls should include a job_config with query_parameters
        for call in bq.query_and_wait.call_args_list:
            job_config = call.kwargs.get("job_config")
            assert job_config is not None
            assert len(job_config.query_parameters) > 0

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_bq_error_returns_500(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """BigQuery failure should return 500."""
        mock_client_fn.side_effect = Exception("BQ timeout")

        resp = client.get(
            "/api/v1/graph/node/Agent%3A%3Aroot",
            params={"project_id": "test-project"},
        )
        assert resp.status_code == 500
        assert "bq timeout" in resp.json()["detail"].lower()


class TestEdgeDetailEndpoint:
    """Tests for GET /api/v1/graph/edge/{source_id}/{target_id}."""

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_returns_200_with_metrics(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Edge detail should return 200 with metrics."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        row = _make_row(
            call_count=50,
            error_count=2,
            error_rate=0.04,
            avg_duration_ms=75.5,
            p95_duration_ms=200.0,
            p99_duration_ms=400.0,
            total_tokens=5000,
            input_tokens=3000,
            output_tokens=2000,
        )
        bq.query_and_wait.return_value = _mock_query_result([row])

        resp = client.get(
            "/api/v1/graph/edge/Agent%3A%3Aroot/Tool%3A%3Asearch",
            params={"project_id": "test-project", "hours": 24},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sourceId"] == "Agent::root"
        assert data["targetId"] == "Tool::search"
        assert data["callCount"] == 50
        assert data["errorCount"] == 2
        assert data["errorRate"] == 0.04
        assert data["avgDurationMs"] == 75.5
        assert data["p95DurationMs"] == 200.0
        assert data["p99DurationMs"] == 400.0
        assert data["totalTokens"] == 5000
        assert data["inputTokens"] == 3000
        assert data["outputTokens"] == 2000

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_returns_404_when_no_data(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Edge detail should return 404 when no matching edge data found."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        row = _make_row(call_count=None)
        bq.query_and_wait.return_value = _mock_query_result([row])

        resp = client.get(
            "/api/v1/graph/edge/Agent%3A%3Aroot/Tool%3A%3Amissing",
            params={"project_id": "test-project"},
        )
        assert resp.status_code == 404

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_returns_404_when_zero_calls(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Edge detail should return 404 when call_count is zero."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        row = _make_row(call_count=0)
        bq.query_and_wait.return_value = _mock_query_result([row])

        resp = client.get(
            "/api/v1/graph/edge/Agent%3A%3Aroot/Tool%3A%3Aempty",
            params={"project_id": "test-project"},
        )
        assert resp.status_code == 404

    def test_invalid_source_id_returns_400(self, client: TestClient) -> None:
        """Invalid source node ID should return 400."""
        resp = client.get(
            "/api/v1/graph/edge/invalid/Tool%3A%3Asearch",
            params={"project_id": "test-project"},
        )
        assert resp.status_code == 400

    def test_invalid_target_id_returns_400(self, client: TestClient) -> None:
        """Invalid target node ID should return 400."""
        resp = client.get(
            "/api/v1/graph/edge/Agent%3A%3Aroot/invalid",
            params={"project_id": "test-project"},
        )
        assert resp.status_code == 400

    def test_missing_project_id_returns_422(self, client: TestClient) -> None:
        """Missing project_id should return 422."""
        resp = client.get("/api/v1/graph/edge/Agent%3A%3Aroot/Tool%3A%3Asearch")
        assert resp.status_code == 422

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_uses_parameterized_query(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Edge detail should use parameterized BQ query."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        row = _make_row(
            call_count=10,
            error_count=0,
            error_rate=0.0,
            avg_duration_ms=50.0,
            p95_duration_ms=100.0,
            p99_duration_ms=150.0,
            total_tokens=1000,
            input_tokens=600,
            output_tokens=400,
        )
        bq.query_and_wait.return_value = _mock_query_result([row])

        client.get(
            "/api/v1/graph/edge/Agent%3A%3Aroot/Tool%3A%3Asearch",
            params={"project_id": "test-project"},
        )

        call = bq.query_and_wait.call_args
        job_config = call.kwargs.get("job_config")
        assert job_config is not None
        param_names = [p.name for p in job_config.query_parameters]
        assert "source_id" in param_names
        assert "target_id" in param_names

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_bq_error_returns_500(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """BigQuery failure should return 500."""
        mock_client_fn.side_effect = Exception("Network error")

        resp = client.get(
            "/api/v1/graph/edge/Agent%3A%3Aroot/Tool%3A%3Asearch",
            params={"project_id": "test-project"},
        )
        assert resp.status_code == 500
        assert "network error" in resp.json()["detail"].lower()


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

    def test_node_detail_route_exists(self) -> None:
        """The /node/{logical_node_id} route should be registered."""
        paths = [route.path for route in router.routes]
        assert "/api/v1/graph/node/{logical_node_id:path}" in paths

    def test_edge_detail_route_exists(self) -> None:
        """The /edge/{source_id}/{target_id} route should be registered."""
        paths = [route.path for route in router.routes]
        assert "/api/v1/graph/edge/{source_id:path}/{target_id:path}" in paths

    def test_timeseries_route_exists(self) -> None:
        """The /timeseries route should be registered."""
        paths = [route.path for route in router.routes]
        assert "/api/v1/graph/timeseries" in paths


class TestDetectLoops:
    """Tests for the _detect_loops function."""

    def test_no_loop_in_short_sequence(self) -> None:
        assert _detect_loops(["A", "B"]) == []

    def test_no_loop_in_non_repeating_sequence(self) -> None:
        assert _detect_loops(["A", "B", "C", "D", "E"]) == []

    def test_detects_single_node_loop(self) -> None:
        """A->A->A should be detected as a loop."""
        result = _detect_loops(["A", "A", "A"])
        assert len(result) == 1
        assert result[0]["cycle"] == ["A"]
        assert result[0]["repetitions"] == 3

    def test_detects_two_node_cycle(self) -> None:
        """A->B->A->B->A->B should be detected."""
        result = _detect_loops(["A", "B", "A", "B", "A", "B"])
        assert len(result) >= 1
        two_cycles = [r for r in result if r["cycle"] == ["A", "B"]]
        assert len(two_cycles) == 1
        assert two_cycles[0]["repetitions"] == 3

    def test_detects_loop_with_prefix(self) -> None:
        """Non-looping prefix followed by loop should be detected."""
        result = _detect_loops(["X", "Y", "A", "B", "A", "B", "A", "B"])
        two_cycles = [r for r in result if r["cycle"] == ["A", "B"]]
        assert len(two_cycles) == 1
        assert two_cycles[0]["startIndex"] == 2

    def test_min_repeats_respected(self) -> None:
        """Two repetitions should not be detected with min_repeats=3."""
        result = _detect_loops(["A", "B", "A", "B"])
        assert result == []

    def test_custom_min_repeats(self) -> None:
        """min_repeats=2 should detect 2 repetitions."""
        result = _detect_loops(["A", "B", "A", "B"], min_repeats=2)
        assert len(result) >= 1

    def test_empty_sequence(self) -> None:
        assert _detect_loops([]) == []


class TestNodeDetailPayloads:
    """Tests for Phase 3 payload data in node detail endpoint."""

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_returns_recent_payloads(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Node detail should include recentPayloads array."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        metrics_row = _make_row(
            total_invocations=10,
            error_count=0,
            error_rate=0.0,
            input_tokens=1000,
            output_tokens=500,
            estimated_cost=0.001,
            p50=50.0,
            p95=100.0,
            p99=200.0,
        )
        payload_row = _make_row(
            span_id="span-123",
            start_time=None,
            node_type="LLM",
            prompt='{"text": "hello"}',
            completion='{"text": "world"}',
            tool_input=None,
            tool_output=None,
        )

        def mock_query(query, *args, **kwargs):
            if "COUNT(*)" in query and "total_invocations" in query:
                return _mock_query_result([metrics_row])
            if "status_code AS message" in query:
                return _mock_query_result([])
            if "JSON_VALUE(s.attributes" in query:
                return _mock_query_result([payload_row])
            return _mock_query_result([])

        bq.query_and_wait.side_effect = mock_query

        resp = client.get(
            "/api/v1/graph/node/LLM%3A%3Agemini",
            params={"project_id": "test-project"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["recentPayloads"]) == 1
        p = data["recentPayloads"][0]
        assert p["spanId"] == "span-123"
        assert p["nodeType"] == "LLM"
        assert p["prompt"] == '{"text": "hello"}'
        assert p["completion"] == '{"text": "world"}'
        assert p["toolInput"] is None

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_payload_query_uses_trace_dataset(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Payload query should reference the trace_dataset parameter."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        metrics_row = _make_row(
            total_invocations=1,
            error_count=0,
            error_rate=0.0,
            input_tokens=100,
            output_tokens=50,
            estimated_cost=0.0001,
            p50=10.0,
            p95=20.0,
            p99=30.0,
        )
        bq.query_and_wait.side_effect = [
            _mock_query_result([metrics_row]),
            _mock_query_result([]),
            _mock_query_result([]),
        ]

        client.get(
            "/api/v1/graph/node/Agent%3A%3Aroot",
            params={
                "project_id": "test-project",
                "trace_dataset": "my_traces",
            },
        )

        # The third query (payloads) should reference the trace dataset
        found = False
        for call in bq.query_and_wait.call_args_list:
            if "my_traces._AllSpans" in call[0][0]:
                found = True
                break
        assert found, "Expected to find my_traces._AllSpans in one of the queries"


class TestTrajectoriesLoopDetection:
    """Tests for Phase 3 loop detection in trajectories endpoint."""

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_response_includes_loop_traces(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Trajectories response should include loopTraces key."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        sankey_row = _make_row(
            source_node="Agent::root",
            source_type="Agent",
            target_node="Tool::search",
            target_type="Tool",
            trace_count=5,
        )
        loop_row = _make_row(
            trace_id="trace-abc",
            step_sequence=["A", "B", "A", "B", "A", "B"],
        )

        bq.query_and_wait.side_effect = [
            _mock_query_result([sankey_row]),
            _mock_query_result([loop_row]),
        ]

        resp = client.get(
            "/api/v1/graph/trajectories",
            params={"project_id": "test-project"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "loopTraces" in data
        assert len(data["loopTraces"]) == 1
        assert data["loopTraces"][0]["traceId"] == "trace-abc"
        assert len(data["loopTraces"][0]["loops"]) >= 1

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_no_loops_returns_empty_list(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """No loops should return empty loopTraces."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        loop_row = _make_row(
            trace_id="trace-xyz",
            step_sequence=["A", "B", "C"],
        )

        bq.query_and_wait.side_effect = [
            _mock_query_result([]),  # sankey
            _mock_query_result([loop_row]),
        ]

        data = client.get(
            "/api/v1/graph/trajectories",
            params={"project_id": "test-project"},
        ).json()

        assert data["loopTraces"] == []


class TestTimeSeriesEndpoint:
    """Tests for GET /api/v1/graph/timeseries."""

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_returns_200_with_series_dict(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Timeseries endpoint should return 200 with a series dict."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        row = _make_row(
            time_bucket="2026-02-20T10:00:00+00:00",
            node_id="Agent::root",
            call_count=12,
            error_count=1,
            avg_duration_ms=432.1,
            total_tokens=840,
            total_cost=0.001234,
        )
        bq.query_and_wait.return_value = _mock_query_result([row])

        resp = client.get(
            "/api/v1/graph/timeseries",
            params={"project_id": "test-project", "hours": 24},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "series" in data
        assert isinstance(data["series"], dict)

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_series_point_has_required_fields(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Each series point should have all required metric fields."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        row = _make_row(
            time_bucket="2026-02-20T10:00:00+00:00",
            node_id="Agent::root",
            call_count=12,
            error_count=1,
            avg_duration_ms=432.1,
            total_tokens=840,
            total_cost=0.001234,
        )
        bq.query_and_wait.return_value = _mock_query_result([row])

        data = client.get(
            "/api/v1/graph/timeseries",
            params={"project_id": "test-project", "hours": 24},
        ).json()

        point = data["series"]["Agent::root"][0]
        assert "bucket" in point
        assert "callCount" in point
        assert "errorCount" in point
        assert "avgDurationMs" in point
        assert "totalTokens" in point
        assert "totalCost" in point

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_multiple_nodes_returned_as_separate_keys(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Different node_ids should appear as separate keys in series."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        row1 = _make_row(
            time_bucket="2026-02-20T10:00:00+00:00",
            node_id="Agent::root",
            call_count=5,
            error_count=0,
            avg_duration_ms=100.0,
            total_tokens=400,
            total_cost=0.001,
        )
        row2 = _make_row(
            time_bucket="2026-02-20T10:00:00+00:00",
            node_id="Tool::search",
            call_count=8,
            error_count=2,
            avg_duration_ms=200.0,
            total_tokens=600,
            total_cost=0.002,
        )
        bq.query_and_wait.return_value = _mock_query_result([row1, row2])

        data = client.get(
            "/api/v1/graph/timeseries",
            params={"project_id": "test-project", "hours": 6},
        ).json()

        assert "Agent::root" in data["series"]
        assert "Tool::search" in data["series"]

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_multiple_buckets_per_node_are_ordered(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Multiple buckets for the same node should preserve order."""
        bq = MagicMock()
        mock_client_fn.return_value = bq

        row1 = _make_row(
            time_bucket="2026-02-20T10:00:00+00:00",
            node_id="Agent::root",
            call_count=5,
            error_count=0,
            avg_duration_ms=100.0,
            total_tokens=400,
            total_cost=0.001,
        )
        row2 = _make_row(
            time_bucket="2026-02-20T11:00:00+00:00",
            node_id="Agent::root",
            call_count=8,
            error_count=1,
            avg_duration_ms=150.0,
            total_tokens=600,
            total_cost=0.002,
        )
        bq.query_and_wait.return_value = _mock_query_result([row1, row2])

        data = client.get(
            "/api/v1/graph/timeseries",
            params={"project_id": "test-project", "hours": 6},
        ).json()

        points = data["series"]["Agent::root"]
        assert len(points) == 2
        assert points[0]["bucket"] == "2026-02-20T10:00:00+00:00"
        assert points[1]["bucket"] == "2026-02-20T11:00:00+00:00"

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_empty_result_returns_empty_series(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Empty BigQuery result should return empty series dict."""
        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.return_value = _mock_query_result([])

        data = client.get(
            "/api/v1/graph/timeseries",
            params={"project_id": "test-project", "hours": 24},
        ).json()

        assert data["series"] == {}

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_bq_error_returns_500(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """BigQuery errors should return HTTP 500."""
        mock_client_fn.side_effect = Exception("Connection refused")

        resp = client.get(
            "/api/v1/graph/timeseries",
            params={"project_id": "test-project", "hours": 24},
        )
        assert resp.status_code == 500

    def test_missing_project_id_returns_422(self, client: TestClient) -> None:
        """Missing required project_id should return 422."""
        resp = client.get("/api/v1/graph/timeseries")
        assert resp.status_code == 422

    def test_invalid_project_id_returns_400(self, client: TestClient) -> None:
        """SQL-injection-style project_id should be rejected."""
        resp = client.get(
            "/api/v1/graph/timeseries",
            params={"project_id": "proj; DROP TABLE x--"},
        )
        assert resp.status_code == 400

    def test_hours_below_minimum_returns_422(self, client: TestClient) -> None:
        """hours=-1 should be rejected since ge=0.0."""
        resp = client.get(
            "/api/v1/graph/timeseries",
            params={"project_id": "test-project", "hours": -1.0},
        )
        assert resp.status_code == 422

    def test_hours_above_maximum_returns_422(self, client: TestClient) -> None:
        """hours=721 should be rejected since le=720."""
        resp = client.get(
            "/api/v1/graph/timeseries",
            params={"project_id": "test-project", "hours": 721},
        )
        assert resp.status_code == 422

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_start_time_param_accepted(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """start_time parameter should be used in the time filter."""
        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.return_value = _mock_query_result([])

        resp = client.get(
            "/api/v1/graph/timeseries",
            params={
                "project_id": "test-project",
                "start_time": "2026-02-20T00:00:00Z",
            },
        )
        assert resp.status_code == 200

    def test_invalid_start_time_returns_400(self, client: TestClient) -> None:
        """Invalid start_time should be rejected."""
        resp = client.get(
            "/api/v1/graph/timeseries",
            params={
                "project_id": "test-project",
                "start_time": "not-a-timestamp",
            },
        )
        assert resp.status_code == 400

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_uses_time_bucket_column_in_query(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """SQL should reference time_bucket column."""
        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.return_value = _mock_query_result([])

        client.get(
            "/api/v1/graph/timeseries",
            params={"project_id": "test-project", "hours": 6},
        )

        sql = bq.query_and_wait.call_args[0][0]
        assert "time_bucket" in sql

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_only_one_bq_query_issued(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        """Timeseries should issue exactly one BigQuery query."""
        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.return_value = _mock_query_result([])

        client.get(
            "/api/v1/graph/timeseries",
            params={"project_id": "test-project", "hours": 24},
        )

        assert bq.query_and_wait.call_count == 1


class TestRegistryEndpoints:
    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_get_agent_registry_success(self, mock_get_client, client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Mock the BigQuery RowIterator
        mock_row = MagicMock()
        mock_row.service_name = "test-service"
        mock_row.agent_id = "Agent::test-agent"
        mock_row.agent_name = "test-agent"
        mock_row.total_sessions = 10
        mock_row.total_turns = 50
        mock_row.input_tokens = 1000
        mock_row.output_tokens = 2000
        mock_row.error_count = 2
        mock_row.error_rate = 0.04
        mock_row.p50_duration_ms = 150.0
        mock_row.p95_duration_ms = 500.0
        mock_client.query_and_wait.return_value = [mock_row]

        response = client.get(
            "/api/v1/graph/registry/agents?project_id=test-project&dataset=test_ds"
        )

        assert response.status_code == 200
        data = response.json()
        assert "agents" in data
        assert len(data["agents"]) == 1
        agent = data["agents"][0]
        assert agent["serviceName"] == "test-service"
        assert agent["agentId"] == "Agent::test-agent"
        assert agent["agentName"] == "test-agent"
        assert agent["totalSessions"] == 10
        assert agent["errorRate"] == 0.04
        assert agent["p95DurationMs"] == 500.0

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_get_tool_registry_success(self, mock_get_client, client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_row = MagicMock()
        mock_row.service_name = "test-service"
        mock_row.tool_id = "Tool::search"
        mock_row.tool_name = "search"
        mock_row.execution_count = 100
        mock_row.error_count = 5
        mock_row.error_rate = 0.05
        mock_row.avg_duration_ms = 200.0
        mock_row.p95_duration_ms = 600.0
        mock_client.query_and_wait.return_value = [mock_row]

        response = client.get(
            "/api/v1/graph/registry/tools?project_id=test-project&dataset=test_ds"
        )

        assert response.status_code == 200
        data = response.json()
        assert "tools" in data
        assert len(data["tools"]) == 1
        tool = data["tools"][0]
        assert tool["serviceName"] == "test-service"
        assert tool["toolId"] == "Tool::search"
        assert tool["toolName"] == "search"
        assert tool["executionCount"] == 100
        assert tool["errorRate"] == 0.05
        assert tool["p95DurationMs"] == 600.0


class TestDashboardKpis:
    """Tests for GET /dashboard/kpis endpoint."""

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_returns_kpis_with_trends(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.return_value = [
            _make_row(
                total_sessions=42,
                root_invocations=28,
                avg_turns=3.5,
                error_rate=0.02,
                prev_total_sessions=30,
                prev_root_invocations=20,
                prev_avg_turns=4.0,
                prev_error_rate=0.03,
            )
        ]

        resp = client.get(
            "/api/v1/graph/dashboard/kpis",
            params={"project_id": "test-project"},
        )

        assert resp.status_code == 200
        data = resp.json()
        kpis = data["kpis"]
        assert kpis["totalSessions"] == 42
        assert kpis["avgTurns"] == 3.5
        assert kpis["rootInvocations"] == 28
        assert kpis["errorRate"] == 0.02
        assert isinstance(kpis["totalSessionsTrend"], (int, float))
        assert isinstance(kpis["errorRateTrend"], (int, float))

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_returns_zeroes_when_no_data(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.return_value = []

        resp = client.get(
            "/api/v1/graph/dashboard/kpis",
            params={"project_id": "test-project"},
        )

        assert resp.status_code == 200
        kpis = resp.json()["kpis"]
        assert kpis["totalSessions"] == 0
        assert kpis["avgTurns"] == 0
        assert kpis["rootInvocations"] == 0
        assert kpis["errorRate"] == 0

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_not_found_returns_404_not_setup(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        from google.api_core.exceptions import NotFound

        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.side_effect = NotFound("Table not found")

        resp = client.get(
            "/api/v1/graph/dashboard/kpis",
            params={"project_id": "test-project"},
        )

        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "NOT_SETUP"

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_unexpected_error_returns_500(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.side_effect = RuntimeError("boom")

        resp = client.get(
            "/api/v1/graph/dashboard/kpis",
            params={"project_id": "test-project"},
        )

        assert resp.status_code == 500

    def test_invalid_project_id_returns_400(self, client: TestClient) -> None:
        resp = client.get(
            "/api/v1/graph/dashboard/kpis",
            params={"project_id": "bad;sql"},
        )
        assert resp.status_code == 400

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_service_name_filter_included_in_sql(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.return_value = [
            _make_row(
                total_sessions=1,
                root_invocations=1,
                avg_turns=1.0,
                error_rate=0.0,
                prev_total_sessions=0,
                prev_root_invocations=0,
                prev_avg_turns=0.0,
                prev_error_rate=0.0,
            )
        ]

        client.get(
            "/api/v1/graph/dashboard/kpis",
            params={"project_id": "test-project", "service_name": "my-agent"},
        )

        sql = bq.query_and_wait.call_args[0][0]
        assert "my-agent" in sql


class TestDashboardTimeseries:
    """Tests for GET /dashboard/timeseries endpoint."""

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_returns_latency_qps_tokens(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        from datetime import datetime

        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.return_value = [
            _make_row(
                time_bucket=datetime(2026, 2, 22, 12, 0),
                total_calls=360,
                total_errors=4,
                avg_duration_ms=120.5,
                p95_duration_ms=350.3,
                input_tokens=5000,
                output_tokens=2000,
            )
        ]

        resp = client.get(
            "/api/v1/graph/dashboard/timeseries",
            params={"project_id": "test-project", "hours": 24},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["latency"]) == 1
        assert len(data["qps"]) == 1
        assert len(data["tokens"]) == 1
        assert data["latency"][0]["p50"] == 120.5
        assert data["latency"][0]["p95"] == 350.3
        assert data["qps"][0]["qps"] == round(360 / 3600.0, 2)
        assert data["tokens"][0]["input"] == 5000
        assert data["tokens"][0]["output"] == 2000

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_empty_data_returns_empty_arrays(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.return_value = []

        resp = client.get(
            "/api/v1/graph/dashboard/timeseries",
            params={"project_id": "test-project"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data == {"latency": [], "qps": [], "tokens": []}

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_not_found_returns_404(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        from google.api_core.exceptions import NotFound

        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.side_effect = NotFound("Table not found")

        resp = client.get(
            "/api/v1/graph/dashboard/timeseries",
            params={"project_id": "test-project"},
        )

        assert resp.status_code == 404
        assert resp.json()["detail"]["code"] == "NOT_SETUP"

    def test_hours_below_minimum_returns_422(self, client: TestClient) -> None:
        resp = client.get(
            "/api/v1/graph/dashboard/timeseries",
            params={"project_id": "test-project", "hours": 0.5},
        )
        assert resp.status_code == 422


class TestDashboardModels:
    """Tests for GET /dashboard/models endpoint."""

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_returns_model_calls(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.return_value = [
            _make_row(
                model_name="gemini-2.5-flash",
                total_calls=100,
                p95_duration=1200.5,
                error_rate=2.5,
                tokens_used=50000,
            )
        ]

        resp = client.get(
            "/api/v1/graph/dashboard/models",
            params={"project_id": "test-project"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["modelCalls"]) == 1
        row = data["modelCalls"][0]
        assert row["modelName"] == "gemini-2.5-flash"
        assert row["totalCalls"] == 100
        assert row["p95Duration"] == 1200.5
        assert row["errorRate"] == 2.5
        assert row["quotaExits"] == 0
        assert row["tokensUsed"] == 50000

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_empty_returns_empty_list(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.return_value = []

        resp = client.get(
            "/api/v1/graph/dashboard/models",
            params={"project_id": "test-project"},
        )

        assert resp.status_code == 200
        assert resp.json() == {"modelCalls": []}

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_not_found_returns_404(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        from google.api_core.exceptions import NotFound

        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.side_effect = NotFound("Table not found")

        resp = client.get(
            "/api/v1/graph/dashboard/models",
            params={"project_id": "test-project"},
        )

        assert resp.status_code == 404

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_multiple_models_sorted(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.return_value = [
            _make_row(
                model_name="flash",
                total_calls=200,
                p95_duration=100.0,
                error_rate=1.0,
                tokens_used=80000,
            ),
            _make_row(
                model_name="pro",
                total_calls=50,
                p95_duration=300.0,
                error_rate=0.5,
                tokens_used=20000,
            ),
        ]

        resp = client.get(
            "/api/v1/graph/dashboard/models",
            params={"project_id": "test-project"},
        )

        assert resp.status_code == 200
        models = resp.json()["modelCalls"]
        assert len(models) == 2
        assert models[0]["modelName"] == "flash"
        assert models[1]["modelName"] == "pro"


class TestDashboardTools:
    """Tests for GET /dashboard/tools endpoint."""

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_returns_tool_calls(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.return_value = [
            _make_row(
                tool_name="fetch_traces",
                total_calls=80,
                p95_duration=500.3,
                error_rate=1.2,
            )
        ]

        resp = client.get(
            "/api/v1/graph/dashboard/tools",
            params={"project_id": "test-project"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["toolCalls"]) == 1
        row = data["toolCalls"][0]
        assert row["toolName"] == "fetch_traces"
        assert row["totalCalls"] == 80
        assert row["p95Duration"] == 500.3
        assert row["errorRate"] == 1.2

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_empty_returns_empty_list(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.return_value = []

        resp = client.get(
            "/api/v1/graph/dashboard/tools",
            params={"project_id": "test-project"},
        )

        assert resp.status_code == 200
        assert resp.json() == {"toolCalls": []}

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_not_found_returns_404(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        from google.api_core.exceptions import NotFound

        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.side_effect = NotFound("Table not found")

        resp = client.get(
            "/api/v1/graph/dashboard/tools",
            params={"project_id": "test-project"},
        )

        assert resp.status_code == 404

    def test_invalid_dataset_returns_400(self, client: TestClient) -> None:
        resp = client.get(
            "/api/v1/graph/dashboard/tools",
            params={"project_id": "test-project", "dataset": "drop;table"},
        )
        assert resp.status_code == 400


class TestDashboardLogs:
    """Tests for GET /dashboard/logs endpoint."""

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_returns_agent_logs(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        from datetime import datetime

        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.return_value = [
            _make_row(
                start_time=datetime(2026, 2, 22, 12, 0),
                node_type="Agent",
                node_label="sre_agent",
                duration_ms=500.0,
                status_code=0,
                status_desc="OK",
                input_tokens=800,
                output_tokens=200,
                trace_id="abc123def456",
                error_type=None,
            )
        ]

        resp = client.get(
            "/api/v1/graph/dashboard/logs",
            params={"project_id": "test-project"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["agentLogs"]) == 1
        log = data["agentLogs"][0]
        assert log["agentId"] == "sre_agent"
        assert log["severity"] == "INFO"
        assert log["traceId"] == "abc123def456"
        assert "sre_agent" in log["message"]
        assert "500ms" in log["message"]
        assert "1000 tokens" in log["message"]

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_error_status_yields_error_severity(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        from datetime import datetime

        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.return_value = [
            _make_row(
                start_time=datetime(2026, 2, 22, 12, 0),
                node_type="Tool",
                node_label="fetch_traces",
                duration_ms=2000.0,
                status_code=2,
                status_desc="TIMEOUT",
                input_tokens=0,
                output_tokens=0,
                trace_id="err123",
                error_type="timeout",
            )
        ]

        resp = client.get(
            "/api/v1/graph/dashboard/logs",
            params={"project_id": "test-project"},
        )

        assert resp.status_code == 200
        log = resp.json()["agentLogs"][0]
        assert log["severity"] == "ERROR"
        assert "error=timeout" in log["message"]

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_slow_duration_yields_warning(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        from datetime import datetime

        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.return_value = [
            _make_row(
                start_time=datetime(2026, 2, 22, 12, 0),
                node_type="Agent",
                node_label="slow_agent",
                duration_ms=15000.0,
                status_code=0,
                status_desc="OK",
                input_tokens=0,
                output_tokens=0,
                trace_id="slow123",
                error_type=None,
            )
        ]

        resp = client.get(
            "/api/v1/graph/dashboard/logs",
            params={"project_id": "test-project"},
        )

        assert resp.status_code == 200
        log = resp.json()["agentLogs"][0]
        assert log["severity"] == "WARNING"

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_llm_node_yields_debug_severity(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        from datetime import datetime

        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.return_value = [
            _make_row(
                start_time=datetime(2026, 2, 22, 12, 0),
                node_type="LLM",
                node_label="gemini-flash",
                duration_ms=300.0,
                status_code=0,
                status_desc=None,
                input_tokens=500,
                output_tokens=100,
                trace_id="llm123",
                error_type=None,
            )
        ]

        resp = client.get(
            "/api/v1/graph/dashboard/logs",
            params={"project_id": "test-project"},
        )

        assert resp.status_code == 200
        log = resp.json()["agentLogs"][0]
        assert log["severity"] == "DEBUG"

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_custom_limit_param(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.return_value = []

        client.get(
            "/api/v1/graph/dashboard/logs",
            params={"project_id": "test-project", "limit": 500},
        )

        sql = bq.query_and_wait.call_args[0][0]
        assert "LIMIT 500" in sql

    @patch("sre_agent.api.routers.agent_graph._get_bq_client")
    def test_not_found_returns_404(
        self, mock_client_fn: MagicMock, client: TestClient
    ) -> None:
        from google.api_core.exceptions import NotFound

        bq = MagicMock()
        mock_client_fn.return_value = bq
        bq.query_and_wait.side_effect = NotFound("Table not found")

        resp = client.get(
            "/api/v1/graph/dashboard/logs",
            params={"project_id": "test-project"},
        )

        assert resp.status_code == 404

    def test_limit_below_minimum_returns_422(self, client: TestClient) -> None:
        resp = client.get(
            "/api/v1/graph/dashboard/logs",
            params={"project_id": "test-project", "limit": 10},
        )
        assert resp.status_code == 422

    def test_limit_above_maximum_returns_422(self, client: TestClient) -> None:
        resp = client.get(
            "/api/v1/graph/dashboard/logs",
            params={"project_id": "test-project", "limit": 10000},
        )
        assert resp.status_code == 422
