from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.adk.tools import ToolContext

from sre_agent.agent import run_deep_dive_analysis, run_triage_analysis
from sre_agent.schema import ToolStatus


@pytest.mark.asyncio
async def test_run_triage_analysis_flow():
    """Test run_triage_analysis runs Stage 1 squad."""
    # Mock tool_context
    mock_tool_context = MagicMock(spec=ToolContext)

    # Mock AgentTool to intercept run_async calls
    with patch("sre_agent.agent.AgentTool") as MockAgentTool:
        mock_tool_instance = AsyncMock()
        MockAgentTool.return_value = mock_tool_instance

        # Setup mock return
        mock_tool_instance.run_async.return_value = "Stage 1 Report Content"

        response = await run_triage_analysis(
            baseline_trace_id="b1", target_trace_id="t1", tool_context=mock_tool_context
        )

        # Verify AgentTool instantiation (2 sub-agents: trace, log)
        assert MockAgentTool.call_count == 2

        # Verify run_async calls
        assert mock_tool_instance.run_async.call_count == 2

        # Verify result structure
        assert response.metadata["stage"] == "triage"
        result = response.result
        assert result["baseline_trace_id"] == "b1"
        assert result["target_trace_id"] == "t1"
        # Since AgentTool is mocked to return a string, and result is constructed manually in run_triage_analysis,
        # we need to check how run_triage_analysis constructs "results".
        # Assuming run_triage_analysis wraps tool outputs.
        # If run_triage_analysis returns BaseToolResponse, then response.result is the payload.
        # But wait, run_triage_analysis calls other tools.
        # Let's assume the previous code `response["result"]` was correct for the structure,
        # but now response is an object.
        # The internal structure of `result` (the dict) depends on run_triage_analysis implementation.
        # If run_triage_analysis returns a dict as result, then `result["baseline_trace_id"]` is fine.
        assert result["results"]["trace"]["result"] == "Stage 1 Report Content"


@pytest.mark.asyncio
async def test_run_deep_dive_analysis_flow():
    """Test run_deep_dive_analysis runs Stage 2 squad."""
    mock_tool_context = MagicMock(spec=ToolContext)

    with patch("sre_agent.agent.AgentTool") as MockAgentTool:
        mock_tool_instance = AsyncMock()
        MockAgentTool.return_value = mock_tool_instance
        mock_tool_instance.run_async.return_value = "Stage 2 Report Content"

        response = await run_deep_dive_analysis(
            baseline_trace_id="b1",
            target_trace_id="t1",
            triage_findings={"findings": "Stage 1 Findings"},
            tool_context=mock_tool_context,
        )

        assert MockAgentTool.call_count == 1
        assert mock_tool_instance.run_async.call_count == 1
        assert response.metadata["stage"] == "deep_dive"
        assert response.status == ToolStatus.SUCCESS
        assert response.result == "Stage 2 Report Content"


@pytest.mark.asyncio
async def test_tools_require_context():
    """Test that missing tool_context raises ValueError."""
    with pytest.raises(ValueError, match="tool_context is required"):
        await run_triage_analysis("b1", "t1", tool_context=None)

    with pytest.raises(ValueError, match="tool_context is required"):
        await run_deep_dive_analysis("b1", "t1", triage_findings={}, tool_context=None)
