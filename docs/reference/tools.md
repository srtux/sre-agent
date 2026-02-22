# Tools & Analysis Guide

The SRE Agent's power comes from its massive "Superpower" catalog of specialized tools. This document categorizes these capabilities and provides guidelines for extending the system.

## Tool Categories

### 1. Observability (Core Fetch)
Direct wrappers around GCP APIs for raw data retrieval.
- `fetch_trace`: Retrieve full span JSON for a trace by ID.
- `list_traces`: List traces with filtering and pagination.
- `find_example_traces`: Find example traces for comparison.
- `get_trace_by_url`: Fetch a trace using its Cloud Console URL.
- `get_current_time`: Get current time in various formats (UTC, ISO, epoch).
- `list_log_entries`: Filtered log fetching from Cloud Logging.
- `get_logs_for_trace`: Get log entries correlated with a specific trace.
- `list_error_events`: List error events from Cloud Logging.
- `list_time_series`: Raw metric retrieval from Cloud Monitoring.
- `list_metric_descriptors`: List and filter GCP metric descriptors and types.
- `query_promql`: Execute PromQL queries against Cloud Monitoring.
- `list_alerts`: List active alerts/incidents from Cloud Monitoring.
- `get_alert`: Get details of a specific alert.
- `list_alert_policies`: List alert policies from Cloud Monitoring.

### 2. SRE Analysis (The Brain)
High-level tools that perform multi-step analysis or statistical processing.
- `analyze_critical_path`: Calculates which spans determine the total duration.
- `calculate_critical_path_contribution`: Calculate each service's contribution to the critical path.
- `find_bottleneck_services`: Find services that are bottlenecks in the request path.
- `extract_log_patterns`: Clusters millions of log lines into meaningful patterns using the Drain3 algorithm.
- `compare_log_patterns`: Compare log patterns between two time periods.
- `analyze_log_anomalies`: Detect log anomalies and emerging issues.
- `detect_metric_anomalies`: Uses seasonality and z-scores to identify statistical outliers.
- `compare_metric_windows`: Compare metrics between two time windows.
- `calculate_series_stats`: Calculate statistical metrics for time series data.
- `analyze_multi_window_burn_rate`: Implements Google's multi-window alerting to distinguish between fast and slow burn rates.
- `analyze_trace_comprehensive`: Mega-tool combining validation, durations, errors, critical path, and structure analysis in a single call.

### 3. Trace Analysis (Deep Dive)
Specialized tools for detailed trace inspection.
- `calculate_span_durations`: Calculate durations for all spans in a trace.
- `extract_errors`: Extract error information from trace spans.
- `build_call_graph`: Build a call graph from trace data.
- `summarize_trace`: Generate a summary of trace data.
- `validate_trace_quality`: Validate the quality and completeness of trace data.
- `compare_span_timings`: Compare span timings between two traces.
- `find_structural_differences`: Find structural differences between two traces.
- `analyze_trace_patterns`: Analyze trace patterns for statistical anomalies.
- `compute_latency_statistics`: Compute latency statistics for traces.
- `detect_latency_anomalies`: Detect statistical latency anomalies in traces.
- `perform_causal_analysis`: Perform causal analysis on trace data to identify root cause.
- `select_traces_from_statistical_outliers`: Select traces that are statistical outliers.
- `select_traces_manually`: Manually select traces for analysis.

### 4. SRE Pattern Detection
Detect known SRE anti-patterns in traces.
- `detect_all_sre_patterns`: Comprehensive scan for multiple SRE anti-patterns.
- `detect_retry_storm`: Identify excessive retries and exponential backoff patterns.
- `detect_cascading_timeout`: Trace timeout propagation through the call chain.
- `detect_connection_pool_issues`: Detect waits for database or HTTP connections.
- `detect_circular_dependencies`: Detect circular dependencies in the service graph.

### 5. BigQuery Fleet Analysis
Enables fleet-wide analysis by querying telemetry data exported to BigQuery.
- `analyze_aggregate_metrics`: Health overview of all services.
- `find_exemplar_traces`: Automatically separates "Fast" from "Slow" traces for comparison.
- `compare_time_periods`: Compare metrics between two time periods.
- `detect_trend_changes`: Detect trend changes in metrics over time.
- `correlate_logs_with_trace`: Correlate log entries with a specific trace via BigQuery.
- `analyze_bigquery_log_patterns`: Analyze log patterns using BigQuery for large-scale analysis.
- `query_data_agent`: Query BigQuery telemetry using the Conversational Analytics Data Agent.

