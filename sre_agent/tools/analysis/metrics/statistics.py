"""Statistical analysis for time series data."""

import math
from typing import Any

from sre_agent.schema import BaseToolResponse, ToolStatus

from ...common.decorators import adk_tool


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _median(sorted_values: list[float]) -> float:
    n = len(sorted_values)
    if not n:
        return 0.0
    mid = n // 2
    return (
        sorted_values[mid]
        if n % 2 != 0
        else (sorted_values[mid - 1] + sorted_values[mid]) / 2.0
    )


def _variance(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    m = _mean(values)
    return sum((x - m) ** 2 for x in values) / (n - 1)


def _stdev(values: list[float]) -> float:
    return math.sqrt(_variance(values))


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

    stats = {
        "count": float(count),
        "min": points_sorted[0],
        "max": points_sorted[-1],
        "mean": _mean(points_sorted),
        "median": _median(points_sorted),
    }

    if count > 1:
        stats["stdev"] = _stdev(points_sorted)
        stats["variance"] = _variance(points_sorted)
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
