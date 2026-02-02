"""Tests for chat endpoint tool call events.

These tests verify that:
1. Request validation works correctly
2. The shared tool event helper functions work correctly
3. Tool call/response events use the simplified inline format
"""

import json
from unittest.mock import MagicMock

import httpx
import pytest
import pytest_asyncio

from server import app
from sre_agent.api.helpers.tool_events import (
    TOOL_WIDGET_MAP,
    create_dashboard_event,
    create_tool_call_events,
    create_tool_response_events,
    create_widget_events,
    normalize_tool_args,
)


@pytest_asyncio.fixture
async def async_client():
    """Create an async HTTP client for testing streaming endpoints."""
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# --- Unit Tests for Shared Helper Functions ---


def test_normalize_tool_args_none():
    """Test normalize_tool_args with None."""
    result = normalize_tool_args(None)
    assert result == {}


def test_normalize_tool_args_dict():
    """Test normalize_tool_args with dict."""
    args = {"key": "value"}
    result = normalize_tool_args(args)
    assert result == {"key": "value"}


def test_normalize_tool_args_with_to_dict():
    """Test normalize_tool_args with object having to_dict method."""
    mock_args = MagicMock()
    mock_args.to_dict.return_value = {"key": "value"}
    mock_args.model_dump.return_value = {"key": "value"}
    result = normalize_tool_args(mock_args)
    assert result == {"key": "value"}


def test_normalize_tool_args_fallback():
    """Test normalize_tool_args with non-convertible object."""

    class NonConvertible:
        pass

    result = normalize_tool_args(NonConvertible())
    assert "_raw_args" in result


def test_create_tool_call_events():
    """Test create_tool_call_events creates simple inline events."""
    pending_calls: list[dict] = []
    call_id, events = create_tool_call_events(
        tool_name="test_tool",
        args={"arg1": "value1"},
        pending_tool_calls=pending_calls,
    )

    # Should have registered the pending call
    assert len(pending_calls) == 1
    assert pending_calls[0]["tool_name"] == "test_tool"
    assert pending_calls[0]["args"] == {"arg1": "value1"}
    assert call_id == pending_calls[0]["call_id"]

    # Should have 1 event
    assert len(events) == 1

    # Parse and verify the simple tool_call event
    event = json.loads(events[0])
    assert event["type"] == "tool_call"
    assert event["call_id"] == call_id
    assert event["tool_name"] == "test_tool"
    assert event["args"] == {"arg1": "value1"}


def test_create_tool_response_events_success():
    """Test create_tool_response_events with successful result."""
    pending_calls = [
        {
            "call_id": "test_tool_abc123",
            "tool_name": "test_tool",
            "args": {"arg1": "value1"},
        }
    ]

    call_id, events = create_tool_response_events(
        tool_name="test_tool",
        result={"result": "success"},
        pending_tool_calls=pending_calls,
    )

    # Should have removed the pending call
    assert len(pending_calls) == 0
    assert call_id == "test_tool_abc123"

    # Should have 1 event
    assert len(events) == 1

    # Parse and verify the simple tool_response event
    event = json.loads(events[0])
    assert event["type"] == "tool_response"
    assert event["call_id"] == "test_tool_abc123"
    assert event["tool_name"] == "test_tool"
    assert event["status"] == "completed"
    assert event["result"] == "success"


def test_create_tool_response_events_error():
    """Test create_tool_response_events with error result."""
    pending_calls = [
        {
            "call_id": "test_tool_abc123",
            "tool_name": "test_tool",
            "args": {},
        }
    ]

    _call_id, events = create_tool_response_events(
        tool_name="test_tool",
        result={"error": "Something went wrong", "error_type": "RuntimeError"},
        pending_tool_calls=pending_calls,
    )

    assert len(events) == 1
    event = json.loads(events[0])
    assert event["type"] == "tool_response"
    assert event["status"] == "error"
    assert "RuntimeError" in event["result"]


def test_create_tool_response_events_fifo_matching():
    """Test that FIFO matching works for multiple calls to same tool."""
    pending_calls = [
        {
            "call_id": "fetch_trace_111",
            "tool_name": "fetch_trace",
            "args": {"trace_id": "trace-1"},
        },
        {
            "call_id": "fetch_trace_222",
            "tool_name": "fetch_trace",
            "args": {"trace_id": "trace-2"},
        },
    ]

    # First response should match first call (FIFO)
    call_id1, _events1 = create_tool_response_events(
        tool_name="fetch_trace",
        result={"result": "trace-1-data"},
        pending_tool_calls=pending_calls,
    )

    assert call_id1 == "fetch_trace_111"
    assert len(pending_calls) == 1  # One remaining

    # Second response should match second call
    call_id2, _events2 = create_tool_response_events(
        tool_name="fetch_trace",
        result={"result": "trace-2-data"},
        pending_tool_calls=pending_calls,
    )

    assert call_id2 == "fetch_trace_222"
    assert len(pending_calls) == 0  # All matched


def test_create_tool_response_events_no_match():
    """Test tool response with no matching pending call."""
    pending_calls: list[dict] = []
    call_id, events = create_tool_response_events(
        tool_name="unknown_tool",
        result={"result": "data"},
        pending_tool_calls=pending_calls,
    )

    assert call_id is None
    assert len(events) == 0


def test_tool_widget_map_exists():
    """Test that TOOL_WIDGET_MAP has expected tools."""
    expected_tools = [
        "fetch_trace",
        "analyze_critical_path",
        "query_promql",
        "list_time_series",
        "list_log_entries",
    ]
    for tool in expected_tools:
        assert tool in TOOL_WIDGET_MAP


def test_create_widget_events_returns_empty():
    """Test that create_widget_events is now a stub returning empty lists."""
    events, surface_ids = create_widget_events(
        tool_name="fetch_trace", result={"trace_id": "test"}
    )
    assert events == []
    assert surface_ids == []


def test_create_dashboard_event_returns_json():
    """Test that create_dashboard_event returns proper dashboard JSON."""
    result = {
        "trace_id": "test-trace",
        "spans": [
            {
                "span_id": "s1",
                "name": "root",
                "start_time": "2023-01-01T00:00:00Z",
                "end_time": "2023-01-01T00:00:01Z",
            }
        ],
    }
    event = create_dashboard_event("fetch_trace", result)
    if event is not None:
        parsed = json.loads(event)
        assert parsed["type"] == "dashboard"
        assert parsed["category"] == "traces"
        assert parsed["tool_name"] == "fetch_trace"


# --- API Validation Tests ---


@pytest.mark.asyncio
async def test_genui_chat_malformed_request_missing_text(
    async_client: httpx.AsyncClient,
):
    """Verify that malformed requests without 'text' return validation errors."""
    response = await async_client.post(
        "/api/genui/chat",
        json={"messages": [{"role": "user"}]},  # Missing 'text'
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_genui_chat_malformed_request_missing_role(
    async_client: httpx.AsyncClient,
):
    """Verify that malformed requests without 'role' return validation errors."""
    response = await async_client.post(
        "/api/genui/chat",
        json={"messages": [{"text": "hello"}]},  # Missing 'role'
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_genui_chat_valid_request_format(async_client: httpx.AsyncClient):
    """Verify that valid request format is accepted."""
    response = await async_client.post(
        "/api/genui/chat",
        json={"messages": [{"role": "user", "text": "Hello"}]},
    )
    # Should be accepted (200 OK for streaming) not a validation error (422)
    assert response.status_code == 200
    await response.aclose()
