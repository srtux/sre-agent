"""Advanced BigQuery tools for analyzing new OTel schema features.

This module provides analysis tools for advanced OpenTelemetry features:
- Events (exceptions, log annotations)
- Links (causal relationships between spans)
- Instrumentation scope (library tracking)
- Trace state (W3C vendor-specific data)
"""

import json
import logging

from ..decorators import adk_tool

logger = logging.getLogger(__name__)


@adk_tool
def analyze_span_events(
    dataset_id: str,
    table_name: str = "_AllSpans",
    time_window_hours: int = 24,
    event_name_filter: str | None = None,
    service_name: str | None = None,
    limit: int = 100,
) -> str:
    """
    Analyzes span events (exceptions, logs, annotations) from traces.

    Events are discrete occurrences during a span's lifetime, commonly used for:
    - Exceptions and error details
    - Log messages attached to spans
    - Custom annotations and milestones

    Args:
        dataset_id: BigQuery dataset ID
        table_name: Table name containing OTEL traces
        time_window_hours: How many hours back to analyze
        event_name_filter: Optional filter for event names (e.g., 'exception')
        service_name: Optional filter for specific service
        limit: Maximum number of results

    Returns:
        JSON with SQL query to analyze span events.

    Common event names:
    - exception: Exception events with stack traces
    - log: Log messages
    - Custom event names defined by applications
    """
    where_conditions = [
        f"start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {time_window_hours} HOUR)",
        "ARRAY_LENGTH(events) > 0",
    ]

    if service_name:
        where_conditions.append(
            f"JSON_EXTRACT_SCALAR(resource.attributes, '$.service.name') = '{service_name}'"
        )

    where_clause = " AND ".join(where_conditions)

    # Build event filter for UNNEST
    event_filter = ""
    if event_name_filter:
        event_filter = f"AND event.name = '{event_name_filter}'"

    query = f"""
SELECT
  trace_id,
  span_id,
  name as span_name,
  JSON_EXTRACT_SCALAR(resource.attributes, '$.service.name') as service_name,
  event.name as event_name,
  event.time as event_time,
  JSON_EXTRACT_SCALAR(event.attributes, '$.exception.type') as exception_type,
  JSON_EXTRACT_SCALAR(event.attributes, '$.exception.message') as exception_message,
  JSON_EXTRACT_SCALAR(event.attributes, '$.exception.stacktrace') as exception_stacktrace,
  event.attributes as event_attributes,
  status.code as span_status_code,
  status.message as span_status_message
FROM `{dataset_id}.{table_name}`,
UNNEST(events) as event
WHERE {where_clause}
  {event_filter}
ORDER BY event.time DESC
LIMIT {limit}
"""

    return json.dumps(
        {
            "analysis_type": "span_events",
            "sql_query": query.strip(),
            "description": f"Analyze span events for last {time_window_hours}h",
            "next_steps": [
                "Execute this query using BigQuery MCP execute_sql tool",
                "Look for exception events to identify error root causes",
                "Examine exception_stacktrace for detailed error information",
                "Correlate event timestamps with span timing issues",
            ],
        }
    )


