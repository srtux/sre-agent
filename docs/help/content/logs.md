### Log Intelligence and Pattern Analysis

AutoSRE goes beyond simple log searching. It uses AI-powered pattern extraction and clustering to find meaningful signals in millions of log lines, identifying anomalies, new error signatures, and emerging issues.

### Core Log Tools

| Tool | Purpose |
|------|---------|
| `list_log_entries` | Query Cloud Logging with filters (service, severity, time range, text search) |
| `get_logs_for_trace` | Retrieve logs correlated with a specific trace ID |
| `extract_log_patterns` | Extract recurring patterns from log entries using the Drain3 algorithm |
| `compare_log_patterns` | Compare log patterns between two time windows (e.g., before and after a release) |
| `analyze_log_anomalies` | Detect anomalous log patterns -- new errors, frequency spikes, disappearing patterns |

### BigQuery-Based Log Analysis

For large-scale log analysis across extended time windows:

| Tool | Purpose |
|------|---------|
| `analyze_bigquery_log_patterns` | Pattern extraction and analysis via BigQuery on the `_AllLogs` table |
| `mcp_execute_sql` | Run custom SQL queries against log data in BigQuery |

### How Pattern Extraction Works

AutoSRE uses the **Drain3** algorithm for log pattern extraction:

1. **Tokenization**: Log messages are parsed into tokens.
2. **Tree-Based Clustering**: Similar log messages are grouped by their structural pattern, replacing variable parts (timestamps, IDs, values) with wildcards.
3. **Pattern Identification**: Each cluster represents a distinct log pattern with a count of occurrences.
4. **Anomaly Detection**: New patterns, frequency changes, and disappeared patterns are flagged.

### Example Workflows

**Error Investigation**:
1. "Check logs for `checkout-service` from 10:00 to 11:00."
2. Agent queries logs and extracts patterns using Drain3.
3. Result: "Identified 5 rare `ConnectionTimeout` errors not present in the previous hour."
4. Agent correlates the timeout pattern with a 3x latency spike in metrics.

**Before/After Comparison**:
1. "Compare log patterns before and after the 2 PM deployment."
2. Agent extracts patterns from both time windows.
3. Highlights new error patterns that appeared post-deployment.
4. Shows patterns that disappeared (possibly removed logging or fixed issues).
5. Flags frequency changes in existing patterns (e.g., warning rate doubled).

**Trace-Correlated Logs**:
1. "Show me the logs for trace `abc123def456`."
2. Agent retrieves all log entries associated with that trace's spans.
3. Organizes logs chronologically with the span context for each entry.
4. Highlights error and warning severity entries.

### Cross-Signal Integration

Log analysis integrates with other observability signals:

- **Trace Correlation**: `correlate_logs_with_trace` maps log entries to specific trace spans, showing you exactly which log messages correspond to which parts of a request flow.
- **Metrics Correlation**: Log frequency patterns can be compared with metric time series to validate whether an increase in error logs corresponds to a metric anomaly.
- **Change Correlation**: Log patterns before and after a deployment or configuration change help identify the root cause.

### Tips

- The agent automatically filters by severity to surface errors and warnings first. You can ask for all severities if needed.
- Pattern extraction works best with structured or semi-structured logs. Fully unstructured free-text logs may produce noisier patterns.
- For large log volumes, prefer BigQuery-based analysis (`analyze_bigquery_log_patterns`) over direct API queries -- BigQuery handles millions of log entries efficiently.
- The "compare" workflow is especially powerful for deployment-related issues: compare the 30 minutes before and after a deployment to spot newly introduced errors.
