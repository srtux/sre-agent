### Changes and Deployment Correlation

AutoSRE can correlate incidents with recent system changes to identify the most likely trigger. Change correlation is one of the most powerful root cause analysis techniques -- the majority of production incidents are caused by recent changes.

### What Changes Are Tracked

The agent scans for several categories of changes:

| Change Type | Source | Detection Method |
|-------------|--------|-----------------|
| **Deployments** | GCP Audit Logs | Filters for `UpdateService`, `Deploy`, `CreateRevision` events |
| **Configuration Changes** | GCP Audit Logs | Filters for `SetIamPolicy`, `UpdateConfig`, feature flag toggles |
| **Kubernetes Changes** | GKE Audit Logs | `RoleBinding` changes, `Deployment` updates, `ConfigMap` modifications |
| **Code Changes** | GitHub Integration | Recent commits, pull request merges, file modifications |
| **Infrastructure Changes** | GCP Audit Logs | Node pool scaling, network policy changes, quota modifications |

### Correlation Tools

| Tool | Purpose |
|------|---------|
| `correlate_changes_with_incident` | Scan for changes in a configurable window around an incident (requires project context) |
| `detect_trend_changes` | Detect change points in metric time series -- identify exactly when metrics shifted |
| `compare_time_periods` | Compare metrics between pre-change and post-change windows |
| `build_cross_signal_timeline` | Build a unified timeline of changes, alerts, metric anomalies, and log patterns |
| `github_list_recent_commits` | List recent code commits that may have introduced the issue |
| `github_search_code` | Search the codebase for patterns related to the incident |

### How Change Correlation Works

1. **Time Window**: The agent looks for events that occurred within a configurable window (typically 15--60 minutes) before the incident started.
2. **Audit Log Scanning**: GCP Audit Logs are queried for modification events in the affected project.
3. **Scoring**: Changes are scored by proximity to the incident start time and relevance to the affected service.
4. **Cross-Signal Validation**: Suspected changes are validated by checking if metric trends shifted at the same time using `detect_trend_changes`.

### GitHub Integration

When GitHub integration is configured, the agent can:

- **Inspect recent commits**: Check what code changed before the incident (`github_list_recent_commits`)
- **Read source code**: Examine specific files to understand the change (`github_read_file`)
- **Search for patterns**: Find related code patterns across the repository (`github_search_code`)
- **Create fix PRs**: For identified issues, create a pull request with the fix (`github_create_pull_request`)

### Example Workflow

1. Alert: "High Error Rate in Checkout."
2. Agent scans audit logs and finds a `RoleBinding` removal 2 minutes before the incident.
3. `detect_trend_changes` confirms the error rate change point aligns with the IAM modification.
4. `github_list_recent_commits` shows a commit titled "Clean up unused service accounts" from the same timeframe.
5. Agent concludes: "IAM RoleBinding removal at 14:58 UTC removed access for the checkout-to-payment service account, causing 403 errors."
6. Remediation: Restore the IAM policy, add a pre-deployment IAM dependency check.

### Tips

- Change correlation is most effective when GCP Audit Logs are enabled for the project.
- The agent automatically adjusts the correlation window based on the incident duration and available data.
- For recurring incidents, `find_similar_past_incidents` can check if the same type of change has caused issues before.
- Combine change correlation with `build_cross_signal_timeline` for a comprehensive "what happened when" view.