### 6. Cross-Signal Correlation
The "Holy Grail" of observability -- linking different pillars.
- `correlate_metrics_with_traces_via_exemplars`: Jumps from a chart spike to the exact request that caused it.
- `correlate_trace_with_metrics`: Correlate trace data with related metrics.
- `build_cross_signal_timeline`: Build a unified timeline from multiple signal sources.
- `analyze_signal_correlation_strength`: Analyze the correlation strength between different signals.
- `correlate_changes_with_incident`: Queries GCP Audit Logs to find and rank deployments/config changes by correlation score.
- `correlate_trace_with_kubernetes`: Correlate trace data with Kubernetes events.

### 7. Dependency Analysis
Service topology and dependency mapping.
- `build_service_dependency_graph`: Build a graph of service dependencies from trace data.
- `analyze_upstream_downstream_impact`: Analyze upstream and downstream service impact.
- `find_hidden_dependencies`: Find hidden or implicit service dependencies.

### 8. SLO/SLI Monitoring
Service Level Objective tracking and analysis.
- `list_slos`: List Service Level Objectives.
- `get_slo_status`: Get current status of an SLO.
- `analyze_error_budget_burn`: Analyze error budget burn rate.
- `get_golden_signals`: Get SRE golden signals (latency, traffic, errors, saturation) for a service.
- `correlate_incident_with_slo_impact`: Correlate an incident with its SLO impact.
- `predict_slo_violation`: Predict potential SLO violations.

### 9. GKE/Kubernetes Health
Kubernetes cluster and workload monitoring.
- `get_gke_cluster_health`: Get health status of a GKE cluster.
- `analyze_node_conditions`: Analyze GKE node conditions.
- `get_pod_restart_events`: Get pod restart events from GKE.
- `analyze_hpa_events`: Analyze Horizontal Pod Autoscaler events.
- `get_container_oom_events`: Get container Out-of-Memory events.
- `get_workload_health_summary`: Get health summary of GKE workloads.

### 10. MCP Tools (Model Context Protocol)
Heavy queries routed through MCP servers for BigQuery SQL, Cloud Logging, and Cloud Monitoring.
- `mcp_execute_sql`: Execute SQL queries via MCP BigQuery server.
- `mcp_list_log_entries`: List log entries via MCP Cloud Logging server.
- `mcp_list_timeseries`: List metrics via MCP Cloud Monitoring server.
- `mcp_query_range`: Execute PromQL queries via MCP Cloud Monitoring server.

### 11. Remediation & Reporting
Moving from "What is wrong" to "How to fix it."
- `generate_remediation_suggestions`: Proposes GKE restarts, config changes, or rollback commands.
- `get_gcloud_commands`: Get ready-to-execute gcloud commands for remediation.
- `estimate_remediation_risk`: Estimate the risk level of proposed remediation actions.
- `find_similar_past_incidents`: Find similar past incidents to guide resolution.
- `generate_postmortem`: Generates a structured, blameless Markdown postmortem based on the investigation findings.
- `synthesize_report`: Generates a high-level executive summary of the investigation.

### 12. Research (Online Intelligence)
Augments the agent's knowledge with up-to-date information from the web. Results are automatically saved to memory.
- `search_google`: Search Google via Custom Search JSON API. Supports site restriction (e.g., `cloud.google.com` for GCP docs only). Requires `GOOGLE_CUSTOM_SEARCH_API_KEY` and `GOOGLE_CUSTOM_SEARCH_ENGINE_ID`.
- `fetch_web_page`: Fetch a URL and extract readable text. Automatically strips HTML (scripts, styles, navigation). Supports HTML, JSON, and plain text.

See [Online Research & Self-Healing Architecture](../concepts/online_research_and_self_healing.md) for full documentation.

### 13. Memory & Self-Improvement
Tools for the agent's learning system. See [Memory Best Practices](../concepts/memory.md).
- `search_memory`: Semantic search over past findings and patterns.
- `add_finding_to_memory`: Explicitly store a discovery or insight.
- `complete_investigation`: Mark investigation complete and learn the pattern.
- `get_recommended_investigation_strategy`: Retrieve proven tool sequences.
- `analyze_and_learn_from_traces`: Self-analyze past agent traces from BigQuery.

