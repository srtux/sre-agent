
import json
import pytest
from trace_analyzer.tools.trace_analysis import (
    build_call_graph,
    calculate_span_durations,
    compare_span_timings,
    extract_errors,
)

# Sample trace data
@pytest.fixture
def sample_trace_dict():
    return {
        "trace_id": "test-trace-1",
        "spans": [
            {
                "span_id": "root",
                "name": "root_span",
                "start_time": "2023-01-01T12:00:00Z",
                "end_time": "2023-01-01T12:00:01Z",
                "parent_span_id": None,
                "labels": {}
            },
            {
                "span_id": "child1",
                "name": "child_span",
                "start_time": "2023-01-01T12:00:00.100Z",
                "end_time": "2023-01-01T12:00:00.200Z",
                "parent_span_id": "root",
                "labels": {"status": "200"}
            }
        ]
    }

@pytest.fixture
def sample_trace_str(sample_trace_dict):
    return json.dumps(sample_trace_dict)

def test_build_call_graph_dict(sample_trace_dict):
    """Test build_call_graph with a dictionary input."""
    graph = build_call_graph(sample_trace_dict)
    assert graph["root_spans"] == ["root"]
    assert len(graph["span_tree"]) == 1
    assert graph["span_tree"][0]["span_id"] == "root"
    assert len(graph["span_tree"][0]["children"]) == 1
    assert graph["span_tree"][0]["children"][0]["span_id"] == "child1"
    assert graph["total_spans"] == 2

def test_build_call_graph_str(sample_trace_str):
    """Test build_call_graph with a JSON string input (The Fix)."""
    graph = build_call_graph(sample_trace_str)
    assert graph["root_spans"] == ["root"]
    assert len(graph["span_tree"]) == 1
    assert graph["total_spans"] == 2

def test_build_call_graph_invalid_json():
    """Test build_call_graph with an invalid JSON string."""
    result = build_call_graph("{invalid_json")
    assert "error" in result
    assert "Failed to parse trace JSON" in result["error"]

def test_build_call_graph_error_trace():
    """Test build_call_graph with a trace containing an error."""
    result = build_call_graph({"error": "Trace not found"})
    assert "error" in result
    assert result["error"] == "Trace not found"

def test_calculate_span_durations(sample_trace_str):
    """Test calculate_span_durations with string input."""
    timings = calculate_span_durations(sample_trace_str)
    assert len(timings) == 2
    root = next(s for s in timings if s["span_id"] == "root")
    child = next(s for s in timings if s["span_id"] == "child1")
    
    assert root["duration_ms"] == 1000.0
    assert child["duration_ms"] == 100.0

def test_extract_errors():
    """Test extract_errors."""
    trace = {
        "spans": [
            {"span_id": "1", "name": "ok", "labels": {"status": "200"}},
            {"span_id": "2", "name": "error", "labels": {"status": "500"}},
            {"span_id": "3", "name": "fail", "labels": {"error": "true"}}
        ]
    }
    errors = extract_errors(json.dumps(trace))
    # 'status': '200' is NOT an error.
    # 'status': '500' IS an error.
    # 'error': 'true' IS an error.
    # The logic in trace_analysis.py:
    # Check for HTTP error status codes (4xx, 5xx)
    # Check for explicitly named error/exception labels... if value_str not in ("false", "0", "none", "ok")

    # Wait, does "status": "200" trigger the named error check?
    # error_indicators = ["error", "exception", "fault", "failure", "status"]
    # "status" is in error_indicators.
    # value is "200". "200" is NOT in ("false", "0", "none", "ok").
    # So "status": "200" is considered an error by the generic check!

    # However, there is a specific check for HTTP status codes BEFORE that.
    # if "status" in key_lower ... code = int(value)...
    # But it doesn't stop processing if it finds a status code.

    # It continues to the next block:
    # if any(indicator in key_lower ...):
    #   if value_str and value_str not in ...:
    #       is_error = True

    # So "status": "200" is flagged as an error because "status" is an indicator and "200" is not "ok".
    # This seems like a bug in the implementation, but I am writing tests for existing code.
    # Or I should fix the code. The task is "improve unit testing...".
    # I should probably fix the code if it's flagging 200 as error.

    # For now, let's adjust the test to expect what the code currently does, OR fix the code.
    # Given the task description, I should probably fix bugs if found.
    # But I'll start by matching behavior, then maybe fix.

    # Actually, if I look at the failure, it says 3 == 2. So it found 3 errors.
    # That confirms 200 is being flagged.

    # I will modify the test to assert what is reasonable (that 200 is NOT an error) and then I will fix the code.
    assert len(errors) == 2
    assert any(e["span_id"] == "2" for e in errors)
    assert any(e["span_id"] == "3" for e in errors)

def test_compare_span_timings(sample_trace_dict):
    """Test compare_span_timings."""
    baseline = sample_trace_dict
    target = {
        "trace_id": "test-trace-2",
        "spans": [
            {
                "span_id": "root_2",
                "name": "root_span",
                "start_time": "2023-01-01T12:00:00Z",
                "end_time": "2023-01-01T12:00:02Z", # 2000ms (1000ms slower)
                "parent_span_id": None
            }
        ]
    }
    
    result = compare_span_timings(json.dumps(baseline), json.dumps(target))
    
    assert len(result["slower_spans"]) == 1
    slower = result["slower_spans"][0]
    assert slower["span_name"] == "root_span"
    assert slower["diff_ms"] == 1000.0
    assert slower["diff_percent"] == 100.0

def test_build_call_graph_empty_trace():
    """Test build_call_graph with empty span list."""
    trace = {"trace_id": "empty", "spans": []}
    graph = build_call_graph(json.dumps(trace))
    assert graph["total_spans"] == 0
    assert graph["root_spans"] == []

def test_build_call_graph_disconnected():
    """Test build_call_graph with disconnected spans (multiple roots)."""
    trace = {
        "trace_id": "disconnected",
        "spans": [
            {"span_id": "root1", "name": "root1", "parent_span_id": None},
            {"span_id": "root2", "name": "root2", "parent_span_id": None}
        ]
    }
    graph = build_call_graph(json.dumps(trace))
    assert len(graph["root_spans"]) == 2
    assert "root1" in graph["root_spans"]
    assert "root2" in graph["root_spans"]

def test_extract_errors_various_formats():
    """Test extract_errors with different error indications."""
    trace = {
        "spans": [
            {"span_id": "1", "name": "http_error", "labels": {"/http/status_code": "500"}},
            {"span_id": "2", "name": "error_bool", "labels": {"error": "true"}},
            {"span_id": "3", "name": "error_msg", "labels": {"/error/message": "something failed"}},
            {"span_id": "4", "name": "ok", "labels": {"/http/status_code": "200"}}
        ]
    }
    errors = extract_errors(json.dumps(trace))
    error_ids = [e["span_id"] for e in errors]
    assert "1" in error_ids
    assert "2" in error_ids
    assert "3" in error_ids
    assert "4" not in error_ids
