"""Agent graph topology and trajectory endpoints.

Serves pre-aggregated agent execution graph data from BigQuery
for visualization in the React Flow topology view and Nivo Sankey
trajectory diagrams.
"""

import logging
import os
import re
import subprocess
from collections import defaultdict
from typing import Any
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query
from google.api_core.exceptions import NotFound
from google.cloud import bigquery
from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)
router = APIRouter(tags=["agent_graph"], prefix="/api/v1/graph")

# Allow only valid GCP identifier characters (alphanumeric, hyphens, underscores, dots)
_IDENTIFIER_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$")

# Logical node ID format: "Type::label" (e.g. "Agent::root", "Tool::search_logs")
_NODE_ID_RE = re.compile(
    r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}::[a-zA-Z0-9][a-zA-Z0-9._/ -]{0,127}$"
)

# ISO 8601 basic validation (e.g. 2026-02-20T12:00:00Z or with offset)
_ISO8601_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)


def _validate_identifier(value: str, name: str) -> str:
    """Validate that a value is a safe BigQuery identifier.

    Args:
        value: The identifier to validate.
        name: Human-readable parameter name for error messages.

    Returns:
        The validated identifier string.

    Raises:
        HTTPException: If the identifier contains invalid characters.
    """
    if not _IDENTIFIER_RE.match(value):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {name}: must match [a-zA-Z0-9._-]{{1,128}}",
        )
    return value


def _validate_logical_node_id(value: str) -> str:
    """URL-decode and validate a logical node ID.

    Node IDs follow the ``Type::label`` format (e.g. ``Agent::root``).
    Path parameters may arrive URL-encoded (``Agent%3A%3Aroot``).

    Args:
        value: The raw path parameter value.

    Returns:
        The decoded and validated node ID.

    Raises:
        HTTPException: If the node ID format is invalid.
    """
    decoded = unquote(value)
    if not _NODE_ID_RE.match(decoded):
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid node ID: must match 'Type::label' format (e.g. 'Agent::root')"
            ),
        )
    return decoded


def _validate_iso8601(value: str, name: str) -> str:
    """Validate that a string looks like an ISO 8601 timestamp.

    Args:
        value: The timestamp string to validate.
        name: Human-readable parameter name for error messages.

    Returns:
        The validated timestamp string.

    Raises:
        HTTPException: If the format does not match ISO 8601.
    """
    if not _ISO8601_RE.match(value):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid {name}: must be ISO 8601 format (e.g. '2026-02-20T12:00:00Z')"
            ),
        )
    return value


def _build_time_filter(
    *,
    timestamp_col: str,
    hours: float,
    start_time: str | None,
    end_time: str | None,
) -> str:
    """Build a SQL time-filter clause.

    If *start_time* is provided it takes precedence over the *hours*
    INTERVAL calculation.

    Args:
        timestamp_col: The column name to filter on.
        hours: Look-back window in hours (used when start_time is None).
        start_time: Optional validated ISO 8601 lower bound.
        end_time: Optional validated ISO 8601 upper bound (defaults to
            ``CURRENT_TIMESTAMP()``).

    Returns:
        A SQL fragment suitable for inclusion in a WHERE clause.
    """
    end_expr = f"TIMESTAMP('{end_time}')" if end_time else "CURRENT_TIMESTAMP()"

    if start_time:
        return (
            f"{timestamp_col} >= TIMESTAMP('{start_time}') "
            f"AND {timestamp_col} <= {end_expr}"
        )

    minutes = int(hours * 60)
    return f"{timestamp_col} >= TIMESTAMP_SUB({end_expr}, INTERVAL {minutes} MINUTE)"


def _get_bq_client(project_id: str) -> bigquery.Client:
    """Create a BigQuery client scoped to the given project.

    Args:
        project_id: GCP project ID to bind the client to.

    Returns:
        A configured BigQuery client.
    """
    return bigquery.Client(project=project_id)


def _get_node_color(node_type: str) -> str:
    """Map a node type to its display colour.

    Args:
        node_type: One of Agent, Tool, LLM, User, or any other string.

    Returns:
        A hex colour string.
    """
    colour_map: dict[str, str] = {
        "Agent": "#26A69A",
        "Tool": "#FFA726",
        "LLM": "#AB47BC",
        "User": "#42A5F5",
    }
    return colour_map.get(node_type, "#78909C")


def _node_type_to_rf_type(node_type: str | None) -> str:
    """Map a BigQuery node_type to a React Flow custom node type key."""
    mapping: dict[str, str] = {"Agent": "agent", "Tool": "tool", "LLM": "llm"}
    return mapping.get(node_type or "", "agent")


