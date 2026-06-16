## 2024-05-22 - Double Serialization in FastAPI
**Learning:** FastAPI's default behavior is to take the return value of an endpoint handler and serialize it to JSON. If the handler returns a `dict` that was just parsed from a JSON string (via `json.loads`), this results in redundant deserialization and re-serialization.
**Action:** When an underlying service (like `fetch_trace`) already returns a valid JSON string, skip the `json.loads()` step in the endpoint handler and return `fastapi.Response(content=json_str, media_type="application/json")` directly. This can significantly reduce latency for large payloads (e.g., 2MB trace reduced by ~40ms).

## 2025-02-18 - [Parallelize Independent API Calls]
**Learning:** `find_example_traces` was performing 3 sequential Cloud Trace API calls to gather different types of traces (slow, recent, errors). These are independent and can be parallelized using `asyncio.gather` for significant latency reduction.
**Action:** Always check for independent `await` calls in async functions and use `asyncio.gather` where possible.

## 2025-02-18 - [Single Fetch for Composite Tools]
**Learning:** Composite "Mega-Tools" like `analyze_trace_comprehensive` often call multiple granular tools sequentially. If each granular tool fetches its own data, this results in significant redundant API calls (e.g., fetching the same trace 5 times).
**Action:** Refactor granular tools to separate logic (into `_impl` functions that accept data objects) from I/O. Have the composite tool fetch data once and pass it to the `_impl` functions. This reduced API calls from 5 to 1 and latency from ~500ms to ~100ms in testing.
## 2024-05-20 - Eliminating N+1 Bottlenecks in Async Topology Queries
**Learning:** Sequential `run_in_threadpool` executions inside loops (like iterating through cloud_run_services or gke_clusters) introduce severe N+1 latency bottlenecks. Since the underlying operations involve synchronous I/O blocks, running them one by one blocks the completion of the aggregate tool call unnecessarily.
**Action:** Always batch these tasks into a list and execute them concurrently using `asyncio.gather`. Also ensure we use `strict=True` on `zip()` when matching the results back to the objects to adhere to codebase style standards (B905).
