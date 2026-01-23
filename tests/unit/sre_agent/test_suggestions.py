from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sre_agent.suggestions import DEFAULT_SUGGESTIONS, generate_contextual_suggestions


@pytest.mark.asyncio
async def test_generate_suggestions_default():
    """Test suggestions when no project or session is provided."""
    suggestions = await generate_contextual_suggestions()
    assert suggestions == DEFAULT_SUGGESTIONS


@pytest.mark.asyncio
async def test_generate_suggestions_project_only_no_alerts():
    """Test suggestions with project_id but no alerts."""
    project_id = "test-project-123"
    with patch(
        "sre_agent.tools.clients.alerts.list_alerts", new_callable=AsyncMock
    ) as mock_list:
        mock_list.return_value = []
        suggestions = await generate_contextual_suggestions(project_id=project_id)
        assert project_id[:15] in suggestions[0]
        assert "Summarize GKE cluster health" in suggestions
        assert "Check for high latency traces" in suggestions


@pytest.mark.asyncio
async def test_generate_suggestions_with_alerts():
    """Test suggestions when there are active alerts."""
    project_id = "test-project-123"
    mock_alerts = [{"display_name": "High CPU Usage", "state": "OPEN"}]
    with patch(
        "sre_agent.tools.clients.alerts.list_alerts", new_callable=AsyncMock
    ) as mock_list:
        mock_list.return_value = mock_alerts
        suggestions = await generate_contextual_suggestions(project_id=project_id)
        assert "Analyze alert: High CPU Usage" in suggestions
        assert "List all firing alerts" in suggestions


@pytest.mark.asyncio
async def test_generate_suggestions_session_history_log():
    """Test suggestions based on session history containing 'log'."""
    session_id = "sess-123"

    class MockPart:
        def __init__(self, text):
            self.text = text

    mock_event = MagicMock()
    mock_event.author = "user"
    mock_event.content.parts = [MockPart("Tell me about logs")]

    mock_session = MagicMock()
    mock_session.events = [mock_event]

    mock_service = MagicMock()
    mock_service.get_session = AsyncMock(return_value=mock_session)

    with patch("sre_agent.suggestions.get_session_service", return_value=mock_service):
        suggestions = await generate_contextual_suggestions(session_id=session_id)
        assert "Analyze log patterns" in suggestions
        assert "Filter for ERROR logs" in suggestions


@pytest.mark.asyncio
async def test_generate_suggestions_session_history_trace():
    """Test suggestions based on session history containing 'trace'."""
    session_id = "sess-123"

    class MockPart:
        def __init__(self, text):
            self.text = text

    mock_event = MagicMock()
    mock_event.author = "user"
    mock_event.content.parts = [MockPart("Check traces")]

    mock_session = MagicMock()
    mock_session.events = [mock_event]

    mock_service = MagicMock()
    mock_service.get_session = AsyncMock(return_value=mock_session)

    with patch("sre_agent.suggestions.get_session_service", return_value=mock_service):
        suggestions = await generate_contextual_suggestions(session_id=session_id)
        assert "Find bottleneck services" in suggestions
        assert "Analyze critical path" in suggestions


@pytest.mark.asyncio
async def test_generate_suggestions_session_history_metric():
    """Test suggestions based on session history containing 'metric'."""
    session_id = "sess-123"

    class MockPart:
        def __init__(self, text):
            self.text = text

    mock_event = MagicMock()
    mock_event.author = "user"
    mock_event.content.parts = [MockPart("Show me metrics")]

    mock_session = MagicMock()
    mock_session.events = [mock_event]

    mock_service = MagicMock()
    mock_service.get_session = AsyncMock(return_value=mock_session)

    with patch("sre_agent.suggestions.get_session_service", return_value=mock_service):
        suggestions = await generate_contextual_suggestions(session_id=session_id)
        assert "Detect metric anomalies" in suggestions
        assert "Check SLO status" in suggestions


@pytest.mark.asyncio
async def test_generate_suggestions_error_handling():
    """Test that errors in session service don't crash the suggestion engine."""
    session_id = "sess-123"
    with patch(
        "sre_agent.suggestions.get_session_service",
        side_effect=Exception("Database down"),
    ):
        suggestions = await generate_contextual_suggestions(session_id=session_id)
        # Should fallback to default since project_id is None
        assert suggestions == DEFAULT_SUGGESTIONS


@pytest.mark.asyncio
async def test_generate_suggestions_session_no_user_msg():
    """Test suggestions when session has events but no user messages with text."""
    session_id = "sess-123"
    mock_event = MagicMock()
    mock_event.author = "bot"  # Not a user
    mock_session = MagicMock()
    mock_session.events = [mock_event]
    mock_service = MagicMock()
    mock_service.get_session = AsyncMock(return_value=mock_session)

    with patch("sre_agent.suggestions.get_session_service", return_value=mock_service):
        suggestions = await generate_contextual_suggestions(session_id=session_id)
        assert suggestions == DEFAULT_SUGGESTIONS


@pytest.mark.asyncio
async def test_generate_suggestions_alerts_dict_format():
    """Test suggestions when alerts are returned in dict format."""
    project_id = "test-project-123"
    mock_alerts_data = {"alerts": [{"display_name": "Database Error"}]}
    with patch(
        "sre_agent.tools.clients.alerts.list_alerts", new_callable=AsyncMock
    ) as mock_list:
        mock_list.return_value = mock_alerts_data
        suggestions = await generate_contextual_suggestions(project_id=project_id)
        assert "Analyze alert: Database Error" in suggestions


@pytest.mark.asyncio
async def test_generate_suggestions_alerts_invalid_format():
    """Test suggestions when alerts are returned in an invalid format."""
    project_id = "test-project-123"
    with patch(
        "sre_agent.tools.clients.alerts.list_alerts", new_callable=AsyncMock
    ) as mock_list:
        mock_list.return_value = "invalid"
        suggestions = await generate_contextual_suggestions(project_id=project_id)
        assert project_id[:15] in suggestions[0]


@pytest.mark.asyncio
async def test_generate_suggestions_alerts_error():
    """Test suggestions when list_alerts fails."""
    project_id = "test-project-123"
    with patch(
        "sre_agent.tools.clients.alerts.list_alerts", side_effect=Exception("API error")
    ):
        suggestions = await generate_contextual_suggestions(project_id=project_id)
        # Should fallback to project-aware defaults
        assert project_id[:15] in suggestions[0]
