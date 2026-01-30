"""Tests for telemetry setup and structured logging."""

import json
import logging
import os
from unittest.mock import MagicMock, patch

import pytest

from sre_agent.tools.common.telemetry import (
    _StructuredJsonFormatter,
    configure_logging,
    log_tool_call,
    setup_telemetry,
)

# ---------------------------------------------------------------------------
# log_tool_call
# ---------------------------------------------------------------------------


def test_log_tool_call_basic():
    """Test log_tool_call with basic arguments."""
    logger = MagicMock(spec=logging.Logger)
    log_tool_call(logger, "test_func", arg1="value1", arg2=123)
    logger.debug.assert_called_once_with(
        "Tool Call: test_func | Args: {'arg1': 'value1', 'arg2': '123'}"
    )


def test_log_tool_call_truncation():
    """Test log_tool_call truncates long values."""
    logger = MagicMock(spec=logging.Logger)
    long_value = "x" * 250
    log_tool_call(logger, "test_func", long_arg=long_value)
    expected_truncated = long_value[:200] + "... (truncated)"
    logger.debug.assert_called_once_with(
        f"Tool Call: test_func | Args: {{'long_arg': '{expected_truncated}'}}"
    )


def test_log_tool_call_no_args():
    """Test log_tool_call with no keyword arguments."""
    logger = MagicMock(spec=logging.Logger)
    log_tool_call(logger, "no_args_func")
    logger.debug.assert_called_once_with("Tool Call: no_args_func | Args: {}")


# ---------------------------------------------------------------------------
# _StructuredJsonFormatter
# ---------------------------------------------------------------------------


class TestStructuredJsonFormatter:
    """Tests for the Cloud Logging JSON formatter."""

    def test_format_basic_record(self):
        """Formatter produces valid JSON with required Cloud Logging fields."""
        formatter = _StructuredJsonFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test_file.py",
            lineno=42,
            msg="hello world",
            args=None,
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)

        assert parsed["severity"] == "INFO"
        assert parsed["message"] == "hello world"
        assert parsed["logger"] == "test.logger"
        assert "logging.googleapis.com/sourceLocation" in parsed
        src = parsed["logging.googleapis.com/sourceLocation"]
        assert src["file"] == "test_file.py"
        assert src["line"] == 42

    def test_format_with_args(self):
        """Formatter applies %-style args to the message."""
        formatter = _StructuredJsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="f.py",
            lineno=1,
            msg="count=%d",
            args=(5,),
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "count=5"
        assert parsed["severity"] == "WARNING"

    def test_format_with_exception(self):
        """Formatter includes exception info when present."""
        formatter = _StructuredJsonFormatter()
        try:
            raise ValueError("boom")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="f.py",
            lineno=1,
            msg="failure",
            args=None,
            exc_info=exc_info,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "exception" in parsed
        assert "ValueError: boom" in parsed["exception"]

    def test_format_without_exception(self):
        """Formatter omits exception key when no exception."""
        formatter = _StructuredJsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="f.py",
            lineno=1,
            msg="ok",
            args=None,
            exc_info=None,
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert "exception" not in parsed


# ---------------------------------------------------------------------------
# setup_telemetry
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_root_logger():
    """Remove handlers added during tests to avoid cross-contamination."""
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    yield
    root.handlers = original_handlers


class TestSetupTelemetry:
    """Tests for the setup_telemetry function."""

    def test_text_format_by_default(self):
        """When LOG_FORMAT is not set, uses plain-text formatter."""
        root = logging.getLogger()
        root.handlers.clear()

        with patch.dict(os.environ, {"LOG_FORMAT": ""}, clear=False):
            setup_telemetry()

        assert len(root.handlers) >= 1
        handler = root.handlers[0]
        assert not isinstance(handler.formatter, _StructuredJsonFormatter)

    def test_json_format_when_env_set(self):
        """When LOG_FORMAT=JSON, uses structured JSON formatter."""
        root = logging.getLogger()
        root.handlers.clear()

        with patch.dict(os.environ, {"LOG_FORMAT": "JSON"}, clear=False):
            setup_telemetry()

        assert len(root.handlers) >= 1
        handler = root.handlers[0]
        assert isinstance(handler.formatter, _StructuredJsonFormatter)

    def test_json_format_case_insensitive(self):
        """LOG_FORMAT matching is case-insensitive."""
        root = logging.getLogger()
        root.handlers.clear()

        with patch.dict(os.environ, {"LOG_FORMAT": "json"}, clear=False):
            setup_telemetry()

        handler = root.handlers[0]
        assert isinstance(handler.formatter, _StructuredJsonFormatter)

    def test_log_level_from_env(self):
        """LOG_LEVEL env overrides the default level."""
        root = logging.getLogger()
        root.handlers.clear()

        with patch.dict(
            os.environ, {"LOG_LEVEL": "DEBUG", "LOG_FORMAT": ""}, clear=False
        ):
            setup_telemetry(level=logging.WARNING)

        assert root.level == logging.DEBUG

    def test_silences_chatty_loggers(self):
        """Chatty third-party loggers are set to WARNING."""
        root = logging.getLogger()
        root.handlers.clear()

        with patch.dict(os.environ, {"LOG_FORMAT": ""}, clear=False):
            setup_telemetry()

        for name in ["google.auth", "urllib3", "grpc", "httpcore", "httpx"]:
            assert logging.getLogger(name).level == logging.WARNING

    def test_no_duplicate_handlers(self):
        """Calling setup_telemetry twice does not add duplicate handlers."""
        root = logging.getLogger()
        root.handlers.clear()

        with patch.dict(os.environ, {"LOG_FORMAT": ""}, clear=False):
            setup_telemetry()
            handler_count = len(root.handlers)
            setup_telemetry()
            assert len(root.handlers) == handler_count

    def test_configure_logging_alias(self):
        """configure_logging is an alias for setup_telemetry."""
        assert configure_logging is setup_telemetry
