"""ADK tools for agent trace analysis and debugging.

Provides four tools for listing, reconstructing, analyzing, and debugging
AI agent interactions from Vertex Agent Engine via OpenTelemetry traces.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sre_agent.schema import (
    BaseToolResponse,
    ToolStatus,
)
from sre_agent.tools.common import adk_tool
from sre_agent.tools.mcp.gcp import get_project_id_with_fallback

from .queries import (
    get_agent_token_usage_query,
    get_agent_tool_usage_query,
    get_agent_trace_spans_query,
    get_agent_traces_query,
)

logger = logging.getLogger(__name__)

# Default BigQuery table suffix for OTel spans
_DEFAULT_TABLE_SUFFIX = "_AllSpans"


def _resolve_table(project_id: str, dataset_id: str | None) -> str:
    """Resolve the fully-qualified BigQuery table name.

    Args:
        project_id: GCP project ID.
        dataset_id: Optional dataset ID override.

    Returns:
        Fully-qualified table reference.
    """
    ds = dataset_id or f"{project_id}.otel"
    return f"{ds}{_DEFAULT_TABLE_SUFFIX}"


@adk_tool
async def list_agent_traces(
    project_id: str | None = None,
    dataset_id: str | None = None,
    reasoning_engine_id: str | None = None,
    agent_name: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    limit: int = 20,
    error_only: bool = False,
    tool_context: Any = None,
) -> BaseToolResponse:
    """List recent AI agent runs from Vertex Agent Engine traces.

    Queries BigQuery OTel data to find agent execution traces, filtered
    by reasoning engine, agent name, time window, and error status.

    Args:
        project_id: GCP project ID. Uses default if not provided.
        dataset_id: BigQuery dataset ID (e.g. 'my_project.telemetry').
        reasoning_engine_id: Filter by Vertex Reasoning Engine resource ID.
        agent_name: Filter by root agent name.
        start_time: Start of time window (ISO 8601). Defaults to last 24h.
        end_time: End of time window (ISO 8601). Defaults to now.
        limit: Maximum number of traces to return.
        error_only: If True, only return traces with errors.
        tool_context: ADK tool context.

    Returns:
        List of AgentRunSummary objects.
    """
    pid = project_id or get_project_id_with_fallback()
    if not pid:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="project_id is required but could not be determined",
        )

    table = _resolve_table(pid, dataset_id)
    sql = get_agent_traces_query(
        table,
        agent_name=agent_name,
        reasoning_engine_id=reasoning_engine_id,
        error_only=error_only,
        limit=limit,
    )

    # Build parameters for the query
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    end_dt = end_time or now.isoformat()
    start_dt = start_time or (now - timedelta(hours=24)).isoformat()

    # Replace parameter placeholders with actual values for MCP execution
    sql = sql.replace("@start", f"TIMESTAMP('{start_dt}')").replace(
        "@end", f"TIMESTAMP('{end_dt}')"
    )

    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result={
            "analysis_type": "list_agent_traces",
            "sql_query": sql.strip(),
            "description": (
                f"Agent traces for {'engine ' + reasoning_engine_id if reasoning_engine_id else 'all engines'}"
                f"{', agent=' + agent_name if agent_name else ''}"
                f"{', errors only' if error_only else ''}"
            ),
            "next_steps": [
                "Execute this query using mcp_execute_sql tool",
                "Pick a trace_id and use reconstruct_agent_interaction to visualize it",
                "Use analyze_agent_token_usage for cost analysis across traces",
            ],
        },
        metadata={"project_id": pid, "table": table},
    )


@adk_tool
async def reconstruct_agent_interaction(
    trace_id: str,
    project_id: str | None = None,
    dataset_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Reconstruct the full agent interaction graph for a trace.

    Fetches all spans for a trace, parses GenAI semantic convention
    attributes, builds the parent-child tree, and computes aggregates.

    Primary path uses BigQuery; falls back to Cloud Trace API.

    Args:
        trace_id: The trace ID to reconstruct.
        project_id: GCP project ID.
        dataset_id: BigQuery dataset ID override.
        tool_context: ADK tool context.

    Returns:
        AgentInteractionGraph with the full interaction tree.
    """
    pid = project_id or get_project_id_with_fallback()
    if not pid:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="project_id is required but could not be determined",
        )

    table = _resolve_table(pid, dataset_id)
    sql = get_agent_trace_spans_query(table)
    sql = sql.replace("@trace_id", f"'{trace_id}'")

    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result={
            "analysis_type": "reconstruct_agent_interaction",
            "sql_query": sql.strip(),
            "trace_id": trace_id,
            "description": (
                f"Full span data for trace {trace_id}. Execute the SQL, "
                "then the results can be parsed into an interaction graph."
            ),
            "parse_instructions": (
                "After executing the SQL, the rows contain: trace_id, span_id, "
                "parent_span_id, name, start_time, end_time, duration_nano, "
                "status, kind, attributes (JSON), resource (JSON), events. "
                "Use GenAI semantic convention attributes (gen_ai.agent.name, "
                "gen_ai.tool.name, gen_ai.operation.name, etc.) to classify spans."
            ),
            "next_steps": [
                "Execute the SQL using mcp_execute_sql",
                "Analyze the agent interaction pattern from the results",
                "Use detect_agent_anti_patterns for optimization suggestions",
            ],
        },
        metadata={"project_id": pid, "table": table, "trace_id": trace_id},
    )


