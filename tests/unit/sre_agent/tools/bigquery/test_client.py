"""Tests for BigQuery Client."""

from unittest.mock import AsyncMock, patch

import pytest

from sre_agent.tools.bigquery.client import BigQueryClient, _normalize_schema_fields


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
    """Test getting table schema returns normalized fields."""
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
        assert fields[0]["type"] == "STRING"
        # Verify normalized fields include mode, description, and nested fields
        assert fields[0]["mode"] == "NULLABLE"
        assert fields[0]["description"] == ""
        assert fields[0]["fields"] == []


@pytest.mark.asyncio
async def test_get_table_schema_nested_record(mock_tool_context):
    """Test schema with nested RECORD/STRUCT fields is properly normalized."""
    with patch("sre_agent.tools.bigquery.client.call_mcp_tool_with_retry") as mock_call:
        mock_call.return_value = {
            "status": "success",
            "result": {
                "schema": {
                    "fields": [
                        {"name": "id", "type": "INTEGER", "mode": "REQUIRED"},
                        {
                            "name": "attributes",
                            "type": "RECORD",
                            "mode": "NULLABLE",
                            "description": "Span attributes",
                            "fields": [
                                {
                                    "name": "key",
                                    "type": "STRING",
                                    "mode": "REQUIRED",
                                },
                                {
                                    "name": "value",
                                    "type": "STRING",
                                    "mode": "NULLABLE",
                                },
                            ],
                        },
                        {
                            "name": "events",
                            "type": "RECORD",
                            "mode": "REPEATED",
                            "fields": [
                                {"name": "timestamp", "type": "TIMESTAMP"},
                                {"name": "name", "type": "STRING"},
                            ],
                        },
                    ]
                }
            },
        }

        client = BigQueryClient(
            project_id="test-project", tool_context=mock_tool_context
        )
        fields = await client.get_table_schema("ds", "otel_spans")

        assert len(fields) == 3

        # Simple field
        assert fields[0]["name"] == "id"
        assert fields[0]["type"] == "INTEGER"
        assert fields[0]["mode"] == "REQUIRED"
        assert fields[0]["fields"] == []

        # RECORD with nested fields and description
        assert fields[1]["name"] == "attributes"
        assert fields[1]["type"] == "RECORD"
        assert fields[1]["description"] == "Span attributes"
        assert len(fields[1]["fields"]) == 2
        assert fields[1]["fields"][0]["name"] == "key"
        assert fields[1]["fields"][0]["mode"] == "REQUIRED"
        assert fields[1]["fields"][1]["name"] == "value"
        assert fields[1]["fields"][1]["mode"] == "NULLABLE"

        # REPEATED RECORD
        assert fields[2]["name"] == "events"
        assert fields[2]["mode"] == "REPEATED"
        assert len(fields[2]["fields"]) == 2
        assert fields[2]["fields"][0]["type"] == "TIMESTAMP"
        assert fields[2]["fields"][0]["mode"] == "NULLABLE"  # default


@pytest.mark.asyncio
async def test_get_table_schema_failure(mock_tool_context):
    """Test failed schema retrieval."""
    with patch("sre_agent.tools.bigquery.client.call_mcp_tool_with_retry") as mock_call:
        mock_call.return_value = {"status": "error", "error": "Not Found"}

        client = BigQueryClient(
            project_id="test-project", tool_context=mock_tool_context
        )
        with pytest.raises(
            RuntimeError, match="MCP fallback failed to fetch schema: Not Found"
        ):
            await client.get_table_schema("ds", "tbl")


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
    assert result[0]["description"] == ""
    assert result[0]["fields"] == []

    assert result[1]["name"] == "col2"
    assert result[1]["type"] == "INTEGER"


def test_normalize_schema_fields_preserves_mode_and_description():
    """Test normalization preserves existing mode and description."""
    fields = [
        {
            "name": "id",
            "type": "INTEGER",
            "mode": "REQUIRED",
            "description": "Primary key",
        },
        {
            "name": "tags",
            "type": "STRING",
            "mode": "REPEATED",
        },
    ]
    result = _normalize_schema_fields(fields)

    assert result[0]["mode"] == "REQUIRED"
    assert result[0]["description"] == "Primary key"
    assert result[1]["mode"] == "REPEATED"
    assert result[1]["description"] == ""


def test_normalize_schema_fields_nested_record():
    """Test recursive normalization of nested RECORD fields."""
    fields = [
        {
            "name": "resource",
            "type": "RECORD",
            "fields": [
                {"name": "type", "type": "STRING"},
                {
                    "name": "labels",
                    "type": "RECORD",
                    "fields": [
                        {"name": "key", "type": "STRING"},
                        {"name": "value", "type": "STRING"},
                    ],
                },
            ],
        }
    ]
    result = _normalize_schema_fields(fields)

    assert len(result) == 1
    assert result[0]["name"] == "resource"
    assert result[0]["type"] == "RECORD"
    assert len(result[0]["fields"]) == 2

    # Nested fields should also be normalized
    nested = result[0]["fields"]
    assert nested[0]["mode"] == "NULLABLE"
    assert nested[0]["fields"] == []

    # Deeply nested RECORD
    assert nested[1]["name"] == "labels"
    assert nested[1]["type"] == "RECORD"
    assert len(nested[1]["fields"]) == 2
    assert nested[1]["fields"][0]["name"] == "key"


def test_normalize_schema_fields_empty_input():
    """Test normalization of empty fields list."""
    assert _normalize_schema_fields([]) == []


def test_normalize_schema_fields_missing_keys():
    """Test normalization handles fields with missing keys."""
    fields = [
        {},  # completely empty
        {"name": "partial"},  # missing type
    ]
    result = _normalize_schema_fields(fields)
    assert len(result) == 2
    assert result[0]["name"] == ""
    assert result[0]["type"] == "UNKNOWN"
    assert result[1]["name"] == "partial"
    assert result[1]["type"] == "UNKNOWN"


def test_normalize_schema_fields_skips_non_dict():
    """Test normalization skips non-dict entries in fields list."""
    fields = [
        {"name": "valid", "type": "STRING"},
        "not_a_dict",
        42,
        None,
    ]
    result = _normalize_schema_fields(fields)
    assert len(result) == 1
    assert result[0]["name"] == "valid"


def test_normalize_schema_fields_json_type():
    """Test normalization handles BigQuery native JSON type."""
    fields = [
        {
            "name": "payload",
            "type": "JSON",
            "mode": "NULLABLE",
            "description": "Structured event payload",
        },
        {
            "name": "metadata",
            "type": "JSON",
            "mode": "REQUIRED",
        },
    ]
    result = _normalize_schema_fields(fields)
    assert len(result) == 2

    assert result[0]["name"] == "payload"
    assert result[0]["type"] == "JSON"
    assert result[0]["mode"] == "NULLABLE"
    assert result[0]["description"] == "Structured event payload"
    assert result[0]["fields"] == []

    assert result[1]["name"] == "metadata"
    assert result[1]["type"] == "JSON"
    assert result[1]["mode"] == "REQUIRED"
