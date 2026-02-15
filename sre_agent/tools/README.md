# SRE Agent Tools

This directory contains all the tools used by the SRE Agent for analyzing Google Cloud Observability data. Tools are lazy-loaded via PEP 562 `__getattr__` to avoid importing heavy dependencies at startup.

## Directory Structure

```
tools/
├── __init__.py            # Lazy-import registry (PEP 562), exports all tool symbols
├── config.py              # Tool configuration registry (ToolConfig, ToolCategory, enable/disable)
├── registry.py            # Tool registration and discovery (queryable by category/signal/keyword)
├── investigation.py       # Investigation state management (update_investigation_state, get_investigation_summary)
├── reporting.py           # Report synthesis tools (synthesize_report)
├── research.py            # Online research tools (search_google, fetch_web_page)
├── memory.py              # Memory tools (add_finding_to_memory, search_memory, analyze_and_learn_from_traces)
├── test_functions.py      # Runtime connectivity checks
│
├── analysis/              # Pure analysis modules
│   ├── trace/             #   Trace analysis, comparison, filtering, patterns, statistical analysis
│   ├── logs/              #   Log pattern extraction (Drain3), anomaly detection
│   ├── metrics/           #   Anomaly detection, statistical analysis
│   ├── slo/               #   SLO multi-window burn rate analysis
│   ├── correlation/       #   Cross-signal, critical path, dependencies, change correlation
│   ├── bigquery/          #   BigQuery-based OTel analysis, log analysis
│   ├── agent_trace/       #   Agent self-analysis (token usage, anti-patterns, interaction reconstruction)
│   ├── remediation/       #   Remediation suggestions, postmortem generation
│   ├── genui_adapter.py   #   GenUI/A2UI protocol adapter for frontend rendering
│   └── trace_comprehensive.py  # Mega-tool: consolidated trace analysis in one call
│
├── bigquery/              # BigQuery client, query builders, schemas, CA Data Agent
├── clients/               # Direct GCP API clients (singleton factory pattern)
│   ├── factory.py         #   Client factory (get_trace_client, get_monitoring_client, etc.)
│   ├── alerts.py          #   Cloud Monitoring Alerts (list_alerts, get_alert, list_alert_policies)
│   ├── app_telemetry.py   #   App telemetry client
│   ├── apphub.py          #   App Hub integration
│   ├── asset_inventory.py #   Cloud Asset Inventory
│   ├── dependency_graph.py#   Service dependency graph client
│   ├── gcp_projects.py    #   GCP project listing
│   ├── gke.py             #   GKE/Kubernetes (cluster health, pods, nodes, OOM, HPA)
│   ├── logging.py         #   Cloud Logging (log entries, error events, trace-correlated logs)
│   ├── monitoring.py      #   Cloud Monitoring (time series, PromQL, metric descriptors)
│   ├── slo.py             #   Service Level Objectives (SLOs, error budgets, golden signals)
│   └── trace.py           #   Cloud Trace (fetch, list, find examples, get_current_time)
│
├── common/                # Shared utilities
│   ├── cache.py           #   Result caching (TTL 300s)
│   ├── decorators.py      #   @adk_tool decorator (response standardization, telemetry, summarization)
│   ├── debug.py           #   Debug utilities (auth state, telemetry state, MCP auth)
│   ├── serialization.py   #   GCP JSON serialization (proto-plus types)
│   └── telemetry.py       #   OpenTelemetry setup and configuration
│
├── discovery/             # GCP resource and telemetry source discovery
├── exploration/           # Health check exploration (explore_project_health)
├── github/                # GitHub integration for self-healing
│   ├── client.py          #   GitHub API client (authenticated REST calls)
│   └── tools.py           #   @adk_tool functions: read, search, list commits, create PRs
├── mcp/                   # Model Context Protocol integrations
│   ├── gcp.py             #   BigQuery SQL, Cloud Logging, Cloud Monitoring MCP toolsets
│   ├── fallback.py        #   MCP-to-direct API fallback logic
│   └── mock_mcp.py        #   Mock MCP for testing (USE_MOCK_MCP=true)
├── playbooks/             # Runbook execution for GCP services
│   ├── registry.py        #   Playbook registry and lookup
│   ├── schemas.py         #   Playbook, DiagnosticStep, TroubleshootingIssue models
│   ├── gke.py             #   GKE troubleshooting playbook
│   ├── cloud_run.py       #   Cloud Run troubleshooting playbook
│   ├── cloud_sql.py       #   Cloud SQL troubleshooting playbook
│   ├── pubsub.py          #   Pub/Sub troubleshooting playbook
│   ├── gce.py             #   GCE troubleshooting playbook
│   ├── bigquery.py        #   BigQuery troubleshooting playbook
│   └── self_healing.py    #   Agent self-healing playbook (OODA loop: Observe > Orient > Decide > Act)
├── proactive/             # Proactive signal analysis (suggest_next_steps, related_signals)
├── sandbox/               # Sandboxed code execution for large data processing
│   ├── executor.py        #   SandboxExecutor (cloud), LocalCodeExecutor (dev), templates
│   ├── processors.py      #   Pre-built processors: metrics, logs, traces, time series, custom
│   └── schemas.py         #   Sandbox configuration and result models
└── synthetic/             # Synthetic data generation for testing
    ├── provider.py        #   Synthetic OTel data provider
    └── scenarios.py       #   Test scenario definitions
```

