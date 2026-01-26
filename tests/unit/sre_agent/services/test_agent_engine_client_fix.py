from unittest.mock import AsyncMock, MagicMock

import pytest

from sre_agent.services.agent_engine_client import AgentEngineClient, AgentEngineConfig


@pytest.mark.asyncio
async def test_agent_engine_client_uses_message_keyword():
    """Verify that AgentEngineClient uses 'message=' keyword argument."""
    config = AgentEngineConfig(
        project_id="test-project", location="test-location", agent_id="test-agent"
    )
    client = AgentEngineClient(config)

    # Mock AdkApp
    mock_app = MagicMock()
    client._adk_app = mock_app
    client._initialized = True

    # Mock async_stream_query
    mock_stream = AsyncMock()
    # mock_stream is an async generator
    mock_stream.__aiter__.return_value = [].__iter__()
    mock_app.async_stream_query.return_value = mock_stream

    # Call stream_query
    # We need to wrap it in a list to consume the generator
    events = []
    async for event in client.stream_query(
        user_id="test-user", message="test-message", session_id="test-session"
    ):
        events.append(event)

    # Verify async_stream_query was called with 'message='
    mock_app.async_stream_query.assert_called_once()
    _args, kwargs = mock_app.async_stream_query.call_args
    assert "message" in kwargs
    assert kwargs["message"] == "test-message"
    assert "input" not in kwargs


@pytest.mark.asyncio
async def test_agent_engine_client_fallback_to_stream_query():
    """Verify fallback to sync stream_query with 'message='."""
    config = AgentEngineConfig(
        project_id="test-project", location="test-location", agent_id="test-agent"
    )
    client = AgentEngineClient(config)

    # Mock AdkApp without async_stream_query
    mock_app = MagicMock()
    del mock_app.async_stream_query
    client._adk_app = mock_app
    client._initialized = True

    # Mock stream_query
    mock_app.stream_query.return_value = []

    # Call stream_query
    events = []
    async for event in client.stream_query(
        user_id="test-user", message="test-message", session_id="test-session"
    ):
        events.append(event)

    # Verify stream_query was called with 'message='
    mock_app.stream_query.assert_called_once()
    _args, kwargs = mock_app.stream_query.call_args
    assert "message" in kwargs
    assert kwargs["message"] == "test-message"


@pytest.mark.asyncio
async def test_agent_engine_client_fallback_to_query():
    """Verify fallback to sync query with 'message='."""
    config = AgentEngineConfig(
        project_id="test-project", location="test-location", agent_id="test-agent"
    )
    client = AgentEngineClient(config)

    # Mock AdkApp without any streaming methods
    mock_app = MagicMock()
    del mock_app.async_stream_query
    del mock_app.stream_query
    client._adk_app = mock_app
    client._initialized = True

    # Mock query
    mock_app.query.return_value = {"type": "event", "content": "response"}

    # Call stream_query
    events = []
    async for event in client.stream_query(
        user_id="test-user", message="test-message", session_id="test-session"
    ):
        events.append(event)

    # Verify query was called with 'message='
    mock_app.query.assert_called_once()
    _args, kwargs = mock_app.query.call_args
    assert "message" in kwargs
    assert kwargs["message"] == "test-message"
