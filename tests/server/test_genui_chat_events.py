"""Tests for GenUI chat endpoint tool call events.

These tests verify that:
1. Request validation works correctly (Fix #3)
2. The shared tool event helper functions work correctly
"""

import json
from unittest.mock import MagicMock

import httpx
import pytest
import pytest_asyncio

from server import app
from sre_agent.api.helpers.tool_events import (
    TOOL_WIDGET_MAP,
    create_tool_call_events,
    create_tool_response_events,
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


# --- Unit Tests for Shared Helper Functions (Fix #2) ---


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
    result = normalize_tool_args(mock_args)
    assert result == {"key": "value"}


def test_normalize_tool_args_fallback():
    """Test normalize_tool_args with non-convertible object."""

    class NonConvertible:
        pass

    result = normalize_tool_args(NonConvertible())
    assert "_raw_args" in result


def test_create_tool_call_events():
    """Test _create_tool_call_events creates proper A2UI events."""
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

    # Should have 1 event (bundled A2UI v0.8)
    assert len(events) == 1

    # Parse and verify event
    update_event = json.loads(events[0])
    assert update_event["type"] == "a2ui"
    assert "surfaceUpdate" in update_event["message"]
    assert "beginRendering" in update_event["message"]

    # Verify tool log data in surfaceUpdate
    components = update_event["message"]["surfaceUpdate"]["components"]
    assert "id" in components[0]
    assert "component" in components[0]
    tool_log = components[0]["component"]["x-sre-tool-log"]
    assert tool_log["tool_name"] == "test_tool"
    assert tool_log["status"] == "running"
    assert tool_log["args"] == {"arg1": "value1"}

    # Verify beginRendering references the component
    assert update_event["message"]["beginRendering"]["root"] == components[0]["id"]


def test_create_tool_response_events_success():
    """Test _create_tool_response_events with successful result."""
    pending_calls = [
        {
            "call_id": "test_tool_abc123",
            "tool_name": "test_tool",
            "surface_id": "surface-123",
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

    # Should have 1 event: surfaceUpdate with completed status
    assert len(events) == 1

    update_event = json.loads(events[0])
    assert "beginRendering" in update_event["message"]
    components = update_event["message"]["surfaceUpdate"]["components"]
    tool_log = components[0]["component"]["x-sre-tool-log"]
    assert tool_log["status"] == "completed"
    assert tool_log["result"] == "success"


def test_create_tool_response_events_error():
    """Test _create_tool_response_events with error result."""
    pending_calls = [
        {
            "call_id": "test_tool_abc123",
            "tool_name": "test_tool",
            "surface_id": "surface-123",
            "args": {},
        }
    ]

    _call_id, events = create_tool_response_events(
        tool_name="test_tool",
        result={"error": "Something went wrong", "error_type": "RuntimeError"},
        pending_tool_calls=pending_calls,
    )

    assert len(events) == 1
    update_event = json.loads(events[0])
    components = update_event["message"]["surfaceUpdate"]["components"]
    tool_log = components[0]["component"]["x-sre-tool-log"]
    assert tool_log["status"] == "error"
    assert "RuntimeError" in tool_log["result"]


def test_create_tool_response_events_no_match():
    """Test _create_tool_response_events with no matching pending call."""
    pending_calls = [
        {
            "call_id": "other_tool_abc123",
            "tool_name": "other_tool",
            "surface_id": "surface-123",
            "args": {},
        }
    ]

    call_id, events = create_tool_response_events(
        tool_name="test_tool",  # Different tool name
        result={"result": "success"},
        pending_tool_calls=pending_calls,
    )

    # Should not have matched
    assert call_id is None
    assert len(events) == 0
    # Original pending call should still be there
    assert len(pending_calls) == 1


def test_create_tool_response_events_fifo_matching():
    """Test that FIFO matching works for multiple calls to same tool (Fix #1)."""
    pending_calls = [
        {
            "call_id": "fetch_trace_111",
            "tool_name": "fetch_trace",
            "surface_id": "surface-1",
            "args": {"trace_id": "trace-1"},
        },
        {
            "call_id": "fetch_trace_222",
            "tool_name": "fetch_trace",
            "surface_id": "surface-2",
            "args": {"trace_id": "trace-2"},
        },
    ]

    # First response should match first call (FIFO)
    call_id1, events1 = create_tool_response_events(
        tool_name="fetch_trace",
        result={"result": "trace-1-data"},
        pending_tool_calls=pending_calls,
    )

    assert call_id1 == "fetch_trace_111"
    assert len(pending_calls) == 1  # One remaining

    # Verify the correct args were preserved
    update_event = json.loads(events1[0])
    components = update_event["message"]["surfaceUpdate"]["components"]
    tool_log = components[0]["component"]["x-sre-tool-log"]
    assert tool_log["args"] == {"trace_id": "trace-1"}

    # Second response should match second call
    call_id2, _events2 = create_tool_response_events(
        tool_name="fetch_trace",
        result={"result": "trace-2-data"},
        pending_tool_calls=pending_calls,
    )

    assert call_id2 == "fetch_trace_222"
    assert len(pending_calls) == 0  # All matched


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


# --- API Validation Tests (Fix #3) ---


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
    # This tests that the request validation accepts the correct format
    # The actual agent execution may fail, but the request should be validated
    response = await async_client.post(
        "/api/genui/chat",
        json={"messages": [{"role": "user", "text": "Hello"}]},
    )
    # Should be accepted (200 OK for streaming) not a validation error (422)
    assert response.status_code == 200
    await response.aclose()
