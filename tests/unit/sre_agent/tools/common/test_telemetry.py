"""Tests for simplified telemetry."""

import logging
from unittest.mock import MagicMock, patch

from sre_agent.tools.common.telemetry import (
    log_tool_call,
    setup_telemetry,
)


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


def test_setup_telemetry_basic():
    """Test that setup_telemetry configures the root logger."""
    from sre_agent.tools.common import telemetry

    telemetry._TELEMETRY_INITIALIZED = False  # Reset state for test

    with patch("logging.getLogger") as mock_get_logger:
        mock_root = MagicMock()
        mock_root.handlers = []  # Ensure we test the path that adds a handler
        mock_get_logger.return_value = mock_root

        # We need to handle the case where getLogger is called with __name__ or empty
        def get_logger_side_effect(name=None):
            return mock_root

        mock_get_logger.side_effect = get_logger_side_effect

        setup_telemetry()

        # Verify setLevel and addHandler were called on root logger
        mock_root.setLevel.assert_called()
        mock_root.addHandler.assert_called()


def test_langfuse_context_setters():
    """Test Langfuse context variable setters."""
    from sre_agent.tools.common.telemetry import (
        add_langfuse_tags,
        get_langfuse_metadata,
        get_langfuse_session,
        get_langfuse_tags,
        get_langfuse_user,
        set_langfuse_metadata,
        set_langfuse_session,
        set_langfuse_user,
    )

    set_langfuse_session("test-session")
    assert get_langfuse_session() == "test-session"

    set_langfuse_user("test-user")
    assert get_langfuse_user() == "test-user"

    set_langfuse_metadata({"key": "value"})
    assert get_langfuse_metadata() == {"key": "value"}

    add_langfuse_tags(["tag1", "tag2"])
    assert "tag1" in get_langfuse_tags()
    assert "tag2" in get_langfuse_tags()


def test_json_formatter():
    """Test the JsonFormatter for GCP log correlation."""
    from sre_agent.tools.common.telemetry import JsonFormatter

    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test_file.py",
        lineno=10,
        msg="test message",
        args=(),
        exc_info=None,
    )

    with patch("os.environ.get") as mock_env_get:
        mock_env_get.side_effect = lambda k, default=None: (
            "test-project" if k == "GOOGLE_CLOUD_PROJECT" else default
        )
        with patch("sre_agent.auth.get_trace_id") as mock_get_trace_id:
            mock_get_trace_id.return_value = "1234567890abcdef1234567890abcdef"

            import json

            output = formatter.format(record)
            log_data = json.loads(output)

            assert log_data["severity"] == "INFO"
            assert log_data["message"] == "test message"
            assert (
                log_data["logging.googleapis.com/trace"]
                == "projects/test-project/traces/1234567890abcdef1234567890abcdef"
            )
            assert (
                log_data["logging.googleapis.com/sourceLocation"]["file"]
                == "test_file.py"
            )
