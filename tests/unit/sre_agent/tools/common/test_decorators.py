import logging
import os
from unittest.mock import patch

import pytest

from sre_agent.schema import BaseToolResponse, ToolStatus
from sre_agent.tools.common.decorators import adk_tool


@pytest.mark.asyncio
async def test_adk_tool_detects_logical_error_in_basetool_response(caplog):
    caplog.set_level(logging.ERROR)

    @adk_tool
    async def failing_tool():
        return BaseToolResponse(status=ToolStatus.ERROR, error="Something went wrong")

    with patch.dict(
        os.environ, {"OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "false"}
    ):
        result = await failing_tool()

    assert result.status == ToolStatus.ERROR
    # Verify that we logged an error, not a success
    assert "❌ Tool Failed (Logical): 'failing_tool'" in caplog.text
    assert "✅ Tool Success" not in caplog.text


@pytest.mark.asyncio
async def test_adk_tool_detects_success_in_basetool_response(caplog):
    caplog.set_level(logging.INFO)

    @adk_tool
    async def successful_tool():
        return BaseToolResponse(status=ToolStatus.SUCCESS, result={"data": "ok"})

    with patch.dict(
        os.environ, {"OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "false"}
    ):
        result = await successful_tool()

    assert result.status == ToolStatus.SUCCESS
    assert "✅ Tool Success: 'successful_tool'" in caplog.text


def test_adk_tool_sync_detects_logical_error_in_dict(caplog):
    caplog.set_level(logging.ERROR)

    @adk_tool
    def failing_sync_tool():
        return {"error": "logical failure"}

    with patch.dict(
        os.environ, {"OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "false"}
    ):
        result = failing_sync_tool()

    assert result == {"error": "logical failure"}
    assert "❌ Tool Failed (Logical): 'failing_sync_tool'" in caplog.text


@pytest.mark.asyncio
async def test_adk_tool_detects_logical_error_in_json_string(caplog):
    caplog.set_level(logging.ERROR)

    @adk_tool
    async def failing_json_tool():
        return '{"status": "error", "error": "json failure"}'

    with patch.dict(
        os.environ, {"OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "false"}
    ):
        result = await failing_json_tool()

    assert "error" in result
    assert "❌ Tool Failed (Logical): 'failing_json_tool'" in caplog.text


@pytest.mark.asyncio
async def test_adk_tool_does_not_flag_dict_with_none_error_as_failure(caplog):
    """Dict results with 'error': None should NOT be treated as failures."""
    caplog.set_level(logging.INFO)

    @adk_tool
    async def tool_with_null_error():
        return {"result": {"entries": [{"id": "1"}]}, "error": None}

    with patch.dict(
        os.environ, {"OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "false"}
    ):
        result = await tool_with_null_error()

    assert result == {"result": {"entries": [{"id": "1"}]}, "error": None}
    assert "✅ Tool Success: 'tool_with_null_error'" in caplog.text
    assert "❌ Tool Failed" not in caplog.text


@pytest.mark.asyncio
async def test_adk_tool_does_not_flag_dict_with_empty_error_as_failure(caplog):
    """Dict results with 'error': '' should NOT be treated as failures."""
    caplog.set_level(logging.INFO)

    @adk_tool
    async def tool_with_empty_error():
        return {"result": {"data": "ok"}, "error": ""}

    with patch.dict(
        os.environ, {"OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "false"}
    ):
        await tool_with_empty_error()

    assert "✅ Tool Success: 'tool_with_empty_error'" in caplog.text
    assert "❌ Tool Failed" not in caplog.text


@pytest.mark.asyncio
async def test_adk_tool_does_not_flag_json_string_with_null_error_as_failure(caplog):
    """JSON string results with 'error': null should NOT be treated as failures."""
    caplog.set_level(logging.INFO)

    @adk_tool
    async def tool_json_null_error():
        return '{"status": "success", "result": {"data": "ok"}, "error": null}'

    with patch.dict(
        os.environ, {"OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "false"}
    ):
        await tool_json_null_error()

    assert "✅ Tool Success: 'tool_json_null_error'" in caplog.text
    assert "❌ Tool Failed" not in caplog.text


def test_adk_tool_sync_does_not_flag_dict_with_none_error_as_failure(caplog):
    """Sync: dict results with 'error': None should NOT be treated as failures."""
    caplog.set_level(logging.INFO)

    @adk_tool
    def sync_tool_null_error():
        return {"result": "data", "error": None}

    with patch.dict(
        os.environ, {"OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "false"}
    ):
        result = sync_tool_null_error()

    assert result == {"result": "data", "error": None}
    assert "✅ Tool Success: 'sync_tool_null_error'" in caplog.text
    assert "❌ Tool Failed" not in caplog.text


@pytest.mark.asyncio
async def test_adk_tool_calls_queue_on_success(caplog):
    """Successful tool results should trigger queue_tool_result."""
    caplog.set_level(logging.INFO)

    @adk_tool
    async def dashboard_tool():
        return BaseToolResponse(status=ToolStatus.SUCCESS, result={"data": "ok"})

    with (
        patch.dict(
            os.environ,
            {"OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "false"},
        ),
        patch("sre_agent.tools.common.decorators._queue_tool_result") as mock_queue,
    ):
        await dashboard_tool()

    mock_queue.assert_called_once()
    call_args = mock_queue.call_args
    assert call_args[0][0] == "dashboard_tool"


@pytest.mark.asyncio
async def test_adk_tool_does_not_queue_failed_result(caplog):
    """Failed tool results should NOT trigger queue_tool_result."""
    caplog.set_level(logging.ERROR)

    @adk_tool
    async def failing_dashboard_tool():
        return BaseToolResponse(status=ToolStatus.ERROR, error="Something went wrong")

    with (
        patch.dict(
            os.environ,
            {"OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "false"},
        ),
        patch("sre_agent.tools.common.decorators._queue_tool_result") as mock_queue,
    ):
        await failing_dashboard_tool()

    mock_queue.assert_not_called()


@pytest.mark.asyncio
async def test_adk_tool_queues_dict_with_null_error(caplog):
    """Dict results with 'error': None should trigger queue_tool_result."""
    caplog.set_level(logging.INFO)

    @adk_tool
    async def tool_null_error_queued():
        return {"result": {"entries": [{"id": "1"}]}, "error": None}

    with (
        patch.dict(
            os.environ,
            {"OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "false"},
        ),
        patch("sre_agent.tools.common.decorators._queue_tool_result") as mock_queue,
    ):
        await tool_null_error_queued()

    mock_queue.assert_called_once()
    call_args = mock_queue.call_args
    assert call_args[0][0] == "tool_null_error_queued"


@pytest.mark.asyncio
async def test_adk_tool_skips_instrumentation_when_enabled(caplog):
    """Test that adk_tool skips spans/logs when native instrumentation is enabled."""
    import os
    from unittest.mock import patch

    caplog.set_level(logging.INFO)

    with patch.dict(
        os.environ, {"OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT": "true"}
    ):

        @adk_tool
        async def skip_me():
            return "skipped"

        result = await skip_me()

        assert result == "skipped"
        # Verify NO tool logs were emitted
        assert "🛠️  Tool Call" not in caplog.text
        assert "✅ Tool Success" not in caplog.text
