
import pytest
from unittest import mock
from trace_analyzer.telemetry import get_tracer, get_meter

def test_get_tracer():
    with mock.patch("trace_analyzer.telemetry.trace.get_tracer") as mock_get_tracer:
        mock_tracer = mock.Mock()
        mock_get_tracer.return_value = mock_tracer

        tracer = get_tracer("test_module")

        mock_get_tracer.assert_called_with("test_module")
        assert tracer == mock_tracer

def test_get_meter():
    with mock.patch("trace_analyzer.telemetry.metrics.get_meter") as mock_get_meter:
        mock_meter = mock.Mock()
        mock_get_meter.return_value = mock_meter

        meter = get_meter("test_module")

        mock_get_meter.assert_called_with("test_module")
        assert meter == mock_meter

def test_logging_filter():
    import logging
    from trace_analyzer.telemetry import _FunctionCallWarningFilter

    log_filter = _FunctionCallWarningFilter()

    # Record that should be filtered out
    record_filtered = logging.LogRecord(
        name="test", level=logging.WARNING, pathname="path", lineno=1,
        msg="Warning: there are non-text parts in the response", args=(), exc_info=None
    )
    assert log_filter.filter(record_filtered) == False

    # Record that should NOT be filtered out
    record_allowed = logging.LogRecord(
        name="test", level=logging.WARNING, pathname="path", lineno=1,
        msg="Some other warning", args=(), exc_info=None
    )
    assert log_filter.filter(record_allowed) == True
