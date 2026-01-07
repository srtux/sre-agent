
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from trace_analyzer.agent import run_two_stage_analysis
from google.adk.tools import ToolContext

@pytest.mark.asyncio
async def test_run_two_stage_analysis_accepts_project_id():
    """Test that run_two_stage_analysis accepts project_id and passes it to sub-agents."""
    
    # Mock tool context
    mock_context = MagicMock(spec=ToolContext)
    
    # Mock AgentTool to capture inputs
    with patch("trace_analyzer.agent.AgentTool") as MockAgentTool:
        mock_tool_instance = AsyncMock()
        mock_tool_instance.run_async.return_value = "Mock Report"
        MockAgentTool.return_value = mock_tool_instance
        
        # Run the tool
        result = await run_two_stage_analysis(
            baseline_trace_id="base",
            target_trace_id="target",
            project_id="test-project-id",
            tool_context=mock_context
        )
        
        # Verify it ran two agents (triage and deep dive)
        assert MockAgentTool.call_count == 2
        
        # Verify result structure
        assert "stage1_triage_report" in result
        assert "stage2_deep_dive_report" in result
        
        # Verify project_id was passed in the context string to the sub-agents
        # The arguments to run_async are {"args": ..., "tool_context": ...}
        
        # First call (Triage)
        call1_args = mock_tool_instance.run_async.await_args_list[0]
        # call1_args[1] is kwargs
        triage_input = call1_args[1]["args"]["request"]
        assert ' "project_id": "test-project-id"' in triage_input or "'project_id': 'test-project-id'" in triage_input
        
        # Second call (Deep Dive)
        call2_args = mock_tool_instance.run_async.await_args_list[1]
        deep_dive_input = call2_args[1]["args"]["request"]
        assert ' "project_id": "test-project-id"' in deep_dive_input or "'project_id': 'test-project-id'" in deep_dive_input
