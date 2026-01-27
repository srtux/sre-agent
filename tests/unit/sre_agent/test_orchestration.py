from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.tools import ToolContext

from sre_agent.agent import (
    run_aggregate_analysis,
    run_deep_dive_analysis,
    run_log_pattern_analysis,
    run_triage_analysis,
)
from sre_agent.schema import ToolStatus


@pytest.mark.asyncio
async def test_run_aggregate_analysis_success():
    tool_context = MagicMock(spec=ToolContext)
    with patch("sre_agent.agent.AgentTool") as MockAgentTool:
        mock_instance = MockAgentTool.return_value
        mock_instance.run_async = AsyncMock(return_value="Analysis complete")

        response = await run_aggregate_analysis(
            dataset_id="d", table_name="t", tool_context=tool_context
        )

        assert response.status == ToolStatus.SUCCESS
        assert response.result == "Analysis complete"
        assert response.metadata["stage"] == "aggregate"
        mock_instance.run_async.assert_called_once()


@pytest.mark.asyncio
async def test_run_triage_analysis_success():
    tool_context = MagicMock(spec=ToolContext)
    with patch("sre_agent.agent.get_project_id_with_fallback", return_value="p"):
        with patch("sre_agent.agent.AgentTool") as MockAgentTool:
            mock_instance = MockAgentTool.return_value
            mock_instance.run_async = AsyncMock(return_value="OK")

            response = await run_triage_analysis(
                baseline_trace_id="b", target_trace_id="t", tool_context=tool_context
            )

            assert response.status == ToolStatus.SUCCESS
            assert response.metadata["stage"] == "triage"
            result = response.result
            assert result["baseline_trace_id"] == "b"
            assert result["target_trace_id"] == "t"
            results = result["results"]
            assert results["trace"]["status"] == "success"
            assert results["log_analyst"]["status"] == "success"
            # 2 agents called in parallel (Trace Analyst + Log Analyst)
            assert mock_instance.run_async.await_count == 2


@pytest.mark.asyncio
async def test_run_log_pattern_analysis_success():
    tool_context = MagicMock(spec=ToolContext)
    with patch("sre_agent.agent.get_project_id_with_fallback", return_value="p"):
        with patch("sre_agent.agent.AgentTool") as MockAgentTool:
            mock_instance = MockAgentTool.return_value
            mock_instance.run_async = AsyncMock(return_value="Patterns found")

            response = await run_log_pattern_analysis(
                log_filter="f",
                baseline_start="s1",
                baseline_end="e1",
                comparison_start="s2",
                comparison_end="e2",
                tool_context=tool_context,
            )

            assert response.status == ToolStatus.SUCCESS
            assert response.result == "Patterns found"
            assert response.metadata["stage"] == "log_pattern"


@pytest.mark.asyncio
async def test_run_deep_dive_analysis_success():
    tool_context = MagicMock(spec=ToolContext)
    with patch("sre_agent.agent.get_project_id_with_fallback", return_value="p"):
        with patch("sre_agent.agent.AgentTool") as MockAgentTool:
            mock_instance = MockAgentTool.return_value
            mock_instance.run_async = AsyncMock(return_value="Deep dive done")

            response = await run_deep_dive_analysis(
                baseline_trace_id="b",
                target_trace_id="t",
                triage_findings={},
                tool_context=tool_context,
            )

            assert response.status == ToolStatus.SUCCESS
            assert response.result == "Deep dive done"
            assert response.metadata["stage"] == "deep_dive"
            # 1 agent called (Root Cause Analyst)
            assert mock_instance.run_async.await_count == 1