def _detect_loops(sequence: list[str], min_repeats: int = 3) -> list[dict[str, Any]]:
    """Detect pathological loops in a step sequence.

    A pathological loop is a cyclical pattern that repeats
    consecutively *min_repeats* or more times.

    Args:
        sequence: Ordered list of logical node IDs from a single trace.
        min_repeats: Minimum number of consecutive repetitions to
            qualify as a loop (default 3).

    Returns:
        A list of dicts, each describing one detected loop::

            {"cycle": ["A", "B"], "repetitions": 5, "startIndex": 3}
    """
    results: list[dict[str, Any]] = []
    n = len(sequence)
    if n < min_repeats:
        return results

    max_cycle_len = n // min_repeats

    for cycle_len in range(1, max_cycle_len + 1):
        i = 0
        while i <= n - cycle_len * min_repeats:
            cycle = sequence[i : i + cycle_len]
            reps = 1
            j = i + cycle_len
            while j + cycle_len <= n and sequence[j : j + cycle_len] == cycle:
                reps += 1
                j += cycle_len
            if reps >= min_repeats:
                results.append(
                    {
                        "cycle": cycle,
                        "repetitions": reps,
                        "startIndex": i,
                    }
                )
                # Skip past this detected loop to avoid overlapping reports
                i = j
            else:
                i += 1

    return results


