"""Fast mathematical utility functions."""

import math
from collections.abc import Iterable


def fast_mean(data: Iterable[float] | Iterable[int]) -> float:
    """Calculates mean quickly."""
    data_list = list(data) if not isinstance(data, list) else data
    return sum(data_list) / len(data_list) if data_list else 0.0


def fast_median(sorted_data: list[float] | list[int]) -> float:
    """Calculates median quickly on sorted data."""
    if not sorted_data:
        return 0.0
    n = len(sorted_data)
    mid = n // 2
    return float(
        sorted_data[mid]
        if n % 2 != 0
        else (sorted_data[mid - 1] + sorted_data[mid]) / 2.0
    )


def fast_variance(data: list[float] | list[int]) -> float:
    """Calculates variance quickly."""
    if len(data) < 2:
        return 0.0
    mean_val = sum(data) / len(data)
    return sum((x - mean_val) ** 2 for x in data) / (len(data) - 1)


def fast_stdev(data: list[float] | list[int]) -> float:
    """Calculates standard deviation quickly."""
    if len(data) < 2:
        return 0.0
    mean_val = sum(data) / len(data)
    return math.sqrt(sum((x - mean_val) ** 2 for x in data) / (len(data) - 1))
