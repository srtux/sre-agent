"""Error Analyzer sub-agent for detecting error changes between traces."""

from google.adk.agents import Agent

from ...tools.trace_client import fetch_trace
from ...tools.trace_analysis import extract_errors
from . import prompt

error_analyzer = Agent(
    name="error_analyzer",
    model="gemini-2.5-pro",
    description="""Error Detection Specialist - Identifies errors and failures in traces.

Capabilities:
- Detect HTTP 4xx/5xx status codes in span labels
- Identify gRPC errors (non-OK status)
- Find exception and fault indicators in span attributes
- Compare error patterns between baseline and target traces

Tools: fetch_trace, extract_errors

Use when: You need to find what errors occurred in a trace or compare error patterns.""",
    instruction=prompt.ERROR_ANALYZER_PROMPT,
    tools=[fetch_trace, extract_errors],
)
