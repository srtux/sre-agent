
import pytest
from sre_agent.schema import ToolStatus
from sre_agent.tools.analysis.trace.statistical_analysis import (
    compute_latency_statistics,
    analyze_critical_path,
)
from unittest.mock import patch, MagicMock

@pytest.fixture
def optimized_trace_data():
    return {
        "trace_id": "optimized-trace",
        "duration_ms": 100.0,
        "spans": [
            {
                "span_id": "span-1",
                "name": "fast-span",
                # Invalid ISO strings that would cause crash if parsed
                "start_time": "INVALID_START",
                "end_time": "INVALID_END",
                # Valid Unix timestamps (100ms duration)
                "start_time_unix": 1600000000.0,
                "end_time_unix": 1600000000.1,
                "parent_span_id": None,
                # duration_ms missing to force calculation
            }
        ]
    }

@patch("sre_agent.tools.analysis.trace.statistical_analysis._fetch_traces_parallel")
def test_compute_latency_statistics_optimized(mock_fetch, optimized_trace_data):
    """
    Test that compute_latency_statistics uses start_time_unix/end_time_unix
    even when start_time/end_time strings are invalid.
    """
    mock_fetch.return_value = [optimized_trace_data]

    response = compute_latency_statistics(
        ["optimized-trace"], project_id="test-p"
    )

    assert response.status == ToolStatus.SUCCESS
    stats = response.result

    # Check per-span stats
    assert "per_span_stats" in stats
    span_stats = stats["per_span_stats"]
    assert "fast-span" in span_stats

    # Duration should be 100ms (1600000000.1 - 1600000000.0) * 1000
    # Floating point precision might vary slightly
    assert abs(span_stats["fast-span"]["mean"] - 100.0) < 0.01

@patch("sre_agent.tools.analysis.trace.statistical_analysis.fetch_trace_data")
def test_analyze_critical_path_optimized(mock_fetch, optimized_trace_data):
    """
    Test that analyze_critical_path uses start_time_unix/end_time_unix.
    """
    mock_fetch.return_value = optimized_trace_data

    response = analyze_critical_path("optimized-trace", project_id="test-p")

    assert response.status == ToolStatus.SUCCESS
    result = response.result

    assert "critical_path" in result
    path = result["critical_path"]
    assert len(path) == 1
    assert path[0]["name"] == "fast-span"
    assert abs(path[0]["duration_ms"] - 100.0) < 0.01
