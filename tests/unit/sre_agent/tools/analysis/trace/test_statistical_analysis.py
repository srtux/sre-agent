import pytest

from sre_agent.tools.analysis.trace.statistical_analysis import (
    compute_latency_statistics,
    detect_latency_anomalies,
    perform_causal_analysis,
)


@pytest.fixture
def baseline_trace():
    return {
        "trace_id": "baseline",
        "duration_ms": 100,  # Add explicit duration
        "spans": [
            {
                "span_id": "root",
                "name": "root",
                "start_time": "2020-01-01T00:00:00.000Z",
                "end_time": "2020-01-01T00:00:00.100Z",  # 100ms
                "parent_span_id": None,
                "duration_ms": 100,
            },
            {
                "span_id": "child",
                "name": "child",
                "start_time": "2020-01-01T00:00:00.010Z",
                "end_time": "2020-01-01T00:00:00.060Z",  # 50ms
                "parent_span_id": "root",
                "duration_ms": 50,
            },
        ],
    }


@pytest.fixture
def slow_target_trace():
    return {
        "trace_id": "target",
        "duration_ms": 200,  # Add explicit duration
        "spans": [
            {
                "span_id": "root",
                "name": "root",  # 200ms (100ms slower)
                "start_time": "2020-01-01T00:00:00.000Z",
                "end_time": "2020-01-01T00:00:00.200Z",
                "parent_span_id": None,
                "duration_ms": 200,
            },
            {
                "span_id": "child",
                "name": "child",  # 150ms (100ms slower) -> Root cause likely here
                "start_time": "2020-01-01T00:00:00.010Z",
                "end_time": "2020-01-01T00:00:00.160Z",
                "parent_span_id": "root",
                "duration_ms": 150,
            },
        ],
    }


def test_perform_causal_analysis(baseline_trace, slow_target_trace):
    """Test causal analysis using string inputs (integration checks build_call_graph fix)."""
    response = perform_causal_analysis(
        baseline_trace, slow_target_trace, project_id="test-p"
    )

    assert response["status"] == "success"
    analysis = response["result"]

    assert "root_cause_candidates" in analysis
    candidates = analysis["root_cause_candidates"]
    assert len(candidates) > 0
    # Child is likely identified as root cause because it slowed down and parent slowed down too
    # Logic: child slowed by 100ms (50->150), root slowed by 100ms (100->200).
    # Since child is independent (leaf), it's a candidate.

    # The sort order might prioritize root because it is also slow.
    # We just want to ensure candidates are found.
    assert len(candidates) >= 1
    # Check if child is in candidates
    child_cand = next((c for c in candidates if c["span_name"] == "child"), None)
    assert child_cand is not None


def test_compute_latency_statistics(baseline_trace):
    """Test latency statistics computation."""
    # Pass a list of trace strings
    response = compute_latency_statistics(
        [baseline_trace, baseline_trace], project_id="test-p"
    )

    assert response["status"] == "success"
    stats = response["result"]

    assert "per_span_stats" in stats
    root_stats = stats["per_span_stats"]["root"]
    assert root_stats["count"] == 2
    assert root_stats["mean"] == 100.0
    assert root_stats["min"] == 100.0
    assert root_stats["max"] == 100.0


def test_detect_latency_anomalies(baseline_trace, slow_target_trace):
    """Test anomaly detection logic."""
    # We need multiple baseline traces to get a std_dev, or at least one (std_dev will be 0->1)
    # If we pass 5 identical traces, std_dev = 0, so it defaults to 1.
    # Mean = 100ms.
    # Target root = 200ms. Z-score = (200 - 100) / 1 = 100. Very high.

    response = detect_latency_anomalies(
        [baseline_trace] * 5, slow_target_trace, project_id="test-p"
    )
    assert response["status"] == "success"
    result = response["result"]

    assert len(result["anomalous_spans"]) > 0
    anomalies = {a["span_name"]: a for a in result["anomalous_spans"]}

    assert "root" in anomalies
    assert anomalies["root"]["anomaly_type"] == "slow"
    assert "child" in anomalies
    assert anomalies["child"]["anomaly_type"] == "slow"


def test_perform_causal_analysis_with_invalid_json(baseline_trace):
    """Test that causal analysis handles invalid JSON."""
    invalid_json = '{"trace_id": "invalid", "spans": [}'

    # Test with invalid baseline
    result1 = perform_causal_analysis(invalid_json, baseline_trace, project_id="test-p")
    assert result1["status"] == "error"
    assert result1["error"] is not None

    # Test with invalid target
    result2 = perform_causal_analysis(baseline_trace, invalid_json, project_id="test-p")
    assert result2["status"] == "error"
    assert result2["error"] is not None
