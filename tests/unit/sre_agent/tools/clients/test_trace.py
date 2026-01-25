"""
Goal: Verify the Cloud Trace client correctly fetches and processes distributed traces.
Patterns: Cloud Trace API Mocking, Trace Waterfall Transformation.
"""

from unittest.mock import MagicMock, patch

import pytest

from sre_agent.tools.clients.trace import fetch_trace, list_traces


@pytest.fixture
def mock_trace_client():
    with patch("sre_agent.tools.clients.trace.get_trace_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.mark.asyncio
async def test_list_traces(mock_trace_client):
    mock_trace = MagicMock()
    mock_trace.trace_id = "trace-1"
    mock_trace.project_id = "test-proj"
    mock_trace.spans = []

    mock_trace_client.list_traces.return_value = [mock_trace]

    # Mock credentials in tool_context
    mock_context = MagicMock()
    mock_context.session_state = {"credentials": "fake"}

    with patch(
        "sre_agent.tools.clients.trace.get_credentials_from_tool_context"
    ) as mock_creds:
        mock_creds.return_value = "fake"
        result = await list_traces(project_id="test-proj", tool_context=mock_context)
        assert len(result) == 1
        assert result[0]["trace_id"] == "trace-1"


@pytest.mark.asyncio
async def test_fetch_trace(mock_trace_client):
    mock_trace = MagicMock()
    mock_trace.trace_id = "trace-1"
    mock_trace.project_id = "test-proj"

    mock_span = MagicMock()
    mock_span.span_id = "span-1"
    mock_span.name = "op1"
    # Create valid mock timestamps

    st = MagicMock()
    st.timestamp.return_value = 1000.0
    et = MagicMock()
    et.timestamp.return_value = 1001.0
    mock_span.start_time = st
    mock_span.end_time = et
    mock_span.labels = {"key": "val"}

    mock_trace.spans = [mock_span]
    mock_trace_client.get_trace.return_value = mock_trace

    with patch(
        "sre_agent.tools.clients.trace.get_credentials_from_tool_context"
    ) as mock_creds:
        mock_creds.return_value = "fake"
        result = await fetch_trace(trace_id="trace-1", project_id="test-proj")
        assert result["trace_id"] == "trace-1"
        assert len(result["spans"]) == 1
        assert result["spans"][0]["name"] == "op1"
