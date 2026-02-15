
import pytest
from datetime import datetime, timedelta
from typing import Any
from sre_agent.tools.analysis.trace.analysis import _validate_trace_quality_impl

class TestValidateTraceOptimization:
    def test_optimized_path_valid(self):
        """Test validation using unix timestamps (optimized path)."""
        base_time = datetime.fromisoformat("2023-01-01T12:00:00+00:00")
        start_ts = base_time.timestamp()
        end_ts = start_ts + 1.0  # 1 second duration

        trace = {
            "trace_id": "optimized-valid",
            "spans": [
                {
                    "span_id": "root",
                    "name": "root",
                    "start_time": base_time.isoformat(),
                    "end_time": (base_time + timedelta(seconds=1)).isoformat(),
                    "start_time_unix": start_ts,
                    "end_time_unix": end_ts,
                }
            ]
        }

        result = _validate_trace_quality_impl(trace)
        assert result["valid"] is True
        assert result["issue_count"] == 0

    def test_optimized_path_negative_duration_no_strings(self):
        """Test negative duration detection using ONLY unix timestamps."""
        start_ts = 1000.0
        end_ts = 999.0  # Negative duration

        trace = {
            "trace_id": "optimized-negative",
            "spans": [
                {
                    "span_id": "span1",
                    "name": "span1",
                    # No string timestamps provided
                    "start_time_unix": start_ts,
                    "end_time_unix": end_ts,
                }
            ]
        }

        result = _validate_trace_quality_impl(trace)
        assert result["valid"] is False
        issues = result["issues"]
        assert any(i["type"] == "negative_duration" for i in issues)

    def test_optimized_path_clock_skew_no_strings(self):
        """Test clock skew detection using ONLY unix timestamps."""
        # Parent: 1000-1010
        # Child:  0999-1005 (Starts before parent)

        trace = {
            "trace_id": "optimized-skew",
            "spans": [
                {
                    "span_id": "parent",
                    "name": "parent",
                    # No string timestamps
                    "start_time_unix": 1000.0,
                    "end_time_unix": 1010.0,
                },
                {
                    "span_id": "child",
                    "name": "child",
                    "parent_span_id": "parent",
                    # No string timestamps
                    "start_time_unix": 999.0,
                    "end_time_unix": 1005.0,
                }
            ]
        }

        result = _validate_trace_quality_impl(trace)
        assert result["valid"] is False
        assert any(i["type"] == "clock_skew" for i in result["issues"])

    def test_fallback_path_valid(self):
        """Test validation falling back to string parsing."""
        trace = {
            "trace_id": "fallback-valid",
            "spans": [
                {
                    "span_id": "root",
                    "name": "root",
                    "start_time": "2023-01-01T12:00:00Z",
                    "end_time": "2023-01-01T12:00:01Z",
                    # No unix timestamps
                }
            ]
        }

        result = _validate_trace_quality_impl(trace)
        assert result["valid"] is True

    def test_fallback_path_clock_skew(self):
        """Test clock skew detection using string parsing."""
        trace = {
            "trace_id": "fallback-skew",
            "spans": [
                {
                    "span_id": "parent",
                    "start_time": "2023-01-01T12:00:10Z",
                    "end_time": "2023-01-01T12:00:20Z",
                },
                {
                    "span_id": "child",
                    "parent_span_id": "parent",
                    "start_time": "2023-01-01T12:00:09Z", # Starts before parent
                    "end_time": "2023-01-01T12:00:15Z",
                }
            ]
        }

        result = _validate_trace_quality_impl(trace)
        assert result["valid"] is False
        assert any(i["type"] == "clock_skew" for i in result["issues"])

    def test_mixed_timestamps_clock_skew(self):
        """Test clock skew detection when child has unix but parent only has strings."""
        # This exercises the fallback path inside the optimized block

        parent_start = datetime.fromisoformat("2023-01-01T12:00:10+00:00")

        trace = {
            "trace_id": "mixed-skew",
            "spans": [
                {
                    "span_id": "parent",
                    "start_time": "2023-01-01T12:00:10Z",
                    "end_time": "2023-01-01T12:00:20Z",
                    # No unix timestamps for parent
                },
                {
                    "span_id": "child",
                    "parent_span_id": "parent",
                    "start_time_unix": parent_start.timestamp() - 1.0, # Starts 1s before parent
                    "end_time_unix": parent_start.timestamp() + 5.0,
                    # No string timestamps for child (forces usage of optimized path for child, fallback for parent)
                }
            ]
        }

        result = _validate_trace_quality_impl(trace)
        assert result["valid"] is False
        assert any(i["type"] == "clock_skew" for i in result["issues"])
