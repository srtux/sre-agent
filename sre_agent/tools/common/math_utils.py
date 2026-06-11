import math
from collections.abc import Sequence


def _mean(values: Sequence[float | int]) -> float:
    """Calculate the arithmetic mean. Much faster than statistics.mean."""
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _median(values: Sequence[float | int]) -> float:
    """Calculate the median. Faster than statistics.median."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    mid = n // 2
    if n % 2 == 0:
        return float((sorted_vals[mid - 1] + sorted_vals[mid]) / 2.0)
    return float(sorted_vals[mid])


def _variance(values: Sequence[float | int]) -> float:
    """Calculate sample variance. Faster than statistics.variance."""
    n = len(values)
    if n < 2:
        return 0.0
    m = _mean(values)
    return float(sum((x - m) ** 2 for x in values) / (n - 1))


def _stdev(values: Sequence[float | int]) -> float:
    """Calculate sample standard deviation. Faster than statistics.stdev."""
    n = len(values)
    if n < 2:
        return 0.0
    return float(math.sqrt(_variance(values)))
