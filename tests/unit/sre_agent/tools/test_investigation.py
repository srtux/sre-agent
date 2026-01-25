"""
Goal: Verify the investigation tool correctly tracks state transitions and findings in session storage.
Patterns: Session Service Mocking, Investigation State Schema Testing.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sre_agent.tools.investigation import (
    get_investigation_summary,
    update_investigation_state,
)


@pytest.mark.asyncio
async def test_update_investigation_state():
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

        # Test phase update
        result = await update_investigation_state(
            mock_tool_context, phase="analysis", new_findings=["Disk is 90% full"]
        )

        assert "Successfully updated" in result
        assert "analysis" in result
        mock_service.update_session_state.assert_called_once()

        # Verify call arguments
        args = mock_service.update_session_state.call_args
        state_update = args[0][1]
        assert state_update["investigation_state"]["phase"] == "analysis"
        assert "Disk is 90% full" in state_update["investigation_state"]["findings"]


@pytest.mark.asyncio
async def test_update_investigation_state_invalid_phase():
    mock_session = MagicMock()
    mock_session.state = {"investigation_state": {}}
    mock_tool_context = MagicMock()
    mock_tool_context.invocation_context.session = mock_session

    result = await update_investigation_state(mock_tool_context, phase="invalid_phase")
    assert "Error: Invalid phase" in result


@pytest.mark.asyncio
async def test_get_investigation_summary():
    mock_session = MagicMock()
    mock_session.state = {
        "investigation_state": {
            "phase": "root_cause",
            "findings": ["Error 500 in logs"],
            "hypotheses": ["DB connection issue"],
            "confirmed_root_cause": "DB is down",
        }
    }
    mock_tool_context = MagicMock()
    mock_tool_context.invocation_context.session = mock_session

    result = await get_investigation_summary(mock_tool_context)
    assert "ROOT_CAUSE" in result
    assert "Error 500" in result
    assert "DB connection issue" in result
    assert "DB is down" in result


@pytest.mark.asyncio
async def test_investigation_no_session():
    mock_tool_context = MagicMock()
    # Ensure both possible attributes are None
    mock_tool_context.invocation_context = None
    mock_tool_context._invocation_context = None

    result = await update_investigation_state(mock_tool_context, phase="analysis")
    assert "Error: No active session" in result

    result = await get_investigation_summary(mock_tool_context)
    assert "Error: No active session" in result
