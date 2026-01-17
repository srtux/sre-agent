"""E2E tests for the API endpoints."""

from fastapi.testclient import TestClient

from server import app

client = TestClient(app)


def test_session_lifecycle():
    """Test the full lifecycle of a session via API."""

    # 1. Create Session
    response = client.post(
        "/api/sessions",
        json={"title": "E2E Test Session", "project_id": "test-project"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    session_id = data["id"]
    assert data["state"]["title"] == "E2E Test Session"

    # 2. Get Session
    response = client.get(f"/api/sessions/{session_id}")
    assert response.status_code == 200
    assert response.json()["id"] == session_id

    # 3. List Sessions
    response = client.get("/api/sessions")
    assert response.status_code == 200
    sessions = response.json()["sessions"]
    assert any(s["id"] == session_id for s in sessions)

    # 4. Delete Session
    response = client.delete(f"/api/sessions/{session_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "Session deleted"

    # 5. Verify Deletion
    response = client.get(f"/api/sessions/{session_id}")
    # Depending on implementation, might be 404 or return None/Empty
    # server.py implementation: returns 404 if not found
    assert response.status_code == 404
