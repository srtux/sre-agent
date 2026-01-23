from unittest.mock import patch

import pytest

from sre_agent.tools.analysis.trace.patterns import detect_all_sre_patterns
from sre_agent.tools.analysis.trace.statistical_analysis import (
    compute_latency_statistics,
    detect_latency_anomalies,
)


@pytest.fixture
def complex_trace():
    return {
        "trace_id": "complex-trace",
        "duration_ms": 100.0,
        "spans": [
            {
                "span_id": "root",
                "name": "root",
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-01T00:00:00.100Z",
                "duration_ms": 100.0,
                "parent_span_id": None,
            },
            {
                "span_id": "child1",
                "name": "db_call",
                "start_time": "2024-01-01T00:00:00.010Z",
                "end_time": "2024-01-01T00:00:00.020Z",
                "duration_ms": 10.0,
                "parent_span_id": "root",
            },
            {
                "span_id": "child2",
                "name": "db_call",
                "start_time": "2024-01-01T00:00:00.025Z",
                "end_time": "2024-01-01T00:00:00.035Z",
                "duration_ms": 10.0,
                "parent_span_id": "root",
            },
            {
                "span_id": "child3",
                "name": "db_call",
                "start_time": "2024-01-01T00:00:00.040Z",
                "end_time": "2024-01-01T00:00:00.050Z",
                "duration_ms": 10.0,
                "parent_span_id": "root",
            },
        ],
    }


def test_compute_latency_statistics(complex_trace):
    with patch(
        "sre_agent.tools.analysis.trace.statistical_analysis._fetch_traces_parallel"
    ) as mock_fetch:
        mock_fetch.return_value = [complex_trace]
        res = compute_latency_statistics(["trace-1"])
        stats = res
        assert stats["count"] == 1
        assert stats["mean"] == 100.0
        assert stats["max"] == 100.0
        assert stats["min"] == 100.0


def test_detect_latency_anomalies(complex_trace):
    with (
        patch(
            "sre_agent.tools.analysis.trace.statistical_analysis.compute_latency_statistics"
        ) as mock_stats,
        patch(
            "sre_agent.tools.analysis.trace.statistical_analysis.fetch_trace_data"
        ) as mock_fetch,
    ):
        mock_stats.return_value = {
            "count": 10,
            "mean": 50.0,
            "stdev": 5.0,
            "per_span_stats": {},
        }
        mock_fetch.return_value = complex_trace  # root is 100ms, which is > 50 + 2*5

        res = detect_latency_anomalies(["baseline-1"], "target-1", threshold_sigma=2.0)
        report = res
        assert report["is_anomaly"] is True
        assert report["z_score"] > 2.0


def test_detect_all_sre_patterns(complex_trace):
    with patch(
        "sre_agent.tools.analysis.trace.patterns.fetch_trace_data"
    ) as mock_fetch:
        # Mock retry storm
        complex_trace["spans"].append(
            {
                "span_id": "retry1",
                "name": "op",
                "labels": {"rpc.retry_count": "1"},
                "parent_span_id": "root",
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-01T00:00:00.010Z",
            }
        )
        complex_trace["spans"].append(
            {
                "span_id": "retry2",
                "name": "op",
                "labels": {"rpc.retry_count": "2"},
                "parent_span_id": "root",
                "start_time": "2024-01-01T00:00:00.020Z",
                "end_time": "2024-01-01T00:00:00.030Z",
            }
        )
        mock_fetch.return_value = complex_trace

        res = detect_all_sre_patterns("trace-1")
        report = res
        assert report["trace_id"] == "trace-1"
