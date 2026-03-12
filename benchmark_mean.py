import statistics
import time

data = [float(i) for i in range(1000)]

# warmup
for _ in range(100):
    statistics.mean(data)
    sum(data) / len(data)

t0 = time.perf_counter()
for _ in range(10000):
    statistics.mean(data)
t1 = time.perf_counter()

t2 = time.perf_counter()
for _ in range(10000):
    sum(data) / len(data)
t3 = time.perf_counter()

print(f"statistics.mean: {t1 - t0:.4f}s")
print(f"sum/len: {t3 - t2:.4f}s")