## Tool Categories

### 1. Trace Analysis Tools
Tools for analyzing distributed traces from Cloud Trace API and BigQuery.

| Tool | Source | Description |
|------|--------|-------------|
| `fetch_trace` | `clients/trace.py` | Retrieve a complete trace by ID |
| `list_traces` | `clients/trace.py` | List traces with filtering |
| `find_example_traces` | `clients/trace.py` | Find example traces matching criteria |
| `get_trace_by_url` | `clients/trace.py` | Parse a Cloud Trace console URL into a trace |
| `get_current_time` | `clients/trace.py` | Get current timestamp for time-range queries |
| `calculate_span_durations` | `analysis/trace/analysis.py` | Calculate timing for all spans |
| `extract_errors` | `analysis/trace/analysis.py` | Find error spans in a trace |
| `build_call_graph` | `analysis/trace/analysis.py` | Build hierarchical call tree |
| `summarize_trace` | `analysis/trace/analysis.py` | Produce a concise trace summary |
| `validate_trace_quality` | `analysis/trace/analysis.py` | Validate trace data completeness |
| `compare_span_timings` | `analysis/trace/comparison.py` | Compare timing between two traces |
| `find_structural_differences` | `analysis/trace/comparison.py` | Find structural changes between traces |
| `select_traces_from_statistical_outliers` | `analysis/trace/filters.py` | Select outlier traces from a set |
| `select_traces_manually` | `analysis/trace/filters.py` | Manual trace selection helper |
| `detect_all_sre_patterns` | `analysis/trace/patterns.py` | Detect all SRE anti-patterns (retry storms, cascading timeouts, connection pool issues) |
| `analyze_trace_patterns` | `analysis/trace/statistical_analysis.py` | Statistical trace pattern analysis |
| `compute_latency_statistics` | `analysis/trace/statistical_analysis.py` | Latency distribution statistics |
| `detect_latency_anomalies` | `analysis/trace/statistical_analysis.py` | Find latency anomalies |
| `perform_causal_analysis` | `analysis/trace/statistical_analysis.py` | Causal analysis from trace data |
| `analyze_trace_comprehensive` | `analysis/trace_comprehensive.py` | Mega-tool: full trace analysis in one call |

### 2. BigQuery Analysis Tools
Tools for fleet-wide analysis using BigQuery and OpenTelemetry data.

| Tool | Source | Description |
|------|--------|-------------|
| `analyze_aggregate_metrics` | `analysis/bigquery/otel.py` | Service-level health metrics at scale |
| `find_exemplar_traces` | `analysis/bigquery/otel.py` | Find baseline and outlier traces |
| `compare_time_periods` | `analysis/bigquery/otel.py` | Detect performance regressions |
| `detect_trend_changes` | `analysis/bigquery/otel.py` | Identify when metrics started degrading |
| `correlate_logs_with_trace` | `analysis/bigquery/otel.py` | Correlate BigQuery logs with traces |
| `analyze_bigquery_log_patterns` | `analysis/bigquery/logs.py` | Mine log patterns via BigQuery SQL |
| `query_data_agent` | `bigquery/ca_data_agent.py` | Conversational Analytics Data Agent |

### 3. Log Analysis Tools
Tools for log pattern extraction and anomaly detection.

