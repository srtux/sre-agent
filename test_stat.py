import math


def calculate_stats(points_sorted):
    count = len(points_sorted)
    stats = {
        "count": float(count),
        "min": points_sorted[0],
        "max": points_sorted[-1],
        "mean": sum(points_sorted) / count,
        "median": points_sorted[count // 2]
        if count % 2 != 0
        else (points_sorted[count // 2 - 1] + points_sorted[count // 2]) / 2,
    }

    if count > 1:
        variance = sum((x - stats["mean"]) ** 2 for x in points_sorted) / (count - 1)
        stats["variance"] = variance
        stats["stdev"] = math.sqrt(variance)
    else:
        stats["variance"] = 0.0
        stats["stdev"] = 0.0

    return stats
