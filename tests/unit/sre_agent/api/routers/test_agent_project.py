from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request

from sre_agent.api.routers.agent import AgentMessage, AgentRequest, chat_agent
from sre_agent.auth import (
    SESSION_STATE_PROJECT_ID_KEY,
)


@pytest.mark.asyncio
async def test_chat_agent_updates_session_project_id():
    """Test that chat_agent updates the session state when project_id changes."""

    # Mock Request
    mock_raw_request = MagicMock(spec=Request)
    mock_raw_request.is_disconnected = AsyncMock(return_value=False)

    # Mock Session Service
    mock_session = MagicMock()
    mock_session.id = "test-session-id"
    mock_session.user_id = "test-user"
    mock_session.state = {
        SESSION_STATE_PROJECT_ID_KEY: "old-project",
        "investigation_state": {},
    }

    mock_session_service = AsyncMock()
    mock_session_service.get_session.return_value = mock_session
    mock_session_service.update_session_state = AsyncMock()
    mock_session_service.session_service = AsyncMock()

    # Mock Credentials
    mock_creds = MagicMock()
    mock_creds.token = "test-token"

    with (
        patch(
            "sre_agent.api.routers.agent.get_session_service",
            return_value=mock_session_service,
        ),
        patch(
            "sre_agent.api.routers.agent.get_current_credentials_or_none",
            return_value=mock_creds,
        ),
        patch(
            "sre_agent.api.routers.agent.get_current_project_id",
            return_value="new-project",
        ),
        patch("sre_agent.agent.root_agent") as mock_root_agent,
        patch("sre_agent.api.routers.agent.is_remote_mode", return_value=False),
        patch("sre_agent.api.routers.agent.InvocationContext") as mock_inv_ctx_class,
    ):
        mock_inv_ctx = MagicMock()
        mock_inv_ctx.invocation_id = "test-invocation-id"
        mock_inv_ctx_class.return_value = mock_inv_ctx

        # Setup root agent mock to return an empty generator
        async def empty_gen(*args, **kwargs):
            if False:
                yield

        mock_root_agent.run_async.side_effect = empty_gen

        chat_req = AgentRequest(
            messages=[AgentMessage(role="user", text="hello")],
            session_id="test-session-id",
            project_id="new-project",
        )

        # Execute
        await chat_agent(chat_req, mock_raw_request)

        # Verify update_session_state was called with new project ID
        mock_session_service.update_session_state.assert_called_once()
        args, _ = mock_session_service.update_session_state.call_args
        assert args[0] == mock_session
        assert args[1][SESSION_STATE_PROJECT_ID_KEY] == "new-project"


@pytest.mark.asyncio
async def test_chat_agent_initializes_new_session_with_project_id():
    """Test that chat_agent creates a new session with the project ID from request."""

    # Mock Request
    mock_raw_request = MagicMock(spec=Request)
    mock_raw_request.is_disconnected = AsyncMock(return_value=False)

    # Mock Session Service
    mock_session = MagicMock()
    mock_session.id = "new-session-id"
    mock_session.state = {}

    mock_session_service = AsyncMock()
    mock_session_service.get_session.return_value = None  # Force new session
    mock_session_service.create_session.return_value = mock_session
    mock_session_service.session_service = AsyncMock()

    # Mock Credentials
    mock_creds = MagicMock()
    mock_creds.token = "test-token"

    with (
        patch(
            "sre_agent.api.routers.agent.get_session_service",
            return_value=mock_session_service,
        ),
        patch(
            "sre_agent.api.routers.agent.get_current_credentials_or_none",
            return_value=mock_creds,
        ),
        patch("sre_agent.api.routers.agent.get_current_project_id", return_value=None),
        patch("sre_agent.agent.root_agent") as mock_root_agent,
        patch("sre_agent.api.routers.agent.is_remote_mode", return_value=False),
        patch("sre_agent.api.routers.agent.InvocationContext") as mock_inv_ctx_class,
    ):
        mock_inv_ctx = MagicMock()
        mock_inv_ctx.invocation_id = "test-invocation-id"
        mock_inv_ctx_class.return_value = mock_inv_ctx

        mock_root_agent.run_async.side_effect = lambda *args, **kwargs: (yield from [])

        chat_req = AgentRequest(
            messages=[AgentMessage(role="user", text="hello")],
            project_id="request-project",
        )

        # Execute
        await chat_agent(chat_req, mock_raw_request)

        # Verify create_session was called with request project ID
        mock_session_service.create_session.assert_called_once()
        kwargs = mock_session_service.create_session.call_args.kwargs
        assert (
            kwargs["initial_state"][SESSION_STATE_PROJECT_ID_KEY] == "request-project"
        )
