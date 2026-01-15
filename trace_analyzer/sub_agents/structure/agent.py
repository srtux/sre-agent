"""Structure Analyzer sub-agent for comparing call graph topology between traces."""

from google.adk.agents import Agent

from ...tools.trace_client import fetch_trace
from ...tools.trace_analysis import build_call_graph, find_structural_differences
from . import prompt

structure_analyzer = Agent(
    name="structure_analyzer",
    model="gemini-2.5-pro",
    description="""Structure Analysis Specialist - Compares call graph topology between traces.

Capabilities:
- Build hierarchical call tree from parent-child span relationships
- Identify missing operations (spans in baseline but not target)
- Detect new operations (spans in target but not baseline)
- Track changes in call tree depth and fan-out

Tools: fetch_trace, build_call_graph, find_structural_differences

Use when: You need to understand if the code path or service topology changed.""",
    instruction=prompt.STRUCTURE_ANALYZER_PROMPT,
    tools=[fetch_trace, build_call_graph, find_structural_differences],
)
