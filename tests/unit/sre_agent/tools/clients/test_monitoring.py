from unittest import mock

import pytest

from sre_agent.schema import ToolStatus
from sre_agent.tools.clients.monitoring import (
    list_metric_descriptors,
    list_time_series,
    query_promql,
)


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

    # Fix: Mock objects have _pb by default, triggering the optimized path.
    # We must configure it to return the correct type.
    mock_point.value._pb.WhichOneof.return_value = "double_value"

    mock_ts.points = [mock_point]

    mock_client.list_time_series.return_value = [mock_ts]

    result = await list_time_series("filter", 60, project_id="p1")

    assert result.status == ToolStatus.SUCCESS
    res_data = result.result
    assert len(res_data) == 1
    assert res_data[0]["metric"]["type"] == "metric_type"
    assert res_data[0]["points"][0]["value"] == 100.0


@pytest.mark.asyncio
@mock.patch("sre_agent.tools.clients.monitoring.get_monitoring_client")
async def test_list_time_series_fallback(mock_get_client):
    """Test list_time_series tool fallback path (no _pb)."""
    mock_client = mock.Mock()
    mock_get_client.return_value = mock_client

    mock_ts = mock.Mock()
    mock_ts.metric.type = "metric_type"
    mock_ts.metric.labels = {"l1": "v1"}
    mock_ts.resource.type = "res_type"
    mock_ts.resource.labels = {"l2": "v2"}

    mock_point = mock.Mock()
    mock_point.interval.end_time.isoformat.return_value = "2023-01-01T00:00:00Z"

    # Create a value mock that explicitly does NOT have _pb
    # We use spec to restrict attributes to only the ones we expect
    value_mock = mock.Mock(
        spec=["double_value", "int64_value", "bool_value", "string_value"]
    )
    value_mock.double_value = 100.0
    mock_point.value = value_mock

    mock_ts.points = [mock_point]

    mock_client.list_time_series.return_value = [mock_ts]

    result = await list_time_series("filter", 60, project_id="p1")

    assert result.status == ToolStatus.SUCCESS
    res_data = result.result
    assert len(res_data) == 1
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

    assert result.status == ToolStatus.SUCCESS
    assert result.result["status"] == "success"
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

    assert result.status == ToolStatus.ERROR
    assert "API error" in result.error


@pytest.mark.asyncio
@mock.patch("sre_agent.tools.clients.monitoring.get_monitoring_client")
async def test_list_metric_descriptors_split_or(mock_get_client):
    """Test list_metric_descriptors tool with OR splitting."""
    mock_client = mock.Mock()
    mock_get_client.return_value = mock_client

    # Define mock return values
    desc1 = mock.Mock()
    desc1.type = "metric1"
    desc1.metric_kind = mock.Mock()
    desc1.metric_kind.name = "GAUGE"
    desc1.value_type = mock.Mock()
    desc1.value_type.name = "DOUBLE"
    desc1.name = "name1"
    desc1.unit = "unit1"
    desc1.description = "desc1"
    desc1.display_name = "display1"
    desc1.labels = []

    desc2 = mock.Mock()
    desc2.type = "metric2"
    desc2.metric_kind = mock.Mock()
    desc2.metric_kind.name = "GAUGE"
    desc2.value_type = mock.Mock()
    desc2.value_type.name = "DOUBLE"
    desc2.name = "name2"
    desc2.unit = "unit2"
    desc2.description = "desc2"
    desc2.display_name = "display2"
    desc2.labels = []

    # Mock side effect to return different values for different filters
    def side_effect(request):
        if "metric1" in request["filter"]:
            return [desc1]
        elif "metric2" in request["filter"]:
            return [desc2]
        return []

    mock_client.list_metric_descriptors.side_effect = side_effect

    # This should trigger splitting
    filter_str = 'metric.type="metric1" OR metric.type="metric2"'
    result = await list_metric_descriptors(filter_str, project_id="p1")

    assert result.status == ToolStatus.SUCCESS
    assert len(result.result) == 2
    assert {d["type"] for d in result.result} == {"metric1", "metric2"}
    # Should have called twice due to OR split
    assert mock_client.list_metric_descriptors.call_count == 2
