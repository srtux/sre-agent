import math
import statistics
import time

data = list(range(100000))
data.sort()
n = len(data)

# Test statistics.mean
t0 = time.time()
for _ in range(100):
    m1 = statistics.mean(data)
t1 = time.time()
print(f"statistics.mean: {t1 - t0:.4f}s")

# Test custom mean
t0 = time.time()
for _ in range(100):
    m2 = sum(data) / n
t1 = time.time()
print(f"custom mean: {t1 - t0:.4f}s")

# Test statistics.median
t0 = time.time()
for _ in range(100):
    med1 = statistics.median(data)
t1 = time.time()
print(f"statistics.median: {t1 - t0:.4f}s")

# Test custom median
t0 = time.time()
for _ in range(100):
    mid = n // 2
    med2 = (data[mid] + data[mid - 1]) / 2 if n % 2 == 0 else data[mid]
t1 = time.time()
print(f"custom median: {t1 - t0:.4f}s")

# Test statistics.variance & stdev
t0 = time.time()
for _ in range(100):
    v1 = statistics.variance(data)
    s1 = statistics.stdev(data)
t1 = time.time()
print(f"statistics.variance/stdev: {t1 - t0:.4f}s")

# Test custom variance & stdev
t0 = time.time()
for _ in range(100):
    mean_val = sum(data) / n
    v2 = sum((x - mean_val) ** 2 for x in data) / (n - 1)
    s2 = math.sqrt(v2)
t1 = time.time()
print(f"custom variance/stdev (generator): {t1 - t0:.4f}s")

t0 = time.time()
for _ in range(100):
    mean_val = sum(data) / n
    v2 = sum([(x - mean_val) ** 2 for x in data]) / (n - 1)
    s2 = math.sqrt(v2)
t1 = time.time()
print(f"custom variance/stdev (list comp): {t1 - t0:.4f}s")
