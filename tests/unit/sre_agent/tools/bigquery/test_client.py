"""Tests for BigQuery Client."""

from unittest.mock import AsyncMock, patch

import pytest

from sre_agent.tools.bigquery.client import BigQueryClient


@pytest.mark.asyncio
async def test_execute_query_success(mock_tool_context):
    """Test successful query execution."""
    mock_toolset = AsyncMock()
    mock_execute = AsyncMock()
    mock_execute.name = "execute_sql"
    # The tool itself returns the data structure
    mock_execute.run_async.return_value = {"rows": [{"col": "val"}]}
    mock_toolset.get_tools.return_value = [mock_execute]

    client = BigQueryClient(project_id="test-project", tool_context=mock_tool_context)

    with patch(
        "sre_agent.tools.bigquery.client.create_bigquery_mcp_toolset",
        return_value=mock_toolset,
    ):
        rows = await client.execute_query("SELECT 1")
        assert len(rows) == 1
        assert rows[0]["col"] == "val"


@pytest.mark.asyncio
async def test_execute_query_list_result(mock_tool_context):
    """Test successful query execution where result is a direct list."""
    mock_toolset = AsyncMock()
    mock_execute = AsyncMock()
    mock_execute.name = "execute_sql"
    mock_execute.run_async.return_value = [{"col": "val"}]
    mock_toolset.get_tools.return_value = [mock_execute]

    client = BigQueryClient(project_id="test-project", tool_context=mock_tool_context)

    with patch(
        "sre_agent.tools.bigquery.client.create_bigquery_mcp_toolset",
        return_value=mock_toolset,
    ):
        rows = await client.execute_query("SELECT 1")
        assert len(rows) == 1
        assert rows[0]["col"] == "val"


@pytest.mark.asyncio
async def test_execute_query_bad_data_format(mock_tool_context):
    """Test query where data is neither dict nor list."""
    with patch("sre_agent.tools.bigquery.client.call_mcp_tool_with_retry") as mock_call:
        # result['result'] is an int
        mock_call.return_value = {"status": "success", "result": 123}

        client = BigQueryClient(
            project_id="test-project", tool_context=mock_tool_context
        )
        rows = await client.execute_query("SELECT 1")
        assert rows == []


@pytest.mark.asyncio
async def test_execute_query_failure(mock_tool_context):
    """Test failed query execution."""
    with patch("sre_agent.tools.bigquery.client.call_mcp_tool_with_retry") as mock_call:
        mock_call.return_value = {"status": "error", "error": "Table not found"}

        client = BigQueryClient(
            project_id="test-project", tool_context=mock_tool_context
        )
        with pytest.raises(
            RuntimeError, match="BigQuery execution failed: Table not found"
        ):
            await client.execute_query("SELECT 1")


@pytest.mark.asyncio
async def test_get_table_schema_success(mock_tool_context):
    """Test getting table schema."""
    mock_toolset = AsyncMock()
    mock_get_info = AsyncMock()
    mock_get_info.name = "get_table_info"
    mock_get_info.run_async.return_value = {
        "schema": {"fields": [{"name": "col1", "type": "STRING"}]},
    }
    mock_toolset.get_tools.return_value = [mock_get_info]

    client = BigQueryClient(project_id="test-project", tool_context=mock_tool_context)

    with patch(
        "sre_agent.tools.bigquery.client.create_bigquery_mcp_toolset",
        return_value=mock_toolset,
    ):
        fields = await client.get_table_schema("ds", "tbl")
        assert len(fields) == 1
        assert fields[0]["name"] == "col1"


@pytest.mark.asyncio
async def test_get_table_schema_failure(mock_tool_context):
    """Test failed schema retrieval."""
    with patch("sre_agent.tools.bigquery.client.call_mcp_tool_with_retry") as mock_call:
        mock_call.return_value = {"status": "error", "error": "Not Found"}

        client = BigQueryClient(
            project_id="test-project", tool_context=mock_tool_context
        )
        fields = await client.get_table_schema("ds", "tbl")
        assert fields == []


def test_client_init_no_context():
    """Test initialization without tool context."""
    with pytest.raises(ValueError, match="ToolContext is required"):
        BigQueryClient(project_id="test-project", tool_context=None)


@pytest.mark.asyncio
async def test_execute_query_no_project(mock_tool_context):
    """Test query without project ID."""
    with patch(
        "sre_agent.tools.bigquery.client.get_project_id_with_fallback",
        return_value=None,
    ):
        client = BigQueryClient(tool_context=mock_tool_context)
        with pytest.raises(ValueError, match="No project ID"):
            await client.execute_query("SELECT 1")


@pytest.mark.asyncio
async def test_get_table_schema_no_project(mock_tool_context):
    """Test schema fetch without project ID."""
    with patch(
        "sre_agent.tools.bigquery.client.get_project_id_with_fallback",
        return_value=None,
    ):
        client = BigQueryClient(tool_context=mock_tool_context)
        with pytest.raises(ValueError, match="No project ID"):
            await client.get_table_schema("ds", "tbl")
