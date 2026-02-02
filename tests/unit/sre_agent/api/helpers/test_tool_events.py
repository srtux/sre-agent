"""Tests for inline tool event helpers."""

import json

from sre_agent.api.helpers import (
    create_dashboard_event,
    create_tool_call_events,
    create_tool_response_events,
    create_widget_events,
    normalize_tool_args,
)


class TestNormalizeToolArgs:
    """Tests for normalize_tool_args function."""

    def test_none_returns_empty_dict(self) -> None:
        """Test that None returns empty dict."""
        assert normalize_tool_args(None) == {}

    def test_dict_returns_dict(self) -> None:
        """Test that dict returns dict."""
        args = {"key": "value"}
        assert normalize_tool_args(args) == args

    def test_json_string_returns_dict(self) -> None:
        """Test that JSON string returns parsed dict."""
        args = '{"key": "value"}'
        assert normalize_tool_args(args) == {"key": "value"}


class TestCreateToolCallEvents:
    """Tests for create_tool_call_events function."""

    def test_creates_simple_tool_call_event(self) -> None:
        """Test that tool call events use the simple inline format."""
        pending: list[dict] = []
        call_id, events = create_tool_call_events(
            "fetch_trace", {"trace_id": "abc123"}, pending
        )

        assert len(events) == 1
        assert len(pending) == 1

        event = json.loads(events[0])
        assert event["type"] == "tool_call"
        assert event["call_id"] == call_id
        assert event["tool_name"] == "fetch_trace"
        assert event["args"] == {"trace_id": "abc123"}

    def test_registers_pending_call(self) -> None:
        """Test that pending call is properly registered."""
        pending: list[dict] = []
        call_id, _ = create_tool_call_events(
            "list_logs", {"filter": "severity>=ERROR"}, pending
        )

        assert len(pending) == 1
        assert pending[0]["call_id"] == call_id
        assert pending[0]["tool_name"] == "list_logs"
        assert pending[0]["args"] == {"filter": "severity>=ERROR"}


class TestCreateToolResponseEvents:
    """Tests for create_tool_response_events function."""

    def test_creates_simple_tool_response_event(self) -> None:
        """Test that tool response events use the simple inline format."""
        pending: list[dict] = [
            {
                "call_id": "surface-123",
                "tool_name": "fetch_trace",
                "args": {"trace_id": "abc123"},
            }
        ]

        result = {"trace_id": "abc123", "spans": [{"span_id": "s1"}]}
        call_id, events = create_tool_response_events("fetch_trace", result, pending)

        assert call_id == "surface-123"
        assert len(events) == 1
        assert len(pending) == 0  # Pending call removed

        event = json.loads(events[0])
        assert event["type"] == "tool_response"
        assert event["call_id"] == "surface-123"
        assert event["tool_name"] == "fetch_trace"
        assert event["status"] == "completed"

    def test_handles_error_result(self) -> None:
        """Test that error results are handled correctly."""
        pending: list[dict] = [
            {
                "call_id": "surface-456",
                "tool_name": "fetch_trace",
                "args": {},
            }
        ]

        error_result = {"error": "Trace not found", "error_type": "NotFoundError"}
        _call_id, events = create_tool_response_events(
            "fetch_trace", error_result, pending
        )

        event = json.loads(events[0])
        assert event["type"] == "tool_response"
        assert event["status"] == "error"
        assert "NotFoundError" in event["result"]

    def test_returns_empty_for_unmatched_tool(self) -> None:
        """Test that unmatched tool returns empty events."""
        pending: list[dict] = [
            {
                "call_id": "surface-789",
                "tool_name": "different_tool",
                "args": {},
            }
        ]

        call_id, events = create_tool_response_events(
            "fetch_trace", {"result": "data"}, pending
        )

        assert call_id is None
        assert events == []

    def test_fifo_matching(self) -> None:
        """Test FIFO matching for multiple calls to the same tool."""
        pending: list[dict] = [
            {"call_id": "call-1", "tool_name": "fetch_trace", "args": {"id": "1"}},
            {"call_id": "call-2", "tool_name": "fetch_trace", "args": {"id": "2"}},
        ]

        call_id1, _ = create_tool_response_events(
            "fetch_trace", {"result": "data-1"}, pending
        )
        assert call_id1 == "call-1"
        assert len(pending) == 1

        call_id2, _ = create_tool_response_events(
            "fetch_trace", {"result": "data-2"}, pending
        )
        assert call_id2 == "call-2"
        assert len(pending) == 0


