import pytest
from fastapi.testclient import TestClient

from server import app

client = TestClient(app)


@pytest.mark.asyncio
async def test_session_renaming():
    """Test that we can create a session and then rename it via PATCH."""

    # 1. Create a session
    create_payload = {"user_id": "test-user", "title": "Original Title"}
    response = client.post("/api/sessions", json=create_payload)
    assert response.status_code == 200
    session_data = response.json()
    session_id = session_data["id"]
    assert session_data["state"]["title"] == "Original Title"

    # 2. Rename the session
    update_payload = {"title": "Updated Title"}
    # Must pass user_id so backend can find the session for this user
    response = client.patch(
        f"/api/sessions/{session_id}?user_id=test-user", json=update_payload
    )
    assert response.status_code == 200
    update_data = response.json()
    assert update_data["updates"]["title"] == "Updated Title"

    # 3. Verify persistence via get_session
    # Note: mocking might be needed if using real async services in a sync test client,
    # but TestClient usually handles FastAPI apps well if they don't depend on complex external event loops.
    # However, since ADKSessionManager might be using aiosqlite or similar, we might need to be careful.
    # The server.py uses `app` which initializes `ADKSessionManager`.

    response = client.get(f"/api/sessions/{session_id}?user_id=test-user")
    assert response.status_code == 200
    get_data = response.json()
    assert get_data["state"]["title"] == "Updated Title"

    # 4. Verify in list
    response = client.get("/api/sessions?user_id=test-user")
    assert response.status_code == 200
    list_data = response.json()
    sessions = list_data["sessions"]
    # Find our session
    my_session = next((s for s in sessions if s["id"] == session_id), None)
    assert my_session is not None
    assert my_session["title"] == "Updated Title"
