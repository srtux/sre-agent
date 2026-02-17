"""Tests for logs and traces query endpoint parameter handling.

Validates that:
- The logs query endpoint constructs time filters from `minutes_ago`.
- The traces query endpoint forwards `payload.limit` to `list_traces`.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from server import app
from sre_agent.schema import BaseToolResponse, ToolStatus

client = TestClient(app)


@pytest.fixture
def mock_log_entries():
    """Patch list_log_entries to return an empty success response."""
    with patch(
        "sre_agent.api.routers.tools.list_log_entries",
        new_callable=AsyncMock,
    ) as mock:
        mock.return_value = BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={"entries": []},
        )
        yield mock


@pytest.fixture
def mock_traces():
    """Patch list_traces and fetch_trace for traces query tests."""
    with (
        patch(
            "sre_agent.api.routers.tools.list_traces",
            new_callable=AsyncMock,
        ) as l_traces,
        patch(
            "sre_agent.api.routers.tools.fetch_trace",
            new_callable=AsyncMock,
        ) as f_trace,
    ):
        # Default: list_traces returns a list with one trace summary
        l_traces.return_value = BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=[
                {
                    "trace_id": "trace-abc123",
                    "spans": [
                        {
                            "span_id": "s1",
                            "name": "/api/v1/test",
                            "start_time": "2024-01-01T00:00:00Z",
                            "end_time": "2024-01-01T00:00:01Z",
                            "attributes": {},
                        }
                    ],
                }
            ],
        )
        # fetch_trace returns full trace details
        f_trace.return_value = BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result={
                "trace_id": "trace-abc123",
                "spans": [
                    {
                        "span_id": "s1",
                        "name": "/api/v1/test",
                        "start_time": "2024-01-01T00:00:00Z",
                        "end_time": "2024-01-01T00:00:01Z",
                        "attributes": {},
                    }
                ],
            },
        )
        yield {"list_traces": l_traces, "fetch_trace": f_trace}


# =============================================================================
# LOGS QUERY ENDPOINT: minutes_ago time filter construction
# =============================================================================


@pytest.mark.asyncio
async def test_query_logs_with_minutes_ago_constructs_time_filter(
    mock_log_entries,
) -> None:
    """When minutes_ago=15 is provided, a timestamp>= filter is constructed."""
    before = datetime.now(timezone.utc)

    payload = {"minutes_ago": 15, "project_id": "test-project"}
    response = client.post("/api/tools/logs/query", json=payload)

    after = datetime.now(timezone.utc)

    assert response.status_code == 200
    mock_log_entries.assert_awaited_once()

    call_kwargs = mock_log_entries.call_args.kwargs
    filter_str = call_kwargs["filter_str"]

    # The filter should contain a timestamp>= clause
    assert 'timestamp>="' in filter_str

    # Extract the timestamp from the filter and verify it's roughly correct
    # Filter format: timestamp>="2024-01-01T00:00:00+00:00"
    ts_start = filter_str.index('timestamp>="') + len('timestamp>="')
    ts_end = filter_str.index('"', ts_start)
    cutoff_str = filter_str[ts_start:ts_end]
    cutoff = datetime.fromisoformat(cutoff_str)

    # The cutoff should be approximately (now - 15 minutes)
    # Allow a small tolerance window for test execution time
    from datetime import timedelta

    expected_earliest = before - timedelta(minutes=15, seconds=5)
    expected_latest = after - timedelta(minutes=15) + timedelta(seconds=5)
    assert expected_earliest <= cutoff <= expected_latest


@pytest.mark.asyncio
async def test_query_logs_with_minutes_ago_and_existing_filter(
    mock_log_entries,
) -> None:
    """When both filter and minutes_ago are provided, they are ANDed together."""
    payload = {
        "filter": "severity>=ERROR",
        "minutes_ago": 30,
        "project_id": "test-project",
    }
    response = client.post("/api/tools/logs/query", json=payload)

    assert response.status_code == 200
    mock_log_entries.assert_awaited_once()

    call_kwargs = mock_log_entries.call_args.kwargs
    filter_str = call_kwargs["filter_str"]

    # Should contain the original filter AND the time filter
    assert filter_str.startswith("severity>=ERROR AND ")
    assert 'timestamp>="' in filter_str


@pytest.mark.asyncio
async def test_query_logs_without_minutes_ago_passes_filter_as_is(
    mock_log_entries,
) -> None:
    """When minutes_ago is None, no time filter is appended."""
    payload = {
        "filter": "severity>=WARNING",
        "project_id": "test-project",
        # minutes_ago is not provided (defaults to None)
    }
    response = client.post("/api/tools/logs/query", json=payload)

    assert response.status_code == 200
    mock_log_entries.assert_awaited_once()

    call_kwargs = mock_log_entries.call_args.kwargs
    filter_str = call_kwargs["filter_str"]

    # Filter should be passed through unchanged, no timestamp clause
    assert filter_str == "severity>=WARNING"
    assert "timestamp>=" not in filter_str


@pytest.mark.asyncio
async def test_query_logs_empty_filter_with_minutes_ago(
    mock_log_entries,
) -> None:
    """When filter is empty string and minutes_ago is set, time filter is the only filter."""
    payload = {
        "filter": "",
        "minutes_ago": 60,
        "project_id": "test-project",
    }
    response = client.post("/api/tools/logs/query", json=payload)

    assert response.status_code == 200
    mock_log_entries.assert_awaited_once()

    call_kwargs = mock_log_entries.call_args.kwargs
    filter_str = call_kwargs["filter_str"]

    # Should contain only the time filter, not "AND"
    assert 'timestamp>="' in filter_str
    # Should NOT be prefixed with "AND" since the original filter was empty
    assert not filter_str.startswith("AND")
    assert not filter_str.startswith(" AND")


# =============================================================================
# TRACES QUERY ENDPOINT: payload.limit forwarding
# =============================================================================


@pytest.mark.asyncio
async def test_query_traces_uses_payload_limit(mock_traces) -> None:
    """When limit=20 is passed, it is forwarded to list_traces."""
    payload = {
        "filter": "RootSpan:/api/v1",
        "minutes_ago": 60,
        "project_id": "test-project",
        "limit": 20,
    }
    response = client.post("/api/tools/traces/query", json=payload)

    assert response.status_code == 200
    mock_traces["list_traces"].assert_awaited_once()

    call_kwargs = mock_traces["list_traces"].call_args.kwargs
    assert call_kwargs["limit"] == 20


@pytest.mark.asyncio
async def test_query_traces_default_limit(mock_traces) -> None:
    """When limit is not provided, the default of 10 is used."""
    payload = {
        "filter": "",
        "minutes_ago": 60,
        "project_id": "test-project",
        # limit not specified — should default to 10
    }
    response = client.post("/api/tools/traces/query", json=payload)

    assert response.status_code == 200
    mock_traces["list_traces"].assert_awaited_once()

    call_kwargs = mock_traces["list_traces"].call_args.kwargs
    assert call_kwargs["limit"] == 10
