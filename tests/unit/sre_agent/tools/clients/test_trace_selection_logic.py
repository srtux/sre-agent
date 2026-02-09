from unittest.mock import patch

import pytest

from sre_agent.schema import ToolStatus
from sre_agent.tools.clients.trace import find_example_traces, get_trace_by_url


@pytest.mark.asyncio
@patch("sre_agent.tools.clients.trace._list_traces_sync")
@patch("sre_agent.tools.clients.trace._get_project_id", return_value="p")
async def test_find_example_traces_hybrid(mock_pid, mock_list_traces):
    # Setup mock traces
    # 50 normal traces (around 100ms)
    traces = [
        {"trace_id": f"t{i}", "duration_ms": 100 + i, "project_id": "p"}
        for i in range(50)
    ]
    # Add one valid anomaly (500ms)
    traces.append({"trace_id": "t_slow", "duration_ms": 500, "project_id": "p"})

    # _list_traces_sync returns list directly
    mock_list_traces.return_value = traces

    # Call function
    result = await find_example_traces(project_id="p", prefer_errors=False)

    assert result.status == ToolStatus.SUCCESS
    final_res = result.result
    assert "baseline" in final_res
    assert "anomaly" in final_res
    assert "stats" in final_res

    # Baseline should be close to median (100-150 range)
    assert 100 <= final_res["baseline"]["duration_ms"] <= 150
    # Anomaly should be the slow one
    assert final_res["anomaly"]["trace_id"] == "t_slow"
    assert final_res["stats"]["count"] == 51


@pytest.mark.asyncio
@patch("sre_agent.tools.clients.trace.fetch_trace")
async def test_get_trace_by_url_success(mock_fetch_trace):
    url = "https://console.cloud.google.com/traces/list?project=my-project&tid=1234567890abcdef"  # pragma: allowlist secret
    mock_fetch_trace.return_value = {
        "status": "success",
        "result": {"trace_id": "1234567890abcdef"},
    }  # pragma: allowlist secret

    data = await get_trace_by_url(url)

    assert data["result"]["trace_id"] == "1234567890abcdef"  # pragma: allowlist secret
    mock_fetch_trace.assert_called_with(
        "1234567890abcdef",  # pragma: allowlist secret
        "my-project",
    )  # pragma: allowlist secret


@pytest.mark.asyncio
@patch("sre_agent.tools.clients.trace.fetch_trace")
async def test_get_trace_by_url_details_path(mock_fetch_trace):
    url = "https://console.cloud.google.com/traces/list/details/1234567890abcdef?project=my-project"  # pragma: allowlist secret
    mock_fetch_trace.return_value = {
        "status": "success",
        "result": {"trace_id": "1234567890abcdef"},
    }  # pragma: allowlist secret

    data = await get_trace_by_url(url)

    assert data["result"]["trace_id"] == "1234567890abcdef"  # pragma: allowlist secret


@pytest.mark.asyncio
async def test_get_trace_by_url_invalid():
    url = "https://google.com"
    data = await get_trace_by_url(url)
    assert data.status == ToolStatus.ERROR
