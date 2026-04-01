"""Statistical analysis for time series data."""

import math
from typing import Any

from sre_agent.schema import BaseToolResponse, ToolStatus

from ...common.decorators import adk_tool


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

    mean_val = sum(points_sorted) / count
    var_val = (
        sum([(x - mean_val) ** 2 for x in points_sorted]) / (count - 1)
        if count > 1
        else 0.0
    )

    stats = {
        "count": float(count),
        "min": points_sorted[0],
        "max": points_sorted[-1],
        "mean": mean_val,
        "median": points_sorted[count // 2],
    }

    if count > 1:
        stats["stdev"] = math.sqrt(var_val)
        stats["variance"] = var_val
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
