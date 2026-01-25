"""Tests for LocalMemoryService."""

import os

import pytest

from sre_agent.memory.local import LocalMemoryService

DB_PATH = "test_memory.db"


@pytest.fixture
def local_memory():
    """Create a fresh local memory service."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    service = LocalMemoryService(db_path=DB_PATH)
    yield service

    # Cleanup
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)


@pytest.mark.asyncio
async def test_save_and_retrieve(local_memory):
    """Test saving and retrieving memories."""
    # Save generic memory
    mid = await local_memory.save_memory(
        session_id="sess_1",
        memory_content="CPU usage high",
        metadata={"user_id": "user_a", "confidence": "high"},
    )
    assert mid is not None

    # Retrieve
    results = await local_memory.search_memory(query="CPU")
    assert len(results) == 1
    assert results[0].content == "CPU usage high"
    assert results[0].metadata["user_id"] == "user_a"


@pytest.mark.asyncio
async def test_missing_user_id_error(local_memory):
    """Test that saving without user_id raises error."""
    with pytest.raises(PermissionError):
        await local_memory.save_memory(
            session_id="sess_1",
            memory_content="Should fail",
            metadata={"tool": "test"},  # Missing user_id
        )


@pytest.mark.asyncio
async def test_persistence(local_memory):
    """Test that data persists across service instances."""
    await local_memory.save_memory(
        session_id="sess_1",
        memory_content="Persistent Data",
        metadata={"user_id": "user_a"},
    )

    # Re-initialize service pointing to same DB
    new_service = LocalMemoryService(db_path=DB_PATH)
    results = await new_service.search_memory(query="Persistent")

    assert len(results) == 1
    assert results[0].content == "Persistent Data"


@pytest.mark.asyncio
async def test_search_limit(local_memory):
    """Test search limits."""
    for i in range(10):
        await local_memory.save_memory(
            session_id=f"sess_{i}",
            memory_content=f"Log entry {i}",
            metadata={"user_id": "user_a"},
        )

    results = await local_memory.search_memory(query="Log", limit=3)
    assert len(results) <= 6  # It returns limit * 2 internally
    # Wait, the local service returns Broad results.
    # The actual filtering happens in Manager.
    # But let's check what search_memory returns.
    # It executes LIMIT ? with limit * 2.
    # So if limit=3, it returns 6.

    # Let's verify exact count returned by service
    assert len(results) == 6