@adk_tool
def analyze_exception_patterns(
    dataset_id: str,
    table_name: str = "_AllSpans",
    time_window_hours: int = 24,
    service_name: str | None = None,
    group_by: str = "exception_type",
) -> str:
    """
    Analyzes exception patterns across services using span events.

    This tool aggregates exception data to identify:
    - Most common exception types
    - Services with highest exception rates
    - Exception message patterns

    Args:
        dataset_id: BigQuery dataset ID
        table_name: Table name containing OTEL traces
        time_window_hours: How many hours back to analyze
        service_name: Optional filter for specific service
        group_by: How to group exceptions (exception_type, service_name, span_name)

    Returns:
        JSON with SQL query to analyze exception patterns.
    """
    where_conditions = [
        f"start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {time_window_hours} HOUR)",
        "ARRAY_LENGTH(events) > 0",
    ]

    if service_name:
        where_conditions.append(
            f"JSON_EXTRACT_SCALAR(resource.attributes, '$.service.name') = '{service_name}'"
        )

    where_clause = " AND ".join(where_conditions)

    # Map group_by to field
    if group_by == "exception_type":
        group_field = "JSON_EXTRACT_SCALAR(event.attributes, '$.exception.type')"
    elif group_by == "service_name":
        group_field = "JSON_EXTRACT_SCALAR(resource.attributes, '$.service.name')"
    elif group_by == "span_name":
        group_field = "name"
    else:
        group_field = "JSON_EXTRACT_SCALAR(event.attributes, '$.exception.type')"

    query = f"""
WITH exception_events AS (
  SELECT
    trace_id,
    span_id,
    name as span_name,
    JSON_EXTRACT_SCALAR(resource.attributes, '$.service.name') as service_name,
    JSON_EXTRACT_SCALAR(event.attributes, '$.exception.type') as exception_type,
    JSON_EXTRACT_SCALAR(event.attributes, '$.exception.message') as exception_message,
    event.time as event_time
  FROM `{dataset_id}.{table_name}`,
  UNNEST(events) as event
  WHERE {where_clause}
    AND event.name = 'exception'
)
SELECT
  {group_field} as {group_by},
  COUNT(*) as exception_count,
  COUNT(DISTINCT trace_id) as affected_traces,
  COUNT(DISTINCT service_name) as affected_services,
  ARRAY_AGG(DISTINCT exception_message IGNORE NULLS LIMIT 10) as sample_messages,
  MIN(event_time) as first_seen,
  MAX(event_time) as last_seen
FROM exception_events
GROUP BY {group_by}
ORDER BY exception_count DESC
LIMIT 50
"""

    return json.dumps(
        {
            "analysis_type": "exception_patterns",
            "sql_query": query.strip(),
            "description": f"Analyze exception patterns grouped by {group_by}",
            "next_steps": [
                "Execute this query using BigQuery MCP execute_sql tool",
                "Identify the most common exceptions",
                "Use find_exemplar_traces with error strategy for detailed analysis",
                "Check if exceptions correlate with specific time periods",
            ],
        }
    )


@adk_tool
def analyze_span_links(
    dataset_id: str,
    table_name: str = "_AllSpans",
    time_window_hours: int = 24,
    service_name: str | None = None,
    limit: int = 100,
) -> str:
    """
    Analyzes span links to understand causal relationships between traces.

    Links connect spans that are related but not in a parent-child relationship.
    Common use cases:
    - Batch processing (linking request to batch job)
    - Fan-out operations (linking parent to multiple async children)
    - Async messaging (linking producer to consumer)

    Args:
        dataset_id: BigQuery dataset ID
        table_name: Table name containing OTEL traces
        time_window_hours: How many hours back to analyze
        service_name: Optional filter for specific service
        limit: Maximum number of results

    Returns:
        JSON with SQL query to analyze span links.
    """
    where_conditions = [
        f"start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {time_window_hours} HOUR)",
        "ARRAY_LENGTH(links) > 0",
    ]

    if service_name:
        where_conditions.append(
            f"JSON_EXTRACT_SCALAR(resource.attributes, '$.service.name') = '{service_name}'"
        )

    where_clause = " AND ".join(where_conditions)

    query = f"""
SELECT
  trace_id as source_trace_id,
  span_id as source_span_id,
  name as source_span_name,
  JSON_EXTRACT_SCALAR(resource.attributes, '$.service.name') as source_service,
  link.trace_id as linked_trace_id,
  link.span_id as linked_span_id,
  JSON_EXTRACT_SCALAR(link.attributes, '$.link.type') as link_type,
  JSON_EXTRACT_SCALAR(link.attributes, '$.link.reason') as link_reason,
  link.attributes as link_attributes,
  start_time as source_start_time,
  ARRAY_LENGTH(links) as total_links
FROM `{dataset_id}.{table_name}`,
UNNEST(links) as link
WHERE {where_clause}
ORDER BY start_time DESC
LIMIT {limit}
"""

    return json.dumps(
        {
            "analysis_type": "span_links",
            "sql_query": query.strip(),
            "description": f"Analyze span links for last {time_window_hours}h",
            "next_steps": [
                "Execute this query using BigQuery MCP execute_sql tool",
                "Identify patterns in link types (batch, async, fan-out)",
                "Use fetch_trace to get details of linked traces",
                "Investigate if linked traces show correlated performance issues",
            ],
        }
    )