@router.get("/topology")
async def get_topology(
    project_id: str,
    dataset: str = "agent_graph",
    hours: float = Query(default=24.0, ge=0.0, le=720.0),
    start_time: str | None = None,
    end_time: str | None = None,
    errors_only: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    """Return aggregated topology nodes and edges for React Flow.

    For time ranges >= 1 hour the pre-aggregated ``agent_graph_hourly``
    table is used.  For ranges < 1 hour the raw
    ``agent_topology_nodes`` / ``agent_topology_edges`` views are
    queried instead.

    Args:
        project_id: GCP project that owns the BigQuery dataset.
        dataset: BigQuery dataset name.
        hours: Look-back window in hours (0-720).
        start_time: Optional ISO 8601 lower bound (overrides *hours*).
        end_time: Optional ISO 8601 upper bound (defaults to now).
        errors_only: When True only return nodes/edges with errors.

    Returns:
        A dict with ``nodes`` and ``edges`` lists formatted for
        React Flow consumption.
    """
    _validate_identifier(project_id, "project_id")
    _validate_identifier(dataset, "dataset")
    if start_time is not None:
        start_time = _validate_iso8601(start_time, "start_time")
    if end_time is not None:
        end_time = _validate_iso8601(end_time, "end_time")

    errors_only_edge_having = "HAVING SUM(error_count) > 0" if errors_only else ""
    errors_only_node_having = "HAVING SUM(error_count) > 0" if errors_only else ""

    try:
        client = _get_bq_client(project_id)

        # Determine whether to use start_time or hours for the path decision
        use_hourly = hours >= 1 and start_time is None

        if use_hourly:
            time_filter = _build_time_filter(
                timestamp_col="time_bucket",
                hours=hours,
                start_time=start_time,
                end_time=end_time,
            )
            # The agent_graph_hourly table is edge-centric.
            # We derive both nodes and edges from it in a single query.
            query = f"""
                WITH edges AS (
                    SELECT
                        source_id,
                        source_type,
                        target_id,
                        target_type,
                        SUM(call_count) AS call_count,
                        SAFE_DIVIDE(SUM(sum_duration_ms), NULLIF(SUM(call_count), 0))
                            AS avg_duration_ms,
                        SUM(error_count) AS error_count,
                        SUM(edge_tokens) AS total_tokens
                    FROM `{project_id}.{dataset}.agent_graph_hourly`
                    WHERE {time_filter}
                    GROUP BY source_id, source_type, target_id, target_type
                    {errors_only_edge_having}
                ),
                all_nodes AS (
                    SELECT source_id AS node_id, source_type AS node_type
                    FROM edges
                    UNION DISTINCT
                    SELECT target_id AS node_id, target_type AS node_type
                    FROM edges
                ),
                node_metrics AS (
                    SELECT
                        n.node_id,
                        n.node_type,
                        COALESCE(SUM(e.call_count), 0) AS execution_count,
                        COALESCE(SUM(e.total_tokens), 0) AS total_tokens,
                        COALESCE(SUM(e.error_count), 0) AS error_count,
                        COALESCE(
                            SAFE_DIVIDE(
                                SUM(e.avg_duration_ms * e.call_count),
                                NULLIF(SUM(e.call_count), 0)
                            ), 0
                        ) AS avg_duration_ms
                    FROM all_nodes n
                    LEFT JOIN edges e
                        ON n.node_id = e.target_id
                    GROUP BY n.node_id, n.node_type
                    {errors_only_node_having}
                )
                SELECT 'node' AS record_kind, * FROM node_metrics
            """
            node_rows = list(client.query(query).result())

            edges_query = f"""
                SELECT
                    source_id,
                    target_id,
                    SUM(call_count) AS call_count,
                    SAFE_DIVIDE(SUM(sum_duration_ms), NULLIF(SUM(call_count), 0))
                        AS avg_duration_ms,
                    SUM(error_count) AS error_count,
                    SUM(edge_tokens) AS total_tokens
                FROM `{project_id}.{dataset}.agent_graph_hourly`
                WHERE {time_filter}
                GROUP BY source_id, target_id
                {errors_only_edge_having}
            """
            edge_rows = list(client.query(edges_query).result())

        else:
            # Real-time views for sub-hour ranges or explicit start_time
            nodes_time_filter = _build_time_filter(
                timestamp_col="start_time",
                hours=hours,
                start_time=start_time,
                end_time=end_time,
            )
            edges_time_filter = _build_time_filter(
                timestamp_col="start_time",
                hours=hours,
                start_time=start_time,
                end_time=end_time,
            )

            nodes_query = f"""
                SELECT
                    logical_node_id AS node_id,
                    ANY_VALUE(node_type) AS node_type,
                    SUM(execution_count) AS execution_count,
                    SUM(COALESCE(total_input_tokens, 0)
                        + COALESCE(total_output_tokens, 0)) AS total_tokens,
                    SUM(error_count) AS error_count,
                    SAFE_DIVIDE(
                        SUM(total_duration_ms),
                        NULLIF(SUM(execution_count), 0)
                    ) AS avg_duration_ms
                FROM `{project_id}.{dataset}.agent_topology_nodes`
                WHERE {nodes_time_filter}
                GROUP BY logical_node_id
                {errors_only_node_having}
            """
            edges_query = f"""
                SELECT
                    source_node_id AS source_id,
                    destination_node_id AS target_id,
                    SUM(edge_weight) AS call_count,
                    SAFE_DIVIDE(
                        SUM(total_duration_ms),
                        NULLIF(SUM(edge_weight), 0)
                    ) AS avg_duration_ms,
                    SUM(error_count) AS error_count,
                    SUM(total_tokens) AS total_tokens
                FROM `{project_id}.{dataset}.agent_topology_edges`
                WHERE {edges_time_filter}
                GROUP BY source_node_id, destination_node_id
                {errors_only_edge_having}
            """
            node_rows = list(client.query(nodes_query).result())
            edge_rows = list(client.query(edges_query).result())

        # Extract label from logical_node_id format "Type::label"
        def _extract_label(node_id: str) -> str:
            return node_id.split("::", 1)[1] if "::" in node_id else node_id

        def _extract_type(node_id: str, fallback: str | None) -> str:
            if "::" in node_id:
                return node_id.split("::", 1)[0]
            return fallback or "Agent"

        nodes: list[dict[str, Any]] = [
            {
                "id": row.node_id,
                "type": _node_type_to_rf_type(
                    _extract_type(row.node_id, getattr(row, "node_type", None))
                ),
                "data": {
                    "label": _extract_label(row.node_id),
                    "nodeType": _extract_type(
                        row.node_id, getattr(row, "node_type", None)
                    ),
                    "executionCount": row.execution_count or 0,
                    "totalTokens": row.total_tokens or 0,
                    "errorCount": row.error_count or 0,
                    "avgDurationMs": round(row.avg_duration_ms or 0, 1),
                },
                "position": {"x": 0, "y": 0},
            }
            for row in node_rows
        ]

        formatted_edges: list[dict[str, Any]] = []
        for row in edge_rows:
            edge: dict[str, Any] = {
                "id": f"{row.source_id}->{row.target_id}",
                "source": row.source_id,
                "target": row.target_id,
                "data": {
                    "callCount": row.call_count or 0,
                    "avgDurationMs": round(row.avg_duration_ms or 0, 1),
                    "errorCount": row.error_count or 0,
                    "totalTokens": row.total_tokens or 0,
                },
            }
            error_count = row.error_count or 0
            if error_count > 0:
                edge["animated"] = True
                edge["style"] = {"stroke": "#f85149", "strokeWidth": 2}
            formatted_edges.append(edge)

        return {"nodes": nodes, "edges": formatted_edges}

    except NotFound as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NOT_SETUP",
                "detail": "BigQuery agent graph is not configured for this project.",
            },
        ) from exc
    except Exception as exc:
        logger.exception("Failed to fetch agent graph topology")
        raise HTTPException(
            status_code=500,
            detail="Failed to query topology data. Check server logs for details.",
        ) from exc


