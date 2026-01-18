"""Tests for GCP projects client."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sre_agent.tools.clients.gcp_projects import list_gcp_projects


@pytest.mark.asyncio
async def test_list_gcp_projects_success():
    """Test successful listing of GCP projects."""
    mock_credentials = MagicMock()
    mock_credentials.token = "test-token"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "projects": [
            {"projectId": "project-1", "name": "Project One"},
            {"projectId": "project-2", "name": "Project Two"},
        ]
    }

    with (
        patch("sre_agent.tools.clients.gcp_projects.get_current_credentials", return_value=(mock_credentials, "test-project")),
        patch("httpx.AsyncClient") as mock_client_class,
    ):
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        result = await list_gcp_projects()

        assert result == {
            "projects": [
                {"project_id": "project-1", "display_name": "Project One"},
                {"project_id": "project-2", "display_name": "Project Two"},
            ]
        }

        mock_client.get.assert_called_once_with(
            "https://cloudresourcemanager.googleapis.com/v1/projects",
            headers={"Authorization": "Bearer test-token"},
        )


@pytest.mark.asyncio
async def test_list_gcp_projects_no_token_refresh():
    """Test listing projects when token exists."""
    mock_credentials = MagicMock()
    mock_credentials.token = "existing-token"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"projects": []}

    with (
        patch("sre_agent.tools.clients.gcp_projects.get_current_credentials", return_value=(mock_credentials, "test-project")),
        patch("httpx.AsyncClient") as mock_client_class,
    ):
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        result = await list_gcp_projects()

        assert result == {"projects": []}

        # Should not attempt refresh since token exists
        mock_credentials.refresh.assert_not_called()


@pytest.mark.asyncio
async def test_list_gcp_projects_refresh_token():
    """Test listing projects with token refresh."""
    mock_credentials = MagicMock()
    mock_credentials.token = None

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"projects": []}

    with (
        patch("sre_agent.tools.clients.gcp_projects.get_current_credentials", return_value=(mock_credentials, "test-project")),
        patch("httpx.AsyncClient") as mock_client_class,
        patch("google.auth.transport.requests.Request"),
    ):
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        result = await list_gcp_projects()

        assert result == {"projects": []}

        # Should attempt refresh
        mock_credentials.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_list_gcp_projects_api_error():
    """Test handling of API errors."""
    mock_credentials = MagicMock()
    mock_credentials.token = "test-token"

    mock_response = MagicMock()
    mock_response.status_code = 403
    mock_response.text = "Forbidden"

    with (
        patch("sre_agent.tools.clients.gcp_projects.get_current_credentials", return_value=(mock_credentials, "test-project")),
        patch("httpx.AsyncClient") as mock_client_class,
    ):
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        result = await list_gcp_projects()

        assert result == {"projects": [], "error": "API error: 403"}


@pytest.mark.asyncio
async def test_list_gcp_projects_exception():
    """Test handling of exceptions."""
    with patch("sre_agent.tools.clients.gcp_projects.get_current_credentials", side_effect=Exception("Auth failed")):
        result = await list_gcp_projects()

        assert result == {"projects": [], "error": "Auth failed"}