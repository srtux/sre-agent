"""Unit tests for the GKE forensics client."""

from unittest.mock import MagicMock, patch

import pytest

from sre_agent.tools.clients.gke import (
    analyze_hpa_events,
    analyze_node_conditions,
    get_container_oom_events,
    get_gke_cluster_health,
    get_pod_restart_events,
)


@pytest.mark.asyncio
async def test_get_gke_cluster_health():
    with patch(
        "sre_agent.tools.clients.gke._get_authorized_session"
    ) as mock_session_factory:
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "name": "test-cluster",
            "location": "us-central1",
            "status": "RUNNING",
            "nodePools": [{"name": "default", "status": "RUNNING"}],
            "conditions": [],
        }
        mock_session.get.return_value = mock_response

        result = await get_gke_cluster_health(
            cluster_name="test-cluster", location="us-central1", project_id="test-proj"
        )

        assert result["cluster_name"] == "test-cluster"
        assert result["health"] == "HEALTHY"


@pytest.mark.asyncio
async def test_analyze_node_conditions():
    with patch(
        "sre_agent.tools.clients.gke.get_monitoring_client"
    ) as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        # Mock metric response
        mock_series = MagicMock()
        mock_series.resource.labels = {"node_name": "node-1"}
        mock_point = MagicMock()
        mock_point.value.double_value = 0.9  # 90% utilization
        mock_series.points = [mock_point]
        mock_client.list_time_series.return_value = [mock_series]

        result = await analyze_node_conditions(
            cluster_name="test-cluster", location="us-central1", project_id="test-proj"
        )

        assert "node-1" in result["nodes"]
        assert len(result["pressure_warnings"]) > 0


@pytest.mark.asyncio
async def test_get_pod_restart_events():
    with patch(
        "sre_agent.tools.clients.gke.get_monitoring_client"
    ) as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        mock_series = MagicMock()
        mock_series.resource.labels = {
            "namespace_name": "default",
            "pod_name": "pod-1",
            "container_name": "app",
        }
        p1 = MagicMock()
        p1.value.int64_value = 10
        p2 = MagicMock()
        p2.value.int64_value = 5
        mock_series.points = [p1, p2]  # current=10, old=5 -> 5 restarts
        mock_client.list_time_series.return_value = [mock_series]

        result = await get_pod_restart_events(project_id="test-proj")
        assert result["summary"]["total_restarts"] == 5


@pytest.mark.asyncio
async def test_analyze_hpa_events():
    with patch(
        "sre_agent.tools.clients.gke.get_monitoring_client"
    ) as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        mock_series = MagicMock()
        p1 = MagicMock()
        p1.value.int64_value = 10
        p1.interval.end_time.isoformat.return_value = "2024-01-01T00:00:00Z"
        p2 = MagicMock()
        p2.value.int64_value = 5
        mock_series.points = [p1, p2]
        mock_client.list_time_series.return_value = [mock_series]

        result = await analyze_hpa_events(
            namespace="default", deployment_name="app", project_id="test-proj"
        )
        assert len(result["scaling_activity"]) > 0


@pytest.mark.asyncio
async def test_get_container_oom_events():
    with patch(
        "sre_agent.tools.clients.gke._get_authorized_session"
    ) as mock_session_factory:
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "entries": [{"textPayload": "Pod OOMKilled"}]
        }
        mock_session.post.return_value = mock_response

        # Mock monitoring client for memory usage part
        with patch(
            "sre_agent.tools.clients.gke.get_monitoring_client"
        ) as mock_m_client:
            mock_m_client.return_value.list_time_series.return_value = []

            result = await get_container_oom_events(project_id="test-proj")
            assert "oom_events_in_logs" in result
