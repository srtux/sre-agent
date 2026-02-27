"""BigQuery graph query tools for historical trajectories."""

import logging
from typing import Any

from pydantic import Field

from sre_agent.auth import get_current_project_id
from sre_agent.tools.bigquery.client import BigQueryClient
from sre_agent.tools.common import adk_tool

logger = logging.getLogger(__name__)


@adk_tool
async def query_historical_trajectories(
    gql_query: str = Field(
        ...,
        description="A valid BigQuery GQL query. Ensure your query targets the graph: `GRAPH `{project_id}.agentops.agent_topology_graph` "
        "and uses MATCH statements to find paths. You MUST template the project ID with {project_id}, e.g. GRAPH `{project_id}.agentops.agent_topology_graph`",
    ),
    **kwargs: Any,
) -> dict[str, Any]:
    """Query historical reasoning trajectories of the AutoSRE agent using BigQuery Graph Query Language (GQL).

    Use this tool to find out what tools were historically useful for similar incidents, or what the common
    patterns of investigation are. You must write a valid GQL query targeting the `agentops.agent_topology_graph` property graph.
    """
    project_id = get_current_project_id()
    if not project_id:
        return {"error": "No active GCP project_id found in context."}

    # Automatically swap the {project_id} string
    try:
        query = gql_query.format(project_id=project_id)
    except KeyError as e:
        return {
            "error": f"Failed to format GQL query. Did you include unsupported template variables? Error: {e}"
        }

    logger.info(f"Executing GQL query on agent topology graph in {project_id}")
    logger.debug(f"Query: {query}")

    client = BigQueryClient(project_id, tool_context=kwargs.get("tool_context"))

    try:
        # We use the execute_query method
        # BigQuery GQL is executed via standard query interface, just starts with GRAPH
        results = await client.execute_query(query)

        # Handle list of dicts
        if not results:
            return {
                "status": "success",
                "message": "Query returned no results",
                "results": [],
            }

        # Truncate if results are too large
        if len(results) > 50:
            logger.warning(f"GQL query returned {len(results)} rows. Truncating to 50.")
            results = results[:50]

        return {"status": "success", "results": results, "row_count": len(results)}
    except Exception as e:
        logger.error(f"Failed to execute GQL query: {e}")
        return {"error": str(e)}


@adk_tool
async def find_successful_strategy(
    symptom: str = Field(
        ...,
        description="The symptom, alert name, or key failure indicator to search for.",
    ),
    **kwargs: Any,
) -> dict[str, Any]:
    """Query historical BigQuery Graph to find successful investigation paths (score >= 80) for a given symptom or alert.

    Returns the ordered sequence of tool calls that led to root cause. Use this at the start of an investigation to learn from past successes.
    """
    query = f"""
    GRAPH `{{project_id}}.agentops.agent_topology_graph`
    MATCH p = (start_node)-[*]->(end_node)
    WHERE (start_node.name LIKE '%{symptom}%' OR start_node.attributes.message LIKE '%{symptom}%')
      AND CAST(end_node.attributes.`sre.investigation.score` AS FLOAT64) >= 80.0
    RETURN p
    LIMIT 3
    """
    return await query_historical_trajectories(  # type: ignore[no-any-return]
        gql_query=query, tool_context=kwargs.get("tool_context")
    )


@adk_tool
async def find_past_mistakes(
    symptom: str = Field(
        ...,
        description="The symptom, alert name, or key failure indicator to search for.",
    ),
    **kwargs: Any,
) -> dict[str, Any]:
    """Query historical BigQuery Graph to find failed investigation paths (score < 50 or errors) for a given symptom.

    Use this to avoid repeating past diagnostic mistakes or pursuing dead ends.
    """
    query = f"""
    GRAPH `{{project_id}}.agentops.agent_topology_graph`
    MATCH p = (start_node)-[*]->(end_node)
    WHERE (start_node.name LIKE '%{symptom}%' OR start_node.attributes.message LIKE '%{symptom}%')
      AND (CAST(end_node.attributes.`sre.investigation.score` AS FLOAT64) < 50.0
           OR end_node.attributes.error IS NOT NULL)
    RETURN p
    LIMIT 3
    """
    return await query_historical_trajectories(  # type: ignore[no-any-return]
        gql_query=query, tool_context=kwargs.get("tool_context")
    )
