"""
Goal: Verify MemoryManager correctly orchestrates between Vertex AI and Local fallbacks.
Patterns: Mocking, Dependency Injection, Graceful Degradation.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sre_agent.memory.manager import MemoryManager
from sre_agent.schema import InvestigationPhase


class TestMemoryManager:
    """Test suite for MemoryManager."""

    @pytest.fixture
    def mock_vertex_ai(self):
        """Mock Vertex AI Memory Bank Service."""
        with patch("sre_agent.memory.manager.VertexAiMemoryBankService") as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_init_success(self, mock_vertex_ai):
        """Test successful initialization."""
        manager = MemoryManager(project_id="test-proj")
        assert manager.project_id == "test-proj"
        mock_vertex_ai.assert_called_once()
        assert manager.memory_service is not None

    @pytest.mark.asyncio
    async def test_init_failure_safe(self, mock_vertex_ai):
        """Test initialization failure is handled gracefully."""
        mock_vertex_ai.side_effect = Exception("Auth failed")
        manager = MemoryManager(project_id="test-proj")
        from sre_agent.memory.local import LocalMemoryService

        assert isinstance(manager.memory_service, LocalMemoryService)
        # Should not raise exception

    @pytest.mark.asyncio
    async def test_add_finding_cache_only(self, mock_vertex_ai):
        """Test adding finding works with cache (no persistence)."""
        mock_vertex_ai.side_effect = Exception("No service")
        manager = MemoryManager(project_id="test-proj")

        await manager.add_finding("Test finding", "test_tool")

        assert len(manager._findings_cache) == 1
        assert manager._findings_cache[0].description == "Test finding"

    @pytest.mark.asyncio
    async def test_add_finding_persistence(self, mock_vertex_ai):
        """Test adding finding persists to Vertex AI."""
        mock_service = AsyncMock()
        mock_vertex_ai.return_value = mock_service
        manager = MemoryManager(project_id="test-proj")

        await manager.add_finding("Test finding", "test_tool", session_id="sess-123")

        mock_service.save_memory.assert_called_once()
        call_kwargs = mock_service.save_memory.call_args.kwargs
        assert call_kwargs["session_id"] == "sess-123"
        assert "Test finding" in call_kwargs["memory_content"]

    @pytest.mark.asyncio
    async def test_update_state(self, mock_vertex_ai):
        """Test updating state."""
        manager = MemoryManager(project_id="test-proj")

        await manager.update_state(InvestigationPhase.TRIAGE)
        assert manager.get_state() == InvestigationPhase.TRIAGE

    @pytest.mark.asyncio
    async def test_get_relevant_findings(self, mock_vertex_ai):
        """Test searching findings."""
        mock_service = AsyncMock()
        mock_vertex_ai.return_value = mock_service

        # Mock search results
        mock_mem = MagicMock()
        mock_mem.content = "Found item"
        mock_mem.metadata = {"tool": "tool1", "confidence": "high"}
        mock_service.search_memory.return_value = [mock_mem]

        manager = MemoryManager(project_id="test-proj")
        results = await manager.get_relevant_findings("query", session_id="sess-1")

        assert len(results) == 1
        assert results[0].description == "Found item"
        assert results[0].source_tool == "tool1"
