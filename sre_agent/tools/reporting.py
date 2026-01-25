"""Tool for synthesizing investigation reports."""

from typing import Any

from sre_agent.schema import BaseToolResponse, ToolStatus
from sre_agent.tools.common import adk_tool


@adk_tool
async def synthesize_report(
    root_cause_analysis: dict[str, Any],
    triage_results: dict[str, Any],
    aggregate_results: dict[str, Any] | None = None,
    log_analysis: dict[str, Any] | None = None,
    tool_context: Any | None = None,
) -> BaseToolResponse:
    """Synthesize a structured Root Cause Hypothesis report.

    Args:
        root_cause_analysis: Output from run_deep_dive_analysis.
        triage_results: Output from run_triage_analysis.
        aggregate_results: Output from run_aggregate_analysis (optional).
        log_analysis: Output from run_log_pattern_analysis (optional).
        tool_context: Tool context.

    Returns:
        Markdown-formatted investigation report in BaseToolResponse.
    """

    def extract_result(data: Any) -> Any:
        """Robustly extract the 'result' field from tool output."""
        if not isinstance(data, dict):
            return data
        # Check if it's a BaseToolResponse-style dict
        if "status" in data and "result" in data:
            return data["result"]
        return data

    # Extract inner results
    rc_result = extract_result(root_cause_analysis)
    triage_result = extract_result(triage_results)
    agg_result = extract_result(aggregate_results) if aggregate_results else None
    log_result = extract_result(log_analysis) if log_analysis else None

    report = ["# Root Cause Investigation Report\n"]

    # 1. Executive Summary
    report.append("## Executive Summary")

    # If rc_result is a string (from LlmAgent), use it directly as the summary
    if isinstance(rc_result, str):
        report.append(f"{rc_result}\n")
    else:
        # If it's a dict (legacy/structured), try to find causality
        causality = rc_result.get("causality", {}).get("result")
        if not causality:
            # Maybe it's nested under results
            causality = (
                rc_result.get("results", {})
                .get("causality", {})
                .get("result", "Analysis Inconclusive")
            )
        report.append(f"{causality}\n")

    # 2. Evidence
    report.append("## Evidence")

    # Change Detection
    if isinstance(rc_result, dict):
        change_detective = (
            rc_result.get("results", {})
            .get("change_detective", {})
            .get("result", "No change detection data")
        )
        report.append(f"### Change Correlation\n{change_detective}\n")

    # 3. Trace Forensics
    report.append("## Trace Forensics")

    if agg_result:
        if isinstance(agg_result, str):
            report.append(f"### Aggregate Patterns\n{agg_result}\n")
        else:
            report.append(
                f"### Aggregate Patterns\n{agg_result.get('result', 'No aggregate data')}\n"
            )

    # Triage Findings
    if isinstance(triage_result, dict):
        findings = triage_result.get("results", {})
        for name, res in findings.items():
            if isinstance(res, dict) and res.get("status") == "success":
                report.append(f"### {name.title()} Analyst\n{res.get('result')}\n")
            elif isinstance(res, str):
                report.append(f"### {name.title()} Analyst\n{res}\n")

    # 4. Log Analysis
    if log_result:
        report.append("## Log Patterns")
        if isinstance(log_result, str):
            report.append(f"{log_result}\n")
        else:
            report.append(f"{log_result.get('result', 'No log analysis data')}\n")

    # 5. Service Impact
    report.append("## Impact Assessment")
    if isinstance(rc_result, dict):
        impact = (
            rc_result.get("results", {})
            .get("service_impact", {})
            .get("result", "Unknown Impact")
        )
        report.append(f"{impact}\n")
    else:
        report.append("Refer to Executive Summary for impact details.\n")

    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result={"report": "\n".join(report)},
        metadata={"stage": "reporting"},
    )