| Tool | Source | Description |
|------|--------|-------------|
| `list_log_entries` | `clients/logging.py` | Query log entries from Cloud Logging |
| `get_logs_for_trace` | `clients/logging.py` | Get logs correlated with a trace ID |
| `list_error_events` | `clients/logging.py` | List Error Reporting events |
| `extract_log_patterns` | `analysis/logs/patterns.py` | Compress logs into patterns using Drain3 |
| `compare_log_patterns` | `analysis/logs/patterns.py` | Compare patterns between time periods |
| `analyze_log_anomalies` | `analysis/logs/patterns.py` | Find new error patterns |

### 4. Metrics Analysis Tools
Tools for time-series analysis and anomaly detection.

| Tool | Source | Description |
|------|--------|-------------|
| `list_time_series` | `clients/monitoring.py` | Query metrics via Cloud Monitoring API |
| `list_metric_descriptors` | `clients/monitoring.py` | List available metric types |
| `query_promql` | `clients/monitoring.py` | Execute PromQL queries |
| `detect_metric_anomalies` | `analysis/metrics/anomaly_detection.py` | Identify sudden spikes or drops |
| `compare_metric_windows` | `analysis/metrics/anomaly_detection.py` | Compare metric distributions |
| `calculate_series_stats` | `analysis/metrics/statistics.py` | Compute statistical summary of time series |

### 5. Alert Tools
Tools for alert triage and policy management.

| Tool | Source | Description |
|------|--------|-------------|
| `list_alerts` | `clients/alerts.py` | List active alerts |
| `get_alert` | `clients/alerts.py` | Get a specific alert by ID |
| `list_alert_policies` | `clients/alerts.py` | List alert policies |

### 6. Cross-Signal Correlation Tools
Tools for correlating data across traces, logs, and metrics.

| Tool | Source | Description |
|------|--------|-------------|
| `correlate_trace_with_metrics` | `analysis/correlation/cross_signal.py` | Overlay trace times on metric charts |
| `correlate_metrics_with_traces_via_exemplars` | `analysis/correlation/cross_signal.py` | Find traces for metric spikes via exemplars |
| `build_cross_signal_timeline` | `analysis/correlation/cross_signal.py` | Unified timeline of all signals |
| `analyze_signal_correlation_strength` | `analysis/correlation/cross_signal.py` | Measure correlation strength across signals |

### 7. Critical Path & Dependency Tools
Tools for analyzing service dependencies and bottlenecks.

| Tool | Source | Description |
|------|--------|-------------|
| `analyze_critical_path` | `analysis/correlation/critical_path.py` | Identify the latency-determining chain |
| `find_bottleneck_services` | `analysis/correlation/critical_path.py` | Find services causing delays |
| `calculate_critical_path_contribution` | `analysis/correlation/critical_path.py` | Per-service contribution to critical path |
| `build_service_dependency_graph` | `analysis/correlation/dependencies.py` | Map service relationships |
| `analyze_upstream_downstream_impact` | `analysis/correlation/dependencies.py` | Trace impact through dependency graph |
| `detect_circular_dependencies` | `analysis/correlation/dependencies.py` | Find circular service dependencies |
| `find_hidden_dependencies` | `analysis/correlation/dependencies.py` | Discover undocumented dependencies |
| `correlate_changes_with_incident` | `analysis/correlation/change_correlation.py` | Correlate deployments/changes with incidents |

### 8. SLO/SLI Tools
Tools for Service Level Objective analysis.

| Tool | Source | Description |
|------|--------|-------------|
| `list_slos` | `clients/slo.py` | List defined SLOs |
| `get_slo_status` | `clients/slo.py` | Get current compliance status |
| `analyze_error_budget_burn` | `clients/slo.py` | Calculate error budget burn rate |
| `get_golden_signals` | `clients/slo.py` | Get the 4 SRE golden signals |
| `predict_slo_violation` | `clients/slo.py` | Predict upcoming SLO violations |
| `correlate_incident_with_slo_impact` | `clients/slo.py` | Map incident to SLO impact |
| `analyze_multi_window_burn_rate` | `analysis/slo/burn_rate.py` | Multi-window burn rate analysis |

### 9. GKE/Kubernetes Tools
Tools for Kubernetes cluster and workload analysis.

