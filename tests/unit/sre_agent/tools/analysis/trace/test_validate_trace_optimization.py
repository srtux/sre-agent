from unittest.mock import patch

from sre_agent.tools.analysis.trace.analysis import _validate_trace_quality_impl


def test_validate_trace_quality_uses_unix_timestamps():
    """Test that validation uses unix timestamps if available, avoiding slow datetime parsing."""
    trace = {
        "spans": [
            {
                "span_id": "root",
                "start_time": "2023-01-01T12:00:00Z",
                "end_time": "2023-01-01T12:00:01Z",
                "start_time_unix": 1672574400.0,
                "end_time_unix": 1672574401.0,
                "parent_span_id": None,
            },
            {
                "span_id": "child",
                "start_time": "2023-01-01T12:00:00.100Z",
                "end_time": "2023-01-01T12:00:00.200Z",
                "start_time_unix": 1672574400.1,
                "end_time_unix": 1672574400.2,
                "parent_span_id": "root",
            },
        ]
    }

    # Patch datetime to ensure fromisoformat is NOT called
    with patch("sre_agent.tools.analysis.trace.analysis.datetime") as mock_datetime:
        # We need to allow datetime.fromisoformat to be called if it IS called,
        # but we want to assert that it wasn't.
        # However, since we are patching the class, we can just assert on the mock.

        result = _validate_trace_quality_impl(trace)

        assert result["valid"] is True
        assert len(result["issues"]) == 0

        # Verify fromisoformat was NOT called
        mock_datetime.fromisoformat.assert_not_called()


def test_validate_trace_quality_fallback():
    """Test that validation falls back to string parsing if unix timestamps are missing."""
    trace = {
        "spans": [
            {
                "span_id": "root",
                "start_time": "2023-01-01T12:00:00Z",
                "end_time": "2023-01-01T12:00:01Z",
                # No unix timestamps
                "parent_span_id": None,
            }
        ]
    }

    # Here we EXPECT fromisoformat to be called
    with patch("sre_agent.tools.analysis.trace.analysis.datetime") as mock_datetime:
        # Make the mock behave like real datetime for the return values we need for comparison?
        # Actually, since we are patching the module 'sre_agent.tools.analysis.trace.analysis',
        # we are replacing the imported datetime.

        # To make the test logic work with the mock, we need the mock to return objects that support subtraction and comparison.
        # But for this specific test, we just want to verify it IS called.
        # We can let it return a MagicMock which supports operations.

        # However, _validate_trace_quality_impl does `(end - start).total_seconds()`.
        # So the return value of fromisoformat must support this.

        mock_dt_obj = mock_datetime.fromisoformat.return_value
        mock_dt_obj.__sub__.return_value.total_seconds.return_value = 1.0

        _validate_trace_quality_impl(trace)

        assert mock_datetime.fromisoformat.call_count == 2  # start and end


def test_validate_trace_quality_clock_skew_optimization():
    """Test that clock skew check uses unix timestamps."""
    trace = {
        "spans": [
            {
                "span_id": "root",
                "start_time": "2023-01-01T12:00:00Z",
                "end_time": "2023-01-01T12:00:01Z",
                "start_time_unix": 1672574400.0,
                "end_time_unix": 1672574401.0,
                "parent_span_id": None,
            },
            {
                "span_id": "child",
                "start_time": "2023-01-01T11:59:59Z",  # Skewed (starts before parent)
                "end_time": "2023-01-01T12:00:00.200Z",
                "start_time_unix": 1672574399.0,  # Skewed
                "end_time_unix": 1672574400.2,
                "parent_span_id": "root",
            },
        ]
    }

    with patch("sre_agent.tools.analysis.trace.analysis.datetime") as mock_datetime:
        result = _validate_trace_quality_impl(trace)

        assert result["valid"] is False
        assert any(i["type"] == "clock_skew" for i in result["issues"])

        mock_datetime.fromisoformat.assert_not_called()
