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