| Tool | Source | Description |
|------|--------|-------------|
| `get_gke_cluster_health` | `clients/gke.py` | Cluster health overview |
| `analyze_node_conditions` | `clients/gke.py` | Check for resource pressure |
| `get_pod_restart_events` | `clients/gke.py` | Find pod crash loops |
| `get_container_oom_events` | `clients/gke.py` | Find OOMKilled containers |
| `get_workload_health_summary` | `clients/gke.py` | Workload health overview |
| `analyze_hpa_events` | `clients/gke.py` | HPA scaling event analysis |
| `correlate_trace_with_kubernetes` | `clients/gke.py` | Correlate traces with K8s events |

### 10. Remediation Tools
Tools for generating fix recommendations and postmortems.

| Tool | Source | Description |
|------|--------|-------------|
| `generate_remediation_suggestions` | `analysis/remediation/suggestions.py` | Smart fix recommendations |
| `get_gcloud_commands` | `analysis/remediation/suggestions.py` | Ready-to-run gcloud commands |
| `estimate_remediation_risk` | `analysis/remediation/suggestions.py` | Risk assessment for remediations |
| `find_similar_past_incidents` | `analysis/remediation/suggestions.py` | Find similar past incidents |
| `generate_postmortem` | `analysis/remediation/postmortem.py` | Generate structured postmortem documents |

### 11. Memory Tools
Tools for long-term context retention and learning.

| Tool | Source | Description |
|------|--------|-------------|
| `add_finding_to_memory` | `memory.py` | Save key findings to memory |
| `search_memory` | `memory.py` | Semantic search over past investigations |
| `analyze_and_learn_from_traces` | `memory.py` | Learn from agent execution traces |
| `get_recommended_investigation_strategy` | `memory.py` | Get strategy based on past learnings |
| `complete_investigation` | `memory.py` | Mark investigation as complete with learnings |

### 12. Research Tools
Tools for online research to augment agent knowledge during investigations.

| Tool | Source | Description |
|------|--------|-------------|
| `search_google` | `research.py` | Search Google via Custom Search JSON API |
| `fetch_web_page` | `research.py` | Fetch and extract text content from a web page |

Requires `GOOGLE_CUSTOM_SEARCH_API_KEY` and `GOOGLE_CUSTOM_SEARCH_ENGINE_ID` environment variables.

### 13. GitHub Self-Healing Tools
Tools for the agent to read, search, and modify its own source code on GitHub.

| Tool | Source | Description |
|------|--------|-------------|
| `github_read_file` | `github/tools.py` | Read a file from the agent's GitHub repository |
| `github_search_code` | `github/tools.py` | Search code across the repository |
| `github_list_recent_commits` | `github/tools.py` | List recent commits (for change context) |
| `github_create_pull_request` | `github/tools.py` | Create a pull request with a fix |

Used by the self-healing playbook (`playbooks/self_healing.py`) following an OODA loop pattern: Observe (trace analysis) > Orient (code research) > Decide (fix strategy) > Act (create PR).

### 14. Sandbox Execution Tools
Tools for processing large data volumes in isolated sandbox environments.

| Tool | Source | Description |
|------|--------|-------------|
| `execute_custom_analysis_in_sandbox` | `sandbox/processors.py` | Run custom Python code in sandbox |
| `get_sandbox_status` | `sandbox/processors.py` | Check sandbox availability and mode |
| `summarize_metric_descriptors_in_sandbox` | `sandbox/processors.py` | Summarize large metric descriptor lists |
| `summarize_log_entries_in_sandbox` | `sandbox/processors.py` | Summarize large log entry sets |
| `summarize_time_series_in_sandbox` | `sandbox/processors.py` | Summarize large time series data |
| `summarize_traces_in_sandbox` | `sandbox/processors.py` | Summarize large trace collections |

Supports two execution modes: Agent Engine sandbox (cloud, secure) and local execution (development via `SRE_AGENT_LOCAL_EXECUTION=true`).

### 15. Agent Self-Analysis Tools
Tools for debugging and analyzing the agent's own execution.

| Tool | Source | Description |
|------|--------|-------------|
| `list_agent_traces` | `analysis/agent_trace/tools.py` | Find recent agent execution traces |
| `reconstruct_agent_interaction` | `analysis/agent_trace/tools.py` | Get full span tree for an agent trace |
| `analyze_agent_token_usage` | `analysis/agent_trace/tools.py` | Token cost and efficiency analysis |
| `detect_agent_anti_patterns` | `analysis/agent_trace/tools.py` | Find optimization opportunities (retries, waste, loops) |

