from unittest import mock

import pytest

from sre_agent.schema import BaseToolResponse, ToolStatus
from sre_agent.tools.clients.logging import list_log_entries
from sre_agent.tools.clients.monitoring import list_time_series, query_promql


@pytest.mark.asyncio
@mock.patch("sre_agent.tools.mcp.gcp.mcp_list_log_entries")
@mock.patch("sre_agent.tools.clients.logging._list_log_entries_sync")
@mock.patch("sre_agent.tools.clients.logging.get_tool_config_manager")
async def test_list_log_entries_mcp_priority(
    mock_get_config, mock_list_sync, mock_mcp_list
):
    """Test that list_log_entries prioritizes MCP when enabled."""
    # Setup mocks
    mock_config = mock.Mock()
    mock_config.is_enabled.return_value = True
    mock_get_config.return_value = mock_config

    mcp_response = BaseToolResponse(
        status=ToolStatus.SUCCESS, result={"entries": [{"id": "mcp-1"}]}
    )
    mock_mcp_list.return_value = mcp_response

    # Call tool
    result = await list_log_entries("filter", project_id="p1")

    # Verify MCP called, sync version NOT called
    assert result.status == ToolStatus.SUCCESS
    assert result.result["entries"][0]["id"] == "mcp-1"
    mock_mcp_list.assert_called_once()
    mock_list_sync.assert_not_called()


@pytest.mark.asyncio
@mock.patch("sre_agent.tools.mcp.gcp.mcp_list_log_entries")
@mock.patch("sre_agent.tools.clients.logging._list_log_entries_sync")
@mock.patch("sre_agent.tools.clients.logging.get_tool_config_manager")
async def test_list_log_entries_fallback_on_mcp_disabled(
    mock_get_config, mock_list_sync, mock_mcp_list
):
    """Test fallback when MCP is disabled."""
    mock_config = mock.Mock()
    mock_config.is_enabled.return_value = False
    mock_get_config.return_value = mock_config

    mock_list_sync.return_value = {"entries": [{"id": "api-1"}]}

    result = await list_log_entries("filter", project_id="p1")

    assert result.status == ToolStatus.SUCCESS
    assert result.result["entries"][0]["id"] == "api-1"
    mock_mcp_list.assert_not_called()
    mock_list_sync.assert_called_once()


@pytest.mark.asyncio
@mock.patch("sre_agent.tools.mcp.gcp.mcp_list_log_entries")
@mock.patch("sre_agent.tools.clients.logging._list_log_entries_sync")
@mock.patch("sre_agent.tools.clients.logging.get_tool_config_manager")
async def test_list_log_entries_fallback_on_mcp_failure(
    mock_get_config, mock_list_sync, mock_mcp_list
):
    """Test fallback when MCP call fails."""
    mock_config = mock.Mock()
    mock_config.is_enabled.return_value = True
    mock_get_config.return_value = mock_config

    # MCP returns error
    mock_mcp_list.return_value = BaseToolResponse(
        status=ToolStatus.ERROR, error="MCP Error"
    )
    mock_list_sync.return_value = {"entries": [{"id": "api-1"}]}

    result = await list_log_entries("filter", project_id="p1")

    assert result.status == ToolStatus.SUCCESS
    assert result.result["entries"][0]["id"] == "api-1"
    mock_mcp_list.assert_called_once()
    mock_list_sync.assert_called_once()


@pytest.mark.asyncio
@mock.patch("sre_agent.tools.mcp.gcp.mcp_list_timeseries")
@mock.patch("sre_agent.tools.clients.monitoring._list_time_series_sync")
@mock.patch("sre_agent.tools.clients.monitoring.get_tool_config_manager")
async def test_list_time_series_mcp_priority(
    mock_get_config, mock_list_sync, mock_mcp_list
):
    """Test that list_time_series prioritizes MCP when enabled."""
    mock_config = mock.Mock()
    mock_config.is_enabled.return_value = True
    mock_get_config.return_value = mock_config

    mcp_response = BaseToolResponse(
        status=ToolStatus.SUCCESS, result=[{"metric": "mcp"}]
    )
    mock_mcp_list.return_value = mcp_response

    result = await list_time_series("filter", project_id="p1")

    assert result.status == ToolStatus.SUCCESS
    assert result.result[0]["metric"] == "mcp"
    mock_mcp_list.assert_called_once()
    mock_list_sync.assert_not_called()


@pytest.mark.asyncio
@mock.patch("sre_agent.tools.mcp.gcp.mcp_query_range")
@mock.patch("sre_agent.tools.clients.monitoring._query_promql_sync")
@mock.patch("sre_agent.tools.clients.monitoring.get_tool_config_manager")
async def test_query_promql_mcp_priority(
    mock_get_config, mock_query_sync, mock_mcp_query
):
    """Test that query_promql prioritizes MCP when enabled."""
    mock_config = mock.Mock()
    mock_config.is_enabled.return_value = True
    mock_get_config.return_value = mock_config

    mcp_response = BaseToolResponse(status=ToolStatus.SUCCESS, result={"data": "mcp"})
    mock_mcp_query.return_value = mcp_response

    result = await query_promql("up", project_id="p1")

    assert result.status == ToolStatus.SUCCESS
    assert result.result["data"] == "mcp"
    mock_mcp_query.assert_called_once()
    mock_query_sync.assert_not_called()
