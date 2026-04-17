import math
import random
import statistics
import time

data = [random.random() * 100 for _ in range(100000)]
count = len(data)

t0 = time.time()
for _ in range(10):
    m = statistics.mean(data)
    md = statistics.median(data)
    v = statistics.variance(data)
    s = statistics.stdev(data)
t1 = time.time()
print(f"statistics module: {t1 - t0:.4f}s")

t0 = time.time()
for _ in range(10):
    m = sum(data) / count
    mid = count // 2
    md = data[mid] if count % 2 != 0 else (data[mid - 1] + data[mid]) / 2
    v = sum((x - m) ** 2 for x in data) / (count - 1)
    s = math.sqrt(v)
t1 = time.time()
print(f"native: {t1 - t0:.4f}s")
