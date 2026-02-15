### Metrics, SLOs, and Burn Rate Analysis

AutoSRE provides comprehensive metrics analysis capabilities, from real-time time-series queries to sophisticated SLO burn rate analysis following Google SRE standards.

### Core Metrics Tools

| Tool | Purpose |
|------|---------|
| `list_time_series` | Query Cloud Monitoring time-series data with filters and aggregations |
| `query_promql` | Execute PromQL queries for complex metric expressions |
| `list_metric_descriptors` | Discover available GCP metric types and their labels |
| `mcp_list_timeseries` | Query metrics via MCP (for heavier aggregations) |
| `mcp_query_range` | Execute range queries via MCP |

### Analysis Tools

| Tool | Purpose |
|------|---------|
| `detect_metric_anomalies` | Detect anomalous metric values using statistical methods |
| `detect_trend_changes` | Identify change points where metric trends shifted |
| `compare_metric_windows` | Compare metrics between a "good" and "bad" time window |
| `calculate_series_stats` | Compute statistical summaries (mean, p50, p95, p99, std dev) |
| `get_golden_signals` | Retrieve the four Golden Signals (Latency, Traffic, Errors, Saturation) for a service |

### SLO and Error Budget Analysis

AutoSRE follows Google SRE standards using **Multi-Window Burn Rate** alerting:

| Tool | Purpose |
|------|---------|
| `list_slos` | List all SLOs defined for a service |
| `get_slo_status` | Get the current compliance status of an SLO |
| `analyze_error_budget_burn` | Analyze error budget consumption rate |
| `analyze_multi_window_burn_rate` | Multi-window burn rate analysis (1h, 6h, 1d, 3d windows) |
| `predict_slo_violation` | Predict when an SLO will be violated at current burn rate |
| `correlate_incident_with_slo_impact` | Measure an incident's impact on SLO compliance |

### Burn Rate Thresholds

| Window | Burn Rate | Severity | Meaning |
|--------|-----------|----------|---------|
| 1h vs 6h | > 14.4x | Critical | Exhausts monthly budget in hours. Immediate action required. |
| 6h vs 1d | > 6.0x | High | Exhausts monthly budget in days. Urgent investigation needed. |
| 1d vs 3d | > 1.0x | Warning | Chronic consumption that threatens the month's budget. |

### Cross-Signal Correlation

| Tool | Purpose |
|------|---------|
| `correlate_trace_with_metrics` | Match trace anomalies to metric changes |
| `correlate_metrics_with_traces_via_exemplars` | Use metric exemplars to find specific trace IDs associated with metric spikes |

### Example Workflows

**SLO Burn Rate Check**:
1. "Show me the burn rate for the Payments service."
2. Agent queries multi-window burn rate (1h, 6h, 1d, 3d).
3. If the 1h burn rate exceeds 14.4x, it recommends immediate triage.
4. Agent correlates the burn with recent deployments or traffic changes.

**Metric Anomaly Detection**:
1. "Are there any metric anomalies for frontend-service in the last hour?"
2. Agent runs anomaly detection on key metrics (CPU, memory, error rate, latency).
3. Highlights deviations with statistical significance.
4. Suggests correlated traces via exemplars for deeper investigation.

**Golden Signals Dashboard**:
1. "What are the golden signals for checkout-service?"
2. Agent retrieves Latency (p50, p95, p99), Traffic (QPS), Errors (error rate %), and Saturation (CPU, memory utilization).
3. Flags any signals outside normal bounds.

### Tips

- The agent auto-discovers available metric types using `list_metric_descriptors`. You do not need to know the exact metric name.
- PromQL queries support the full PromQL syntax supported by Cloud Monitoring.
- For large metric datasets, the agent uses MCP to offload aggregation, falling back to direct API if MCP is unavailable.
- Metric exemplars bridge the gap between aggregated metrics and individual traces -- use them to find the specific requests causing a metric spike.
