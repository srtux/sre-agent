"""Tests for BigQuery Client."""

from unittest.mock import MagicMock, patch

import pytest

from sre_agent.tools.bigquery.client import BigQueryClient, _normalize_schema_fields


@pytest.mark.asyncio
async def test_execute_query_success(mock_tool_context):
    """Test successful query execution via direct API."""
    with patch.object(BigQueryClient, "_get_direct_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_row = MagicMock()
        mock_row.items.return_value = [("col1", "val")]
        mock_client.query_and_wait.return_value = [mock_row]

        client = BigQueryClient(
            project_id="test-project", tool_context=mock_tool_context
        )
        rows = await client.execute_query("SELECT 1")

        assert len(rows) == 1
        assert rows[0]["col1"] == "val"
        mock_client.query_and_wait.assert_called_once_with("SELECT 1")


@pytest.mark.asyncio
async def test_execute_query_failure(mock_tool_context):
    """Test failed query execution."""
    with patch.object(BigQueryClient, "_get_direct_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.query_and_wait.side_effect = Exception("Table not found")

        client = BigQueryClient(
            project_id="test-project", tool_context=mock_tool_context
        )
        with pytest.raises(
            RuntimeError, match="BigQuery execution failed: Table not found"
        ):
            await client.execute_query("SELECT 1")


@pytest.mark.asyncio
async def test_get_table_schema_success(mock_tool_context):
    """Test getting table schema returns normalized fields."""
    with patch("sre_agent.tools.bigquery.client.call_mcp_tool_with_retry") as mock_call:
        mock_call.return_value = {
            "status": "success",
            "result": {
                "tableInfo": {
                    "schema": {"fields": [{"name": "col1", "type": "STRING"}]}
                }
            },
        }

        client = BigQueryClient(
            project_id="test-project", tool_context=mock_tool_context
        )
        # Mock direct SDK failure to trigger MCP fallback
        with patch.object(client, "_get_direct_client") as mock_direct:
            mock_direct.side_effect = Exception("SDK failure")
            fields = await client.get_table_schema("ds", "tbl")

            assert len(fields) == 1
            assert fields[0]["name"] == "col1"
            assert fields[0]["type"] == "STRING"
            assert fields[0]["mode"] == "NULLABLE"
            assert fields[0]["fields"] == []


@pytest.mark.asyncio
async def test_list_tables_preserves_underscores(mock_tool_context):
    """Test that table IDs with leading underscores are preserved."""
    with patch("sre_agent.tools.bigquery.client.call_mcp_tool_with_retry") as mock_call:
        mock_call.return_value = {
            "status": "success",
            "result": {
                "tables": [
                    {"id": "project:dataset._hidden_table"},
                    {"id": "project.dataset.normal_table"},
                    {"id": "_another_hidden"},
                ]
            },
        }

        client = BigQueryClient(
            project_id="test-project", tool_context=mock_tool_context
        )
        # Mock direct SDK failure to trigger MCP fallback
        with patch.object(client, "_get_direct_client") as mock_direct:
            mock_direct.side_effect = Exception("SDK failure")
            tables = await client.list_tables("dataset")

            assert "_hidden_table" in tables
            assert "normal_table" in tables
            assert "_another_hidden" in tables
            # Verify no stripping occurred
            assert "hidden_table" not in tables


@pytest.mark.asyncio
async def test_list_tables_direct_sdk(mock_tool_context):
    """Test listing tables via direct SDK handles all_tables=True."""
    mock_sdk_client = MagicMock()
    mock_table = MagicMock()
    mock_table.table_id = "_AllSpans"
    mock_sdk_client.list_tables.return_value = [mock_table]

    client = BigQueryClient(project_id="test-project", tool_context=mock_tool_context)
    with patch.object(client, "_get_direct_client", return_value=mock_sdk_client):
        tables = await client.list_tables("traces")

        assert tables == ["_AllSpans"]
        # Verify list_tables was called correctly
        mock_sdk_client.list_tables.assert_called_once_with("traces")


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


@pytest.mark.asyncio
async def test_get_json_keys_success(mock_tool_context):
    """Test successful JSON key inference."""
    with patch.object(BigQueryClient, "_get_direct_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_row1 = MagicMock()
        mock_row1.items.return_value = [("key", "key1")]
        mock_row2 = MagicMock()
        mock_row2.items.return_value = [("key", "key2")]
        mock_client.query_and_wait.return_value = [mock_row1, mock_row2]

        client = BigQueryClient(
            project_id="test-project", tool_context=mock_tool_context
        )
        keys = await client.get_json_keys("ds", "tbl", "col")

        assert keys == ["key1", "key2"]
        # Verify SQL contains JSON_KEYS
        args = mock_client.query_and_wait.call_args[0][0]
        assert "JSON_KEYS(col)" in args
        assert "UNNEST" in args


@pytest.mark.asyncio
async def test_get_json_keys_failure(mock_tool_context):
    """Test JSON key inference failure returns empty list."""
    with patch.object(BigQueryClient, "_get_direct_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.query_and_wait.side_effect = Exception("Column not found")

        client = BigQueryClient(
            project_id="test-project", tool_context=mock_tool_context
        )
        keys = await client.get_json_keys("ds", "tbl", "bad_col")
        assert keys == []


# ---- Tests for _normalize_schema_fields ----


def test_normalize_schema_fields_basic():
    """Test basic field normalization adds defaults."""
    fields = [
        {"name": "col1", "type": "STRING"},
        {"name": "col2", "type": "INTEGER"},
    ]
    result = _normalize_schema_fields(fields)
    assert len(result) == 2
    assert result[0]["name"] == "col1"
    assert result[0]["type"] == "STRING"
    assert result[0]["mode"] == "NULLABLE"
    assert result[0]["fields"] == []


def test_normalize_schema_fields_nested_record():
    """Test recursive normalization of nested RECORD fields."""
    fields = [
        {
            "name": "resource",
            "type": "RECORD",
            "fields": [
                {"name": "type", "type": "STRING"},
            ],
        }
    ]
    result = _normalize_schema_fields(fields)
    assert len(result) == 1
    assert result[0]["name"] == "resource"
    assert len(result[0]["fields"]) == 1
    assert result[0]["fields"][0]["name"] == "type"


def test_normalize_schema_fields_empty_input():
    """Test normalization of empty fields list."""
    assert _normalize_schema_fields([]) == []


def test_normalize_schema_fields_skips_non_dict():
    """Test normalization skips non-dict entries in fields list."""
    fields = [{"name": "valid", "type": "STRING"}, "invalid"]
    result = _normalize_schema_fields(fields)
    assert len(result) == 1
    assert result[0]["name"] == "valid"
