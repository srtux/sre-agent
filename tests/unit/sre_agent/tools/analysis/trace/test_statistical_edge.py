"""Edge case tests for Statistical Trace Analysis."""

from unittest.mock import patch

import pytest

from sre_agent.schema import ToolStatus
from sre_agent.tools.analysis.trace.statistical_analysis import (
    _fetch_traces_parallel,
    analyze_trace_patterns,
    compute_latency_statistics,
    compute_service_level_stats,
    detect_latency_anomalies,
    perform_causal_analysis,
)


@pytest.fixture
def mock_trace_data():
    return {
        "trace_id": "target_id",
        "duration_ms": 1000,
        "spans": [
            {
                "span_id": "root",
                "name": "gateway",
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-01T00:00:01Z",
                "duration_ms": 1000,
                "labels": {"service.name": "frontend"},
            }
        ],
    }


def test_fetch_traces_parallel_exception():
    with patch(
        "sre_agent.tools.analysis.trace.statistical_analysis.fetch_trace_data",
        side_effect=Exception("API Down"),
    ):
        results = _fetch_traces_parallel(["t1", "t2"])
        assert len(results) == 0


def test_compute_latency_statistics_real_logic():
    traces = [
        {
            "trace_id": "b1",
            "duration_ms": 100,
            "spans": [{"name": "s1", "duration_ms": 100}],
        },
        {
            "trace_id": "b2",
            "duration_ms": 200,
            "spans": [{"name": "s1", "duration_ms": 200}],
        },
        {
            "trace_id": "b3",
            "duration_ms": 150,
            "spans": [{"name": "s1", "duration_ms": 150}],
        },
    ]
    with patch(
        "sre_agent.tools.analysis.trace.statistical_analysis._fetch_traces_parallel",
        return_value=traces,
    ):
        res = compute_latency_statistics(["b1", "b2", "b3"])
        assert res.status == ToolStatus.SUCCESS
        stats = res.result
        assert stats["mean"] == 150.0
        assert stats["per_span_stats"]["s1"]["mean"] == 150.0


def test_detect_latency_anomalies_full_flow(mock_trace_data):
    baseline_traces = [
        {
            "trace_id": "b1",
            "duration_ms": 100,
            "spans": [{"name": "gateway", "duration_ms": 100}],
        },
        {
            "trace_id": "b2",
            "duration_ms": 110,
            "spans": [{"name": "gateway", "duration_ms": 110}],
        },
        {
            "trace_id": "b3",
            "duration_ms": 90,
            "spans": [{"name": "gateway", "duration_ms": 90}],
        },
    ]  # Mean 100, Stdev 10

    with patch(
        "sre_agent.tools.analysis.trace.statistical_analysis._fetch_traces_parallel",
        return_value=baseline_traces,
    ):
        with patch(
            "sre_agent.tools.analysis.trace.statistical_analysis.fetch_trace_data",
            return_value=mock_trace_data,
        ):
            # Target 1000 -> Z=90! -> Heavy Anomaly
            res = detect_latency_anomalies(["b1", "b2", "b3"], "target_id")
            assert res.status == ToolStatus.SUCCESS
            assert res.result["is_anomaly"] is True
            assert len(res.result["anomalous_spans"]) > 0


def test_perform_causal_analysis_success():
    baseline = {"spans": [{"name": "gateway", "duration_ms": 100}]}
    target = {
        "spans": [
            {
                "span_id": "root",
                "name": "gateway",
                "duration_ms": 1000,
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-01T00:00:01Z",
            }
        ]
    }
    with patch(
        "sre_agent.tools.analysis.trace.statistical_analysis.fetch_trace_data",
        side_effect=[baseline, target],
    ):
        res = perform_causal_analysis("b1", "t1")
        assert res.status == ToolStatus.SUCCESS
        assert res.result["root_cause_candidates"][0]["is_likely_root_cause"] is True


def test_analyze_trace_patterns_trends():
    traces = [
        {
            "duration_ms": 100,
            "trace_id": "v1",
            "spans": [{"name": "s1", "duration_ms": 10, "labels": {"error": "true"}}],
        },
        {
            "duration_ms": 100,
            "trace_id": "v2",
            "spans": [{"name": "s1", "duration_ms": 1000}],
        },
        {
            "duration_ms": 200,
            "trace_id": "v3",
            "spans": [{"name": "s1", "duration_ms": 10}],
        },
        {
            "duration_ms": 200,
            "trace_id": "v4",
            "spans": [{"name": "s1", "duration_ms": 1000}],
        },
    ]  # Mean ~500, Stdev ~570, CV > 1.0 -> High Variance / Intermittent

    with patch(
        "sre_agent.tools.analysis.trace.statistical_analysis._fetch_traces_parallel",
        return_value=traces,
    ):
        res = analyze_trace_patterns(["t1", "t2", "t3", "t4"])
        assert res.result["overall_trend"] == "degrading"
        assert len(res.result["patterns"]["intermittent_issues"]) > 0


def test_compute_service_level_stats_various():
    traces = [
        {
            "spans": [
                {
                    "labels": {"service": "s1", "error": "yes"},
                    "start_time": "2024-01-01T00:00:00Z",
                    "end_time": "2024-01-01T00:00:01Z",
                },
                {
                    "labels": {"app": "s2"},
                    "start_time": "2024-01-01T00:00:00Z",
                    "end_time": "2024-01-01T00:00:00.5Z",
                },
            ]
        }
    ]
    with patch(
        "sre_agent.tools.analysis.trace.statistical_analysis._fetch_traces_parallel",
        return_value=traces,
    ):
        res = compute_service_level_stats(["t1"])
        assert res.status == ToolStatus.SUCCESS
        assert res.result["s1"]["error_rate"] == 100.0
