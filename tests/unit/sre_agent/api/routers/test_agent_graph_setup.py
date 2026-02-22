from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from sre_agent.api.app import create_app


@pytest.fixture
def app() -> FastAPI:
    _app = create_app()
    return _app


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.mark.anyio
async def test_check_observability_bucket(client: AsyncClient):
    with patch(
        "sre_agent.api.routers.agent_graph_setup.httpx.AsyncClient"
    ) as mock_client_class:
        mock_instance = mock_client_class.return_value.__aenter__.return_value
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "observabilityBuckets": [
                {
                    "loggingSink": {
                        "destination": "storage.googleapis.com/test-bucket"
                    },
                    "name": "projects/123/buckets/test-bucket",
                }
            ]
        }
        mock_instance.get = AsyncMock(return_value=mock_response)

        # We need to mock auth
        with patch(
            "sre_agent.api.routers.agent_graph_setup._get_auth_token",
            return_value="dummy",
        ):
            response = await client.get(
                "/api/v1/graph/setup/check_bucket",
                params={"project_id": "test-project"},
            )
            assert response.status_code == 200
            assert response.json()["exists"]


@pytest.mark.anyio
async def test_check_observability_bucket_not_found(client: AsyncClient):
    with patch(
        "sre_agent.api.routers.agent_graph_setup.httpx.AsyncClient"
    ) as mock_client_class:
        mock_instance = mock_client_class.return_value.__aenter__.return_value
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        # Simulate HTTTPX HTTPStatusError for 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )

        mock_instance.get = AsyncMock(return_value=mock_response)
        with patch(
            "sre_agent.api.routers.agent_graph_setup._get_auth_token",
            return_value="dummy",
        ):
            response = await client.get(
                "/api/v1/graph/setup/check_bucket",
                params={"project_id": "test-project"},
            )
            assert response.status_code == 404
            assert "Failed to check Observability Bucket" in response.json()["detail"]


@pytest.mark.anyio
async def test_link_dataset(client: AsyncClient):
    with (
        patch("sre_agent.api.routers.agent_graph_setup.bigquery.Client") as mock_bq,
        patch(
            "sre_agent.api.routers.agent_graph_setup.httpx.AsyncClient"
        ) as mock_client_class,
        patch(
            "sre_agent.api.routers.agent_graph_setup._get_auth_token",
            return_value="dummy",
        ),
    ):
        mock_instance = mock_client_class.return_value.__aenter__.return_value
        # Mock BigQuery Client
        mock_bq_instance = MagicMock()
        mock_bq.return_value = mock_bq_instance

        # Mock Observation API response
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "operations/test-op",
            "metadata": {"state": "RUNNING"},
        }
        mock_instance.post = AsyncMock(return_value=mock_response)

        response = await client.post(
            "/api/v1/graph/setup/link_dataset",
            json={
                "project_id": "test-project",
                "bucket_id": "test-bucket",
                "dataset_id": "test-dataset",
            },
        )

        assert response.status_code == 200
        assert response.json()["status"] == "creating"
        assert response.json()["operation"]["name"] == "operations/test-op"


@pytest.mark.anyio
async def test_link_dataset_already_exists(client: AsyncClient):
    with (
        patch("sre_agent.api.routers.agent_graph_setup.bigquery.Client") as mock_bq,
        patch(
            "sre_agent.api.routers.agent_graph_setup.httpx.AsyncClient"
        ) as mock_client_class,
        patch(
            "sre_agent.api.routers.agent_graph_setup._get_auth_token",
            return_value="dummy",
        ),
    ):
        mock_instance = mock_client_class.return_value.__aenter__.return_value
        mock_bq_instance = MagicMock()
        mock_bq.return_value = mock_bq_instance

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 409  # Already exists
        mock_response.text = "Conflict"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Conflict", request=MagicMock(), response=mock_response
        )
        mock_instance.post = AsyncMock(return_value=mock_response)

        response = await client.post(
            "/api/v1/graph/setup/link_dataset",
            json={
                "project_id": "test-project",
                "bucket_id": "test-bucket",
                "dataset_id": "test-dataset",
            },
        )

        assert response.status_code == 409
        assert "Conflict" in response.json()["detail"]


@pytest.mark.anyio
async def test_lro_status(client: AsyncClient):
    with (
        patch(
            "sre_agent.api.routers.agent_graph_setup.httpx.AsyncClient"
        ) as mock_client_class,
        patch(
            "sre_agent.api.routers.agent_graph_setup._get_auth_token",
            return_value="dummy",
        ),
    ):
        mock_instance = mock_client_class.return_value.__aenter__.return_value
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"done": True, "response": {}}
        mock_instance.get = AsyncMock(return_value=mock_response)

        response = await client.get(
            "/api/v1/graph/setup/lro_status",
            params={
                "project_id": "test_project",
                "operation_name": "projects/test_project/operations/123",
            },
        )
        assert response.status_code == 200
        assert response.json()["done"]


@pytest.mark.anyio
async def test_execute_schema_step(client: AsyncClient):
    with patch("sre_agent.api.routers.agent_graph_setup.bigquery.Client") as mock_bq:
        mock_bq_instance = MagicMock()
        mock_job = MagicMock()
        mock_job.result = MagicMock()
        mock_bq_instance.query.return_value = mock_job
        mock_bq.return_value = mock_bq_instance

        response = await client.post(
            "/api/v1/graph/setup/schema/nodes",
            json={
                "project_id": "test-project",
                "trace_dataset": "traces",
                "graph_dataset": "agent_graph",
                "service_name": "test-service",
            },
        )

        assert response.status_code == 200
        assert response.json()["status"] == "success"
        mock_bq_instance.query.assert_called()
