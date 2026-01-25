import json

from sre_agent.api.helpers.tool_events import create_widget_events


def test_create_widget_events_log_success():
    """Test widget events for successful log tool call."""
    tool_name = "list_log_entries"
    result = {
        "status": "success",
        "result": {"entries": [{"insertId": "1", "textPayload": "test log"}]},
    }

    events, sids = create_widget_events(tool_name, result)
    assert len(events) == 2
    assert len(sids) == 1

    begin_event = json.loads(events[0])
    assert "beginRendering" in begin_event["message"]

    update_event = json.loads(events[1])
    assert "surfaceUpdate" in update_event["message"]

    # Verify data transformation happened
    data = update_event["message"]["surfaceUpdate"]["components"][0]["component"][
        "x-sre-log-entries-viewer"
    ]
    # Check if entries are flattened/transformed per genui_adapter
    assert len(data["entries"]) == 1
    assert data["entries"][0]["payload"] == "test log"


def test_create_widget_events_log_error():
    """Test widget events for error log tool call (verifying it is NOT skipped)."""
    tool_name = "list_log_entries"
    result = {"status": "error", "error": "Failed to fetch logs"}

    events, sids = create_widget_events(tool_name, result)

    # Critical: Should NOT be empty
    assert len(events) == 2
    assert len(sids) == 1

    update_event = json.loads(events[1])
    data = update_event["message"]["surfaceUpdate"]["components"][0]["component"][
        "x-sre-log-entries-viewer"
    ]

    # Verify error is propagated via genui_adapter
    assert data["error"] == "Failed to fetch logs"
    assert len(data["entries"]) == 0


def test_create_widget_events_string_result():
    """Test widget events with stringified JSON result."""
    tool_name = "fetch_trace"
    # Stringified result (common from MCP tools)
    result_dict = {"trace_id": "trace-123", "spans": [{"span_id": "s1"}]}
    result_str = json.dumps(result_dict)

    events, sids = create_widget_events(tool_name, result_str)

    assert len(events) == 2
    assert len(sids) == 1
    update_event = json.loads(events[1])
    data = update_event["message"]["surfaceUpdate"]["components"][0]["component"][
        "x-sre-trace-waterfall"
    ]

    # Should have been parsed and transformed
    assert data["trace_id"] == "trace-123"
    assert len(data["spans"]) == 1
