"""Unit tests for Mock MCP implementation."""

import pytest

from sre_agent.tools.mcp.mock_mcp import MockMcpTool, MockMcpToolset


@pytest.mark.asyncio
async def test_mock_tool_run():
    """Test MockMcpTool.run_async for various tool names."""

    # Test log entries
    tool = MockMcpTool("list_log_entries")
    result = await tool.run_async({}, None)
    assert "entries" in result
    assert result["entries"][0]["textPayload"] == "Mock log message"

    # Test timeseries
    tool = MockMcpTool("list_timeseries")
    result = await tool.run_async({}, None)
    assert "timeSeries" in result

    # Test query range
    tool = MockMcpTool("query_range")
    result = await tool.run_async({}, None)
    assert result["data"]["resultType"] == "matrix"

    # Test fallback
    tool = MockMcpTool("unknown_tool")
    result = await tool.run_async({}, None)
    assert result["mock"] is True


@pytest.mark.asyncio
async def test_mock_toolset():
    """Test MockMcpToolset returns expected tools."""
    toolset = MockMcpToolset()
    tools = await toolset.get_tools()

    names = [t.name for t in tools]
    assert "list_log_entries" in names
    assert "list_timeseries" in names
    assert "query_range" in names
    assert len(tools) == 3
