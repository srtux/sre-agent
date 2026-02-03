"""Broad project health exploration tool.

Runs parallel queries across all telemetry signals (alerts, logs, traces,
metrics) to give the agent a quick overview of project health and populate
all dashboard tabs simultaneously.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sre_agent.schema import BaseToolResponse, ToolStatus
from sre_agent.tools.common import adk_tool

logger = logging.getLogger(__name__)


def _compute_health_summary(
    alerts_result: BaseToolResponse,
    logs_result: BaseToolResponse,
    traces_result: BaseToolResponse,
    metrics_result: BaseToolResponse,
) -> dict[str, Any]:
    """Derive a health summary from the collected signal results."""
    # --- Alerts ---
    alerts_data: list[Any] = []
    if alerts_result.status == ToolStatus.SUCCESS and alerts_result.result:
        alerts_data = (
            alerts_result.result if isinstance(alerts_result.result, list) else []
        )
    total_alerts = len(alerts_data)
    open_alerts = sum(
        1
        for a in alerts_data
        if isinstance(a, dict) and a.get("state", "").upper() == "OPEN"
    )

    # --- Logs ---
    error_log_count = 0
    warning_log_count = 0
    if logs_result.status == ToolStatus.SUCCESS and logs_result.result:
        entries: list[Any] = []
        if isinstance(logs_result.result, dict):
            entries = logs_result.result.get("entries", [])
        elif isinstance(logs_result.result, list):
            entries = logs_result.result
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            sev = str(entry.get("severity", "")).upper()
            if sev in ("ERROR", "CRITICAL", "ALERT", "EMERGENCY"):
                error_log_count += 1
            elif sev == "WARNING":
                warning_log_count += 1

    # --- Traces ---
    trace_count = 0
    if traces_result.status == ToolStatus.SUCCESS and traces_result.result:
        if isinstance(traces_result.result, list):
            trace_count = len(traces_result.result)

    # --- Health status ---
    has_issues = open_alerts > 0 or error_log_count > 0
    if open_alerts >= 3 or error_log_count >= 10:
        health_status = "critical"
    elif has_issues:
        health_status = "degraded"
    else:
        health_status = "healthy"

    return {
        "total_alerts": total_alerts,
        "open_alerts": open_alerts,
        "error_log_count": error_log_count,
        "warning_log_count": warning_log_count,
        "trace_count": trace_count,
        "has_issues": has_issues,
        "health_status": health_status,
    }


def _safe_result(response: BaseToolResponse | BaseException) -> BaseToolResponse:
    """Convert a gather result (possibly an exception) to a BaseToolResponse."""
    if isinstance(response, BaseException):
        logger.warning("Exploration sub-query failed: %s", response)
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=str(response),
        )
    return response


@adk_tool
async def explore_project_health(
    project_id: str | None = None,
    minutes_ago: int = 15,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Perform a broad health scan of a GCP project.

    Queries alerts, logs, traces, and metrics in parallel to give a quick
    overview of recent project health.  The result populates all dashboard
    tabs simultaneously so the user can immediately explore any signal.

    Args:
        project_id: The Google Cloud Project ID. Resolved from context if omitted.
        minutes_ago: How far back to scan (default 15 minutes).
        tool_context: Context object for tool execution (credential propagation).

    Returns:
        Structured health scan with alerts, logs, traces, metrics, and a
        summary including health_status (healthy/degraded/critical).
    """
    from sre_agent.auth import is_guest_mode

    if is_guest_mode():
        from sre_agent.tools.synthetic.provider import SyntheticDataProvider

        return SyntheticDataProvider.explore_project_health(
            project_id=project_id,
            minutes_ago=minutes_ago,
        )

    from sre_agent.auth import get_current_project_id

    if not project_id:
        project_id = get_current_project_id()
        if not project_id:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error=(
                    "Project ID is required but not provided or found in context. "
                    "HINT: If you are using the Agent Engine playground, please pass "
                    "the project ID in your request (e.g., 'Analyze logs in project "
                    "my-project-id') or use the project selector. Local users should "
                    "set the GOOGLE_CLOUD_PROJECT environment variable."
                ),
            )

    # Build the time boundary for log/trace queries
    start_time = (
        datetime.now(tz=timezone.utc) - timedelta(minutes=minutes_ago)
    ).isoformat()

    # Import the underlying tool functions
    from sre_agent.tools.clients.alerts import list_alerts
    from sre_agent.tools.clients.logging import list_log_entries
    from sre_agent.tools.clients.monitoring import list_time_series
    from sre_agent.tools.clients.trace import list_traces

    # Fire all queries in parallel
    raw_results = await asyncio.gather(
        list_alerts(
            project_id=project_id,
            minutes_ago=minutes_ago,
            tool_context=tool_context,
        ),
        list_log_entries(
            filter_str=f'severity>=WARNING AND timestamp>="{start_time}"',
            project_id=project_id,
            limit=50,
            tool_context=tool_context,
        ),
        list_traces(
            project_id=project_id,
            limit=10,
            start_time=start_time,
            tool_context=tool_context,
        ),
        list_time_series(
            filter_str='metric.type="logging.googleapis.com/log_entry_count"',
            project_id=project_id,
            minutes_ago=minutes_ago,
            tool_context=tool_context,
        ),
        return_exceptions=True,
    )

    alerts_result = _safe_result(raw_results[0])
    logs_result = _safe_result(raw_results[1])
    traces_result = _safe_result(raw_results[2])
    metrics_result = _safe_result(raw_results[3])

    summary = _compute_health_summary(
        alerts_result, logs_result, traces_result, metrics_result
    )

    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result={
            "project_id": project_id,
            "scan_window_minutes": minutes_ago,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "alerts": alerts_result.result,
            "logs": logs_result.result,
            "traces": traces_result.result,
            "metrics": metrics_result.result,
            "summary": summary,
        },
    )
