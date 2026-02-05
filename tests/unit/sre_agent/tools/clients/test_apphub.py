"""Unit tests for AppHub client."""

from unittest.mock import MagicMock, patch

import pytest

from sre_agent.schema import ToolStatus
from sre_agent.tools.clients.apphub import (
    get_application,
    get_application_topology,
    list_applications,
    list_discovered_services,
    list_discovered_workloads,
    list_services,
    list_workloads,
)


@pytest.fixture
def mock_session():
    """Create a mock authorized session."""
    with patch(
        "sre_agent.tools.clients.apphub._get_authorized_session"
    ) as mock_factory:
        session = MagicMock()
        mock_factory.return_value = session
        yield session


class TestListApplications:
    """Tests for list_applications function."""

    @pytest.mark.asyncio
    async def test_list_applications_success(self, mock_session):
        """Test successful application listing."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "applications": [
                {
                    "name": "projects/test/locations/global/applications/my-app",
                    "displayName": "My Application",
                    "description": "Test application",
                    "uid": "app-123",
                    "state": "ACTIVE",
                    "createTime": "2024-01-01T00:00:00Z",
                    "attributes": {
                        "criticality": {"type": "MISSION_CRITICAL"},
                        "environment": {"type": "PRODUCTION"},
                    },
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = await list_applications(project_id="test-project")

        assert result.status == ToolStatus.SUCCESS
        assert result.result["application_count"] == 1
        assert result.result["applications"][0]["display_name"] == "My Application"

    @pytest.mark.asyncio
    async def test_list_applications_empty(self, mock_session):
        """Test listing with no applications."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"applications": []}
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = await list_applications(project_id="test-project")

        assert result.status == ToolStatus.SUCCESS
        assert result.result["application_count"] == 0

    @pytest.mark.asyncio
    async def test_list_applications_no_project(self):
        """Test listing without project ID."""
        with patch(
            "sre_agent.tools.clients.apphub.get_current_project_id",
            return_value=None,
        ):
            result = await list_applications()
            assert result.status == ToolStatus.ERROR


class TestGetApplication:
    """Tests for get_application function."""

    @pytest.mark.asyncio
    async def test_get_application_success(self, mock_session):
        """Test successful application retrieval."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "name": "projects/test/locations/global/applications/my-app",
            "displayName": "My Application",
            "description": "Test application",
            "state": "ACTIVE",
            "attributes": {},
        }
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = await get_application(
            application_id="my-app",
            project_id="test-project",
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.result["display_name"] == "My Application"


class TestListServices:
    """Tests for list_services function."""

    @pytest.mark.asyncio
    async def test_list_services_success(self, mock_session):
        """Test successful service listing."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "services": [
                {
                    "name": "projects/test/locations/global/applications/my-app/services/svc-1",
                    "displayName": "Frontend Service",
                    "state": "ACTIVE",
                    "serviceReference": {
                        "uri": "//run.googleapis.com/projects/test/locations/us-central1/services/frontend"
                    },
                    "serviceProperties": {
                        "gcpProject": "test-project",
                        "location": "us-central1",
                    },
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = await list_services(
            application_id="my-app",
            project_id="test-project",
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.result["service_count"] == 1
        assert (
            "run.googleapis.com"
            in result.result["services"][0]["service_reference"]["uri"]
        )


class TestListWorkloads:
    """Tests for list_workloads function."""

    @pytest.mark.asyncio
    async def test_list_workloads_success(self, mock_session):
        """Test successful workload listing."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "workloads": [
                {
                    "name": "projects/test/locations/global/applications/my-app/workloads/wl-1",
                    "displayName": "Backend Workload",
                    "state": "ACTIVE",
                    "workloadReference": {
                        "uri": "//container.googleapis.com/projects/test/locations/us-central1/clusters/my-cluster/namespaces/default/deployments/backend"
                    },
                    "workloadProperties": {
                        "gcpProject": "test-project",
                    },
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = await list_workloads(
            application_id="my-app",
            project_id="test-project",
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.result["workload_count"] == 1


class TestListDiscoveredServices:
    """Tests for list_discovered_services function."""

    @pytest.mark.asyncio
    async def test_list_discovered_services_success(self, mock_session):
        """Test successful discovered service listing."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "discoveredServices": [
                {
                    "name": "projects/test/locations/global/discoveredServices/ds-1",
                    "serviceReference": {
                        "uri": "//run.googleapis.com/projects/test/locations/us/services/unregistered"
                    },
                    "serviceProperties": {},
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = await list_discovered_services(project_id="test-project")

        assert result.status == ToolStatus.SUCCESS
        assert result.result["discovered_count"] == 1


class TestListDiscoveredWorkloads:
    """Tests for list_discovered_workloads function."""

    @pytest.mark.asyncio
    async def test_list_discovered_workloads_success(self, mock_session):
        """Test successful discovered workload listing."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "discoveredWorkloads": [
                {
                    "name": "projects/test/locations/global/discoveredWorkloads/dw-1",
                    "workloadReference": {
                        "uri": "//container.googleapis.com/projects/test/clusters/cluster/workloads/wl"
                    },
                    "workloadProperties": {},
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        mock_session.get.return_value = mock_response

        result = await list_discovered_workloads(project_id="test-project")

        assert result.status == ToolStatus.SUCCESS
        assert result.result["discovered_count"] == 1


class TestGetApplicationTopology:
    """Tests for get_application_topology function."""

    @pytest.mark.asyncio
    async def test_get_topology_success(self, mock_session):
        """Test successful topology retrieval."""
        # Mock responses for app, services, and workloads
        app_response = MagicMock()
        app_response.json.return_value = {
            "name": "projects/test/locations/global/applications/my-app",
            "displayName": "My App",
            "state": "ACTIVE",
            "attributes": {
                "criticality": {"type": "HIGH"},
                "environment": {"type": "PRODUCTION"},
            },
        }
        app_response.raise_for_status = MagicMock()

        services_response = MagicMock()
        services_response.json.return_value = {
            "services": [
                {
                    "name": "svc-1",
                    "displayName": "Service 1",
                    "state": "ACTIVE",
                }
            ]
        }
        services_response.raise_for_status = MagicMock()

        workloads_response = MagicMock()
        workloads_response.json.return_value = {
            "workloads": [
                {
                    "name": "wl-1",
                    "displayName": "Workload 1",
                    "state": "ACTIVE",
                }
            ]
        }
        workloads_response.raise_for_status = MagicMock()

        # Return different responses for different URLs
        mock_session.get.side_effect = [
            app_response,
            services_response,
            workloads_response,
        ]

        result = await get_application_topology(
            application_id="my-app",
            project_id="test-project",
        )

        assert result.status == ToolStatus.SUCCESS
        assert result.result["topology"]["service_count"] == 1
        assert result.result["topology"]["workload_count"] == 1
        assert result.result["summary"]["total_components"] == 2
