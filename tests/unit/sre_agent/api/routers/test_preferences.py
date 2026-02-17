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
    assert response.json() == {"projects": [{"project_id": "p1", "display_name": "P1"}]}


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


# ========== Recent Queries ==========


@pytest.mark.asyncio
async def test_get_recent_queries(mock_storage):
    mock_storage.get_recent_queries.return_value = [
        {"query": "severity>=ERROR", "panel_type": "logs", "language": "LOG FILTER"}
    ]
    response = client.get("/api/preferences/queries/recent?panel_type=logs")
    assert response.status_code == 200
    data = response.json()
    assert len(data["queries"]) == 1
    assert data["queries"][0]["query"] == "severity>=ERROR"
    mock_storage.get_recent_queries.assert_called_once()


@pytest.mark.asyncio
async def test_get_recent_queries_empty(mock_storage):
    mock_storage.get_recent_queries.return_value = []
    response = client.get("/api/preferences/queries/recent")
    assert response.status_code == 200
    assert response.json() == {"queries": []}


@pytest.mark.asyncio
async def test_get_recent_queries_error(mock_storage):
    mock_storage.get_recent_queries.side_effect = Exception("Storage error")
    response = client.get("/api/preferences/queries/recent")
    assert response.status_code == 200
    assert response.json() == {"queries": []}


@pytest.mark.asyncio
async def test_add_recent_query(mock_storage):
    mock_storage.add_recent_query.return_value = [
        {"query": "severity>=ERROR", "panel_type": "logs"}
    ]
    response = client.post(
        "/api/preferences/queries/recent",
        json={
            "query": "severity>=ERROR",
            "panel_type": "logs",
            "language": "LOG FILTER",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["queries"]) == 1
    mock_storage.add_recent_query.assert_called_once()
    call_entry = mock_storage.add_recent_query.call_args[0][0]
    assert call_entry["query"] == "severity>=ERROR"
    assert call_entry["panel_type"] == "logs"
    assert "timestamp" in call_entry


@pytest.mark.asyncio
async def test_add_recent_query_error(mock_storage):
    mock_storage.add_recent_query.side_effect = Exception("Boom")
    response = client.post(
        "/api/preferences/queries/recent",
        json={"query": "SELECT 1", "panel_type": "analytics"},
    )
    assert response.status_code == 500


# ========== Saved Queries ==========


@pytest.mark.asyncio
async def test_get_saved_queries(mock_storage):
    mock_storage.get_saved_queries.return_value = [
        {
            "id": "abc",
            "name": "My Query",
            "query": "SELECT 1",
            "panel_type": "analytics",
        }
    ]
    response = client.get("/api/preferences/queries/saved?panel_type=analytics")
    assert response.status_code == 200
    data = response.json()
    assert len(data["queries"]) == 1
    assert data["queries"][0]["name"] == "My Query"


@pytest.mark.asyncio
async def test_get_saved_queries_empty(mock_storage):
    mock_storage.get_saved_queries.return_value = []
    response = client.get("/api/preferences/queries/saved")
    assert response.status_code == 200
    assert response.json() == {"queries": []}


@pytest.mark.asyncio
async def test_save_query(mock_storage):
    mock_storage.add_saved_query.return_value = []
    response = client.post(
        "/api/preferences/queries/saved",
        json={
            "name": "Error logs",
            "query": "severity>=ERROR",
            "panel_type": "logs",
            "language": "LOG FILTER",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["query"]["name"] == "Error logs"
    assert "id" in data["query"]
    assert "created_at" in data["query"]


@pytest.mark.asyncio
async def test_save_query_error(mock_storage):
    mock_storage.add_saved_query.side_effect = Exception("Boom")
    response = client.post(
        "/api/preferences/queries/saved",
        json={"name": "Q", "query": "SELECT 1", "panel_type": "analytics"},
    )
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_update_saved_query(mock_storage):
    mock_storage.update_saved_query.return_value = [
        {"id": "abc", "name": "Renamed", "query": "SELECT 1"}
    ]
    response = client.put(
        "/api/preferences/queries/saved/abc",
        json={"name": "Renamed"},
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


@pytest.mark.asyncio
async def test_update_saved_query_error(mock_storage):
    mock_storage.update_saved_query.side_effect = Exception("Boom")
    response = client.put(
        "/api/preferences/queries/saved/abc",
        json={"name": "Renamed"},
    )
    assert response.status_code == 500


@pytest.mark.asyncio
async def test_delete_saved_query(mock_storage):
    mock_storage.delete_saved_query.return_value = []
    response = client.delete("/api/preferences/queries/saved/abc")
    assert response.status_code == 200
    assert response.json()["success"] is True
    mock_storage.delete_saved_query.assert_called_once_with("abc", "default")


@pytest.mark.asyncio
async def test_delete_saved_query_error(mock_storage):
    mock_storage.delete_saved_query.side_effect = Exception("Boom")
    response = client.delete("/api/preferences/queries/saved/abc")
    assert response.status_code == 500
