"""
Goal: Verify Memory tools correctly wrap results in BaseToolResponse (normalized as dict by @adk_tool).
Patterns: Mocking, BaseToolResponse Validation.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sre_agent.memory.manager import InvestigationPattern
from sre_agent.schema import BaseToolResponse, InvestigationPhase, ToolStatus
from sre_agent.tools.memory import (
    add_finding_to_memory,
    analyze_and_learn_from_traces,
    complete_investigation,
    get_recommended_investigation_strategy,
    search_memory,
)


@pytest.fixture
def mock_memory_manager():
    """Mock memory manager."""
    with patch("sre_agent.tools.memory.get_memory_manager") as mock:
        yield mock


@pytest.fixture
def mock_tool_context():
    """Create a mock tool context with invocation_context."""
    mock_ctx = MagicMock()
    mock_inv_ctx = MagicMock()
    mock_session = MagicMock()
    mock_session.id = "test-session-123"
    mock_inv_ctx.session = mock_session
    mock_ctx.invocation_context = mock_inv_ctx
    return mock_ctx


@pytest.mark.asyncio
async def test_search_memory_returns_basetool_response(mock_memory_manager):
    """Verify search_memory wraps results correctly."""
    mock_manager = AsyncMock()
    mock_manager.get_relevant_findings.return_value = []
    mock_memory_manager.return_value = mock_manager

    response = await search_memory(query="test", tool_context=None)

    # @adk_tool returns Pydantic models directly in unit tests unless runtime wrapper is active
    assert isinstance(response, BaseToolResponse)
    assert response.status == ToolStatus.SUCCESS
    assert response.result == []


@pytest.mark.asyncio
async def test_add_finding_to_memory_returns_basetool_response(mock_memory_manager):
    """Verify add_finding_to_memory wraps results correctly."""
    mock_manager = AsyncMock()
    mock_memory_manager.return_value = mock_manager

    response = await add_finding_to_memory(
        description="test", source_tool="test", tool_context=None
    )

    assert isinstance(response, BaseToolResponse)
    assert response.status == ToolStatus.SUCCESS
    assert "Finding added" in response.result


@pytest.mark.asyncio
async def test_complete_investigation_learns_pattern(
    mock_memory_manager, mock_tool_context
):
    """Verify complete_investigation calls learn_from_investigation and updates state."""
    mock_manager = AsyncMock()
    mock_manager.update_state = AsyncMock()
    mock_manager.learn_from_investigation = AsyncMock()
    mock_manager.add_session_to_memory = AsyncMock(return_value=True)
    mock_manager.reset_session_tracking = MagicMock()
    mock_memory_manager.return_value = mock_manager

    with patch("sre_agent.tools.memory._get_context") as mock_get_ctx:
        mock_get_ctx.return_value = ("test-session-123", "user@test.com")

        response = await complete_investigation(
            symptom_type="high_latency_checkout",
            root_cause_category="connection_pool_exhaustion",
            resolution_summary="Increased pool size from 10 to 50",
            tool_context=mock_tool_context,
        )

    assert isinstance(response, BaseToolResponse)
    assert response.status == ToolStatus.SUCCESS
    assert "pattern" in response.result
    assert response.result["pattern"]["symptom_type"] == "high_latency_checkout"

    # Verify the manager was called correctly
    mock_manager.update_state.assert_called_once()
    call_args = mock_manager.update_state.call_args
    assert call_args[0][0] == InvestigationPhase.RESOLVED

    mock_manager.learn_from_investigation.assert_called_once()
    learn_call = mock_manager.learn_from_investigation.call_args
    assert learn_call.kwargs["symptom_type"] == "high_latency_checkout"
    assert learn_call.kwargs["root_cause_category"] == "connection_pool_exhaustion"
    mock_manager.reset_session_tracking.assert_called_once()


@pytest.mark.asyncio
async def test_get_recommended_investigation_strategy_with_patterns(
    mock_memory_manager,
):
    """Verify get_recommended_investigation_strategy returns matching patterns."""
    mock_manager = AsyncMock()
    mock_pattern = InvestigationPattern(
        symptom_type="high_latency",
        root_cause_category="connection_pool",
        tool_sequence=["fetch_trace", "analyze_critical_path"],
        resolution_summary="Increase pool size",
        confidence=0.8,
        occurrence_count=3,
    )
    mock_manager.get_recommended_strategy.return_value = [mock_pattern]
    mock_memory_manager.return_value = mock_manager

    response = await get_recommended_investigation_strategy(
        symptom_description="checkout is slow",
        tool_context=None,
    )

    assert isinstance(response, BaseToolResponse)
    assert response.status == ToolStatus.SUCCESS
    assert "patterns" in response.result
    assert len(response.result["patterns"]) == 1
    assert response.result["patterns"][0]["symptom_type"] == "high_latency"


@pytest.mark.asyncio
async def test_get_recommended_investigation_strategy_no_patterns(mock_memory_manager):
    """Verify get_recommended_investigation_strategy handles no matches."""
    mock_manager = AsyncMock()
    mock_manager.get_recommended_strategy.return_value = []
    mock_memory_manager.return_value = mock_manager

    response = await get_recommended_investigation_strategy(
        symptom_description="never seen this before",
        tool_context=None,
    )

    assert isinstance(response, BaseToolResponse)
    assert response.status == ToolStatus.SUCCESS
    assert response.result["patterns"] == []
    assert "No matching patterns" in response.result["message"]


@pytest.mark.asyncio
async def test_analyze_and_learn_from_traces_generates_sql():
    """Verify analyze_and_learn_from_traces generates correct SQL query."""
    with patch("sre_agent.tools.mcp.gcp.get_project_id_with_fallback") as mock_pid:
        mock_pid.return_value = "test-project"

        response = await analyze_and_learn_from_traces(
            trace_project_id="my-agent-project",
            hours_back=12,
            focus_on_errors=True,
            tool_context=None,
        )

        assert isinstance(response, BaseToolResponse)
        assert response.status == ToolStatus.SUCCESS
        assert "sql_query" in response.result
        assert response.result["analysis_type"] == "self_improvement"
        assert response.metadata["project_id"] == "my-agent-project"
        assert response.metadata["hours_back"] == 12


@pytest.mark.asyncio
async def test_analyze_and_learn_from_traces_no_project_id():
    """Verify analyze_and_learn_from_traces errors without project ID."""
    with patch("sre_agent.tools.mcp.gcp.get_project_id_with_fallback") as mock_pid:
        mock_pid.return_value = None

        response = await analyze_and_learn_from_traces(
            trace_project_id=None,
            tool_context=None,
        )

        assert isinstance(response, BaseToolResponse)
        assert response.status == ToolStatus.ERROR
        assert "trace_project_id is required" in response.error
