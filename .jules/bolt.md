## 2024-05-22 - Double Serialization in FastAPI
**Learning:** FastAPI's default behavior is to take the return value of an endpoint handler and serialize it to JSON. If the handler returns a `dict` that was just parsed from a JSON string (via `json.loads`), this results in redundant deserialization and re-serialization.
**Action:** When an underlying service (like `fetch_trace`) already returns a valid JSON string, skip the `json.loads()` step in the endpoint handler and return `fastapi.Response(content=json_str, media_type="application/json")` directly. This can significantly reduce latency for large payloads (e.g., 2MB trace reduced by ~40ms).

## 2025-02-18 - [Parallelize Independent API Calls]
**Learning:** `find_example_traces` was performing 3 sequential Cloud Trace API calls to gather different types of traces (slow, recent, errors). These are independent and can be parallelized using `asyncio.gather` for significant latency reduction.
**Action:** Always check for independent `await` calls in async functions and use `asyncio.gather` where possible.

## 2025-02-18 - [Single Fetch for Composite Tools]
**Learning:** Composite "Mega-Tools" like `analyze_trace_comprehensive` often call multiple granular tools sequentially. If each granular tool fetches its own data, this results in significant redundant API calls (e.g., fetching the same trace 5 times).
**Action:** Refactor granular tools to separate logic (into `_impl` functions that accept data objects) from I/O. Have the composite tool fetch data once and pass it to the `_impl` functions. This reduced API calls from 5 to 1 and latency from ~500ms to ~100ms in testing.

## 2024-05-14 - Optimize App Telemetry Health Check
**Learning:** In `get_application_health` within `sre_agent/tools/clients/app_telemetry.py`, making multiple independent `run_in_threadpool` calls sequentially inside a loop (to check logs for Cloud Run services and GKE clusters) introduces severe N+1 latency. We can optimize this by mapping each iteration to a background task using `asyncio.gather`. Also, when formatting Python after refactoring, using `zip(..., strict=True)` is mandatory to pass the `B905` rule during linting. And don't forget the frontend test dependencies like `vitest` need manual installation in this environment if they're missing before `uv run poe test-all`.
**Action:** Use `asyncio.gather` on an array of `run_in_threadpool` promises to parallelize independent external API and log requests. Ensure `strict=True` is provided to any `zip()` calls.
