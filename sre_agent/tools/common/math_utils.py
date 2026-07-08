import math
from collections.abc import Sequence


def _mean(data: Sequence[float | int]) -> float:
    if not data:
        raise ValueError("mean requires at least one data point")
    return float(sum(data)) / len(data)


def _median(data: Sequence[float | int]) -> float:
    if not data:
        raise ValueError("median requires at least one data point")
    s = sorted(data)
    n = len(s)
    mid = n // 2
    if n % 2 == 0:
        return float((s[mid - 1] + s[mid]) / 2.0)
    return float(s[mid])


def _variance(data: Sequence[float | int]) -> float:
    n = len(data)
    if n < 2:
        raise ValueError("variance requires at least two data points")
    m = _mean(data)
    return float(sum((x - m) ** 2 for x in data)) / (n - 1)


def _stdev(data: Sequence[float | int]) -> float:
    return float(math.sqrt(_variance(data)))
