"""Automated Postmortem Generator for blameless incident reviews.

Generates structured, blameless postmortems following Google's SRE practices.
The postmortem captures what happened, why, and what will prevent recurrence.

Key principles:
- Blameless: Focus on systemic issues, not individual mistakes
- Actionable: Every postmortem produces concrete action items
- Measurable: Include SLO impact and error budget consumption
- Reusable: Learn from past incidents to prevent future ones

Reference: https://sre.google/sre-book/postmortem-culture/
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sre_agent.schema import BaseToolResponse, Severity, ToolStatus
from sre_agent.tools.common import adk_tool

logger = logging.getLogger(__name__)


def _calculate_incident_duration(
    start_time: str, end_time: str | None
) -> dict[str, Any]:
    """Calculate incident duration metrics.

    Args:
        start_time: ISO 8601 start time.
        end_time: ISO 8601 end time (None if ongoing).

    Returns:
        Duration metrics.
    """
    try:
        start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))

        if end_time:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        else:
            end_dt = datetime.now(timezone.utc)

        delta = end_dt - start_dt
        total_minutes = delta.total_seconds() / 60.0

        return {
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat() if end_time else "ONGOING",
            "duration_minutes": round(total_minutes, 1),
            "duration_human": _format_duration(total_minutes),
            "is_ongoing": end_time is None,
        }
    except (ValueError, TypeError):
        return {
            "start_time": start_time,
            "end_time": end_time or "ONGOING",
            "duration_minutes": 0,
            "duration_human": "Unknown",
            "is_ongoing": end_time is None,
        }


def _format_duration(minutes: float) -> str:
    """Format duration in minutes to human-readable string."""
    if minutes < 1:
        return f"{minutes * 60:.0f} seconds"
    if minutes < 60:
        return f"{minutes:.0f} minutes"
    hours = minutes / 60
    if hours < 24:
        remaining_mins = minutes % 60
        return f"{int(hours)}h {int(remaining_mins)}m"
    days = hours / 24
    remaining_hours = hours % 24
    return f"{int(days)}d {int(remaining_hours)}h"


def _assess_severity(
    user_impact_percent: float | None = None,
    error_budget_consumed_percent: float | None = None,
    duration_minutes: float | None = None,
    revenue_impact: bool = False,
) -> dict[str, Any]:
    """Assess incident severity based on multiple signals.

    Args:
        user_impact_percent: Percentage of users affected.
        error_budget_consumed_percent: Percentage of error budget consumed.
        duration_minutes: Duration of the incident in minutes.
        revenue_impact: Whether the incident affected revenue.

    Returns:
        Severity assessment.
    """
    severity = Severity.LOW
    factors: list[str] = []

    if revenue_impact:
        severity = Severity.CRITICAL
        factors.append("Revenue-impacting incident")

    if user_impact_percent is not None:
        if user_impact_percent >= 50:
            severity = Severity.CRITICAL
            factors.append(f"{user_impact_percent}% of users affected (majority)")
        elif user_impact_percent >= 10:
            if severity.value not in ("critical",):
                severity = Severity.HIGH
            factors.append(f"{user_impact_percent}% of users affected")
        elif user_impact_percent >= 1:
            if severity.value not in ("critical", "high"):
                severity = Severity.MEDIUM
            factors.append(f"{user_impact_percent}% of users affected")

    if error_budget_consumed_percent is not None:
        if error_budget_consumed_percent >= 50:
            severity = Severity.CRITICAL
            factors.append(
                f"{error_budget_consumed_percent}% of error budget consumed"
            )
        elif error_budget_consumed_percent >= 20:
            if severity.value not in ("critical",):
                severity = Severity.HIGH
            factors.append(
                f"{error_budget_consumed_percent}% of error budget consumed"
            )
        elif error_budget_consumed_percent >= 5:
            if severity.value not in ("critical", "high"):
                severity = Severity.MEDIUM
            factors.append(
                f"{error_budget_consumed_percent}% of error budget consumed"
            )

    if duration_minutes is not None:
        if duration_minutes >= 240:
            if severity.value not in ("critical",):
                severity = Severity.HIGH
            factors.append(f"Extended duration: {_format_duration(duration_minutes)}")
        elif duration_minutes >= 60:
            if severity.value not in ("critical", "high"):
                severity = Severity.MEDIUM
            factors.append(f"Significant duration: {_format_duration(duration_minutes)}")

    if not factors:
        factors.append("No specific severity factors identified")

    return {
        "severity": severity.value,
        "factors": factors,
    }


def _generate_action_items(
    root_cause: str,
    contributing_factors: list[str],
    category: str,
) -> list[dict[str, Any]]:
    """Generate action items based on root cause analysis.

    Args:
        root_cause: Primary root cause description.
        contributing_factors: List of contributing factors.
        category: Incident category.

    Returns:
        List of action items with priorities and owners.
    """
    action_items: list[dict[str, Any]] = []

    # Always include detection improvement
    action_items.append(
        {
            "priority": "P1",
            "type": "detection",
            "action": "Improve monitoring and alerting for this failure mode",
            "description": (
                "Add or tune alerts to detect this issue faster. "
                "Target: reduce Time-to-Detect (TTD) by 50%."
            ),
            "owner": "SRE Team",
            "due": "1 week",
        }
    )

    # Root cause fix
    action_items.append(
        {
            "priority": "P0",
            "type": "fix",
            "action": f"Address root cause: {root_cause[:100]}",
            "description": (
                "Implement a permanent fix for the root cause to prevent recurrence."
            ),
            "owner": "Service Owner",
            "due": "2 weeks",
        }
    )

    # Category-specific actions
    root_lower = root_cause.lower()
    if "deploy" in root_lower or "rollback" in root_lower or category == "deployment":
        action_items.append(
            {
                "priority": "P1",
                "type": "process",
                "action": "Add canary deployment validation",
                "description": (
                    "Implement canary deployments with automatic rollback "
                    "on error rate increase. Monitor golden signals during rollout."
                ),
                "owner": "Platform Team",
                "due": "1 month",
            }
        )

    if "capacity" in root_lower or "scaling" in root_lower or "oom" in root_lower:
        action_items.append(
            {
                "priority": "P1",
                "type": "infrastructure",
                "action": "Implement capacity planning and load testing",
                "description": (
                    "Set up regular load tests to validate capacity. "
                    "Implement proactive autoscaling based on demand forecasting."
                ),
                "owner": "SRE Team",
                "due": "1 month",
            }
        )

    if "config" in root_lower or "flag" in root_lower:
        action_items.append(
            {
                "priority": "P1",
                "type": "process",
                "action": "Add configuration validation in CI/CD",
                "description": (
                    "Validate configuration changes in staging before production. "
                    "Add schema validation for configuration files."
                ),
                "owner": "Platform Team",
                "due": "2 weeks",
            }
        )

    # Contributing factor actions
    for factor in contributing_factors[:3]:
        action_items.append(
            {
                "priority": "P2",
                "type": "improvement",
                "action": f"Address contributing factor: {factor[:80]}",
                "description": "Mitigate this contributing factor to reduce blast radius.",
                "owner": "Service Owner",
                "due": "1 month",
            }
        )

    # Process improvements
    action_items.append(
        {
            "priority": "P2",
            "type": "documentation",
            "action": "Update runbooks with lessons learned",
            "description": (
                "Document the diagnosis steps and resolution for this type of incident. "
                "Add to on-call playbook."
            ),
            "owner": "SRE Team",
            "due": "1 week",
        }
    )

    return action_items


@adk_tool
async def generate_postmortem(
    title: str,
    incident_start: str,
    root_cause: str,
    summary: str,
    affected_services: list[str] | None = None,
    incident_end: str | None = None,
    detection_method: str | None = None,
    detection_time: str | None = None,
    mitigation_time: str | None = None,
    user_impact_percent: float | None = None,
    error_budget_consumed_percent: float | None = None,
    revenue_impact: bool = False,
    contributing_factors: list[str] | None = None,
    timeline_events: list[dict[str, str]] | None = None,
    findings: list[str] | None = None,
    category: str = "unknown",
    tool_context: Any = None,
) -> BaseToolResponse:
    """Generate a structured, blameless postmortem report.

    Creates a comprehensive postmortem following Google SRE best practices.
    The report includes incident timeline, root cause analysis, impact
    assessment, and actionable items to prevent recurrence.

    Args:
        title: Short descriptive title for the incident.
        incident_start: When the incident began (ISO 8601).
        root_cause: Primary root cause of the incident.
        summary: Brief summary of what happened.
        affected_services: List of affected service names.
        incident_end: When the incident was resolved (ISO 8601).
        detection_method: How the incident was detected (alert, user report, etc.).
        detection_time: When the incident was first detected (ISO 8601).
        mitigation_time: When mitigation was applied (ISO 8601).
        user_impact_percent: Percentage of users affected (0-100).
        error_budget_consumed_percent: Percentage of error budget consumed.
        revenue_impact: Whether the incident impacted revenue.
        contributing_factors: List of factors that contributed to the incident.
        timeline_events: List of timeline entries, each with "time" and "event" keys.
        findings: List of investigation findings from the SRE agent.
        category: Incident category (deployment, infrastructure, etc.).
        tool_context: Context object for tool execution.

    Returns:
        Structured postmortem document with severity, timeline, RCA, and action items.

    Example:
        generate_postmortem(
            title="Checkout service latency spike",
            incident_start="2024-06-15T14:00:00Z",
            root_cause="Database connection pool exhaustion due to connection leak",
            summary="Users experienced 5x latency on checkout for 45 minutes",
            affected_services=["checkout", "payment"],
            incident_end="2024-06-15T14:45:00Z",
            user_impact_percent=30,
            error_budget_consumed_percent=8,
        )
    """
    try:
        affected_services = affected_services or []
        contributing_factors = contributing_factors or []
        timeline_events = timeline_events or []
        findings = findings or []

        # Duration and timing analysis
        duration = _calculate_incident_duration(incident_start, incident_end)

        # Time-to-detect (TTD)
        ttd_minutes: float | None = None
        if detection_time:
            try:
                start_dt = datetime.fromisoformat(
                    incident_start.replace("Z", "+00:00")
                )
                detect_dt = datetime.fromisoformat(
                    detection_time.replace("Z", "+00:00")
                )
                ttd_minutes = (detect_dt - start_dt).total_seconds() / 60.0
            except (ValueError, TypeError):
                pass

        # Time-to-mitigate (TTM)
        ttm_minutes: float | None = None
        if mitigation_time and detection_time:
            try:
                detect_dt = datetime.fromisoformat(
                    detection_time.replace("Z", "+00:00")
                )
                mitigate_dt = datetime.fromisoformat(
                    mitigation_time.replace("Z", "+00:00")
                )
                ttm_minutes = (mitigate_dt - detect_dt).total_seconds() / 60.0
            except (ValueError, TypeError):
                pass

        # Severity assessment
        severity = _assess_severity(
            user_impact_percent=user_impact_percent,
            error_budget_consumed_percent=error_budget_consumed_percent,
            duration_minutes=duration.get("duration_minutes"),
            revenue_impact=revenue_impact,
        )

        # Generate action items
        action_items = _generate_action_items(
            root_cause, contributing_factors, category
        )

        # Build the postmortem
        postmortem: dict[str, Any] = {
            "title": title,
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "status": "DRAFT" if duration.get("is_ongoing") else "COMPLETE",
            "severity": severity,
            "summary": summary,
            "incident_details": {
                "duration": duration,
                "affected_services": affected_services,
                "detection_method": detection_method or "Unknown",
                "category": category,
            },
            "impact": {
                "user_impact_percent": user_impact_percent,
                "error_budget_consumed_percent": error_budget_consumed_percent,
                "revenue_impact": revenue_impact,
                "description": (
                    f"{'Approximately ' + str(user_impact_percent) + '% of users were affected. ' if user_impact_percent else ''}"
                    f"{'Error budget consumption: ' + str(error_budget_consumed_percent) + '%. ' if error_budget_consumed_percent else ''}"
                    f"{'Revenue was impacted. ' if revenue_impact else ''}"
                    f"Duration: {duration.get('duration_human', 'Unknown')}."
                ),
            },
            "metrics": {
                "time_to_detect_minutes": (
                    round(ttd_minutes, 1) if ttd_minutes is not None else None
                ),
                "time_to_mitigate_minutes": (
                    round(ttm_minutes, 1) if ttm_minutes is not None else None
                ),
                "total_duration_minutes": duration.get("duration_minutes"),
            },
            "timeline": timeline_events,
            "root_cause_analysis": {
                "root_cause": root_cause,
                "contributing_factors": contributing_factors,
                "findings": findings,
                "category": category,
            },
            "action_items": action_items,
            "lessons_learned": {
                "what_went_well": [
                    (
                        f"Incident was detected via {detection_method}"
                        if detection_method
                        else "Incident was detected"
                    ),
                    (
                        f"Time to detect: {_format_duration(ttd_minutes)}"
                        if ttd_minutes is not None
                        else "Detection time not measured"
                    ),
                ],
                "what_went_poorly": [],
                "where_we_got_lucky": [],
            },
        }

        # Add assessment-specific lessons
        if ttd_minutes is not None and ttd_minutes > 15:
            postmortem["lessons_learned"]["what_went_poorly"].append(
                f"Detection took {_format_duration(ttd_minutes)} - "
                "target is under 15 minutes"
            )

        if ttm_minutes is not None and ttm_minutes > 30:
            postmortem["lessons_learned"]["what_went_poorly"].append(
                f"Mitigation took {_format_duration(ttm_minutes)} - "
                "consider automating common mitigations"
            )

        if not detection_method or detection_method.lower() in (
            "user report",
            "customer complaint",
            "manual",
        ):
            postmortem["lessons_learned"]["what_went_poorly"].append(
                "Incident was detected by users, not monitoring - "
                "improve alerting coverage"
            )

        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=postmortem,
            metadata={
                "tool_category": "postmortem",
                "severity": severity["severity"],
            },
        )

    except Exception as e:
        error_msg = f"Failed to generate postmortem: {e!s}"
        logger.error(error_msg, exc_info=True)
        return BaseToolResponse(status=ToolStatus.ERROR, error=error_msg)