### 14. Agent Self-Analysis
Tools for inspecting the agent's own execution behavior.
- `list_agent_traces`: List recent agent runs from Vertex AI traces.
- `reconstruct_agent_interaction`: Rebuild the full span tree for an agent trace.
- `analyze_agent_token_usage`: Token usage breakdown by agent/model.
- `detect_agent_anti_patterns`: Find excessive retries, token waste, long chains, and redundant tool calls.

### 15. GitHub (Self-Healing)
Tools for interacting with source code repositories to fix identified root causes. Requires `GITHUB_TOKEN` and `GITHUB_REPO` environment variables.
- `github_read_file`: Read contents of a specific file in the repository.
- `github_search_code`: Search for code patterns across the repository.
- `github_list_recent_commits`: List recent commits to identify recent changes.
- `github_create_pull_request`: Open a pull request with the applied fixes.

### 16. Sandbox Processing
Tools for processing large datasets in sandboxed environments to avoid context window limits. Automatically invoked by the Large Payload Handler when tool outputs exceed thresholds.
- `summarize_metric_descriptors_in_sandbox`: Summarize metric descriptors in a sandboxed process.
- `summarize_time_series_in_sandbox`: Summarize time series data in a sandboxed process.
- `summarize_log_entries_in_sandbox`: Summarize log entries in a sandboxed process.
- `summarize_traces_in_sandbox`: Summarize trace data in a sandboxed process.
- `execute_custom_analysis_in_sandbox`: Run custom Python analysis code in an isolated sandbox.
- `get_sandbox_status`: Check status of sandbox execution environment.

### 17. Discovery & Exploration
Tools for finding data sources and performing broad health checks.
- `discover_telemetry_sources`: Discover available telemetry sources in a project.
- `list_gcp_projects`: List accessible GCP projects for the current user.
- `explore_project_health`: Broad project health exploration across all signals (traces, logs, metrics, alerts).

### 18. Orchestration & Investigation State
Tools for managing the investigation lifecycle and routing.
- `update_investigation_state`: Update the current phase, findings, and hypotheses of an investigation.
- `get_investigation_summary`: Get a summary of current findings and investigation progress.
- `suggest_next_steps`: Suggest the next best steps based on investigation state and memory.
- `route_request`: Route a user query to the appropriate handling tier (direct tools, sub-agent, or council).
- `run_council_investigation`: Run a multi-panel council investigation with parallel analysis and debate.
- `classify_investigation_mode`: Classify user query into investigation mode (FAST/STANDARD/DEBATE).
- `run_aggregate_analysis`: Run Stage 0: Aggregate analysis using BigQuery.
- `run_triage_analysis`: Run Stage 1: Parallel triage analysis with sub-agents.
- `run_log_pattern_analysis`: Run log pattern analysis to find emergent issues.
- `run_deep_dive_analysis`: Run Stage 2: Deep dive root cause analysis.

---

## Large Payload Handler

**Location**: `sre_agent/core/large_payload_handler.py`

The Large Payload Handler automatically intercepts tool results that exceed configurable thresholds and processes them through the sandbox before they reach the LLM, preventing context window overflow while preserving data insights.

### How It Works

