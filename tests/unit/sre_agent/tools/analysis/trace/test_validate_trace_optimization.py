import pytest

from sre_agent.tools.analysis.trace.analysis import _validate_trace_quality_impl


@pytest.fixture
def valid_unix_trace():
    return {
        "trace_id": "unix-trace",
        "spans": [
            {
                "span_id": "root",
                "start_time_unix": 1000.0,
                "end_time_unix": 1010.0,
                "start_time": "2023-01-01T00:00:00Z",  # Should be ignored if optimization works
                "end_time": "2023-01-01T00:00:10Z",
            },
            {
                "span_id": "child",
                "parent_span_id": "root",
                "start_time_unix": 1001.0,
                "end_time_unix": 1005.0,
                "start_time": "2023-01-01T00:00:01Z",
                "end_time": "2023-01-01T00:00:05Z",
            },
        ],
    }


def test_fast_path_valid(valid_unix_trace):
    """Test that valid trace with unix timestamps passes validation."""
    result = _validate_trace_quality_impl(valid_unix_trace)
    assert result["valid"] is True
    assert result["issue_count"] == 0


def test_fast_path_clock_skew():
    """Test that clock skew is detected using unix timestamps."""
    trace = {
        "trace_id": "skew-trace",
        "spans": [
            {
                "span_id": "root",
                "start_time_unix": 1000.0,
                "end_time_unix": 1010.0,
                "start_time": "ignored",
                "end_time": "ignored",
            },
            {
                "span_id": "child_bad_start",
                "parent_span_id": "root",
                "start_time_unix": 999.0,  # Before parent
                "end_time_unix": 1005.0,
                "start_time": "ignored",
                "end_time": "ignored",
            },
        ],
    }
    result = _validate_trace_quality_impl(trace)
    assert result["valid"] is False
    assert result["issue_count"] == 1
    assert result["issues"][0]["type"] == "clock_skew"
    assert result["issues"][0]["span_id"] == "child_bad_start"


def test_fast_path_negative_duration():
    """Test that negative duration is detected using unix timestamps."""
    trace = {
        "trace_id": "neg-trace",
        "spans": [
            {
                "span_id": "span1",
                "start_time_unix": 1005.0,
                "end_time_unix": 1000.0,  # Negative duration
                "start_time": "ignored",
                "end_time": "ignored",
            }
        ],
    }
    result = _validate_trace_quality_impl(trace)
    assert result["valid"] is False
    assert result["issues"][0]["type"] == "negative_duration"


def test_fallback_path_no_unix():
    """Test fallback to string parsing when unix timestamps are missing."""
    trace = {
        "trace_id": "string-trace",
        "spans": [
            {
                "span_id": "root",
                "start_time": "2023-01-01T00:00:00Z",
                "end_time": "2023-01-01T00:00:10Z",
            },
            {
                "span_id": "child_skew",
                "parent_span_id": "root",
                "start_time": "2022-12-31T23:59:59Z",  # Skew
                "end_time": "2023-01-01T00:00:05Z",
            },
        ],
    }
    result = _validate_trace_quality_impl(trace)
    assert result["valid"] is False
    assert result["issues"][0]["type"] == "clock_skew"


def test_mixed_path_child_unix_parent_string():
    """Test optimization handles case where child has unix ts but parent only has strings."""
    # 1000.0 unix is 2023-01-01T00:16:40Z ? No.
    # 0 unix is 1970-01-01

    # Let's align times.
    base_ts = 1672531200.0  # 2023-01-01 00:00:00 UTC

    trace = {
        "trace_id": "mixed-trace",
        "spans": [
            {
                "span_id": "root",
                "start_time": "2023-01-01T00:00:00Z",  # 1672531200.0
                "end_time": "2023-01-01T00:00:10Z",  # 1672531210.0
                # No unix timestamps
            },
            {
                "span_id": "child_ok",
                "parent_span_id": "root",
                "start_time_unix": base_ts + 1,
                "end_time_unix": base_ts + 5,
                "start_time": "ignored",
                "end_time": "ignored",
            },
            {
                "span_id": "child_skew",
                "parent_span_id": "root",
                "start_time_unix": base_ts - 1,  # Skew
                "end_time_unix": base_ts + 5,
                "start_time": "ignored",
                "end_time": "ignored",
            },
        ],
    }

    result = _validate_trace_quality_impl(trace)

    issues = result["issues"]
    assert any(
        i["span_id"] == "child_skew" and i["type"] == "clock_skew" for i in issues
    )
    assert not any(i["span_id"] == "child_ok" for i in issues)


def test_priority_of_unix_over_string():
    """Verify that unix timestamps are used even if they contradict strings (proving optimization is used)."""
    trace = {
        "trace_id": "prio-trace",
        "spans": [
            {
                "span_id": "span1",
                "start_time_unix": 1000.0,
                "end_time_unix": 1005.0,  # Valid duration 5.0
                # Invalid strings that would fail parsing or show negative duration
                "start_time": "2023-01-01T00:00:10Z",
                "end_time": "2023-01-01T00:00:00Z",  # Would be negative -10s
            }
        ],
    }
    result = _validate_trace_quality_impl(trace)

    # Should be valid because unix timestamps are valid and prioritized
    assert result["valid"] is True
    assert result["issue_count"] == 0
