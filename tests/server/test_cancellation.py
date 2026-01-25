import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure we can import server
sys.path.append(os.getcwd())


class TestStopButtonCancellation(unittest.IsolatedAsyncioTestCase):
    async def test_backend_cancellation(self):
        """
        Verify that:
        1. genui_chat starts a stream.
        2. When raw_request.is_disconnected() returns True, the agent loop is cancelled.
        """
        from starlette.requests import Request

        from sre_agent.api.routers.agent import AgentMessage as ChatMessage
        from sre_agent.api.routers.agent import AgentRequest as ChatRequest
        from sre_agent.api.routers.agent import chat_agent as genui_chat

        # Mock Request
        mock_raw_request = MagicMock(spec=Request)
        mock_raw_request.is_disconnected = AsyncMock(return_value=False)

        # Mock Session Service
        with (
            patch(
                "sre_agent.api.routers.agent.get_session_service"
            ) as mock_get_session_service,
            patch("sre_agent.agent.root_agent") as mock_root_agent,
            patch(
                "sre_agent.api.routers.agent.InvocationContext"
            ) as mock_inv_ctx_class,
            patch("sre_agent.api.routers.agent.RunConfig") as _mock_run_config_class,
            patch("sre_agent.api.routers.agent.Event") as _mock_event_class,
            patch("sre_agent.api.routers.agent.Content") as _mock_content_class,
            patch("sre_agent.api.routers.agent.Part") as _mock_part_class,
        ):
            # Setup Session
            mock_session = MagicMock()
            mock_session.id = "test-session-id"
            mock_session.events = []
            mock_session_service = AsyncMock()
            mock_session_service.get_session.return_value = mock_session
            mock_session_service.create_session.return_value = mock_session
            mock_session_service.session_service = AsyncMock()
            mock_get_session_service.return_value = mock_session_service

            # Setup InvocationContext instance
            mock_inv_ctx = MagicMock()
            mock_inv_ctx.invocation_id = "test-inv-id"
            mock_inv_ctx_class.return_value = mock_inv_ctx

            # --- AGENT MOCK ---
            agent_cancelled_event = asyncio.Event()

            async def slow_agent_run(inv_ctx):
                try:
                    while True:
                        yield MagicMock()
                        # Sleep long enough to allow disconnect_checker (which sleeps 0.1s)
                        # to run and detect disconnection.
                        await asyncio.sleep(0.5)
                except asyncio.CancelledError:
                    agent_cancelled_event.set()
                    raise

            mock_root_agent.run_async = slow_agent_run

            # --- REQUEST MOCK ---
            chat_req = ChatRequest(
                messages=[ChatMessage(role="user", text="start")], project_id="p"
            )

            # --- CLIENT DISCONNECT SIMULATION ---
            # Return False a few times, then True to simulate disconnect
            is_disconnected_responses = [False, False, True]

            async def side_effect_is_disconnected():
                if is_disconnected_responses:
                    return is_disconnected_responses.pop(0)
                return True

            mock_raw_request.is_disconnected.side_effect = side_effect_is_disconnected

            # Call Endpoint
            response = await genui_chat(chat_req, mock_raw_request)
            iterator = response.body_iterator

            # Consume stream
            try:
                async for _item in iterator:
                    # Force yield to event loop to allow background tasks to run
                    await asyncio.sleep(0)
                    pass
            except asyncio.CancelledError:
                pass
            except Exception as e:
                # server.py handles internal exceptions, but CancelledError is re-raised
                if "Client disconnected" not in str(e):
                    print(f"Unexpected exception during stream consumption: {e}")

            # Verify Agent Cancellation
            try:
                await asyncio.wait_for(agent_cancelled_event.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.fail("FAILURE: Agent task was NOT cancelled within timeout.")


if __name__ == "__main__":
    unittest.main()
