"""
Goal: Verify the agent router handles streaming queries and remote mode correctly.
Patterns: ADK Agent Mocking, Async Generator Streaming, Environment Variable Patching.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from server import app

client = TestClient(app)


@pytest.fixture
def mock_agent_deps():
    with (
        patch("sre_agent.api.routers.agent.get_session_service") as m_session,
        patch("sre_agent.api.routers.agent.is_remote_mode") as m_remote,
        patch(
            "sre_agent.api.routers.agent.generate_contextual_suggestions"
        ) as m_suggest,
    ):
        session_service = AsyncMock()
        m_session.return_value = session_service
        m_remote.return_value = False
        m_suggest.return_value = ["suggest1"]

        yield {
            "session_service": session_service,
            "is_remote": m_remote,
            "suggestions": m_suggest,
        }


@pytest.mark.asyncio
async def test_get_suggestions_direct(mock_agent_deps):
    response = client.get("/api/suggestions")
    assert response.status_code == 200
    assert "suggest1" in response.json()["suggestions"]


@pytest.mark.asyncio
async def test_chat_agent_local(mock_agent_deps):
    # Mock local agent execution
    mock_session = MagicMock()
    mock_session.id = "s1"
    mock_session.state = {"investigation_state": {}}
    mock_agent_deps["session_service"].create_session.return_value = mock_session
    mock_agent_deps["session_service"].get_session.return_value = mock_session

    with (
        patch("sre_agent.api.routers.agent.InvocationContext") as mock_inv_ctx_class,
        patch("sre_agent.api.routers.agent.InvestigationState") as mock_inv_state_class,
        patch("sre_agent.api.routers.agent.Event"),
        patch("sre_agent.agent.root_agent") as mock_agent,
    ):
        # Configure mocks to return expected types/values
        mock_inv_ctx = MagicMock()
        mock_inv_ctx.invocation_id = "test-inv-id"
        mock_inv_ctx_class.return_value = mock_inv_ctx

        mock_inv_state = MagicMock()
        mock_inv_state.phase.value = "triage"
        mock_inv_state_class.from_dict.return_value = mock_inv_state

        # Mock generator
        async def mock_gen(*args, **kwargs):
            # Return an ADK event-like object
            event = MagicMock()
            event.content.parts = [{"text": "Hello"}]
            yield event

        mock_agent.run_async.return_value = mock_gen()

        payload = {"messages": [{"role": "user", "text": "Hi"}], "project_id": "p1"}

        response = client.post("/api/genui/chat", json=payload)
        assert response.status_code == 200
        # Check stream content
        lines = response.content.split(b"\n")
        assert any(b"session" in line for line in lines)
        assert any(b"Hello" in line for line in lines)


@pytest.mark.asyncio
async def test_chat_agent_remote(mock_agent_deps):
    mock_agent_deps["is_remote"].return_value = True

    with patch(
        "sre_agent.api.routers.agent.get_agent_engine_client"
    ) as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        async def mock_stream(*args, **kwargs):
            yield {"type": "session", "id": "s1"}
            yield {"content": {"parts": [{"text": "Remote Hello"}]}}

        mock_client.stream_query.return_value = mock_stream()

        payload = {"messages": [{"role": "user", "text": "Hi"}], "project_id": "p1"}

        response = client.post("/api/genui/chat", json=payload)
        assert response.status_code == 200
        assert b"Remote Hello" in response.content


def test_generate_session_title():
    from sre_agent.api.routers.agent import _generate_session_title

    # The current implementation only removes ONE prefix
    assert _generate_session_title("Can you help me with GKE?") == "Help me with GKE"
    assert (
        _generate_session_title("I need to fixed the database") == "Fixed the database"
    )
    assert _generate_session_title("Hello") == "Hello"
