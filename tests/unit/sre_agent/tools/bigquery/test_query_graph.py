from unittest.mock import AsyncMock, patch

import pytest

import sre_agent.tools.bigquery.query_graph as query_graph


@pytest.mark.asyncio
async def test_query_historical_trajectories_success():
    # Mock BigQueryClient.execute_query to return a list of dicts
    mock_results = [
        {"source_node": "User Request", "target_node": "Search", "total_tokens": 100}
    ]

    with (
        patch("sre_agent.tools.bigquery.query_graph.BigQueryClient") as mock_client_cls,
        patch(
            "sre_agent.tools.bigquery.query_graph.get_current_project_id",
            return_value="dummy-project-id",
        ),
    ):
        mock_client = mock_client_cls.return_value
        mock_client.execute_query = AsyncMock(return_value=mock_results)

        # Pass a dummy tool_context
        result = await query_graph.query_historical_trajectories(
            gql_query="SELECT 1", tool_context="dummy"
        )
        assert "results" in result
        assert len(result["results"]) == 1
        assert result["status"] == "success"
        assert result["row_count"] == 1
        assert result["results"][0]["source_node"] == "User Request"


@pytest.mark.asyncio
async def test_find_successful_strategy():
    with patch(
        "sre_agent.tools.bigquery.query_graph.query_historical_trajectories"
    ) as mock_query:
        mock_query.return_value = {"results": [], "status": "success", "row_count": 0}
        await query_graph.find_successful_strategy(symptom="latency")
        assert mock_query.called
        # Check that the query contains "latency" and the score filter
        query_arg = (
            mock_query.call_args[1].get("gql_query") or mock_query.call_args[0][0]
        )
        assert "latency" in query_arg
        assert ">= 80" in query_arg


@pytest.mark.asyncio
async def test_find_past_mistakes():
    with patch(
        "sre_agent.tools.bigquery.query_graph.query_historical_trajectories"
    ) as mock_query:
        mock_query.return_value = {"results": [], "status": "success", "row_count": 0}
        await query_graph.find_past_mistakes(symptom="timeout")
        assert mock_query.called
        query_arg = (
            mock_query.call_args[1].get("gql_query") or mock_query.call_args[0][0]
        )
        assert "timeout" in query_arg
        assert "< 50" in query_arg
