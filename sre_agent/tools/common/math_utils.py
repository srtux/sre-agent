"""Native math equivalents for statistics module to improve performance.

The standard library `statistics` module is notoriously slow for basic operations
due to its overhead handling precision and different numeric types.
Using native Python math functions can be 8-10x faster.
"""

import math
from typing import Any


def _mean(values: Any) -> float:
    """Calculate the arithmetic mean of a sequence of numbers."""
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _median(values: Any) -> float:
    """Calculate the median of a sequence of numbers."""
    if not values:
        return 0.0
    n = len(values)
    s = sorted(values)
    mid = n // 2
    if n % 2 == 0:
        return float((s[mid - 1] + s[mid]) / 2.0)
    return float(s[mid])


def _variance(values: Any, m: float | None = None) -> float:
    """Calculate the sample variance of a sequence of numbers."""
    if len(values) < 2:
        return 0.0
    if m is None:
        m = _mean(values)
    return float(sum((x - m) ** 2 for x in values) / (len(values) - 1))


def _stdev(values: Any, m: float | None = None) -> float:
    """Calculate the sample standard deviation of a sequence of numbers."""
    if len(values) < 2:
        return 0.0
    return math.sqrt(_variance(values, m))
