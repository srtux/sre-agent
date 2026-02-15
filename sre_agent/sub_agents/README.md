# SRE Agent Sub-Agents

This directory contains specialized sub-agents that form the investigation pipeline used by the main SRE Agent. The sub-agents can operate both in the direct "Council of Experts" orchestration pattern and within the parallel Council of Experts architecture.

## Architecture Overview

The SRE Agent uses a multi-stage analysis pipeline where specialized sub-agents handle different aspects of investigation. Each sub-agent imports its tool set from `council/tool_registry.py` (OPT-4: single source of truth for domain tool sets).

```
┌─────────────────────────────────────────────────────────────────────┐
│  Stage 0: Aggregate Analysis (BigQuery)                              │
│  • aggregate_analyzer: Analyzes thousands of traces at scale         │
│  • Identifies trends, patterns, and selects exemplar traces          │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Stage 1: Specialized Analysis (Parallel)                            │
│  ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐  │
│  │   trace_analyst   │ │    log_analyst    │ │ metrics_analyzer  │  │
│  │ (Latency, Errors, │ │ (Patterns, BQ,   │ │ (PromQL, Anomaly, │  │
│  │  Critical Path,   │ │  Drain3)          │ │  Exemplars)       │  │
│  │  Resiliency)      │ │                   │ │                   │  │
│  └───────────────────┘ └───────────────────┘ └───────────────────┘  │
│  ┌───────────────────┐                                               │
│  │  alert_analyst    │                                               │
│  │ (Triage, Policy,  │                                               │
│  │  Severity)        │                                               │
│  └───────────────────┘                                               │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Stage 2: Deep Dive (Synthesis)                                      │
│  ┌───────────────────┐                                               │
│  │root_cause_analyst │                                               │
│  │(Causality, Impact,│                                               │
│  │ Change Correl.,   │                                               │
│  │ Research, GitHub)  │                                               │
│  └───────────────────┘                                               │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  Standalone: Agent Debugging                                         │
│  ┌───────────────────┐                                               │
│  │  agent_debugger   │                                               │
│  │ (Vertex Agent     │                                               │
│  │  Engine analysis, │                                               │
│  │  Token usage,     │                                               │
│  │  Anti-patterns)   │                                               │
│  └───────────────────┘                                               │
└─────────────────────────────────────────────────────────────────────┘
```

## Sub-Agent Files

| File | Sub-Agents | Model | Description |
|------|------------|-------|-------------|
| `trace.py` | `aggregate_analyzer`, `trace_analyst` | deep, fast | Core trace analysis pipeline |
| `logs.py` | `log_analyst` | fast | Log pattern analysis |
| `metrics.py` | `metrics_analyzer` (alias: `metrics_analyst`) | fast | Metrics analysis with PromQL and exemplar correlation |
| `alerts.py` | `alert_analyst` | fast | Alert triage (First Responder) |
| `root_cause.py` | `root_cause_analyst` | deep | Root cause synthesis with research and GitHub self-healing |
| `agent_debugger.py` | `agent_debugger` | fast | Vertex Agent Engine interaction analysis and optimization |
| `_init_env.py` | (helper) | -- | Shared environment initialization for all sub-agents |

## Detailed Sub-Agent Descriptions

### Stage 0: Aggregate Analysis

#### `aggregate_analyzer` (trace.py)
- **Role**: Data Analyst -- fleet-wide BigQuery analysis specialist
- **Model**: `gemini-2.5-pro` (deep) -- handles complex SQL generation
- **Purpose**: Analyze fleet-wide patterns using BigQuery before diving into specific traces.
- **Workflow**: Discover tables > Aggregate ("Which service has high error rates?") > Trend ("When did it start?") > Zoom In (specific trace IDs)
- **Tools**: `mcp_execute_sql`, `analyze_aggregate_metrics`, `find_exemplar_traces`, `discover_telemetry_sources`, `list_traces`, `find_bottleneck_services`, `build_service_dependency_graph`, `list_log_entries`, `list_time_series`, `query_promql`, `detect_trend_changes`, `correlate_metrics_with_traces_via_exemplars`

