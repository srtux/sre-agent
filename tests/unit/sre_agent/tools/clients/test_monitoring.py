from unittest import mock

import pytest
from opentelemetry.trace import Status, StatusCode

from sre_agent.tools.clients.monitoring import list_time_series, query_promql


@pytest.fixture(autouse=True)
def mock_user_auth():
    """Mock user credentials for all monitoring tool tests."""
    from unittest.mock import MagicMock

    from sre_agent.auth import clear_current_credentials, set_current_credentials

    mock_creds = MagicMock()
    mock_creds.token = "test-token"
    set_current_credentials(mock_creds)
    yield
    clear_current_credentials()


@pytest.mark.asyncio
@mock.patch("sre_agent.tools.clients.monitoring.get_monitoring_client")
async def test_list_time_series(mock_get_client):
    """Test list_time_series tool."""
    mock_client = mock.Mock()
    mock_get_client.return_value = mock_client

    # Mock TimeSeries
    mock_ts = mock.Mock()
    mock_ts.metric.type = "metric_type"
    mock_ts.metric.labels = {"l1": "v1"}
    mock_ts.resource.type = "res_type"
    mock_ts.resource.labels = {"l2": "v2"}

    mock_point = mock.Mock()
    mock_point.interval.end_time.isoformat.return_value = "2023-01-01T00:00:00Z"
    mock_point.value.double_value = 100.0
    mock_ts.points = [mock_point]

    mock_client.list_time_series.return_value = [mock_ts]

    result = await list_time_series("filter", 60, project_id="p1")

    assert result["status"] == "success"
    res_data = result["result"]
    assert len(res_data) == 1
    assert res_data[0]["metric"]["type"] == "metric_type"
    assert res_data[0]["points"][0]["value"] == 100.0


@pytest.mark.asyncio
@mock.patch("sre_agent.tools.clients.monitoring.AuthorizedSession")
@mock.patch("google.auth.default")
async def test_query_promql(mock_auth_default, mock_session_cls):
    """Test query_promql tool."""
    mock_auth_default.return_value = (mock.Mock(), "p1")
    mock_session = mock.Mock()
    mock_session_cls.return_value = mock_session

    mock_response = mock.Mock()
    mock_response.json.return_value = {"status": "success", "data": {"result": []}}
    mock_session.get.return_value = mock_response

    result = await query_promql("up", project_id="p1")

    assert result["status"] == "success"
    assert result["result"]["status"] == "success"
    mock_session.get.assert_called_once()
    call_args = mock_session.get.call_args
    assert call_args.kwargs["params"]["query"] == "up"


@pytest.mark.asyncio
@mock.patch("sre_agent.tools.clients.monitoring.get_monitoring_client")
async def test_list_time_series_error(mock_get_client):
    """Test list_time_series tool error handling."""
    mock_client = mock_get_client.return_value
    mock_client.list_time_series.side_effect = Exception("API error")

    result = await list_time_series("filter", project_id="p1")

    assert "API error" in result["error"]


@pytest.mark.asyncio
@mock.patch("sre_agent.tools.clients.monitoring.tracer")
@mock.patch("sre_agent.tools.clients.monitoring.AuthorizedSession")
@mock.patch("google.auth.default")
async def test_query_promql_otel_error_status(
    mock_auth_default, mock_session_cls, mock_tracer
):
    """Test that query_promql sets OTel span status to ERROR on failure."""
    # Setup Auth Mock
    mock_auth_default.return_value = (mock.Mock(), "p1")
    mock_session = mock.Mock()
    mock_session_cls.return_value = mock_session

    # Setup Tracer Mock
    mock_span = mock.Mock()
    mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span

    # Simulate API Failure
    mock_session.get.side_effect = Exception("Prometheus API Failed")

    # Execute tool
    result = await query_promql("up", project_id="p1")

    # Verify tool behavior
    assert "error" in result
    assert "Prometheus API Failed" in result["error"]

    # Verify Tracer Interactions
    mock_tracer.start_as_current_span.assert_called_with("query_promql")

    assert mock_span.set_status.call_count == 1
    args, _ = mock_span.set_status.call_args
    status_obj = args[0]
    assert isinstance(status_obj, Status)
    assert status_obj.status_code == StatusCode.ERROR
    assert "Prometheus API Failed" in status_obj.description


@pytest.mark.asyncio
@mock.patch("sre_agent.tools.clients.monitoring.tracer")
@mock.patch("sre_agent.tools.clients.monitoring.get_monitoring_client")
async def test_list_time_series_otel_error_status(mock_get_client, mock_tracer):
    """Test that list_time_series sets OTel span status to ERROR on failure."""
    # Setup Tracer Mock
    mock_span = mock.Mock()
    mock_tracer.start_as_current_span.return_value.__enter__.return_value = mock_span

    # Setup Client Mock
    mock_client = mock_get_client.return_value
    mock_client.list_time_series.side_effect = Exception("Monitoring API Failed")

    # Execute tool
    result = await list_time_series("filter", project_id="p1")

    # Verify tool behavior
    assert "error" in result
    assert "Monitoring API Failed" in result["error"]

    # Verify Tracer Interactions
    mock_tracer.start_as_current_span.assert_called_with("list_time_series")

    assert mock_span.set_status.call_count == 1
    args, _ = mock_span.set_status.call_args
    status_obj = args[0]
    assert isinstance(status_obj, Status)
    assert status_obj.status_code == StatusCode.ERROR
    # Original code wraps the error message
    assert "Failed to list time series: Monitoring API Failed" in status_obj.description