@router.get("/trajectories")
async def get_trajectories(
    project_id: str,
    dataset: str = "agent_graph",
    trace_dataset: str = "traces",
    hours: float = Query(default=24.0, ge=0.0, le=720.0),
    start_time: str | None = None,
    end_time: str | None = None,
    errors_only: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    """Return trajectory links for a Nivo Sankey diagram.

    Queries the ``agent_trajectories`` view which contains
    chronological step-transition counts aggregated across traces.
    Time filtering is applied by joining back to the underlying
    ``agent_spans_raw`` materialized view.  Also performs loop
    detection to identify pathological cycles within individual
    traces.

    Args:
        project_id: GCP project that owns the BigQuery dataset.
        dataset: BigQuery dataset name.
        trace_dataset: BigQuery dataset containing ``_AllSpans``.
        hours: Look-back window in hours (0-720).
        start_time: Optional ISO 8601 lower bound (overrides *hours*).
        end_time: Optional ISO 8601 upper bound (defaults to now).
        errors_only: When True only return nodes/edges with errors.

    Returns:
        A dict with ``nodes``, ``links``, and ``loopTraces`` lists
        formatted for Nivo Sankey consumption with loop annotations.
    """
    _validate_identifier(project_id, "project_id")
    _validate_identifier(dataset, "dataset")
    _validate_identifier(trace_dataset, "trace_dataset")
    if start_time is not None:
        start_time = _validate_iso8601(start_time, "start_time")
    if end_time is not None:
        end_time = _validate_iso8601(end_time, "end_time")

    time_filter = _build_time_filter(
        timestamp_col="start_time",
        hours=hours,
        start_time=start_time,
        end_time=end_time,
    )

    errors_only_clause = "AND status_code = 'ERROR'" if errors_only else ""

    try:
        client = _get_bq_client(project_id)

        # The agent_trajectories view is pre-aggregated without a
        # timestamp column. We rebuild it inline with a time filter on
        # the underlying agent_spans_raw MV.
        query = f"""
            WITH sequenced_steps AS (
                SELECT
                    trace_id,
                    logical_node_id,
                    node_type,
                    ROW_NUMBER() OVER(
                        PARTITION BY trace_id ORDER BY start_time ASC
                    ) AS step_sequence
                FROM `{project_id}.{dataset}.agent_spans_raw`
                WHERE node_type != 'Glue'
                  AND {time_filter}
                  {errors_only_clause}
            ),
            trajectory_links AS (
                SELECT
                    a.logical_node_id AS source_node,
                    a.node_type       AS source_type,
                    b.logical_node_id AS target_node,
                    b.node_type       AS target_type,
                    a.trace_id
                FROM sequenced_steps a
                JOIN sequenced_steps b
                    ON a.trace_id = b.trace_id
                    AND a.step_sequence + 1 = b.step_sequence
            )
            SELECT
                source_node,
                source_type,
                target_node,
                target_type,
                COUNT(DISTINCT trace_id) AS trace_count
            FROM trajectory_links
            GROUP BY source_node, source_type, target_node, target_type
        """

        rows = client.query(query).result()

        seen_nodes: dict[str, str] = {}
        links: list[dict[str, Any]] = []

        for row in rows:
            source: str = row.source_node
            target: str = row.target_node

            if source not in seen_nodes:
                seen_nodes[source] = row.source_type or "Agent"
            if target not in seen_nodes:
                seen_nodes[target] = row.target_type or "Tool"

            links.append(
                {
                    "source": source,
                    "target": target,
                    "value": row.trace_count,
                }
            )

        nodes: list[dict[str, str]] = [
            {"id": node_id, "nodeColor": _get_node_color(node_type)}
            for node_id, node_type in seen_nodes.items()
        ]

        # --- Loop detection ---
        loop_query = f"""
            SELECT
                trace_id,
                ARRAY_AGG(logical_node_id ORDER BY start_time ASC) AS step_sequence
            FROM `{project_id}.{dataset}.agent_spans_raw`
            WHERE node_type != 'Glue'
              AND {time_filter}
              {errors_only_clause}
            GROUP BY trace_id
        """

        loop_rows = client.query(loop_query).result()

        loop_results: dict[str, list[dict[str, Any]]] = {}
        for row in loop_rows:
            detected = _detect_loops(list(row.step_sequence))
            if detected:
                loop_results[row.trace_id] = detected

        return {
            "nodes": nodes,
            "links": links,
            "loopTraces": [
                {
                    "traceId": trace_id,
                    "loops": loops_detected,
                }
                for trace_id, loops_detected in loop_results.items()
            ],
        }

    except NotFound as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "NOT_SETUP",
                "detail": "BigQuery trajectories are not configured for this project.",
            },
        ) from exc
    except Exception as exc:
        logger.exception("Failed to fetch agent trajectories")
        raise HTTPException(
            status_code=500,
            detail="Failed to query trajectory data. Check server logs for details.",
        ) from exc


