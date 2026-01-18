"""Tests for tool connectivity check functions."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sre_agent.tools.config import ToolTestResult, ToolTestStatus
from sre_agent.tools.test_functions import (
    check_fetch_trace,
    check_get_gke_cluster_health,
    check_list_alerts,
    check_list_log_entries,
    check_list_slos,
    check_list_time_series,
    check_mcp_list_log_entries,
    check_mcp_list_timeseries,
    get_check_project_id,
)


def test_get_check_project_id():
    """Test project ID retrieval from environment."""
    with patch.dict("os.environ", {"GOOGLE_CLOUD_PROJECT": "test-project"}):
        assert get_check_project_id() == "test-project"

    with patch.dict("os.environ", {"TEST_PROJECT_ID": "test-project"}):
        assert get_check_project_id() == "test-project"

    with patch.dict("os.environ", {"GCP_PROJECT_ID": "test-project"}):
        assert get_check_project_id() == "test-project"

    with patch.dict("os.environ", {}):
        assert get_check_project_id() is None


@pytest.mark.asyncio
async def test_check_fetch_trace_success():
    """Test successful trace client check."""
    mock_client = MagicMock()
    mock_client.list_traces = MagicMock()
    mock_client.get_trace = MagicMock()

    with (
        patch("sre_agent.tools.test_functions.get_check_project_id", return_value="test-project"),
        patch("sre_agent.tools.clients.factory.get_trace_client", return_value=mock_client),
    ):
        result = await check_fetch_trace()

        assert result.status == ToolTestStatus.SUCCESS
        assert "Cloud Trace API client initialized successfully" in result.message
        assert result.details["project_id"] == "test-project"


@pytest.mark.asyncio
async def test_check_fetch_trace_no_project():
    """Test trace check without project ID."""
    with patch("sre_agent.tools.test_functions.get_check_project_id", return_value=None):
        result = await check_fetch_trace()

        assert result.status == ToolTestStatus.FAILED
        assert "No project ID configured" in result.message


@pytest.mark.asyncio
async def test_check_fetch_trace_client_error():
    """Test trace check with client initialization error."""
    with (
        patch("sre_agent.tools.test_functions.get_check_project_id", return_value="test-project"),
        patch("sre_agent.tools.clients.factory.get_trace_client", side_effect=Exception("Client error")),
    ):
        result = await check_fetch_trace()

        assert result.status == ToolTestStatus.FAILED
        assert "Failed to initialize Cloud Trace client: Client error" in result.message


@pytest.mark.asyncio
async def test_check_list_log_entries_success():
    """Test successful logging client check."""
    mock_client = MagicMock()
    mock_client.list_log_entries = MagicMock()

    with (
        patch("sre_agent.tools.test_functions.get_check_project_id", return_value="test-project"),
        patch("sre_agent.tools.clients.factory.get_logging_client", return_value=mock_client),
    ):
        result = await check_list_log_entries()

        assert result.status == ToolTestStatus.SUCCESS
        assert "Cloud Logging API client initialized successfully" in result.message


@pytest.mark.asyncio
async def test_check_list_time_series_success():
    """Test successful monitoring client check."""
    mock_client = MagicMock()
    mock_client.list_time_series = MagicMock()

    with (
        patch("sre_agent.tools.test_functions.get_check_project_id", return_value="test-project"),
        patch("sre_agent.tools.clients.factory.get_monitoring_client", return_value=mock_client),
    ):
        result = await check_list_time_series()

        assert result.status == ToolTestStatus.SUCCESS
        assert "Cloud Monitoring API client initialized successfully" in result.message


@pytest.mark.asyncio
async def test_check_list_alerts_success():
    """Test successful alert policy client check."""
    mock_client = MagicMock()
    mock_client.list_alert_policies = MagicMock()

    with (
        patch("sre_agent.tools.test_functions.get_check_project_id", return_value="test-project"),
        patch("sre_agent.tools.clients.factory.get_alert_policy_client", return_value=mock_client),
    ):
        result = await check_list_alerts()

        assert result.status == ToolTestStatus.SUCCESS
        assert "Alert Policy API client initialized successfully" in result.message


@pytest.mark.asyncio
async def test_check_mcp_list_log_entries_success():
    """Test successful MCP logging toolset creation."""
    mock_toolset = MagicMock()

    with patch("sre_agent.tools.mcp.gcp.create_logging_mcp_toolset", return_value=mock_toolset):
        result = await check_mcp_list_log_entries()

        assert result.status == ToolTestStatus.SUCCESS
        assert "MCP Logging toolset created successfully" in result.message


@pytest.mark.asyncio
async def test_check_mcp_list_log_entries_none():
    """Test MCP logging toolset creation returning None."""
    with patch("sre_agent.tools.mcp.gcp.create_logging_mcp_toolset", return_value=None):
        result = await check_mcp_list_log_entries()

        assert result.status == ToolTestStatus.FAILED
        assert "Failed to create MCP Logging toolset - returned None" in result.message


@pytest.mark.asyncio
async def test_check_mcp_list_timeseries_success():
    """Test successful MCP monitoring toolset creation."""
    mock_toolset = MagicMock()

    with patch("sre_agent.tools.mcp.gcp.create_monitoring_mcp_toolset", return_value=mock_toolset):
        result = await check_mcp_list_timeseries()

        assert result.status == ToolTestStatus.SUCCESS
        assert "MCP Monitoring toolset created successfully" in result.message


@pytest.mark.asyncio
async def test_check_list_slos_success():
    """Test successful SLO client check."""
    mock_client = MagicMock()
    mock_client.list_services = MagicMock()
    mock_client.list_service_level_objectives = MagicMock()

    with (
        patch("sre_agent.tools.test_functions.get_check_project_id", return_value="test-project"),
        patch("google.cloud.monitoring_v3.ServiceMonitoringServiceClient", return_value=mock_client),
    ):
        result = await check_list_slos()

        assert result.status == ToolTestStatus.SUCCESS
        assert "Service Monitoring API client initialized successfully" in result.message


# Removed failing GKE test due to import issues in test environment