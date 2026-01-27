"""Unit tests for the GKE forensics client."""

from unittest.mock import MagicMock, patch

import pytest

from sre_agent.schema import ToolStatus

# Mock these globally to avoid segfaults
with patch("google.cloud.monitoring_v3.TimeInterval", MagicMock()):
    with patch("google.cloud.monitoring_v3.ListTimeSeriesRequest", MagicMock()):
        from sre_agent.tools.clients.gke import (
            _get_authorized_session,
            analyze_hpa_events,
            analyze_node_conditions,
            correlate_trace_with_kubernetes,
            get_container_oom_events,
            get_gke_cluster_health,
            get_pod_restart_events,
            get_workload_health_summary,
        )


def test_get_authorized_session():
    with patch(
        "sre_agent.tools.clients.gke.get_credentials_from_tool_context"
    ) as mock_tool_cred:
        with patch(
            "sre_agent.tools.clients.gke.get_current_credentials"
        ) as mock_curr_cred:
            # Case 1: Tool context credentials
            mock_tool_cred.return_value = MagicMock()
            _get_authorized_session(tool_context=MagicMock())
            mock_tool_cred.assert_called()

            # Case 2: Fallback to current credentials
            mock_tool_cred.return_value = None
            mock_curr_cred.return_value = (MagicMock(), "proj")
            _get_authorized_session()
            mock_curr_cred.assert_called()


@pytest.mark.asyncio
async def test_get_gke_cluster_health_happy():
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
            "nodePools": [
                {
                    "name": "pool1",
                    "status": "RUNNING",
                    "config": {"machineType": "n1-standard-1"},
                }
            ],
        }
        mock_session.get.return_value = mock_response
        result = await get_gke_cluster_health(
            "test-cluster", "us-central1", "test-proj"
        )
        assert result.status == ToolStatus.SUCCESS
        res_data = result.result
        assert res_data["health"] == "HEALTHY"
        assert res_data["node_pools"][0]["machine_type"] == "n1-standard-1"


@pytest.mark.asyncio
async def test_get_gke_cluster_health_states():
    with patch(
        "sre_agent.tools.clients.gke._get_authorized_session"
    ) as mock_session_factory:
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session

        # Test RECONCILING state
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "name": "test-cluster",
            "location": "us-central1",
            "status": "RECONCILING",
            "nodePools": [{"name": "pool1", "status": "RECONCILING"}],
        }
        mock_session.get.return_value = mock_response
        result = await get_gke_cluster_health(
            "test-cluster", "us-central1", "test-proj"
        )
        assert result.status == ToolStatus.SUCCESS
        assert result.result["health"] == "UPDATING"
        assert result.result["node_pools"][0]["upgrade_in_progress"] is True

        # Test DEGRADED state
        mock_response.json.return_value = {
            "name": "test-cluster",
            "location": "us-central1",
            "status": "DEGRADED",
            "conditions": [
                {"type": "Degraded", "status": "True", "message": "Bad things"}
            ],
        }
        result = await get_gke_cluster_health(
            "test-cluster", "us-central1", "test-proj"
        )
        assert result.status == ToolStatus.SUCCESS
        assert result.result["health"] == "DEGRADED"

        # Test status other than RUNNING, RECONCILING, DEGRADED
        mock_response.json.return_value = {
            "name": "test-cluster",
            "status": "STOPPED",
        }
        result = await get_gke_cluster_health(
            "test-cluster", "us-central1", "test-proj"
        )
        assert result.status == ToolStatus.SUCCESS
        assert result.result["health"] == "STOPPED"

        # Test error handling
        mock_session.get.side_effect = Exception("API error")
        result = await get_gke_cluster_health(
            "test-cluster", "us-central1", "test-proj"
        )
        assert result.error is not None


@pytest.mark.asyncio
async def test_get_gke_cluster_health_no_project():
    with patch("sre_agent.tools.clients.gke.get_current_project_id", return_value=None):
        result = await get_gke_cluster_health("test-cluster", "us-central1")
        assert result.error is not None


