"""Tests for BigQuery query functions."""

from sre_agent.tools.bigquery.queries import (
    get_aggregate_eval_metrics_query,
    get_aggregate_metrics_query,
    get_anomaly_traces_query,
    get_baseline_traces_query,
)


def test_get_aggregate_metrics_query():
    """Test aggregate metrics query generation."""
    query = get_aggregate_metrics_query(
        table_name="project.dataset.table",
        start_time="2023-01-01T00:00:00Z",
        end_time="2023-01-02T00:00:00Z",
    )

    assert isinstance(query, str)
    assert "SELECT" in query
    assert "project.dataset.table" in query
    assert "service_name" in query
    assert "avg_latency" in query
    assert "p50_latency" in query
    assert "error_count" in query


def test_get_baseline_traces_query():
    """Test baseline traces query generation."""
    query = get_baseline_traces_query(
        table_name="project.dataset.table",
        service_name="checkout-service",
        start_time="2023-01-01T00:00:00Z",
        end_time="2023-01-02T00:00:00Z",
        limit=5,
    )

    assert isinstance(query, str)
    assert "checkout-service" in query
    assert "PERCENTILE_CONT" in query
    assert "ORDER BY" in query
    assert "QUALIFY" in query


def test_get_anomaly_traces_query():
    """Test anomaly traces query generation."""
    query = get_anomaly_traces_query(
        table_name="project.dataset.table",
        service_name="checkout-service",
        start_time="2023-01-01T00:00:00Z",
        end_time="2023-01-02T00:00:00Z",
        limit=10,
    )

    assert isinstance(query, str)
    assert "checkout-service" in query
    assert "PERCENTILE_CONT(duration_ms, 0.99)" in query
    assert "status_code = 2" in query
    assert "LIMIT 10" in query


def test_get_aggregate_eval_metrics_query_basic():
    """Test eval metrics query includes expected clauses."""
    query = get_aggregate_eval_metrics_query(
        table_name="project.dataset._AllSpans",
        start_time="2026-02-22T00:00:00Z",
        end_time="2026-02-23T00:00:00Z",
    )

    assert isinstance(query, str)
    assert "project.dataset._AllSpans" in query
    assert "gen_ai.evaluation.result" in query
    assert "gen_ai.evaluation.metric.name" in query
    assert "gen_ai.evaluation.score" in query
    assert "TIMESTAMP_TRUNC" in query
    assert "AVG" in query
    assert "GROUP BY" in query
    assert "time_bucket" in query


def test_get_aggregate_eval_metrics_query_with_service_filter():
    """Test eval metrics query includes service name filter when provided."""
    query = get_aggregate_eval_metrics_query(
        table_name="project.dataset._AllSpans",
        start_time="2026-02-22T00:00:00Z",
        end_time="2026-02-23T00:00:00Z",
        service_name="my-agent",
    )

    assert "service.name" in query
    assert "my-agent" in query


def test_get_aggregate_eval_metrics_query_no_service_filter():
    """Test eval metrics query omits service filter when None."""
    query = get_aggregate_eval_metrics_query(
        table_name="project.dataset._AllSpans",
        start_time="2026-02-22T00:00:00Z",
        end_time="2026-02-23T00:00:00Z",
        service_name=None,
    )

    assert "service.name" not in query
