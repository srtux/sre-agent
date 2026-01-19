"""Tests for telemetry utilities."""

import logging
from unittest.mock import MagicMock, patch

from sre_agent.tools.common.telemetry import (
    GenAiAttributes,
    _FunctionCallWarningFilter,
    log_tool_call,
    set_span_attribute,
)


def test_function_call_warning_filter():
    """Test the function call warning filter."""
    filter_obj = _FunctionCallWarningFilter()

    # Should allow normal messages
    record = MagicMock()
    record.getMessage.return_value = "Normal message"
    assert filter_obj.filter(record) is True

    # Should filter out specific warning
    record.getMessage.return_value = "Warning: there are non-text parts in the response"
    assert filter_obj.filter(record) is False


def test_gen_ai_attributes_constants():
    """Test that GenAI attributes constants are defined."""
    assert GenAiAttributes.SYSTEM == "gen_ai.system"
    assert GenAiAttributes.REQUEST_MODEL == "gen_ai.request.model"
    assert GenAiAttributes.RESPONSE_ID == "gen_ai.response.id"
    assert GenAiAttributes.USAGE_TOTAL_TOKENS == "gen_ai.usage.total_tokens"


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


def test_set_span_attribute_with_active_span():
    """Test set_span_attribute with an active span."""
    mock_span = MagicMock()
    mock_span.is_recording.return_value = True

    with patch(
        "sre_agent.tools.common.telemetry.trace.get_current_span",
        return_value=mock_span,
    ):
        set_span_attribute("test.key", "test.value")

        mock_span.set_attribute.assert_called_once_with("test.key", "test.value")


def test_set_span_attribute_no_active_span():
    """Test set_span_attribute with no active span."""
    mock_span = MagicMock()
    mock_span.is_recording.return_value = False

    with patch(
        "sre_agent.tools.common.telemetry.trace.get_current_span",
        return_value=mock_span,
    ):
        set_span_attribute("test.key", "test.value")

        mock_span.set_attribute.assert_not_called()
