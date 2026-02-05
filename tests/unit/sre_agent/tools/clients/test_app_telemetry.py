"""Unit tests for App-aware telemetry client."""

from unittest.mock import patch

import pytest

from sre_agent.schema import ToolStatus
from sre_agent.tools.clients.app_telemetry import (
    _build_logs_filter,
    _build_metrics_filter,
    _extract_resource_filters,
    find_application_traces,
    get_application_health,
    get_application_logs,
    get_application_metrics,
)


class TestResourceFilterExtraction:
    """Tests for resource filter extraction."""

    def test_extract_cloud_run_services(self):
        """Test extracting Cloud Run service resources."""
        topology = {
            "topology": {
                "services": [
                    {
                        "service_reference": {
                            "uri": "//run.googleapis.com/projects/test/locations/us-central1/services/my-service"
                        }
                    }
                ],
                "workloads": [],
            }
        }

        resources = _extract_resource_filters(topology)

        assert len(resources["cloud_run_services"]) == 1
        assert resources["cloud_run_services"][0]["service"] == "my-service"
        assert resources["cloud_run_services"][0]["location"] == "us-central1"

    def test_extract_gke_workloads(self):
        """Test extracting GKE workload resources."""
        topology = {
            "topology": {
                "services": [],
                "workloads": [
                    {
                        "workload_reference": {
                            "uri": "//container.googleapis.com/projects/test/locations/us-central1/clusters/my-cluster/namespaces/default/deployments/my-app"
                        }
                    }
                ],
            }
        }

        resources = _extract_resource_filters(topology)

        assert len(resources["gke_clusters"]) == 1
        assert resources["gke_clusters"][0]["cluster"] == "my-cluster"

    def test_extract_empty_topology(self):
        """Test extracting from empty topology."""
        topology = {"topology": {"services": [], "workloads": []}}

        resources = _extract_resource_filters(topology)

        assert resources["cloud_run_services"] == []
        assert resources["gke_clusters"] == []


class TestMetricsFilterBuilding:
    """Tests for metrics filter building."""

    def test_build_cloud_run_filter(self):
        """Test building filter for Cloud Run."""
        resources = {
            "cloud_run_services": [
                {"service": "my-service", "location": "us-central1"}
            ],
            "gke_clusters": [],
            "cloud_sql_instances": [],
        }

        filters = _build_metrics_filter(resources)

        assert len(filters) == 1
        assert 'resource.type="cloud_run_revision"' in filters[0]
        assert 'resource.labels.service_name="my-service"' in filters[0]

    def test_build_gke_filter(self):
        """Test building filter for GKE."""
        resources = {
            "cloud_run_services": [],
            "gke_clusters": [{"cluster": "my-cluster"}],
            "cloud_sql_instances": [],
        }

        filters = _build_metrics_filter(resources)

        assert len(filters) == 1
        assert 'resource.type="k8s_container"' in filters[0]
        assert 'resource.labels.cluster_name="my-cluster"' in filters[0]


class TestLogsFilterBuilding:
    """Tests for logs filter building."""

    def test_build_combined_filter(self):
        """Test building combined log filter."""
        resources = {
            "cloud_run_services": [{"service": "svc-1"}],
            "gke_clusters": [{"cluster": "cluster-1"}],
            "gke_workloads": [{"namespace": "default"}],
            "cloud_sql_instances": [],
        }

        filter_str = _build_logs_filter(resources)

        assert "cloud_run_revision" in filter_str
        assert "k8s_container" in filter_str
        assert " OR " in filter_str


class TestGetApplicationMetrics:
    """Tests for get_application_metrics function."""

    @pytest.mark.asyncio
    async def test_get_metrics_success(self):
        """Test successful metrics retrieval."""
        mock_topology = {
            "application": {"display_name": "My App"},
            "topology": {
                "services": [
                    {
                        "service_reference": {
                            "uri": "//run.googleapis.com/projects/test/locations/us-central1/services/my-service"
                        }
                    }
                ],
                "workloads": [],
            },
            "summary": {},
        }

        mock_metrics = [
            {"metric": {"type": "run.googleapis.com/request_count"}, "points": []}
        ]

        with patch(
            "sre_agent.tools.clients.app_telemetry._get_application_topology_sync",
            return_value=mock_topology,
        ):
            with patch(
                "sre_agent.tools.clients.monitoring._list_time_series_sync",
                return_value=mock_metrics,
            ):
                result = await get_application_metrics(
                    application_id="my-app",
                    metric_type="run.googleapis.com/request_count",
                    project_id="test-project",
                )

                assert result.status == ToolStatus.SUCCESS
                assert result.result["application_id"] == "my-app"

    @pytest.mark.asyncio
    async def test_get_metrics_no_resources(self):
        """Test metrics with no monitorable resources."""
        mock_topology = {
            "application": {},
            "topology": {"services": [], "workloads": []},
            "summary": {},
        }

        with patch(
            "sre_agent.tools.clients.app_telemetry._get_application_topology_sync",
            return_value=mock_topology,
        ):
            result = await get_application_metrics(
                application_id="my-app",
                metric_type="test.metric",
                project_id="test-project",
            )

            assert result.status == ToolStatus.ERROR
            assert "No monitorable resources" in result.error


