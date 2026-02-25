from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sre_agent.api.helpers.bq_discovery import (
    get_linked_log_dataset,
    get_linked_trace_dataset,
)


@pytest.fixture
def mock_httpx_client():
    with patch("httpx.AsyncClient") as mock:
        yield mock


@pytest.fixture
def mock_google_auth():
    with patch("sre_agent.api.helpers.bq_discovery.default") as mock_default:
        mock_creds = AsyncMock()
        mock_creds.token = "fake-token"
        # refresh is a sync method, so we must mock it as such to avoid "coroutine never awaited"
        mock_creds.refresh = MagicMock()
        mock_default.return_value = (mock_creds, "project-id")
        yield mock_default


@pytest.mark.asyncio
async def test_get_linked_log_dataset_success(mock_httpx_client, mock_google_auth):
    mock_client_instance = mock_httpx_client.return_value.__aenter__.return_value
    mock_client_instance.get.return_value = AsyncMock(
        status_code=200,
        json=lambda: {
            "links": [
                {
                    "bigqueryDataset": {
                        "datasetId": "bigquery.googleapis.com/projects/p/datasets/my_logs"
                    }
                }
            ]
        },
    )

    result = await get_linked_log_dataset("project-123")
    assert result == "my_logs"

    # Verify URL
    assert "logging.googleapis.com" in mock_client_instance.get.call_args[0][0]
    assert "_Default/links" in mock_client_instance.get.call_args[0][0]


@pytest.mark.asyncio
async def test_get_linked_trace_dataset_success(mock_httpx_client, mock_google_auth):
    mock_client_instance = mock_httpx_client.return_value.__aenter__.return_value

    # Configure responses for list buckets and then list links
    # 1. List buckets for global (empty)
    # 2. List buckets for us (contains one)
    # 3. List links for that one bucket

    responses = [
        AsyncMock(status_code=200, json=lambda: {"buckets": []}),  # global list
        AsyncMock(
            status_code=200,
            json=lambda: {
                "buckets": [{"name": "projects/p/locations/us/buckets/trace-bucket"}]
            },
        ),  # us list
        AsyncMock(
            status_code=200,
            json=lambda: {
                "links": [
                    {
                        "bigqueryDataset": {
                            "datasetId": "bigquery.googleapis.com/projects/p/datasets/trace_data"
                        }
                    }
                ]
            },
        ),  # link list
    ]
    mock_client_instance.get.side_effect = responses

    result = await get_linked_trace_dataset("project-123")
    assert result == "trace_data"

    # Verify we hit the observability API
    # Call 1: global buckets
    # Call 2: us buckets
    # Call 3: datasets/Spans/links
    assert mock_client_instance.get.call_count == 3
    assert (
        "observability.googleapis.com"
        in mock_client_instance.get.call_args_list[2][0][0]
    )
    assert (
        "trace-bucket/datasets/Spans/links"
        in mock_client_instance.get.call_args_list[2][0][0]
    )


@pytest.mark.asyncio
async def test_get_linked_trace_dataset_logging_scan(
    mock_httpx_client, mock_google_auth
):
    mock_client_instance = mock_httpx_client.return_value.__aenter__.return_value

    # 1. List buckets -> returns one
    # 2. Get links for that bucket -> returns a trace-like link
    responses = [
        AsyncMock(
            status_code=200,
            json=lambda: {
                "buckets": [
                    {"name": "projects/p/locations/global/buckets/trace-bucket"}
                ]
            },
        ),
        AsyncMock(
            status_code=200,
            json=lambda: {
                "links": [
                    {
                        "name": "projects/p/locations/global/buckets/trace-bucket/links/my-traces",
                        "bigqueryDataset": {
                            "datasetId": "bigquery.googleapis.com/projects/p/datasets/traces"
                        },
                    }
                ]
            },
        ),
    ]
    mock_client_instance.get.side_effect = responses

    result = await get_linked_trace_dataset("project-123")
    assert result == "traces"


@pytest.mark.asyncio
async def test_get_linked_trace_dataset_fallback(mock_httpx_client, mock_google_auth):
    mock_client_instance = mock_httpx_client.return_value.__aenter__.return_value
    # All API calls return empty
    mock_client_instance.get.return_value = AsyncMock(status_code=200, json=lambda: {})

    with patch("google.cloud.bigquery.Client") as mock_bq:
        mock_bq_instance = mock_bq.return_value
        # Mock traces._AllSpans working
        mock_bq_instance.get_table.return_value = AsyncMock()

        result = await get_linked_trace_dataset("project-123")
        assert result == "traces"
        mock_bq_instance.get_table.assert_called_with("project-123.traces._AllSpans")
