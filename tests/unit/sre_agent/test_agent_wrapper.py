from unittest.mock import MagicMock

import pytest
from google.adk.agents import LlmAgent

from sre_agent.agent import emojify_agent


class TestEmojifyAgentWrapper:
    @pytest.mark.asyncio
    async def test_run_async_with_no_session(self):
        """Test that wrapped agent handles missing session/state without crashing.

        Regression test for UnboundLocalError: local variable 'remote_trace_id' referenced before assignment.
        """
        # 1. Mock the underlying agent
        mock_agent = MagicMock(spec=LlmAgent)
        mock_agent.name = "TestAgent"
        mock_agent.model = MagicMock()

        # Mock run_async to yield a simple response
        async def mock_run_async(context):
            yield MagicMock(content=MagicMock(parts=[MagicMock(text="Response")]))

        mock_agent.run_async = mock_run_async

        # 2. Wrap the agent
        wrapped_agent = emojify_agent(mock_agent)

        # 3. Create context with NO session
        mock_context = MagicMock()
        mock_context.session = None
        mock_context.user_content = MagicMock()

        # 4. Run calls - this should NOT crash
        events = []
        async for event in wrapped_agent.run_async(mock_context):
            events.append(event)

        assert len(events) == 1

    @pytest.mark.asyncio
    async def test_run_async_with_empty_session_state(self):
        """Test that wrapped agent handles empty session state without crashing."""
        # 1. Mock the underlying agent
        mock_agent = MagicMock(spec=LlmAgent)
        mock_agent.name = "TestAgent"
        mock_agent.model = MagicMock()

        async def mock_run_async(context):
            yield MagicMock(content=MagicMock(parts=[MagicMock(text="Response")]))

        mock_agent.run_async = mock_run_async

        # 2. Wrap the agent
        wrapped_agent = emojify_agent(mock_agent)

        # 3. Create context with empty session state
        mock_context = MagicMock()
        mock_context.session = MagicMock()
        mock_context.session.state = None

        # Handle dict access for session if code checks that
        # (The code checks hasattr(context.session, "state"))

        # 4. Run calls - this should NOT crash
        events = []
        async for event in wrapped_agent.run_async(mock_context):
            events.append(event)

        assert len(events) == 1
