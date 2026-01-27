"""Edge case tests for SRE Pattern Detection."""

from unittest.mock import patch

import pytest

from sre_agent.schema import BaseToolResponse, ToolStatus
from sre_agent.tools.analysis.trace.patterns import (
    _get_span_duration,
    _parse_timestamp,
    detect_all_sre_patterns,
    detect_cascading_timeout,
    detect_connection_pool_issues,
    detect_retry_storm,
)


def test_internal_helpers():
    # _parse_timestamp
    assert _parse_timestamp("!!!") is None
    assert _parse_timestamp("2024-01-01T00:00:00Z") > 0

    # _get_span_duration
    assert _get_span_duration({"duration_ms": "123"}) == 123.0
    assert (
        _get_span_duration(
            {"start_time": "2024-01-01T00:00:00Z", "end_time": "2024-01-01T00:00:01Z"}
        )
        == 1000.0
    )
    assert _get_span_duration({}) is None


@pytest.fixture
def mock_fetch():
    with patch("sre_agent.tools.analysis.trace.patterns.fetch_trace_data") as mock:
        yield mock


def test_detect_retry_storm_exponential_backoff(mock_fetch):
    trace = {
        "spans": [
            {
                "name": "op",
                "start_time": "2024-01-01T00:00:00.000Z",
                "end_time": "2024-01-01T00:00:00.010Z",
                "duration_ms": 10,
            },
            {
                "name": "op",
                "start_time": "2024-01-01T00:00:00.020Z",
                "end_time": "2024-01-01T00:00:00.040Z",
                "duration_ms": 20,
            },
            {
                "name": "op",
                "start_time": "2024-01-01T00:00:00.060Z",
                "end_time": "2024-01-01T00:00:00.090Z",
                "duration_ms": 30,
            },
        ]
    }  # Sequential with small gaps, and increasing durations -> exponential backoff
    mock_fetch.return_value = trace
    res = detect_retry_storm("t1", threshold=3)
    assert res.status == ToolStatus.SUCCESS
    assert res.result["retry_patterns"][0]["has_exponential_backoff"] is True


def test_detect_cascading_timeout_subset_and_explicit(mock_fetch):
    trace = {
        "spans": [
            {
                "span_id": "root",
                "name": "root",
                "labels": {"error.type": "timeout"},
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-01T00:00:01Z",
            },
            {
                "span_id": "child",
                "parent_span_id": "root",
                "name": "child",
                "labels": {"status": "deadline_exceeded"},
                "start_time": "2024-01-01T00:00:00.1Z",
                "end_time": "2024-01-01T00:00:00.9Z",
            },
        ]
    }
    mock_fetch.return_value = trace
    res = detect_cascading_timeout("t1")
    assert res.status == ToolStatus.SUCCESS
    assert res.result["cascade_detected"] is True
    assert len(res.result["cascade_chains"]) == 1  # Subset should be removed


def test_detect_connection_pool_severities(mock_fetch):
    trace = {
        "spans": [
            {"name": "pool acquire", "duration_ms": 150},  # medium
            {"name": "pool pool", "duration_ms": 550},  # high
            {"name": "pool checkout", "duration_ms": 110},  # low
            {
                "name": "pool wait",
                "duration_ms": 50,
                "labels": {"pool.size": 10, "pool.active": 10, "pool.waiting": 5},
            },
        ]
    }
    mock_fetch.return_value = trace
    res = detect_connection_pool_issues("t1", wait_threshold_ms=100)
    # Note: the 4th span is NOT included because 50 < 100
    issues = res.result["pool_issues"]
    sev = [i["severity"] for i in issues]
    assert "high" in sev
    assert "low" in sev


def test_detect_all_sre_patterns_health_mapping(mock_fetch):
    # 1. Critical (cascading timeout)
    with patch(
        "sre_agent.tools.analysis.trace.patterns.detect_cascading_timeout"
    ) as mock_ct:
        mock_ct.return_value = BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={
                "cascade_detected": True,
                "impact": "critical",
                "cascade_chains": [],
            },
        )
        with patch(
            "sre_agent.tools.analysis.trace.patterns.detect_retry_storm",
            return_value=BaseToolResponse(status=ToolStatus.SUCCESS, result={}),
        ):
            with patch(
                "sre_agent.tools.analysis.trace.patterns.detect_connection_pool_issues",
                return_value=BaseToolResponse(status=ToolStatus.SUCCESS, result={}),
            ):
                res = detect_all_sre_patterns("t1")
                assert res.result["overall_health"] == "critical"

    # 2. Degraded (retry storm)
    with patch("sre_agent.tools.analysis.trace.patterns.detect_retry_storm") as mock_rs:
        mock_rs.return_value = BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={"has_retry_storm": True, "retry_patterns": [{"impact": "high"}]},
        )
        with patch(
            "sre_agent.tools.analysis.trace.patterns.detect_cascading_timeout",
            return_value=BaseToolResponse(status=ToolStatus.SUCCESS, result={}),
        ):
            with patch(
                "sre_agent.tools.analysis.trace.patterns.detect_connection_pool_issues",
                return_value=BaseToolResponse(status=ToolStatus.SUCCESS, result={}),
            ):
                res = detect_all_sre_patterns("t1")
                assert res.result["overall_health"] == "degraded"

    # 3. Warning (low impact pattern)
    with patch("sre_agent.tools.analysis.trace.patterns.detect_retry_storm") as mock_rs:
        mock_rs.return_value = BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={"has_retry_storm": True, "retry_patterns": [{"impact": "low"}]},
        )
        with patch(
            "sre_agent.tools.analysis.trace.patterns.detect_cascading_timeout",
            return_value=BaseToolResponse(status=ToolStatus.SUCCESS, result={}),
        ):
            with patch(
                "sre_agent.tools.analysis.trace.patterns.detect_connection_pool_issues",
                return_value=BaseToolResponse(status=ToolStatus.SUCCESS, result={}),
            ):
                res = detect_all_sre_patterns("t1")
                assert res.result["overall_health"] == "warning"

    # 4. Connection pool exhaustion
    with patch(
        "sre_agent.tools.analysis.trace.patterns.detect_connection_pool_issues"
    ) as mock_cp:
        mock_cp.return_value = BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={
                "has_pool_exhaustion": True,
                "pool_issues": [],
                "total_wait_ms": 1000,
            },
        )
        with patch(
            "sre_agent.tools.analysis.trace.patterns.detect_retry_storm",
            return_value=BaseToolResponse(status=ToolStatus.SUCCESS, result={}),
        ):
            with patch(
                "sre_agent.tools.analysis.trace.patterns.detect_cascading_timeout",
                return_value=BaseToolResponse(status=ToolStatus.SUCCESS, result={}),
            ):
                res = detect_all_sre_patterns("t1")
                assert any(
                    p["pattern_type"] == "connection_pool_exhaustion"
                    for p in res.result["patterns"]
                )


def test_detectors_error_paths(mock_fetch):
    mock_fetch.return_value = {"error": "API Failure"}

    assert detect_retry_storm("t1").status == ToolStatus.ERROR
    assert detect_cascading_timeout("t1").status == ToolStatus.ERROR
    assert detect_connection_pool_issues("t1").status == ToolStatus.ERROR


def test_detect_all_patterns_exception():
    with patch(
        "sre_agent.tools.analysis.trace.patterns.detect_retry_storm",
        side_effect=Exception("Global Fail"),
    ):
        res = detect_all_sre_patterns("t1")
        assert res.status == ToolStatus.ERROR
        assert "Global Fail" in res.error