#### `alert_analyst` (alerts.py)
- **Role**: Alert Analyst -- rapid incident triage and classification specialist
- **Model**: `gemini-2.5-flash` (fast)
- **Purpose**: Triage incoming alerts and policy violations. Classify severity and recommend next specialist.
- **Workflow**: Triage (active alerts?) > Policy Mapping (what was violated?) > Severity (P1 or P4?) > Handoff (which specialist?)
- **Tools**: `list_alerts`, `get_alert`, `list_alert_policies`, `list_log_entries`, `list_time_series`, `discover_telemetry_sources`, `generate_remediation_suggestions`, `estimate_remediation_risk`, `get_gcloud_commands`

### Stage 1: Specialized Analysts

#### `trace_analyst` (trace.py)
- **Role**: Trace Analyst -- comprehensive performance expert for latency, errors, and structure
- **Model**: `gemini-2.5-flash` (fast)
- **Purpose**: Consolidated analysis of latency, errors, structure, resiliency, and critical path. Uses the `analyze_trace_comprehensive` mega-tool for one-shot analysis before falling back to individual tools.
- **Capabilities**: One-shot analysis, baseline vs target comparison, critical path identification, SRE anti-pattern detection (retry storms, cascading timeouts, connection pool issues)
- **Tools**: `analyze_trace_comprehensive`, `compare_span_timings`, `analyze_critical_path`, `calculate_critical_path_contribution`, `find_bottleneck_services`, `fetch_trace`, `detect_latency_anomalies`, `detect_all_sre_patterns`, `detect_retry_storm`, `detect_cascading_timeout`, `detect_connection_pool_issues`, `correlate_logs_with_trace`, `correlate_metrics_with_traces_via_exemplars`, `query_promql`

#### `log_analyst` (logs.py)
- **Role**: Log Analyst -- pattern mining and anomaly detection specialist
- **Model**: `gemini-2.5-flash` (fast)
- **Purpose**: Mine error patterns from massive log streams using BigQuery SQL and Drain3 algorithms. Correlates log clusters to trace IDs.
- **Workflow**: Discover tables > Mine errors (`analyze_bigquery_log_patterns`) > Compare periods > Correlate with trace_id > Remediate
- **Tools**: `list_log_entries`, `analyze_bigquery_log_patterns`, `extract_log_patterns`, `mcp_execute_sql`, `discover_telemetry_sources`, `list_time_series`, `compare_time_periods`, `generate_remediation_suggestions`, `estimate_remediation_risk`, `get_gcloud_commands`

#### `metrics_analyzer` (metrics.py)
- **Role**: Metrics Analyzer -- time-series analysis, PromQL, and exemplar correlation specialist
- **Model**: `gemini-2.5-flash` (fast)
- **Purpose**: Quantify the magnitude and timing of metrics anomalies, correlate metric spikes with distributed traces via exemplars, and contextualize against historical baselines.
- **Capabilities**:
  - **PromQL expertise**: Translates Cloud Monitoring metric names to PromQL format, handles distributions, rate calculations, and histogram percentiles
  - **Exemplar correlation**: Links metric spikes to specific traces using `correlate_metrics_with_traces_via_exemplars`
  - **Anomaly detection**: Statistical anomaly detection and cross-window metric comparison
  - **GCP metric catalog**: Includes a built-in reference of common GCP metrics by service (from `resources/gcp_metrics.py`)
- **Workflow**: Quantify spike (`query_promql`) > Link to traces (exemplars) > Compare baselines (`compare_metric_windows`) > Detect anomalies (`detect_metric_anomalies`)
- **Tools**: `list_time_series`, `list_metric_descriptors`, `query_promql`, `mcp_list_timeseries`, `mcp_query_range`, `detect_metric_anomalies`, `compare_metric_windows`, `calculate_series_stats`, `correlate_trace_with_metrics`, `correlate_metrics_with_traces_via_exemplars`, `list_log_entries`
- **Aliases**: `metrics_analyst` (backward compatibility), `get_metrics_analyzer()`, `get_metrics_analyst()`

### Stage 2: Deep Dive Investigation

