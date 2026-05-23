"""Mathematical utilities for performance-critical path."""

import math
from typing import Any


def _mean(values: Any) -> float:
    if not values:
        return 0.0
    val_list = list(values) if not isinstance(values, list) else values
    if not val_list:
        return 0.0
    return float(sum(val_list) / len(val_list))


def _median(values: Any) -> float:
    if not values:
        return 0.0
    val_list = list(values) if not isinstance(values, list) else values
    if not val_list:
        return 0.0
    n = len(val_list)
    s = sorted(val_list)
    mid = n // 2
    if n % 2 == 0:
        return float((s[mid - 1] + s[mid]) / 2.0)
    return float(s[mid])


def _variance(values: Any) -> float:
    val_list = list(values) if not isinstance(values, list) else values
    n = len(val_list)
    if n < 2:
        return 0.0
    m = sum(val_list) / n
    return float(sum((x - m) ** 2 for x in val_list) / (n - 1))


def _stdev(values: Any) -> float:
    return math.sqrt(_variance(values))
