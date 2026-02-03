"""Agent trace analysis tools for Vertex Agent Engine debugging.

This package provides tools for analyzing AI agent interactions
via OpenTelemetry traces with GenAI semantic conventions.
"""

from .parsing import (
    build_interaction_tree,
    classify_span,
    compute_graph_aggregates,
    detect_anti_patterns,
    parse_bq_row_to_agent_span,
    parse_cloud_trace_span_to_agent_span,
)
from .queries import (
    get_agent_token_usage_query,
    get_agent_tool_usage_query,
    get_agent_trace_spans_query,
    get_agent_traces_query,
)
from .tools import (
    analyze_agent_token_usage,
    detect_agent_anti_patterns,
    list_agent_traces,
    reconstruct_agent_interaction,
)

__all__ = [
    "analyze_agent_token_usage",
    "build_interaction_tree",
    "classify_span",
    "compute_graph_aggregates",
    "detect_agent_anti_patterns",
    "detect_anti_patterns",
    "get_agent_token_usage_query",
    "get_agent_tool_usage_query",
    "get_agent_trace_spans_query",
    "get_agent_traces_query",
    "list_agent_traces",
    "parse_bq_row_to_agent_span",
    "parse_cloud_trace_span_to_agent_span",
    "reconstruct_agent_interaction",
]
