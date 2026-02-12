from sre_agent.schema import ToolStatus
from sre_agent.tools.analysis.trace.analysis import validate_trace_quality


def test_validate_trace_quality_optimization_unix_timestamps():
    """Test that validation works correctly when unix timestamps are present (optimized path)."""
    trace = {
        "trace_id": "optimized-trace",
        "spans": [
            {
                "span_id": "root",
                "name": "root",
                "start_time": "2023-01-01T10:00:00Z",
                "end_time": "2023-01-01T10:00:01Z",
                "start_time_unix": 1672567200.0,
                "end_time_unix": 1672567201.0,
                "parent_span_id": None,
            },
            {
                "span_id": "child_skewed",
                "name": "child",
                "start_time": "2023-01-01T10:00:02Z",  # Starts after parent ends
                "end_time": "2023-01-01T10:00:03Z",
                "start_time_unix": 1672567202.0,
                "end_time_unix": 1672567203.0,
                "parent_span_id": "root",
            },
            {
                "span_id": "negative_duration",
                "name": "negative",
                "start_time": "2023-01-01T10:00:05Z",
                "end_time": "2023-01-01T10:00:04Z",  # Ends before start
                "start_time_unix": 1672567205.0,
                "end_time_unix": 1672567204.0,
                "parent_span_id": "root",
            },
        ],
    }

    result = validate_trace_quality(trace)
    assert result.status == ToolStatus.SUCCESS
    res_data = result.result

    assert res_data["valid"] is False
    assert res_data["issue_count"] == 3

    issues = res_data["issues"]
    skew_issues = [i for i in issues if i["type"] == "clock_skew"]
    negative_issues = [i for i in issues if i["type"] == "negative_duration"]

    assert len(skew_issues) == 2
    assert len(negative_issues) == 1

    assert any(i["span_id"] == "child_skewed" for i in skew_issues)
    assert any(i["span_id"] == "negative_duration" for i in skew_issues)
    assert negative_issues[0]["span_id"] == "negative_duration"


def test_validate_trace_quality_fallback_string_parsing():
    """Test that validation falls back to string parsing when unix timestamps are missing."""
    trace = {
        "trace_id": "fallback-trace",
        "spans": [
            {
                "span_id": "root",
                "name": "root",
                "start_time": "2023-01-01T10:00:00Z",
                "end_time": "2023-01-01T10:00:01Z",
                # Missing unix timestamps
                "parent_span_id": None,
            },
            {
                "span_id": "child_skewed",
                "name": "child",
                "start_time": "2023-01-01T10:00:02Z",
                "end_time": "2023-01-01T10:00:03Z",
                "parent_span_id": "root",
            },
            {
                "span_id": "negative_duration",
                "name": "negative",
                "start_time": "2023-01-01T10:00:05Z",
                "end_time": "2023-01-01T10:00:04Z",
                "parent_span_id": "root",
            },
        ],
    }

    result = validate_trace_quality(trace)
    assert result.status == ToolStatus.SUCCESS
    res_data = result.result

    assert res_data["valid"] is False
    assert res_data["issue_count"] == 3

    issues = res_data["issues"]
    skew_issues = [i for i in issues if i["type"] == "clock_skew"]
    negative_issues = [i for i in issues if i["type"] == "negative_duration"]

    assert len(skew_issues) == 2
    assert len(negative_issues) == 1


def test_validate_trace_quality_priority():
    """Test that unix timestamps are prioritized over strings when both are present."""
    trace = {
        "trace_id": "priority-trace",
        "spans": [
            {
                "span_id": "span1",
                "name": "span1",
                # Strings say this is valid (positive duration)
                "start_time": "2023-01-01T10:00:00Z",
                "end_time": "2023-01-01T10:00:01Z",
                # Unix timestamps say this is invalid (negative duration)
                "start_time_unix": 1672567205.0,
                "end_time_unix": 1672567204.0,
                "parent_span_id": None,
            }
        ],
    }

    result = validate_trace_quality(trace)
    assert result.status == ToolStatus.SUCCESS
    res_data = result.result

    # Asserting that the issue IS found (optimization active and prioritized)
    assert not res_data["valid"]
    assert res_data["issue_count"] == 1
    assert res_data["issues"][0]["type"] == "negative_duration"