@router.get("/node/{logical_node_id:path}")
async def get_node_detail(
    logical_node_id: str,
    project_id: str,
    dataset: str = "agent_graph",
    trace_dataset: str = "traces",
    hours: float = Query(default=24.0, ge=0.0, le=720.0),
    errors_only: bool = False,
) -> dict[str, Any]:
    """Return detailed metrics for a single topology node.

    Queries the ``agent_spans_raw`` materialized view to compute
    invocation counts, error rates, token breakdowns, cost estimates,
    and latency percentiles for the given node.  Also returns the 3
    most recent raw payloads by joining back to the source
    ``_AllSpans`` table for prompt/completion/tool data.

    Args:
        logical_node_id: URL-encoded node ID in ``Type::label`` format.
        project_id: GCP project that owns the BigQuery dataset.
        dataset: BigQuery dataset name.
        trace_dataset: BigQuery dataset containing ``_AllSpans``.
        hours: Look-back window in hours (0-720).
        errors_only: Only fetch error payloads if True.

    Returns:
        A dict with detailed node metrics and recent payloads.
    """
    _validate_identifier(project_id, "project_id")
    _validate_identifier(dataset, "dataset")
    _validate_identifier(trace_dataset, "trace_dataset")
    node_id = _validate_logical_node_id(logical_node_id)

    try:
        client = _get_bq_client(project_id)

        # --- Aggregate metrics ---
        metrics_query = f"""
            SELECT
                COUNT(*) AS total_invocations,
                COUNTIF(status_code = 'ERROR') AS error_count,
                SAFE_DIVIDE(
                    COUNTIF(status_code = 'ERROR'),
                    COUNT(*)
                ) AS error_rate,
                SUM(COALESCE(input_tokens, 0)) AS input_tokens,
                SUM(COALESCE(output_tokens, 0)) AS output_tokens,
                SUM(
                    CASE
                        WHEN LOWER(logical_node_id) LIKE '%pro%' THEN
                            COALESCE(input_tokens, 0) * 0.00000125
                            + COALESCE(output_tokens, 0) * 0.000005
                        WHEN LOWER(logical_node_id) LIKE '%flash%' THEN
                            COALESCE(input_tokens, 0) * 0.000000075
                            + COALESCE(output_tokens, 0) * 0.0000003
                        ELSE
                            COALESCE(input_tokens, 0) * 0.000000075
                            + COALESCE(output_tokens, 0) * 0.0000003
                    END
                ) AS estimated_cost,
                APPROX_QUANTILES(duration_ms, 100)[OFFSET(50)] AS p50,
                APPROX_QUANTILES(duration_ms, 100)[OFFSET(95)] AS p95,
                APPROX_QUANTILES(duration_ms, 100)[OFFSET(99)] AS p99
            FROM `{project_id}.{dataset}.agent_spans_raw`
            WHERE logical_node_id = @node_id
              AND start_time >= TIMESTAMP_SUB(
                  CURRENT_TIMESTAMP(), INTERVAL {int(hours * 60)} MINUTE
              )
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("node_id", "STRING", node_id),
            ]
        )

        metrics_rows = list(client.query(metrics_query, job_config=job_config).result())

        if not metrics_rows or metrics_rows[0].total_invocations == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for node '{node_id}' in the last {hours}h.",
            )

        m = metrics_rows[0]

        # --- Top errors ---
        errors_query = f"""
            SELECT
                status_code AS message,
                COUNT(*) AS count
            FROM `{project_id}.{dataset}.agent_spans_raw`
            WHERE logical_node_id = @node_id
              AND status_code = 'ERROR'
              AND start_time >= TIMESTAMP_SUB(
                  CURRENT_TIMESTAMP(), INTERVAL {int(hours * 60)} MINUTE
              )
            GROUP BY status_code
            ORDER BY count DESC
            LIMIT 3
        """

        error_rows = list(client.query(errors_query, job_config=job_config).result())

        # --- Recent payloads (join raw MV back to source _AllSpans) ---
        payload_query = f"""
            SELECT
                r.trace_id,
                r.span_id,
                r.start_time,
                r.node_type,
                JSON_VALUE(s.attributes, '$.\"gen_ai.prompt\"') AS prompt,
                JSON_VALUE(s.attributes, '$.\"gen_ai.completion\"') AS completion,
                JSON_VALUE(s.attributes, '$.\"tool.input\"') AS tool_input,
                JSON_VALUE(s.attributes, '$.\"tool.output\"') AS tool_output
            FROM `{project_id}.{dataset}.agent_spans_raw` r
            JOIN `{project_id}.{trace_dataset}._AllSpans` s
              ON r.span_id = s.span_id AND r.trace_id = s.trace_id
            WHERE r.logical_node_id = @node_id
              AND r.start_time >= TIMESTAMP_SUB(
                  CURRENT_TIMESTAMP(), INTERVAL {int(hours * 60)} MINUTE
              )
              {"AND r.status_code = 'ERROR'" if errors_only else ""}
            ORDER BY r.start_time DESC
            LIMIT 10
        """

        payload_rows = list(client.query(payload_query, job_config=job_config).result())

        # Decompose node_id into type and label
        if "::" in node_id:
            node_type, label = node_id.split("::", 1)
        else:
            node_type, label = "Agent", node_id

        return {
            "nodeId": node_id,
            "nodeType": node_type,
            "label": label,
            "totalInvocations": m.total_invocations,
            "errorRate": round(m.error_rate or 0, 4),
            "errorCount": m.error_count or 0,
            "inputTokens": m.input_tokens or 0,
            "outputTokens": m.output_tokens or 0,
            "estimatedCost": round(m.estimated_cost or 0, 6),
            "latency": {
                "p50": round(float(m.p50 or 0), 1),
                "p95": round(float(m.p95 or 0), 1),
                "p99": round(float(m.p99 or 0), 1),
            },
            "topErrors": [
                {"message": row.message or "", "count": row.count} for row in error_rows
            ],
            "recentPayloads": [
                {
                    "traceId": row.trace_id,
                    "spanId": row.span_id,
                    "timestamp": (
                        row.start_time.isoformat() if row.start_time else None
                    ),
                    "nodeType": row.node_type,
                    "prompt": row.prompt,
                    "completion": row.completion,
                    "toolInput": row.tool_input,
                    "toolOutput": row.tool_output,
                }
                for row in payload_rows
            ],
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to fetch node detail for %s", node_id)
        raise HTTPException(
            status_code=500,
            detail="Failed to query node detail. Check server logs for details.",
        ) from exc


class SetupGraphRequest(BaseModel):
    """Request model for auto-setting up the Agent Graph BigQuery resources."""

    model_config = ConfigDict(extra="forbid")

    project_id: str
    trace_dataset: str
    service_name: str


@router.post("/setup")
async def setup_agent_graph(req: SetupGraphRequest) -> dict[str, str]:
    """Execute the bigquery setup script."""
    _validate_identifier(req.project_id, "project_id")
    _validate_identifier(req.trace_dataset, "trace_dataset")

    script_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "scripts",
        "setup_agent_graph_bq.sh",
    )

    if not os.path.exists(script_path):
        raise HTTPException(status_code=500, detail="Setup script not found.")

    env = os.environ.copy()
    env["PROJECT_ID"] = req.project_id
    env["TRACE_DATASET"] = req.trace_dataset
    env["SERVICE_NAME"] = req.service_name

    try:
        subprocess.run(
            [
                script_path,
                req.project_id,
                req.trace_dataset,
                "agent_graph",
                req.service_name,
            ],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        return {
            "status": "success",
            "message": "BigQuery agent graph configured successfully.",
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Setup script failed: {e.stderr}")
        raise HTTPException(
            status_code=500, detail=f"Setup script failed: {e.stderr}"
        ) from e


@router.get("/edge/{source_id:path}/{target_id:path}")
async def get_edge_detail(
    source_id: str,
    target_id: str,
    project_id: str,
    dataset: str = "agent_graph",
    hours: float = Query(default=24.0, ge=0.0, le=720.0),
) -> dict[str, Any]:
    """Return detailed metrics for a single topology edge.

    Queries the ``agent_topology_edges`` view filtered by source and
    destination node IDs.

    Args:
        source_id: URL-encoded source node ID in ``Type::label`` format.
        target_id: URL-encoded target node ID in ``Type::label`` format.
        project_id: GCP project that owns the BigQuery dataset.
        dataset: BigQuery dataset name.
        hours: Look-back window in hours (0-720).

    Returns:
        A dict with detailed edge metrics.
    """
    _validate_identifier(project_id, "project_id")
    _validate_identifier(dataset, "dataset")
    validated_source = _validate_logical_node_id(source_id)
    validated_target = _validate_logical_node_id(target_id)

    try:
        client = _get_bq_client(project_id)

        query = f"""
            SELECT
                SUM(edge_weight) AS call_count,
                SUM(error_count) AS error_count,
                SAFE_DIVIDE(
                    SUM(error_count),
                    NULLIF(SUM(edge_weight), 0)
                ) AS error_rate,
                SAFE_DIVIDE(
                    SUM(total_duration_ms),
                    NULLIF(SUM(edge_weight), 0)
                ) AS avg_duration_ms,
                APPROX_QUANTILES(total_duration_ms, 100)[OFFSET(95)] AS p95_duration_ms,
                APPROX_QUANTILES(total_duration_ms, 100)[OFFSET(99)] AS p99_duration_ms,
                SUM(total_tokens) AS total_tokens,
                SUM(input_tokens) AS input_tokens,
                SUM(output_tokens) AS output_tokens
            FROM `{project_id}.{dataset}.agent_topology_edges`
            WHERE source_node_id = @source_id
              AND destination_node_id = @target_id
              AND start_time >= TIMESTAMP_SUB(
                  CURRENT_TIMESTAMP(), INTERVAL {int(hours * 60)} MINUTE
              )
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("source_id", "STRING", validated_source),
                bigquery.ScalarQueryParameter("target_id", "STRING", validated_target),
            ]
        )

        rows = list(client.query(query, job_config=job_config).result())

        if not rows or rows[0].call_count is None or rows[0].call_count == 0:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"No data found for edge '{validated_source}' -> "
                    f"'{validated_target}' in the last {hours}h."
                ),
            )

        r = rows[0]

        return {
            "sourceId": validated_source,
            "targetId": validated_target,
            "callCount": r.call_count or 0,
            "errorCount": r.error_count or 0,
            "errorRate": round(r.error_rate or 0, 4),
            "avgDurationMs": round(float(r.avg_duration_ms or 0), 1),
            "p95DurationMs": round(float(r.p95_duration_ms or 0), 1),
            "p99DurationMs": round(float(r.p99_duration_ms or 0), 1),
            "totalTokens": r.total_tokens or 0,
            "inputTokens": r.input_tokens or 0,
            "outputTokens": r.output_tokens or 0,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "Failed to fetch edge detail for %s -> %s",
            validated_source,
            validated_target,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to query edge detail. Check server logs for details.",
        ) from exc


