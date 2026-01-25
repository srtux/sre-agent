"""Unit tests for RunnerAgentAdapter."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from google.adk.events import Event
from google.genai import types

from sre_agent.auth import SESSION_STATE_PROJECT_ID_KEY
from sre_agent.core.runner import Runner
from sre_agent.core.runner_adapter import RunnerAgentAdapter


class TestRunnerAgentAdapter:
    @pytest.mark.asyncio
    async def test_run_async_delegation(self):
        """Test that run_async delegates correctly to runner.run_turn."""
        # 1. Mock Runner
        mock_runner = MagicMock(spec=Runner)
        mock_runner.run_turn = AsyncMock()

        async def _events(*args, **kwargs):
            yield Event(
                invocation_id="1",
                author="model",
                content=types.Content(parts=[types.Part.from_text(text="Response")]),
            )

        mock_runner.run_turn = _events

        # 2. Create Adapter
        adapter = RunnerAgentAdapter(mock_runner)

        # 3. Create Mock Context
        mock_context = MagicMock()
        mock_session = MagicMock()
        mock_session.user_id = "test-user"
        mock_session.state = {
            SESSION_STATE_PROJECT_ID_KEY: "my-project",
            "investigation_state": {"phase": "triage"},
        }
        mock_context.session = mock_session

        # User content
        mock_context.user_content.parts = [MagicMock(text="Help me")]

        # 4. Run
        events = []
        async for event in adapter.run_async(mock_context):
            events.append(event)

        # 5. Verify
        assert len(events) == 1
        # Since run_turn is a real function (not MagicMock) we can't assert calls
        event = events[0]
        assert event.content.parts[0].text == "Response"
