"""Tests for the Stateless Execution Runner."""

from unittest.mock import MagicMock, patch

import pytest
from google.adk.events import Event
from google.adk.sessions import Session
from google.genai import types

from sre_agent.core.approval import ApprovalManager, HumanApprovalRequest
from sre_agent.core.context_compactor import (
    ContextCompactor,
    SessionSummary,
    WorkingContext,
)
from sre_agent.core.policy_engine import PolicyDecision, PolicyEngine, ToolAccessLevel
from sre_agent.core.prompt_composer import PromptComposer
from sre_agent.core.runner import Runner, RunnerConfig, create_runner


@pytest.fixture
def mock_agent():
    """Mock LLM agent."""
    agent = MagicMock()

    # Mock run_async to return an async generator
    async def _async_gen(*args, **kwargs):
        yield MagicMock(spec=Event)

    agent.run_async.side_effect = _async_gen
    return agent


@pytest.fixture
def mock_policy_engine():
    """Mock policy engine."""
    engine = MagicMock(spec=PolicyEngine)
    engine.evaluate.return_value = PolicyDecision(
        tool_name="test_tool",
        allowed=True,
        requires_approval=False,
        reason="Test reason",
        access_level=ToolAccessLevel.READ_ONLY,
    )
    return engine


@pytest.fixture
def mock_context_compactor():
    """Mock context compactor."""
    compactor = MagicMock(spec=ContextCompactor)
    compactor.get_working_context.return_value = WorkingContext(
        summary=SessionSummary(summary_text="Test summary"),
        recent_events=[],
    )
    return compactor


@pytest.fixture
def mock_prompt_composer():
    """Mock prompt composer."""
    return MagicMock(spec=PromptComposer)


@pytest.fixture
def mock_approval_manager():
    """Mock approval manager."""
    manager = MagicMock(spec=ApprovalManager)
    manager.get_pending_requests.return_value = []
    manager.create_request.return_value = HumanApprovalRequest(
        request_id="req-123",
        tool_name="test_tool",
        tool_args={},
        reason="test reason",
        risk_assessment="test risk",
        session_id="session-123",
        user_id="user-123",
        created_at="2024-01-01T00:00:00Z",
    )
    return manager


@pytest.fixture
def runner(
    mock_agent,
    mock_policy_engine,
    mock_context_compactor,
    mock_prompt_composer,
    mock_approval_manager,
):
    """Create a Runner instance with mocks."""
    config = RunnerConfig(enforce_policy=True)
    return Runner(
        agent=mock_agent,
        config=config,
        policy_engine=mock_policy_engine,
        context_compactor=mock_context_compactor,
        prompt_composer=mock_prompt_composer,
        approval_manager=mock_approval_manager,
    )


@pytest.fixture
def session():
    """Create a mock ADK session."""
    session = MagicMock(spec=Session)
    session.id = "session-123"
    session.events = []
    return session