@adk_tool
async def analyze_agent_token_usage(
    trace_ids_json: str,
    project_id: str | None = None,
    dataset_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Analyze token usage and tool invocation patterns across agent traces.

    Generates SQL queries for token usage breakdown by agent/model and
    tool invocation statistics for one or more traces.

    Args:
        trace_ids_json: JSON array of trace IDs to analyze (e.g. '["abc123"]').
        project_id: GCP project ID.
        dataset_id: BigQuery dataset ID override.
        tool_context: ADK tool context.

    Returns:
        SQL queries for token and tool usage analysis.
    """
    pid = project_id or get_project_id_with_fallback()
    if not pid:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="project_id is required but could not be determined",
        )

    try:
        trace_ids = json.loads(trace_ids_json)
        if not isinstance(trace_ids, list) or not trace_ids:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error="trace_ids_json must be a non-empty JSON array of trace IDs",
            )
    except json.JSONDecodeError as e:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=f"Invalid JSON in trace_ids_json: {e}",
        )

    table = _resolve_table(pid, dataset_id)

    # Generate queries for each trace
    queries: list[dict[str, str]] = []
    for tid in trace_ids:
        token_sql = get_agent_token_usage_query(table).replace(
            "@trace_id", f"'{tid}'"
        )
        tool_sql = get_agent_tool_usage_query(table).replace(
            "@trace_id", f"'{tid}'"
        )
        queries.append(
            {
                "trace_id": str(tid),
                "token_usage_sql": token_sql.strip(),
                "tool_usage_sql": tool_sql.strip(),
            }
        )

    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result={
            "analysis_type": "agent_token_usage",
            "queries": queries,
            "description": (
                f"Token and tool usage analysis for {len(trace_ids)} trace(s). "
                "Execute each SQL query using mcp_execute_sql."
            ),
            "next_steps": [
                "Execute each token_usage_sql and tool_usage_sql using mcp_execute_sql",
                "Compare token consumption across agents and models",
                "Identify high-cost tool invocations",
            ],
        },
        metadata={"project_id": pid, "trace_count": len(trace_ids)},
    )


@adk_tool
async def detect_agent_anti_patterns(
    trace_id: str,
    project_id: str | None = None,
    dataset_id: str | None = None,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Detect anti-patterns in agent interaction traces.

    First reconstructs the agent interaction graph, then runs detectors
    for: excessive retries, token waste, long reasoning chains, and
    redundant tool calls.

    Args:
        trace_id: The trace ID to analyze.
        project_id: GCP project ID.
        dataset_id: BigQuery dataset ID override.
        tool_context: ADK tool context.

    Returns:
        List of detected anti-patterns with recommendations.
    """
    pid = project_id or get_project_id_with_fallback()
    if not pid:
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error="project_id is required but could not be determined",
        )

    table = _resolve_table(pid, dataset_id)
    sql = get_agent_trace_spans_query(table).replace("@trace_id", f"'{trace_id}'")

    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result={
            "analysis_type": "detect_agent_anti_patterns",
            "sql_query": sql.strip(),
            "trace_id": trace_id,
            "description": (
                f"Fetch spans for trace {trace_id} to detect anti-patterns. "
                "After executing the SQL, analyze the results for: "
                "excessive retries (same tool >3x under one parent), "
                "token waste (output >> input on intermediate LLM calls), "
                "long chains (>8 LLM calls without tool use), "
                "redundant tool calls (same tool called repeatedly)."
            ),
            "anti_pattern_definitions": {
                "excessive_retries": "Same tool called >3 times under same parent span",
                "token_waste": "Output tokens >5x input tokens on non-final LLM calls",
                "long_chain": ">8 consecutive LLM calls without tool use in between",
                "redundant_tool_calls": "Same tool invoked >3 times across the trace",
            },
            "next_steps": [
                "Execute the SQL using mcp_execute_sql",
                "Inspect the span tree for the anti-patterns described above",
                "Use reconstruct_agent_interaction for full visualization",
            ],
        },
        metadata={"project_id": pid, "table": table, "trace_id": trace_id},
    )
