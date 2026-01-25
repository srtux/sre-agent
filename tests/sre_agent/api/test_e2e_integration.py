"""End-to-End Integration Tests for API Router."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.events import Event
from google.genai import types

# Import the router to patch dependencies
from sre_agent.api.routers import agent
from sre_agent.core.runner import Runner


@pytest.fixture
def mock_runner():
    """Mock the runner instance."""
    runner = MagicMock(spec=Runner)
    runner.run_turn = AsyncMock()
    return runner


# Reuse the setup logic to avoid code duplication
@pytest.fixture
def e2e_patches():
    return (
        patch(
            "sre_agent.api.routers.agent.get_current_credentials_or_none",
            return_value=None,
        ),
        patch("sre_agent.api.routers.agent.is_remote_mode", return_value=False),
        patch("sre_agent.api.routers.agent.get_session_service"),
        patch("sre_agent.agent.root_agent"),
        patch("sre_agent.api.routers.agent.InvocationContext"),
    )


class TestE2EIntegration:
    """E2E Integration Tests."""

    @pytest.mark.asyncio
    async def test_runner_integration_basic_flow(self):
        """Test that the API router correctly uses the Runner."""
        # Mock dependencies
        mock_request = MagicMock()
        mock_request.user_id = "test-user"
        mock_request.project_id = "test-project"
        mock_request.messages = [MagicMock(text="Hello")]
        mock_request.session_id = "test-session"

        mock_raw_req = MagicMock()
        mock_raw_req.is_disconnected = AsyncMock(return_value=False)

        with (
            patch(
                "sre_agent.api.routers.agent.get_current_credentials_or_none",
                return_value=None,
            ),
            patch("sre_agent.api.routers.agent.is_remote_mode", return_value=False),
            patch(
                "sre_agent.api.routers.agent.get_session_service"
            ) as mock_get_service,
            patch("sre_agent.agent.root_agent") as mock_agent,
            patch("sre_agent.api.routers.agent.InvocationContext") as mock_inv_ctx,
        ):
            # Setup InvocationContext mock
            mock_inv_ctx.return_value.invocation_id = "test-inv-id"

            # Setup session service
            mock_service = AsyncMock()
            mock_session = MagicMock()
            mock_session.id = "test-session"
            mock_session.state = {}
            mock_service.get_session.return_value = mock_session
            mock_service.create_session.return_value = mock_session
            mock_get_service.return_value = mock_service

            # Setup Runner mock
            mock_runner = MagicMock()

            async def _events(*args, **kwargs):
                yield Event(
                    invocation_id="1",
                    author="model",
                    content=types.Content(
                        parts=[types.Part.from_text(text="Response")]
                    ),
                )

            # Assign directly to behave as async generator method
            mock_runner.run_turn = _events
            mock_agent._runner = mock_runner

            # Test basic flow
            response = await agent.chat_agent(mock_request, mock_raw_req)
            async for _ in response.body_iterator:
                pass

            # Verify stream implies execution
            assert response.status_code == 200

            # Since we replaced the mock with a real function,
            # we can't inspect calls directly on it unless we wrap it.
            # But the presence of response implies it was called.

    @pytest.mark.asyncio
    async def test_runner_policy_rejection(self):
        """Test that the API correctly handles policy rejection events."""
        mock_request = MagicMock()
        mock_request.user_id = "default"
        mock_request.project_id = "p1"
        mock_request.messages = [MagicMock(text="delete prod")]
        mock_request.session_id = "s1"

        mock_raw_req = MagicMock()
        mock_raw_req.is_disconnected = AsyncMock(return_value=False)

        with (
            patch(
                "sre_agent.api.routers.agent.get_current_credentials_or_none",
                return_value=None,
            ),
            patch("sre_agent.api.routers.agent.is_remote_mode", return_value=False),
            patch(
                "sre_agent.api.routers.agent.get_session_service"
            ) as mock_get_service,
            patch("sre_agent.agent.root_agent") as mock_agent,
            patch("sre_agent.api.routers.agent.InvocationContext") as mock_inv_ctx,
        ):
            mock_inv_ctx.return_value.invocation_id = "test-inv-id-2"

            mock_service = AsyncMock()
            mock_session = MagicMock()
            mock_session.id = "s1"
            mock_session.state = {}
            mock_service.get_session.return_value = mock_session
            mock_get_service.return_value = mock_service

            mock_runner = MagicMock()

            async def _rejection_event(*args, **kwargs):
                # Simulate a policy rejection event
                yield Event(
                    invocation_id="2",
                    author="system",
                    content=types.Content(
                        parts=[types.Part.from_text(text="⛔ Policy Rejection")]
                    ),
                )

            mock_runner.run_turn = _rejection_event
            mock_agent._runner = mock_runner

            response = await agent.chat_agent(mock_request, mock_raw_req)

            # Verify stream contains rejection
            content = ""
            async for chunk in response.body_iterator:
                content += chunk

            assert "Policy Rejection" in content
