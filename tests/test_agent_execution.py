
import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from google.adk.tools import ToolContext, AgentTool

from trace_analyzer.agent import run_two_stage_analysis

@pytest.mark.asyncio
async def test_run_two_stage_analysis_flow():
    """
    Test run_two_stage_analysis properly orchestrates the 2 stages
    using AgentTool and passing context.
    """
    # Mock tool_context
    mock_tool_context = MagicMock(spec=ToolContext)
    
    # Mock AgentTool to intercept run_async calls
    with patch("trace_analyzer.agent.AgentTool") as MockAgentTool:
        mock_tool_instance = AsyncMock()
        MockAgentTool.return_value = mock_tool_instance
        
        # Setup mock returns
        # Stage 1 return
        mock_tool_instance.run_async.side_effect = [
            "Stage 1 Report Content", # First call (Stage 1)
            "Stage 2 Report Content"  # Second call (Stage 2)
        ]
        
        result = await run_two_stage_analysis(
            baseline_trace_id="b1",
            target_trace_id="t1",
            tool_context=mock_tool_context
        )
        
        # Verify AgentTool instantiation
        assert MockAgentTool.call_count == 2
        
        # Verify run_async calls
        assert mock_tool_instance.run_async.call_count == 2
        
        # Check first call args (Stage 1)
        call1_args = mock_tool_instance.run_async.call_args_list[0]
        args1 = call1_args.kwargs['args']
        assert "Context:" in args1['request']
        assert "b1" in args1['request']
        assert "t1" in args1['request']
        assert call1_args.kwargs['tool_context'] == mock_tool_context
        
        # Check second call args (Stage 2)
        call2_args = mock_tool_instance.run_async.call_args_list[1]
        args2 = call2_args.kwargs['args']
        assert "Stage 1 Report Content" in args2['request']
        
        # Verify result
        assert result["stage1_triage_report"] == "Stage 1 Report Content"
        assert result["stage2_deep_dive_report"] == "Stage 2 Report Content"

@pytest.mark.asyncio
async def test_run_two_stage_analysis_missing_context():
    """Test that missing tool_context raises ValueError."""
    with pytest.raises(ValueError, match="tool_context is required"):
        await run_two_stage_analysis("b1", "t1", tool_context=None)
