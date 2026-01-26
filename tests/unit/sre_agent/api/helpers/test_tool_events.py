"""Tests for A2UI v0.8 tool event helpers."""

import json

from sre_agent.api.helpers import (
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

    def test_creates_valid_a2ui_v08_format(self) -> None:
        """Test that tool call events follow A2UI v0.8 format."""
        pending: list[dict] = []
        surface_id, events = create_tool_call_events(
            "fetch_trace", {"trace_id": "abc123"}, pending
        )

        assert len(events) == 1  # Only 1 event (beginRendering)
        assert len(pending) == 1

        # First event: beginRendering
        begin_event = json.loads(events[0])
        assert begin_event["type"] == "a2ui"
        assert "beginRendering" in begin_event["message"]
        assert begin_event["message"]["beginRendering"]["surfaceId"] == surface_id

        components = begin_event["message"]["beginRendering"]["components"]
        assert len(components) == 1
        component = components[0]
        assert "id" in component
        assert "component" in component

        # Verify Hybrid Structure
        component_data = component["component"]
        assert component_data["type"] == "x-sre-tool-log"
        assert "x-sre-tool-log" in component_data
        inner_data = component_data["x-sre-tool-log"]
        assert inner_data["tool_name"] == "fetch_trace"
        assert inner_data["args"] == {"trace_id": "abc123"}
        assert inner_data["status"] == "running"

        # Verify beginRendering references the component (root field)
        assert begin_event["message"]["beginRendering"]["root"] == component["id"]

    def test_registers_pending_call_with_component_id(self) -> None:
        """Test that pending call includes component_id for response matching."""
        pending: list[dict] = []
        surface_id, _ = create_tool_call_events(
            "list_logs", {"filter": "severity>=ERROR"}, pending
        )

        assert len(pending) == 1
        assert pending[0]["call_id"] == surface_id
        assert pending[0]["tool_name"] == "list_logs"
        assert pending[0]["args"] == {"filter": "severity>=ERROR"}
        assert "component_id" in pending[0]


class TestCreateToolResponseEvents:
    """Tests for create_tool_response_events function."""

    def test_creates_valid_a2ui_v08_format(self) -> None:
        """Test that tool response events follow A2UI v0.8 format."""
        pending: list[dict] = [
            {
                "call_id": "surface-123",
                "tool_name": "fetch_trace",
                "args": {"trace_id": "abc123"},
                "component_id": "tool-log-surface",
            }
        ]

        result = {"trace_id": "abc123", "spans": [{"span_id": "s1"}]}
        surface_id, events = create_tool_response_events("fetch_trace", result, pending)

        assert surface_id == "surface-123"
        assert len(events) == 1
        assert len(pending) == 0  # Pending call removed

        response_event = json.loads(events[0])
        assert response_event["type"] == "a2ui"
        assert "surfaceUpdate" in response_event["message"]

        update_msg = response_event["message"]["surfaceUpdate"]
        assert update_msg["surfaceId"] == surface_id
        assert len(update_msg["components"]) == 1

        component = update_msg["components"][0]
        # A2UI v0.8 format
        assert "id" in component
        assert "component" in component

        # Verify Hybrid Structure
        component_data = component["component"]
        assert component_data["type"] == "x-sre-tool-log"
        assert "x-sre-tool-log" in component_data
        inner_data = component_data["x-sre-tool-log"]
        assert inner_data["tool_name"] == "fetch_trace"
        assert inner_data["status"] == "completed"
        assert inner_data["result"] == result

    def test_handles_error_result(self) -> None:
        """Test that error results are handled correctly."""
        pending: list[dict] = [
            {
                "call_id": "surface-456",
                "tool_name": "fetch_trace",
                "args": {},
                "component_id": "tool-log-456",
            }
        ]

        error_result = {"error": "Trace not found", "error_type": "NotFoundError"}
        _surface_id, events = create_tool_response_events(
            "fetch_trace", error_result, pending
        )

        response_event = json.loads(events[0])
        component = response_event["message"]["surfaceUpdate"]["components"][0]

        # Verify Hybrid Structure
        component_data = component["component"]
        assert component_data["type"] == "x-sre-tool-log"
        inner_data = component_data["x-sre-tool-log"]
        assert inner_data["status"] == "error"

    def test_returns_empty_for_unmatched_tool(self) -> None:
        """Test that unmatched tool returns empty events."""
        pending: list[dict] = [
            {
                "call_id": "surface-789",
                "tool_name": "different_tool",
                "args": {},
                "component_id": "tool-log-789",
            }
        ]

        surface_id, events = create_tool_response_events(
            "fetch_trace", {"result": "data"}, pending
        )

        assert surface_id is None
        assert events == []


class TestCreateWidgetEvents:
    """Tests for create_widget_events function."""

    def test_creates_valid_a2ui_v08_format_for_trace(self) -> None:
        """Test that widget events follow A2UI v0.8 format for trace."""
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

        events, sids = create_widget_events("fetch_trace", result)

        assert len(events) == 2
        assert len(sids) == 1

        # First event: beginRendering
        begin_event = json.loads(events[0])
        assert begin_event["type"] == "a2ui"
        assert "beginRendering" in begin_event["message"]

        # Second event: surfaceUpdate
        surface_update = json.loads(events[1])
        assert surface_update["type"] == "a2ui"
        assert "surfaceUpdate" in surface_update["message"]

        update_msg = surface_update["message"]["surfaceUpdate"]
        component = update_msg["components"][0]
        assert "id" in component
        assert "component" in component
        assert "x-sre-trace-waterfall" in component["component"]

        # Verify beginRendering references the component
        assert begin_event["message"]["beginRendering"]["root"] == component["id"]

    def test_returns_empty_for_unmapped_tool(self) -> None:
        """Test that unmapped tools return no widget events."""
        events, sids = create_widget_events("unmapped_tool", {"data": "value"})
        assert events == []
        assert sids == []

    def test_handles_json_string_result(self) -> None:
        """Test that JSON string results are parsed."""
        result = json.dumps(
            {
                "trace_id": "abc123",
                "spans": [
                    {
                        "span_id": "s1",
                        "name": "test",
                        "start_time": "2024-01-01T00:00:00Z",
                        "end_time": "2024-01-01T00:00:01Z",
                    }
                ],
            }
        )

        events, sids = create_widget_events("fetch_trace", result)
        assert len(events) == 2
        assert len(sids) == 1

    def test_creates_valid_a2ui_v08_format_for_list_alerts(self) -> None:
        """Test that widget events follow A2UI v0.8 format for list_alerts."""
        result = [
            {
                "name": "projects/p1/alertPolicies/a1",
                "state": "OPEN",
                "severity": "CRITICAL",
                "openTime": "2024-01-01T10:00:00Z",
                "policy": {"displayName": "High CPU"},
            }
        ]

        events, sids = create_widget_events("list_alerts", result)

        assert len(events) == 2
        assert len(sids) == 1

        surface_update = json.loads(events[1])
        component = surface_update["message"]["surfaceUpdate"]["components"][0]
        assert "x-sre-incident-timeline" in component["component"]

    def test_handles_tool_execution_failure(self) -> None:
        """Test that None result (failure) is handled and returns an error widget."""
        # Tool result of None indicates failure/timeout
        events, sids = create_widget_events("fetch_trace", None)

        assert len(events) == 2
        assert len(sids) == 1

        surface_update = json.loads(events[1])
        component = surface_update["message"]["surfaceUpdate"]["components"][0]
        # It should still be the mapped widget type, but with an error property
        assert "x-sre-trace-waterfall" in component["component"]
        assert "error" in component["component"]["x-sre-trace-waterfall"]
        assert (
            "Tool execution failed"
            in component["component"]["x-sre-trace-waterfall"]["error"]
        )
