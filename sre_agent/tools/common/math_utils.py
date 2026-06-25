import math
from collections.abc import Sequence


def _mean(values: Sequence[float | int]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _variance(values: Sequence[float | int]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean_val = _mean(values)
    return sum((x - mean_val) ** 2 for x in values) / (n - 1)


def _stdev(values: Sequence[float | int]) -> float:
    return math.sqrt(_variance(values))


def _median(values: Sequence[float | int]) -> float:
    n = len(values)
    if n == 0:
        return 0.0
    sorted_values = sorted(values)
    mid = n // 2
    if n % 2 == 0:
        return float((sorted_values[mid - 1] + sorted_values[mid]) / 2)
    return float(sorted_values[mid])
