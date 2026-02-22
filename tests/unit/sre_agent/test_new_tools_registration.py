from sre_agent.agent import (
    TOOL_NAME_MAP,
    base_tools,
    run_aggregate_analysis,
    run_deep_dive_analysis,
    run_log_pattern_analysis,
    run_triage_analysis,
)
from sre_agent.tools import (
    analyze_critical_path,
    detect_trend_changes,
    discover_telemetry_sources,
    get_alert,
    get_golden_signals,
    get_logs_for_trace,
    list_traces,
    summarize_trace,
    synthesize_report,
)
from sre_agent.tools.analysis.bigquery.logs import analyze_bigquery_log_patterns
from sre_agent.tools.analysis.bigquery.otel import (
    analyze_aggregate_metrics,
    find_exemplar_traces,
)
from sre_agent.tools.mcp.gcp import (
    gcp_execute_sql,
    mcp_list_log_entries,
    mcp_list_timeseries,
    mcp_query_range,
)


def test_new_tools_in_base_tools():
    """Verify that all newly added tools are in the base_tools list."""
    expected_tools = [
        # MCP Tools
        gcp_execute_sql,
        mcp_list_log_entries,
        mcp_list_timeseries,
        mcp_query_range,
        # BigQuery Analysis Tools
        analyze_aggregate_metrics,
        find_exemplar_traces,
        analyze_bigquery_log_patterns,
        # Orchestration & Reporting
        run_aggregate_analysis,
        run_triage_analysis,
        run_deep_dive_analysis,
        run_log_pattern_analysis,
        synthesize_report,
        # Observability & Analysis
        list_traces,
        get_logs_for_trace,
        get_golden_signals,
        analyze_critical_path,
        summarize_trace,
        get_alert,
        detect_trend_changes,
        discover_telemetry_sources,
    ]

    for tool in expected_tools:
        assert tool in base_tools, f"Tool {tool} missing from base_tools"


def test_new_tools_in_tool_name_map():
    """Verify that all newly added tools are in the TOOL_NAME_MAP."""
    expected_tool_names = [
        "gcp_execute_sql",
        "mcp_list_log_entries",
        "mcp_list_timeseries",
        "mcp_query_range",
        "analyze_aggregate_metrics",
        "find_exemplar_traces",
        "analyze_bigquery_log_patterns",
        "list_traces",
        "get_logs_for_trace",
        "get_golden_signals",
        "analyze_critical_path",
        "summarize_trace",
        "get_alert",
        "detect_trend_changes",
        "discover_telemetry_sources",
        "synthesize_report",
    ]

    for name in expected_tool_names:
        assert name in TOOL_NAME_MAP, f"Tool name {name} missing from TOOL_NAME_MAP"


def test_tool_name_map_consistency():
    """Verify that TOOL_NAME_MAP points to the correct functions."""
    assert TOOL_NAME_MAP["gcp_execute_sql"] == gcp_execute_sql
    assert TOOL_NAME_MAP["analyze_aggregate_metrics"] == analyze_aggregate_metrics
    assert TOOL_NAME_MAP["synthesize_report"] == synthesize_report
    assert TOOL_NAME_MAP["list_traces"] == list_traces
