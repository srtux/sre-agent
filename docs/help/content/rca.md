### Root Cause Analysis

AutoSRE uses a structured, multi-signal approach to diagnose the root cause of production issues. The **Root Cause Analyst** sub-agent synthesizes findings from traces, logs, metrics, and change data to answer three questions: **WHAT** happened, **WHO/WHAT** changed, and **HOW BAD** is the impact.

### The Detective Methodology

The Root Cause Analyst follows a five-step workflow:

1. **Identify Root Cause**: Use `perform_causal_analysis` to pinpoint the specific span or service responsible for the failure.
2. **Confirm with Cross-Signal Correlation**: Use `build_cross_signal_timeline` or `correlate_logs_with_trace` to validate findings across multiple telemetry signals.
3. **Detect Triggering Change**: Use `detect_trend_changes` for timing analysis, then search logs for deployment markers ("UpdateService", "Deploy") or configuration changes.
4. **Measure Blast Radius**: Use `analyze_upstream_downstream_impact` to identify all affected downstream services and quantify the impact.
5. **Suggest Remediation**: After confirming the root cause, call `generate_remediation_suggestions` and `get_gcloud_commands` for actionable fix steps.

### Available Tools

| Tool | Purpose |
|------|---------|
| `perform_causal_analysis` | Identify the causal chain from symptom to root cause |
| `build_cross_signal_timeline` | Create a unified timeline across traces, logs, and metrics |
| `correlate_logs_with_trace` | Correlate log entries with specific trace spans |
| `correlate_trace_with_metrics` | Match trace anomalies to metric changes |
| `analyze_upstream_downstream_impact` | Map blast radius across service dependencies |
| `build_service_dependency_graph` | Visualize service-to-service call relationships |
| `detect_trend_changes` | Detect when metric trends shifted (change point detection) |
| `compare_time_periods` | Compare metrics between "good" and "bad" time windows |
| `generate_remediation_suggestions` | Get prioritized fix recommendations |
| `get_gcloud_commands` | Generate ready-to-run gcloud commands for common remediations |
| `search_google` / `fetch_web_page` | Research unfamiliar error messages or GCP service quotas |

### GitHub Integration for Self-Healing

The Root Cause Analyst also has access to GitHub tools for advanced remediation:

- `github_read_file`: Inspect source code, configuration files, or Kubernetes manifests
- `github_search_code`: Search the codebase for error patterns or configuration issues
- `github_list_recent_commits`: Check for recent code changes that may have caused the incident
- `github_create_pull_request`: Create a PR with a fix (e.g., rolling back a config change)

### Output Format

The Root Cause Analyst produces a structured report:

- **Root Cause**: The specific trigger (e.g., "Deployment v2.3 caused retry storm in Service A due to removed timeout configuration")
- **Evidence**: Supporting trace IDs, log patterns, and metric data
- **Impact**: Number and names of affected services, estimated user impact
- **Recommended Actions**: Specific, prioritized remediation steps with risk assessments

### Example Workflows

**Scenario 1: Latency Spike**
1. You say: "Service API is slow."
2. Agent identifies high p99 latency via metrics, locates a bottleneck span in traces.
3. Causal analysis reveals a slow database query introduced in a recent deployment.
4. Conclusion: "Deployment v2.3.1 introduced an unindexed query on the `orders` table -- 92% confidence."
5. Remediation: Rollback to v2.3.0, add database index, verify with load test.

**Scenario 2: Error Rate Spike**
1. Alert fires: "High Error Rate in Checkout."
2. Agent correlates the error spike with a Kubernetes RoleBinding removal 2 minutes before the incident.
3. Blast radius analysis shows 3 downstream services affected.
4. Remediation: Restore the IAM policy, add a pre-deployment IAM validation check.

### Tips

- The Root Cause Analyst uses the **deep** model tier (Gemini 2.5 Pro) for higher reasoning quality during multi-signal synthesis.
- For best results, provide as much context as possible: service names, approximate timeframes, and any symptoms you have observed.
- The agent can research unfamiliar error messages using Google Search, restricted to `cloud.google.com` documentation.