1. After each tool execution, the handler checks if the result exceeds `SRE_AGENT_LARGE_PAYLOAD_THRESHOLD_ITEMS` (default: 50 items) or `SRE_AGENT_LARGE_PAYLOAD_THRESHOLD_CHARS` (default: 100,000 chars).
2. If a threshold is exceeded and the originating tool maps to a known sandbox template (metrics, logs, traces, time series), the data is auto-summarized in-process via `LocalCodeExecutor` or `SandboxExecutor`.
3. For unknown data shapes, the handler returns a compact sample plus a structured prompt that tells the LLM to generate analysis code, which can then be executed via `execute_custom_analysis_in_sandbox`.

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SRE_AGENT_LARGE_PAYLOAD_ENABLED` | `true` | Enable/disable the handler |
| `SRE_AGENT_LARGE_PAYLOAD_THRESHOLD_ITEMS` | `50` | Item count threshold |
| `SRE_AGENT_LARGE_PAYLOAD_THRESHOLD_CHARS` | `100000` | Character count threshold |

---

## Tool Implementation Pattern

Every tool follows a strict implementation pattern to ensure compatibility with both the LLM and the GenUI frontend.

### 1. The `@adk_tool` Decorator
Tools must be decorated to be registered in the ADK registry. The decorator provides:
- Circuit breaker protection (`SRE_AGENT_CIRCUIT_BREAKER=true`)
- Dashboard event queuing for the frontend
- Tool output truncation and summarization callbacks
- Large payload handler integration

Use `@adk_tool(skip_summarization=True)` for tools that return structured data that should not be LLM-summarized.

### 2. Structured Return Type (`BaseToolResponse`)
Tools should return a consistent structure that includes:
- `status`: SUCCESS or ERROR.
- `result`: The actual analysis data.
- `metadata`: Used by the GenUI adapter to trigger specific widgets.
- `error`: Error message string (only when status is ERROR).
- `non_retryable`: Boolean flag indicating if the error should not be retried.

### 3. Argument Mapping
LLMs are sensitive to parameter naming and descriptions. SRE Agent tools use clear, descriptive arguments with detailed docstrings.

```python
@adk_tool
async def analyze_trace_patterns(
    trace_id: str,
    project_id: str | None = None,
    tool_context: ToolContext | None = None,
) -> str:
    """Analyze a trace for known SRE anti-patterns (e.g. Circular Dependencies)."""
    # ... logic ...
    return json.dumps({"status": "success", "result": {...}})
