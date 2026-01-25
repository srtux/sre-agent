"""Unit tests for the permissions router."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from server import app

client = TestClient(app)


@pytest.fixture
def mock_creds():
    with patch("google.auth.default") as mock:
        creds = MagicMock()
        creds.service_account_email = "test-sa@example.com"
        mock.return_value = (creds, "test-proj")
        yield creds


@pytest.mark.asyncio
async def test_get_permissions_info(mock_creds):
    with patch("google.auth.transport.requests.Request"):
        response = client.get("/api/permissions/info")
        assert response.status_code == 200
        data = response.json()
        assert data["service_account"] == "test-sa@example.com"
        assert "roles" in data
        assert data["project_id"] == "test-proj"


@pytest.mark.asyncio
async def test_get_permissions_info_error():
    with patch("google.auth.default", side_effect=Exception("Auth error")):
        response = client.get("/api/permissions/info")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "Auth error" in data["error"]


@pytest.mark.asyncio
async def test_get_gcloud_commands(mock_creds):
    with patch("google.auth.transport.requests.Request"):
        response = client.get("/api/permissions/gcloud?project_id=user-proj")
        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == "user-proj"
        assert len(data["commands"]) > 0
        assert "one_liner" in data


@pytest.mark.asyncio
async def test_check_permissions_ok(mock_creds):
    with patch("google.cloud.trace_v2.TraceServiceClient") as mock_trace:
        with patch("google.cloud.logging.Client") as mock_logging:
            with patch(
                "google.cloud.monitoring_v3.MetricServiceClient"
            ) as mock_monitoring:
                # Mock successful list calls
                mock_trace.return_value.list_traces.return_value = []
                mock_logging.return_value.list_logs.return_value = []
                mock_monitoring.return_value.list_metric_descriptors.return_value = []

                response = client.get("/api/permissions/check/user-proj")
                assert response.status_code == 200
                data = response.json()
                assert data["all_ok"] is True
                assert data["results"]["cloudtrace.user"]["status"] == "ok"


@pytest.mark.asyncio
async def test_check_permissions_missing(mock_creds):
    with patch("google.cloud.trace_v2.TraceServiceClient") as mock_trace:
        with patch("google.cloud.logging.Client") as mock_logging:
            with patch(
                "google.cloud.monitoring_v3.MetricServiceClient"
            ) as mock_monitoring:
                # Mock permission denied
                mock_trace.return_value.list_traces.side_effect = Exception(
                    "PermissionDenied: 403"
                )
                mock_logging.return_value.list_logs.side_effect = Exception(
                    "403 Permission Denied"
                )
                mock_monitoring.return_value.list_metric_descriptors.side_effect = (
                    Exception("PermissionDenied")
                )

                response = client.get("/api/permissions/check/user-proj")
                assert response.status_code == 200
                data = response.json()
                assert data["all_ok"] is False
                assert data["results"]["cloudtrace.user"]["status"] == "missing"
