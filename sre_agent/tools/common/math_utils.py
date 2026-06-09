import math
from collections.abc import Sequence


def _mean(values: Sequence[float | int]) -> float:
    """Calculates the mean of a sequence using native math operations for better performance."""
    return float(sum(values) / len(values)) if values else 0.0


def _median(values: Sequence[float | int]) -> float:
    """Calculates the median of a sorted sequence using native math operations."""
    if not values:
        return 0.0
    n = len(values)
    mid = n // 2
    if n % 2 == 0:
        return float((values[mid - 1] + values[mid]) / 2.0)
    else:
        return float(values[mid])


def _variance(values: Sequence[float | int]) -> float:
    """Calculates the sample variance using native math operations."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = _mean(values)
    return float(sum((x - mean) ** 2 for x in values) / (n - 1))


def _stdev(values: Sequence[float | int]) -> float:
    """Calculates the sample standard deviation using native math operations."""
    return float(math.sqrt(_variance(values)))