@pytest.mark.asyncio
async def test_analyze_node_conditions():
    with patch(
        "sre_agent.tools.clients.gke.get_monitoring_client"
    ) as mock_client_factory:
        with patch("sre_agent.tools.clients.gke.monitoring_v3"):
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client

            # Mock metric response
            mock_series = MagicMock()
            mock_series.resource.labels = {"node_name": "node-1"}
            mock_point = MagicMock()
            mock_point.value.__str__.return_value = "double_value: 0.9"
            mock_point.value.double_value = 0.9
            mock_series.points = [mock_point]
            mock_client.list_time_series.return_value = [mock_series]

            result = await analyze_node_conditions(
                cluster_name="test-cluster",
                location="us-central1",
                project_id="test-proj",
            )

            assert result.status == ToolStatus.SUCCESS
            res_data = result.result
            assert "node-1" in res_data["nodes"]
            assert len(res_data["pressure_warnings"]) > 0


@pytest.mark.asyncio
async def test_analyze_node_conditions_edge_cases():
    with patch(
        "sre_agent.tools.clients.gke.get_monitoring_client"
    ) as mock_client_factory:
        with patch("sre_agent.tools.clients.gke.monitoring_v3"):
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client

            # No results from monitoring
            mock_client.list_time_series.return_value = []
            result = await analyze_node_conditions(
                "test-cluster", "us-central1", project_id="test-proj"
            )
            assert result.status == ToolStatus.SUCCESS
            assert result.result["nodes"] == {}

            # No points in series
            mock_series = MagicMock()
            mock_series.resource.labels = {"node_name": "node-1"}
            mock_series.points = []
            mock_client.list_time_series.return_value = [mock_series]
            result = await analyze_node_conditions(
                "test-cluster", "us-central1", project_id="test-proj"
            )
            assert result.status == ToolStatus.SUCCESS
            assert "node-1" in result.result["nodes"]


@pytest.mark.asyncio
async def test_get_pod_restart_events():
    with patch(
        "sre_agent.tools.clients.gke.get_monitoring_client"
    ) as mock_client_factory:
        with patch("sre_agent.tools.clients.gke.monitoring_v3"):
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
            mock_series.points = [p1, p2]
            mock_client.list_time_series.return_value = [mock_series]

            result = await get_pod_restart_events(project_id="test-proj")
            assert result.status == ToolStatus.SUCCESS
            assert result.result["summary"]["total_restarts"] == 5


@pytest.mark.asyncio
async def test_analyze_hpa_events():
    with patch(
        "sre_agent.tools.clients.gke.get_monitoring_client"
    ) as mock_client_factory:
        with patch("sre_agent.tools.clients.gke.monitoring_v3"):
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
            assert result.status == ToolStatus.SUCCESS
            assert len(result.result["scaling_activity"]) > 0


@pytest.mark.asyncio
async def test_get_container_oom_events():
    with patch(
        "sre_agent.tools.clients.gke._get_authorized_session"
    ) as mock_session_factory:
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "entries": [
                {
                    "resource": {
                        "type": "k8s_container",
                        "labels": {"pod_name": "app-123", "namespace_name": "default"},
                    },
                    "textPayload": "Pod app-123 unit test memory limit exceeded OOMKilled",
                }
            ]
        }
        mock_session.post.return_value = mock_response

        with patch(
            "sre_agent.tools.clients.gke.get_monitoring_client"
        ) as mock_m_client:
            with patch("sre_agent.tools.clients.gke.monitoring_v3"):
                mock_series = MagicMock()
                mock_series.resource.labels = {
                    "pod_name": "app-123",
                    "namespace_name": "default",
                    "container_name": "app",
                }
                p1 = MagicMock()
                p1.value.double_value = 0.95
                mock_series.points = [p1]
                mock_m_client.return_value.list_time_series.return_value = [mock_series]

                result = await get_container_oom_events(project_id="test-proj")
                assert result.status == ToolStatus.SUCCESS
                assert result.result["oom_events_in_logs"] == 1


