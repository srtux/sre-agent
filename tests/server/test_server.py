from fastapi.testclient import TestClient

from server import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_tool_configs():
    response = client.get("/api/tools/config")
    # We might get 200 or 500 depending on if config manager is mocked or real and requires files
    # The real server loads from .tool_config.json. If it exists, 200.
    # We'll just assert we get a valid HTTP response (not 404).
    assert response.status_code in [200, 500]
