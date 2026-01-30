"""Tests for emojify_agent prompt-response logging.

Verifies that prompt and response logging is always emitted regardless of
environment (local vs Agent Engine).
"""

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture()
def _mock_agent_deps():
    """Patch heavy imports that agent.py pulls in at module level."""
    # We only need the emojify_agent function, so patch out the heavy deps
    # that would otherwise require real GCP credentials / Vertex SDK.
    with (
        patch("sre_agent.agent.get_current_project_id", return_value="test-project"),
        patch("sre_agent.agent._inject_global_credentials", return_value=None),
        patch("sre_agent.agent.get_credentials_from_session", return_value=None),
        patch("sre_agent.agent.get_project_id_from_session", return_value=None),
    ):
        yield


def _make_fake_agent(response_text: str = "I found the issue.") -> Any:
    """Create a minimal fake LlmAgent-like object for testing emojify_agent."""
    from google.adk.agents import LlmAgent

    # Build a fake event with content.parts[0].text
    part = SimpleNamespace(text=response_text)
    content = SimpleNamespace(parts=[part])
    event = SimpleNamespace(content=content)

    async def fake_run_async(context: Any):  # type: ignore[no-untyped-def]
        yield event

    agent = MagicMock(spec=LlmAgent)
    agent.name = "test_agent"
    agent.model = "gemini-2.5-flash"
    agent.run_async = fake_run_async
    return agent


def _make_context(prompt: str = "Why is latency high?") -> Any:
    """Create a minimal invocation context with user_content."""
    part = SimpleNamespace(text=prompt)
    user_content = SimpleNamespace(parts=[part])
    session = SimpleNamespace(id="sess-123", state=None)
    return SimpleNamespace(
        user_content=user_content,
        session=session,
        message=None,
        user_id="testuser@example.com",
    )


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_agent_deps")
async def test_emojify_logs_prompt_and_response():
    """emojify_agent always logs prompt and response."""
    from sre_agent.agent import emojify_agent

    agent = _make_fake_agent("Root cause: database connection pool exhaustion.")
    wrapped = emojify_agent(agent)

    context = _make_context("Investigate high latency on checkout service")

    with patch("sre_agent.agent.logger") as mock_logger:
        events = []
        async for ev in wrapped.run_async(context):
            events.append(ev)

        # Verify prompt was logged
        prompt_calls = [
            c
            for c in mock_logger.info.call_args_list
            if "Incoming user request" in str(c)
        ]
        assert len(prompt_calls) == 1, "Expected exactly one prompt log entry"
        prompt_log = str(prompt_calls[0])
        assert "Investigate high latency" in prompt_log

        # Verify response was logged
        response_calls = [
            c
            for c in mock_logger.info.call_args_list
            if "Agent response" in str(c)
        ]
        assert len(response_calls) == 1, "Expected exactly one response log entry"
        response_log = str(response_calls[0])
        assert "database connection pool" in response_log


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_agent_deps")
async def test_emojify_logs_in_agent_engine_env():
    """Prompt/response logging works even with RUNNING_IN_AGENT_ENGINE=true.

    This is a regression test for the bug where setting
    RUNNING_IN_AGENT_ENGINE or OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT
    suppressed all prompt-response logging.
    """
    import os
    from unittest.mock import patch as mock_patch

    from sre_agent.agent import emojify_agent

    agent = _make_fake_agent("The fix is to increase pool size.")
    # Wrap the agent fresh (emojify_agent is evaluated at call time)
    wrapped = emojify_agent(agent)

    context = _make_context("What is the root cause?")

    env_overrides = {
        "RUNNING_IN_AGENT_ENGINE": "true",
        "OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "true",
    }
    with (
        mock_patch.dict(os.environ, env_overrides, clear=False),
        mock_patch("sre_agent.agent.logger") as mock_logger,
    ):
        async for _ in wrapped.run_async(context):
            pass

        # Must still log prompt
        prompt_calls = [
            c
            for c in mock_logger.info.call_args_list
            if "Incoming user request" in str(c)
        ]
        assert len(prompt_calls) == 1, (
            "Prompt logging must NOT be suppressed in Agent Engine"
        )

        # Must still log response
        response_calls = [
            c
            for c in mock_logger.info.call_args_list
            if "Agent response" in str(c)
        ]
        assert len(response_calls) == 1, (
            "Response logging must NOT be suppressed in Agent Engine"
        )


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_agent_deps")
async def test_emojify_truncates_long_prompt():
    """Prompts longer than 500 chars are truncated in the log."""
    from sre_agent.agent import emojify_agent

    agent = _make_fake_agent("ok")
    wrapped = emojify_agent(agent)

    long_prompt = "x" * 1000
    context = _make_context(long_prompt)

    with patch("sre_agent.agent.logger") as mock_logger:
        async for _ in wrapped.run_async(context):
            pass

        prompt_calls = [
            c
            for c in mock_logger.info.call_args_list
            if "Incoming user request" in str(c)
        ]
        assert len(prompt_calls) == 1
        # The logged prompt should be at most 500 chars
        logged_args = prompt_calls[0]
        # The 4th positional arg (index 3) is the prompt text
        logged_prompt = logged_args[0][4] if len(logged_args[0]) > 4 else str(logged_args)
        assert len(str(logged_prompt)) <= 500


@pytest.mark.asyncio
@pytest.mark.usefixtures("_mock_agent_deps")
async def test_emojify_no_response_log_when_empty():
    """No response log is emitted when the agent returns no text."""
    from sre_agent.agent import emojify_agent

    # Agent that yields event with no text content
    empty_part = SimpleNamespace(text=None)
    empty_content = SimpleNamespace(parts=[empty_part])
    empty_event = SimpleNamespace(content=empty_content)

    agent = MagicMock()
    agent.name = "test_agent"
    agent.model = "gemini-2.5-flash"

    async def no_text_run_async(context: Any):  # type: ignore[no-untyped-def]
        yield empty_event

    agent.run_async = no_text_run_async

    wrapped = emojify_agent(agent)
    context = _make_context("hello")

    with patch("sre_agent.agent.logger") as mock_logger:
        async for _ in wrapped.run_async(context):
            pass

        response_calls = [
            c
            for c in mock_logger.info.call_args_list
            if "Agent response" in str(c)
        ]
        assert len(response_calls) == 0, "Should not log empty response"
