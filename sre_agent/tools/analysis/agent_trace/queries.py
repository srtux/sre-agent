"""BigQuery SQL generators for agent trace analysis.

Generates SQL queries for extracting agent interaction data from
OpenTelemetry traces stored in BigQuery (_AllSpans table).
"""

from __future__ import annotations


def get_agent_traces_query(
    table: str,
    *,
    agent_name: str | None = None,
    reasoning_engine_id: str | None = None,
    error_only: bool = False,
    limit: int = 20,
) -> str:
    """Generate SQL to list agent runs from the _AllSpans table.

    Args:
        table: Fully qualified BigQuery table (e.g. 'project.dataset.table').
        agent_name: Optional filter for a specific agent name.
        reasoning_engine_id: Optional filter for reasoning engine resource ID.
        error_only: If True, only return traces with errors.
        limit: Maximum number of traces to return.

    Returns:
        SQL query string with @start and @end parameters.
    """
    where_clauses = [
        "start_time BETWEEN @start AND @end",
    ]

    if reasoning_engine_id:
        where_clauses.append(
            f"JSON_EXTRACT_SCALAR(resource.attributes, '$.cloud.resource_id') "
            f"LIKE '%{reasoning_engine_id}%'"
        )
    else:
        where_clauses.append(
            "JSON_EXTRACT_SCALAR(resource.attributes, '$.cloud.resource_id') "
            "LIKE '%reasoningEngine%'"
        )

    if agent_name:
        where_clauses.append(
            f"JSON_EXTRACT_SCALAR(attributes, '$.gen_ai.agent.name') = '{agent_name}'"
        )

    where = " AND ".join(where_clauses)

    having = ""
    if error_only:
        having = "HAVING error_count > 0"

    return f"""\
SELECT
  trace_id,
  MIN(start_time) AS start_time,
  MAX(end_time) AS end_time,
  (UNIX_MILLIS(MAX(end_time)) - UNIX_MILLIS(MIN(start_time))) AS duration_ms,
  COUNT(*) AS span_count,
  COUNTIF(status.code = 2) AS error_count,
  SUM(SAFE_CAST(JSON_EXTRACT_SCALAR(attributes, '$.gen_ai.usage.input_tokens') AS INT64)) AS total_input_tokens,
  SUM(SAFE_CAST(JSON_EXTRACT_SCALAR(attributes, '$.gen_ai.usage.output_tokens') AS INT64)) AS total_output_tokens,
  ARRAY_AGG(DISTINCT JSON_EXTRACT_SCALAR(attributes, '$.gen_ai.agent.name') IGNORE NULLS LIMIT 1)[SAFE_OFFSET(0)] AS root_agent_name
FROM `{table}`
WHERE {where}
GROUP BY trace_id
{having}
ORDER BY start_time DESC
LIMIT {limit}"""


def get_agent_trace_spans_query(table: str) -> str:
    """Generate SQL to fetch all spans for a single agent trace.

    Args:
        table: Fully qualified BigQuery table.

    Returns:
        SQL query string with @trace_id parameter.
    """
    return f"""\
SELECT
  trace_id,
  span_id,
  parent_span_id,
  name,
  start_time,
  end_time,
  duration_nano,
  status,
  kind,
  attributes,
  resource,
  events
FROM `{table}`
WHERE trace_id = @trace_id
ORDER BY start_time ASC"""


def get_agent_token_usage_query(table: str) -> str:
    """Generate SQL to get token usage breakdown by agent and model.

    Args:
        table: Fully qualified BigQuery table.

    Returns:
        SQL query string with @trace_id parameter.
    """
    return f"""\
SELECT
  JSON_EXTRACT_SCALAR(attributes, '$.gen_ai.agent.name') AS agent_name,
  JSON_EXTRACT_SCALAR(attributes, '$.gen_ai.request.model') AS model,
  COUNT(*) AS call_count,
  SUM(SAFE_CAST(JSON_EXTRACT_SCALAR(attributes, '$.gen_ai.usage.input_tokens') AS INT64)) AS input_tokens,
  SUM(SAFE_CAST(JSON_EXTRACT_SCALAR(attributes, '$.gen_ai.usage.output_tokens') AS INT64)) AS output_tokens
FROM `{table}`
WHERE trace_id = @trace_id
  AND JSON_EXTRACT_SCALAR(attributes, '$.gen_ai.operation.name') IN ('generate_content', 'chat')
GROUP BY agent_name, model
ORDER BY input_tokens DESC"""


def get_agent_tool_usage_query(table: str) -> str:
    """Generate SQL to get tool invocation statistics.

    Args:
        table: Fully qualified BigQuery table.

    Returns:
        SQL query string with @trace_id parameter.
    """
    return f"""\
SELECT
  JSON_EXTRACT_SCALAR(attributes, '$.gen_ai.tool.name') AS tool_name,
  JSON_EXTRACT_SCALAR(attributes, '$.gen_ai.agent.name') AS invoked_by,
  COUNT(*) AS call_count,
  AVG(duration_nano / 1e6) AS avg_duration_ms,
  COUNTIF(status.code = 2) AS error_count
FROM `{table}`
WHERE trace_id = @trace_id
  AND JSON_EXTRACT_SCALAR(attributes, '$.gen_ai.operation.name') = 'execute_tool'
GROUP BY tool_name, invoked_by
ORDER BY call_count DESC"""
