"""Edge case tests for Trace Comparison."""

from unittest.mock import patch

import pytest

from sre_agent.schema import BaseToolResponse, ToolStatus
from sre_agent.tools.analysis.trace.comparison import (
    compare_span_timings,
    find_structural_differences,
)


@pytest.fixture
def mock_analysis():
    with patch(
        "sre_agent.tools.analysis.trace.comparison.calculate_span_durations"
    ) as mock_dur:
        with patch(
            "sre_agent.tools.analysis.trace.comparison.build_call_graph"
        ) as mock_graph:
            yield mock_dur, mock_graph


def test_compare_span_timings_error_handling(mock_analysis):
    mock_dur, _ = mock_analysis

    # 1. Baseline Error
    mock_dur.return_value = BaseToolResponse(status=ToolStatus.ERROR, error="B1")
    res = compare_span_timings("b1", "t1")
    assert res.status == ToolStatus.ERROR
    assert "Baseline" in res.error

    # 2. Target Error
    mock_dur.side_effect = [
        BaseToolResponse(status=ToolStatus.SUCCESS, result={"spans": []}),
        BaseToolResponse(status=ToolStatus.ERROR, error="T1"),
    ]
    res = compare_span_timings("b1", "t1")
    assert res.status == ToolStatus.ERROR
    assert "Target" in res.error


def test_compare_span_timings_n_plus_one_inside_loop(mock_analysis):
    mock_dur, _ = mock_analysis

    target_spans = [
        {
            "span_id": "1",
            "name": "db",
            "start_time": "2024-01-01T00:00:00.000Z",
            "duration_ms": 100,
        },
        {
            "span_id": "2",
            "name": "db",
            "start_time": "2024-01-01T00:00:00.100Z",
            "duration_ms": 100,
        },
        {
            "span_id": "3",
            "name": "db",
            "start_time": "2024-01-01T00:00:00.200Z",
            "duration_ms": 100,
        },
        {
            "span_id": "4",
            "name": "other",
            "start_time": "2024-01-01T00:00:00.300Z",
            "duration_ms": 10,
        },
    ]  # Triggers check inside loop when 'other' is encountered

    mock_dur.side_effect = [
        BaseToolResponse(status=ToolStatus.SUCCESS, result={"spans": []}),
        BaseToolResponse(status=ToolStatus.SUCCESS, result={"spans": target_spans}),
    ]

    res = compare_span_timings("b1", "t1")
    assert res.status == ToolStatus.SUCCESS
    patterns = res.result["patterns"]
    assert any(p["type"] == "n_plus_one" for p in patterns)


def test_compare_span_timings_serial_chain_gaps_and_parents(mock_analysis):
    mock_dur, _ = mock_analysis

    target_spans = [
        # Chain 1: p-c relationship (should break chain)
        {
            "span_id": "p",
            "name": "p",
            "start_time": "2024-01-01T00:00:00.000Z",
            "end_time": "2024-01-01T00:00:00.100Z",
            "duration_ms": 100,
        },
        {
            "span_id": "c",
            "parent_span_id": "p",
            "name": "c",
            "start_time": "2024-01-01T00:00:00.101Z",
            "end_time": "2024-01-01T00:00:00.201Z",
            "duration_ms": 100,
        },
        # Chain 2: large gap
        {
            "span_id": "3",
            "name": "s3",
            "start_time": "2024-01-01T00:00:00.500Z",
            "end_time": "2024-01-01T00:00:00.600Z",
            "duration_ms": 100,
        },
        {
            "span_id": "4",
            "name": "s4",
            "start_time": "2024-01-01T00:00:01.000Z",
            "end_time": "2024-01-01T00:00:01.100Z",
            "duration_ms": 100,
        },
    ]

    mock_dur.side_effect = [
        BaseToolResponse(status=ToolStatus.SUCCESS, result={"spans": []}),
        BaseToolResponse(status=ToolStatus.SUCCESS, result={"spans": target_spans}),
    ]

    res = compare_span_timings("b1", "t1")
    assert res.status == ToolStatus.SUCCESS


def test_compare_span_timings_faster_spans(mock_analysis):
    mock_dur, _ = mock_analysis
    mock_dur.side_effect = [
        BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={"spans": [{"name": "fast", "duration_ms": 1000}]},
        ),
        BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={"spans": [{"name": "fast", "duration_ms": 100}]},
        ),
    ]
    res = compare_span_timings("b1", "t1")
    assert len(res.result["faster_spans"]) == 1


def test_find_structural_differences_success(mock_analysis):
    _, mock_graph = mock_analysis

    mock_graph.side_effect = [
        BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={"span_names": ["s1"], "max_depth": 1, "total_spans": 1},
        ),
        BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={"span_names": ["s1", "s2"], "max_depth": 3, "total_spans": 2},
        ),
    ]

    res = find_structural_differences("b1", "t1")
    assert res.status == ToolStatus.SUCCESS
    result = res.result
    assert result["depth_change"] == 2
    assert "s2" in result["new_spans"]


def test_find_structural_differences_error_handling(mock_analysis):
    _, mock_graph = mock_analysis

    # 1. Baseline Error
    mock_graph.return_value = BaseToolResponse(status=ToolStatus.ERROR, error="GB1")
    res = find_structural_differences("b1", "t1")
    assert res.status == ToolStatus.ERROR
    assert "GB1" in res.error

    # 2. Target Error
    mock_graph.side_effect = [
        BaseToolResponse(status=ToolStatus.SUCCESS, result={}),
        BaseToolResponse(status=ToolStatus.ERROR, error="GT1"),
    ]
    res = find_structural_differences("b1", "t1")
    assert res.status == ToolStatus.ERROR
    assert "GT1" in res.error


def test_find_structural_differences_exception(mock_analysis):
    _, mock_graph = mock_analysis
    mock_graph.side_effect = Exception("Graph Boom")
    res = find_structural_differences("b1", "t1")
    assert res.status == ToolStatus.ERROR
    assert "Graph Boom" in res.error
