"""Unit tests for the SLO/SLI client."""

from unittest.mock import MagicMock, patch

import pytest

from sre_agent.tools.clients.slo import (
    analyze_error_budget_burn,
    correlate_incident_with_slo_impact,
    get_golden_signals,
    get_slo_status,
    list_slos,
    predict_slo_violation,
)


@pytest.fixture
def mock_monitoring_v3():
    with patch("google.cloud.monitoring_v3.ServiceMonitoringServiceClient") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


def test_list_slos(mock_monitoring_v3):
    mock_slo = MagicMock()
    mock_slo.name = "test-slo"
    mock_slo.display_name = "Test SLO"
    mock_slo.goal = 0.99
    mock_slo.rolling_period.days = 30
    mock_slo.service_level_indicator.basic_sli.latency.threshold.seconds = 1
    mock_slo.service_level_indicator.basic_sli.latency.threshold.nanos = 0

    mock_monitoring_v3.list_service_level_objectives.return_value = [mock_slo]

    result = list_slos(project_id="test-proj", service_id="svc-1")
    assert len(result) == 1
    assert result[0]["display_name"] == "Test SLO"


def test_get_slo_status():
    with patch(
        "sre_agent.tools.clients.slo._get_authorized_session"
    ) as mock_session_factory:
        mock_session = MagicMock()
        mock_session_factory.return_value = mock_session

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "displayName": "Test SLO",
            "goal": 0.99,
            "serviceLevelIndicator": {"basicSli": {"availability": {}}},
        }
        mock_session.get.return_value = mock_response

        result = get_slo_status(
            project_id="test-proj", service_id="svc-1", slo_id="slo-1"
        )
        assert result["display_name"] == "Test SLO"
        assert result["sli_type"] == "availability"


def test_analyze_error_budget_burn():
    with patch(
        "sre_agent.tools.clients.slo.get_monitoring_client"
    ) as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        mock_series = MagicMock()
        p1 = MagicMock()
        p1.value.double_value = 0.99  # oldest
        p1.interval.end_time.isoformat.return_value = "2024-01-01T01:00:00Z"
        p2 = MagicMock()
        p2.value.double_value = 0.95  # newest
        p2.interval.end_time.isoformat.return_value = "2024-01-01T00:00:00Z"
        # The loop appends p1 then p2. compliance_points = [p1, p2]
        # first_val = p2 (oldest? No, if we want burn rate > 0, we want first_val > last_val)
        # first_val = compliance_points[-1] = p2
        # last_val = compliance_points[0] = p1
        # budget_consumed = p2 - p1 = 0.95 - 0.99 = -0.04 (negative burn)

        # Let's fix points to [newest, oldest]
        mock_series.points = [p2, p1]
        # compliance_points = [p2, p1]
        # first_val = p1 (0.99)
        # last_val = p2 (0.95)
        # budget_consumed = 0.04

        mock_client.list_time_series.return_value = [mock_series]

        result = analyze_error_budget_burn(
            project_id="test-proj", service_id="svc-1", slo_id="slo-1", hours=24
        )
        assert result.get("burn_rate_per_hour", 0) > 0


@pytest.mark.asyncio
async def test_get_golden_signals():
    with patch(
        "sre_agent.tools.clients.slo.get_monitoring_client"
    ) as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        # Mock traffic
        mock_series_traffic = MagicMock()
        mock_point_traffic = MagicMock()
        mock_point_traffic.value.int64_value = 6000
        mock_series_traffic.points = [mock_point_traffic]

        # Mock latency
        mock_series_latency = MagicMock()
        mock_point_latency = MagicMock()
        mock_point_latency.value.distribution_value.mean = 250
        mock_series_latency.points = [mock_point_latency]

        mock_client.list_time_series.side_effect = [
            [mock_series_latency],  # Latency
            [mock_series_traffic],  # Traffic
            [],  # Errors
            [],  # Saturation
        ]

        result = await get_golden_signals(project_id="test-proj", service_name="svc-1")
        assert result["signals"]["traffic"]["requests_per_second"] > 0
        assert result["signals"]["latency"]["value_ms"] == 250


@pytest.mark.asyncio
async def test_correlate_incident_with_slo_impact():
    with patch("sre_agent.tools.clients.slo.get_slo_status") as mock_status:
        mock_status.return_value = {"goal": 0.99, "rolling_period_days": 30}

        result = await correlate_incident_with_slo_impact(
            project_id="test-proj",
            service_id="svc-1",
            slo_id="slo-1",
            incident_start="2024-01-15T10:00:00Z",
            incident_end="2024-01-15T10:30:00Z",
        )
        assert result["incident_window"]["duration_minutes"] == 30
        assert "error_budget_analysis" in result


@pytest.mark.asyncio
async def test_predict_slo_violation():
    with patch("sre_agent.tools.clients.slo.analyze_error_budget_burn") as mock_burn:
        mock_burn.return_value = {
            "burn_rate_per_hour": 0.001,
            "hours_to_budget_exhaustion": 10,
        }

        result = await predict_slo_violation(
            project_id="test-proj", service_id="svc-1", slo_id="slo-1", hours_ahead=24
        )
        assert result["prediction"]["will_violate"] is True
