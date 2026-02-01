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
        mock_get_logger.return_value = mock_root

        # We need to handle the case where getLogger is called with __name__ or empty
        def get_logger_side_effect(name=None):
            return mock_root

        mock_get_logger.side_effect = get_logger_side_effect

        setup_telemetry()

        # Verify setLevel and addHandler were called on root logger
        mock_root.setLevel.assert_called()
        mock_root.addHandler.assert_called()


def test_langsmith_context_setters():
    """Test LangSmith context variable setters."""
    from sre_agent.tools.common.telemetry import (
        add_langsmith_tags,
        get_langsmith_metadata,
        get_langsmith_session,
        get_langsmith_tags,
        get_langsmith_user,
        set_langsmith_metadata,
        set_langsmith_session,
        set_langsmith_user,
    )

    set_langsmith_session("test-session")
    assert get_langsmith_session() == "test-session"

    set_langsmith_user("test-user")
    assert get_langsmith_user() == "test-user"

    set_langsmith_metadata({"key": "value"})
    assert get_langsmith_metadata() == {"key": "value"}

    add_langsmith_tags(["tag1", "tag2"])
    assert "tag1" in get_langsmith_tags()
    assert "tag2" in get_langsmith_tags()
