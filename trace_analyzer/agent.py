"""Cloud Trace Analyzer - Root Agent Definition."""

import json
from google.adk.agents import LlmAgent, ParallelAgent
from google.adk.tools import AgentTool

from . import prompt
from .tools.trace_client import find_example_traces, fetch_trace, list_traces, get_trace_by_url, get_current_time
from .tools.trace_analysis import summarize_trace
from .sub_agents.latency.agent import latency_analyzer
from .sub_agents.error.agent import error_analyzer
from .sub_agents.structure.agent import structure_analyzer
from .sub_agents.statistics.agent import statistics_analyzer
from .sub_agents.causality.agent import causality_analyzer

# Define the parallel squad of specialists
trace_analysis_squad = ParallelAgent(
    name="trace_analysis_squad",
    sub_agents=[
        latency_analyzer,
        error_analyzer,
        structure_analyzer,
        statistics_analyzer,
        causality_analyzer
    ],
    description="Runs a comprehensive analysis using 5 specialized agents in parallel."
)


import os
import google.auth
from google.adk.tools.api_registry import ApiRegistry
from google.adk.tools.base_toolset import BaseToolset
from toolbox_core import ToolboxSyncClient

class LazyMcpRegistryToolset(BaseToolset):
    """Lazily initializes the ApiRegistry and McpToolset to ensure session creation happens in the correct event loop."""
    def __init__(self, project_id: str, mcp_server_name: str, tool_filter: list[str]):
        self.project_id = project_id
        self.mcp_server_name = mcp_server_name
        self.tool_filter = tool_filter
        self.tool_name_prefix = None
        self._inner_toolset = None
        
    async def get_tools(self, readonly_context=None):
        if not self._inner_toolset:
            # Initialize ApiRegistry lazily in the running event loop
            api_registry = ApiRegistry(self.project_id)
            self._inner_toolset = api_registry.get_toolset(
                mcp_server_name=self.mcp_server_name,
                tool_filter=self.tool_filter
            )
        return await self._inner_toolset.get_tools()

def load_mcp_tools():
    """Loads tools from configured MCP endpoints."""
    tools = []
    
    # 1. Google Cloud BigQuery MCP Endpoint via ApiRegistry
    try:
        # Get default project if not set, or use env var
        _, project_id = google.auth.default()
        # Fallback to env var if default auth doesn't provide project_id (e.g. running locally with user creds sometimes)
        project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        
        if project_id:
            # Pattern: projects/{project}/locations/global/mcpServers/{server_id}
            mcp_server_name = f"projects/{project_id}/locations/global/mcpServers/google-bigquery.googleapis.com-mcp"
            
            # Use LazyMcpRegistryToolset to avoid creating aiohttp sessions at module import time
            # which causes crashes in ASGI/uvicorn environments (especially with forking).
            bq_lazy_toolset = LazyMcpRegistryToolset(
                project_id=project_id,
                mcp_server_name=mcp_server_name,
                tool_filter=["execute_sql", "list_dataset_ids", "list_table_ids", "get_table_info"]
            )
            # Add the toolset directly. LlmAgent will call get_tools() on it.
            tools.append(bq_lazy_toolset)
            
    except Exception as e:
        print(f"Warning: Failed to setup BigQuery MCP tools: {e}")

    # 2. MCP Toolbox for Databases (Local/Self-hosted)
    # toolbox_url = "http://localhost:8080"
    # try:
    #     toolbox_client = ToolboxSyncClient(toolbox_url)
    #     if hasattr(toolbox_client, 'list_tools'):
    #          tools.extend(toolbox_client.list_tools())
    # except Exception:
    #     # Ignore if toolbox is not running
    #     pass
        
    return tools

# Initialize base tools
base_tools = [
        # Direct tools for trace discovery and fetching
        find_example_traces,
        fetch_trace,
        list_traces,
        get_trace_by_url,
        summarize_trace,
        get_current_time,
        # The parallel squad as a single tool
        AgentTool(agent=trace_analysis_squad),
]

# Load MCP tools
mcp_tools = load_mcp_tools()


# Detect Project ID for instruction
try:
    _, project_id = google.auth.default()
    project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
except Exception:
    project_id = None

final_instruction = prompt.ROOT_AGENT_PROMPT
if project_id:
    final_instruction += f"\n\nCurrent Project ID: {project_id}\nUse this for 'projectId' arguments in BigQuery tools."

trace_analyzer_agent = LlmAgent(
    name="trace_analyzer_agent",
    model="gemini-2.5-pro",
    description="Orchestrates a team of trace analysis specialists to perform diff analysis between distributed traces.",
    instruction=final_instruction,
    output_key="trace_analysis_report",
    tools=base_tools + mcp_tools,
)

# Expose as root_agent for ADK CLI compatibility
root_agent = trace_analyzer_agent
