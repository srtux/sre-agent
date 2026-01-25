"""Unit tests for proactive signal suggestions."""

from unittest.mock import MagicMock, patch

import pytest

from sre_agent.schema import InvestigationPhase
from sre_agent.tools.proactive.related_signals import suggest_next_steps


@pytest.fixture
def mock_memory_manager():
    """Mock memory manager."""
    with patch("sre_agent.tools.proactive.related_signals.get_memory_manager") as mock:
        yield mock


@pytest.mark.asyncio
async def test_suggest_next_steps_initiated(mock_memory_manager):
    """Test suggestions for INITIATED phase."""
    mock_manager = MagicMock()
    mock_manager.get_state.return_value = InvestigationPhase.INITIATED
    mock_memory_manager.return_value = mock_manager

    result = await suggest_next_steps(tool_context=None)

    assert "Suggested Next Steps" in result
    assert "run_aggregate_analysis" in result
    assert "list_alerts" in result


@pytest.mark.asyncio
async def test_suggest_next_steps_triage(mock_memory_manager):
    """Test suggestions for TRIAGE phase."""
    mock_manager = MagicMock()
    mock_manager.get_state.return_value = InvestigationPhase.TRIAGE
    mock_memory_manager.return_value = mock_manager

    result = await suggest_next_steps(tool_context=None)

    assert "find_bottleneck_services" in result
    assert "run_triage_analysis" in result


@pytest.mark.asyncio
async def test_suggest_next_steps_deep_dive(mock_memory_manager):
    """Test suggestions for DEEP_DIVE phase."""
    mock_manager = MagicMock()
    mock_manager.get_state.return_value = InvestigationPhase.DEEP_DIVE
    mock_memory_manager.return_value = mock_manager

    result = await suggest_next_steps(tool_context=None)

    assert "run_deep_dive_analysis" in result
    assert "run_log_pattern_analysis" in result


@pytest.mark.asyncio
async def test_suggest_next_steps_remediation(mock_memory_manager):
    """Test suggestions for REMEDIATION phase."""
    mock_manager = MagicMock()
    mock_manager.get_state.return_value = InvestigationPhase.REMEDIATION
    mock_memory_manager.return_value = mock_manager

    result = await suggest_next_steps(tool_context=None)

    assert "generate_remediation_suggestions" in result
    assert "estimate_remediation_risk" in result
