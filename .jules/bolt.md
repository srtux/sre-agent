## 2024-05-22 - Double Serialization in FastAPI
**Learning:** FastAPI's default behavior is to take the return value of an endpoint handler and serialize it to JSON. If the handler returns a `dict` that was just parsed from a JSON string (via `json.loads`), this results in redundant deserialization and re-serialization.
**Action:** When an underlying service (like `fetch_trace`) already returns a valid JSON string, skip the `json.loads()` step in the endpoint handler and return `fastapi.Response(content=json_str, media_type="application/json")` directly. This can significantly reduce latency for large payloads (e.g., 2MB trace reduced by ~40ms).

## 2025-02-18 - [Parallelize Independent API Calls]
**Learning:** `find_example_traces` was performing 3 sequential Cloud Trace API calls to gather different types of traces (slow, recent, errors). These are independent and can be parallelized using `asyncio.gather` for significant latency reduction.
**Action:** Always check for independent `await` calls in async functions and use `asyncio.gather` where possible.

## 2025-02-18 - [Single Fetch for Composite Tools]
**Learning:** Composite "Mega-Tools" like `analyze_trace_comprehensive` often call multiple granular tools sequentially. If each granular tool fetches its own data, this results in significant redundant API calls (e.g., fetching the same trace 5 times).
**Action:** Refactor granular tools to separate logic (into `_impl` functions that accept data objects) from I/O. Have the composite tool fetch data once and pass it to the `_impl` functions. This reduced API calls from 5 to 1 and latency from ~500ms to ~100ms in testing.

## 2025-05-06 - [Native Math Operations over Statistics Module]
**Learning:** Python's `statistics` module (e.g., `statistics.mean`, `statistics.median`, `statistics.stdev`, `statistics.variance`) tracks internal exactness and is significantly slower (~60-80x for mean, ~100x+ for median/stdev/variance) compared to using standard library equivalents like `sum() / len()`, inline index division, and `math.sqrt()`. For hot paths or large latency distribution data lists, `statistics` presents a noticeable bottleneck.
**Action:** Always prefer native math built-ins and custom list operations for metrics processing where extreme precision isn't necessary. Replace `statistics.mean(x)` with `sum(x) / len(x)`, `statistics.median(x)` with `x[len(x)//2] if len(x)%2!=0 else (x[len(x)//2 - 1] + x[len(x)//2]) / 2.0`, and manually compute standard deviations using `math.sqrt(sum((v-m)**2) / (n-1))`.
