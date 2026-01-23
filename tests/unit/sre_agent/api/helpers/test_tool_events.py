import json

from sre_agent.api.helpers import (
    create_tool_call_events,
    create_tool_response_events,
    create_widget_events,
)


def test_create_tool_call_events_structure():
    """Verify that tool call events do NOT have the redundant 'component' wrapper."""
    tool_name = "test_tool"
    args = {"arg1": "val1"}
    pending_tool_calls = []

    _call_id, events = create_tool_call_events(tool_name, args, pending_tool_calls)

    assert len(events) == 2
    # Second event is the surfaceUpdate
    event_data = json.loads(events[1])

    components = event_data["message"]["surfaceUpdate"]["components"]
    assert len(components) == 1

    # Check for direct map (no 'component' key)
    assert "x-sre-tool-log" in components[0]
    assert "component" not in components[0]
    assert components[0]["x-sre-tool-log"]["status"] == "running"


def test_create_tool_response_events_structure():
    """Verify that tool response events do NOT have the redundant 'component' wrapper."""
    tool_name = "test_tool"
    args = {"arg1": "val1"}
    call_id = "test-uuid"
    pending_tool_calls = [{"call_id": call_id, "tool_name": tool_name, "args": args}]
    result = {"status": "ok"}

    returned_call_id, events = create_tool_response_events(
        tool_name, result, pending_tool_calls
    )

    assert returned_call_id == call_id
    assert len(events) == 1
    event_data = json.loads(events[0])

    components = event_data["message"]["surfaceUpdate"]["components"]
    assert len(components) == 1

    # Check for direct map (no 'component' key)
    assert "x-sre-tool-log" in components[0]
    assert "component" not in components[0]
    assert components[0]["x-sre-tool-log"]["status"] == "completed"


def test_create_widget_events_structure():
    """Verify that widget events do NOT have the redundant 'component' wrapper."""
    # Using fetch_trace which maps to x-sre-trace-waterfall
    tool_name = "fetch_trace"
    # Minimal mock result that can be transformed
    result = {
        "spans": [{"span_id": "1", "name": "span1", "start_time": 0, "end_time": 1000}]
    }

    events = create_widget_events(tool_name, result)

    assert len(events) == 2
    # Second event is the surfaceUpdate
    event_data = json.loads(events[1])

    components = event_data["message"]["surfaceUpdate"]["components"]
    assert len(components) == 1

    # Check for direct map (no 'component' key)
    assert "x-sre-trace-waterfall" in components[0]
    assert "component" not in components[0]
