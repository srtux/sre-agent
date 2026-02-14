"""
Goal: Verify the investigation tool correctly tracks state transitions and findings in session storage.
Patterns: Session Service Mocking, Investigation State Schema Testing.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sre_agent.schema import BaseToolResponse, ToolStatus
from sre_agent.tools.investigation import (
    get_investigation_summary,
    update_investigation_state,
)


@pytest.fixture
def mock_memory_manager():
    """Mock get_memory_manager to avoid real backend calls."""
    with patch("sre_agent.tools.investigation.get_memory_manager") as mock:
        manager = AsyncMock()
        mock.return_value = manager
        yield manager


@pytest.mark.asyncio
async def test_update_investigation_state(mock_memory_manager):
    mock_session = MagicMock()
    mock_session.id = "s1"
    mock_session.state = {"investigation_state": {}}

    mock_inv_ctx = MagicMock()
    mock_inv_ctx.session = mock_session

    mock_tool_context = MagicMock()
    mock_tool_context.invocation_context = mock_inv_ctx

    with patch("sre_agent.services.get_session_service") as mock_service_factory:
        mock_service = AsyncMock()
        mock_service_factory.return_value = mock_service

        # Test full update
        response = await update_investigation_state(
            phase="triage",
            new_findings=["Disk is 90% full"],
            hypothesis="Disk pressure causing latency",
            root_cause="Log rotation failure",
            tool_context=mock_tool_context,
        )

        assert isinstance(response, BaseToolResponse)
        assert response.status == ToolStatus.SUCCESS
        assert "Successfully updated" in response.result

        # Verify session service update
        mock_service.update_session_state.assert_called_once()
        args = mock_service.update_session_state.call_args
        state_update = args[0][1]
        inv_state = state_update["investigation_state"]

        assert inv_state["phase"] == "triage"
        assert "Disk is 90% full" in inv_state["findings"]
        assert "Disk pressure causing latency" in inv_state["hypotheses"]
        assert inv_state["confirmed_root_cause"] == "Log rotation failure"

        # Verify memory manager calls
        mock_memory_manager.update_state.assert_called()
        mock_memory_manager.add_finding.assert_called()


@pytest.mark.asyncio
async def test_update_investigation_state_invalid_phase(mock_memory_manager):
    mock_session = MagicMock()
    mock_session.state = {"investigation_state": {}}
    mock_tool_context = MagicMock()
    mock_tool_context.invocation_context.session = mock_session

    with patch("sre_agent.services.get_session_service") as mock_service_factory:
        mock_service = AsyncMock()
        mock_service_factory.return_value = mock_service

        response = await update_investigation_state(
            phase="invalid_phase", tool_context=mock_tool_context
        )
        assert response.status == ToolStatus.SUCCESS
        assert "Successfully updated" in response.result


@pytest.mark.asyncio
async def test_get_investigation_summary():
    mock_session = MagicMock()
    mock_session.state = {
        "investigation_state": {
            "phase": "deep_dive",
            "findings": ["Error 500 in logs"],
            "hypotheses": ["DB connection issue"],
            "confirmed_root_cause": "DB is down",
        }
    }
    mock_tool_context = MagicMock()
    mock_tool_context.invocation_context.session = mock_session

    response = await get_investigation_summary(tool_context=mock_tool_context)
    result = response.result
    assert "DEEP_DIVE" in result
    assert "Error 500" in result
    assert "DB connection issue" in result
    assert "DB is down" in result


@pytest.mark.asyncio
async def test_investigation_no_session():
    mock_tool_context = MagicMock()
    # Ensure both possible attributes are None
    mock_tool_context.invocation_context = None
    mock_tool_context._invocation_context = None

    response = await update_investigation_state(
        phase="triage", tool_context=mock_tool_context
    )
    assert response.status == ToolStatus.ERROR
    assert "No active session" in response.error

    response = await get_investigation_summary(tool_context=mock_tool_context)
    assert response.status == ToolStatus.ERROR
    assert "No active session" in response.error
