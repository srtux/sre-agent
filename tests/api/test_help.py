import pytest
from fastapi.testclient import TestClient

from sre_agent.api.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_get_help_manifest(client):
    response = client.get("/api/help/manifest")
    assert response.status_code == 200
    manifest = response.json()
    assert isinstance(manifest, list)
    assert len(manifest) > 0
    # Check for core fields in the first item
    first_item = manifest[0]
    assert "id" in first_item
    assert "title" in first_item
    assert "content_file" in first_item


def test_get_help_content_success(client):
    # Use 'traces' as it's a known ID from our manifest
    response = client.get("/api/help/content/traces")
    assert response.status_code == 200
    assert "### Getting Started with Traces" in response.text


def test_get_help_content_not_found(client):
    response = client.get("/api/help/content/non_existent_topic_12345")
    assert response.status_code == 404


def test_get_help_content_traversal_protection(client):
    # Try suspicious content ID that should be rejected by our guard
    # We use something that won't be normalized by the TestClient's URL handling
    response = client.get("/api/help/content/suspicious..path")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid content ID"


def test_get_help_content_council(client):
    """Council help content should be accessible and contain key information."""
    response = client.get("/api/help/content/council")
    assert response.status_code == 200
    assert "### Council Investigation" in response.text
    assert "Fast" in response.text
    assert "Standard" in response.text
    assert "Debate" in response.text


def test_get_help_manifest_includes_council(client):
    """Manifest should include the council help topic."""
    response = client.get("/api/help/manifest")
    assert response.status_code == 200
    manifest = response.json()
    council_entries = [t for t in manifest if t["id"] == "council"]
    assert len(council_entries) == 1
    assert council_entries[0]["title"] == "Council Investigation"
    assert "Analysis" in council_entries[0]["categories"]


def test_get_help_content_sanitization(client):
    # Test that it handles dots safely if they aren't traversal
    # Actually our router currently rejects ANY / or \ or ..
    response = client.get("/api/help/content/traces.md")
    # If it ends with .md, the router handles it
    assert response.status_code == 200
    assert "### Getting Started with Traces" in response.text
