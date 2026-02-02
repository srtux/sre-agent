"""Multi-Window, Multi-Burn-Rate SLO Alerting.

Implements Google's recommended SLO alerting strategy from the SRE Workbook:
- Fast burn detection (short window, high threshold) for pages
- Slow burn detection (long window, lower threshold) for tickets

Reference: https://sre.google/workbook/alerting-on-slos/

The burn rate is defined as: actual_error_rate / max_allowed_error_rate
- burn_rate = 1 means consuming budget at exactly the SLO limit
- burn_rate > 1 means consuming budget faster than sustainable
- burn_rate = 14.4 means 2% of 30-day budget consumed in 1 hour
"""

import logging
from typing import Any

from sre_agent.schema import BaseToolResponse, ToolStatus
from sre_agent.tools.common import adk_tool

logger = logging.getLogger(__name__)

# Google SRE Workbook recommended windows and thresholds
# Each entry: (long_window_hours, short_window_hours, burn_rate_threshold, action)
MULTI_WINDOW_CONFIG: list[dict[str, Any]] = [
    {
        "name": "page_fast_burn",
        "long_window_hours": 1,
        "short_window_hours": 0.083,  # 5 minutes
        "burn_rate_threshold": 14.4,
        "budget_consumed_percent": 2.0,
        "action": "PAGE",
        "description": "2% of 30-day budget consumed in 1 hour",
    },
    {
        "name": "page_medium_burn",
        "long_window_hours": 6,
        "short_window_hours": 0.5,  # 30 minutes
        "burn_rate_threshold": 6.0,
        "budget_consumed_percent": 5.0,
        "action": "PAGE",
        "description": "5% of 30-day budget consumed in 6 hours",
    },
    {
        "name": "ticket_slow_burn",
        "long_window_hours": 24,
        "short_window_hours": 2,
        "burn_rate_threshold": 3.0,
        "budget_consumed_percent": 10.0,
        "action": "TICKET",
        "description": "10% of 30-day budget consumed in 24 hours",
    },
    {
        "name": "ticket_chronic_burn",
        "long_window_hours": 72,
        "short_window_hours": 6,
        "burn_rate_threshold": 1.0,
        "budget_consumed_percent": 10.0,
        "action": "TICKET",
        "description": "10% of 30-day budget consumed in 3 days",
    },
]


def _calculate_burn_rate(
    error_count: int,
    total_count: int,
    slo_target: float,
) -> float:
    """Calculate the burn rate given error counts and SLO target.

    Args:
        error_count: Number of bad events in the window.
        total_count: Total number of events in the window.
        slo_target: SLO target as a fraction (e.g., 0.999 for 99.9%).

    Returns:
        The burn rate multiplier. >1 means unsustainable.
    """
    if total_count == 0:
        return 0.0
    error_rate = error_count / total_count
    max_error_rate = 1.0 - slo_target
    if max_error_rate <= 0:
        return float("inf") if error_count > 0 else 0.0
    return error_rate / max_error_rate


def _calculate_error_budget_status(
    current_burn_rate: float,
    slo_target: float,
    rolling_period_days: int = 30,
) -> dict[str, Any]:
    """Calculate error budget consumption and projected exhaustion.

    Args:
        current_burn_rate: The current burn rate multiplier.
        slo_target: SLO target fraction.
        rolling_period_days: SLO rolling period in days.

    Returns:
        Dictionary with budget analysis.
    """
    max_error_rate = 1.0 - slo_target
    total_budget_minutes = rolling_period_days * 24 * 60 * max_error_rate

    if current_burn_rate <= 0:
        return {
            "budget_total_minutes": round(total_budget_minutes, 2),
            "burn_rate": 0.0,
            "projected_exhaustion_hours": None,
            "status": "HEALTHY",
            "recommendation": "No error budget consumption detected. Service is healthy.",
        }

    hours_to_exhaustion = (rolling_period_days * 24) / current_burn_rate

    if hours_to_exhaustion < 1:
        status = "CRITICAL"
        recommendation = (
            "Error budget will be exhausted within 1 hour. "
            "Immediate action required: rollback recent changes, scale up, or shed load."
        )
    elif hours_to_exhaustion < 24:
        status = "CRITICAL"
        recommendation = (
            f"Error budget exhaustion projected in {hours_to_exhaustion:.1f} hours. "
            "Page the on-call engineer and begin incident response."
        )
    elif hours_to_exhaustion < 72:
        status = "WARNING"
        recommendation = (
            f"Error budget projected to last {hours_to_exhaustion:.1f} hours. "
            "Create a ticket and investigate root cause within 24 hours."
        )
    elif hours_to_exhaustion < rolling_period_days * 24:
        status = "ELEVATED"
        recommendation = (
            f"Burn rate is {current_burn_rate:.2f}x sustainable. "
            "Monitor closely and plan remediation."
        )
    else:
        status = "HEALTHY"
        recommendation = (
            f"Burn rate ({current_burn_rate:.2f}x) is within sustainable limits."
        )

    return {
        "budget_total_minutes": round(total_budget_minutes, 2),
        "burn_rate": round(current_burn_rate, 4),
        "projected_exhaustion_hours": round(hours_to_exhaustion, 1),
        "status": status,
        "recommendation": recommendation,
    }


