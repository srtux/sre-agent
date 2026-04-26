1. **Optimize `sre_agent/tools/analysis/metrics/statistics.py`**: Rewrite `calculate_series_stats` to use `sum() / len()` for mean, a custom mid-index based calculation for median, and a generator expression for variance/stdev. Remove the `import statistics` and add `import math`. Use `run_in_bash_session` to execute a python script:
```bash
cat << 'PYEOF' > update_metrics.py
import sys
with open('sre_agent/tools/analysis/metrics/statistics.py', 'r') as f:
    content = f.read()

content = content.replace("import statistics", "import math")
content = content.replace(
'''    stats = {
        "count": float(count),
        "min": points_sorted[0],
        "max": points_sorted[-1],
        "mean": statistics.mean(points_sorted),
        "median": statistics.median(points_sorted),
    }

    if count > 1:
        stats["stdev"] = statistics.stdev(points_sorted)
        stats["variance"] = statistics.variance(points_sorted)
        stats["p90"] = points_sorted[int(count * 0.9)]
        stats["p95"] = points_sorted[int(count * 0.95)]
        stats["p99"] = points_sorted[int(count * 0.99)]
    else:
        stats["stdev"] = 0.0
        stats["variance"] = 0.0''',
'''    mean = sum(points_sorted) / count
    mid = count // 2
    median = points_sorted[mid] if count % 2 != 0 else (points_sorted[mid - 1] + points_sorted[mid]) / 2.0
    stats = {
        "count": float(count),
        "min": points_sorted[0],
        "max": points_sorted[-1],
        "mean": mean,
        "median": median,
    }

    if count > 1:
        variance = sum((x - mean) ** 2 for x in points_sorted) / (count - 1)
        stats["stdev"] = math.sqrt(variance)
        stats["variance"] = variance
        stats["p90"] = points_sorted[int(count * 0.9)]
        stats["p95"] = points_sorted[int(count * 0.95)]
        stats["p99"] = points_sorted[int(count * 0.99)]
    else:
        stats["stdev"] = 0.0
        stats["variance"] = 0.0'''
)
with open('sre_agent/tools/analysis/metrics/statistics.py', 'w') as f:
    f.write(content)
PYEOF
python3 update_metrics.py
```
2. **Verify optimization of `sre_agent/tools/analysis/metrics/statistics.py`**: Read the file to ensure the edits were applied successfully and accurately.
3. **Optimize `sre_agent/tools/analysis/trace/statistical_analysis.py`**: Use `run_in_bash_session` to execute a python script:
```bash
cat << 'PYEOF' > update_trace_stats.py
import sys
with open('sre_agent/tools/analysis/trace/statistical_analysis.py', 'r') as f:
    content = f.read()
content = content.replace("import statistics", "import math")

content = content.replace(
'''    stats: dict[str, Any] = {
        "count": count,
        "min": latencies[0],
        "max": latencies[-1],
        "mean": statistics.mean(latencies),
        "median": statistics.median(latencies),
        "p90": latencies[int(count * 0.9)] if count > 0 else latencies[0],
        "p95": latencies[int(count * 0.95)] if count > 0 else latencies[0],
        "p99": latencies[int(count * 0.99)] if count > 0 else latencies[0],
    }

    if count > 1:
        stats["stdev"] = statistics.stdev(latencies)
        stats["variance"] = statistics.variance(latencies)
    else:
        stats["stdev"] = 0
        stats["variance"] = 0''',
'''    mean_lat = sum(latencies) / count
    mid_lat = count // 2
    median_lat = latencies[mid_lat] if count % 2 != 0 else (latencies[mid_lat - 1] + latencies[mid_lat]) / 2.0
    stats: dict[str, Any] = {
        "count": count,
        "min": latencies[0],
        "max": latencies[-1],
        "mean": mean_lat,
        "median": median_lat,
        "p90": latencies[int(count * 0.9)] if count > 0 else latencies[0],
        "p95": latencies[int(count * 0.95)] if count > 0 else latencies[0],
        "p99": latencies[int(count * 0.99)] if count > 0 else latencies[0],
    }

    if count > 1:
        var_lat = sum((x - mean_lat) ** 2 for x in latencies) / (count - 1)
        stats["stdev"] = math.sqrt(var_lat)
        stats["variance"] = var_lat
    else:
        stats["stdev"] = 0
        stats["variance"] = 0'''
)

content = content.replace(
'''        span_mean = statistics.mean(durs)
        per_span_stats[name] = {
            "count": c,
            "mean": span_mean,
            "min": durs[0],
            "max": durs[-1],
            "p95": durs[int(c * 0.95)] if c > 0 else durs[0],
        }
        # Calculate stdev for Z-score anomaly detection (need at least 2 samples)
        if c > 1:
            per_span_stats[name]["stdev"] = statistics.stdev(durs)
            per_span_stats[name]["variance"] = statistics.variance(durs)
        else:
            per_span_stats[name]["stdev"] = 0
            per_span_stats[name]["variance"] = 0''',
'''        span_mean = sum(durs) / c
        per_span_stats[name] = {
            "count": c,
            "mean": span_mean,
            "min": durs[0],
            "max": durs[-1],
            "p95": durs[int(c * 0.95)] if c > 0 else durs[0],
        }
        # Calculate stdev for Z-score anomaly detection (need at least 2 samples)
        if c > 1:
            var_durs = sum((x - span_mean) ** 2 for x in durs) / (c - 1)
            per_span_stats[name]["stdev"] = math.sqrt(var_durs)
            per_span_stats[name]["variance"] = var_durs
        else:
            per_span_stats[name]["stdev"] = 0
            per_span_stats[name]["variance"] = 0'''
)

content = content.replace(
    '''baseline_avg = statistics.mean(baseline_durations)''',
    '''baseline_avg = sum(baseline_durations) / len(baseline_durations)'''
)

content = content.replace(
'''        mean_dur = statistics.mean(durs)
        stdev_dur: float = statistics.stdev(durs) if len(durs) > 1 else 0.0''',
'''        mean_dur = sum(durs) / len(durs)
        stdev_dur: float = math.sqrt(sum((x - mean_dur) ** 2 for x in durs) / (len(durs) - 1)) if len(durs) > 1 else 0.0'''
)

content = content.replace(
'''        first = statistics.mean(trace_durations[: len(trace_durations) // 2])
        second = statistics.mean(trace_durations[len(trace_durations) // 2 :])''',
'''        first_slice = trace_durations[: len(trace_durations) // 2]
        second_slice = trace_durations[len(trace_durations) // 2 :]
        first = sum(first_slice) / len(first_slice)
        second = sum(second_slice) / len(second_slice)'''
)

with open('sre_agent/tools/analysis/trace/statistical_analysis.py', 'w') as f:
    f.write(content)
PYEOF
python3 update_trace_stats.py
```
4. **Verify optimization of `sre_agent/tools/analysis/trace/statistical_analysis.py`**: Read the file to ensure the edits were applied successfully and accurately.
5. **Optimize `sre_agent/tools/clients/trace.py`**: Replace `statistics.median`, `statistics.mean`, and `statistics.stdev` with fast implementations. Use `run_in_bash_session`:
```bash
cat << 'PYEOF' > update_trace_client.py
with open('sre_agent/tools/clients/trace.py', 'r') as f:
    content = f.read()
content = content.replace("import statistics", "import math")
content = content.replace(
'''            p50 = statistics.median(latencies)
            mean = statistics.mean(latencies)
            stdev = statistics.stdev(latencies) if len(latencies) > 1 else 0''',
'''            count = len(latencies)
            mid = count // 2
            p50 = latencies[mid] if count % 2 != 0 else (latencies[mid - 1] + latencies[mid]) / 2.0
            mean = sum(latencies) / count
            stdev = math.sqrt(sum((x - mean) ** 2 for x in latencies) / (count - 1)) if count > 1 else 0'''
)
with open('sre_agent/tools/clients/trace.py', 'w') as f:
    f.write(content)
PYEOF
python3 update_trace_client.py
```
6. **Verify optimization of `sre_agent/tools/clients/trace.py`**: Read the file to ensure the edits were applied successfully and accurately.
7. **Optimize `sre_agent/tools/analysis/trace/filters.py`**: Replace `statistics.mean` and `statistics.stdev` with fast implementations. Use `run_in_bash_session`:
```bash
cat << 'PYEOF' > update_filters.py
with open('sre_agent/tools/analysis/trace/filters.py', 'r') as f:
    content = f.read()
content = content.replace("import statistics", "import math")
content = content.replace(
'''        mean_latency = statistics.mean(latencies)
        std_dev_latency = statistics.stdev(latencies) if len(latencies) > 1 else 0''',
'''        count = len(latencies)
        mean_latency = sum(latencies) / count
        std_dev_latency = math.sqrt(sum((x - mean_latency) ** 2 for x in latencies) / (count - 1)) if count > 1 else 0'''
)
with open('sre_agent/tools/analysis/trace/filters.py', 'w') as f:
    f.write(content)
PYEOF
python3 update_filters.py
```
8. **Verify optimization of `sre_agent/tools/analysis/trace/filters.py`**: Read the file to ensure the edits were applied successfully and accurately.
9. **Optimize `sre_agent/tools/synthetic/demo_data_generator.py`**: Use `run_in_bash_session`:
```bash
cat << 'PYEOF' > update_synthetic.py
import re
with open('sre_agent/tools/synthetic/demo_data_generator.py', 'r') as f:
    content = f.read()

content = content.replace("import statistics", "import math")
content = re.sub(
    r'statistics\.mean\(([^)]+)\)',
    r'(sum(\1) / len(\1))',
    content
)

with open('sre_agent/tools/synthetic/demo_data_generator.py', 'w') as f:
    f.write(content)
PYEOF
python3 update_synthetic.py
```
10. **Verify optimization of `sre_agent/tools/synthetic/demo_data_generator.py`**: Read the file to ensure the edits were applied successfully and accurately.
11. **Update .jules/bolt.md**: Append the journal entry with the `statistics` module performance insight. Use `run_in_bash_session`:
```bash
cat << 'EOF' >> .jules/bolt.md

## 2025-02-18 - [Avoid the `statistics` Module in Hot Paths]
**Learning:** Python's `statistics` module (`mean`, `median`, `stdev`, `variance`) is extremely slow compared to basic math operations using `sum()` and `math.sqrt()` (often >20x slower) because it prioritizes numerical exactness over speed. This becomes a major bottleneck when calculating stats for many traces or metrics during analysis.
**Action:** Always prefer native math built-ins (`sum(l)/len(l)`, calculating variance via a generator expression) over the `statistics` module for latency/duration data processing where extreme precision loss is negligible.