@adk_tool
def analyze_link_patterns(
    dataset_id: str,
    table_name: str = "_AllSpans",
    time_window_hours: int = 24,
    service_name: str | None = None,
) -> str:
    """
    Analyzes patterns in span links to understand cross-trace relationships.

    Aggregates link data to show:
    - Services with most cross-trace links
    - Common link patterns
    - Link density by service

    Args:
        dataset_id: BigQuery dataset ID
        table_name: Table name containing OTEL traces
        time_window_hours: How many hours back to analyze
        service_name: Optional filter for specific service

    Returns:
        JSON with SQL query to analyze link patterns.
    """
    where_conditions = [
        f"start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {time_window_hours} HOUR)",
        "ARRAY_LENGTH(links) > 0",
    ]

    if service_name:
        where_conditions.append(
            f"JSON_EXTRACT_SCALAR(resource.attributes, '$.service.name') = '{service_name}'"
        )

    where_clause = " AND ".join(where_conditions)

    query = f"""
SELECT
  JSON_EXTRACT_SCALAR(resource.attributes, '$.service.name') as service_name,
  COUNT(*) as spans_with_links,
  SUM(ARRAY_LENGTH(links)) as total_links,
  ROUND(SUM(ARRAY_LENGTH(links)) / COUNT(*), 2) as avg_links_per_span,
  COUNT(DISTINCT trace_id) as traces_with_links,
  APPROX_TOP_COUNT(name, 5) as top_operations_with_links
FROM `{dataset_id}.{table_name}`
WHERE {where_clause}
GROUP BY service_name
ORDER BY total_links DESC
LIMIT 50
"""

    return json.dumps(
        {
            "analysis_type": "link_patterns",
            "sql_query": query.strip(),
            "description": f"Analyze link patterns for last {time_window_hours}h",
            "next_steps": [
                "Execute this query using BigQuery MCP execute_sql tool",
                "Identify services with high link density",
                "Use analyze_span_links to get detailed link information",
                "Investigate if link patterns correlate with performance issues",
            ],
        }
    )