@router.get("/timeseries")
async def get_timeseries(
    project_id: str,
    dataset: str = "agent_graph",
    hours: float = Query(default=24.0, ge=0.0, le=720.0),
    start_time: str | None = None,
    end_time: str | None = None,
) -> dict[str, Any]:
    """Return per-bucket time-series metrics for each node.

    Queries the ``agent_graph_hourly`` table grouped by
    ``time_bucket`` and ``target_id`` to produce trend data suitable
    for sparkline rendering.

    Args:
        project_id: GCP project that owns the BigQuery dataset.
        dataset: BigQuery dataset name.
        hours: Look-back window in hours (2-720).
        start_time: Optional ISO 8601 lower bound (overrides *hours*).
        end_time: Optional ISO 8601 upper bound (defaults to now).

    Returns:
        A dict with a ``series`` mapping of node IDs to ordered
        time-series points.
    """
    _validate_identifier(project_id, "project_id")
    _validate_identifier(dataset, "dataset")
    if start_time is not None:
        start_time = _validate_iso8601(start_time, "start_time")
    if end_time is not None:
        end_time = _validate_iso8601(end_time, "end_time")

    time_filter = _build_time_filter(
        timestamp_col="time_bucket",
        hours=hours,
        start_time=start_time,
        end_time=end_time,
    )

    try:
        client = _get_bq_client(project_id)

        query = f"""
            SELECT
                time_bucket,
                target_id AS node_id,
                SUM(node_call_count) AS call_count,
                SUM(node_error_count) AS error_count,
                SAFE_DIVIDE(
                    SUM(node_sum_duration_ms),
                    NULLIF(SUM(node_call_count), 0)
                ) AS avg_duration_ms,
                SUM(node_total_tokens) AS total_tokens,
                SUM(node_total_cost) AS total_cost
            FROM `{project_id}.{dataset}.agent_graph_hourly`
            WHERE {time_filter}
              AND node_call_count IS NOT NULL
            GROUP BY time_bucket, target_id
            ORDER BY target_id, time_bucket ASC
        """

        rows = list(client.query(query).result())

        series: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            series[row.node_id].append(
                {
                    "bucket": (
                        row.time_bucket.isoformat()
                        if hasattr(row.time_bucket, "isoformat")
                        else str(row.time_bucket)
                    ),
                    "callCount": row.call_count or 0,
                    "errorCount": row.error_count or 0,
                    "avgDurationMs": round(float(row.avg_duration_ms or 0), 1),
                    "totalTokens": row.total_tokens or 0,
                    "totalCost": round(float(row.total_cost or 0), 6),
                }
            )

        return {"series": dict(series)}

    except Exception as exc:
        logger.exception("Failed to fetch timeseries data")
        raise HTTPException(
            status_code=500,
            detail="Failed to query timeseries data. Check server logs for details.",
        ) from exc


