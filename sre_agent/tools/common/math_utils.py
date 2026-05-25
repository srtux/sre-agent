import math
from typing import Any


def _mean(values: Any) -> float:
    """Computes the mean of a sequence."""
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _median(values: Any) -> float:
    """Computes the median of a sequence."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 0:
        return float((sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0)
    return float(sorted_vals[mid])


def _variance(values: Any) -> float:
    """Computes the sample variance of a sequence."""
    n = len(values)
    if n < 2:
        return 0.0
    m = sum(values) / n
    return float(sum((x - m) ** 2 for x in values) / (n - 1))


def _stdev(values: Any) -> float:
    """Computes the sample standard deviation of a sequence."""
    return float(math.sqrt(_variance(values)))
