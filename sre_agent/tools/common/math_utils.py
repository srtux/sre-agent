import math
from typing import Any


def _mean(values: Any) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _variance(values: Any) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    return float(sum((x - m) ** 2 for x in values) / (len(values) - 1))


def _stdev(values: Any) -> float:
    if len(values) < 2:
        return 0.0
    return float(math.sqrt(_variance(values)))


def _median(values: Any) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2 == 0:
        return float((s[mid - 1] + s[mid]) / 2)
    return float(s[mid])
