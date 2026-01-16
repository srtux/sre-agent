"""Statistics Analyzer sub-agent for statistical analysis of trace data."""

from google.adk.agents import Agent

from ...tools.trace_client import fetch_trace, list_traces
from ...tools.statistical_analysis import (
    compute_latency_statistics,
    detect_latency_anomalies,
    analyze_critical_path,
    compute_service_level_stats,
)
from . import prompt

statistics_analyzer = Agent(
    name="statistics_analyzer",
    model="gemini-2.5-pro",
    description="""Statistical Analysis Specialist - Computes distributions, percentiles, and detects anomalies.

Capabilities:
- Calculate P50/P90/P95/P99 latency percentiles across multiple traces
- Detect anomalies using z-score analysis (configurable threshold)
- Identify critical path (sequence determining total latency)
- Aggregate statistics by service name
- Detect high-variability and bimodal latency patterns

Tools: fetch_trace, list_traces, compute_latency_statistics, detect_latency_anomalies, analyze_critical_path, compute_service_level_stats

Use when: You need statistical analysis, percentile distributions, or anomaly detection.""",
    instruction=prompt.STATISTICS_ANALYZER_PROMPT,
    tools=[
        fetch_trace,
        list_traces,
        compute_latency_statistics,
        detect_latency_anomalies,
        analyze_critical_path,
        compute_service_level_stats,
    ],
)
