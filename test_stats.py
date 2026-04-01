import math
import random
import statistics
import time

data = [random.random() * 100 for _ in range(10000)]
data.sort()

start = time.time()
for _ in range(100):
    m = statistics.mean(data)
    med = statistics.median(data)
    if len(data) > 1:
        stdev = statistics.stdev(data)
        var = statistics.variance(data)
end = time.time()
print(f"statistics module: {end - start:.4f}s")

start = time.time()
for _ in range(100):
    n = len(data)
    m = sum(data) / n
    med = data[n // 2]
    if n > 1:
        var = sum([(x - m) ** 2 for x in data]) / (n - 1)
        stdev = math.sqrt(var)
end = time.time()
print(f"native: {end - start:.4f}s")
