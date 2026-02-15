# GCP Integrations & Enhancements

## Overview

The SRE Agent provides deep integrations with Google Cloud Platform observability and infrastructure services. This document catalogs the current capabilities, the structured playbook system for service-specific troubleshooting, and the enhancement roadmap for future modules.

---

## Implemented Integrations

### Core Observability Stack

#### Cloud Trace (Distributed Tracing)

| Capability | Module | Tools |
| :--- | :--- | :--- |
| Single trace fetch | `tools/clients/trace.py` | `fetch_trace`, `fetch_trace_spans` |
| Trace listing | `tools/clients/trace.py` | `list_traces` |
| Comprehensive analysis | `tools/analysis/trace/` | `analyze_trace_comprehensive` (Mega-Tool) |
| Critical path analysis | `tools/analysis/trace/` | `analyze_critical_path` |
| Span comparison | `tools/analysis/trace/` | `compare_span_timings` |
| SRE pattern detection | `tools/analysis/trace/` | `detect_all_sre_patterns` (retry storms, cascading timeouts, connection pool issues, circular deps) |
| BigQuery aggregate analysis | `tools/mcp/`, `tools/bigquery/` | `mcp_execute_sql`, `query_data_agent` |

The `analyze_trace_comprehensive` tool is a "Mega-Tool" that combines timing, error, structure, and resiliency analysis into a single call, reducing round trips between the LLM and the tool layer.

#### Cloud Logging

| Capability | Module | Tools |
| :--- | :--- | :--- |
| Log entry listing | `tools/clients/logging.py` | `list_log_entries` |
| Pattern extraction (Drain3) | `tools/analysis/logs/` | `extract_log_patterns` |
| Log anomaly analysis | `tools/analysis/logs/` | `analyze_log_anomalies` |
| BigQuery log analysis | `tools/analysis/bigquery/` | `analyze_bigquery_log_patterns` |

Drain3 (streaming log template mining) is used for automatic pattern extraction, grouping similar log entries into templates that reveal error trends and anomalies.

#### Cloud Monitoring (Metrics & Alerting)

| Capability | Module | Tools |
| :--- | :--- | :--- |
| Time series queries | `tools/clients/monitoring.py` | `list_time_series` |
| PromQL queries | `tools/clients/monitoring.py` | `query_promql` |
| Anomaly detection | `tools/analysis/metrics/` | `detect_metric_anomalies` |
| Metric comparison | `tools/analysis/metrics/` | `compare_metric_windows` |
| Active alert listing | `tools/clients/alerting.py` | `list_alerts` |
| Alert policy listing | `tools/clients/alerting.py` | `list_alert_policies` |
| Single alert detail | `tools/clients/alerting.py` | `get_alert` |
| Proactive signals | `tools/proactive/` | `check_related_signals` |
| Resource metrics catalog | `resources/` | Metrics definitions organized by GCP service |

### SLO / Error Budget Analysis

The SLO subsystem (`sre_agent/tools/analysis/slo/burn_rate.py`) implements multi-window burn rate analysis following the Google SRE Workbook methodology.

| Capability | Tool |
| :--- | :--- |
| Multi-window burn rate (1h, 6h, 1d, 3d) | `analyze_error_budget_burn` |
| Budget exhaustion prediction | `analyze_error_budget_burn` |
| SLO breach detection | `analyze_error_budget_burn` |

### Cross-Signal Correlation

The correlation subsystem (`sre_agent/tools/analysis/correlation/`) provides multi-signal analysis:

| Capability | Tools |
| :--- | :--- |
| Cross-signal timeline | `build_cross_signal_timeline` |
| Critical path analysis | `analyze_critical_path` |
| Service dependency impact | `analyze_upstream_downstream_impact` |
| Change-incident correlation | `correlate_changes_with_incident` |
| Causal analysis | `perform_causal_analysis` |
| Historical incident matching | `find_similar_past_incidents` |
| Trace-metric correlation | `correlate_trace_with_metrics` |

### BigQuery Analytics

| Component | Module | Purpose |
| :--- | :--- | :--- |
| MCP SQL execution | `tools/mcp/` | BigQuery SQL via Model Context Protocol |
| Data agent | `tools/bigquery/` | `query_data_agent` for structured queries |
| Telemetry discovery | `tools/discovery/` | `discover_telemetry_sources` (scans for `_AllSpans`, `_AllLogs` tables) |
| MCP fallback | `tools/mcp/fallback.py` | Auto-fallback to direct API when MCP fails |