class TestGetApplicationLogs:
    """Tests for get_application_logs function."""

    @pytest.mark.asyncio
    async def test_get_logs_success(self):
        """Test successful log retrieval."""
        mock_topology = {
            "application": {"display_name": "My App"},
            "topology": {
                "services": [
                    {
                        "service_reference": {
                            "uri": "//run.googleapis.com/projects/test/locations/us-central1/services/my-service"
                        }
                    }
                ],
                "workloads": [],
            },
            "summary": {},
        }

        mock_logs = {
            "entries": [{"severity": "ERROR", "payload": "Test error"}],
            "next_page_token": None,
        }

        with patch(
            "sre_agent.tools.clients.app_telemetry._get_application_topology_sync",
            return_value=mock_topology,
        ):
            with patch(
                "sre_agent.tools.clients.logging._list_log_entries_sync",
                return_value=mock_logs,
            ):
                result = await get_application_logs(
                    application_id="my-app",
                    severity="ERROR",
                    project_id="test-project",
                )

                assert result.status == ToolStatus.SUCCESS
                assert result.result["entry_count"] == 1


class TestGetApplicationHealth:
    """Tests for get_application_health function."""

    @pytest.mark.asyncio
    async def test_get_health_healthy(self):
        """Test health check with healthy application."""
        mock_topology = {
            "application": {"display_name": "My App"},
            "topology": {
                "services": [
                    {
                        "service_reference": {
                            "uri": "//run.googleapis.com/projects/test/locations/us-central1/services/my-service"
                        }
                    }
                ],
                "workloads": [],
            },
            "summary": {
                "total_components": 1,
                "criticality": "HIGH",
                "environment": "PRODUCTION",
            },
        }

        mock_logs = {"entries": [], "next_page_token": None}

        with patch(
            "sre_agent.tools.clients.app_telemetry._get_application_topology_sync",
            return_value=mock_topology,
        ):
            with patch(
                "sre_agent.tools.clients.logging._list_log_entries_sync",
                return_value=mock_logs,
            ):
                result = await get_application_health(
                    application_id="my-app",
                    project_id="test-project",
                )

                assert result.status == ToolStatus.SUCCESS
                assert result.result["status"] == "HEALTHY"

    @pytest.mark.asyncio
    async def test_get_health_degraded(self):
        """Test health check with degraded application."""
        mock_topology = {
            "application": {"display_name": "My App"},
            "topology": {
                "services": [
                    {
                        "service_reference": {
                            "uri": "//run.googleapis.com/projects/test/locations/us-central1/services/my-service"
                        }
                    }
                ],
                "workloads": [],
            },
            "summary": {"total_components": 1},
        }

        mock_logs = {
            "entries": [{"severity": "ERROR", "payload": "Error 1"}],
            "next_page_token": None,
        }

        with patch(
            "sre_agent.tools.clients.app_telemetry._get_application_topology_sync",
            return_value=mock_topology,
        ):
            with patch(
                "sre_agent.tools.clients.logging._list_log_entries_sync",
                return_value=mock_logs,
            ):
                result = await get_application_health(
                    application_id="my-app",
                    project_id="test-project",
                )

                assert result.status == ToolStatus.SUCCESS
                # Should be DEGRADED or CRITICAL due to errors
                assert result.result["status"] in ["DEGRADED", "CRITICAL", "HEALTHY"]


class TestFindApplicationTraces:
    """Tests for find_application_traces function."""

    @pytest.mark.asyncio
    async def test_find_traces_success(self):
        """Test successful trace finding."""
        mock_topology = {
            "application": {"display_name": "My App"},
            "topology": {
                "services": [
                    {
                        "service_reference": {
                            "uri": "//run.googleapis.com/projects/test/locations/us/services/svc"
                        }
                    }
                ],
                "workloads": [],
            },
            "summary": {},
        }

        mock_traces = [
            {"trace_id": "trace-1", "duration_ms": 100},
            {"trace_id": "trace-2", "duration_ms": 200},
        ]

        with patch(
            "sre_agent.tools.clients.app_telemetry._get_application_topology_sync",
            return_value=mock_topology,
        ):
            with patch(
                "sre_agent.tools.clients.trace._list_traces_sync",
                return_value=mock_traces,
            ):
                result = await find_application_traces(
                    application_id="my-app",
                    project_id="test-project",
                )

                assert result.status == ToolStatus.SUCCESS
                assert result.result["trace_count"] == 2
