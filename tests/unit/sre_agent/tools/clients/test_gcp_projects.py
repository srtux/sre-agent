"""
Goal: Verify the GCP projects tool correctly lists and searches accessible projects.
Patterns: HTTPX Mocking, Credential Refresh Simulation, Project ID Parsing Logic.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sre_agent.tools.clients.gcp_projects import list_gcp_projects


@pytest.mark.asyncio
async def test_list_gcp_projects_success():
    mock_creds = MagicMock()
    mock_creds.token = "token123"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "projects": [
            {"projectId": "p1", "displayName": "Project 1"},
            {"name": "projects/p2", "displayName": "Project 2"},
        ]
    }

    with patch(
        "sre_agent.tools.clients.gcp_projects.get_credentials_from_tool_context",
        return_value=mock_creds,
    ):
        with patch(
            "httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await list_gcp_projects()
            assert len(result["projects"]) == 2
            assert result["projects"][0]["project_id"] == "p1"
            assert result["projects"][1]["project_id"] == "p2"


@pytest.mark.asyncio
async def test_list_gcp_projects_with_query():
    mock_creds = MagicMock()
    mock_creds.token = "token123"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"projects": []}

    with patch(
        "sre_agent.tools.clients.gcp_projects.get_credentials_from_tool_context",
        return_value=mock_creds,
    ):
        with patch(
            "httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await list_gcp_projects(query="test")
            assert "projects" in result


@pytest.mark.asyncio
async def test_list_gcp_projects_no_creds():
    with patch(
        "sre_agent.tools.clients.gcp_projects.get_credentials_from_tool_context",
        return_value=None,
    ):
        result = await list_gcp_projects()
        assert "error" in result
        assert "Authentication required" in result["error"]


@pytest.mark.asyncio
async def test_list_gcp_projects_refresh_fail():
    mock_creds = MagicMock()
    mock_creds.token = None  # Needs refresh
    mock_creds.refresh.side_effect = Exception("Refresh failed")

    with patch(
        "sre_agent.tools.clients.gcp_projects.get_credentials_from_tool_context",
        return_value=mock_creds,
    ):
        result = await list_gcp_projects()
        assert "error" in result
        # Should fall back to "No valid authentication token found" if token is still None after refresh
        assert "No valid authentication token found" in result["error"]


@pytest.mark.asyncio
async def test_list_gcp_projects_api_error():
    mock_creds = MagicMock()
    mock_creds.token = "token123"

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch(
        "sre_agent.tools.clients.gcp_projects.get_credentials_from_tool_context",
        return_value=mock_creds,
    ):
        with patch(
            "httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await list_gcp_projects()
            assert "error" in result
            assert "API error: 500" in result["error"]


@pytest.mark.asyncio
async def test_list_gcp_projects_invalid_json():
    mock_creds = MagicMock()
    mock_creds.token = "token123"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = Exception("not json")

    with patch(
        "sre_agent.tools.clients.gcp_projects.get_credentials_from_tool_context",
        return_value=mock_creds,
    ):
        with patch(
            "httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await list_gcp_projects()
            assert "error" in result
            assert "Invalid API response" in result["error"]
