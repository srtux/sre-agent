"""BigQuery Client wrapper using Model Context Protocol (MCP).

This client acts as a bridge to the BigQuery MCP server. Instead of using the
Google Cloud BigQuery client library directly in this process, it delegates
SQL execution and schema inspection to the MCP server.

This architecture allows:
- **Separation of Concerns**: The MCP server handles connection pooling and auth.
- **Sandboxing**: The agent integration is lightweight and stateless.
- **Consistency**: All BigQuery operations go through the same controlled interface.
"""

import logging
from typing import Any, cast

from google.adk.tools import ToolContext  # type: ignore[attr-defined]

from ..mcp.gcp import (
    call_mcp_tool_with_retry,
    create_bigquery_mcp_toolset,
    get_project_id_with_fallback,
)

logger = logging.getLogger(__name__)


class BigQueryClient:
    """Wrapper around BigQuery MCP toolset for SQL execution."""

    def __init__(
        self, project_id: str | None = None, tool_context: ToolContext | None = None
    ):
        """Initialize BigQuery Client.

        Args:
            project_id: GCP Project ID.
            tool_context: ADK ToolContext (required for MCP calls).
        """
        self.project_id = project_id or get_project_id_with_fallback()
        self.tool_context = tool_context
        if not self.tool_context:
            raise ValueError("ToolContext is required for BigQueryClient")

    async def execute_query(self, query: str) -> list[dict[str, Any]]:
        """Execute a SQL query using BigQuery MCP.

        Args:
            query: SQL query string.

        Returns:
            List of rows (dicts).
        """
        if not self.project_id:
            logger.error("No project ID for BigQuery execution")
            raise ValueError("No project ID")

        assert self.tool_context is not None, "ToolContext required"

        result = await call_mcp_tool_with_retry(
            create_bigquery_mcp_toolset,
            "execute_sql",
            {"query": query, "projectId": self.project_id},
            self.tool_context,
            project_id=self.project_id,
        )

        if result.get("status") != "success":
            logger.error(f"BigQuery execution failed: {result.get('error')}")
            raise RuntimeError(f"BigQuery execution failed: {result.get('error')}")

        # MCP 'execute_sql' usually returns a structure like:
        # {"schema": ..., "rows": [...]} or just the rows if simplified.
        # We need to verify the exact output format of the MCP server's execute_sql.
        # Assuming generic MCP generic response which typically puts the data in 'result'.

        # NOTE: The MCP implementation details might vary.
        # If the MCP returns a raw JSON string, we might need to parse it.
        # For now assuming it returns a python dictionary matching the result structure.

        data = result.get("result", {})

        if not isinstance(data, dict):
            return data if isinstance(data, list) else []

        structured = data.get("structuredContent", data)

        # If 'rows' key exists, return that. fallback to the result itself if it is a list.
        rows_data = (
            structured.get("rows", []) if isinstance(structured, dict) else structured
        )
        schema_data = (
            structured.get("schema", {}).get("fields", [])
            if isinstance(structured, dict)
            else []
        )

        if not schema_data or not isinstance(rows_data, list):
            return rows_data if isinstance(rows_data, list) else []

        # Parse BigQuery raw rows format: {"f": [{"v": "val1"}, {"v": "val2"}]} -> {"col1": "val1", "col2": "val2"}
        parsed_rows = []
        field_names = [field.get("name") for field in schema_data]

        for row in rows_data:
            if isinstance(row, dict) and "f" in row:
                values = row.get("f", [])
                parsed_row = {}
                for col, val_dict in zip(field_names, values, strict=False):
                    parsed_row[col] = (
                        val_dict.get("v") if isinstance(val_dict, dict) else val_dict
                    )
                parsed_rows.append(parsed_row)
            else:
                parsed_rows.append(row)

        return parsed_rows

    async def get_table_schema(
        self, dataset_id: str, table_id: str
    ) -> list[dict[str, Any]]:
        """Get table schema.

        Args:
            dataset_id: Dataset ID.
            table_id: Table ID.

        Returns:
            List of schema fields.
        """
        if not self.project_id:
            raise ValueError("No project ID")

        assert self.tool_context is not None, "ToolContext required"

        result = await call_mcp_tool_with_retry(
            create_bigquery_mcp_toolset,
            "get_table_info",
            {
                "datasetId": dataset_id,
                "tableId": table_id,
                "projectId": self.project_id,
            },
            self.tool_context,
            project_id=self.project_id,
        )

        if result.get("status") != "success":
            logger.warning(f"Failed to get table info: {result.get('error')}")
            return []

        # result['result'] should contain 'schema' OR 'structuredContent' -> 'schema'
        data = result.get("result", {})
        if not isinstance(data, dict):
            return []

        structured = data.get("structuredContent", data)
        info = structured.get("tableInfo", structured)  # in case it's nested
        schema = info.get("schema", structured.get("schema", {}))
        return cast(list[dict[str, Any]], schema.get("fields", []))

    async def list_datasets(self) -> list[str]:
        """List BigQuery dataset IDs.

        Returns:
            List of dataset IDs.
        """
        if not self.project_id:
            raise ValueError("No project ID")

        assert self.tool_context is not None, "ToolContext required"

        result = await call_mcp_tool_with_retry(
            create_bigquery_mcp_toolset,
            "list_dataset_ids",
            {
                "projectId": self.project_id,
            },
            self.tool_context,
            project_id=self.project_id,
        )

        if result.get("status") != "success":
            logger.warning(f"Failed to list datasets: {result.get('error')}")
            return []

        data = result.get("result", {})
        if not isinstance(data, dict):
            return data if isinstance(data, list) else []

        structured = data.get("structuredContent", data)
        datasets = structured.get("datasets", [])

        res = []
        for d in datasets:
            if isinstance(d, dict):
                # MCP typically returns "projectId:datasetId"
                id_str = d.get("id", "")
                if ":" in id_str:
                    id_str = id_str.split(":", 1)[-1]
                res.append(id_str)
            else:
                res.append(str(d))

        return res

    async def list_tables(self, dataset_id: str) -> list[str]:
        """List BigQuery table IDs for a dataset.

        Args:
            dataset_id: Dataset ID.

        Returns:
            List of table IDs.
        """
        if not self.project_id:
            raise ValueError("No project ID")

        assert self.tool_context is not None, "ToolContext required"

        result = await call_mcp_tool_with_retry(
            create_bigquery_mcp_toolset,
            "list_table_ids",
            {
                "datasetId": dataset_id,
                "projectId": self.project_id,
            },
            self.tool_context,
            project_id=self.project_id,
        )

        if result.get("status") != "success":
            logger.warning(f"Failed to list tables: {result.get('error')}")
            return []

        data = result.get("result", {})
        if not isinstance(data, dict):
            return data if isinstance(data, list) else []

        structured = data.get("structuredContent", data)
        tables = structured.get("tables", [])

        res = []
        for t in tables:
            if isinstance(t, dict):
                # MCP typically returns "projectId:datasetId.tableId"
                id_str = t.get("id", "")
                if ":" in id_str:
                    id_str = id_str.split(":", 1)[-1]
                if "." in id_str:
                    id_str = id_str.split(".", 1)[-1]
                res.append(id_str)
            else:
                res.append(str(t))

        return res
