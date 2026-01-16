"""Latency Analyzer sub-agent for comparing span timings between traces."""

from google.adk.agents import Agent

from ...tools.trace_client import fetch_trace
from ...tools.trace_analysis import calculate_span_durations, compare_span_timings
from . import prompt

latency_analyzer = Agent(
    name="latency_analyzer",
    model="gemini-2.5-pro",
    description="""Latency Analysis Specialist - Compares span timing between baseline and target traces.

Capabilities:
- Calculate duration for each span in a trace
- Compare timing between two traces to find slower/faster spans
- Identify spans with >10% or >50ms latency changes
- Report missing or new operations

Tools: fetch_trace, calculate_span_durations, compare_span_timings

Use when: You need to understand what got slower or faster between two requests.""",
    instruction=prompt.LATENCY_ANALYZER_PROMPT,
    tools=[fetch_trace, calculate_span_durations, compare_span_timings],
)
