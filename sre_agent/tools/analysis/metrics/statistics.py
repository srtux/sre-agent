"""Statistical analysis for time series data."""

from typing import Any

from sre_agent.schema import BaseToolResponse, ToolStatus

from ...common.decorators import adk_tool
from ...common.stats_utils import calculate_stats


@adk_tool
def calculate_series_stats(
    points: list[float], tool_context: Any = None
) -> BaseToolResponse:
    """Calculates statistical metrics for a list of data points.

    Args:
        points: List of numerical values.
        tool_context: Context object for tool execution.

    Returns:
        Statistical metrics in BaseToolResponse.
    """
    if not points:
        return BaseToolResponse(status=ToolStatus.SUCCESS, result={})

    points_sorted = sorted(points)
    count = len(points_sorted)

    mean, median, stdev, variance = calculate_stats(points_sorted)
    stats = {
        "count": float(count),
        "min": points_sorted[0],
        "max": points_sorted[-1],
        "mean": mean,
        "median": median,
    }

    if count > 1:
        stats["stdev"] = stdev
        stats["variance"] = variance
        stats["p90"] = points_sorted[int(count * 0.9)]
        stats["p95"] = points_sorted[int(count * 0.95)]
        stats["p99"] = points_sorted[int(count * 0.99)]
    else:
        stats["stdev"] = 0.0
        stats["variance"] = 0.0
        stats["p90"] = points_sorted[0]
        stats["p95"] = points_sorted[0]
        stats["p99"] = points_sorted[0]

    return BaseToolResponse(status=ToolStatus.SUCCESS, result=stats)
