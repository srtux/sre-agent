---
name: log-pattern-analysis
description: "Log pattern extraction and clustering workflow. Use when analyzing log volumes for recurring patterns, anomalies, error clustering, or correlating log patterns with traces and metrics."
---

## Log Pattern Analysis Workflow

Use this skill to extract, cluster, and analyze log patterns from Google Cloud Logging.

### Step 1: Collect Logs

1. Use `list_log_entries` with an appropriate filter to retrieve logs:
   - Filter by resource type: `resource.type="k8s_container"`, `resource.type="cloud_run_revision"`, etc.
   - Filter by severity: `severity>=ERROR` for error-focused analysis
   - Filter by time: use `minutes_ago` parameter for the relevant time window
   - Filter by service: include service-specific labels
2. Start with a broad filter, then narrow down based on initial findings

### Step 2: Extract Patterns

1. Use `extract_log_patterns` to identify recurring log patterns using Drain3 clustering:
   - The tool automatically groups similar log messages
   - Each pattern includes a template, frequency count, and sample messages
   - Variable parts of the messages are replaced with wildcards
2. Focus on:
   - **High-frequency error patterns**: Indicate systemic issues
   - **New patterns**: May indicate new bugs or configuration changes
   - **Patterns with increasing frequency**: Suggest growing problems

### Step 3: Analyze BigQuery Logs (For Large Scale)

1. Use `analyze_bigquery_log_patterns` for large-scale log analysis via BigQuery
   - Handles millions of log entries efficiently
   - Provides statistical breakdowns and time-series patterns
2. Use `gcp_execute_sql` for custom log queries in BigQuery

### Step 4: Correlate with Other Signals

1. Use `correlate_logs_with_trace` to link log entries to specific trace spans:
   - Match by trace ID embedded in log entries
   - Identify which log patterns correspond to which request flows
2. Use `build_cross_signal_timeline` to place log patterns alongside metrics and trace events
3. Use `detect_all_sre_patterns` to find SRE-specific patterns (retry storms, cascading failures, etc.)

### Step 5: Investigate Root Cause

1. For error log patterns:
   - Check if errors correlate with deployments (`github_list_recent_commits`)
   - Check if errors correlate with metric anomalies (`detect_metric_anomalies`)
   - Use `detect_cascading_timeout` to check for cascading failure patterns
2. For performance-related log patterns:
   - Use `detect_connection_pool_issues` for connection-related logs
   - Use `detect_retry_storm` for retry-related patterns

### Common Log Filters

```
# GKE container errors
resource.type="k8s_container" AND severity>=ERROR

# Cloud Run errors
resource.type="cloud_run_revision" AND severity>=ERROR

# Specific service logs
resource.type="k8s_container" AND resource.labels.container_name="my-service"

# HTTP errors
httpRequest.status>=500

# Custom text search
textPayload:"connection refused" OR textPayload:"timeout"
```

### Tips

- Always start with a reasonable time window (30-60 minutes) to avoid overwhelming results
- Use `extract_log_patterns` before reading individual logs to get the big picture
- Look for patterns that appeared or increased around the time of an incident
- Correlate log timestamps with trace spans for precise causality analysis
