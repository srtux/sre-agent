"""
Goal: Verify the permissions router correctly reports and validates user project access.
Patterns: Project Service Mocking, IAM Permission Simulation.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from server import app

client = TestClient(app)


@pytest.fixture
def mock_storage():
    with patch("sre_agent.api.routers.preferences.get_storage_service") as mock:
        storage = AsyncMock()
        mock.return_value = storage
        yield storage


@pytest.mark.asyncio
async def test_get_selected_project(mock_storage):
    mock_storage.get_selected_project.return_value = "test-proj"
    response = client.get("/api/preferences/project?user_id=test-user")
    assert response.status_code == 200
    assert response.json() == {"project_id": "test-proj"}
    mock_storage.get_selected_project.assert_called_once_with("test-user")


@pytest.mark.asyncio
async def test_get_selected_project_error(mock_storage):
    mock_storage.get_selected_project.side_effect = Exception("Storage error")
    response = client.get("/api/preferences/project")
    assert response.status_code == 200
    assert response.json() == {"project_id": None}


@pytest.mark.asyncio
async def test_set_selected_project(mock_storage):
    response = client.post(
        "/api/preferences/project",
        json={"project_id": "new-proj", "user_id": "test-user"},
    )
    assert response.status_code == 200
    assert response.json() == {"success": True, "project_id": "new-proj"}
    mock_storage.set_selected_project.assert_called_once_with("new-proj", "test-user")


@pytest.mark.asyncio
async def test_set_selected_project_error(mock_storage):
    mock_storage.set_selected_project.side_effect = Exception("Storage error")
    response = client.post("/api/preferences/project", json={"project_id": "new-proj"})
    assert response.status_code == 500
    assert "Storage error" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_tool_preferences(mock_storage):
    mock_storage.get_tool_config.return_value = {"tool1": True}
    response = client.get("/api/preferences/tools")
    assert response.status_code == 200
    assert response.json() == {"enabled_tools": {"tool1": True}}


@pytest.mark.asyncio
async def test_get_tool_preferences_error(mock_storage):
    mock_storage.get_tool_config.side_effect = Exception("Storage error")
    response = client.get("/api/preferences/tools")
    assert response.status_code == 200
    assert response.json() == {"enabled_tools": {}}


@pytest.mark.asyncio
async def test_set_tool_preferences(mock_storage):
    response = client.post(
        "/api/preferences/tools",
        json={"enabled_tools": {"tool1": False}, "user_id": "test-user"},
    )
    assert response.status_code == 200
    assert response.json() == {"success": True}
    mock_storage.set_tool_config.assert_called_once_with({"tool1": False}, "test-user")


@pytest.mark.asyncio
async def test_get_recent_projects(mock_storage):
    mock_storage.get_recent_projects.return_value = [{"id": "p1", "name": "P1"}]
    response = client.get("/api/preferences/projects/recent")
    assert response.status_code == 200
    assert response.json() == {"projects": [{"id": "p1", "name": "P1"}]}


@pytest.mark.asyncio
async def test_set_recent_projects(mock_storage):
    projects = [{"id": "p1", "name": "P1"}]
    response = client.post(
        "/api/preferences/projects/recent",
        json={"projects": projects, "user_id": "test-user"},
    )
    assert response.status_code == 200
    assert response.json() == {"success": True}
    mock_storage.set_recent_projects.assert_called_once_with(projects, "test-user")
