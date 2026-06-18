"""High-performance native math utilities for SRE Agent."""

import math
from collections.abc import Sequence


def _mean(values: Sequence[float | int]) -> float:
    """Calculates the arithmetic mean of a sequence."""
    if not values:
        raise ValueError("Sequence cannot be empty")
    return float(sum(values) / len(values))


def _median(values: Sequence[float | int]) -> float:
    """Calculates the median of a sequence."""
    if not values:
        raise ValueError("Sequence cannot be empty")
    n = len(values)
    # Using sorted() creates a new list, which is safer if the input isn't already sorted
    sorted_values = sorted(values)
    mid = n // 2
    if n % 2 == 0:
        return float(sorted_values[mid - 1] + sorted_values[mid]) / 2.0
    return float(sorted_values[mid])


def _variance(values: Sequence[float | int]) -> float:
    """Calculates the sample variance of a sequence."""
    n = len(values)
    if n < 2:
        raise ValueError("variance requires at least two data points")
    m = _mean(values)
    return float(sum((x - m) ** 2 for x in values) / (n - 1))


def _stdev(values: Sequence[float | int]) -> float:
    """Calculates the sample standard deviation of a sequence."""
    return float(math.sqrt(_variance(values)))
