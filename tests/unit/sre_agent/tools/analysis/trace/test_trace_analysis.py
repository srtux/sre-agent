import pytest

from sre_agent.schema import ToolStatus
from sre_agent.tools.analysis.trace.analysis import (
    build_call_graph,
    calculate_span_durations,
    extract_errors,
    validate_trace_quality,
)
from sre_agent.tools.analysis.trace.comparison import compare_span_timings


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
                "labels": {},
            },
            {
                "span_id": "child1",
                "name": "child_span",
                "start_time": "2023-01-01T12:00:00.100Z",
                "end_time": "2023-01-01T12:00:00.200Z",
                "parent_span_id": "root",
                "labels": {"status": "200"},
            },
        ],
    }


def test_build_call_graph_dict(sample_trace_dict):
    """Test build_call_graph with a dictionary input."""
    graph = build_call_graph(sample_trace_dict)
    assert graph.status == ToolStatus.SUCCESS
    res_data = graph.result
    assert res_data["root_spans"] == ["root"]
    assert len(res_data["span_tree"]) == 1
    assert res_data["span_tree"][0]["span_id"] == "root"
    assert len(res_data["span_tree"][0]["children"]) == 1
    assert res_data["span_tree"][0]["children"][0]["span_id"] == "child1"
    assert res_data["total_spans"] == 2
    assert res_data["max_depth"] == 1


def test_build_call_graph_str(sample_trace_dict):
    """Test build_call_graph with a dictionary input."""
    graph = build_call_graph(sample_trace_dict)
    assert graph.status == ToolStatus.SUCCESS
    res_data = graph.result
    assert res_data["root_spans"] == ["root"]
    assert len(res_data["span_tree"]) == 1
    assert res_data["total_spans"] == 2
    assert res_data["max_depth"] == 1


def test_build_call_graph_invalid_json():
    """Test build_call_graph with an invalid JSON string."""
    result = build_call_graph("{invalid_json")
    assert result.status == ToolStatus.ERROR
    assert result.error is not None


def test_build_call_graph_error_trace():
    """Test build_call_graph with a trace containing an error."""
    result = build_call_graph({"error": "Trace not found"})
    assert result.status == ToolStatus.ERROR
    assert result.error == "Trace not found"


def test_calculate_span_durations(sample_trace_dict):
    """Test calculate_span_durations."""
    result = calculate_span_durations(sample_trace_dict)
    assert result.status == ToolStatus.SUCCESS
    timings = result.result["spans"]
    assert len(timings) == 2
    root = next(s for s in timings if s["span_id"] == "root")
    child = next(s for s in timings if s["span_id"] == "child1")

    assert root["duration_ms"] == pytest.approx(1000.0, rel=1e-3)
    assert child["duration_ms"] == pytest.approx(100.0, rel=1e-3)


def test_extract_errors():
    """Test extract_errors."""
    trace = {
        "spans": [
            {"span_id": "1", "name": "ok", "labels": {"status": "200"}},
            {"span_id": "2", "name": "error", "labels": {"status": "500"}},
            {"span_id": "3", "name": "fail", "labels": {"error": "true"}},
        ]
    }
    # Note: status:200 is NOT an error in the fixed implementation
    result = extract_errors(trace)
    assert result.status == ToolStatus.SUCCESS
    errors = result.result["errors"]
    assert len(errors) == 2
    assert any(e["span_id"] == "2" for e in errors)
    assert any(e["span_id"] == "3" for e in errors)
    assert not any(e["span_id"] == "1" for e in errors)


def test_extract_errors_http_200_not_flagged():
    """Regression test: HTTP 200 should NOT be flagged as error."""
    trace = {
        "spans": [
            {
                "span_id": "1",
                "name": "test_span",
                "labels": {"/http/status_code": "200"},
            }
        ]
    }
    result = extract_errors(trace)
    assert result.status == ToolStatus.SUCCESS
    errors = result.result["errors"]
    assert len(errors) == 0, "HTTP 200 should not be treated as error"


def test_extract_errors_http_500_flagged():
    """Test HTTP 5xx is correctly flagged."""
    trace = {
        "spans": [
            {
                "span_id": "1",
                "name": "error_span",
                "labels": {"/http/status_code": "500"},
            }
        ]
    }
    result = extract_errors(trace)
    assert result.status == ToolStatus.SUCCESS
    errors = result.result["errors"]
    assert len(errors) == 1
    assert errors[0]["status_code"] == 500
    assert errors[0]["span_id"] == "1"


def test_validate_trace_quality_detects_orphans():
    """Test trace validation detects orphaned spans."""
    trace = {
        "spans": [
            {
                "span_id": "1",
                "name": "root",
                "start_time": "2023-01-01T00:00:00Z",
                "end_time": "2023-01-01T00:00:01Z",
            },
            {
                "span_id": "2",
                "name": "child",
                "parent_span_id": "999",
                "start_time": "2023-01-01T00:00:00Z",
                "end_time": "2023-01-01T00:00:01Z",
            },
        ]
    }
    result = validate_trace_quality(trace)
    assert result.status == ToolStatus.SUCCESS
    res_data = result.result
    assert not res_data["valid"]
    assert res_data["issue_count"] == 1
    assert res_data["issues"][0]["type"] == "orphaned_span"


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
                "end_time": "2023-01-01T12:00:02Z",  # 2000ms (1000ms slower)
                "parent_span_id": None,
            }
        ],
    }

    res = compare_span_timings(baseline, target)
    assert res.status == ToolStatus.SUCCESS
    result = res.result

    assert len(result["slower_spans"]) == 1
    slower = result["slower_spans"][0]
    assert slower["span_name"] == "root_span"
    assert slower["diff_ms"] == 1000.0
    assert slower["diff_percent"] == 100.0
