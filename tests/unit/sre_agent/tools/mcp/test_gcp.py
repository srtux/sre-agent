"""
Goal: Verify GCP MCP integration correctly handles tool execution with retry logic and project context fallbacks.
Patterns: Async Tool Execution Mocking, Context Variable Management.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sre_agent.schema import ToolStatus
from sre_agent.tools.mcp.gcp import (
    clear_mcp_tool_context,
    get_project_id_with_fallback,
    mcp_execute_sql,
    mcp_list_log_entries,
    mcp_list_timeseries,
    mcp_query_range,
    set_mcp_tool_context,
)


def test_mcp_tool_context_management():
    ctx = MagicMock()
    set_mcp_tool_context(ctx)
    from sre_agent.tools.mcp.gcp import _mcp_tool_context

    assert _mcp_tool_context.get() == ctx
    clear_mcp_tool_context()
    assert _mcp_tool_context.get() is None


@pytest.mark.asyncio
async def test_get_project_id_with_fallback_context():
    mock_context = MagicMock()
    with patch(
        "sre_agent.auth.get_project_id_from_tool_context", return_value="p-context"
    ):
        set_mcp_tool_context(mock_context)
        try:
            assert get_project_id_with_fallback() == "p-context"
        finally:
            clear_mcp_tool_context()


@pytest.mark.asyncio
async def test_get_project_id_with_fallback_creds():
    with patch(
        "sre_agent.tools.mcp.gcp.get_current_credentials",
        return_value=(None, "p-creds"),
    ):
        with patch.dict("os.environ", {}, clear=True):
            assert get_project_id_with_fallback() == "p-creds"


@pytest.mark.asyncio
async def test_mcp_list_log_entries():
    mock_context = MagicMock()
    with patch(
        "sre_agent.tools.mcp.gcp.call_mcp_tool_with_retry", new_callable=AsyncMock
    ) as mock_call:
        mock_call.return_value = {
            "status": ToolStatus.SUCCESS,
            "result": {"entries": []},
        }
        result = await mcp_list_log_entries(
            filter='severity="ERROR"', project_id="p1", tool_context=mock_context
        )
        assert result.status == ToolStatus.SUCCESS
        assert "entries" in result.result
        mock_call.assert_called_once()


@pytest.mark.asyncio
async def test_mcp_list_timeseries():
    mock_context = MagicMock()
    with patch(
        "sre_agent.tools.mcp.gcp.call_mcp_tool_with_retry", new_callable=AsyncMock
    ) as mock_call:
        mock_call.return_value = {
            "status": ToolStatus.SUCCESS,
            "result": {"timeSeries": []},
        }
        result = await mcp_list_timeseries(
            filter='metric.type="m1"', project_id="p1", tool_context=mock_context
        )
        assert result.status == ToolStatus.SUCCESS
        assert "timeSeries" in result.result


@pytest.mark.asyncio
async def test_mcp_query_range():
    mock_context = MagicMock()
    with patch(
        "sre_agent.tools.mcp.gcp.call_mcp_tool_with_retry", new_callable=AsyncMock
    ) as mock_call:
        mock_call.return_value = {
            "status": ToolStatus.SUCCESS,
            "result": {"status": "success"},
        }
        result = await mcp_query_range(
            query="up", project_id="p1", tool_context=mock_context
        )
        assert result.status == ToolStatus.SUCCESS
        assert result.result["status"] == "success"


@pytest.mark.asyncio
async def test_mcp_execute_sql():
    mock_context = MagicMock()
    with patch(
        "sre_agent.tools.mcp.gcp.call_mcp_tool_with_retry", new_callable=AsyncMock
    ) as mock_call:
        mock_call.return_value = {"status": ToolStatus.SUCCESS, "result": {"rows": []}}
        result = await mcp_execute_sql(
            sql_query="SELECT 1", project_id="p1", tool_context=mock_context
        )
        assert result.status == ToolStatus.SUCCESS
        assert "rows" in result.result
