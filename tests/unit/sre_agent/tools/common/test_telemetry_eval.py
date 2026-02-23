"""Tests for the log_evaluation_result function in telemetry.

Tests the OTel evaluation result logging (sre_agent/tools/common/telemetry.py)
including:
- Successful logging with correct span/event structure
- Multiple metrics producing multiple events
- Empty eval_results
- ImportError fallback (OTel not installed)
- General exception handling
"""

from unittest.mock import MagicMock, patch

from sre_agent.tools.common.telemetry import log_evaluation_result

# ========== Successful logging ==========


def test_log_evaluation_result_success():
    """Successful logging returns True and creates span with correct name and events."""
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=False)

    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value = mock_span

    with patch("opentelemetry.trace.get_tracer", return_value=mock_tracer):
        with patch("opentelemetry.trace.set_span_in_context", return_value=MagicMock()):
            result = log_evaluation_result(
                original_trace_id="a" * 32,
                original_span_id="b" * 16,
                eval_results={
                    "coherence": {"score": 0.9, "explanation": "Well structured"},
                },
            )

    assert result is True
    # Verify tracer was obtained with correct instrumentation name
    mock_tracer.start_as_current_span.assert_called_once()
    call_args = mock_tracer.start_as_current_span.call_args
    assert call_args[0][0] == "gen_ai.evaluation"
    # Verify add_event was called for the metric
    mock_span.add_event.assert_called_once()
    event_args = mock_span.add_event.call_args
    assert event_args[0][0] == "gen_ai.evaluation.result"
    attrs = event_args[1]["attributes"]
    assert attrs["gen_ai.evaluation.metric.name"] == "coherence"
    assert attrs["gen_ai.evaluation.score"] == 0.9
    assert attrs["gen_ai.evaluation.explanation"] == "Well structured"


def test_log_evaluation_result_multiple_metrics():
    """Multiple metrics produce multiple events on the span."""
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=False)

    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value = mock_span

    with patch("opentelemetry.trace.get_tracer", return_value=mock_tracer):
        with patch("opentelemetry.trace.set_span_in_context", return_value=MagicMock()):
            result = log_evaluation_result(
                original_trace_id="a" * 32,
                original_span_id="b" * 16,
                eval_results={
                    "coherence": {"score": 0.9, "explanation": "Good"},
                    "fluency": {"score": 0.8, "explanation": "OK"},
                    "safety": {"score": 1.0, "explanation": "Safe"},
                },
            )

    assert result is True
    assert mock_span.add_event.call_count == 3
    # Verify each metric name is present in events
    metric_names = [
        call[1]["attributes"]["gen_ai.evaluation.metric.name"]
        for call in mock_span.add_event.call_args_list
    ]
    assert set(metric_names) == {"coherence", "fluency", "safety"}


def test_log_evaluation_result_empty_results():
    """Empty eval_results creates span but no events, returns True."""
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=False)

    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value = mock_span

    with patch("opentelemetry.trace.get_tracer", return_value=mock_tracer):
        with patch("opentelemetry.trace.set_span_in_context", return_value=MagicMock()):
            result = log_evaluation_result(
                original_trace_id="a" * 32,
                original_span_id="b" * 16,
                eval_results={},
            )

    assert result is True
    mock_tracer.start_as_current_span.assert_called_once()
    mock_span.add_event.assert_not_called()


def test_log_evaluation_result_missing_explanation():
    """Metric without explanation key defaults to empty string."""
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=False)

    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value = mock_span

    with patch("opentelemetry.trace.get_tracer", return_value=mock_tracer):
        with patch("opentelemetry.trace.set_span_in_context", return_value=MagicMock()):
            result = log_evaluation_result(
                original_trace_id="a" * 32,
                original_span_id="b" * 16,
                eval_results={
                    "coherence": {"score": 0.7},  # No "explanation" key
                },
            )

    assert result is True
    attrs = mock_span.add_event.call_args[1]["attributes"]
    assert attrs["gen_ai.evaluation.explanation"] == ""


def test_log_evaluation_result_span_context_created_correctly():
    """Verifies SpanContext is created with correct trace/span IDs."""
    mock_span = MagicMock()
    mock_span.__enter__ = MagicMock(return_value=mock_span)
    mock_span.__exit__ = MagicMock(return_value=False)

    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value = mock_span

    trace_id = "a" * 32
    span_id = "b" * 16

    with patch("opentelemetry.trace.get_tracer", return_value=mock_tracer):
        with patch("opentelemetry.trace.SpanContext") as mock_span_context_cls:
            with patch("opentelemetry.trace.NonRecordingSpan"):
                with patch(
                    "opentelemetry.trace.set_span_in_context",
                    return_value=MagicMock(),
                ):
                    result = log_evaluation_result(
                        original_trace_id=trace_id,
                        original_span_id=span_id,
                        eval_results={},
                    )

    assert result is True
    # Verify SpanContext was called with parsed hex IDs
    mock_span_context_cls.assert_called_once()
    call_kwargs = mock_span_context_cls.call_args
    assert call_kwargs[1]["trace_id"] == int(trace_id, 16)
    assert call_kwargs[1]["span_id"] == int(span_id, 16)
    assert call_kwargs[1]["is_remote"] is True


# ========== Error handling ==========


def test_log_evaluation_result_import_error():
    """ImportError (OTel not installed) returns False."""
    # Simulate ImportError by making the opentelemetry import fail
    # inside the function's try block
    original_import = __import__

    def _import_raiser(name, *args, **kwargs):
        if name == "opentelemetry":
            raise ImportError("No module named 'opentelemetry'")
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=_import_raiser):
        result = log_evaluation_result(
            original_trace_id="a" * 32,
            original_span_id="b" * 16,
            eval_results={"coherence": {"score": 0.5}},
        )

    assert result is False


def test_log_evaluation_result_general_exception():
    """General exception returns False and logs warning."""
    # Make SpanContext constructor raise a ValueError to trigger the
    # general except clause
    with patch(
        "opentelemetry.trace.SpanContext",
        side_effect=ValueError("bad trace id"),
    ):
        result = log_evaluation_result(
            original_trace_id="a" * 32,
            original_span_id="b" * 16,
            eval_results={"coherence": {"score": 0.5}},
        )

    assert result is False


def test_log_evaluation_result_invalid_trace_id():
    """Invalid (non-hex) trace ID triggers exception and returns False."""
    result = log_evaluation_result(
        original_trace_id="not_a_hex_string",
        original_span_id="b" * 16,
        eval_results={"coherence": {"score": 0.5}},
    )
    assert result is False
