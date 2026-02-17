from sre_agent.tools.analysis.trace.analysis import _validate_trace_quality_impl


def test_validate_unix_timestamps_only():
    """Test validation using only unix timestamps (optimized path)."""
    trace = {
        "spans": [
            {
                "span_id": "root",
                "name": "root",
                "start_time_unix": 1000.0,
                "end_time_unix": 1001.0,
            },
            {
                "span_id": "child",
                "name": "child",
                "parent_span_id": "root",
                "start_time_unix": 1000.1,
                "end_time_unix": 1000.9,
            },
        ]
    }
    result = _validate_trace_quality_impl(trace)
    assert result["valid"] is True
    assert result["issue_count"] == 0


def test_validate_string_timestamps_only():
    """Test validation using only string timestamps (fallback path)."""
    trace = {
        "spans": [
            {
                "span_id": "root",
                "name": "root",
                "start_time": "2023-01-01T12:00:00Z",
                "end_time": "2023-01-01T12:00:01Z",
            },
            {
                "span_id": "child",
                "name": "child",
                "parent_span_id": "root",
                "start_time": "2023-01-01T12:00:00.100Z",
                "end_time": "2023-01-01T12:00:00.900Z",
            },
        ]
    }
    result = _validate_trace_quality_impl(trace)
    assert result["valid"] is True
    assert result["issue_count"] == 0


def test_validate_mixed_timestamps():
    """Test validation when one span has unix and another has string."""
    # This shouldn't happen in practice with fetch_trace_data, but good for robustness
    trace = {
        "spans": [
            {
                "span_id": "root",
                "name": "root",
                "start_time": "2023-01-01T12:00:00Z",
                "end_time": "2023-01-01T12:00:01Z",
                # No unix timestamps for root
            },
            {
                "span_id": "child",
                "name": "child",
                "parent_span_id": "root",
                "start_time_unix": 1672574400.1,  # 12:00:00.1
                "end_time_unix": 1672574400.9,  # 12:00:00.9
            },
        ]
    }
    result = _validate_trace_quality_impl(trace)
    assert result["valid"] is True
    assert result["issue_count"] == 0


def test_clock_skew_unix():
    """Test clock skew detection with unix timestamps."""
    trace = {
        "spans": [
            {
                "span_id": "root",
                "start_time_unix": 1000.0,
                "end_time_unix": 1001.0,
            },
            {
                "span_id": "child_bad",
                "parent_span_id": "root",
                "start_time_unix": 999.0,  # Starts before parent
                "end_time_unix": 1000.5,
            },
        ]
    }
    result = _validate_trace_quality_impl(trace)
    assert result["valid"] is False
    assert any(i["type"] == "clock_skew" for i in result["issues"])


def test_clock_skew_string():
    """Test clock skew detection with string timestamps."""
    trace = {
        "spans": [
            {
                "span_id": "root",
                "start_time": "2023-01-01T12:00:00Z",
                "end_time": "2023-01-01T12:00:01Z",
            },
            {
                "span_id": "child_bad",
                "parent_span_id": "root",
                "start_time": "2023-01-01T11:59:59Z",  # Starts before parent
                "end_time": "2023-01-01T12:00:00.500Z",
            },
        ]
    }
    result = _validate_trace_quality_impl(trace)
    assert result["valid"] is False
    assert any(i["type"] == "clock_skew" for i in result["issues"])


def test_negative_duration_unix():
    """Test negative duration detection with unix timestamps."""
    trace = {
        "spans": [
            {
                "span_id": "bad_span",
                "start_time_unix": 1000.0,
                "end_time_unix": 999.0,  # Ends before start
            }
        ]
    }
    result = _validate_trace_quality_impl(trace)
    assert result["valid"] is False
    assert any(i["type"] == "negative_duration" for i in result["issues"])
