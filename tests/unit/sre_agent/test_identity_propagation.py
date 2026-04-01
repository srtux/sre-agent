from unittest.mock import MagicMock, patch

import pytest

from sre_agent.auth import (
    SESSION_STATE_ACCESS_TOKEN_KEY,
    SESSION_STATE_SPAN_ID_KEY,
    SESSION_STATE_TRACE_ID_KEY,
    _credentials_context,
    _trace_id_context,
    get_current_credentials_or_none,
    get_trace_id,
)
from sre_agent.tools.common.decorators import adk_tool


@pytest.fixture(autouse=True)
def reset_contexts():
    """Reset ContextVars before each test."""
    _credentials_context.set(None)
    _trace_id_context.set(None)
    yield
    _credentials_context.set(None)
    _trace_id_context.set(None)


@adk_tool
async def mock_tool(arg: str, tool_context: MagicMock | None = None):
    """A mock tool to test identity propagation."""
    return {
        "arg": arg,
        "current_trace_id": get_trace_id(),
        "current_creds_token": getattr(
            get_current_credentials_or_none(), "token", None
        ),
    }


@pytest.mark.anyio
async def test_identity_propagation_decorator():
    """Verify that @adk_tool propagates identity from tool_context."""
    # Setup mock tool context with session state
    mock_tool_context = MagicMock()
    mock_tool_context.invocation_context.session.state = {
        SESSION_STATE_ACCESS_TOKEN_KEY: "test-token-123",
        SESSION_STATE_TRACE_ID_KEY: "test-trace-id-456",
    }

    # Execute tool
    result = await mock_tool("hello", tool_context=mock_tool_context)

    # Verify context was propagated INSIDE the tool
    assert result["current_trace_id"] == "test-trace-id-456"
    assert result["current_creds_token"] == "test-token-123"

    # Verify context was reset OUTSIDE the tool
    assert get_trace_id() is None
    assert get_current_credentials_or_none() is None


@pytest.mark.anyio
async def test_identity_propagation_to_factory():
    """Verify that clients from factory use the propagated identity."""
    from sre_agent.auth import GLOBAL_CONTEXT_CREDENTIALS
    from sre_agent.tools.clients.factory import get_trace_client

    # Setup mock tool context
    mock_tool_context = MagicMock()
    mock_tool_context.invocation_context.session.state = {
        SESSION_STATE_ACCESS_TOKEN_KEY: "factory-token",
    }

    @adk_tool
    async def tool_using_factory(tool_context: MagicMock | None = None):
        client = get_trace_client()
        # The client library transport credentials will be GLOBAL_CONTEXT_CREDENTIALS
        # and we verify it resolves to the session token.
        return client.transport.credentials.token

    # We need to mock TraceServiceClient to avoid actual API calls during instantiation
    with patch("google.cloud.trace_v1.TraceServiceClient") as mock_client_cls:
        # Configure the mock instance to have a transport with credentials
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance

        # When get_trace_client() is called, it initializes with credentials=GLOBAL_CONTEXT_CREDENTIALS
        # and returns the mock_instance.
        # We simulate the transport credentials.
        mock_instance.transport.credentials = GLOBAL_CONTEXT_CREDENTIALS

        token = await tool_using_factory(tool_context=mock_tool_context)

        assert token == "factory-token"


@pytest.mark.anyio
async def test_otel_rehydration():
    """Verify that OTel context is rehydrated from trace ID."""
    from opentelemetry import trace

    mock_tool_context = MagicMock()
    # Trace ID must be 32 chars hex for OTel
    trace_id_hex = "1234567890abcdef1234567890abcdef"
    span_id_hex = "1234567890abcdef"
    mock_tool_context.invocation_context.session.state = {
        SESSION_STATE_TRACE_ID_KEY: trace_id_hex,
        SESSION_STATE_SPAN_ID_KEY: span_id_hex,
        SESSION_STATE_ACCESS_TOKEN_KEY: "token",
    }

    @adk_tool
    async def tool_checking_otel(tool_context: MagicMock | None = None):
        current_span = trace.get_current_span()
        span_ctx = current_span.get_span_context()
        if span_ctx.is_valid:
            return trace.format_trace_id(span_ctx.trace_id)
        return f"INVALID_SPAN: {span_ctx}"

    # We use a clean OTel context for this test
    from opentelemetry import context

    # Clear any existing context
    token = context.attach(context.Context())
    try:
        result_trace_id = await tool_checking_otel(tool_context=mock_tool_context)
        assert result_trace_id == trace_id_hex
    finally:
        context.detach(token)
