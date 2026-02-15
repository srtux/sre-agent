### Data Sources and Telemetry Integration

AutoSRE is a thin analysis layer on top of your existing Google Cloud observability stack. It fetches telemetry data in real-time, analyzes it, and discards the raw data when the session ends. Your data never leaves your GCP project.

### Primary Data Sources

| Source | What It Provides | Access Method |
|--------|-----------------|---------------|
| **Cloud Trace** | Distributed traces, spans, latency data, error status, span attributes | Direct API (`fetch_trace`, `list_traces`) |
| **Cloud Logging** | Application logs, system logs, audit logs, platform logs | Direct API (`list_log_entries`) + BigQuery (`analyze_bigquery_log_patterns`) |
| **Cloud Monitoring** | Time-series metrics, custom metrics, GCP service metrics | Direct API (`list_time_series`) + PromQL (`query_promql`) + MCP (`mcp_list_timeseries`, `mcp_query_range`) |
| **Cloud Alerting** | Active alerts, alert policies, notification channels | Direct API (`list_alerts`, `list_alert_policies`, `get_alert`) |
| **BigQuery** | OTel trace/log tables (`_AllSpans`, `_AllLogs`), aggregate analytics | MCP (`mcp_execute_sql`) + Conversational Analytics Data Agent (`query_data_agent`) |
| **GKE / Kubernetes** | Cluster health, node conditions, pod status, HPA events, OOM events | Playbook tools (`get_gke_cluster_health`, `analyze_node_conditions`, `get_pod_restart_events`) |
| **Cloud Error Reporting** | Error groups, stack traces, error events | Direct API (`list_error_events`) |

### Optional Integrations

| Source | What It Provides | Access Method |
|--------|-----------------|---------------|
| **GitHub** | Source code, recent commits, PR creation for self-healing | `github_read_file`, `github_search_code`, `github_list_recent_commits`, `github_create_pull_request` |
| **Google Search** | Online research for unfamiliar error messages, GCP documentation | `search_google`, `fetch_web_page` (requires `GOOGLE_CUSTOM_SEARCH_API_KEY`) |
| **GCP Audit Logs** | IAM changes, resource modifications, deployment events | Via Cloud Logging with audit log filters |
| **GCP Resource Discovery** | Project listing, telemetry source discovery | `list_gcp_projects`, `discover_telemetry_sources` |

### MCP vs Direct API

AutoSRE uses two complementary access methods for telemetry:

- **Direct API** (via `tools/clients/`): Used for single-resource fetches (one trace, recent logs, real-time metrics). Low latency, no server overhead.
- **MCP (Model Context Protocol)** (via `tools/mcp/`): Used for complex aggregations, BigQuery SQL queries, heavy PromQL, and cross-table joins. Offloads computation to a dedicated server.
- **Fallback**: If MCP is unavailable, the agent automatically falls back to direct API calls via `tools/mcp/fallback.py`.

### Playbook Coverage

AutoSRE includes built-in playbooks for common GCP services:

| Service | Playbook | Capabilities |
|---------|----------|-------------|
| **GKE** | `playbooks/gke.py` | Cluster health, node conditions, pod restarts, OOM events, HPA analysis, workload health |
| **Cloud Run** | `playbooks/cloud_run.py` | Service health, revision management, traffic splitting |
| **Cloud SQL** | `playbooks/cloud_sql.py` | Connection pool monitoring, query performance |
| **Pub/Sub** | `playbooks/pubsub.py` | Subscription backlog, dead letter queues, throughput |
| **BigQuery** | `playbooks/bigquery.py` | Job performance, slot utilization |
| **GCE** | `playbooks/gce.py` | VM health, disk, network |

### Data Privacy

- **No Persistence**: The agent does not store your telemetry data. It fetches data in real-time, analyzes it within the conversation context, and discards raw data when the session ends.
- **EUC Enforcement**: With `STRICT_EUC_ENFORCEMENT=true`, the agent uses only your End-User Credentials. It can only access data you are authorized to see.
- **Project Scoping**: All queries are scoped to the GCP project specified in the `X-GCP-Project-ID` header or the session's project context.