@router.get("/trace/{trace_id}/logs")
async def get_trace_logs(trace_id: str, project_id: str) -> dict[str, Any]:
    """Fetch logs from Cloud Logging for a specific trace ID."""
    _validate_identifier(project_id, "project_id")
    # Quick sanity check on trace ID to avoid injection
    if not re.match(r"^[a-fA-F0-9]{32}$", trace_id):
        raise HTTPException(status_code=400, detail="Invalid trace ID format.")

    try:
        from google.cloud import logging as cloud_logging

        client = cloud_logging.Client(project=project_id)  # type: ignore[no-untyped-call]
        filter_str = f'trace="projects/{project_id}/traces/{trace_id}"'
        entries = client.list_entries(filter_=filter_str, max_results=100)  # type: ignore[no-untyped-call]

        logs = []
        for entry in entries:
            logs.append(
                {
                    "timestamp": entry.timestamp.isoformat()
                    if entry.timestamp
                    else None,
                    "severity": entry.severity,
                    "payload": entry.payload,
                }
            )

        return {"traceId": trace_id, "logs": logs}
    except Exception as exc:
        logger.exception("Failed to fetch trace logs from Cloud Logging")
        raise HTTPException(
            status_code=500, detail="Failed to query Cloud Logging."
        ) from exc


