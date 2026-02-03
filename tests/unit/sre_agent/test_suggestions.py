"""Tests for contextual suggestions generation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sre_agent.suggestions import (
    DEFAULT_SUGGESTIONS,
    MAX_SUGGESTIONS,
    MIN_SUGGESTIONS,
    _extract_conversation_context,
    _generate_llm_suggestions,
    generate_contextual_suggestions,
)


class MockPart:
    """Mock for ADK Part objects."""

    def __init__(self, text: str | None = None):
        self.text = text


class MockContent:
    """Mock for ADK Content objects."""

    def __init__(self, parts: list[MockPart] | None = None):
        self.parts = parts or []


class MockEvent:
    """Mock for ADK Event objects."""

    def __init__(self, author: str, content: MockContent | None = None):
        self.author = author
        self.content = content


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
        # Should return project-aware defaults
        assert len(suggestions) >= MIN_SUGGESTIONS
        assert len(suggestions) <= MAX_SUGGESTIONS


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
        assert "Investigate alert: High CPU Usage" in suggestions
        assert "Show all firing alerts" in suggestions


@pytest.mark.asyncio
async def test_generate_suggestions_with_multiple_alerts():
    """Test suggestions when there are multiple active alerts."""
    project_id = "test-project-123"
    mock_alerts = [
        {"display_name": "High CPU Usage", "state": "OPEN"},
        {"display_name": "Memory Pressure", "state": "OPEN"},
        {"display_name": "Disk Full", "state": "OPEN"},
        {"display_name": "Network Latency", "state": "OPEN"},
    ]
    with patch(
        "sre_agent.tools.clients.alerts.list_alerts", new_callable=AsyncMock
    ) as mock_list:
        mock_list.return_value = mock_alerts
        suggestions = await generate_contextual_suggestions(project_id=project_id)
        # Should include up to 3 alert-specific suggestions
        alert_suggestions = [
            s for s in suggestions if s.startswith("Investigate alert:")
        ]
        assert len(alert_suggestions) <= 3
        assert len(suggestions) <= MAX_SUGGESTIONS


@pytest.mark.asyncio
async def test_generate_suggestions_with_long_alert_name():
    """Test that long alert names are truncated."""
    project_id = "test-project-123"
    long_name = "This is a very long alert name that should be truncated for display"
    mock_alerts = [{"display_name": long_name, "state": "OPEN"}]
    with patch(
        "sre_agent.tools.clients.alerts.list_alerts", new_callable=AsyncMock
    ) as mock_list:
        mock_list.return_value = mock_alerts
        suggestions = await generate_contextual_suggestions(project_id=project_id)
        # Find the alert suggestion
        alert_suggestion = next(
            s for s in suggestions if s.startswith("Investigate alert:")
        )
        # Should be truncated (40 chars + "..." = 43 max)
        assert len(alert_suggestion) < len(f"Investigate alert: {long_name}")


@pytest.mark.asyncio
async def test_generate_suggestions_session_with_llm():
    """Test suggestions generation with session history using LLM."""
    session_id = "sess-123"

    mock_event = MockEvent(
        author="user",
        content=MockContent([MockPart("Check the Cilium logs in the cluster")]),
    )

    mock_session = MagicMock()
    mock_session.events = [mock_event]

    mock_service = MagicMock()
    mock_service.get_session = AsyncMock(return_value=mock_session)

    mock_llm_response = MagicMock()
    mock_llm_response.text = (
        '["Check Cilium pod status", "Analyze network policies", "Review CNI logs"]'
    )

    mock_agent = MagicMock()
    mock_agent.run_async = MagicMock()

    async def mock_run_async(*args, **kwargs):
        yield MockEvent(
            author="suggestions_generator",
            content=MockContent([MockPart(mock_llm_response.text)]),
        )

    mock_agent.run_async.side_effect = mock_run_async

    with (
        patch("sre_agent.suggestions.get_session_service", return_value=mock_service),
        patch("sre_agent.suggestions.LlmAgent", return_value=mock_agent),
    ):
        suggestions = await generate_contextual_suggestions(session_id=session_id)
        assert len(suggestions) >= MIN_SUGGESTIONS
        assert "Check Cilium pod status" in suggestions


@pytest.mark.asyncio
async def test_generate_suggestions_session_with_recommended_steps():
    """Test that agent's Recommended Next Steps are extracted and used."""
    session_id = "sess-123"

    user_event = MockEvent(
        author="user",
        content=MockContent([MockPart("Analyze the cluster health")]),
    )

    agent_response = """Based on my analysis, there are some issues.

**Recommended Next Steps**:
1. Check Cilium Health
2. Review cluster events
3. Analyze pod logs

Let me know if you need more details."""

    model_event = MockEvent(
        author="model",
        content=MockContent([MockPart(agent_response)]),
    )

    mock_session = MagicMock()
    mock_session.events = [user_event, model_event]

    mock_service = MagicMock()
    mock_service.get_session = AsyncMock(return_value=mock_session)

    # Test context extraction
    context = _extract_conversation_context(mock_session.events)
    assert "Check Cilium Health" in context
    assert "Review cluster events" in context

    # Test full flow with LLM
    mock_llm_response = MagicMock()
    mock_llm_response.text = (
        '["Check Cilium health", "Review cluster events", "Analyze pod logs"]'
    )

    mock_agent = MagicMock()
    mock_agent.run_async = MagicMock()

    async def mock_run_async(*args, **kwargs):
        yield MockEvent(
            author="suggestions_generator",
            content=MockContent([MockPart(mock_llm_response.text)]),
        )

    mock_agent.run_async.side_effect = mock_run_async

    with (
        patch("sre_agent.suggestions.get_session_service", return_value=mock_service),
        patch("sre_agent.suggestions.LlmAgent", return_value=mock_agent),
    ):
        suggestions = await generate_contextual_suggestions(session_id=session_id)
        assert len(suggestions) >= MIN_SUGGESTIONS