### 16. Other Tools

| Tool | Source | Description |
|------|--------|-------------|
| `discover_telemetry_sources` | `discovery/discovery_tool.py` | Find BigQuery datasets with OTel data |
| `explore_project_health` | `exploration/explore_health.py` | Health check exploration |
| `suggest_next_steps` | `proactive/related_signals.py` | Recommend next analysis steps based on phase |
| `update_investigation_state` | `investigation.py` | Update investigation phase and findings |
| `get_investigation_summary` | `investigation.py` | Get current investigation state summary |
| `synthesize_report` | `reporting.py` | Generate professional SRE investigation report |
| `list_gcp_projects` | `clients/gcp_projects.py` | List accessible GCP projects |

### 17. MCP (Model Context Protocol) Tools
MCP tools for heavy queries routed through BigQuery, Cloud Logging, and Cloud Monitoring.

| Tool | Source | Description |
|------|--------|-------------|
| `mcp_execute_sql` | `mcp/gcp.py` | Execute BigQuery SQL queries |
| `mcp_list_log_entries` | `mcp/gcp.py` | Query Cloud Logging via MCP |
| `mcp_list_timeseries` | `mcp/gcp.py` | Query Cloud Monitoring time series via MCP |
| `mcp_query_range` | `mcp/gcp.py` | PromQL range queries via MCP |

MCP tools have automatic fallback to direct API clients via `mcp/fallback.py`.

## Creating New Tools

### Using the @adk_tool Decorator

All tools must use the `@adk_tool` decorator from `tools.common.decorators`:

```python
from sre_agent.tools.common.decorators import adk_tool

@adk_tool
async def my_new_tool(
    param1: str,
    param2: int = 10,
    project_id: str | None = None,
    tool_context: Any = None,
) -> str:
    """Tool description for the LLM.

    Args:
        param1: Description of param1.
        param2: Description of param2 (default: 10).
        project_id: GCP project ID (optional, uses env if not provided).
        tool_context: Context object for tool execution.

    Returns:
        JSON string containing the analysis results.
    """
    return json.dumps({"status": "success", "result": {...}})
```

Use `@adk_tool(skip_summarization=True)` for tools that return structured data that should not be summarized by the model (e.g., GitHub tools, sandbox tools).

### Tool Registration Checklist

1. Create function in appropriate subdirectory under `sre_agent/tools/`.
2. Add `@adk_tool` decorator with clear docstring.
3. Add to `_LAZY_IMPORTS` in `sre_agent/tools/__init__.py`.
4. Add to `base_tools` list in `sre_agent/agent.py`.
5. Add to `TOOL_NAME_MAP` in `sre_agent/agent.py`.
6. Add `ToolConfig` entry in `sre_agent/tools/config.py`.
7. If used by sub-agents/panels: add to relevant tool set in `council/tool_registry.py`.
8. Add test in `tests/` (mirror source path).
9. Run `uv run poe lint && uv run poe test`.

### Tool Guidelines

1. **Docstrings**: Include detailed docstrings as they are shown to the LLM.
2. **Type hints**: Use proper type hints for all parameters and return values.
3. **Error handling**: Return structured error responses via `BaseToolResponse` rather than raising exceptions.
4. **Project ID**: Accept optional `project_id` and fall back to environment variable.
5. **Async**: All tool functions must be async for I/O-bound operations.
6. **Return type**: Return `str` (JSON) or `BaseToolResponse`. All responses follow the `BaseToolResponse` schema.

## Configuration

Tools can be enabled/disabled via the `ToolConfigManager`. See `config.py` for details.

```python
from sre_agent.tools.config import get_tool_config_manager

manager = get_tool_config_manager()
enabled_tools = manager.get_enabled_tools()
```

The `registry.py` module provides a queryable layer on top of tool configurations, supporting discovery by signal type, category, or keyword.

## Testing

Runtime connectivity checks are in `test_functions.py`. To test a tool's connectivity:

```python
from sre_agent.tools.test_functions import check_fetch_trace

result = await check_fetch_trace()
print(result.status, result.message)
```

For unit tests, mock all external GCP APIs. Use `USE_MOCK_MCP=true` for MCP tool tests.