### Remediation & Postmortem

The remediation subsystem (`sre_agent/tools/analysis/remediation/`) provides:

| Tool | Purpose |
| :--- | :--- |
| `generate_remediation_suggestions` | Actionable fix recommendations based on root cause findings |
| `generate_postmortem` | Structured postmortem document generation |

### Service Dependency Graph

The `GraphService` (`sre_agent/core/graph_service.py`) builds a knowledge graph from trace data:

| Tool | Purpose |
| :--- | :--- |
| `build_service_dependency_graph` | Construct dependency graph from trace spans |
| `analyze_upstream_downstream_impact` | Blast radius analysis for failing services |
| `find_bottleneck_services` | Identify services with highest latency/error contribution |

### Sandboxed Code Execution

The sandbox subsystem (`sre_agent/tools/sandbox/`) enables safe execution of data processing code for large result sets:

| Component | Purpose |
| :--- | :--- |
| `executor.py` | Sandboxed code execution engine |
| `processors.py` | Pre-built data processing functions |
| `schemas.py` | Execution request/result schemas |

Controlled by the `SRE_AGENT_LOCAL_EXECUTION` environment variable. The `large_payload_handler.py` in `sre_agent/core/` uses the sandbox to offload processing of large tool results that would otherwise exceed context limits.

---

## GCP Service Playbooks

The playbook system (`sre_agent/tools/playbooks/`) provides structured troubleshooting guides for specific GCP services. Each playbook defines common issues, symptoms, root causes, diagnostic steps, and remediation actions -- all integrated with the agent's tool ecosystem.

### Playbook Architecture

- **`PlaybookRegistry`** (`playbooks/registry.py`): Singleton registry that indexes playbooks by ID, service name, and category. Accessed via `get_playbook_registry()`.
- **`Playbook`** schema (`playbooks/schemas.py`): Pydantic model (`frozen=True, extra="forbid"`) defining the structure.
- **`DiagnosticStep`**: Each step can specify a `tool_name` and `tool_params` for automatic invocation.
- **`TroubleshootingIssue`**: Groups symptoms, root causes, diagnostic and remediation steps for a specific issue.

### Available Playbooks

| Service | Module | Category | Key Issues Covered |
| :--- | :--- | :--- | :--- |
| **GKE** | `playbooks/gke.py` | COMPUTE | Pod CrashLoopBackOff, node pressure, HPA scaling, image pull failures |
| **Cloud Run** | `playbooks/cloud_run.py` | COMPUTE | Cold starts, memory limits, request timeouts, container crashes |
| **Cloud SQL** | `playbooks/cloud_sql.py` | DATA | Connection exhaustion, high CPU, replication lag, storage limits |
| **Pub/Sub** | `playbooks/pubsub.py` | MESSAGING | Message backlog, dead letters, delivery failures, quota limits |
| **GCE** | `playbooks/gce.py` | COMPUTE | Instance failures, disk issues, network connectivity |
| **BigQuery** | `playbooks/bigquery.py` | DATA | Slot contention, query timeouts, quota exhaustion |
| **Self-Healing** | `playbooks/self_healing.py` | OBSERVABILITY | Agent self-improvement: excessive retries, token waste, tool syntax errors, slow investigations |

### Playbook Categories

Defined in `PlaybookCategory` enum:
`COMPUTE`, `DATA`, `STORAGE`, `MESSAGING`, `AI_ML`, `OBSERVABILITY`, `SECURITY`, `NETWORKING`, `MANAGEMENT`

### Playbook Severity Levels

