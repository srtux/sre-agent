from typing import Any, get_type_hints

from google.adk.tools import ToolContext

from sre_agent.agent import base_tools


def get_tool_parameters(func: Any) -> dict[str, Any]:
    """Helper to extract parameter types from a function."""
    # Unwrap @adk_tool decorator if present
    if hasattr(func, "__wrapped__"):
        func = func.__wrapped__
    return get_type_hints(func)


def test_no_complex_union_with_dict_in_tools():
    """Verify that no tool uses Union types containing dicts, which cause AnyOf schema issues."""

    suspicious_tools = []

    for tool in base_tools:
        tool_name = getattr(tool, "__name__", str(tool))
        hints = get_tool_parameters(tool)

        for param_name, param_type in hints.items():
            if param_name == "return":
                continue

            # Check for generic aliases (like list[dict] or Union[...])
            # simplified check logic
            type_str = str(param_type)

            # This detects the specific pattern that caused the detect_metric_anomalies crash
            # list[float] | list[dict[str, Any]]
            if "Union" in type_str and "dict" in type_str:
                suspicious_tools.append(f"{tool_name}.{param_name}: {type_str}")

    assert not suspicious_tools, (
        f"Found tools with risky Union+Dict types: {suspicious_tools}"
    )


def test_no_tool_context_type_in_signatures():
    """Verify that ToolContext is not used in type hints (should be Any)."""

    tools_with_context = []

    for tool in base_tools:
        tool_name = getattr(tool, "__name__", str(tool))
        hints = get_tool_parameters(tool)

        for param_name, param_type in hints.items():
            # Check if type is ToolContext or Optional[ToolContext]
            # String representation check is safer across python versions
            type_str = str(param_type)

            if "ToolContext" in type_str and "google.adk" in type_str:
                tools_with_context.append(f"{tool_name}.{param_name}")
            elif param_type is ToolContext:
                tools_with_context.append(f"{tool_name}.{param_name}")

    assert not tools_with_context, (
        f"Found tools exposing ToolContext in signature (use Any instead): {tools_with_context}"
    )


def test_detect_metric_anomalies_signature_safe():
    """Specific regression test for detect_metric_anomalies."""
    from sre_agent.tools.analysis.metrics.anomaly_detection import (
        detect_metric_anomalies,
    )

    hints = get_tool_parameters(detect_metric_anomalies)
    data_points_type = hints.get("data_points")

    # parameters should be list[float], not a Union
    assert data_points_type == list[float], (
        f"detect_metric_anomalies data_points type is {data_points_type}, expected list[float]"
    )


def test_run_analysis_tools_signature_safe():
    """Specific regression test for run_*_analysis tools."""
    from sre_agent.agent import (
        run_aggregate_analysis,
        run_deep_dive_analysis,
        run_log_pattern_analysis,
        run_triage_analysis,
    )

    tools = [
        run_aggregate_analysis,
        run_triage_analysis,
        run_deep_dive_analysis,
        run_log_pattern_analysis,
    ]

    for tool in tools:
        hints = get_tool_parameters(tool)
        tool_context_type = hints.get("tool_context")

        # Should be Any or Any | None, definitely NOT ToolContext
        type_str = str(tool_context_type)
        assert "ToolContext" not in type_str, (
            f"{tool.__name__} has ToolContext in signature: {type_str}"
        )


def test_mcp_tools_signature_safe():
    """Specific regression test for MCP tools."""
    from sre_agent.tools.mcp.gcp import (
        mcp_execute_sql,
        mcp_list_log_entries,
        mcp_list_timeseries,
        mcp_query_range,
    )

    tools = [
        mcp_list_log_entries,
        mcp_list_timeseries,
        mcp_query_range,
        mcp_execute_sql,
    ]

    for tool in tools:
        hints = get_tool_parameters(tool)
        tool_context_type = hints.get("tool_context")

        type_str = str(tool_context_type)
        assert "ToolContext" not in type_str, (
            f"{tool.__name__} has ToolContext in signature: {type_str}"
        )
