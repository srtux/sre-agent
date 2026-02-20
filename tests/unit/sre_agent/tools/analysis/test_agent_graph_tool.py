from unittest.mock import patch

import pytest

from sre_agent.schema import ToolStatus
from sre_agent.tools.analysis.agent_trace.graph import get_agent_graph


@pytest.mark.asyncio
async def test_get_agent_graph_missing_project_id():
    with patch(
        "sre_agent.tools.analysis.agent_trace.graph.get_project_id_with_fallback",
        return_value=None,
    ):
        result = await get_agent_graph(project_id=None)
        assert result.status == ToolStatus.ERROR
        assert "project_id is required" in result.error


@pytest.mark.asyncio
async def test_get_agent_graph_returns_sql():
    # Mock project ID
    result = await get_agent_graph(project_id="test-project", dataset_id="test_ds")
    assert result.status == ToolStatus.SUCCESS

    payload = result.result
    assert payload["analysis_type"] == "agent_graph"
    assert len(payload["queries"]) == 2

    nodes_query = next(q for q in payload["queries"] if q["name"] == "nodes")
    edges_query = next(q for q in payload["queries"] if q["name"] == "edges")

    assert "SELECT" in nodes_query["sql"]
    assert "`test-project.test_ds.agent_topology_nodes`" in nodes_query["sql"]
    assert "agent_topology_edges" in edges_query["sql"]


@pytest.mark.asyncio
async def test_get_agent_graph_custom_time_range():
    start = "2023-01-01T00:00:00"
    end = "2023-01-02T00:00:00"
    result = await get_agent_graph(project_id="p", start_time=start, end_time=end)

    nodes_query = result.result["queries"][0]["sql"]
    expected_start = "TIMESTAMP('2023-01-01T00:00:00')"
    assert expected_start in nodes_query
