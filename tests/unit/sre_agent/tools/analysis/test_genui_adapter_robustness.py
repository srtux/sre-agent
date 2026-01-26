from sre_agent.tools.analysis.genui_adapter import (
    transform_log_entries,
    transform_log_patterns,
    transform_metrics,
    transform_trace,
)


def test_transform_trace_wrapped():
    # Test MCP-style wrapped response
    wrapped_trace = {
        "status": "success",
        "result": {
            "trace_id": "wrapped-trace-123",
            "spans": [
                {
                    "span_id": "span-1",
                    "labels": {"/http/status_code": "200"},
                }
            ],
        },
    }

    transformed = transform_trace(wrapped_trace)
    assert transformed["trace_id"] == "wrapped-trace-123"
    assert len(transformed["spans"]) == 1
    assert transformed["spans"][0]["status"] == "OK"


def test_transform_trace_error():
    # Test error response handling
    error_response = {
        "status": "error",
        "error": "Trace not found",
        "trace_id": "missing-trace",
    }

    transformed = transform_trace(error_response)
    assert transformed["trace_id"] == "missing-trace"
    assert len(transformed["spans"]) == 0
    assert transformed["error"] == "Trace not found"


def test_transform_metrics_wrapped():
    # Test wrapped metrics response
    wrapped_metrics = {
        "status": "success",
        "result": [
            {
                "metric": {"type": "cpu", "labels": {}},
                "resource": {"labels": {}},
                "points": [{"value": 0.8, "timestamp": "2023-01-01T00:00:00Z"}],
            }
        ],
    }

    transformed = transform_metrics(wrapped_metrics)
    assert transformed["metric_name"] == "cpu"
    assert len(transformed["points"]) == 1


def test_transform_metrics_error():
    # Test error metrics response
    error_response = {"status": "error", "error": "Query timeout"}

    transformed = transform_metrics(error_response)
    assert transformed["metric_name"] == "Error"
    assert transformed["error"] == "Query timeout"


def test_transform_log_entries_wrapped():
    # Test wrapped logs response
    wrapped_logs = {
        "status": "success",
        "result": {
            "entries": [
                {
                    "insertId": "log-1",
                    "timestamp": "2023-01-01T00:00:00Z",
                    "textPayload": "Test log",
                    "resource": {"type": "gce_instance", "labels": {}},
                }
            ]
        },
    }

    transformed = transform_log_entries(wrapped_logs)
    assert len(transformed["entries"]) == 1
    assert transformed["entries"][0]["payload"] == "Test log"


def test_transform_log_entries_error():
    # Test error logs response
    error_response = {
        "status": "error",
        "error": "Filter invalid",
        "filter": "severity=INVALID",
    }

    transformed = transform_log_entries(error_response)
    assert len(transformed["entries"]) == 0
    assert transformed["error"] == "Filter invalid"
    assert transformed["filter"] == "severity=INVALID"


def test_transform_trace_robustness():
    # Test with malformed spans in the list
    trace_data = {
        "trace_id": "robust-trace",
        "spans": [
            {"span_id": "valid-1", "labels": {}},
            "malformed-span-string",
            None,
            {"span_id": "valid-2"},  # missing labels
        ],
    }

    transformed = transform_trace(trace_data)
    assert transformed["trace_id"] == "robust-trace"
    # Should only include the 2 valid dict spans
    assert len(transformed["spans"]) == 2
    assert transformed["spans"][0]["span_id"] == "valid-1"
    assert transformed["spans"][1]["span_id"] == "valid-2"
    assert "attributes" in transformed["spans"][1]


def test_transform_log_patterns_robustness():
    # Test with invalid inputs
    assert transform_log_patterns(None) == {"patterns": [], "count": 0}
    assert transform_log_patterns("string") == {"patterns": [], "count": 0}
    assert transform_log_patterns(123) == {"patterns": [], "count": 0}

    # Test with malformed list items
    malformed_list = [{"pattern_id": "p1"}, "not-a-dict", None]
    result = transform_log_patterns(malformed_list)
    assert result["count"] == 1
    assert result["patterns"][0]["pattern_id"] == "p1"

    # Test with wrapped result
    wrapped = {"status": "success", "result": {"patterns": [{"pattern_id": "w1"}]}}
    result_wrapped = transform_log_patterns(wrapped)
    assert result_wrapped["patterns"][0]["pattern_id"] == "w1"
