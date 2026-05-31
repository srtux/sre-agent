"""Math utility functions for performance-critical data processing."""

import math
from collections.abc import Sequence


def _mean(values: Sequence[float | int]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _median(values: Sequence[float | int]) -> float:
    if not values:
        return 0.0
    s_values = sorted(values)
    n = len(s_values)
    mid = n // 2
    if n % 2 == 0:
        return float((s_values[mid - 1] + s_values[mid]) / 2)
    return float(s_values[mid])


def _variance(values: Sequence[float | int]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    m = _mean(values)
    return float(sum((x - m) ** 2 for x in values) / (n - 1))


def _stdev(values: Sequence[float | int]) -> float:
    return float(math.sqrt(_variance(values)))