@adk_tool
def analyze_instrumentation_libraries(
    dataset_id: str,
    table_name: str = "_AllSpans",
    time_window_hours: int = 24,
    service_name: str | None = None,
) -> str:
    """
    Analyzes instrumentation libraries used across services.

    Tracks which OpenTelemetry instrumentation libraries are in use:
    - Library names and versions
    - Span counts per library
    - Service adoption of instrumentation

    Useful for:
    - Auditing instrumentation coverage
    - Identifying outdated library versions
    - Tracking instrumentation adoption

    Args:
        dataset_id: BigQuery dataset ID
        table_name: Table name containing OTEL traces
        time_window_hours: How many hours back to analyze
        service_name: Optional filter for specific service

    Returns:
        JSON with SQL query to analyze instrumentation libraries.
    """
    where_conditions = [
        f"start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {time_window_hours} HOUR)"
    ]

    if service_name:
        where_conditions.append(
            f"JSON_EXTRACT_SCALAR(resource.attributes, '$.service.name') = '{service_name}'"
        )

    where_clause = " AND ".join(where_conditions)

    query = f"""
SELECT
  instrumentation_scope.name as library_name,
  instrumentation_scope.version as library_version,
  instrumentation_scope.schema_url as schema_url,
  COUNT(*) as span_count,
  COUNT(DISTINCT JSON_EXTRACT_SCALAR(resource.attributes, '$.service.name')) as service_count,
  COUNT(DISTINCT trace_id) as trace_count,
  ARRAY_AGG(DISTINCT JSON_EXTRACT_SCALAR(resource.attributes, '$.service.name') IGNORE NULLS LIMIT 20) as services_using,
  MIN(start_time) as first_seen,
  MAX(start_time) as last_seen
FROM `{dataset_id}.{table_name}`
WHERE {where_clause}
  AND instrumentation_scope.name IS NOT NULL
GROUP BY library_name, library_version, schema_url
ORDER BY span_count DESC
LIMIT 50
"""

    return json.dumps(
        {
            "analysis_type": "instrumentation_libraries",
            "sql_query": query.strip(),
            "description": f"Analyze instrumentation libraries for last {time_window_hours}h",
            "next_steps": [
                "Execute this query using BigQuery MCP execute_sql tool",
                "Review library versions for consistency",
                "Identify services missing instrumentation",
                "Check for outdated library versions that need updates",
            ],
        }
    )


@adk_tool
def analyze_http_attributes(
    dataset_id: str,
    table_name: str = "_AllSpans",
    time_window_hours: int = 24,
    service_name: str | None = None,
    min_request_count: int = 10,
) -> str:
    """
    Analyzes HTTP-specific attributes from span data.

    Extracts and analyzes HTTP semantic conventions:
    - HTTP methods (GET, POST, etc.)
    - HTTP status codes
    - HTTP endpoints/targets
    - User agents
    - Request/response sizes

    Args:
        dataset_id: BigQuery dataset ID
        table_name: Table name containing OTEL traces
        time_window_hours: How many hours back to analyze
        service_name: Optional filter for specific service
        min_request_count: Minimum requests to include in results

    Returns:
        JSON with SQL query to analyze HTTP attributes.
    """
    where_conditions = [
        f"start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {time_window_hours} HOUR)",
        "kind = 2",  # SERVER spans
        "JSON_EXTRACT_SCALAR(attributes, '$.http.method') IS NOT NULL",
    ]

    if service_name:
        where_conditions.append(
            f"JSON_EXTRACT_SCALAR(resource.attributes, '$.service.name') = '{service_name}'"
        )

    where_clause = " AND ".join(where_conditions)

    query = f"""
SELECT
  JSON_EXTRACT_SCALAR(resource.attributes, '$.service.name') as service_name,
  JSON_EXTRACT_SCALAR(attributes, '$.http.method') as http_method,
  JSON_EXTRACT_SCALAR(attributes, '$.http.target') as http_target,
  JSON_EXTRACT_SCALAR(attributes, '$.http.status_code') as http_status_code,
  COUNT(*) as request_count,
  COUNTIF(status.code = 2) as error_count,
  ROUND(COUNTIF(status.code = 2) / COUNT(*) * 100, 2) as error_rate_pct,
  ROUND(APPROX_QUANTILES(duration_nano / 1000000, 100)[OFFSET(50)], 2) as p50_ms,
  ROUND(APPROX_QUANTILES(duration_nano / 1000000, 100)[OFFSET(95)], 2) as p95_ms,
  ROUND(APPROX_QUANTILES(duration_nano / 1000000, 100)[OFFSET(99)], 2) as p99_ms,
  ROUND(AVG(CAST(JSON_EXTRACT_SCALAR(attributes, '$.http.request_content_length') AS INT64)), 0) as avg_request_size_bytes,
  ROUND(AVG(CAST(JSON_EXTRACT_SCALAR(attributes, '$.http.response_content_length') AS INT64)), 0) as avg_response_size_bytes
FROM `{dataset_id}.{table_name}`
WHERE {where_clause}
GROUP BY service_name, http_method, http_target, http_status_code
HAVING request_count >= {min_request_count}
ORDER BY error_rate_pct DESC, p99_ms DESC
LIMIT 100
"""

    return json.dumps(
        {
            "analysis_type": "http_attributes",
            "sql_query": query.strip(),
            "description": f"Analyze HTTP attributes for last {time_window_hours}h",
            "next_steps": [
                "Execute this query using BigQuery MCP execute_sql tool",
                "Identify endpoints with high error rates or latency",
                "Check for unusual request/response sizes",
                "Use find_exemplar_traces for problematic endpoints",
            ],
        }
    )


