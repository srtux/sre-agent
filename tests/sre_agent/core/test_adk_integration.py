"""Integration tests for ADK compatibility."""

from unittest.mock import MagicMock

import pytest
from google.adk.agents import InvocationContext, LlmAgent, RunConfig
from google.adk.sessions import Session

from sre_agent.core.runner import Runner


class TestAdkIntegration:
    """Verify that Runner constructs ADK objects correctly."""

    @pytest.mark.asyncio
    async def test_runner_constructs_valid_context(self):
        """Test that Runner creates a valid InvocationContext with RunConfig."""
        # Setup
        # We must use a real LlmAgent to satisfy validation, but we can't easily mock its instance methods
        # because Pydantic models behave differently.
        # Instead, we patch the class method on BaseAgent (where run_async is defined)

        agent = LlmAgent(name="test_agent", model="test_model")

        async def _events(*args, **kwargs):
            yield MagicMock()

        # Patch BaseAgent.run_async which LlmAgent inherits appropriately
        import unittest.mock

        from google.adk.agents.base_agent import BaseAgent

        with unittest.mock.patch.object(
            BaseAgent, "run_async", side_effect=_events
        ) as mock_run_async:
            runner = Runner(agent=agent)

            # Use REAL Session
            session = Session(
                app_name="test_app", user_id="test_user", id="test_session"
            )

            runner.policy_engine = MagicMock()
            decision = MagicMock()
            decision.allowed = True
            decision.requires_approval = False
            runner.policy_engine.evaluate.return_value = decision

            # Execute
            events = []
            async for event in runner.run_turn(
                session=session,
                user_message="Hello",
                user_id="test-user",
                project_id="test-project",
            ):
                events.append(event)

            # Verification
            mock_run_async.assert_called_once()
            call_args = mock_run_async.call_args
            inv_ctx = call_args[0][0]

            assert isinstance(inv_ctx, InvocationContext)
            # CRITICAL CHECK: ensure run_config is present and not None
            assert inv_ctx.run_config is not None
            assert isinstance(inv_ctx.run_config, RunConfig)