class TestCreateWidgetEvents:
    """Tests for create_widget_events function (now a stub)."""

    def test_returns_empty_for_any_tool(self) -> None:
        """Test that widget events return empty (visualization via dashboard only)."""
        events, sids = create_widget_events("fetch_trace", {"trace_id": "abc"})
        assert events == []
        assert sids == []

    def test_returns_empty_for_unmapped_tool(self) -> None:
        """Test that unmapped tools return no widget events."""
        events, sids = create_widget_events("unmapped_tool", {"data": "value"})
        assert events == []
        assert sids == []


class TestCreateDashboardEvent:
    """Tests for create_dashboard_event function."""

    def test_creates_dashboard_event_for_trace(self) -> None:
        """Test that dashboard event is created for trace tool."""
        result = {
            "trace_id": "abc123",
            "spans": [
                {
                    "span_id": "s1",
                    "name": "test-span",
                    "start_time": "2024-01-01T00:00:00Z",
                    "end_time": "2024-01-01T00:00:01Z",
                }
            ],
        }

        event_str = create_dashboard_event("fetch_trace", result)
        assert event_str is not None

        event = json.loads(event_str)
        assert event["type"] == "dashboard"
        assert event["category"] == "traces"
        assert event["widget_type"] == "x-sre-trace-waterfall"
        assert event["tool_name"] == "fetch_trace"
        assert isinstance(event["data"], dict)

    def test_creates_dashboard_event_for_alerts(self) -> None:
        """Test that dashboard event is created for alerts tool."""
        result = [
            {
                "name": "projects/p1/alertPolicies/a1",
                "state": "OPEN",
                "severity": "CRITICAL",
                "openTime": "2024-01-01T10:00:00Z",
                "policy": {"displayName": "High CPU"},
            }
        ]

        event_str = create_dashboard_event("list_alerts", result)
        assert event_str is not None

        event = json.loads(event_str)
        assert event["type"] == "dashboard"
        assert event["category"] == "alerts"
        assert event["widget_type"] == "x-sre-incident-timeline"

    def test_returns_none_for_unmapped_tool(self) -> None:
        """Test that unmapped tools return None."""
        event = create_dashboard_event("unmapped_tool", {"data": "value"})
        assert event is None

    def test_returns_none_for_none_result(self) -> None:
        """Test that None result returns None."""
        event = create_dashboard_event("fetch_trace", None)
        assert event is None

    def test_returns_none_for_error_result(self) -> None:
        """Test that error results return None."""
        result = {"status": "error", "result": None, "error": "Failed"}
        event = create_dashboard_event("fetch_trace", result)
        assert event is None

    def test_unwraps_status_result_wrapper(self) -> None:
        """Test that status/result wrappers are unwrapped."""
        result = {
            "status": "success",
            "result": {
                "trace_id": "abc123",
                "spans": [
                    {
                        "span_id": "s1",
                        "name": "test",
                        "start_time": "2024-01-01T00:00:00Z",
                        "end_time": "2024-01-01T00:00:01Z",
                    }
                ],
            },
        }

        event_str = create_dashboard_event("fetch_trace", result)
        assert event_str is not None

        event = json.loads(event_str)
        assert event["type"] == "dashboard"
        assert event["category"] == "traces"