#### `root_cause_analyst` (root_cause.py)
- **Role**: Root Cause Analyst -- multi-signal synthesis for causality, impact, and change detection
- **Model**: `gemini-2.5-pro` (deep) -- handles complex multi-signal reasoning
- **Purpose**: Synthesize findings across all signals (Traces, Logs, Metrics, Changes) to determine causality, impact, and triggers. Answers: WHAT happened, WHO/WHAT changed, and HOW BAD is the impact.
- **Capabilities**: Causal analysis, cross-signal correlation, change detection, blast radius assessment, remediation generation, online research, GitHub self-healing (read/search/commit/PR)
- **Workflow**: Identify root cause > Confirm with cross-signal correlation > Measure blast radius > Detect triggering change > Suggest remediation
- **Tools**: `perform_causal_analysis`, `build_cross_signal_timeline`, `correlate_logs_with_trace`, `correlate_trace_with_metrics`, `analyze_upstream_downstream_impact`, `build_service_dependency_graph`, `detect_trend_changes`, `compare_time_periods`, `list_log_entries`, `list_time_series`, `query_promql`, `fetch_trace`, `generate_remediation_suggestions`, `estimate_remediation_risk`, `get_gcloud_commands`, `search_google`, `fetch_web_page`, `github_read_file`, `github_search_code`, `github_list_recent_commits`, `github_create_pull_request`

### Standalone: Agent Debugging

#### `agent_debugger` (agent_debugger.py)
- **Role**: Agent Debugger -- Vertex Agent Engine interaction analyst and optimizer
- **Model**: `gemini-2.5-flash` (fast)
- **Purpose**: Debug AI agent behavior by analyzing Cloud Trace telemetry with GenAI semantic conventions from Vertex Agent Engine. Identifies inefficiencies, anti-patterns, and optimization opportunities in agent execution.
- **Domain Knowledge**: OTel GenAI semantic conventions (`gen_ai.operation.name`, `gen_ai.usage.input_tokens`, etc.), Vertex Agent Engine resource IDs, span classification (agent invocations, LLM calls, tool executions, sub-agent delegations)
- **Anti-Pattern Detection**:
  - **Excessive Retries**: Same tool called >3 times under same parent
  - **Token Waste**: Output tokens >5x input tokens on intermediate LLM calls
  - **Long Reasoning Chains**: >8 consecutive LLM calls without tool use
  - **Redundant Tool Calls**: Same tool invoked repeatedly across trace
- **Tools**: `list_agent_traces`, `reconstruct_agent_interaction`, `analyze_agent_token_usage`, `detect_agent_anti_patterns`, `fetch_trace`, `list_log_entries`, `list_traces`, `mcp_execute_sql`, `discover_telemetry_sources`, `get_current_time`, `get_investigation_summary`, `update_investigation_state`
- **Use when**: Debugging agent runs, analyzing token usage, finding agent anti-patterns, or investigating Vertex Agent Engine reasoning engine behavior

## Orchestration Functions

The main agent uses these orchestration functions in `agent.py` to invoke the Council of Experts:

| Function | Stage | Sub-Agents Invoked |
|----------|-------|-------------------|
| `run_aggregate_analysis` | 0 | `aggregate_analyzer` |
| `run_triage_analysis` | 1 | `trace_analyst`, `log_analyst` |
| `run_deep_dive_analysis` | 2 | `root_cause_analyst` |
| `run_log_pattern_analysis` | Specialist | `log_analyst` |

## Design Principles

1. **Efficiency**: Use "Mega-Tools" like `analyze_trace_comprehensive` to reduce LLM round-trips.
2. **Specialization**: Each sub-agent has a clearly defined scope and persona.
3. **Hierarchy**: The main SRE Agent orchestrates, sub-agents analyze, tools execute.
4. **Resiliency**: Fallback between MCP tools and direct Cloud APIs when failures occur.
5. **Shared Tool Sets**: All tool assignments defined in `council/tool_registry.py` (OPT-4) to prevent drift between council panels and sub-agents.
6. **Model Selection**: Computationally intensive tasks (aggregate analysis, root cause) use `deep` (Pro) model; high-throughput tasks (trace, logs, metrics, alerts) use `fast` (Flash) model.
