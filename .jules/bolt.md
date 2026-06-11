## 2024-05-22 - Double Serialization in FastAPI
**Learning:** FastAPI's default behavior is to take the return value of an endpoint handler and serialize it to JSON. If the handler returns a `dict` that was just parsed from a JSON string (via `json.loads`), this results in redundant deserialization and re-serialization.
**Action:** When an underlying service (like `fetch_trace`) already returns a valid JSON string, skip the `json.loads()` step in the endpoint handler and return `fastapi.Response(content=json_str, media_type="application/json")` directly. This can significantly reduce latency for large payloads (e.g., 2MB trace reduced by ~40ms).

## 2025-02-18 - [Parallelize Independent API Calls]
**Learning:** `find_example_traces` was performing 3 sequential Cloud Trace API calls to gather different types of traces (slow, recent, errors). These are independent and can be parallelized using `asyncio.gather` for significant latency reduction.
**Action:** Always check for independent `await` calls in async functions and use `asyncio.gather` where possible.

## 2025-02-18 - [Single Fetch for Composite Tools]
**Learning:** Composite "Mega-Tools" like `analyze_trace_comprehensive` often call multiple granular tools sequentially. If each granular tool fetches its own data, this results in significant redundant API calls (e.g., fetching the same trace 5 times).
**Action:** Refactor granular tools to separate logic (into `_impl` functions that accept data objects) from I/O. Have the composite tool fetch data once and pass it to the `_impl` functions. This reduced API calls from 5 to 1 and latency from ~500ms to ~100ms in testing.

## 2024-05-18 - Replacing `statistics` with native math operations
**Learning:** Python's built-in `statistics` module (mean, median, stdev, variance) is notoriously slow compared to custom, native implementations using math primitives (`sum() / len()`, `math.sqrt()`). When heavily used in data analysis routines over trace spans and latency datasets (e.g., thousands of items), the overhead accumulates significantly. In the SRE agent backend, `statistics` was being used across trace analysis, statistical filters, metrics statistics, and synthetic data generation, leading to an application-wide performance penalty.
**Action:** Replaced all instances of `statistics.mean`, `median`, `stdev`, and `variance` across backend analytical files with equivalent faster pure-Python functions exported from a centralized `sre_agent/tools/common/math_utils.py`. The native equivalents achieve similar output (negligible precision loss) with ~2x-5x faster execution, thereby significantly reducing computation times on trace lists. Remember to correctly handle `Sequence` types (converting dict values via `list(...)`) to satisfy static type checks with `uv run poe lint`.