@adk_tool
def analyze_database_operations(
    dataset_id: str,
    table_name: str = "_AllSpans",
    time_window_hours: int = 24,
    service_name: str | None = None,
    db_system: str | None = None,
) -> str:
    """
    Analyzes database operation spans using semantic conventions.

    Extracts database-specific attributes:
    - Database system (mysql, postgresql, mongodb, etc.)
    - Database operations (SELECT, INSERT, UPDATE, DELETE)
    - Database names
    - Query patterns

    Args:
        dataset_id: BigQuery dataset ID
        table_name: Table name containing OTEL traces
        time_window_hours: How many hours back to analyze
        service_name: Optional filter for specific service
        db_system: Optional filter for database system (mysql, postgresql, etc.)

    Returns:
        JSON with SQL query to analyze database operations.
    """
    where_conditions = [
        f"start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {time_window_hours} HOUR)",
        "kind = 3",  # CLIENT spans
        "JSON_EXTRACT_SCALAR(attributes, '$.db.system') IS NOT NULL",
    ]

    if service_name:
        where_conditions.append(
            f"JSON_EXTRACT_SCALAR(resource.attributes, '$.service.name') = '{service_name}'"
        )

    if db_system:
        where_conditions.append(
            f"JSON_EXTRACT_SCALAR(attributes, '$.db.system') = '{db_system}'"
        )

    where_clause = " AND ".join(where_conditions)

    query = f"""
SELECT
  JSON_EXTRACT_SCALAR(resource.attributes, '$.service.name') as service_name,
  JSON_EXTRACT_SCALAR(attributes, '$.db.system') as db_system,
  JSON_EXTRACT_SCALAR(attributes, '$.db.name') as db_name,
  JSON_EXTRACT_SCALAR(attributes, '$.db.operation') as db_operation,
  COUNT(*) as operation_count,
  COUNTIF(status.code = 2) as error_count,
  ROUND(COUNTIF(status.code = 2) / COUNT(*) * 100, 2) as error_rate_pct,
  ROUND(APPROX_QUANTILES(duration_nano / 1000000, 100)[OFFSET(50)], 2) as p50_ms,
  ROUND(APPROX_QUANTILES(duration_nano / 1000000, 100)[OFFSET(95)], 2) as p95_ms,
  ROUND(APPROX_QUANTILES(duration_nano / 1000000, 100)[OFFSET(99)], 2) as p99_ms,
  APPROX_TOP_COUNT(SUBSTR(JSON_EXTRACT_SCALAR(attributes, '$.db.statement'), 1, 100), 3) as sample_statements
FROM `{dataset_id}.{table_name}`
WHERE {where_clause}
GROUP BY service_name, db_system, db_name, db_operation
ORDER BY operation_count DESC
LIMIT 100
"""

    return json.dumps(
        {
            "analysis_type": "database_operations",
            "sql_query": query.strip(),
            "description": f"Analyze database operations for last {time_window_hours}h",
            "next_steps": [
                "Execute this query using BigQuery MCP execute_sql tool",
                "Identify slow or error-prone database operations",
                "Review sample statements for query optimization opportunities",
                "Use find_exemplar_traces for detailed query analysis",
            ],
        }
    )
