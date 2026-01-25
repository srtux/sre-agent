"""
Goal: Verify the tools router correctly discovers and describes available agent tools.
Patterns: Tool Registry Mocking, Schema Metadata Verification.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from server import app

client = TestClient(app)


@pytest.fixture
def mock_session_manager():
    with patch("sre_agent.api.routers.sessions.get_session_service") as mock:
        manager = AsyncMock()
        mock.return_value = manager
        yield manager


@pytest.mark.asyncio
async def test_create_session(mock_session_manager):
    mock_session = MagicMock()
    mock_session.id = "s1"
    mock_session.state = {"title": "Test Session"}
    mock_session_manager.create_session.return_value = mock_session

    response = client.post(
        "/api/sessions",
        json={"project_id": "p1", "title": "Test Session", "user_id": "u1"},
    )
    assert response.status_code == 200
    assert response.json()["id"] == "s1"
    mock_session_manager.create_session.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_sessions(mock_session_manager):
    s1 = MagicMock()
    s1.to_dict.return_value = {"id": "s1"}
    mock_session_manager.list_sessions.return_value = [s1]

    response = client.get("/api/sessions?user_id=u1")
    assert response.status_code == 200
    assert len(response.json()["sessions"]) == 1
    mock_session_manager.list_sessions.assert_awaited_once_with(user_id="u1")


@pytest.mark.asyncio
async def test_get_session(mock_session_manager):
    s1 = MagicMock()
    s1.id = "s1"
    s1.state = {}
    s1.events = []
    s1.last_update_time = "now"
    mock_session_manager.get_session.return_value = s1

    response = client.get("/api/sessions/s1")
    assert response.status_code == 200
    assert response.json()["id"] == "s1"


@pytest.mark.asyncio
async def test_get_session_not_found(mock_session_manager):
    mock_session_manager.get_session.return_value = None
    response = client.get("/api/sessions/unknown")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_session(mock_session_manager):
    mock_session_manager.delete_session.return_value = True
    response = client.delete("/api/sessions/s1")
    assert response.status_code == 200
    assert response.json()["message"] == "Session deleted"


@pytest.mark.asyncio
async def test_update_session(mock_session_manager):
    s1 = MagicMock()
    mock_session_manager.get_session.return_value = s1

    response = client.patch("/api/sessions/s1", json={"title": "New Title"})
    assert response.status_code == 200
    mock_session_manager.update_session_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_session_history(mock_session_manager):
    s1 = MagicMock()
    s1.events = []
    mock_session_manager.get_session.return_value = s1

    response = client.get("/api/sessions/s1/history")
    assert response.status_code == 200
    assert "messages" in response.json()
