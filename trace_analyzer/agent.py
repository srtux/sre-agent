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

trace_analyzer_agent = LlmAgent(
    name="trace_analyzer_agent",
    model="gemini-2.5-pro",
    description="Orchestrates a team of trace analysis specialists to perform diff analysis between distributed traces.",
    instruction=prompt.ROOT_AGENT_PROMPT,
    output_key="trace_analysis_report",
    tools=[
        # Direct tools for trace discovery and fetching
        find_example_traces,
        fetch_trace,
        list_traces,
        get_trace_by_url,
        summarize_trace,
        get_current_time,
        # The parallel squad as a single tool
        AgentTool(agent=trace_analysis_squad),
    ],
)

# Expose as root_agent for ADK CLI compatibility
root_agent = trace_analyzer_agent
