from unittest.mock import MagicMock

import pytest
from google.adk.events import Event
from google.genai import types

from sre_agent.core.policy_engine import PolicyDecision, ToolAccessLevel
from sre_agent.core.runner import ExecutionContext, Runner, RunnerConfig


@pytest.mark.asyncio
async def test_intercept_tool_calls_yields_rejection_and_response():
    """Test that _intercept_tool_calls yields both rejection and dummy response when disallowed."""
    # Setup mocks
    agent = MagicMock()
    policy_engine = MagicMock()
    runner = Runner(agent=agent, config=RunnerConfig(enforce_policy=True))
    runner.policy_engine = policy_engine

    # Mock a policy rejection
    policy_engine.evaluate.return_value = PolicyDecision(
        allowed=False,
        reason="Testing rejection",
        tool_name="test_tool",
        access_level=ToolAccessLevel.READ_ONLY,
    )

    # Create a mock function call event
    func_call = types.FunctionCall(name="test_tool", id="call_123", args={"arg": 1})
    event = Event(
        invocation_id="inv_123",
        author="model",
        content=types.Content(
            role="model", parts=[types.Part(function_call=func_call)]
        ),
    )

    exec_ctx = ExecutionContext(
        session_id="sess_123",
        user_id="user1",
        project_id="proj1",
        turn_number=1,
        start_time=123.0,
    )

    # Execute interception
    yielded_events = []
    async for e in runner._intercept_tool_calls(event, exec_ctx):
        yielded_events.append(e)

    # Should yield 3 events: Original Call + Rejection message + Dummy Response
    assert len(yielded_events) == 3

    # 1. Original Event (Tool Call)
    assert yielded_events[0] == event

    # 2. Rejection Event (System message)
    assert yielded_events[1].author == "system"
    assert "Policy Rejection" in yielded_events[1].content.parts[0].text

    # 3. Dummy Response Event (User message to satisfy ADK history)
    assert yielded_events[2].author == "system"
    parts = yielded_events[2].content.parts
    assert len(parts) == 1
    assert parts[0].function_response is not None
    assert parts[0].function_response.name == "test_tool"
    assert parts[0].function_response.id == "call_123"
    assert parts[0].function_response.response["status"] == "error"


@pytest.mark.asyncio
async def test_intercept_tool_calls_yields_original_if_allowed():
    """Test that _intercept_tool_calls yields the original event if allowed."""
    agent = MagicMock()
    policy_engine = MagicMock()
    runner = Runner(agent=agent, config=RunnerConfig(enforce_policy=True))
    runner.policy_engine = policy_engine

    policy_engine.evaluate.return_value = PolicyDecision(
        allowed=True,
        tool_name="test_tool",
        reason="Allowed",
        access_level=ToolAccessLevel.READ_ONLY,
    )

    func_call = types.FunctionCall(name="test_tool", id="call_123")
    event = Event(
        invocation_id="inv_123",
        author="model",
        content=types.Content(parts=[types.Part(function_call=func_call)]),
    )

    exec_ctx = ExecutionContext(
        session_id="sess_123",
        user_id="user1",
        project_id="proj1",
        turn_number=1,
        start_time=123.0,
    )

    yielded_events = []
    async for e in runner._intercept_tool_calls(event, exec_ctx):
        yielded_events.append(e)

    assert len(yielded_events) == 1
    assert yielded_events[0] == event

    yielded_events = []
    async for e in runner._intercept_tool_calls(event, exec_ctx):
        yielded_events.append(e)

    assert len(yielded_events) == 1
    assert yielded_events[0] == event
