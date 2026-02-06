"""Unit tests for the tools router."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from server import app

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
    ):
        f_trace.return_value = json.dumps({"trace": "data"})
        l_projects.return_value = {"projects": []}
        l_logs.return_value = json.dumps({"entries": []})
        e_patterns.return_value = {"patterns": []}

        yield {
            "fetch_trace": f_trace,
            "list_gcp_projects": l_projects,
            "list_log_entries": l_logs,
            "extract_log_patterns": e_patterns,
        }


@pytest.mark.asyncio
async def test_get_trace(mock_tools):
    response = client.get("/api/tools/trace/abc?project_id=test-proj")
    assert response.status_code == 200
    assert response.json() == {"trace": "data"}
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
    from sre_agent.schema import BaseToolResponse, ToolStatus

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
    from sre_agent.schema import BaseToolResponse, ToolStatus

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