class TestRunner:
    """Tests for the Runner class."""

    def test_initialization(self, mock_agent):
        """Test runner initialization."""
        runner = create_runner(mock_agent)
        assert isinstance(runner, Runner)
        assert runner.agent == mock_agent
        assert isinstance(runner.config, RunnerConfig)

    @pytest.mark.asyncio
    async def test_run_turn_basic_flow(self, runner, session):
        """Test basic run_turn flow."""
        # Setup mock agent to yield one event
        event = Event(
            invocation_id="inv-123",
            author="model",
            content=types.Content(
                role="model", parts=[types.Part.from_text(text="Hello")]
            ),
        )

        async def _mock_run(*args, **kwargs):
            yield event

        runner.agent.run_async.side_effect = _mock_run

        # Patch InvocationContext to avoid validation errors
        with patch("google.adk.agents.InvocationContext"):
            # Run turn
            events = []
            async for e in runner.run_turn(
                session=session,
                user_message="Hi",
                user_id="user-123",
            ):
                events.append(e)

        # Verify
        assert len(events) == 1
        assert events[0].content == event.content
        assert events[0].author == event.author
        runner.context_compactor.get_working_context.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_turn_with_pending_approval(
        self, runner, session, mock_approval_manager
    ):
        """Test run_turn returns pending approval event if requests exist."""
        # Setup pending request
        mock_approval_manager.get_pending_requests.return_value = [
            HumanApprovalRequest(
                request_id="req-123",
                tool_name="test_tool",
                tool_args={},
                reason="test reason",
                risk_assessment="test risk",
                session_id="session-123",
                user_id="user-123",
                created_at="2024-01-01T00:00:00Z",
            )
        ]

        # Run turn
        events = []
        async for e in runner.run_turn(
            session=session,
            user_message="Hi",
            user_id="user-123",
        ):
            events.append(e)

        # Verify
        assert len(events) == 1
        content = events[0].content.parts[0].text
        assert "Pending Approvals" in content
        assert "test_tool" in content

        # Agent should NOT have been called
        runner.agent.run_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_policy_rejection(self, runner, session, mock_policy_engine):
        """Test policy rejection event."""
        # Setup policy rejection
        mock_policy_engine.evaluate.return_value = PolicyDecision(
            tool_name="dangerous_tool",
            allowed=False,
            reason="Too dangerous",
            access_level=ToolAccessLevel.ADMIN,
        )

        # Setup event with tool call
        tool_call_event = Event(
            invocation_id="inv-123",
            author="model",
            content=types.Content(
                role="model",
                parts=[
                    types.Part.from_function_call(
                        name="dangerous_tool", args={"arg": "val"}
                    )
                ],
            ),
        )

        async def _mock_run(*args, **kwargs):
            yield tool_call_event

        runner.agent.run_async.side_effect = _mock_run

        with patch("google.adk.agents.InvocationContext"):
            # Run turn
            events = []
            async for e in runner.run_turn(
                session=session,
                user_message="Do something dangerous",
                user_id="user-123",
            ):
                events.append(e)

        # Verify: Should yield 3 events (Original Call + Rejection + Dummy Response)
        assert len(events) == 3
        # First event should be the original tool call
        assert events[0].content == tool_call_event.content

        # Second event should be the rejection message
        content = events[1].content.parts[0].text
        assert "Policy Rejection" in content
        assert "Too dangerous" in content

        # Verify dummy response
        parts = events[2].content.parts
        assert len(parts) == 1
        assert parts[0].function_response is not None
        assert parts[0].function_response.name == "dangerous_tool"
        assert parts[0].function_response.response["status"] == "error"

    @pytest.mark.asyncio
    async def test_approval_request_creation(self, runner, session, mock_policy_engine):
        """Test creation of approval request when policy requires it."""
        # Setup policy requiring approval
        mock_policy_engine.evaluate.return_value = PolicyDecision(
            tool_name="sensitive_tool",
            allowed=True,
            requires_approval=True,
            reason="Sensitive operation",
            access_level=ToolAccessLevel.WRITE,
            risk_assessment="High risk",
        )

        # Setup event with tool call
        tool_call_event = Event(
            invocation_id="inv-123",
            author="model",
            content=types.Content(
                role="model",
                parts=[
                    types.Part.from_function_call(
                        name="sensitive_tool", args={"arg": "val"}
                    )
                ],
            ),
        )

        async def _mock_run(*args, **kwargs):
            yield tool_call_event

        runner.agent.run_async.side_effect = _mock_run

        with patch("google.adk.agents.InvocationContext"):
            # Run turn
            events = []
            async for e in runner.run_turn(
                session=session,
                user_message="Do something sensitive",
                user_id="user-123",
            ):
                events.append(e)

        # Verify: Should yield 2 events (Original Call + Approval Request)
        assert len(events) == 2
        assert events[0].content == tool_call_event.content

        content = events[1].content.parts[0].text
        assert "Human Approval Required" in content
        assert "High risk" in content
        # Verify action state delta
        assert events[1].actions is not None
        assert "pending_approval" in events[1].actions.state_delta

    @pytest.mark.asyncio
    async def test_execution_context_tracking(self, runner, session):
        """Test that execution context is tracked correctly."""

        async def _mock_run(*args, **kwargs):
            # Verify context is set during execution
            assert session.id in runner._active_executions
            ctx = runner._active_executions[session.id]
            assert ctx.user_id == "user-123"
            yield Event(invocation_id="1", author="model")

        runner.agent.run_async.side_effect = _mock_run

        with patch("google.adk.agents.InvocationContext"):
            async for _ in runner.run_turn(
                session=session,
                user_message="Hi",
                user_id="user-123",
            ):
                pass

        # Verify context is cleaned up
        assert session.id not in runner._active_executions

    @pytest.mark.asyncio
    async def test_error_handling(self, runner, session):
        """Test error handling during execution."""
        runner.agent.run_async.side_effect = Exception("Test failure")

        with patch("google.adk.agents.InvocationContext"):
            events = []
            async for e in runner.run_turn(
                session=session,
                user_message="Hi",
                user_id="user-123",
            ):
                events.append(e)

        assert len(events) == 1
        content = events[0].content.parts[0].text
        assert "Error: Agent error: Test failure" in content