@router.get("/trace/{trace_id}/span/{span_id}/details")
async def get_span_details(
    trace_id: str,
    span_id: str,
    project_id: str,
    trace_dataset: str = "traces",
) -> dict[str, Any]:
    """Fetch rich details (including errors) for a specific span from BigQuery."""
    _validate_identifier(project_id, "project_id")
    _validate_identifier(trace_dataset, "trace_dataset")

    if not re.match(r"^[a-fA-F0-9]{32}$", trace_id):
        raise HTTPException(status_code=400, detail="Invalid trace ID format.")
    if not re.match(r"^[a-fA-F0-9]{16}$", span_id):
        raise HTTPException(status_code=400, detail="Invalid span ID format.")

    try:
        client = _get_bq_client(project_id)

        query = f"""
            SELECT
                status.code as status_code,
                status.message as status_message,
                TO_JSON_STRING(events) as events_json,
                TO_JSON_STRING(attributes) as attributes_json
            FROM `{project_id}.{trace_dataset}._AllSpans`
            WHERE trace_id = @trace_id AND span_id = @span_id
            LIMIT 1
        """

        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("trace_id", "STRING", trace_id),
                bigquery.ScalarQueryParameter("span_id", "STRING", span_id),
            ]
        )

        rows = list(client.query(query, job_config=job_config).result())

        if not rows:
            raise HTTPException(status_code=404, detail="Span not found.")

        row = rows[0]

        import json

        events = json.loads(row.events_json) if row.events_json else []
        attributes = json.loads(row.attributes_json) if row.attributes_json else {}

        # Extract exceptions
        exceptions = []
        for evt in events:
            if evt.get("name") == "exception":
                attrs = evt.get("attributes", {})
                exc_obj = {
                    "message": attrs.get("exception.message"),
                    "stacktrace": attrs.get("exception.stacktrace"),
                    "type": attrs.get("exception.type"),
                }
                exceptions.append(exc_obj)

        return {
            "traceId": trace_id,
            "spanId": span_id,
            "statusCode": row.status_code,
            "statusMessage": row.status_message,
            "exceptions": exceptions,
            "attributes": attributes,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to fetch span details")
        raise HTTPException(
            status_code=500, detail="Failed to fetch span details."
        ) from exc
