"""Edge case tests for Trace Analysis."""

from unittest.mock import MagicMock, patch

import pytest

from sre_agent.schema import ToolStatus
from sre_agent.tools.analysis.trace.analysis import (
    _calculate_span_durations_impl,
    _extract_errors_impl,
    build_call_graph,
    calculate_span_durations,
    extract_errors,
    summarize_trace,
    validate_trace_quality,
)


@pytest.fixture
def mock_clients():
    with patch(
        "sre_agent.tools.analysis.trace.analysis.fetch_trace_data"
    ) as mock_fetch:
        with patch(
            "sre_agent.tools.clients.trace.get_credentials_from_tool_context",
            return_value=MagicMock(),
        ):
            with patch(
                "sre_agent.tools.clients.trace._set_thread_credentials"
            ) as mock_set:
                with patch(
                    "sre_agent.tools.clients.trace._clear_thread_credentials"
                ) as mock_clear:
                    yield mock_fetch, mock_set, mock_clear


def test_calculate_span_durations_impl_unix():
    trace = {
        "spans": [
            {
                "name": "op",
                "span_id": "1",
                "start_time_unix": 1000.0,
                "end_time_unix": 1000.5,
            }
        ]
    }
    result = _calculate_span_durations_impl(trace)
    assert result[0]["duration_ms"] == 500.0


def test_calculate_span_durations_impl_bad_timestamps():
    trace = {
        "spans": [
            {
                "span_id": "1",
                "name": "bad",
                "start_time": "invalid",
                "end_time": "invalid",
            }
        ]
    }
    result = _calculate_span_durations_impl(trace)
    assert result[0]["duration_ms"] is None


def test_calculate_span_durations_tool_error(mock_clients):
    mock_fetch, _, _ = mock_clients
    mock_fetch.return_value = {"error": "API Limit"}
    res = calculate_span_durations("t1")
    assert res["status"] == ToolStatus.ERROR
    assert res["error"] == "API Limit"


def test_calculate_span_durations_exception(mock_clients):
    mock_fetch, _, _ = mock_clients
    mock_fetch.side_effect = Exception("Fatal")
    with pytest.raises(Exception, match="Fatal"):
        calculate_span_durations("t1")


def test_extract_errors_tool_error(mock_clients):
    mock_fetch, _, _ = mock_clients
    mock_fetch.return_value = {"error": "Auth Failed"}
    res = extract_errors("t1")
    assert res["status"] == ToolStatus.ERROR
    assert res["error"] == "Auth Failed"


def test_extract_errors_exception(mock_clients):
    mock_fetch, _, _ = mock_clients
    mock_fetch.side_effect = Exception("Explosion")
    with pytest.raises(Exception, match="Explosion"):
        extract_errors("t1")


def test_extract_errors_impl_status_parse_error():
    trace = {
        "spans": [
            {"span_id": "1", "labels": {"/http/status_code": "NaN"}},
            {"span_id": "2", "labels": {"status": "NaN"}},
        ]
    }
    result = _extract_errors_impl(trace)
    assert len(result) == 0


def test_extract_errors_impl_grpc_and_indicators():
    trace = {
        "spans": [
            {
                "span_id": "g1",
                "labels": {"grpc.status": "14"},  # UNAVAILABLE
            },
            {"span_id": "f1", "labels": {"fault": "true"}},
            {"span_id": "ok1", "labels": {"error": "false", "failure": "none"}},
        ]
    }
    result = _extract_errors_impl(trace)
    assert len(result) == 2
    ids = [r["span_id"] for r in result]
    assert "g1" in ids
    assert "f1" in ids


def test_validate_trace_quality_edge_cases():
    # 1. Fetch Error
    res = validate_trace_quality({"error": "Not Found", "trace_id": "t1"})
    assert res["status"] == ToolStatus.ERROR

    # 2. Missing ID
    res = validate_trace_quality({"spans": [{"name": "n"}]})
    assert res["result"]["issue_count"] == 1
    assert res["result"]["issues"][0]["type"] == "missing_span_id"

    # 3. Negative Duration
    res = validate_trace_quality(
        {
            "spans": [
                {
                    "span_id": "1",
                    "start_time": "2024-01-01T00:00:01Z",
                    "end_time": "2024-01-01T00:00:00Z",
                }
            ]
        }
    )
    assert res["result"]["issues"][0]["type"] == "negative_duration"

    # 4. Clock Skew
    res = validate_trace_quality(
        {
            "spans": [
                {
                    "span_id": "p",
                    "start_time": "2024-01-01T01:00:00Z",
                    "end_time": "2024-01-01T02:00:00Z",
                },
                {
                    "span_id": "c",
                    "parent_span_id": "p",
                    "start_time": "2024-01-01T00:59:00Z",
                    "end_time": "2024-01-01T01:30:00Z",
                },
            ]
        }
    )
    assert any(i["type"] == "clock_skew" for i in res["result"]["issues"])

    # 5. Timestamp Error
    res = validate_trace_quality(
        {"spans": [{"span_id": "1", "start_time": "!!!", "end_time": "!!!"}]}
    )
    assert res["result"]["issues"][0]["type"] == "timestamp_error"


def test_validate_trace_quality_exception():
    with patch(
        "sre_agent.tools.analysis.trace.analysis.fetch_trace_data",
        side_effect=Exception("Hard Fail"),
    ):
        res = validate_trace_quality("t1")
        assert res["status"] == ToolStatus.ERROR
        assert "Hard Fail" in res["error"]


def test_build_call_graph_exception():
    with patch(
        "sre_agent.tools.analysis.trace.analysis.fetch_trace_data",
        side_effect=Exception("Boom"),
    ):
        with pytest.raises(Exception, match="Boom"):
            build_call_graph("t1")


def test_summarize_trace_various_paths():
    # 1. Error path
    with patch(
        "sre_agent.tools.analysis.trace.analysis.fetch_trace_data",
        return_value={"error": "Broke", "trace_id": "t1"},
    ):
        res = summarize_trace("t1")
        assert res["status"] == ToolStatus.ERROR

    # 2. Missing spans key (hits extract_errors fallback)
    trace_no_spans = {"trace_id": "t1", "duration_ms": 100}
    with patch(
        "sre_agent.tools.analysis.trace.analysis.fetch_trace_data",
        return_value=trace_no_spans,
    ):
        with patch(
            "sre_agent.tools.analysis.trace.analysis.extract_errors"
        ) as mock_ext:
            mock_ext.return_value = MagicMock(result={"errors": []})
            res = summarize_trace("t1")
            assert res["status"] == ToolStatus.SUCCESS
            mock_ext.assert_called_once()

    # 3. Full data with manual time parsing coverage
    trace_full = {
        "trace_id": "t1",
        "duration_ms": 1000,
        "spans": [
            {
                "name": "s1",
                "start_time": "2024-01-01T01:00:00Z",
                "end_time": "2024-01-01T01:00:01Z",
            },
            {"name": "s2", "start_time": "invalid", "end_time": "invalid"},
        ],
    }
    with patch(
        "sre_agent.tools.analysis.trace.analysis.fetch_trace_data",
        return_value=trace_full,
    ):
        res = summarize_trace("t1")
        assert res["status"] == ToolStatus.SUCCESS
        assert len(res["result"]["slowest_spans"]) == 2
