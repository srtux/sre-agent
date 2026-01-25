"""Unit tests for the SLO/SLI client."""

from unittest.mock import MagicMock, patch

import pytest

from sre_agent.schema import ToolStatus

# Mock these globally to avoid segfaults
with patch("google.cloud.monitoring_v3.TimeInterval", MagicMock()):
    with patch(
        "google.cloud.monitoring_v3.ListServiceLevelObjectivesRequest", MagicMock()
    ):
        with patch("google.cloud.monitoring_v3.ListServicesRequest", MagicMock()):
            from sre_agent.tools.clients.slo import (
                analyze_error_budget_burn,
                get_golden_signals,
                get_slo_status,
                list_slos,
            )


@pytest.fixture(autouse=True)
def mock_auth():
    with patch("sre_agent.tools.clients.slo.get_current_credentials") as mock_current:
        mock_current.return_value = (MagicMock(), "test-project")
        with patch(
            "sre_agent.tools.clients.slo.get_credentials_from_tool_context"
        ) as mock_context:
            mock_context.return_value = None
            yield


@pytest.fixture
def mock_monitoring_v3_client():
    with patch("google.cloud.monitoring_v3.ServiceMonitoringServiceClient") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.mark.asyncio
async def test_list_slos_all_services(mock_monitoring_v3_client):
    mock_service = MagicMock()
    mock_service.name = "projects/test-proj/services/svc-1"
    mock_monitoring_v3_client.list_services.return_value = [mock_service]

    # Mock ListSLOs
    mock_slo = MagicMock()
    mock_slo.name = "test-slo"
    mock_slo.display_name = "Test SLO"
    mock_slo.goal = 0.99
    mock_slo.rolling_period.days = 30
    mock_slo.service_level_indicator.basic_sli.latency = None
    mock_slo.service_level_indicator.basic_sli.availability = MagicMock()

    mock_monitoring_v3_client.list_service_level_objectives.return_value = [mock_slo]

    result = await list_slos(project_id="test-proj")
    assert result["status"] == ToolStatus.SUCCESS
    res_data = result["result"]
    assert len(res_data) == 1
    assert res_data[0]["display_name"] == "Test SLO"


@pytest.mark.asyncio
async def test_get_slo_status_edge_cases():
    with patch(
        "sre_agent.tools.clients.slo._get_authorized_session"
    ) as mock_session_factory:
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session

        # Case 1: Latency SLI
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "displayName": "Latency SLO",
            "goal": 0.95,
            "serviceLevelIndicator": {"basicSli": {"latency": {"threshold": "1.5s"}}},
        }
        mock_session.get.return_value = mock_response
        result = await get_slo_status("proj", "svc", "slo")
        assert result["status"] == ToolStatus.SUCCESS
        assert result["result"]["sli_type"] == "latency"


@pytest.mark.asyncio
async def test_get_golden_signals_diverse():
    with patch(
        "sre_agent.tools.clients.slo.get_monitoring_client"
    ) as mock_client_factory:
        with patch("sre_agent.tools.clients.slo.monitoring_v3"):
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client

            # 1. Latency (double value)
            mock_s1 = MagicMock()
            p1 = MagicMock()
            p1.value.__str__.return_value = "double_value: 200"
            p1.value.double_value = 200
            # Ensure it doesn't look like distribution
            del p1.value.distribution_value
            mock_s1.points = [p1]

            # 2. Traffic (int64)
            mock_s2 = MagicMock()
            p2 = MagicMock()
            p2.value.__str__.return_value = "int64_value: 3600000"
            p2.value.int64_value = 3600000
            mock_s2.points = [p2]

            # 3. Errors (int64)
            mock_s3 = MagicMock()
            p3 = MagicMock()
            p3.value.__str__.return_value = "int64_value: 36000"
            p3.value.int64_value = 36000
            mock_s3.points = [p3]

            # 4. Saturation (distribution)
            mock_s4 = MagicMock()
            p4 = MagicMock()
            p4.value.__str__.return_value = "distribution_value: mean 0.5"
            p4.value.distribution_value.mean = 0.5
            mock_s4.points = [p4]

            mock_client.list_time_series.side_effect = [
                [mock_s1],
                [mock_s2],
                [mock_s3],
                [mock_s4],
            ]

            result = await get_golden_signals(
                project_id="test-proj", service_name="svc"
            )
            assert result["status"] == ToolStatus.SUCCESS
            res_data = result["result"]
            assert res_data["signals"]["latency"]["value_ms"] == 200
            assert (
                res_data["signals"]["saturation"]["cpu_utilization_avg_percent"] == 50.0
            )


@pytest.mark.asyncio
async def test_analyze_error_budget_burn_all_risks():
    with patch(
        "sre_agent.tools.clients.slo.get_monitoring_client"
    ) as mock_client_factory:
        with patch("sre_agent.tools.clients.slo.monitoring_v3"):
            mock_client = MagicMock()
            mock_client_factory.return_value = mock_client

            def create_mock_series(p1_val, p2_val):
                mock_series = MagicMock()
                p1 = MagicMock()
                p1.value.double_value = p1_val
                p1.interval.end_time.isoformat.return_value = "2024-01-01T00:00:00Z"
                p2 = MagicMock()
                p2.value.double_value = p2_val
                p2.interval.end_time.isoformat.return_value = "2024-01-01T01:00:00Z"
                mock_series.points = [p1, p2]
                return [mock_series]

            # LOW risk (burn_rate <= 0 or duration very long)
            mock_client.list_time_series.return_value = create_mock_series(0.9, 0.9)
            result = await analyze_error_budget_burn("proj", "svc", "slo", hours=24)
            assert result["status"] == ToolStatus.SUCCESS
            assert result["result"]["risk_level"] == "HEALTHY"

            # MEDIUM risk
            # 168h > duration > 72h
            # 24 * 0.1 / (0.13 - 0.1) = 24 * 3.33 = 80h.
            mock_client.list_time_series.return_value = create_mock_series(0.1, 0.13)
            result = await analyze_error_budget_burn("proj", "svc", "slo", hours=24)
            assert result["status"] == ToolStatus.SUCCESS
            assert result["result"]["risk_level"] == "MEDIUM"