@pytest.mark.asyncio
async def test_get_container_oom_events_error():
    with patch(
        "sre_agent.tools.clients.gke._get_authorized_session"
    ) as mock_session_factory:
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session
        mock_session.post.side_effect = Exception("Logging API down")

        with patch(
            "sre_agent.tools.clients.gke.get_monitoring_client"
        ) as mock_m_client:
            with patch("sre_agent.tools.clients.gke.monitoring_v3"):
                mock_m_client.return_value.list_time_series.return_value = []
                result = await get_container_oom_events(project_id="test-proj")
                assert result.status == ToolStatus.SUCCESS
                assert result.result["oom_events_in_logs"] == 0


@pytest.mark.asyncio
async def test_correlate_trace_with_kubernetes():
    with patch(
        "sre_agent.tools.clients.gke._get_authorized_session"
    ) as mock_session_factory:
        with patch(
            "sre_agent.tools.clients.gke.get_current_project_id",
            return_value="test-proj",
        ):
            with patch("sre_agent.tools.clients.trace.fetch_trace_data") as mock_fetch:
                mock_fetch.return_value = {
                    "spans": [
                        {
                            "name": "service-a/operation",
                            "start_time": "2024-01-01T00:00:00Z",
                            "end_time": "2024-01-01T00:00:01Z",
                        }
                    ]
                }

                mock_session = MagicMock()
                mock_session_factory.return_value = mock_session

                mock_response = MagicMock()
                mock_response.json.return_value = {
                    "entries": [
                        {
                            "resource": {
                                "type": "k8s_container",
                                "labels": {
                                    "namespace_name": "default",
                                    "pod_name": "pod-1",
                                    "container_name": "app",
                                },
                            }
                        }
                    ]
                }
                mock_session.post.return_value = mock_response

                result = await correlate_trace_with_kubernetes(
                    project_id="test-proj", trace_id="trace-123"
                )
                assert result.status == ToolStatus.SUCCESS
                res_data = result.result
                assert len(res_data["kubernetes_context"]) == 1
                assert "Trace trace-123" in res_data["summary"]


@pytest.mark.asyncio
async def test_get_workload_health_summary_extensive():
    with patch(
        "sre_agent.tools.clients.gke.get_monitoring_client"
    ) as mock_client_factory:
        with patch("sre_agent.tools.clients.gke.monitoring_v3"):
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client

            # CPU Series
            s_cpu = MagicMock()
            s_cpu.resource.labels = {
                "pod_name": "app-v1-123",
                "namespace_name": "default",
            }
            p_cpu = MagicMock()
            p_cpu.value.double_value = 0.95  # Critical CPU
            s_cpu.points = [p_cpu]

            # Memory Series
            s_mem = MagicMock()
            s_mem.resource.labels = {
                "pod_name": "app-v1-456",
                "namespace_name": "default",
            }
            p_mem = MagicMock()
            p_mem.value.double_value = 0.99  # Critical Memory
            s_mem.points = [p_mem]

            # Restarts Series
            s_res = MagicMock()
            s_res.resource.labels = {
                "pod_name": "other-v2-789",
                "namespace_name": "default",
            }
            p_res1 = MagicMock()
            p_res1.value.int64_value = 10
            p_res2 = MagicMock()
            p_res2.value.int64_value = 0
            s_res.points = [p_res1, p_res2]  # 10 restarts

            mock_client.list_time_series.side_effect = [[s_cpu], [s_mem], [s_res]]

            result = await get_workload_health_summary(
                namespace="default", project_id="test-proj"
            )
            assert result.status == ToolStatus.SUCCESS
            res_data = result.result
            assert res_data["summary"]["critical"] >= 2
            assert "app" in [w["name"] for w in res_data["workloads"]]
            assert "other" in [w["name"] for w in res_data["workloads"]]
            assert res_data["workloads"][0]["status"] == "CRITICAL"
