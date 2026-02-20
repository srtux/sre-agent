"""Agent graph topology and trajectory endpoints.

Serves pre-aggregated agent execution graph data from BigQuery
for visualization in the React Flow topology view and Nivo Sankey
trajectory diagrams.
"""

import logging
import re
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from google.cloud import bigquery

logger = logging.getLogger(__name__)
router = APIRouter(tags=["agent_graph"], prefix="/api/v1/graph")

# Allow only valid GCP identifier characters (alphanumeric, hyphens, underscores, dots)
_IDENTIFIER_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$")


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


@router.get("/topology")
async def get_topology(
    project_id: str,
    dataset: str = "agent_graph",
    hours: int = Query(default=24, ge=0, le=720),
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

    Returns:
        A dict with ``nodes`` and ``edges`` lists formatted for
        React Flow consumption.
    """
    _validate_identifier(project_id, "project_id")
    _validate_identifier(dataset, "dataset")

    try:
        client = _get_bq_client(project_id)

        if hours >= 1:
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
                    WHERE time_bucket >= TIMESTAMP_SUB(
                        CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR
                    )
                    GROUP BY source_id, source_type, target_id, target_type
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
                WHERE time_bucket >= TIMESTAMP_SUB(
                    CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR
                )
                GROUP BY source_id, target_id
            """
            edge_rows = list(client.query(edges_query).result())

        else:
            # Real-time views for sub-hour ranges
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
                GROUP BY logical_node_id
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
                GROUP BY source_node_id, destination_node_id
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

        edges: list[dict[str, Any]] = [
            {
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
            for row in edge_rows
        ]

        return {"nodes": nodes, "edges": edges}

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
    hours: int = Query(default=24, ge=0, le=720),
) -> dict[str, list[dict[str, Any]]]:
    """Return trajectory links for a Nivo Sankey diagram.

    Queries the ``agent_trajectories`` view which contains
    chronological step-transition counts aggregated across traces.
    Time filtering is applied by joining back to the underlying
    ``agent_spans_raw`` materialized view.

    Args:
        project_id: GCP project that owns the BigQuery dataset.
        dataset: BigQuery dataset name.
        hours: Look-back window in hours (0-720).

    Returns:
        A dict with ``nodes`` and ``links`` lists formatted for
        Nivo Sankey consumption.
    """
    _validate_identifier(project_id, "project_id")
    _validate_identifier(dataset, "dataset")

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
                  AND start_time >= TIMESTAMP_SUB(
                      CURRENT_TIMESTAMP(), INTERVAL {hours} HOUR
                  )
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

        return {"nodes": nodes, "links": links}

    except Exception as exc:
        logger.exception("Failed to fetch agent trajectories")
        raise HTTPException(
            status_code=500,
            detail="Failed to query trajectory data. Check server logs for details.",
        ) from exc
