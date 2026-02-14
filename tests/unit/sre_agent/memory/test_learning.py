"""Tests for MemoryManager learning and investigation patterns."""

from unittest.mock import AsyncMock, patch

import pytest

from sre_agent.memory.manager import InvestigationPattern, MemoryManager


@pytest.fixture
def manager():
    with (
        patch.dict("os.environ", {"SRE_AGENT_ID": "test-agent"}),
        patch("sre_agent.memory.manager.VertexAiMemoryBankService"),
    ):
        return MemoryManager(project_id="test-project")


@pytest.mark.asyncio
async def test_record_tool_call(manager):
    """Test recording tool calls."""
    manager.record_tool_call("tool1")
    manager.record_tool_call("tool2")
    assert manager._current_tool_sequence == ["tool1", "tool2"]

    manager.reset_session_tracking()
    assert manager._current_tool_sequence == []


@pytest.mark.asyncio
async def test_learn_from_investigation(manager):
    """Test learning from a successful investigation."""
    manager.record_tool_call("query_metrics")
    manager.record_tool_call("fetch_traces")

    # Mock save_memory if it exists on the service
    manager.memory_service.save_memory = AsyncMock()

    await manager.learn_from_investigation(
        symptom_type="high_latency",
        root_cause_category="db_lock",
        resolution_summary="Fixed index",
        session_id="sess-1",
    )

    # Should have added to in-memory patterns
    assert any(p.symptom_type == "high_latency" for p in manager._learned_patterns)
    pattern = next(
        p for p in manager._learned_patterns if p.symptom_type == "high_latency"
    )
    assert pattern.root_cause_category == "db_lock"
    assert pattern.tool_sequence == ["query_metrics", "fetch_traces"]


@pytest.mark.asyncio
async def test_get_recommended_strategy(manager):
    """Test getting recommended strategy based on symptoms."""
    # Pre-populate a pattern
    pattern = InvestigationPattern(
        symptom_type="outage",
        root_cause_category="dns",
        tool_sequence=["check_dns"],
        resolution_summary="Fix DNS",
        confidence=0.9,
    )
    manager._learned_patterns.append(pattern)

    recommendations = await manager.get_recommended_strategy("We have an outage")
    assert len(recommendations) > 0
    assert recommendations[0].root_cause_category == "dns"
    assert recommendations[0].tool_sequence == ["check_dns"]


@pytest.mark.asyncio
async def test_learn_tool_error_pattern(manager):
    """Test recording a tool error pattern."""
    manager.memory_service.save_memory = AsyncMock()

    await manager.learn_tool_error_pattern(
        tool_name="test_tool",
        error_message="Test error",
        wrong_input="wrong",
        correct_input="right",
        resolution_summary="Fixed typo",
        session_id="sess-1",
    )

    manager.memory_service.save_memory.assert_called_once()
    _, kwargs = manager.memory_service.save_memory.call_args
    assert kwargs["session_id"] == "sess-1"
    assert "Test error" in kwargs["memory_content"]
    assert kwargs["metadata"]["type"] == "tool_error_pattern"
    assert kwargs["metadata"]["user_id"] == "system_shared_patterns"
