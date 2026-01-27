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
    """Test that setup_telemetry only configures basic logging."""
    with patch("logging.basicConfig") as mock_basic_config:
        setup_telemetry()
        mock_basic_config.assert_called_once()
