"""Unit tests for the tools router."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from server import app
from sre_agent.schema import BaseToolResponse, ToolStatus

client = TestClient(app)


@pytest.fixture
def mock_tools():
    with (
        patch(
            "sre_agent.api.routers.tools.fetch_trace", new_callable=AsyncMock
        ) as f_trace,
        patch(
            "sre_agent.api.routers.tools.list_gcp_projects", new_callable=AsyncMock
        ) as l_projects,
        patch(
            "sre_agent.api.routers.tools.list_log_entries", new_callable=AsyncMock
        ) as l_logs,
        patch(
            "sre_agent.api.routers.tools.extract_log_patterns", new_callable=AsyncMock
        ) as e_patterns,
        patch(
            "sre_agent.api.routers.tools.list_time_series", new_callable=AsyncMock
        ) as l_metrics,
        patch(
            "sre_agent.api.routers.tools.query_promql", new_callable=AsyncMock
        ) as q_promql,
        patch(
            "sre_agent.api.routers.tools.list_alerts", new_callable=AsyncMock
        ) as l_alerts,
    ):
        # Return BaseToolResponse objects matching real @adk_tool behavior
        f_trace.return_value = BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={
                "trace_id": "abc",
                "spans": [
                    {
                        "span_id": "1",
                        "name": "test-span",
                        "start_time": "2024-01-01T00:00:00Z",
                        "end_time": "2024-01-01T00:00:01Z",
                        "attributes": {},
                    }
                ],
            },
        )
        l_projects.return_value = {"projects": []}
        l_logs.return_value = BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={"entries": []},
        )
        e_patterns.return_value = BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={"patterns": []},
        )
        l_metrics.return_value = BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=[
                {
                    "metric": {
                        "type": "compute.googleapis.com/instance/cpu/utilization",
                        "labels": {},
                    },
                    "resource": {"labels": {}},
                    "points": [
                        {
                            "interval": {"startTime": "2024-01-01T00:00:00Z"},
                            "value": {"doubleValue": 0.75},
                        }
                    ],
                }
            ],
        )
        q_promql.return_value = BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={
                "status": "success",
                "data": {
                    "resultType": "matrix",
                    "result": [
                        {
                            "metric": {"__name__": "up"},
                            "values": [[1704067200.0, "1"]],
                        }
                    ],
                },
            },
        )
        l_alerts.return_value = BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=[],
        )

        yield {
            "fetch_trace": f_trace,
            "list_gcp_projects": l_projects,
            "list_log_entries": l_logs,
            "extract_log_patterns": e_patterns,
            "list_time_series": l_metrics,
            "query_promql": q_promql,
            "list_alerts": l_alerts,
        }


@pytest.mark.asyncio
async def test_get_trace(mock_tools):
    response = client.get("/api/tools/trace/abc?project_id=test-proj")
    assert response.status_code == 200
    data = response.json()
    # Response is genui_adapter.transform_trace() output
    assert data["trace_id"] == "abc"
    assert len(data["spans"]) == 1
    assert data["spans"][0]["span_id"] == "1"
    assert data["spans"][0]["status"] == "OK"
    mock_tools["fetch_trace"].assert_awaited_once_with(
        trace_id="abc", project_id="test-proj"
    )


@pytest.mark.asyncio
async def test_list_projects(mock_tools):
    response = client.get("/api/tools/projects/list?query=proj")
    assert response.status_code == 200
    assert response.json() == {"projects": []}
    mock_tools["list_gcp_projects"].assert_awaited_once_with(query="proj")


@pytest.mark.asyncio
async def test_list_projects_unwraps_base_tool_response(mock_tools):
    """When list_gcp_projects returns a BaseToolResponse, the endpoint unwraps it."""
    mock_tools["list_gcp_projects"].return_value = BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result={"projects": [{"project_id": "p1", "display_name": "P1"}]},
    )
    response = client.get("/api/tools/projects/list")
    assert response.status_code == 200
    data = response.json()
    # Should get the unwrapped result, not the envelope
    assert "projects" in data
    assert data["projects"][0]["project_id"] == "p1"
    # Must NOT contain BaseToolResponse envelope keys
    assert "status" not in data
    assert "metadata" not in data


@pytest.mark.asyncio
async def test_list_projects_error_returns_502(mock_tools):
    """When list_gcp_projects returns an error BaseToolResponse, endpoint returns 502."""
    mock_tools["list_gcp_projects"].return_value = BaseToolResponse(
        status=ToolStatus.ERROR,
        error="EUC not found",
        result={"projects": []},
    )
    response = client.get("/api/tools/projects/list")
    assert response.status_code == 502
    assert "EUC not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_analyze_logs(mock_tools):
    payload = {"filter": "severity=ERROR", "project_id": "test-proj"}
    response = client.post("/api/tools/logs/analyze", json=payload)
    assert response.status_code == 200
    # extract_log_patterns returns BaseToolResponse wrapping {"patterns": []}
    assert response.json() == {"patterns": []}
    mock_tools["list_log_entries"].assert_awaited_once()
    mock_tools["extract_log_patterns"].assert_awaited_once()


@pytest.fixture
def mock_config_manager():
    with patch("sre_agent.api.routers.tools.get_tool_config_manager") as mock:
        manager = MagicMock()
        manager.test_tool = AsyncMock()
        mock.return_value = manager
        yield manager


@pytest.mark.asyncio
async def test_get_tool_configs(mock_config_manager):
    config = MagicMock()
    config.category.value = "analysis"
    config.enabled = True
    config.testable = True
    config.to_dict.return_value = {"name": "tool1"}
    mock_config_manager.get_all_configs.return_value = [config]

    response = client.get("/api/tools/config")
    assert response.status_code == 200
    data = response.json()
    assert "tools" in data
    assert "analysis" in data["tools"]
    assert data["summary"]["total"] == 1


@pytest.mark.asyncio
async def test_get_tool_config_not_found(mock_config_manager):
    mock_config_manager.get_config.return_value = None
    response = client.get("/api/tools/config/unknown")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_tool_config(mock_config_manager):
    config = MagicMock()
    config.to_dict.return_value = {"name": "tool1", "enabled": True}
    mock_config_manager.get_config.return_value = config
    mock_config_manager.set_enabled.return_value = True

    response = client.put("/api/tools/config/tool1", json={"enabled": True})
    assert response.status_code == 200
    assert response.json()["message"] == "Tool 'tool1' enabled successfully"


@pytest.mark.asyncio
async def test_bulk_update_tool_configs(mock_config_manager):
    config = MagicMock()
    mock_config_manager.get_config.return_value = config
    mock_config_manager.set_enabled.return_value = True

    response = client.post(
        "/api/tools/config/bulk", json={"tool1": True, "tool2": False}
    )
    assert response.status_code == 200
    assert "Bulk update completed" in response.json()["message"]


@pytest.mark.asyncio
async def test_test_tool(mock_config_manager):
    config = MagicMock()
    config.testable = True
    config.name = "tool1"
    mock_config_manager.get_config.return_value = config

    test_result = MagicMock()
    test_result.status.value = "success"
    test_result.message = "OK"
    test_result.latency_ms = 100
    test_result.timestamp = "now"
    test_result.details = {}
    mock_config_manager.test_tool.return_value = test_result

    response = client.post("/api/tools/test/tool1")
    assert response.status_code == 200
    assert response.json()["result"]["status"] == "success"


# =============================================================================
# QUERY ENDPOINT TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_query_metrics_endpoint(mock_tools) -> None:
    payload = {
        "filter": 'metric.type="compute.googleapis.com/instance/cpu/utilization"',
        "minutes_ago": 60,
    }
    response = client.post("/api/tools/metrics/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Response is genui_adapter.transform_metrics() output
    assert data["metric_name"] == "compute.googleapis.com/instance/cpu/utilization"
    assert isinstance(data["points"], list)
    assert isinstance(data["labels"], dict)
    mock_tools["list_time_series"].assert_awaited_once()


@pytest.mark.asyncio
async def test_query_promql_endpoint(mock_tools) -> None:
    payload = {"query": "up", "project_id": "test-proj"}
    response = client.post("/api/tools/metrics/promql", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["metric_name"] == "up"
    assert len(data["points"]) == 1
    assert data["points"][0]["value"] == 1.0
    mock_tools["query_promql"].assert_awaited_once()


@pytest.mark.asyncio
async def test_query_alerts_endpoint_empty(mock_tools) -> None:
    payload = {"project_id": "test-proj"}
    response = client.post("/api/tools/alerts/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Empty alerts list -> "No Active Alerts" timeline
    assert data["title"] == "No Active Alerts"
    assert data["status"] == "resolved"
    assert data["events"] == []
    mock_tools["list_alerts"].assert_awaited_once()


@pytest.mark.asyncio
async def test_query_logs_endpoint(mock_tools) -> None:
    payload = {"filter": "severity>=ERROR", "project_id": "test-proj"}
    response = client.post("/api/tools/logs/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Response is genui_adapter.transform_log_entries() output
    assert "entries" in data
    assert data["entries"] == []
    mock_tools["list_log_entries"].assert_awaited()


@pytest.mark.asyncio
async def test_query_metrics_error_returns_502(mock_tools) -> None:
    """When list_time_series returns an error BaseToolResponse, endpoint returns 502."""
    mock_tools["list_time_series"].return_value = BaseToolResponse(
        status=ToolStatus.ERROR,
        error="Permission denied",
        result=[],
    )
    payload = {"filter": 'metric.type="test"'}
    response = client.post("/api/tools/metrics/query", json=payload)
    assert response.status_code == 502
    assert "Permission denied" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_trace_error_returns_502(mock_tools) -> None:
    """When fetch_trace returns an error BaseToolResponse, endpoint returns 502."""
    mock_tools["fetch_trace"].return_value = BaseToolResponse(
        status=ToolStatus.ERROR,
        error="Trace not found",
        result={},
    )
    response = client.get("/api/tools/trace/missing-id")
    assert response.status_code == 502
    assert "Trace not found" in response.json()["detail"]


# =============================================================================
# BIGQUERY ENDPOINT TESTS
# =============================================================================


@pytest.fixture
def mock_bigquery_client():
    with patch("sre_agent.api.routers.tools.BigQueryClient") as mock_class:
        mock_instance = AsyncMock()
        mock_class.return_value = mock_instance

        mock_instance.execute_query.return_value = [{"col1": "val1", "col2": 2}]
        mock_instance.list_datasets.return_value = ["dataset1", "dataset2"]
        mock_instance.list_tables.return_value = ["table1", "table2"]
        mock_instance.get_table_schema.return_value = [
            {"name": "col1", "type": "STRING"},
            {"name": "col2", "type": "INTEGER"},
        ]

        yield mock_instance


@pytest.mark.asyncio
async def test_query_bigquery_endpoint(mock_bigquery_client) -> None:
    payload = {"sql": "SELECT * FROM t", "project_id": "test-proj"}
    response = client.post("/api/tools/bigquery/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["columns"] == ["col1", "col2"]
    assert len(data["rows"]) == 1
    assert data["rows"][0]["col1"] == "val1"
    mock_bigquery_client.execute_query.assert_awaited_once_with("SELECT * FROM t")


@pytest.mark.asyncio
async def test_list_bigquery_datasets(mock_bigquery_client) -> None:
    response = client.get("/api/tools/bigquery/datasets?project_id=test-proj")
    assert response.status_code == 200
    data = response.json()
    assert data["datasets"] == ["dataset1", "dataset2"]
    mock_bigquery_client.list_datasets.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_bigquery_tables(mock_bigquery_client) -> None:
    response = client.get("/api/tools/bigquery/datasets/d1/tables?project_id=test-proj")
    assert response.status_code == 200
    data = response.json()
    assert data["tables"] == ["table1", "table2"]
    mock_bigquery_client.list_tables.assert_awaited_once_with("d1")


@pytest.mark.asyncio
async def test_get_bigquery_table_schema(mock_bigquery_client) -> None:
    response = client.get(
        "/api/tools/bigquery/datasets/d1/tables/t1/schema?project_id=test-proj"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["schema"]) == 2
    assert data["schema"][0]["name"] == "col1"
    mock_bigquery_client.get_table_schema.assert_awaited_once_with("d1", "t1")
