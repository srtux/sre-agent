"""Anomaly detection for metrics data."""

import logging
from typing import Any

from sre_agent.schema import BaseToolResponse, ToolStatus

from ...common.decorators import adk_tool
from .statistics import calculate_series_stats

logger = logging.getLogger(__name__)


@adk_tool
def detect_metric_anomalies(
    data_points: list[float],
    threshold_sigma: float = 3.0,
    value_key: str = "value",
    tool_context: Any = None,
) -> BaseToolResponse:
    """Detects anomalies in a series of data points using Z-score.

    Args:
        data_points: List of values or dicts containing values.
                     If dicts, 'value_key' is used to extract the number.
        threshold_sigma: Z-score threshold for anomaly detection (default 3.0).
        value_key: Key to look for if input is list of dicts.
        tool_context: Context object for tool execution.

    Returns:
        Dictionary with anomaly analysis.
    """
    values = []
    original_data_map = {}  # Map index to original data for reconstruction

    for _i, item in enumerate(data_points):
        val = None
        if isinstance(item, int | float):
            val = float(item)
        elif isinstance(item, dict):
            val = float(item.get(value_key, 0.0))

        if val is not None:
            values.append(val)
            original_data_map[len(values) - 1] = item

    if not values:
        return BaseToolResponse(
            status=ToolStatus.ERROR, error="No valid data points found"
        )

    stats_response = calculate_series_stats(values)
    if stats_response["status"] != "success":
        return BaseToolResponse(
            status=ToolStatus.ERROR,
            error=stats_response["error"] or "Error calculating stats",
        )

    stats = stats_response["result"]
    mean = stats["mean"]
    stdev = stats["stdev"]

    anomalies = []

    if stdev > 0:
        for i, val in enumerate(values):
            z_score = (val - mean) / stdev
            if abs(z_score) > threshold_sigma:
                anomalies.append(
                    {
                        "index": i,
                        "value": val,
                        "z_score": round(z_score, 2),
                        "original_data": original_data_map.get(i),
                        "type": "high" if z_score > 0 else "low",
                    }
                )

    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result={
            "is_anomaly_detected": len(anomalies) > 0,
            "anomalies_count": len(anomalies),
            "total_points": len(values),
            "params": {
                "threshold_sigma": threshold_sigma,
                "mean": round(mean, 2),
                "stdev": round(stdev, 2),
            },
            "anomalies": anomalies,
        },
    )


@adk_tool
def compare_metric_windows(
    baseline_points: list[float],
    target_points: list[float],
    tool_context: Any = None,
) -> BaseToolResponse:
    """Compares two windows of metric data to detect shifts.

    Args:
        baseline_points: List of baseline values.
        target_points: List of target values to compare.
        tool_context: Context object for tool execution.

    Returns:
        Comparison result stats.
    """
    if not baseline_points or not target_points:
        return BaseToolResponse(
            status=ToolStatus.ERROR, error="Missing data for comparison"
        )

    base_stats_response = calculate_series_stats(baseline_points)
    target_stats_response = calculate_series_stats(target_points)

    if (
        base_stats_response["status"] != "success"
        or target_stats_response["status"] != "success"
    ):
        return BaseToolResponse(
            status=ToolStatus.ERROR, error="Error calculating stats for comparison"
        )

    base_stats = base_stats_response["result"]
    target_stats = target_stats_response["result"]

    mean_shift = target_stats["mean"] - base_stats["mean"]
    if base_stats["mean"] != 0:
        mean_shift_pct = (mean_shift / base_stats["mean"]) * 100
    else:
        mean_shift_pct = 100.0 if mean_shift > 0 else 0.0

    return BaseToolResponse(
        status=ToolStatus.SUCCESS,
        result={
            "baseline_stats": base_stats,
            "target_stats": target_stats,
            "comparison": {
                "mean_shift": round(mean_shift, 4),
                "mean_shift_pct": round(mean_shift_pct, 2),
                "is_significant_shift": abs(mean_shift_pct)
                > 10.0,  # 10% arbitrary threshold
            },
        },
    )
