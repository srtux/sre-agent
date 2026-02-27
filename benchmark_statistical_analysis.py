"""Benchmark script for statistical analysis performance."""

import random
import sys
import time
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

from sre_agent.tools.analysis.trace.statistical_analysis import (
    _analyze_critical_path_impl,
    _compute_latency_statistics_impl,
)

# Increase recursion limit to handle deep traces in recursive critical path analysis
sys.setrecursionlimit(20000)


def create_large_trace(num_spans: int = 10000) -> dict[str, Any]:
    """Create a large synthetic trace for benchmarking."""
    spans: list[dict[str, Any]] = []
    base_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc).timestamp()

    for i in range(num_spans):
        start = base_time + i * 0.01
        end = start + random.uniform(0.005, 0.5)

        span = {
            "span_id": f"span-{i}",
            "name": f"operation-{i % 10}",
            "start_time": datetime.fromtimestamp(start, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "end_time": datetime.fromtimestamp(end, tz=timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "start_time_unix": start,
            "end_time_unix": end,
            "parent_span_id": f"span-{i - 1}" if i > 0 else None,
            "duration_ms": (end - start) * 1000,
        }
        spans.append(span)

    start_time_unix = float(spans[0]["start_time_unix"])
    end_time_unix = float(spans[-1]["end_time_unix"])

    return {
        "trace_id": "bench-trace-1",
        "spans": spans,
        "duration_ms": (end_time_unix - start_time_unix) * 1000,
    }


def benchmark() -> None:
    """Run the benchmark for statistical analysis functions."""
    print("Generating synthetic trace...")
    trace = create_large_trace(
        5000
    )  # Reduced size to fit recursion limit comfortably if needed, but increased limit above
    print(f"Generated trace with {len(trace['spans'])} spans.")

    # Mock _fetch_traces_parallel since _compute_latency_statistics_impl calls it
    # We'll monkeypatch it for the benchmark
    import sre_agent.tools.analysis.trace.statistical_analysis as sa

    original_fetch = sa._fetch_traces_parallel
    sa._fetch_traces_parallel = MagicMock(return_value=[trace])

    print("\n--- Benchmarking _compute_latency_statistics_impl ---")
    start_time = time.time()
    for _ in range(10):
        _compute_latency_statistics_impl(["bench-trace-1"])
    end_time = time.time()
    avg_time = (end_time - start_time) / 10
    print(f"Average execution time: {avg_time:.6f} seconds")

    print("\n--- Benchmarking _analyze_critical_path_impl ---")
    start_time = time.time()
    for _ in range(10):
        _analyze_critical_path_impl(trace)
    end_time = time.time()
    avg_time = (end_time - start_time) / 10
    print(f"Average execution time: {avg_time:.6f} seconds")

    # Restore original function
    sa._fetch_traces_parallel = original_fetch


if __name__ == "__main__":
    benchmark()
