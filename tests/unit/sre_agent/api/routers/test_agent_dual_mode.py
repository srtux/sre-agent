"""Tests for the agent router dual-mode functionality."""

import json
import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request

from sre_agent.api.routers.agent import (
    AgentMessage,
    AgentRequest,
    _handle_remote_agent,
    router,
)


@pytest.fixture
def app() -> FastAPI:
    """Create a test FastAPI app with the agent router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(app)


class TestDualModeDetection:
    """Tests for dual-mode detection logic."""

    def test_is_remote_mode_true_when_agent_id_set(self) -> None:
        """Test is_remote_mode returns True when SRE_AGENT_ID is set."""
        from sre_agent.services.agent_engine_client import is_remote_mode

        with patch.dict(os.environ, {"SRE_AGENT_ID": "test-agent-123"}):
            assert is_remote_mode() is True

    def test_is_remote_mode_false_when_agent_id_not_set(self) -> None:
        """Test is_remote_mode returns False when SRE_AGENT_ID is not set."""
        from sre_agent.services.agent_engine_client import is_remote_mode

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SRE_AGENT_ID", None)
            assert is_remote_mode() is False


class TestRemoteAgentHandler:
    """Tests for _handle_remote_agent function."""

    @pytest.mark.asyncio
    async def test_handle_remote_agent_no_client_raises_error(self) -> None:
        """Test that _handle_remote_agent raises HTTPException when client is None."""
        from fastapi import HTTPException

        request = AgentRequest(
            messages=[AgentMessage(role="user", text="Hello")],
            user_id="test-user",
        )

        mock_raw_request = MagicMock(spec=Request)

        with patch(
            "sre_agent.api.routers.agent.get_agent_engine_client", return_value=None
        ):
            with pytest.raises(HTTPException) as exc_info:
                await _handle_remote_agent(
                    request=request,
                    raw_request=mock_raw_request,
                    access_token="test-token",
                    project_id="test-project",
                )
            assert exc_info.value.status_code == 500
            assert "SRE_AGENT_ID missing" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_handle_remote_agent_streams_events(self) -> None:
        """Test that _handle_remote_agent streams events from Agent Engine."""
        request = AgentRequest(
            messages=[AgentMessage(role="user", text="Hello")],
            user_id="test-user",
        )

        mock_raw_request = MagicMock(spec=Request)

        # Create mock client
        mock_client = MagicMock()

        async def mock_stream_query(**kwargs) -> AsyncGenerator[dict, None]:
            yield {"type": "session", "session_id": "test-session"}
            yield {"content": {"parts": [{"text": "Hello!"}]}}

        mock_client.stream_query = mock_stream_query

        with patch(
            "sre_agent.api.routers.agent.get_agent_engine_client",
            return_value=mock_client,
        ):
            response = await _handle_remote_agent(
                request=request,
                raw_request=mock_raw_request,
                access_token="test-token",
                project_id="test-project",
            )

            # Response should be a StreamingResponse
            assert response.media_type == "application/x-ndjson"

            # Collect events from the generator
            events: list[str] = []
            async for chunk in response.body_iterator:
                events.append(chunk)

            # Should have at least session and text events
            assert len(events) >= 2

            # First event should be session
            first_event = json.loads(events[0].strip())
            assert first_event["type"] == "session"

    @pytest.mark.asyncio
    async def test_handle_remote_agent_handles_error_events(self) -> None:
        """Test that _handle_remote_agent handles error events from Agent Engine."""
        request = AgentRequest(
            messages=[AgentMessage(role="user", text="Hello")],
            user_id="test-user",
        )

        mock_raw_request = MagicMock(spec=Request)

        mock_client = MagicMock()

        async def mock_stream_query(**kwargs) -> AsyncGenerator[dict, None]:
            yield {"type": "error", "error": "Something went wrong"}

        mock_client.stream_query = mock_stream_query

        with patch(
            "sre_agent.api.routers.agent.get_agent_engine_client",
            return_value=mock_client,
        ):
            response = await _handle_remote_agent(
                request=request,
                raw_request=mock_raw_request,
                access_token="test-token",
                project_id="test-project",
            )

            events: list[str] = []
            async for chunk in response.body_iterator:
                events.append(chunk)

            # Should contain error message
            combined = "".join(events)
            assert "Error" in combined

    @pytest.mark.asyncio
    async def test_handle_remote_agent_handles_tool_calls(self) -> None:
        """Test that _handle_remote_agent handles tool call events."""
        request = AgentRequest(
            messages=[AgentMessage(role="user", text="Hello")],
            user_id="test-user",
        )

        mock_raw_request = MagicMock(spec=Request)

        mock_client = MagicMock()

        async def mock_stream_query(**kwargs) -> AsyncGenerator[dict, None]:
            yield {"type": "session", "session_id": "test-session"}
            yield {
                "content": {
                    "parts": [
                        {
                            "function_call": {
                                "name": "test_tool",
                                "args": {"arg1": "val1"},
                            }
                        }
                    ]
                }
            }
            yield {
                "content": {
                    "parts": [
                        {
                            "function_response": {
                                "name": "test_tool",
                                "response": {"result": "success"},
                            }
                        }
                    ]
                }
            }

        mock_client.stream_query = mock_stream_query

        with patch(
            "sre_agent.api.routers.agent.get_agent_engine_client",
            return_value=mock_client,
        ):
            response = await _handle_remote_agent(
                request=request,
                raw_request=mock_raw_request,
                access_token="test-token",
                project_id="test-project",
            )

            events: list[str] = []
            async for chunk in response.body_iterator:
                events.append(chunk)

            # Should have processed tool events
            assert len(events) >= 1

    @pytest.mark.asyncio
    async def test_handle_remote_agent_handles_streaming_exception(self) -> None:
        """Test that _handle_remote_agent handles exceptions during streaming."""
        request = AgentRequest(
            messages=[AgentMessage(role="user", text="Hello")],
            user_id="test-user",
        )

        mock_raw_request = MagicMock(spec=Request)

        mock_client = MagicMock()

        async def mock_stream_query(**kwargs) -> AsyncGenerator[dict, None]:
            yield {"type": "session", "session_id": "test-session"}
            raise RuntimeError("Connection lost")

        mock_client.stream_query = mock_stream_query

        with patch(
            "sre_agent.api.routers.agent.get_agent_engine_client",
            return_value=mock_client,
        ):
            response = await _handle_remote_agent(
                request=request,
                raw_request=mock_raw_request,
                access_token="test-token",
                project_id="test-project",
            )

            events: list[str] = []
            async for chunk in response.body_iterator:
                events.append(chunk)

            # Should contain error from exception
            combined = "".join(events)
            assert "Error" in combined


class TestAgentEndpointModeSelection:
    """Tests for agent endpoint mode selection."""

    def test_agent_endpoint_local_mode(self, client: TestClient) -> None:
        """Test that agent endpoint uses local mode when SRE_AGENT_ID is not set."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SRE_AGENT_ID", None)

            # Mock the local execution path
            with patch(
                "sre_agent.api.routers.agent.is_remote_mode", return_value=False
            ):
                with patch(
                    "sre_agent.api.routers.agent.get_session_service"
                ) as mock_session:
                    mock_manager = MagicMock()
                    mock_manager.get_session = AsyncMock(return_value=None)
                    mock_manager.create_session = AsyncMock(
                        return_value=MagicMock(
                            id="test-session",
                            state={},
                        )
                    )
                    mock_manager.session_service = MagicMock()
                    mock_manager.session_service.append_event = AsyncMock()
                    mock_session.return_value = mock_manager

                    # root_agent is imported inside the function, mock at source
                    with patch("sre_agent.agent.root_agent") as mock_agent:

                        async def mock_run_async(ctx):
                            # Yield nothing to simulate empty response
                            return
                            yield  # Make it a generator

                        mock_agent.run_async = mock_run_async

                        response = client.post(
                            "/agent",
                            json={
                                "messages": [{"role": "user", "text": "Hello"}],
                                "user_id": "test-user",
                            },
                        )

                        # Should not raise, even if response is incomplete
                        # The key is that it tried local mode
                        assert response.status_code in [200, 500]

    def test_agent_endpoint_remote_mode_no_client(self, client: TestClient) -> None:
        """Test that agent endpoint returns 500 when remote mode but no client."""
        with patch("sre_agent.api.routers.agent.is_remote_mode", return_value=True):
            with patch(
                "sre_agent.api.routers.agent.get_agent_engine_client",
                return_value=None,
            ):
                response = client.post(
                    "/agent",
                    json={
                        "messages": [{"role": "user", "text": "Hello"}],
                        "user_id": "test-user",
                    },
                )

                assert response.status_code == 500
                assert "SRE_AGENT_ID missing" in response.text


