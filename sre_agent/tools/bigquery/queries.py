"""Pre-defined BigQuery SQL queries for SRE Agent analysis."""


def get_aggregate_metrics_query(table_name: str, start_time: str, end_time: str) -> str:
    """Get query for service-level aggregate metrics.

    Args:
        table_name: Fully qualified table name (e.g. proj.dataset._AllSpans).
        start_time: ISO timestamp.
        end_time: ISO timestamp.
    """
    # Assuming attributes.key='service.name' or similar OTel convention.
    # We unnest attributes to find service name.

    return f"""
    WITH Spans AS (
      SELECT
        span_id,
        trace_id,
        parent_span_id,
        start_time,
        end_time,
        TIMESTAMP_DIFF(end_time, start_time, MILLISECOND) as duration_ms,
        (SELECT value.string_value FROM UNNEST(attributes) WHERE key = 'service.name') as service_name,
        (SELECT value.int_value FROM UNNEST(status) WHERE key = 'code') as status_code # Check OTel status schema.  Actually OTel status is often a struct.
      FROM `{table_name}`
      WHERE start_time BETWEEN TIMESTAMP('{start_time}') AND TIMESTAMP('{end_time}')
    )
    SELECT
      service_name,
      COUNT(*) as request_count,
      AVG(duration_ms) as avg_latency,
      APPROX_QUANTILES(duration_ms, 100)[OFFSET(50)] as p50_latency,
      APPROX_QUANTILES(duration_ms, 100)[OFFSET(95)] as p95_latency,
      APPROX_QUANTILES(duration_ms, 100)[OFFSET(99)] as p99_latency,
      COUNTIF(status_code = 2) as error_count # OTel status: 0=Unset, 1=Ok, 2=Error
    FROM Spans
    WHERE service_name IS NOT NULL
    GROUP BY service_name
    ORDER BY request_count DESC
    """


def get_aggregate_eval_metrics_query(
    table_name: str,
    start_time: str,
    end_time: str,
    service_name: str | None = None,
) -> str:
    """Build a BigQuery SQL query for aggregate evaluation metrics over time.

    Queries the OTel span events table for 'gen_ai.evaluation.result' events,
    extracts metric name and score, groups by hourly time bucket, and
    calculates the average score per metric.

    Args:
        table_name: Fully qualified table name (e.g. proj.dataset._AllSpans).
        start_time: ISO timestamp for the start of the time range.
        end_time: ISO timestamp for the end of the time range.
        service_name: Optional service/agent name to filter on.

    Returns:
        A BigQuery SQL string.
    """
    service_filter = ""
    if service_name:
        service_filter = (
            "AND JSON_VALUE(s.resource.attributes, '$.\"service.name\"') "
            f"= '{service_name}'"
        )

    return f"""
    WITH EvalEvents AS (
      SELECT
        TIMESTAMP_TRUNC(s.start_time, HOUR) AS time_bucket,
        evt.attributes AS evt_attrs
      FROM `{table_name}` AS s,
        UNNEST(s.events) AS evt
      WHERE
        s.start_time BETWEEN TIMESTAMP('{start_time}') AND TIMESTAMP('{end_time}')
        AND evt.name = 'gen_ai.evaluation.result'
        {service_filter}
    )
    SELECT
      time_bucket,
      JSON_VALUE(evt_attrs, '$."gen_ai.evaluation.metric.name"') AS metric_name,
      AVG(CAST(JSON_VALUE(evt_attrs, '$."gen_ai.evaluation.score"') AS FLOAT64)) AS avg_score,
      COUNT(*) AS sample_count
    FROM EvalEvents
    WHERE JSON_VALUE(evt_attrs, '$."gen_ai.evaluation.metric.name"') IS NOT NULL
    GROUP BY time_bucket, metric_name
    ORDER BY time_bucket ASC, metric_name ASC
    """


def get_baseline_traces_query(
    table_name: str, service_name: str, start_time: str, end_time: str, limit: int = 10
) -> str:
    """Get baseline (p50) traces for a service."""
    return f"""
    WITH Spans AS (
      SELECT
        trace_id,
        TIMESTAMP_DIFF(end_time, start_time, MILLISECOND) as duration_ms,
        (SELECT value.string_value FROM UNNEST(attributes) WHERE key = 'service.name') as service_name
      FROM `{table_name}`
      WHERE start_time BETWEEN TIMESTAMP('{start_time}') AND TIMESTAMP('{end_time}')
      AND parent_span_id IS NULL -- Only root spans define trace duration typically
    )
    SELECT trace_id
    FROM Spans
    WHERE service_name = '{service_name}'
    -- Filter for traces near p50 (naive approach: order by ABS(duration - p50))
    QUALIFY ROW_NUMBER() OVER (ORDER BY ABS(duration_ms - (SELECT PERCENTILE_CONT(duration_ms, 0.5) OVER()))) <= {limit}
    """


def get_anomaly_traces_query(
    table_name: str, service_name: str, start_time: str, end_time: str, limit: int = 10
) -> str:
    """Get anomaly (p99 or error) traces for a service."""
    return f"""
    WITH Spans AS (
      SELECT
        trace_id,
        TIMESTAMP_DIFF(end_time, start_time, MILLISECOND) as duration_ms,
        (SELECT value.string_value FROM UNNEST(attributes) WHERE key = 'service.name') as service_name,
        (SELECT value.int_value FROM UNNEST(status) WHERE key = 'code') as status_code
      FROM `{table_name}`
      WHERE start_time BETWEEN TIMESTAMP('{start_time}') AND TIMESTAMP('{end_time}')
      AND parent_span_id IS NULL
    )
    SELECT trace_id
    FROM Spans
    WHERE service_name = '{service_name}'
    AND (
        duration_ms >= (SELECT PERCENTILE_CONT(duration_ms, 0.99) OVER())
        OR status_code = 2
    )
    LIMIT {limit}
    """
