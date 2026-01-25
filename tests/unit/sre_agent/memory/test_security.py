"""
Goal: Verify MemoryManager enforces strict user isolation and privacy hardening.
Patterns: User Identity Propagation, Metadata Filtering, Anonymous Access Safety.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from sre_agent.memory.manager import MemoryManager


@pytest.fixture
def mock_memory_service():
    """Mock the Vertex AI Memory Bank service."""
    service = AsyncMock()
    # Mock search to return everything, forcing the manager to filter
    service.search_memory.return_value = []
    return service


@pytest.fixture
def memory_manager(mock_memory_service):
    """Create a memory manager with mocked service."""
    # Patch the service creation
    manager = MemoryManager(project_id="test-project")
    manager.memory_service = mock_memory_service
    return manager


@pytest.mark.asyncio
async def test_memory_user_isolation(memory_manager, mock_memory_service):
    """Test that findings are filtered by user_id."""
    # Setup mocked search results
    # We simulate the backend returning results from multiple users
    # to verify the manager filters them out.
    mock_memory_service.search_memory.return_value = [
        MagicMock(
            content="Finding A",
            metadata={
                "tool": "test",
                "confidence": "medium",
                "timestamp": "2024-01-01T00:00:00Z",
                "user_id": "user_a@example.com",
            },
        ),
        MagicMock(
            content="Finding B",
            metadata={
                "tool": "test",
                "confidence": "medium",
                "timestamp": "2024-01-01T00:00:00Z",
                "user_id": "user_b@example.com",
            },
        ),
    ]

    # 1. Search as User A
    results_a = await memory_manager.get_relevant_findings(
        query="Finding", user_id="user_a@example.com"
    )
    # DEBUG: Check if search_memory was actually called
    mock_memory_service.search_memory.assert_called()

    assert len(results_a) == 1, f"Expected 1 finding for User A, got {len(results_a)}"
    assert results_a[0].description == "Finding A"

    # 2. Search as User B
    results_b = await memory_manager.get_relevant_findings(
        query="Finding", user_id="user_b@example.com"
    )
    assert len(results_b) == 1
    assert results_b[0].description == "Finding B"

    # 3. Search as Anonymous (should match "anonymous" findings, or nothing if none exist)
    results_anon = await memory_manager.get_relevant_findings(
        query="Finding", user_id=None
    )
    # Since all mocked findings have user_ids, anonymous search should find NOTHING
    assert len(results_anon) == 0


@pytest.mark.asyncio
async def test_add_finding_stores_user_id(memory_manager, mock_memory_service):
    """Verify that add_finding calls save_memory with user_id metadata."""
    await memory_manager.add_finding(
        description="My Secret Info",
        source_tool="test",
        session_id="session_1",
        user_id="user_a@example.com",
    )

    mock_memory_service.save_memory.assert_called_once()
    call_args = mock_memory_service.save_memory.call_args
    metadata = call_args.kwargs["metadata"]
    assert metadata["user_id"] == "user_a@example.com"
