"""Tests for widget event creation.

Since visualization data now goes through the dashboard channel only,
create_widget_events is a stub that returns empty lists.
Dashboard events are tested via create_dashboard_event instead.
"""

import json

from sre_agent.api.helpers.tool_events import (
    create_dashboard_event,
    create_widget_events,
)


def test_create_widget_events_returns_empty():
    """Test that create_widget_events returns empty (visualization via dashboard only)."""
    events, sids = create_widget_events(
        tool_name="list_log_entries",
        result={"status": "success", "result": {"entries": []}},
    )
    assert events == []
    assert sids == []


def test_create_widget_events_returns_empty_for_traces():
    """Test that create_widget_events returns empty for trace tools too."""
    events, sids = create_widget_events(
        tool_name="fetch_trace",
        result={"trace_id": "test", "spans": []},
    )
    assert events == []
    assert sids == []


def test_dashboard_event_for_log_tool():
    """Test dashboard event creation for log tool results."""
    result = {
        "status": "success",
        "result": {"entries": [{"insertId": "1", "textPayload": "test log"}]},
    }

    event = create_dashboard_event("list_log_entries", result)
    if event is not None:
        parsed = json.loads(event)
        assert parsed["type"] == "dashboard"
        assert parsed["category"] == "logs"
        assert parsed["tool_name"] == "list_log_entries"


def test_dashboard_event_for_trace_tool():
    """Test dashboard event creation for trace tool results."""
    result = {
        "trace_id": "trace-123",
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
