## 2024-05-22 - Double Serialization in FastAPI
**Learning:** FastAPI's default behavior is to take the return value of an endpoint handler and serialize it to JSON. If the handler returns a `dict` that was just parsed from a JSON string (via `json.loads`), this results in redundant deserialization and re-serialization.
**Action:** When an underlying service (like `fetch_trace`) already returns a valid JSON string, skip the `json.loads()` step in the endpoint handler and return `fastapi.Response(content=json_str, media_type="application/json")` directly. This can significantly reduce latency for large payloads (e.g., 2MB trace reduced by ~40ms).

## 2025-02-18 - [Parallelize Independent API Calls]
**Learning:** `find_example_traces` was performing 3 sequential Cloud Trace API calls to gather different types of traces (slow, recent, errors). These are independent and can be parallelized using `asyncio.gather` for significant latency reduction.
**Action:** Always check for independent `await` calls in async functions and use `asyncio.gather` where possible.

## 2025-02-18 - [Single Fetch for Composite Tools]
**Learning:** Composite "Mega-Tools" like `analyze_trace_comprehensive` often call multiple granular tools sequentially. If each granular tool fetches its own data, this results in significant redundant API calls (e.g., fetching the same trace 5 times).
**Action:** Refactor granular tools to separate logic (into `_impl` functions that accept data objects) from I/O. Have the composite tool fetch data once and pass it to the `_impl` functions. This reduced API calls from 5 to 1 and latency from ~500ms to ~100ms in testing.
## 2024-05-24 - App Telemetry Data Fetching Bottleneck
**Learning:** In `sre_agent/tools/clients/app_telemetry.py`, looping over resources to fetch metric data and health logs asynchronously with sequential `await run_in_threadpool(...)` calls caused a significant N+1 performance bottleneck. Although the underlying calls are synchronous library methods being offloaded to a thread pool to avoid blocking the event loop, sequentially awaiting them nullifies the concurrency benefits.
**Action:** When executing multiple independent operations wrapped in `run_in_threadpool` within a loop (such as fetching time-series metrics or component health logs for an entire application topology), collect the coroutines into a list and await them concurrently using `asyncio.gather(*tasks)`. This eliminates the N+1 latency issue by dispatching the synchronous tasks to the thread pool concurrently.