Defined in `PlaybookSeverity` enum:
`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, `INFO`

### Playbook Search

The `PlaybookRegistry` supports multiple search patterns:
- **By service name**: `get_by_service("gke")`
- **By category**: `get_by_category(PlaybookCategory.COMPUTE)`
- **By keyword search**: `search(query="connection pool")` (matches issue titles, descriptions, and symptoms)

---

## Client Factory Pattern

All GCP API clients follow a **singleton factory** pattern (`sre_agent/tools/clients/factory.py`) that:
- Creates thread-safe client instances
- Respects End-User Credentials (EUC) for multi-tenant access
- Provides per-request credential injection via `ToolContext`
- Falls back to Application Default Credentials (ADC) when EUC is not available

```python
from sre_agent.tools.clients.factory import get_trace_client
client = get_trace_client(tool_context)  # Thread-safe, EUC-aware
```

---

## MCP vs Direct API Decision Matrix

| Use Case | Approach | Rationale |
| :--- | :--- | :--- |
| Aggregate trace analysis | MCP (`mcp_execute_sql`) | BigQuery processes millions of spans efficiently |
| Single trace fetch | Direct (`fetch_trace`) | Low latency, no BigQuery overhead |
| Log pattern mining | MCP (`analyze_bigquery_log_patterns`) | Bulk analysis over large time windows |
| Real-time metrics | Direct (`query_promql`) | Sub-second latency needed |
| Complex joins | MCP | SQL expressiveness for multi-table analysis |

Fallback: MCP failures automatically route to direct API via `tools/mcp/fallback.py`.

---

## Environment Variables for GCP Integrations

| Variable | Purpose | Default |
| :--- | :--- | :--- |
| `GOOGLE_CLOUD_PROJECT` | Default GCP project ID | Required |
| `GOOGLE_CLOUD_LOCATION` | GCP region | `us-central1` |
| `SRE_AGENT_ID` | Agent Engine resource ID (enables remote mode + Memory Bank) | Unset |
| `STRICT_EUC_ENFORCEMENT` | Block ADC fallback (require EUC tokens) | `false` |
| `SRE_AGENT_LOCAL_EXECUTION` | Enable local sandbox execution | `false` |
| `SRE_AGENT_CONTEXT_CACHING` | Enable Vertex AI context caching (OPT-10) | `false` |
| `USE_MOCK_MCP` | Use mock MCP in tests | `false` |
| `GOOGLE_CUSTOM_SEARCH_API_KEY` | API key for Google Custom Search (research tools) | Unset |
| `GOOGLE_CUSTOM_SEARCH_ENGINE_ID` | Programmable Search Engine ID (research tools) | Unset |

---

## Enhancement Roadmap

The following table summarizes the implementation status of the originally planned enhancement modules:

| Module | Status | Description |
| :--- | :--- | :--- |
| GKE Intelligence Suite | **Implemented** (playbook + tools) | Pod/node/cluster health, HPA analysis |
| Serverless Debugging | **Implemented** (playbook) | Cloud Run cold starts, concurrency, timeouts |
| SLO/SLI Framework | **Implemented** | Multi-window burn rate, budget prediction |
| Pub/Sub Analysis | **Implemented** (playbook) | Backlog, dead letters, delivery failures |
| Remediation Suggestions | **Implemented** | Actionable recommendations, postmortem generation |
| Database Analysis | **Implemented** (playbook) | Cloud SQL connection exhaustion, CPU, replication |
| Cloud Profiler Integration | Planned | CPU/memory profiling correlation with traces |
| Enhanced Error Reporting | Planned | Deep stack trace analysis, error trends |
| Incident Lifecycle | Planned | Operations Suite incident management integration |
| Cost Correlation | Planned | Financial impact assessment for incidents |

### Planned Module: Cloud Profiler Integration
- Connect performance profiling data with trace analysis
- CPU and memory allocation hotspot identification
- Profile comparison between deployment versions
- Tools: `get_cpu_hotspots`, `correlate_profile_with_trace`, `compare_profile_versions`

### Planned Module: Enhanced Error Reporting
- Deep integration with Cloud Error Reporting
- Stack trace analysis and variation pattern detection
- Error trend tracking across deployments
- Tools: `get_error_group_details`, `analyze_error_trends`, `find_error_root_cause_frame`

### Planned Module: Incident Lifecycle
- Google Cloud Operations Suite incident management
- Incident timeline correlation with traces and logs
- Automated postmortem data collection
- Tools: `get_active_incidents`, `correlate_traces_with_incident`, `generate_postmortem_data`

### Planned Module: Cost Correlation
- Connect incidents to financial impact
- Resource waste identification and optimization
- Cost anomaly detection
- Tools: `estimate_incident_cost`, `analyze_resource_waste`, `get_cost_anomalies`

---

## Success Metrics

1. **Coverage**: Support 95% of common GCP debugging scenarios
2. **Accuracy**: Root cause identification accuracy >85%
3. **Time to Resolution**: Reduce MTTR by 50%
4. **User Satisfaction**: "Would recommend" score >4.5/5
5. **Adoption**: Used in >1000 incident investigations per month

---

*Last verified: 2026-02-15 -- Auto SRE Team*
