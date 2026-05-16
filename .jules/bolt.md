## 2024-05-22 - Double Serialization in FastAPI
**Learning:** FastAPI's default behavior is to take the return value of an endpoint handler and serialize it to JSON. If the handler returns a `dict` that was just parsed from a JSON string (via `json.loads`), this results in redundant deserialization and re-serialization.
**Action:** When an underlying service (like `fetch_trace`) already returns a valid JSON string, skip the `json.loads()` step in the endpoint handler and return `fastapi.Response(content=json_str, media_type="application/json")` directly. This can significantly reduce latency for large payloads (e.g., 2MB trace reduced by ~40ms).

## 2025-02-18 - [Parallelize Independent API Calls]
**Learning:** `find_example_traces` was performing 3 sequential Cloud Trace API calls to gather different types of traces (slow, recent, errors). These are independent and can be parallelized using `asyncio.gather` for significant latency reduction.
**Action:** Always check for independent `await` calls in async functions and use `asyncio.gather` where possible.

## 2025-02-18 - [Single Fetch for Composite Tools]
**Learning:** Composite "Mega-Tools" like `analyze_trace_comprehensive` often call multiple granular tools sequentially. If each granular tool fetches its own data, this results in significant redundant API calls (e.g., fetching the same trace 5 times).
**Action:** Refactor granular tools to separate logic (into `_impl` functions that accept data objects) from I/O. Have the composite tool fetch data once and pass it to the `_impl` functions. This reduced API calls from 5 to 1 and latency from ~500ms to ~100ms in testing.

## 2024-05-23 - Python built-in statistics module overhead
**Learning:** Python's built-in `statistics` module (e.g., `mean`, `median`, `variance`, `stdev`) is optimized for mathematical exactness (often using fractions or decimals under the hood), making it extremely slow (up to 240x slower for median and 40x slower for mean) compared to native floating-point math using `sum()` and list indexing. In hot paths analyzing hundreds of trace latencies or metric points, this causes measurable CPU blocking and latency spikes.
**Action:** When calculating basic statistical metrics over lists of floating-point numbers where extreme exactness is not required (e.g., latency durations, resource metrics), use custom inline native implementations (like `sum(l) / len(l)`) or `math` module equivalents instead of importing `statistics`.