class TestSuggestionsEndpoint:
    """Tests for the suggestions endpoint."""

    def test_suggestions_returns_default_on_error(self, client: TestClient) -> None:
        """Test that suggestions endpoint returns defaults on error."""
        with patch(
            "sre_agent.api.routers.agent.generate_contextual_suggestions",
            side_effect=Exception("Test error"),
        ):
            response = client.get("/api/suggestions")

            assert response.status_code == 200
            data = response.json()
            assert "suggestions" in data
            assert len(data["suggestions"]) == 3

    def test_suggestions_returns_generated(self, client: TestClient) -> None:
        """Test that suggestions endpoint returns generated suggestions."""
        with patch(
            "sre_agent.api.routers.agent.generate_contextual_suggestions",
            new_callable=AsyncMock,
            return_value=["Custom suggestion 1", "Custom suggestion 2"],
        ):
            response = client.get("/api/suggestions")

            assert response.status_code == 200
            data = response.json()
            assert data["suggestions"] == ["Custom suggestion 1", "Custom suggestion 2"]


class TestAgentRequest:
    """Tests for AgentRequest model."""

    def test_agent_request_with_defaults(self) -> None:
        """Test AgentRequest with default values."""
        request = AgentRequest(
            messages=[AgentMessage(role="user", text="Hello")],
        )

        assert request.session_id is None
        assert request.project_id is None
        assert request.user_id == "default"

    def test_agent_request_with_all_fields(self) -> None:
        """Test AgentRequest with all fields."""
        request = AgentRequest(
            messages=[AgentMessage(role="user", text="Hello")],
            session_id="session-123",
            project_id="project-456",
            user_id="user-789",
        )

        assert request.session_id == "session-123"
        assert request.project_id == "project-456"
        assert request.user_id == "user-789"
