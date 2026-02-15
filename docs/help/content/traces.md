### Distributed Trace Analysis

Traces visualize the lifecycle of a request as it flows across microservices. AutoSRE provides deep trace analysis capabilities, from fetching individual traces to detecting complex anti-patterns across your distributed system.

### Core Trace Tools

| Tool | Purpose |
|------|---------|
| `fetch_trace` | Fetch a single trace by ID |
| `list_traces` | List and filter traces (by service, status, latency threshold, time range) |
| `get_trace_by_url` | Fetch a trace from a Cloud Console URL |
| `summarize_trace` | Generate a human-readable trace summary |
| `analyze_trace_comprehensive` | All-in-one "mega-tool" combining timing, error, structure, critical path, and pattern analysis |

### Analysis Capabilities

| Tool | What It Finds |
|------|---------------|
| `analyze_critical_path` | The longest chain of sequential spans determining overall latency |
| `calculate_critical_path_contribution` | How much each service contributes to the critical path |
| `find_bottleneck_services` | Services consuming the most time or producing the most errors |
| `calculate_span_durations` | Duration breakdown for every span in a trace |
| `compute_latency_statistics` | Statistical analysis of span durations (mean, p50, p95, p99) |
| `detect_latency_anomalies` | Spans with unusual duration compared to their peers |
| `build_call_graph` | Service-to-service call graph from trace data |
| `build_service_dependency_graph` | Full service dependency map across multiple traces |

### Pattern Detection (Resiliency Anti-Patterns)

| Tool | Pattern Detected |
|------|-----------------|
| `detect_all_sre_patterns` | Comprehensive scan for all known anti-patterns |
| `detect_retry_storm` | Excessive retry loops overwhelming downstream services |
| `detect_cascading_timeout` | Timeout propagation across service boundaries |
| `detect_connection_pool_issues` | Connection pool exhaustion or leak indicators |
| `detect_circular_dependencies` | Circular service call chains that risk deadlocks |
| `find_hidden_dependencies` | Implicit dependencies not obvious from the call graph |

### Trace Comparison

| Tool | Purpose |
|------|---------|
| `compare_span_timings` | Compare timing of matching spans between two traces (healthy vs unhealthy) |
| `find_structural_differences` | Find spans present in one trace but missing in another |
| `analyze_trace_patterns` | Identify recurring patterns across multiple traces |
| `find_example_traces` | Find traces matching specific criteria for comparison |

### Cross-Signal Correlation

| Tool | Purpose |
|------|---------|
| `correlate_logs_with_trace` | Find log entries associated with a specific trace's spans |
| `correlate_trace_with_metrics` | Match trace anomalies to metric time-series changes |
| `correlate_metrics_with_traces_via_exemplars` | Use metric exemplars to find the exact traces behind a metric spike |
| `correlate_trace_with_kubernetes` | Map trace spans to Kubernetes pod/container context |

### BigQuery-Based Fleet Analysis

For large-scale trace analysis across your entire fleet:

| Tool | Purpose |
|------|---------|
| `analyze_aggregate_metrics` | Aggregate span metrics across thousands of traces in BigQuery |
| `find_exemplar_traces` | Find representative traces for specific latency percentiles |
| `compare_time_periods` | Compare trace metrics between two time windows |
| `mcp_execute_sql` | Run custom SQL queries against the `_AllSpans` BigQuery table |

### Example Workflows

**Single Trace Investigation**:
1. "Fetch trace `82e3a1b2c4d5...`"
2. Agent runs `analyze_trace_comprehensive`, identifying the critical path.
3. It highlights a specific DB call causing a 2-second delay.
4. It suggests checking the `billing-db` indexes or adding a cache.

**Fleet-Wide Latency Analysis**:
1. "Why are checkout requests slow today?"
2. Agent uses BigQuery to analyze aggregate latency across all checkout traces.
3. Identifies that p99 latency increased 3x starting at 14:00.
4. Finds exemplar traces from the spike period and analyzes their critical paths.
5. Detects a retry storm pattern in the payment service.

**Trace Comparison (Before/After Deployment)**:
1. "Compare a trace from before the deployment with one from after."
2. Agent finds example traces from both time periods.
3. Uses `compare_span_timings` to show which spans got slower.
4. Uses `find_structural_differences` to reveal new spans (e.g., added middleware).

### Tips

- You can paste a Cloud Console trace URL directly -- the agent extracts the trace ID automatically.
- The `analyze_trace_comprehensive` mega-tool is the most efficient starting point. It combines 5+ analysis steps into a single tool call.
- For traces with hundreds of spans, the agent automatically focuses on the critical path and error spans rather than listing every span.
- Trace quality validation (`validate_trace_quality`) checks for missing attributes, unlinked spans, and instrumentation gaps.
