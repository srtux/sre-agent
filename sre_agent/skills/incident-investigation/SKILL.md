---
name: incident-investigation
description: "Guided multi-signal incident investigation workflow. Use when investigating production incidents, outages, or service degradations that require cross-signal analysis of traces, logs, metrics, and alerts."
---

## Incident Investigation Workflow

Follow this structured workflow to investigate production incidents on Google Cloud Platform.

### Step 1: Initial Triage

1. Use `route_request` to classify the investigation scope (DIRECT, SUB_AGENT, or COUNCIL tier).
2. Gather basic context:
   - What service is affected?
   - When did the issue start?
   - What is the user-reported impact?

### Step 2: Aggregate Analysis (Fleet-Wide)

1. Use `run_aggregate_analysis` to get a fleet-wide view:
   - Identify affected services and endpoints
   - Spot error rate spikes and latency anomalies
   - Find correlated changes across the fleet
2. Use `gcp_execute_sql` for BigQuery-based trace analysis if needed.

### Step 3: Signal Collection

Collect data from all three observability pillars in parallel:

**Traces:**
- Use `fetch_trace` to retrieve specific traces
- Use `analyze_trace_comprehensive` for deep trace analysis (timing, errors, structure, critical path)
- Use `compare_span_timings` to compare healthy vs unhealthy traces

**Logs:**
- Use `list_log_entries` with appropriate filters
- Use `extract_log_patterns` to identify recurring patterns
- Use `correlate_logs_with_trace` to link logs to trace spans

**Metrics:**
- Use `query_promql` or `list_time_series` for metric queries
- Use `get_golden_signals` for the four golden signals (latency, traffic, errors, saturation)
- Use `detect_metric_anomalies` for automated anomaly detection

### Step 4: Cross-Signal Correlation

1. Use `build_cross_signal_timeline` to create a unified timeline of events
2. Use `correlate_trace_with_metrics` to link trace anomalies to metric changes
3. Use `analyze_critical_path` to identify the bottleneck service
4. Use `find_bottleneck_services` for dependency analysis

### Step 5: Root Cause Analysis

1. Use `run_deep_dive_analysis` for automated root cause synthesis
2. Check for recent changes:
   - Use `github_list_recent_commits` for code changes
   - Use `detect_trend_changes` for configuration drift
3. Use `generate_remediation_suggestions` for fix recommendations
4. Use `estimate_remediation_risk` to assess proposed changes

### Step 6: Resolution and Follow-Up

1. Document findings with `add_finding_to_memory` for future reference
2. Use `complete_investigation` to mark the investigation complete
3. Consider using the `postmortem-generation` skill for a formal postmortem

### Tips

- Start broad (aggregate) and narrow down (individual traces/logs)
- Always check for recent deployments or config changes
- Correlate across signals before concluding root cause
- Use the council investigation (`run_council_investigation`) for complex multi-service incidents
