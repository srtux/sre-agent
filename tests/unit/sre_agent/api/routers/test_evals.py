"""Tests for Online GenAI Evaluation configuration endpoints.

Tests the evals router (sre_agent/api/routers/evals.py) including:
- CRUD operations for eval configs
- Guest mode behavior
- Error handling (storage failures -> UserFacingError)
- Validation (sampling_rate bounds)
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from server import app

client = TestClient(app)


@pytest.fixture
def mock_storage():
    """Mock the storage service with an AsyncMock _backend."""
    with patch("sre_agent.api.routers.evals.get_storage_service") as mock:
        storage = MagicMock()
        backend = AsyncMock()
        storage._backend = backend
        mock.return_value = storage
        yield backend


@pytest.fixture
def mock_guest_mode():
    """Mock guest mode to return True."""
    with patch("sre_agent.api.routers.evals.is_guest_mode", return_value=True):
        yield


@pytest.fixture
def mock_no_guest():
    """Mock guest mode to return False (normal mode)."""
    with patch("sre_agent.api.routers.evals.is_guest_mode", return_value=False):
        yield


# ========== LIST configs ==========


@pytest.mark.asyncio
async def test_list_eval_configs_empty(mock_storage, mock_no_guest):
    """List configs when storage is empty returns empty list."""
    mock_storage.get.return_value = None
    response = client.get("/api/v1/evals/config")
    assert response.status_code == 200
    assert response.json() == {"configs": []}
    mock_storage.get.assert_called_once_with("eval_configs")


@pytest.mark.asyncio
async def test_list_eval_configs_empty_dict(mock_storage, mock_no_guest):
    """List configs when storage returns empty dict returns empty list."""
    mock_storage.get.return_value = {}
    response = client.get("/api/v1/evals/config")
    assert response.status_code == 200
    assert response.json() == {"configs": []}


@pytest.mark.asyncio
async def test_list_eval_configs_with_data(mock_storage, mock_no_guest):
    """List configs with data returns all configs."""
    stored = {
        "agent-a": {
            "agent_name": "agent-a",
            "is_enabled": True,
            "sampling_rate": 0.5,
            "metrics": ["coherence"],
            "last_eval_timestamp": None,
        },
        "agent-b": {
            "agent_name": "agent-b",
            "is_enabled": False,
            "sampling_rate": 1.0,
            "metrics": [],
            "last_eval_timestamp": None,
        },
    }
    mock_storage.get.return_value = stored
    response = client.get("/api/v1/evals/config")
    assert response.status_code == 200
    data = response.json()
    assert len(data["configs"]) == 2
    names = {c["agent_name"] for c in data["configs"]}
    assert names == {"agent-a", "agent-b"}


@pytest.mark.asyncio
async def test_list_eval_configs_guest_mode(mock_storage, mock_guest_mode):
    """Guest mode returns empty configs list without hitting storage."""
    response = client.get("/api/v1/evals/config")
    assert response.status_code == 200
    assert response.json() == {"configs": []}
    mock_storage.get.assert_not_called()


@pytest.mark.asyncio
async def test_list_eval_configs_storage_error(mock_storage, mock_no_guest):
    """Storage failure raises UserFacingError (500)."""
    mock_storage.get.side_effect = RuntimeError("disk full")
    response = client.get("/api/v1/evals/config")
    assert response.status_code == 500
    assert "disk full" in response.json()["detail"]


# ========== UPSERT config ==========


@pytest.mark.asyncio
async def test_upsert_new_config(mock_storage, mock_no_guest):
    """Creating a new config stores and returns it."""
    mock_storage.get.return_value = {}
    response = client.post(
        "/api/v1/evals/config/my-agent",
        json={
            "is_enabled": True,
            "sampling_rate": 0.8,
            "metrics": ["coherence", "fluency"],
        },
    )
    assert response.status_code == 200
    cfg = response.json()["config"]
    assert cfg["agent_name"] == "my-agent"
    assert cfg["is_enabled"] is True
    assert cfg["sampling_rate"] == 0.8
    assert cfg["metrics"] == ["coherence", "fluency"]
    assert cfg["last_eval_timestamp"] is None
    mock_storage.set.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_existing_config_preserves_timestamp(mock_storage, mock_no_guest):
    """Upserting an existing config preserves the last_eval_timestamp."""
    ts = "2026-02-20T12:00:00Z"
    mock_storage.get.return_value = {
        "my-agent": {
            "agent_name": "my-agent",
            "is_enabled": False,
            "sampling_rate": 1.0,
            "metrics": [],
            "last_eval_timestamp": ts,
        }
    }
    response = client.post(
        "/api/v1/evals/config/my-agent",
        json={
            "is_enabled": True,
            "sampling_rate": 0.5,
            "metrics": ["coherence"],
        },
    )
    assert response.status_code == 200
    cfg = response.json()["config"]
    assert cfg["is_enabled"] is True
    assert cfg["sampling_rate"] == 0.5
    assert cfg["last_eval_timestamp"] is not None
    # The original timestamp should be preserved
    assert "2026-02-20" in cfg["last_eval_timestamp"]
    mock_storage.set.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_config_guest_mode(mock_storage, mock_guest_mode):
    """Guest mode returns synthetic config without storage writes."""
    response = client.post(
        "/api/v1/evals/config/my-agent",
        json={
            "is_enabled": True,
            "sampling_rate": 0.5,
            "metrics": ["fluency"],
        },
    )
    assert response.status_code == 200
    cfg = response.json()["config"]
    assert cfg["agent_name"] == "my-agent"
    assert cfg["is_enabled"] is True
    mock_storage.get.assert_not_called()
    mock_storage.set.assert_not_called()


@pytest.mark.asyncio
async def test_upsert_config_storage_error(mock_storage, mock_no_guest):
    """Storage failure on upsert raises UserFacingError (500)."""
    mock_storage.get.side_effect = RuntimeError("connection lost")
    response = client.post(
        "/api/v1/evals/config/my-agent",
        json={"is_enabled": True},
    )
    assert response.status_code == 500
    assert "connection lost" in response.json()["detail"]


# ========== Validation ==========


@pytest.mark.asyncio
async def test_upsert_config_sampling_rate_too_high(mock_no_guest):
    """sampling_rate > 1.0 is rejected by Pydantic validation."""
    response = client.post(
        "/api/v1/evals/config/my-agent",
        json={"is_enabled": True, "sampling_rate": 1.5},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upsert_config_sampling_rate_too_low(mock_no_guest):
    """sampling_rate < 0.0 is rejected by Pydantic validation."""
    response = client.post(
        "/api/v1/evals/config/my-agent",
        json={"is_enabled": True, "sampling_rate": -0.1},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upsert_config_sampling_rate_boundary_zero(mock_storage, mock_no_guest):
    """sampling_rate = 0.0 is accepted (boundary)."""
    mock_storage.get.return_value = {}
    response = client.post(
        "/api/v1/evals/config/my-agent",
        json={"is_enabled": True, "sampling_rate": 0.0},
    )
    assert response.status_code == 200
    assert response.json()["config"]["sampling_rate"] == 0.0


@pytest.mark.asyncio
async def test_upsert_config_sampling_rate_boundary_one(mock_storage, mock_no_guest):
    """sampling_rate = 1.0 is accepted (boundary)."""
    mock_storage.get.return_value = {}
    response = client.post(
        "/api/v1/evals/config/my-agent",
        json={"is_enabled": True, "sampling_rate": 1.0},
    )
    assert response.status_code == 200
    assert response.json()["config"]["sampling_rate"] == 1.0


@pytest.mark.asyncio
async def test_upsert_config_extra_fields_rejected(mock_no_guest):
    """Extra fields are rejected by Pydantic extra=forbid."""
    response = client.post(
        "/api/v1/evals/config/my-agent",
        json={"is_enabled": True, "bogus_field": "nope"},
    )
    assert response.status_code == 422


# ========== GET single config ==========


@pytest.mark.asyncio
async def test_get_existing_config(mock_storage, mock_no_guest):
    """Get an existing config returns it."""
    stored_config = {
        "agent_name": "my-agent",
        "is_enabled": True,
        "sampling_rate": 0.5,
        "metrics": ["coherence"],
        "last_eval_timestamp": None,
    }
    mock_storage.get.return_value = {"my-agent": stored_config}
    response = client.get("/api/v1/evals/config/my-agent")
    assert response.status_code == 200
    assert response.json()["config"] == stored_config


@pytest.mark.asyncio
async def test_get_nonexistent_config(mock_storage, mock_no_guest):
    """Get a non-existent config returns 404."""
    mock_storage.get.return_value = {}
    response = client.get("/api/v1/evals/config/missing-agent")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_config_guest_mode(mock_storage, mock_guest_mode):
    """Guest mode returns a default config without hitting storage."""
    response = client.get("/api/v1/evals/config/any-agent")
    assert response.status_code == 200
    cfg = response.json()["config"]
    assert cfg["agent_name"] == "any-agent"
    assert cfg["is_enabled"] is False
    mock_storage.get.assert_not_called()


@pytest.mark.asyncio
async def test_get_config_storage_error(mock_storage, mock_no_guest):
    """Storage failure on get raises UserFacingError (500)."""
    mock_storage.get.side_effect = RuntimeError("db unavailable")
    response = client.get("/api/v1/evals/config/my-agent")
    assert response.status_code == 500
    assert "db unavailable" in response.json()["detail"]


# ========== DELETE config ==========


@pytest.mark.asyncio
async def test_delete_existing_config(mock_storage, mock_no_guest):
    """Deleting an existing config returns 204 and removes it from storage."""
    mock_storage.get.return_value = {
        "my-agent": {
            "agent_name": "my-agent",
            "is_enabled": True,
            "sampling_rate": 1.0,
            "metrics": [],
            "last_eval_timestamp": None,
        }
    }
    response = client.delete("/api/v1/evals/config/my-agent")
    assert response.status_code == 204
    # Verify config was removed before saving
    saved_arg = mock_storage.set.call_args[0][1]
    assert "my-agent" not in saved_arg


@pytest.mark.asyncio
async def test_delete_nonexistent_config(mock_storage, mock_no_guest):
    """Deleting a non-existent config is idempotent (returns 204)."""
    mock_storage.get.return_value = {}
    response = client.delete("/api/v1/evals/config/missing-agent")
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_config_guest_mode(mock_storage, mock_guest_mode):
    """Guest mode delete returns 204 without hitting storage."""
    response = client.delete("/api/v1/evals/config/any-agent")
    assert response.status_code == 204
    mock_storage.get.assert_not_called()
    mock_storage.set.assert_not_called()


@pytest.mark.asyncio
async def test_delete_config_storage_error(mock_storage, mock_no_guest):
    """Storage failure on delete raises UserFacingError (500)."""
    mock_storage.get.side_effect = RuntimeError("disk error")
    response = client.delete("/api/v1/evals/config/my-agent")
    assert response.status_code == 500
    assert "disk error" in response.json()["detail"]


# ========== Edge cases ==========


@pytest.mark.asyncio
async def test_list_configs_non_dict_stored_value(mock_storage, mock_no_guest):
    """If storage returns a non-dict value, treat as empty."""
    mock_storage.get.return_value = "not-a-dict"
    response = client.get("/api/v1/evals/config")
    assert response.status_code == 200
    assert response.json() == {"configs": []}


@pytest.mark.asyncio
async def test_upsert_config_default_sampling_rate(mock_storage, mock_no_guest):
    """Omitting sampling_rate defaults to 1.0."""
    mock_storage.get.return_value = {}
    response = client.post(
        "/api/v1/evals/config/my-agent",
        json={"is_enabled": False},
    )
    assert response.status_code == 200
    assert response.json()["config"]["sampling_rate"] == 1.0


@pytest.mark.asyncio
async def test_upsert_config_default_metrics(mock_storage, mock_no_guest):
    """Omitting metrics defaults to empty list."""
    mock_storage.get.return_value = {}
    response = client.post(
        "/api/v1/evals/config/my-agent",
        json={"is_enabled": True},
    )
    assert response.status_code == 200
    assert response.json()["config"]["metrics"] == []
