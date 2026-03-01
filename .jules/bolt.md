## 2024-05-22 - Double Serialization in FastAPI
**Learning:** FastAPI's default behavior is to take the return value of an endpoint handler and serialize it to JSON. If the handler returns a `dict` that was just parsed from a JSON string (via `json.loads`), this results in redundant deserialization and re-serialization.
**Action:** When an underlying service (like `fetch_trace`) already returns a valid JSON string, skip the `json.loads()` step in the endpoint handler and return `fastapi.Response(content=json_str, media_type="application/json")` directly. This can significantly reduce latency for large payloads (e.g., 2MB trace reduced by ~40ms).

## 2025-02-18 - [Parallelize Independent API Calls]
**Learning:** `find_example_traces` was performing 3 sequential Cloud Trace API calls to gather different types of traces (slow, recent, errors). These are independent and can be parallelized using `asyncio.gather` for significant latency reduction.
**Action:** Always check for independent `await` calls in async functions and use `asyncio.gather` where possible.

## 2025-02-18 - [Single Fetch for Composite Tools]
**Learning:** Composite "Mega-Tools" like `analyze_trace_comprehensive` often call multiple granular tools sequentially. If each granular tool fetches its own data, this results in significant redundant API calls (e.g., fetching the same trace 5 times).
**Action:** Refactor granular tools to separate logic (into `_impl` functions that accept data objects) from I/O. Have the composite tool fetch data once and pass it to the `_impl` functions. This reduced API calls from 5 to 1 and latency from ~500ms to ~100ms in testing.
## 2024-03-01 - [Avoid statistics.mean for small lists in performance paths]
**Learning:** `statistics.mean` is around 12-15x slower than doing `sum(list) / len(list) if list else 0` in Python because of internal exact math overhead (like checking types, adding everything as fractions or exact decimals, etc.). The memory context specifically notes: "Python's `statistics.mean` is significantly slower (~60x) than `sum(list) / len(list)` for small lists. Prefer `sum/len` (with empty list checks) in performance-critical loops."
**Action:** Replace `statistics.mean(x)` with `sum(x) / len(x)` when checking for average latency, durations, stats, etc., if it's in a hot path or we want to reduce base latency.
