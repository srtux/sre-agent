## 2024-05-22 - Double Serialization in FastAPI
**Learning:** FastAPI's default behavior is to take the return value of an endpoint handler and serialize it to JSON. If the handler returns a `dict` that was just parsed from a JSON string (via `json.loads`), this results in redundant deserialization and re-serialization.
**Action:** When an underlying service (like `fetch_trace`) already returns a valid JSON string, skip the `json.loads()` step in the endpoint handler and return `fastapi.Response(content=json_str, media_type="application/json")` directly. This can significantly reduce latency for large payloads (e.g., 2MB trace reduced by ~40ms).

## 2025-02-18 - [Parallelize Independent API Calls]
**Learning:** `find_example_traces` was performing 3 sequential Cloud Trace API calls to gather different types of traces (slow, recent, errors). These are independent and can be parallelized using `asyncio.gather` for significant latency reduction.
**Action:** Always check for independent `await` calls in async functions and use `asyncio.gather` where possible.

## 2025-02-18 - [Single Fetch for Composite Tools]
**Learning:** Composite "Mega-Tools" like `analyze_trace_comprehensive` often call multiple granular tools sequentially. If each granular tool fetches its own data, this results in significant redundant API calls (e.g., fetching the same trace 5 times).
**Action:** Refactor granular tools to separate logic (into `_impl` functions that accept data objects) from I/O. Have the composite tool fetch data once and pass it to the `_impl` functions. This reduced API calls from 5 to 1 and latency from ~500ms to ~100ms in testing.

## 2025-02-18 - Native Math Built-ins Outperform Python Statistics Module
**Learning:** Python's `statistics` module (e.g., `statistics.mean`, `statistics.stdev`, `statistics.median`) is significantly slower (e.g., ~40-80x for mean, ~240x for median on sorted lists) than manual calculations using `sum() / len()` and index-based lookups. This overhead adds up in hot paths analyzing large volumes of telemetry data (traces, metrics).
**Action:** Prefer native math built-ins and custom calculations using `sum()` with generator expressions over the `statistics` module for speed in latency/duration data processing where extreme precision loss is negligible. When refactoring to `sum() / len()`, assign list slices or comprehensions to local variables first to avoid redundant evaluations.
