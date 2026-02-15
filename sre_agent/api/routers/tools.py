"""Tool configuration, testing, and direct query endpoints.

Provides direct API access to GCP telemetry data for the dashboard explorer.
These endpoints bypass the agent orchestrator for structured queries (logs,
traces, metrics, alerts, SQL) and only route through the LLM for natural
language query translation.
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sre_agent.api.dependencies import get_tool_context
from sre_agent.schema import BaseToolResponse
from sre_agent.tools import (
    extract_log_patterns,
    fetch_trace,
    list_alerts,
    list_gcp_projects,
    list_log_entries,
    list_time_series,
    list_traces,
    query_promql,
)
from sre_agent.tools.analysis import genui_adapter
from sre_agent.tools.bigquery.client import BigQueryClient
from sre_agent.tools.config import (
    ToolCategory,
    get_tool_config_manager,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tools", tags=["tools"])


def _unwrap_tool_result(result: Any) -> Any:
    """Unwrap BaseToolResponse envelope to raw result dict/list.

    Raises HTTPException(502) if the tool reported an error.
    """
    if isinstance(result, BaseToolResponse):
        if result.error:
            raise HTTPException(status_code=502, detail=result.error)
        return result.result
    return result


class ToolConfigUpdate(BaseModel):
    """Request model for updating tool configuration."""

    enabled: bool


class ToolTestRequest(BaseModel):
    """Request model for testing a tool."""

    tool_name: str


class LogAnalyzeRequest(BaseModel):
    """Request model for log analysis endpoint."""

    filter: str | None = None
    project_id: str | None = None


class MetricsQueryRequest(BaseModel):
    """Request model for metrics query endpoint."""

    filter: str = ""
    minutes_ago: int = 60
    project_id: str | None = None


class PromQLQueryRequest(BaseModel):
    """Request model for PromQL query endpoint."""

    query: str = ""
    minutes_ago: int = 60
    project_id: str | None = None


class AlertsQueryRequest(BaseModel):
    """Request model for alerts query endpoint."""

    filter: str | None = None
    minutes_ago: int | None = None
    project_id: str | None = None


class LogsQueryRequest(BaseModel):
    """Request model for logs query endpoint."""

    filter: str | None = None
    minutes_ago: int | None = None
    limit: int = 50
    project_id: str | None = None


class TracesQueryRequest(BaseModel):
    """Request model for trace filter query endpoint."""

    filter: str = ""
    minutes_ago: int = 60
    project_id: str | None = None
    limit: int = 10


class NLQueryRequest(BaseModel):
    """Request model for natural language query endpoint."""

    query: str
    domain: str
    natural_language: bool = True
    minutes_ago: int = 60
    project_id: str | None = None


class BigQueryQueryRequest(BaseModel):
    """Request model for BigQuery SQL execution."""

    sql: str
    project_id: str | None = None


# =============================================================================
# TOOL EXECUTION ENDPOINTS
# =============================================================================


@router.get("/trace/{trace_id}")
async def get_trace(trace_id: str, project_id: str | None = None) -> Any:
    """Fetch and summarize a trace."""
    try:
        result = await fetch_trace(
            trace_id=trace_id,
            project_id=project_id,
        )
        raw = _unwrap_tool_result(result)
        return genui_adapter.transform_trace(raw)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error fetching trace %s", trace_id)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/projects/list")
async def list_projects(query: str | None = None) -> Any:
    """List accessible GCP projects using the caller's EUC.

    Returns ``{"projects": [{"project_id": "...", "display_name": "..."}, ...]}``
    """
    try:
        result = await list_gcp_projects(query=query)
        return _unwrap_tool_result(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error listing projects")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/logs/analyze")
async def analyze_logs(payload: LogAnalyzeRequest) -> Any:
    """Fetch logs and extract patterns."""
    try:
        # 1. Fetch logs from Cloud Logging
        result = await list_log_entries(
            filter_str=payload.filter,
            project_id=payload.project_id,
        )
        entries_data = _unwrap_tool_result(result)

        # entries_data is a dict with "entries" key
        if not isinstance(entries_data, dict):
            entries_data = {
                "entries": entries_data if isinstance(entries_data, list) else []
            }

        log_entries = entries_data.get("entries", [])

        # 2. Extract patterns from the fetched entries
        pattern_result = await extract_log_patterns(
            log_entries=log_entries,
        )
        return _unwrap_tool_result(pattern_result)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error analyzing logs")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/metrics/query")
async def query_metrics_endpoint(payload: MetricsQueryRequest) -> Any:
    """Query time series metrics for the explorer.

    Returns data in MetricSeries-compatible format (metric_name, points, labels).
    """
    try:
        result = await list_time_series(
            filter_str=payload.filter,
            minutes_ago=payload.minutes_ago,
            project_id=payload.project_id,
        )
        raw = _unwrap_tool_result(result)
        return genui_adapter.transform_metrics(raw)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error querying metrics")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/metrics/promql")
async def query_promql_endpoint(payload: PromQLQueryRequest) -> Any:
    """Execute a PromQL query for the explorer.

    Returns data in MetricSeries-compatible format (metric_name, points, labels).
    """
    try:
        from datetime import datetime, timedelta, timezone

        end = datetime.now(timezone.utc)
        start = end - timedelta(minutes=payload.minutes_ago)

        result = await query_promql(
            query=payload.query,
            start=start.isoformat(),
            end=end.isoformat(),
            project_id=payload.project_id,
        )
        raw = _unwrap_tool_result(result)
        return genui_adapter.transform_metrics(raw)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error executing PromQL query")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/traces/query")
async def query_traces_endpoint(payload: TracesQueryRequest) -> Any:
    """Query traces using Cloud Trace filter syntax.

    Accepts Cloud Trace query language filters such as:
    ``+span:name:my_span``, ``RootSpan:/api/v1``, ``MinDuration:500ms``.

    Returns data in Trace-compatible format (spans list).
    """
    try:
        # Compute start/end time from minutes_ago
        from datetime import datetime, timedelta, timezone

        end = datetime.now(timezone.utc)
        start = end - timedelta(minutes=payload.minutes_ago)

        result = await list_traces(
            project_id=payload.project_id,
            filter_str=payload.filter,
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            limit=payload.limit,
        )
        raw = _unwrap_tool_result(result)
        return genui_adapter.transform_trace(raw)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error querying traces")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/alerts/query")
async def query_alerts_endpoint(payload: AlertsQueryRequest) -> Any:
    """Query alerts/incidents for the explorer.

    Returns data in IncidentTimelineData-compatible format.
    """
    try:
        result = await list_alerts(
            project_id=payload.project_id,
            filter_str=payload.filter,
            minutes_ago=payload.minutes_ago,
        )
        raw = _unwrap_tool_result(result)
        return genui_adapter.transform_alerts_to_timeline(raw)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error querying alerts")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/logs/query")
async def query_logs_endpoint(payload: LogsQueryRequest) -> Any:
    """Fetch raw log entries without pattern extraction (faster for explorer).

    Returns data in LogEntriesData-compatible format.
    """
    try:
        result = await list_log_entries(
            filter_str=payload.filter,
            project_id=payload.project_id,
            limit=payload.limit,
        )
        raw = _unwrap_tool_result(result)
        return genui_adapter.transform_log_entries(raw)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error querying logs")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/bigquery/query")
async def query_bigquery_endpoint(payload: BigQueryQueryRequest) -> Any:
    """Execute a BigQuery SQL query and return tabular results.

    Returns data in BigQueryQueryResponse-compatible format (columns, rows).
    """
    try:
        ctx = await get_tool_context()
        client = BigQueryClient(project_id=payload.project_id, tool_context=ctx)
        rows = await client.execute_query(payload.sql)
        # Transform rows to columns + rows list format
        columns = list(rows[0].keys()) if rows else []
        return {"columns": columns, "rows": rows}
    except Exception as e:
        logger.exception("Error querying BigQuery")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/bigquery/datasets")
async def list_bigquery_datasets(project_id: str | None = None) -> Any:
    """List datasets in the BigQuery project."""
    try:
        ctx = await get_tool_context()
        client = BigQueryClient(project_id=project_id, tool_context=ctx)
        datasets = await client.list_datasets()
        return {"datasets": datasets}
    except Exception as e:
        logger.exception("Error listing BigQuery datasets")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/bigquery/datasets/{dataset_id}/tables")
async def list_bigquery_tables(dataset_id: str, project_id: str | None = None) -> Any:
    """List tables in a BigQuery dataset."""
    try:
        ctx = await get_tool_context()
        client = BigQueryClient(project_id=project_id, tool_context=ctx)
        tables = await client.list_tables(dataset_id)
        return {"tables": tables}
    except Exception as e:
        logger.exception(f"Error listing tables for dataset {dataset_id}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/bigquery/datasets/{dataset_id}/tables/{table_id}/schema")
async def get_bigquery_table_schema(
    dataset_id: str, table_id: str, project_id: str | None = None
) -> Any:
    """Get the schema of a BigQuery table."""
    try:
        ctx = await get_tool_context()
        client = BigQueryClient(project_id=project_id, tool_context=ctx)
        schema = await client.get_table_schema(dataset_id, table_id)
        return {"schema": schema}
    except Exception as e:
        logger.exception(f"Error getting schema for table {dataset_id}.{table_id}")
        raise HTTPException(status_code=500, detail=str(e)) from e


# =============================================================================
# NATURAL LANGUAGE QUERY ENDPOINT
# =============================================================================

# Domain → structured query translation prompts
_NL_DOMAIN_PROMPTS: dict[str, str] = {
    "traces": (
        "Translate the following natural language request into a Cloud Trace "
        "filter expression. Return ONLY valid JSON with keys: "
        '"filter" (string, Cloud Trace filter syntax), '
        '"minutes_ago" (integer, time window).\n'
        "User request: {query}"
    ),
    "logs": (
        "Translate the following natural language request into a Cloud Logging "
        "filter expression. Return ONLY valid JSON with keys: "
        '"filter" (string, Cloud Logging filter syntax), '
        '"limit" (integer, max entries to return).\n'
        "User request: {query}"
    ),
    "metrics": (
        "Translate the following natural language request into a Cloud Monitoring "
        "ListTimeSeries filter or PromQL query. Return ONLY valid JSON with keys: "
        '"language" (string, "mql" or "promql"), '
        '"filter" or "query" (string, the filter/query expression), '
        '"minutes_ago" (integer, time window).\n'
        "User request: {query}"
    ),
    "bigquery": (
        "Translate the following natural language request into a BigQuery SQL "
        "query. Return ONLY valid JSON with key: "
        '"sql" (string, the SQL query).\n'
        "User request: {query}"
    ),
}


@router.post("/nl/query")
async def query_natural_language_endpoint(payload: NLQueryRequest) -> Any:
    """Translate a natural language query into a structured query and execute it.

    Uses the LLM to translate the user's natural language request into the
    appropriate structured query language (Cloud Trace filter, Cloud Logging
    filter, MQL/PromQL, or BigQuery SQL), then executes the structured query
    directly against the GCP API.

    This is the only explorer endpoint that involves the LLM. All other
    explorer endpoints execute structured queries directly.
    """
    if payload.domain not in _NL_DOMAIN_PROMPTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported domain: {payload.domain}. "
            f"Valid domains: {list(_NL_DOMAIN_PROMPTS.keys())}",
        )

    try:
        # 1. Translate NL → structured query via LLM
        structured = await _translate_nl_query(
            payload.query, payload.domain, payload.project_id
        )

        # 2. Execute the structured query using the appropriate direct endpoint
        return await _execute_structured_query(
            domain=payload.domain,
            structured=structured,
            project_id=payload.project_id,
            minutes_ago=payload.minutes_ago,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error processing natural language query")
        raise HTTPException(status_code=500, detail=str(e)) from e


async def _translate_nl_query(
    query: str, domain: str, project_id: str | None
) -> dict[str, Any]:
    """Use LLM to translate natural language into a structured query."""
    from google import genai

    from sre_agent.model_config import get_model_name

    prompt_template = _NL_DOMAIN_PROMPTS[domain]
    prompt = prompt_template.format(query=query)
    if project_id:
        prompt += f"\nGCP Project: {project_id}"

    client = genai.Client()
    response = await client.aio.models.generate_content(
        model=get_model_name("fast"),
        contents=prompt,
    )

    text = response.text or ""
    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    try:
        return json.loads(text)  # type: ignore[no-any-return]
    except json.JSONDecodeError as e:
        logger.warning("LLM returned non-JSON for NL query: %s", text[:200])
        raise HTTPException(
            status_code=502,
            detail=f"Failed to parse LLM translation: {e}",
        ) from e


async def _execute_structured_query(
    domain: str,
    structured: dict[str, Any],
    project_id: str | None,
    minutes_ago: int,
) -> Any:
    """Execute a structured query produced by the NL translator."""
    if domain == "traces":
        filter_str = structured.get("filter", "")
        mins = structured.get("minutes_ago", minutes_ago)
        return await query_traces_endpoint(
            TracesQueryRequest(
                filter=filter_str,
                minutes_ago=mins,
                project_id=project_id,
            )
        )
    elif domain == "logs":
        filter_str = structured.get("filter", "")
        limit = structured.get("limit", 50)
        return await query_logs_endpoint(
            LogsQueryRequest(
                filter=filter_str,
                limit=limit,
                project_id=project_id,
            )
        )
    elif domain == "metrics":
        language = structured.get("language", "mql")
        mins = structured.get("minutes_ago", minutes_ago)
        if language == "promql":
            return await query_promql_endpoint(
                PromQLQueryRequest(
                    query=structured.get("query", ""),
                    minutes_ago=mins,
                    project_id=project_id,
                )
            )
        else:
            return await query_metrics_endpoint(
                MetricsQueryRequest(
                    filter=structured.get("filter", ""),
                    minutes_ago=mins,
                    project_id=project_id,
                )
            )
    elif domain == "bigquery":
        sql = structured.get("sql", "")
        if not sql:
            raise HTTPException(
                status_code=400, detail="LLM did not produce a SQL query"
            )
        return await query_bigquery_endpoint(
            BigQueryQueryRequest(sql=sql, project_id=project_id)
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown domain: {domain}")


# =============================================================================
# TOOL CONFIGURATION ENDPOINTS
# =============================================================================


@router.get("/config")
async def get_tool_configs(
    category: str | None = None,
    enabled_only: bool = False,
) -> Any:
    """Get all tool configurations.

    Args:
        category: Optional filter by category (api_client, mcp, analysis, etc.)
        enabled_only: If True, only return enabled tools

    Returns:
        List of tool configurations grouped by category.
    """
    try:
        manager = get_tool_config_manager()
        configs = manager.get_all_configs()

        # Filter by category if specified
        if category:
            try:
                cat = ToolCategory(category)
                configs = [c for c in configs if c.category == cat]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid category: {category}. "
                    f"Valid categories: {[c.value for c in ToolCategory]}",
                ) from None

        # Filter by enabled status if specified
        if enabled_only:
            configs = [c for c in configs if c.enabled]

        # Group by category for better UI organization
        grouped: dict[str, list[dict[str, Any]]] = {}
        for config in configs:
            cat_name = config.category.value
            if cat_name not in grouped:
                grouped[cat_name] = []
            grouped[cat_name].append(config.to_dict())

        # Calculate summary stats
        total = len(configs)
        enabled = len([c for c in configs if c.enabled])
        testable = len([c for c in configs if c.testable])

        return {
            "tools": grouped,
            "summary": {
                "total": total,
                "enabled": enabled,
                "disabled": total - enabled,
                "testable": testable,
            },
            "categories": [c.value for c in ToolCategory],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tool configs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/config/{tool_name}")
async def get_tool_config(tool_name: str) -> Any:
    """Get configuration for a specific tool."""
    try:
        manager = get_tool_config_manager()
        config = manager.get_config(tool_name)

        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found",
            )

        return config.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tool config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put("/config/{tool_name}")
async def update_tool_config(tool_name: str, update: ToolConfigUpdate) -> Any:
    """Update configuration for a specific tool (enable/disable)."""
    try:
        manager = get_tool_config_manager()
        config = manager.get_config(tool_name)

        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found",
            )

        success = manager.set_enabled(tool_name, update.enabled)

        if not success:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update tool '{tool_name}'",
            )

        # Return updated config
        updated_config = manager.get_config(tool_name)
        return {
            "message": f"Tool '{tool_name}' "
            f"{'enabled' if update.enabled else 'disabled'} successfully",
            "tool": updated_config.to_dict() if updated_config else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tool config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/config/bulk")
async def bulk_update_tool_configs(updates: dict[str, bool]) -> Any:
    """Bulk update tool configurations.

    Args:
        updates: Dictionary of tool_name -> enabled (bool)

    Returns:
        Summary of updates performed.
    """
    try:
        manager = get_tool_config_manager()
        results: dict[str, Any] = {
            "updated": {},
            "failed": {},
            "not_found": [],
        }

        for tool_name, enabled in updates.items():
            config = manager.get_config(tool_name)
            if not config:
                results["not_found"].append(tool_name)
                continue

            success = manager.set_enabled(tool_name, enabled)
            if success:
                results["updated"][tool_name] = enabled
            else:
                results["failed"][tool_name] = "Update failed"

        return {
            "message": f"Bulk update completed: {len(results['updated'])} updated, "
            f"{len(results['failed'])} failed, {len(results['not_found'])} not found",
            "results": results,
        }
    except Exception as e:
        logger.error(f"Error in bulk update: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


# =============================================================================
# TOOL TESTING ENDPOINTS
# =============================================================================


@router.post("/test/{tool_name}")
async def test_tool(tool_name: str) -> Any:
    """Test a specific tool's connectivity/functionality.

    This performs a lightweight connectivity test to verify the tool is working.
    """
    try:
        manager = get_tool_config_manager()
        config = manager.get_config(tool_name)

        if not config:
            raise HTTPException(
                status_code=404,
                detail=f"Tool '{tool_name}' not found",
            )

        if not config.testable:
            return {
                "tool_name": tool_name,
                "testable": False,
                "message": f"Tool '{tool_name}' is not testable",
            }

        result = await manager.test_tool(tool_name)

        return {
            "tool_name": tool_name,
            "testable": True,
            "result": {
                "status": result.status.value,
                "message": result.message,
                "latency_ms": result.latency_ms,
                "timestamp": result.timestamp,
                "details": result.details,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing tool: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/test-all")
async def test_all_tools(category: str | None = None) -> Any:
    """Test all testable tools and return results.

    Args:
        category: Optional filter to test only tools in a specific category
    """
    try:
        manager = get_tool_config_manager()
        configs = manager.get_all_configs()

        # Filter by category if specified
        if category:
            try:
                cat = ToolCategory(category)
                configs = [c for c in configs if c.category == cat]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid category: {category}",
                ) from None

        # Filter to testable tools only
        testable_configs = [c for c in configs if c.testable]

        results = []
        for config in testable_configs:
            try:
                result = await manager.test_tool(config.name)
                results.append(
                    {
                        "tool_name": config.name,
                        "category": config.category.value,
                        "status": result.status.value,
                        "message": result.message,
                        "latency_ms": result.latency_ms,
                    }
                )
            except Exception as e:
                results.append(
                    {
                        "tool_name": config.name,
                        "category": config.category.value,
                        "status": "error",
                        "message": str(e),
                        "latency_ms": None,
                    }
                )

        # Calculate summary
        passed = len([r for r in results if r["status"] == "success"])
        failed = len([r for r in results if r["status"] != "success"])

        return {
            "summary": {
                "total": len(results),
                "passed": passed,
                "failed": failed,
            },
            "results": results,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing all tools: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e