```

---

## Tool Configuration Registry

The SRE Agent uses a dynamic configuration registry to manage the visibility and status of tools without requiring a full redeploy.

### Master Manifest (`sre_agent/tools/config.py`)
The `TOOL_DEFINITIONS` list is the definitive source of truth for tool metadata. Every configurable tool must have a `ToolConfig` entry here, defining its:
- **Name**: The unique identifier used by the LLM.
- **Display Name**: The human-readable name shown in the UI.
- **Description**: Detailed description of what the tool does.
- **Category**: Helps the agent organize its "Superpower" catalog (see categories below).
- **Enabled Status**: Tools can be toggled on/off at runtime via the management API.
- **Testable Flag**: Whether the tool supports connectivity testing.

### Tool Categories
Categories are defined in `ToolCategory` enum:

| Category | Description |
|----------|-------------|
| `discovery` | Find data sources, projects |
| `orchestration` | High-level flow control (Stage 0, 1, 2) |
| `trace_fetch` | Retrieve raw spans/traces |
| `trace_analyze` | Process spans, critical path, patterns |
| `log_fetch` | Retrieve log entries/events |
| `log_analyze` | Pattern mining, anomaly detection |
| `metric_fetch` | Retrieve time series/exemplars |
| `metric_analyze` | Trends, stats, anomaly detection |
| `alert` | Alert policies, active incidents |
| `slo` | Service Level Objectives & status |
| `gke` | Kubernetes health & events |
| `remediation` | Suggestions, gcloud commands, risk |
| `correlation` | Cross-pillar analysis (Trace + Log + Metric) |
| `api_client` | Generic direct API tools |
| `mcp` | Generic MCP tools |
| `analysis` | Generic analysis tools |
| `memory` | Memory and context tools |
| `sandbox` | Code execution sandbox for large data processing |
| `research` | Web search and page fetching |
| `github` | Source code access and PR creation |

### Registry Synchronization
Tools must be synchronized across these locations:
1. **Exports**: `sre_agent/tools/__init__.py` (lazy import registry and `__all__`)
2. **Logic Mapping**: `sre_agent/agent.py` (`TOOL_NAME_MAP`)
3. **Availability List**: `sre_agent/agent.py` (`base_tools`)
4. **Metadata Registry**: `sre_agent/tools/config.py` (`TOOL_DEFINITIONS`)
5. **Council Tool Sets** (if used by sub-agents): `sre_agent/council/tool_registry.py`

---

## Extending the Catalog

To add a new tool:
1.  **Implement**: Write the logic in a specialized module (e.g., under `sre_agent/tools/analysis/`).
2.  **Decorate**: Use the `@adk_tool` decorator and return a `BaseToolResponse` JSON string.
3.  **Export**: Add to the `_LAZY_IMPORTS` dict in `sre_agent/tools/__init__.py`.
4.  **Register (Metadata)**: Add a `ToolConfig` entry to `TOOL_DEFINITIONS` in `sre_agent/tools/config.py`.
5.  **Register (Logic)**: Map the tool name in `TOOL_NAME_MAP` and add the function to `base_tools` in `sre_agent/agent.py`.
6.  **Council** (if applicable): Add to the relevant tool set in `sre_agent/council/tool_registry.py`.
7.  **Test**: Add tests in `tests/` (mirror source path).
8.  **Verify Sync**: Run the consistency test to ensure all registries are aligned:
    ```bash
    pytest tests/unit/sre_agent/test_tool_map_consistency.py
    ```
9.  **Lint & Test**:
    ```bash
    uv run poe lint && uv run poe test
    ```
10. **(Optional)**: Add a layout mapping in `genui_adapter.py` to enable a custom GenUI widget.

---

## Complete Tool Inventory

The following table lists all tools exported from `sre_agent/tools/__init__.py`:

| Tool Name | Module | Category |
|-----------|--------|----------|
| `analyze_agent_token_usage` | `analysis.agent_trace.tools` | analysis |
| `analyze_aggregate_metrics` | `analysis.bigquery.otel` | metric_analyze |
| `analyze_bigquery_log_patterns` | `analysis.bigquery.logs` | log_analyze |
| `analyze_critical_path` | `analysis.correlation.critical_path` | trace_analyze |
| `analyze_log_anomalies` | `analysis.logs.patterns` | log_analyze |
| `analyze_multi_window_burn_rate` | `analysis.slo.burn_rate` | analysis |
| `analyze_signal_correlation_strength` | `analysis.correlation.cross_signal` | correlation |
| `analyze_trace_comprehensive` | `analysis.trace_comprehensive` | trace_analyze |
| `analyze_trace_patterns` | `analysis.trace.statistical_analysis` | analysis |
| `analyze_upstream_downstream_impact` | `analysis.correlation.dependencies` | trace_analyze |
| `build_call_graph` | `analysis.trace.analysis` | trace_analyze |
| `build_cross_signal_timeline` | `analysis.correlation.cross_signal` | correlation |
| `build_service_dependency_graph` | `analysis.correlation.dependencies` | discovery |
| `calculate_critical_path_contribution` | `analysis.correlation.critical_path` | trace_analyze |
| `calculate_series_stats` | `analysis.metrics.statistics` | metric_analyze |
| `calculate_span_durations` | `analysis.trace.analysis` | trace_analyze |
| `compare_log_patterns` | `analysis.logs.patterns` | log_analyze |
| `compare_metric_windows` | `analysis.metrics.anomaly_detection` | metric_analyze |
| `compare_span_timings` | `analysis.trace.comparison` | trace_analyze |
| `compare_time_periods` | `analysis.bigquery.otel` | metric_analyze |
| `compute_latency_statistics` | `analysis.trace.statistical_analysis` | analysis |
| `correlate_changes_with_incident` | `analysis.correlation.change_correlation` | analysis |
| `correlate_incident_with_slo_impact` | `clients.slo` | slo |
| `correlate_logs_with_trace` | `analysis.bigquery.otel` | correlation |
| `correlate_metrics_with_traces_via_exemplars` | `analysis.correlation.cross_signal` | correlation |
| `correlate_trace_with_kubernetes` | `clients.gke` | correlation |
| `correlate_trace_with_metrics` | `analysis.correlation.cross_signal` | correlation |
| `detect_agent_anti_patterns` | `analysis.agent_trace.tools` | analysis |
| `detect_all_sre_patterns` | `analysis.trace.patterns` | trace_analyze |
| `detect_cascading_timeout` | `analysis.trace.patterns` | trace_analyze |
| `detect_circular_dependencies` | `analysis.correlation.dependencies` | trace_analyze |
| `detect_connection_pool_issues` | `analysis.trace.patterns` | trace_analyze |
| `detect_latency_anomalies` | `analysis.trace.statistical_analysis` | trace_analyze |
| `detect_metric_anomalies` | `analysis.metrics.anomaly_detection` | metric_analyze |
| `detect_retry_storm` | `analysis.trace.patterns` | trace_analyze |
| `detect_trend_changes` | `analysis.bigquery.otel` | metric_analyze |
| `discover_telemetry_sources` | `discovery.discovery_tool` | discovery |
| `estimate_remediation_risk` | `analysis.remediation.suggestions` | remediation |
| `execute_custom_analysis_in_sandbox` | `sandbox` | sandbox |
| `explore_project_health` | `exploration` | discovery |
| `extract_errors` | `analysis.trace.analysis` | trace_analyze |
| `extract_log_patterns` | `analysis.logs.patterns` | log_analyze |
| `fetch_trace` | `clients.trace` | trace_fetch |
| `fetch_web_page` | `research` | research |
| `find_bottleneck_services` | `analysis.correlation.critical_path` | trace_analyze |
| `find_example_traces` | `clients.trace` | api_client |
| `find_exemplar_traces` | `analysis.bigquery.otel` | trace_fetch |
| `find_hidden_dependencies` | `analysis.correlation.dependencies` | trace_analyze |
| `find_similar_past_incidents` | `analysis.remediation.suggestions` | remediation |
| `find_structural_differences` | `analysis.trace.comparison` | trace_analyze |
| `generate_postmortem` | `analysis.remediation.postmortem` | remediation |
| `generate_remediation_suggestions` | `analysis.remediation.suggestions` | remediation |
| `get_alert` | `clients.alerts` | api_client |
| `get_container_oom_events` | `clients.gke` | gke |
| `get_current_time` | `clients.trace` | api_client |
| `get_gcloud_commands` | `analysis.remediation.suggestions` | remediation |
| `get_gke_cluster_health` | `clients.gke` | gke |
| `get_golden_signals` | `clients.slo` | slo |
| `get_investigation_summary` | `investigation` | orchestration |
| `get_logs_for_trace` | `clients.logging` | log_fetch |
| `get_pod_restart_events` | `clients.gke` | gke |
| `get_sandbox_status` | `sandbox` | sandbox |
| `get_slo_status` | `clients.slo` | slo |
| `get_trace_by_url` | `clients.trace` | api_client |
| `get_workload_health_summary` | `clients.gke` | gke |
| `github_create_pull_request` | `github.tools` | github |
| `github_list_recent_commits` | `github.tools` | github |
| `github_read_file` | `github.tools` | github |
| `github_search_code` | `github.tools` | github |
| `list_alert_policies` | `clients.alerts` | api_client |
| `list_alerts` | `clients.alerts` | alert |
| `list_error_events` | `clients.logging` | api_client |
| `list_gcp_projects` | `clients.gcp_projects` | discovery |
| `list_log_entries` | `clients.logging` | log_fetch |
| `list_metric_descriptors` | `clients.monitoring` | metric_fetch |
| `list_slos` | `clients.slo` | slo |
| `list_time_series` | `clients.monitoring` | metric_fetch |
| `list_traces` | `clients.trace` | trace_fetch |
| `mcp_execute_sql` | `mcp.gcp` | mcp |
| `mcp_list_log_entries` | `mcp.gcp` | mcp |
| `mcp_list_timeseries` | `mcp.gcp` | mcp |
| `mcp_query_range` | `mcp.gcp` | mcp |
| `perform_causal_analysis` | `analysis.trace.statistical_analysis` | trace_analyze |
| `predict_slo_violation` | `clients.slo` | slo |
| `query_data_agent` | `bigquery.ca_data_agent` | analysis |
| `query_promql` | `clients.monitoring` | metric_fetch |
| `search_google` | `research` | research |
| `search_memory` | `memory` | memory |
| `add_finding_to_memory` | `memory` | memory |
| `analyze_and_learn_from_traces` | `memory` | memory |
| `complete_investigation` | `memory` | memory |
| `get_recommended_investigation_strategy` | `memory` | memory |
| `select_traces_from_statistical_outliers` | `analysis.trace.filters` | analysis |
| `select_traces_manually` | `analysis.trace.filters` | analysis |
| `suggest_next_steps` | `proactive` | orchestration |
| `summarize_log_entries_in_sandbox` | `sandbox` | sandbox |
| `summarize_metric_descriptors_in_sandbox` | `sandbox` | sandbox |
| `summarize_time_series_in_sandbox` | `sandbox` | sandbox |
| `summarize_traces_in_sandbox` | `sandbox` | sandbox |
| `summarize_trace` | `analysis.trace.analysis` | trace_analyze |
| `synthesize_report` | `reporting` | orchestration |
| `update_investigation_state` | `investigation` | orchestration |
| `validate_trace_quality` | `analysis.trace.analysis` | trace_analyze |
| `list_agent_traces` | `analysis.agent_trace.tools` | analysis |
| `reconstruct_agent_interaction` | `analysis.agent_trace.tools` | analysis |

---
*Last verified: 2026-02-21
