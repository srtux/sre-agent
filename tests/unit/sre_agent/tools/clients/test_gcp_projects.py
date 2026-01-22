"""Tests for GCP projects client."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sre_agent.tools.clients.gcp_projects import list_gcp_projects


@pytest.mark.asyncio
async def test_list_gcp_projects_success():
    """Test successful listing of GCP projects (V3 Search)."""
    mock_credentials = MagicMock()
    mock_credentials.token = "test-token"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "projects": [
            {"projectId": "project-1", "displayName": "Project One"},
            {"projectId": "project-2", "displayName": "Project Two"},
        ]
    }

    with (
        patch(
            "sre_agent.tools.clients.gcp_projects.get_credentials_from_tool_context",
            return_value=mock_credentials,
        ),
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
            "https://cloudresourcemanager.googleapis.com/v3/projects:search",
            headers={"Authorization": "Bearer test-token"},
            params={"pageSize": 50},
        )


@pytest.mark.asyncio
async def test_list_gcp_projects_with_query():
    """Test searching projects with a query."""
    mock_credentials = MagicMock()
    mock_credentials.token = "test-token"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "projects": [
            {"projectId": "test-project", "displayName": "Test Project"},
        ]
    }

    with (
        patch(
            "sre_agent.tools.clients.gcp_projects.get_credentials_from_tool_context",
            return_value=mock_credentials,
        ),
        patch("httpx.AsyncClient") as mock_client_class,
    ):
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        # Call with query
        result = await list_gcp_projects(query="test")

        assert result["projects"][0]["project_id"] == "test-project"

        # Verify query parameter construction
        call_args = mock_client.get.call_args
        assert call_args is not None
        _, kwargs = call_args

        assert kwargs["params"]["pageSize"] == 50
        assert 'projectId:test* OR displayName:"test*"' in kwargs["params"]["query"]


@pytest.mark.asyncio
async def test_list_gcp_projects_json_error():
    """Test handling of invalid JSON response."""
    mock_credentials = MagicMock()
    mock_credentials.token = "test-token"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "Invalid JSON"
    mock_response.json.side_effect = Exception("JSON Decode Error")

    with (
        patch(
            "sre_agent.tools.clients.gcp_projects.get_credentials_from_tool_context",
            return_value=mock_credentials,
        ),
        patch("httpx.AsyncClient") as mock_client_class,
    ):
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client
        mock_client.get.return_value = mock_response

        result = await list_gcp_projects()

        assert result == {"projects": [], "error": "Invalid API response"}


@pytest.mark.asyncio
async def test_list_gcp_projects_no_token_refresh():
    """Test listing projects when token exists."""
    mock_credentials = MagicMock()
    mock_credentials.token = "existing-token"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"projects": []}

    with (
        patch(
            "sre_agent.tools.clients.gcp_projects.get_credentials_from_tool_context",
            return_value=mock_credentials,
        ),
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
        patch(
            "sre_agent.tools.clients.gcp_projects.get_credentials_from_tool_context",
            return_value=mock_credentials,
        ),
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
        patch(
            "sre_agent.tools.clients.gcp_projects.get_credentials_from_tool_context",
            return_value=mock_credentials,
        ),
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
    with patch(
        "sre_agent.tools.clients.gcp_projects.get_credentials_from_tool_context",
        side_effect=Exception("Auth failed"),
    ):
        result = await list_gcp_projects()

        assert result == {"projects": [], "error": "Auth failed"}