@adk_tool
async def analyze_multi_window_burn_rate(
    slo_target: float,
    error_counts_by_window: dict[str, Any] | None = None,
    total_counts_by_window: dict[str, Any] | None = None,
    current_error_rate: float | None = None,
    rolling_period_days: int = 30,
    tool_context: Any = None,
) -> BaseToolResponse:
    """Analyze SLO burn rate using Google's multi-window alerting strategy.

    This implements the recommended approach from the Google SRE Workbook for
    SLO-based alerting. It checks multiple time windows simultaneously to
    detect both fast burns (pages) and slow burns (tickets).

    You can provide either:
    1. error_counts_by_window + total_counts_by_window: For precise calculation
       with per-window data from Cloud Monitoring.
    2. current_error_rate: For quick estimation using a single error rate.

    Args:
        slo_target: SLO target as a decimal (e.g., 0.999 for 99.9%).
        error_counts_by_window: Dict mapping window names to error counts.
            Keys should be: "1h", "6h", "24h", "72h", "5m", "30m", "2h".
            Example: {"1h": 50, "6h": 200, "5m": 10, "30m": 25}
        total_counts_by_window: Dict mapping window names to total request counts.
            Same keys as error_counts_by_window.
            Example: {"1h": 10000, "6h": 60000, "5m": 800, "30m": 5000}
        current_error_rate: Current error rate as decimal (e.g., 0.01 for 1%).
            Used as fallback when per-window data isn't available.
        rolling_period_days: SLO rolling period in days (default 30).
        tool_context: Context object for tool execution.

    Returns:
        Multi-window burn rate analysis with alerts, budget status, and recommendations.

    Example:
        analyze_multi_window_burn_rate(
            slo_target=0.999,
            current_error_rate=0.005,
            rolling_period_days=30,
        )
    """
    try:
        if slo_target <= 0 or slo_target >= 1:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error=(
                    f"Invalid SLO target: {slo_target}. "
                    "Must be between 0 and 1 (e.g., 0.999 for 99.9%)."
                ),
            )

        max_error_rate = 1.0 - slo_target
        alerts_triggered: list[dict[str, Any]] = []
        window_analysis: list[dict[str, Any]] = []

        # Mode 1: Per-window analysis with actual counts
        if error_counts_by_window and total_counts_by_window:
            for config in MULTI_WINDOW_CONFIG:
                long_key = f"{config['long_window_hours']}h"
                short_key_hours = config["short_window_hours"]
                if short_key_hours < 1:
                    short_key = f"{int(short_key_hours * 60)}m"
                else:
                    short_key = f"{int(short_key_hours)}h"

                long_errors = error_counts_by_window.get(long_key, 0)
                long_total = total_counts_by_window.get(long_key, 0)
                short_errors = error_counts_by_window.get(short_key, 0)
                short_total = total_counts_by_window.get(short_key, 0)

                long_burn = _calculate_burn_rate(
                    int(long_errors), int(long_total), slo_target
                )
                short_burn = _calculate_burn_rate(
                    int(short_errors), int(short_total), slo_target
                )

                entry: dict[str, Any] = {
                    "window": config["name"],
                    "long_window": long_key,
                    "short_window": short_key,
                    "long_burn_rate": round(long_burn, 4),
                    "short_burn_rate": round(short_burn, 4),
                    "threshold": config["burn_rate_threshold"],
                    "action": config["action"],
                }

                # Alert fires when BOTH long AND short windows exceed threshold
                both_exceed = (
                    long_burn >= config["burn_rate_threshold"]
                    and short_burn >= config["burn_rate_threshold"]
                )
                entry["triggered"] = both_exceed

                if both_exceed:
                    alerts_triggered.append(
                        {
                            "window": config["name"],
                            "action": config["action"],
                            "description": config["description"],
                            "long_burn_rate": round(long_burn, 4),
                            "short_burn_rate": round(short_burn, 4),
                            "threshold": config["burn_rate_threshold"],
                        }
                    )

                window_analysis.append(entry)

            # Use the 1h burn rate for budget projection
            primary_burn_rate = 0.0
            if window_analysis:
                primary_burn_rate = window_analysis[0].get("long_burn_rate", 0.0)

        # Mode 2: Single error rate estimation
        elif current_error_rate is not None:
            primary_burn_rate = (
                current_error_rate / max_error_rate if max_error_rate > 0 else 0.0
            )

            for config in MULTI_WINDOW_CONFIG:
                entry = {
                    "window": config["name"],
                    "estimated_burn_rate": round(primary_burn_rate, 4),
                    "threshold": config["burn_rate_threshold"],
                    "action": config["action"],
                    "triggered": primary_burn_rate >= config["burn_rate_threshold"],
                    "note": "Estimated from single error rate (not per-window)",
                }
                window_analysis.append(entry)

                if primary_burn_rate >= config["burn_rate_threshold"]:
                    alerts_triggered.append(
                        {
                            "window": config["name"],
                            "action": config["action"],
                            "description": config["description"],
                            "estimated_burn_rate": round(primary_burn_rate, 4),
                            "threshold": config["burn_rate_threshold"],
                        }
                    )
        else:
            return BaseToolResponse(
                status=ToolStatus.ERROR,
                error=(
                    "Provide either error_counts_by_window + total_counts_by_window "
                    "for precise analysis, or current_error_rate for estimation."
                ),
            )

        # Calculate budget status
        budget_status = _calculate_error_budget_status(
            primary_burn_rate, slo_target, rolling_period_days
        )

        # Determine highest-severity alert
        page_alerts = [a for a in alerts_triggered if a["action"] == "PAGE"]
        ticket_alerts = [a for a in alerts_triggered if a["action"] == "TICKET"]

        if page_alerts:
            overall_action = "PAGE"
            overall_severity = "CRITICAL"
        elif ticket_alerts:
            overall_action = "TICKET"
            overall_severity = "WARNING"
        else:
            overall_action = "NONE"
            overall_severity = "OK"

        result: dict[str, Any] = {
            "slo_target": slo_target,
            "slo_target_display": f"{slo_target * 100:.3f}%",
            "max_error_rate": round(max_error_rate, 6),
            "rolling_period_days": rolling_period_days,
            "overall_severity": overall_severity,
            "overall_action": overall_action,
            "alerts_triggered": alerts_triggered,
            "window_analysis": window_analysis,
            "error_budget": budget_status,
        }

        # Add actionable summary
        if overall_action == "PAGE":
            result["summary"] = (
                f"ALERT: SLO burn rate exceeds page threshold. "
                f"{len(page_alerts)} page-level alert(s) triggered. "
                "Immediate human intervention required."
            )
        elif overall_action == "TICKET":
            result["summary"] = (
                f"WARNING: SLO burn rate elevated. "
                f"{len(ticket_alerts)} ticket-level alert(s) triggered. "
                "Create a ticket and investigate within 24 hours."
            )
        else:
            result["summary"] = (
                "OK: SLO burn rates are within acceptable limits across all windows."
            )

        return BaseToolResponse(
            status=ToolStatus.SUCCESS,
            result=result,
            metadata={"tool_category": "slo_analysis"},
        )

    except Exception as e:
        error_msg = f"Failed to analyze multi-window burn rate: {e!s}"
        logger.error(error_msg)
        return BaseToolResponse(status=ToolStatus.ERROR, error=error_msg)
