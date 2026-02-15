import logging
import os
from typing import Any

from google.adk.tools import ToolContext  # type: ignore[attr-defined]
from google.cloud import bigquery

from ...auth import (
    get_credentials_from_tool_context,
)
from ..mcp.gcp import (
    call_mcp_tool_with_retry,
    create_bigquery_mcp_toolset,
    get_project_id_with_fallback,
)

logger = logging.getLogger(__name__)


class BigQueryClient:
    """Wrapper around BigQuery MCP toolset for SQL execution with direct SDK fallback."""

    def __init__(
        self, project_id: str | None = None, tool_context: ToolContext | None = None
    ):
        """Initialize BigQuery Client.

        Args:
            project_id: GCP Project ID.
            tool_context: ADK ToolContext (needed for MCP calls and credential propagation).
        """
        if tool_context is None:
            raise ValueError("ToolContext is required")

        self.tool_context = tool_context
        self.project_id = project_id or get_project_id_with_fallback()

    def _get_direct_client(self) -> bigquery.Client:
        """Create a direct BigQuery client using current credentials."""
        creds = get_credentials_from_tool_context(self.tool_context)
        return bigquery.Client(project=self.project_id, credentials=creds)

    async def execute_query(self, query: str) -> list[dict[str, Any]]:
        """Execute a SQL query using BigQuery MCP with direct fallback.

        Args:
            query: SQL query string.

        Returns:
            List of rows (dicts).
        """
        if not self.project_id:
            logger.error("No project ID for BigQuery execution")
            raise ValueError("No project ID")

        # Configuration: Prefer MCP if enabled and not failing
        use_mcp = os.environ.get("USE_BIGQUERY_MCP", "true").lower() == "true"

        if use_mcp and self.tool_context:
            try:
                result = await call_mcp_tool_with_retry(
                    create_bigquery_mcp_toolset,
                    "execute_sql",
                    {"query": query, "projectId": self.project_id},
                    self.tool_context,
                    project_id=self.project_id,
                )

                if result.get("status") == "success":
                    data = result.get("result", {})
                    if not isinstance(data, dict):
                        return data if isinstance(data, list) else []

                    structured = data.get("structuredContent", data)
                    rows_data = (
                        structured.get("rows", [])
                        if isinstance(structured, dict)
                        else structured
                    )
                    schema_data = (
                        structured.get("schema", {}).get("fields", [])
                        if isinstance(structured, dict)
                        else []
                    )

                    if not schema_data or not isinstance(rows_data, list):
                        return rows_data if isinstance(rows_data, list) else []

                    # Parse BigQuery raw rows format
                    parsed_rows = []
                    field_names = [field.get("name") for field in schema_data]

                    for row in rows_data:
                        if isinstance(row, dict) and "f" in row:
                            values = row.get("f", [])
                            parsed_row = {}
                            for col, val_dict in zip(field_names, values, strict=False):
                                parsed_row[col] = (
                                    val_dict.get("v")
                                    if isinstance(val_dict, dict)
                                    else val_dict
                                )
                            parsed_rows.append(parsed_row)
                        else:
                            parsed_rows.append(row)

                    return parsed_rows
                else:
                    err = str(result.get("error", ""))
                    # If it's a connection/session error, fall back to direct API
                    if any(
                        msg in err
                        for msg in [
                            "Connection closed",
                            "Session terminated",
                            "timeout",
                        ]
                    ):
                        logger.warning(
                            f"BigQuery MCP failed with transient error: {err}. Falling back to direct SDK."
                        )
                    else:
                        logger.error(f"BigQuery MCP execution failed: {err}")
                        raise RuntimeError(f"BigQuery execution failed: {err}")
            except Exception as e:
                if "Connection closed" in str(e) or "Session terminated" in str(e):
                    logger.warning(
                        f"BigQuery MCP connection error: {e}. Falling back to direct SDK."
                    )
                else:
                    raise

        # Direct API Fallback
        logger.info(
            f"💾 Executing BigQuery query directly for project {self.project_id}"
        )
        try:
            client = self._get_direct_client()
            query_job = client.query(query)
            results = query_job.result()
            return [dict(row.items()) for row in results]
        except Exception as e:
            logger.error(f"Direct BigQuery execution failed: {e}")
            raise RuntimeError(f"BigQuery execution failed: {e}") from e

    async def get_table_schema(
        self, dataset_id: str, table_id: str
    ) -> list[dict[str, Any]]:
        """Get table schema with enriched field metadata."""
        if not self.project_id:
            raise ValueError("No project ID")

        # Prefer Direct API for schema as it is more robust
        try:
            client = self._get_direct_client()
            table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
            table = client.get_table(table_ref)

            # Map BigQuery SchemaField to dict
            fields = []
            for field in table.schema or []:
                fields.append(_map_schema_field(field))
            return fields
        except Exception as e:
            logger.warning(f"Direct schema fetch failed: {e}. Trying MCP fallback.")

        # MCP Fallback
        if not self.tool_context:
            raise RuntimeError(
                "Failed to fetch schema (direct SDK failed and NO tool context for MCP fallback)"
            )

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
            logger.warning(f"Failed to get table info via MCP: {result.get('error')}")
            raise RuntimeError(
                f"MCP fallback failed to fetch schema: {result.get('error')}"
            )

        data = result.get("result", {})
        structured = data.get("structuredContent", data)
        info = structured.get("tableInfo", structured)
        schema = info.get("schema", structured.get("schema", {}))
        raw_fields = schema.get("fields", [])

        return _normalize_schema_fields(raw_fields)

    async def list_datasets(self) -> list[str]:
        """List BigQuery dataset IDs."""
        if not self.project_id:
            raise ValueError("No project ID")

        try:
            client = self._get_direct_client()
            datasets = list(client.list_datasets())
            return [d.dataset_id for d in datasets]
        except Exception as e:
            logger.warning(f"Direct dataset list failed: {e}. Trying MCP fallback.")

        if not self.tool_context:
            return []

        result = await call_mcp_tool_with_retry(
            create_bigquery_mcp_toolset,
            "list_dataset_ids",
            {"projectId": self.project_id},
            self.tool_context,
            project_id=self.project_id,
        )

        if result.get("status") != "success":
            return []

        data = result.get("result", {})
        structured = data.get("structuredContent", data)
        datasets_list = structured.get("datasets", [])

        res = []
        for d in datasets_list:
            if isinstance(d, dict):
                id_str = d.get("id", "")
                if ":" in id_str:
                    id_str = id_str.split(":", 1)[-1]
                res.append(id_str)
            else:
                res.append(str(d))
        return res

    async def list_tables(self, dataset_id: str) -> list[str]:
        """List BigQuery table IDs for a dataset."""
        if not self.project_id:
            raise ValueError("No project ID")

        try:
            client = self._get_direct_client()
            # Explicitly include hidden tables (starting with underscore)
            tables = list(client.list_tables(dataset_id, all_tables=True))
            return [t.table_id for t in tables]
        except Exception as e:
            logger.warning(f"Direct table list failed: {e}. Trying MCP fallback.")

        if not self.tool_context:
            return []

        result = await call_mcp_tool_with_retry(
            create_bigquery_mcp_toolset,
            "list_table_ids",
            {"datasetId": dataset_id, "projectId": self.project_id},
            self.tool_context,
            project_id=self.project_id,
        )

        if result.get("status") != "success":
            return []

        data = result.get("result", {})
        structured = data.get("structuredContent", data)
        tables_list = structured.get("tables", [])

        res = []
        for t in tables_list:
            if isinstance(t, dict):
                id_str = t.get("id", "")
                # Robustly extract the table ID (the part after the last dot or colon)
                import re

                parts = re.split(r"[:.]", id_str)
                id_str = parts[-1] if parts else id_str
                res.append(id_str)
            else:
                res.append(str(t))
        return res


def _map_schema_field(field: Any) -> dict[str, Any]:
    """Map BigQuery SchemaField to serializable dict."""
    res = {
        "name": field.name,
        "type": field.field_type,
        "mode": field.mode,
        "description": field.description or "",
    }
    if hasattr(field, "fields") and field.fields:
        res["fields"] = [_map_schema_field(f) for f in field.fields]
    else:
        res["fields"] = []
    return res


def _normalize_schema_fields(fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize BigQuery schema fields to a consistent structure."""
    normalized: list[dict[str, Any]] = []
    for field in fields:
        if not isinstance(field, dict):
            continue
        entry: dict[str, Any] = {
            "name": field.get("name", ""),
            "type": field.get("type", "UNKNOWN"),
            "mode": field.get("mode", "NULLABLE"),
            "description": field.get("description", ""),
        }
        nested = field.get("fields", [])
        if nested and isinstance(nested, list):
            entry["fields"] = _normalize_schema_fields(nested)
        else:
            entry["fields"] = []
        normalized.append(entry)
    return normalized
