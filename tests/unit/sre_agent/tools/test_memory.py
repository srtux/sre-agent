"""
Goal: Verify Memory tools correctly wrap results in BaseToolResponse (normalized as dict by @adk_tool).
Patterns: Mocking, BaseToolResponse Validation.
"""

from unittest.mock import AsyncMock, patch

import pytest

from sre_agent.schema import ToolStatus
from sre_agent.tools.memory import add_finding_to_memory, search_memory


@pytest.fixture
def mock_memory_manager():
    """Mock memory manager."""
    with patch("sre_agent.tools.memory.get_memory_manager") as mock:
        yield mock


@pytest.mark.asyncio
async def test_search_memory_returns_basetool_response(mock_memory_manager):
    """Verify search_memory wraps results correctly."""
    mock_manager = AsyncMock()
    mock_manager.get_relevant_findings.return_value = []
    mock_memory_manager.return_value = mock_manager

    response = await search_memory(query="test", tool_context=None)

    # @adk_tool normalizes Pydantic models to dicts
    assert isinstance(response, dict)
    assert response["status"] == ToolStatus.SUCCESS
    assert response["result"] == []


@pytest.mark.asyncio
async def test_add_finding_to_memory_returns_basetool_response(mock_memory_manager):
    """Verify add_finding_to_memory wraps results correctly."""
    mock_manager = AsyncMock()
    mock_memory_manager.return_value = mock_manager

    response = await add_finding_to_memory(
        description="test", source_tool="test", tool_context=None
    )

    assert isinstance(response, dict)
    assert response["status"] == ToolStatus.SUCCESS
    assert "Finding added" in response["result"]