@pytest.mark.asyncio
async def test_generate_llm_suggestions_handles_markdown_codeblocks():
    """Test that LLM responses with markdown code blocks are parsed correctly."""
    mock_llm_response = MagicMock()
    mock_llm_response.text = '```json\n["Check logs", "Analyze traces"]\n```'

    mock_agent = MagicMock()
    mock_agent.run_async = MagicMock()

    async def mock_run_async(*args, **kwargs):
        yield MockEvent(
            author="suggestions_generator",
            content=MockContent([MockPart(mock_llm_response.text)]),
        )

    mock_agent.run_async.side_effect = mock_run_async

    with patch("sre_agent.suggestions.LlmAgent", return_value=mock_agent):
        suggestions = await _generate_llm_suggestions("test context")
        assert "Check logs" in suggestions
        assert "Analyze traces" in suggestions


@pytest.mark.asyncio
async def test_generate_llm_suggestions_handles_empty_response():
    """Test that empty LLM responses are handled gracefully."""
    mock_llm_response = MagicMock()
    mock_llm_response.text = None

    mock_agent = MagicMock()
    mock_agent.run_async = MagicMock()

    async def mock_run_async(*args, **kwargs):
        text = getattr(mock_llm_response, "text", "") or ""
        yield MockEvent(
            author="suggestions_generator",
            content=MockContent([MockPart(text)]),
        )

    mock_agent.run_async.side_effect = mock_run_async

    with patch("sre_agent.suggestions.LlmAgent", return_value=mock_agent):
        suggestions = await _generate_llm_suggestions("test context")
        assert suggestions == []


@pytest.mark.asyncio
async def test_generate_llm_suggestions_handles_invalid_json():
    """Test that invalid JSON responses are handled gracefully."""
    mock_llm_response = MagicMock()
    mock_llm_response.text = "This is not valid JSON"

    mock_agent = MagicMock()
    mock_agent.run_async = MagicMock()

    async def mock_run_async(*args, **kwargs):
        yield MockEvent(
            author="suggestions_generator",
            content=MockContent([MockPart(mock_llm_response.text)]),
        )

    mock_agent.run_async.side_effect = mock_run_async

    with patch("sre_agent.suggestions.LlmAgent", return_value=mock_agent):
        suggestions = await _generate_llm_suggestions("test context")
        assert suggestions == []


@pytest.mark.asyncio
async def test_generate_llm_suggestions_filters_invalid_suggestions():
    """Test that suggestions that are too short or too long are filtered."""
    import json

    # Create a proper JSON array with too-short, valid, and too-long suggestions
    suggestions_list = ["OK", "This is a valid suggestion", "A" * 200]
    mock_llm_response = MagicMock()
    mock_llm_response.text = json.dumps(suggestions_list)

    mock_agent = MagicMock()
    mock_agent.run_async = MagicMock()

    async def mock_run_async(*args, **kwargs):
        yield MockEvent(
            author="suggestions_generator",
            content=MockContent([MockPart(mock_llm_response.text)]),
        )

    mock_agent.run_async.side_effect = mock_run_async

    with patch("sre_agent.suggestions.LlmAgent", return_value=mock_agent):
        suggestions = await _generate_llm_suggestions("test context")
        # Only "This is a valid suggestion" should pass the filter
        assert len(suggestions) == 1
        assert "This is a valid suggestion" in suggestions


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

    mock_event = MockEvent(
        author="bot",  # Not a user
        content=MockContent([MockPart("Some bot message")]),
    )

    mock_session = MagicMock()
    mock_session.events = [mock_event]

    mock_service = MagicMock()
    mock_service.get_session = AsyncMock(return_value=mock_session)

    with patch("sre_agent.suggestions.get_session_service", return_value=mock_service):
        suggestions = await generate_contextual_suggestions(session_id=session_id)
        # Should fallback since no user messages
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
        assert "Investigate alert: Database Error" in suggestions


