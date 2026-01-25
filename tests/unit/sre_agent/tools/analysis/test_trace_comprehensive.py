import json

import pytest

from sre_agent.tools.analysis.trace_comprehensive import analyze_trace_comprehensive


@pytest.fixture
def sample_trace_dict():
    return {
        "trace_id": "test-trace-comprehensive",
        "project_id": "test-project",
        "spans": [
            {
                "span_id": "root",
                "name": "root_span",
                "start_time": "2023-01-01T12:00:00Z",
                "end_time": "2023-01-01T12:00:01Z",
                "start_time_unix": 1672574400.0,
                "end_time_unix": 1672574401.0,
                "parent_span_id": None,
                "labels": {},
            },
            {
                "span_id": "child1",
                "name": "child_span",
                "start_time": "2023-01-01T12:00:00.100Z",
                "end_time": "2023-01-01T12:00:00.200Z",
                "start_time_unix": 1672574400.1,
                "end_time_unix": 1672574400.2,
                "parent_span_id": "root",
                "labels": {"/http/status_code": "500"},
            },
        ],
        "duration_ms": 1000.0,
    }


def test_analyze_trace_comprehensive(sample_trace_dict):
    trace_json = json.dumps(sample_trace_dict)
    # We pass trace_json as trace_id because fetch_trace_data handles it
    result = analyze_trace_comprehensive(trace_json, project_id="test-project")

    assert result["status"] == "success"
    data = result["result"]
    assert data["trace_id"] == "test-trace-comprehensive"
    assert "quality_check" in data
    assert data["quality_check"]["valid"] is True
    assert "span_count" in data
    assert data["span_count"] == 2
    assert "total_duration_ms" in data
    assert data["total_duration_ms"] == 1000.0
    assert "errors" in data
    assert len(data["errors"]) == 1
    assert data["errors"][0]["span_id"] == "child1"
    assert "critical_path_analysis" in data
    assert "structure" in data
    assert data["structure"]["total_spans"] == 2


def test_analyze_trace_comprehensive_with_baseline(sample_trace_dict):
    target_trace = sample_trace_dict.copy()
    target_trace["duration_ms"] = 2000.0
    # Update spans to match new duration
    target_trace["spans"][0]["end_time_unix"] = 1672574402.0
    target_trace["spans"][0]["end_time"] = "2023-01-01T12:00:02Z"

    baseline_trace = sample_trace_dict.copy()
    baseline_json = json.dumps(baseline_trace)
    target_json = json.dumps(target_trace)

    # In this test environment, we can't easily fetch the baseline by ID
    # unless we mock compute_latency_statistics or fetch_trace_data.
    # However, since the baseline_trace_id will be passed to compute_latency_statistics,
    # which calls _fetch_traces_parallel, which calls fetch_trace_data...
    # passing baseline_json as baseline_trace_id SHOULD work if it's treated as a single list.

    result = analyze_trace_comprehensive(
        target_json, project_id="test-project", baseline_trace_id=baseline_json
    )

    assert result["status"] == "success"
    assert "anomaly_analysis" in result["result"]
    # Since we only have one baseline, stdev might be 0, but it should still return something.


def test_analyze_trace_comprehensive_error():
    result = analyze_trace_comprehensive(json.dumps({"error": "Not found"}))
    assert result["status"] == "error"
    assert result["error"] is not None
