"""Tests for BigQuery schema models."""

import pytest
from datetime import datetime

from sre_agent.tools.bigquery.schemas import BigQueryLogEntry, BigQuerySpan


def test_big_query_span_creation():
    """Test creating a BigQuerySpan instance."""
    span = BigQuerySpan(
        trace_id="abc123",
        span_id="span1",
        parent_span_id="parent1",
        name="test_span",
        kind="SPAN_KIND_INTERNAL",
        start_time=datetime(2023, 1, 1, 0, 0, 0),
        end_time=datetime(2023, 1, 1, 0, 0, 1),
        status={"code": 1, "message": ""},
        attributes={"key": "value"},
        resource={"service.name": "test-service"},
        links=[],
        events=[],
    )

    assert span.trace_id == "abc123"
    assert span.span_id == "span1"
    assert span.parent_span_id == "parent1"
    assert span.name == "test_span"
    assert span.status["code"] == 1
    assert span.attributes["key"] == "value"


def test_big_query_span_minimal():
    """Test BigQuerySpan with minimal required fields."""
    span = BigQuerySpan(
        trace_id="abc123",
        span_id="span1",
    )

    assert span.trace_id == "abc123"
    assert span.span_id == "span1"
    assert span.parent_span_id is None


def test_big_query_log_entry_creation():
    """Test creating a BigQueryLogEntry instance."""
    log_entry = BigQueryLogEntry(
        log_name="projects/test/logs/test",
        resource={"type": "gce_instance"},
        text_payload="Test log message",
        json_payload={"key": "value"},
        timestamp=datetime(2023, 1, 1, 0, 0, 0),
        severity="INFO",
        insert_id="insert123",
        labels={"env": "test"},
        trace="projects/test/traces/abc123",
        span_id="span1",
        trace_sampled=True,
    )

    assert log_entry.log_name == "projects/test/logs/test"
    assert log_entry.text_payload == "Test log message"
    assert log_entry.severity == "INFO"
    assert log_entry.trace == "projects/test/traces/abc123"
    assert log_entry.trace_sampled is True


def test_big_query_log_entry_minimal():
    """Test BigQueryLogEntry with minimal fields."""
    log_entry = BigQueryLogEntry()

    assert log_entry.log_name is None
    assert log_entry.text_payload is None
    assert log_entry.json_payload is None