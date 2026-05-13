import math
from collections.abc import Sequence


def calculate_stats(data: Sequence[float]) -> tuple[float, float, float, float]:
    """Calculate mean, median, standard deviation, and variance for a list of numbers.

    Assumes data is already sorted.
    """
    n = len(data)
    if n == 0:
        return 0.0, 0.0, 0.0, 0.0
    mean = sum(data) / n
    mid = n // 2
    median = data[mid] if n % 2 != 0 else (data[mid - 1] + data[mid]) / 2

    if n > 1:
        variance = sum((x - mean) ** 2 for x in data) / (n - 1)
        stdev = math.sqrt(variance)
    else:
        variance = 0.0
        stdev = 0.0

    return mean, median, stdev, variance
