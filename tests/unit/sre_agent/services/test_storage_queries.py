"""Tests for StorageService recent/saved query methods."""

import pytest

from sre_agent.services.storage import StorageService


@pytest.fixture
def storage(tmp_path):
    """Create a StorageService backed by a temp file."""
    svc = StorageService.__new__(StorageService)
    from sre_agent.services.storage import FilePreferencesBackend

    svc._backend = FilePreferencesBackend(str(tmp_path / "prefs.json"))
    return svc


@pytest.mark.asyncio
async def test_recent_queries_empty(storage):
    result = await storage.get_recent_queries("user1")
    assert result == []


@pytest.mark.asyncio
async def test_add_recent_query(storage):
    entry = {"query": "severity>=ERROR", "panel_type": "logs", "language": "LOG FILTER"}
    result = await storage.add_recent_query(entry, "user1")
    assert len(result) == 1
    assert result[0]["query"] == "severity>=ERROR"


@pytest.mark.asyncio
async def test_recent_queries_dedup(storage):
    entry1 = {"query": "severity>=ERROR", "panel_type": "logs"}
    entry2 = {"query": "SELECT 1", "panel_type": "analytics"}
    entry3 = {"query": "severity>=ERROR", "panel_type": "logs"}

    await storage.add_recent_query(entry1, "user1")
    await storage.add_recent_query(entry2, "user1")
    result = await storage.add_recent_query(entry3, "user1")

    assert len(result) == 2
    # Most recent first
    assert result[0]["query"] == "severity>=ERROR"
    assert result[1]["query"] == "SELECT 1"


@pytest.mark.asyncio
async def test_recent_queries_panel_filter(storage):
    await storage.add_recent_query(
        {"query": "severity>=ERROR", "panel_type": "logs"}, "user1"
    )
    await storage.add_recent_query(
        {"query": "SELECT 1", "panel_type": "analytics"}, "user1"
    )

    logs_only = await storage.get_recent_queries("user1", panel_type="logs")
    assert len(logs_only) == 1
    assert logs_only[0]["panel_type"] == "logs"

    all_queries = await storage.get_recent_queries("user1")
    assert len(all_queries) == 2


@pytest.mark.asyncio
async def test_recent_queries_max_limit(storage):
    for i in range(storage.MAX_RECENT_QUERIES + 10):
        await storage.add_recent_query(
            {"query": f"query_{i}", "panel_type": "logs"}, "user1"
        )
    result = await storage.get_recent_queries("user1")
    assert len(result) == storage.MAX_RECENT_QUERIES


@pytest.mark.asyncio
async def test_saved_queries_empty(storage):
    result = await storage.get_saved_queries("user1")
    assert result == []


@pytest.mark.asyncio
async def test_add_saved_query(storage):
    entry = {
        "id": "q1",
        "name": "My Query",
        "query": "SELECT 1",
        "panel_type": "analytics",
    }
    result = await storage.add_saved_query(entry, "user1")
    assert len(result) == 1
    assert result[0]["name"] == "My Query"


@pytest.mark.asyncio
async def test_saved_queries_panel_filter(storage):
    await storage.add_saved_query(
        {"id": "q1", "name": "Log Q", "query": "x", "panel_type": "logs"}, "user1"
    )
    await storage.add_saved_query(
        {"id": "q2", "name": "SQL Q", "query": "y", "panel_type": "analytics"}, "user1"
    )

    logs_only = await storage.get_saved_queries("user1", panel_type="logs")
    assert len(logs_only) == 1
    assert logs_only[0]["name"] == "Log Q"


@pytest.mark.asyncio
async def test_update_saved_query(storage):
    await storage.add_saved_query(
        {"id": "q1", "name": "Old", "query": "SELECT 1", "panel_type": "analytics"},
        "user1",
    )
    result = await storage.update_saved_query("q1", {"name": "New"}, "user1")
    assert result[0]["name"] == "New"
    assert result[0]["query"] == "SELECT 1"


@pytest.mark.asyncio
async def test_delete_saved_query(storage):
    await storage.add_saved_query(
        {"id": "q1", "name": "Q1", "query": "x", "panel_type": "logs"}, "user1"
    )
    await storage.add_saved_query(
        {"id": "q2", "name": "Q2", "query": "y", "panel_type": "logs"}, "user1"
    )
    result = await storage.delete_saved_query("q1", "user1")
    assert len(result) == 1
    assert result[0]["id"] == "q2"


@pytest.mark.asyncio
async def test_delete_saved_query_nonexistent(storage):
    await storage.add_saved_query(
        {"id": "q1", "name": "Q1", "query": "x", "panel_type": "logs"}, "user1"
    )
    result = await storage.delete_saved_query("nonexistent", "user1")
    assert len(result) == 1
