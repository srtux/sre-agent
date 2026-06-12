import math
from collections.abc import Sequence


def _mean(values: Sequence[float | int]) -> float:
    """Computes the arithmetic mean of the values."""
    if not values:
        return 0.0
    return float(sum(values)) / len(values)


def _variance(values: Sequence[float | int], m: float | None = None) -> float:
    """Computes the sample variance of the values."""
    if len(values) < 2:
        return 0.0
    if m is None:
        m = _mean(values)
    return float(sum((x - m) ** 2 for x in values)) / (len(values) - 1)


def _stdev(values: Sequence[float | int], m: float | None = None) -> float:
    """Computes the sample standard deviation of the values."""
    if len(values) < 2:
        return 0.0
    return float(math.sqrt(_variance(values, m)))


def _median(values: Sequence[float | int]) -> float:
    """Computes the median of the values."""
    if not values:
        return 0.0
    n = len(values)
    s = sorted(values)
    mid = n // 2
    if n % 2 == 0:
        return float(s[mid - 1] + s[mid]) / 2.0
    else:
        return float(s[mid])