@pytest.mark.asyncio
async def test_generate_suggestions_alerts_invalid_format():
    """Test suggestions when alerts are returned in an invalid format."""
    project_id = "test-project-123"
    with patch(
        "sre_agent.tools.clients.alerts.list_alerts", new_callable=AsyncMock
    ) as mock_list:
        mock_list.return_value = "invalid"
        suggestions = await generate_contextual_suggestions(project_id=project_id)
        # Should fallback to project-aware defaults
        assert len(suggestions) >= MIN_SUGGESTIONS


@pytest.mark.asyncio
async def test_generate_suggestions_alerts_error():
    """Test suggestions when list_alerts fails."""
    project_id = "test-project-123"
    with patch(
        "sre_agent.tools.clients.alerts.list_alerts", side_effect=Exception("API error")
    ):
        suggestions = await generate_contextual_suggestions(project_id=project_id)
        # Should fallback to project-aware defaults
        assert len(suggestions) >= MIN_SUGGESTIONS


@pytest.mark.asyncio
async def test_generate_suggestions_llm_fallback_supplements_defaults():
    """Test that when LLM returns too few suggestions, defaults are added."""
    session_id = "sess-123"

    mock_event = MockEvent(
        author="user",
        content=MockContent([MockPart("Check the logs")]),
    )

    mock_session = MagicMock()
    mock_session.events = [mock_event]

    mock_service = MagicMock()
    mock_service.get_session = AsyncMock(return_value=mock_session)

    # LLM returns only 2 suggestions (below MIN_SUGGESTIONS)
    mock_llm_response = MagicMock()
    mock_llm_response.text = '["Check error logs", "Analyze patterns"]'

    mock_agent = MagicMock()
    mock_agent.run_async = MagicMock()

    async def mock_run_async(*args, **kwargs):
        yield MockEvent(
            author="suggestions_generator",
            content=MockContent([MockPart(mock_llm_response.text)]),
        )

    mock_agent.run_async.side_effect = mock_run_async

    with (
        patch("sre_agent.suggestions.get_session_service", return_value=mock_service),
        patch("sre_agent.suggestions.LlmAgent", return_value=mock_agent),
    ):
        suggestions = await generate_contextual_suggestions(session_id=session_id)
        # Should have LLM suggestions plus defaults to reach minimum
        assert len(suggestions) >= MIN_SUGGESTIONS
        assert "Check error logs" in suggestions
        assert "Analyze patterns" in suggestions


def test_extract_conversation_context_empty_events():
    """Test context extraction with empty events list."""
    context = _extract_conversation_context([])
    assert context == ""


def test_extract_conversation_context_user_messages():
    """Test context extraction includes user messages."""
    events = [
        MockEvent(
            author="user",
            content=MockContent([MockPart("First message")]),
        ),
        MockEvent(
            author="user",
            content=MockContent([MockPart("Second message")]),
        ),
    ]
    context = _extract_conversation_context(events)
    assert "User: First message" in context or "User: Second message" in context


def test_extract_conversation_context_recommended_steps():
    """Test context extraction captures Recommended Next Steps."""
    agent_response = """Analysis complete.

**Recommended Next Steps**:
1. Check pod health
2. Review deployment logs
3. Analyze metrics

Done."""

    events = [
        MockEvent(
            author="model",
            content=MockContent([MockPart(agent_response)]),
        ),
    ]
    context = _extract_conversation_context(events)
    assert "Check pod health" in context
    assert "Review deployment logs" in context


def test_extract_conversation_context_findings():
    """Test context extraction captures Key Findings sections."""
    agent_response = """Analysis:

**Key Findings**:
The system is experiencing memory pressure.

More details follow."""

    events = [
        MockEvent(
            author="model",
            content=MockContent([MockPart(agent_response)]),
        ),
    ]
    context = _extract_conversation_context(events)
    assert "memory pressure" in context


def test_extract_conversation_context_truncates_long_messages():
    """Test that very long user messages are truncated."""
    long_message = "A" * 1000  # Very long message
    events = [
        MockEvent(
            author="user",
            content=MockContent([MockPart(long_message)]),
        ),
    ]
    context = _extract_conversation_context(events)
    # Should be truncated to 500 chars
    assert len(context.split("User: ")[1]) <= 500
