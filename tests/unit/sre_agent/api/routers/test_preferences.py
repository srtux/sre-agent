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


# ========== Starred Projects ==========


@pytest.mark.asyncio
async def test_get_starred_projects(mock_storage):
    mock_storage.get_starred_projects.return_value = [
        {"project_id": "p1", "display_name": "P1"}
    ]
    response = client.get("/api/preferences/projects/starred")
    assert response.status_code == 200
    assert response.json() == {
        "projects": [{"project_id": "p1", "display_name": "P1"}]
    }


@pytest.mark.asyncio
async def test_get_starred_projects_empty(mock_storage):
    mock_storage.get_starred_projects.return_value = None
    response = client.get("/api/preferences/projects/starred")
    assert response.status_code == 200
    assert response.json() == {"projects": []}


@pytest.mark.asyncio
async def test_set_starred_projects(mock_storage):
    projects = [{"project_id": "p1", "display_name": "P1"}]
    response = client.post(
        "/api/preferences/projects/starred",
        json={"projects": projects, "user_id": "test-user"},
    )
    assert response.status_code == 200
    assert response.json() == {"success": True}
    mock_storage.set_starred_projects.assert_called_once_with(projects, "test-user")


@pytest.mark.asyncio
async def test_toggle_star_add(mock_storage):
    mock_storage.get_starred_projects.return_value = []
    response = client.post(
        "/api/preferences/projects/starred/toggle",
        json={
            "project_id": "new-proj",
            "display_name": "New Project",
            "starred": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["starred"] is True
    assert any(p["project_id"] == "new-proj" for p in data["projects"])


@pytest.mark.asyncio
async def test_toggle_star_remove(mock_storage):
    mock_storage.get_starred_projects.return_value = [
        {"project_id": "old-proj", "display_name": "Old"}
    ]
    response = client.post(
        "/api/preferences/projects/starred/toggle",
        json={"project_id": "old-proj", "starred": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["starred"] is False
    assert not any(p["project_id"] == "old-proj" for p in data["projects"])


@pytest.mark.asyncio
async def test_toggle_star_idempotent_add(mock_storage):
    """Adding a project that is already starred should not duplicate it."""
    mock_storage.get_starred_projects.return_value = [
        {"project_id": "p1", "display_name": "P1"}
    ]
    response = client.post(
        "/api/preferences/projects/starred/toggle",
        json={"project_id": "p1", "display_name": "P1", "starred": True},
    )
    assert response.status_code == 200
    data = response.json()
    count = sum(1 for p in data["projects"] if p["project_id"] == "p1")
    assert count == 1


@pytest.mark.asyncio
async def test_preferences_uses_auth_user_id(mock_storage):
    """When an authenticated user is present, preferences use their ID."""
    mock_storage.get_selected_project.return_value = "auth-proj"
    with patch("sre_agent.api.routers.preferences.get_current_user_id") as mock_uid:
        mock_uid.return_value = "alice@example.com"
        response = client.get("/api/preferences/project")
    assert response.status_code == 200
    mock_storage.get_selected_project.assert_called_once_with("alice@example.com")
