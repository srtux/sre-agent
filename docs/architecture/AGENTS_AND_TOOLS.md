# Auto SRE: Complete Agent & Tool Architecture

> **Purpose**: Comprehensive map of every agent, sub-agent, panel, and tool — how they connect, which prompts they use, and where the code lives. Includes optimization analysis.

---

## Table of Contents

1. [Architecture Diagram](#architecture-diagram)
2. [Agent Hierarchy Table](#agent-hierarchy-table)
3. [Prompt Registry](#prompt-registry)
4. [Complete Tool Inventory](#complete-tool-inventory)
5. [Tool-to-Agent Assignment Matrix](#tool-to-agent-assignment-matrix)
6. [Data Flow Diagrams](#data-flow-diagrams)
7. [Architecture Analysis & Optimization Recommendations](#architecture-analysis--optimization-recommendations)

---

## Architecture Diagram

### Full System — Two Operating Modes

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         USER REQUEST                                        │
│                    (via FastAPI / ADK CLI)                                   │
└─────────────────────────┬───────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │   Feature Flag Check  │
              │ SRE_AGENT_COUNCIL_    │
              │ ORCHESTRATOR=true?    │
              └───────┬───────┬───────┘
                 NO   │       │  YES
                      ▼       ▼
    ┌─────────────────────┐  ┌──────────────────────────┐
    │  MODE A: LlmAgent   │  │  MODE B: BaseAgent       │
    │  (Default Root)      │  │  (CouncilOrchestrator)   │
    │  sre_agent/agent.py  │  │  council/orchestrator.py │
    │  :1484               │  │  :34                     │
    └─────────┬───────────┘  └────────────┬─────────────┘
              │                            │
              ▼                            ▼
    ┌─────────────────────┐  ┌──────────────────────────┐
    │  route_request()    │  │  classify_intent_with_   │
    │  (3-tier router)    │  │  signal() (rule-based)   │
    │  core/router.py:45  │  │  council/intent_         │
    │                     │  │  classifier.py:268       │
    └──┬──────┬───────┬───┘  └──┬──────┬───────┬───────┘
       │      │       │         │      │       │
       ▼      ▼       ▼         ▼      ▼       ▼
    DIRECT SUB_AGENT COUNCIL  FAST  STANDARD  DEBATE
```

### Mode A: Default Root Agent (LlmAgent)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     sre_agent (LlmAgent)                            │
│                     Model: gemini-flash                              │
│                     Prompt: SRE_AGENT_PROMPT                        │
│                     Tools: ~90 base_tools + preload_memory +        │
│                            load_memory                              │
│                     Code: sre_agent/agent.py:1484                   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              3-Tier Router (route_request)                   │    │
│  │              core/router.py:45                               │    │
│  └──────┬────────────────┬────────────────┬────────────────────┘    │
│         │                │                │                         │
│    ┌────▼────┐    ┌──────▼──────┐   ┌─────▼──────────┐             │
│    │ DIRECT  │    │ SUB_AGENT   │   │ COUNCIL        │             │
│    │ (Tools) │    │ (Delegate)  │   │ (Parallel)     │             │
│    └─────────┘    └──────┬──────┘   └─────┬──────────┘             │
│                          │                │                         │
│         ┌────────────────┼────────────────┼──────────────┐         │
│         │                │                │              │          │
│    ┌────▼─────┐   ┌──────▼──────┐  ┌─────▼────┐  ┌─────▼────┐    │
│    │aggregate │   │trace_analyst│  │log_      │  │metrics_  │    │
│    │_analyzer │   │             │  │analyst   │  │analyzer  │    │
│    │(deep)    │   │(fast)       │  │(deep)    │  │(deep)    │    │
│    └──────────┘   └─────────────┘  └──────────┘  └──────────┘    │
│                                                                     │
│    ┌──────────┐   ┌─────────────┐  ┌──────────────┐               │
│    │alert_    │   │root_cause_  │  │agent_        │               │
│    │analyst   │   │analyst      │  │debugger      │               │
│    │(fast)    │   │(deep)       │  │(fast)        │               │
│    └──────────┘   └─────────────┘  └──────────────┘               │
│                                                                     │
│  Orchestration Tools (invoke sub-agents as AgentTool):              │
│  ├── run_aggregate_analysis  → aggregate_analyzer                   │
│  ├── run_triage_analysis     → trace_analyst + log_analyst          │
│  ├── run_deep_dive_analysis  → root_cause_analyst                   │
│  ├── run_log_pattern_analysis→ log_analyst                          │
│  └── run_council_investigation → Council Pipeline (below)           │
└─────────────────────────────────────────────────────────────────────┘
```

### Mode B: Council Orchestrator (BaseAgent)

```
┌─────────────────────────────────────────────────────────────────────┐
│              CouncilOrchestrator (BaseAgent)                         │
│              council/orchestrator.py:34                              │
│              No LLM — pure routing logic                            │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │     classify_intent_with_signal() → mode + signal_type      │    │
│  │     council/intent_classifier.py:268                        │    │
│  └──────┬─────────────────┬────────────────────┬───────────────┘    │
│         │                 │                    │                     │
│    ┌────▼────┐     ┌──────▼──────┐      ┌──────▼──────┐            │
│    │  FAST   │     │  STANDARD   │      │   DEBATE    │            │
│    │ Single  │     │  Parallel   │      │  Loop +     │            │
│    │ Panel   │     │  Pipeline   │      │  Critique   │            │
│    └────┬────┘     └──────┬──────┘      └──────┬──────┘            │
│         │                 │                    │                     │
│         ▼                 ▼                    ▼                     │
│  ┌────────────┐  ┌────────────────┐  ┌──────────────────────┐      │
│  │Best-fit    │  │ Sequential     │  │ SequentialAgent      │      │
│  │panel by    │  │ Agent          │  │ debate_pipeline      │      │
│  │signal_type │  │                │  │ debate.py:193        │      │
│  │            │  │ council_       │  │                      │      │
│  │(trace/     │  │ pipeline       │  │ ┌──────────────────┐ │      │
│  │ metrics/   │  │ parallel_      │  │ │Initial Panels    │ │      │
│  │ logs/      │  │ council.py:24  │  │ │(ParallelAgent)   │ │      │
│  │ alerts)    │  │                │  │ └────────┬─────────┘ │      │
│  └────────────┘  │ ┌────────────┐│  │          ▼           │      │
│                  │ │Parallel    ││  │ ┌──────────────────┐ │      │
│                  │ │Agent       ││  │ │Initial Synth.    │ │      │
│                  │ │(5 panels)  ││  │ └────────┬─────────┘ │      │
│                  │ └─────┬──────┘│  │          ▼           │      │
│                  │       ▼       │  │ ┌──────────────────┐ │      │
│                  │ ┌────────────┐│  │ │LoopAgent         │ │      │
│                  │ │Synthesizer ││  │ │(debate_loop)     │ │      │
│                  │ │(deep)      ││  │ │max_iter=3        │ │      │
│                  │ └────────────┘│  │ │                  │ │      │
│                  └───────────────┘  │ │ critic →         │ │      │
│                                     │ │ panels(parallel)→│ │      │
│                                     │ │ synthesizer      │ │      │
│                                     │ │                  │ │      │
│                                     │ │ confidence_gate  │ │      │
│                                     │ │ (before_agent)   │ │      │
│                                     │ │ convergence_     │ │      │
│                                     │ │ tracker (after)  │ │      │
│                                     │ └──────────────────┘ │      │
│                                     └──────────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
```

### Council Panel Data Flow

```
                    ┌──────────────────────────────┐
                    │      ParallelAgent            │
                    │      (5 panels concurrent)    │
                    └──┬──────┬──────┬──────┬──────┬┘
                       │      │      │      │      │
              ┌────────▼┐ ┌───▼───┐ ┌▼─────┐┌▼────┐┌▼─────┐
              │Trace    │ │Metrics│ │Logs  ││Alert││Data  │
              │Panel    │ │Panel  │ │Panel ││Panel││Panel │
              │(fast)   │ │(fast) │ │(fast)││(fas)││(fast)│
              └────┬────┘ └───┬───┘ └──┬───┘└──┬──┘└──┬───┘
                   │          │        │       │      │
         output_key:   output_key: output_key: output: output:
         trace_      metrics_    logs_     alerts_ data_
         finding     finding     finding   finding finding
                   │          │        │       │      │
                   └──────────┴────┬───┴───────┴──────┘
                                   │
                          Session State
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │    Synthesizer (deep)         │
                    │    Reads all *_finding keys   │
                    │    Writes: council_synthesis  │
                    │    council/synthesizer.py:16  │
                    └──────────────────────────────┘
                                   │
                          (DEBATE mode only)
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │    Critic (deep)              │
                    │    Reads all *_finding keys   │
                    │    Writes: critic_report      │
                    │    council/critic.py:14       │
                    └──────────────────────────────┘
```

---

## Agent Hierarchy Table

### Root Agents

| Agent | Type | Model | Code | Prompt | Description |
|:------|:-----|:------|:-----|:-------|:------------|
| **sre_agent** | `LlmAgent` | `fast` (Gemini Flash) | [`agent.py:1484`](../../sre_agent/agent.py#L1484) | [`SRE_AGENT_PROMPT`](../../sre_agent/prompt.py#L30) | Default root agent. Full tool set (~90), 7 sub-agents, 3-tier router |
| **CouncilOrchestrator** | `BaseAgent` | None (no LLM) | [`council/orchestrator.py:34`](../../sre_agent/council/orchestrator.py#L34) | None | Alternative root. Pure routing to Fast/Standard/Debate pipelines |

### Sub-Agents (children of sre_agent)

| Agent | Model | Code | Prompt Location | Tools | Purpose |
|:------|:------|:-----|:----------------|:------|:--------|
| **aggregate_analyzer** | `deep` (Gemini Pro) | [`sub_agents/trace.py:194`](../../sre_agent/sub_agents/trace.py#L194) | [`AGGREGATE_ANALYZER_PROMPT`](../../sre_agent/sub_agents/trace.py#L55) | 16 | Stage 0: Fleet-wide BigQuery analysis |
| **trace_analyst** | `fast` (Gemini Flash) | [`sub_agents/trace.py:157`](../../sre_agent/sub_agents/trace.py#L157) | [`TRACE_ANALYST_PROMPT`](../../sre_agent/sub_agents/trace.py#L108) | 16 | Stage 1: Individual trace analysis (latency, errors, structure) |
| **log_analyst** | `deep` (Gemini Pro) | [`sub_agents/logs.py:102`](../../sre_agent/sub_agents/logs.py#L102) | [`LOG_ANALYST_PROMPT`](../../sre_agent/sub_agents/logs.py#L45) | 11 | Log pattern mining via BigQuery/Drain3 |
| **metrics_analyzer** | `deep` (Gemini Pro) | [`sub_agents/metrics.py:180`](../../sre_agent/sub_agents/metrics.py#L180) | [`METRICS_ANALYZER_PROMPT`](../../sre_agent/sub_agents/metrics.py#L55) | 12 | Time-series analysis, PromQL, exemplar correlation |
| **alert_analyst** | `fast` (Gemini Flash) | [`sub_agents/alerts.py:75`](../../sre_agent/sub_agents/alerts.py#L75) | [`ALERT_ANALYST_PROMPT`](../../sre_agent/sub_agents/alerts.py#L38) | 11 | Alert triage and incident classification |
| **root_cause_analyst** | `deep` (Gemini Pro) | [`sub_agents/root_cause.py:88`](../../sre_agent/sub_agents/root_cause.py#L88) | [`ROOT_CAUSE_ANALYST_PROMPT`](../../sre_agent/sub_agents/root_cause.py#L48) | 16 | Stage 2: Multi-signal root cause synthesis |
| **agent_debugger** | `fast` (Gemini Flash) | [`sub_agents/agent_debugger.py:97`](../../sre_agent/sub_agents/agent_debugger.py#L97) | [`AGENT_DEBUGGER_PROMPT`](../../sre_agent/sub_agents/agent_debugger.py#L41) | 12 | Debugs Vertex Agent Engine interactions |

### Council Panel Agents (created dynamically by pipeline factories)

| Panel Agent | Model | Factory | Prompt | output_key | Tools |
|:------------|:------|:--------|:-------|:-----------|:------|
| **trace_panel** | `fast` | [`panels.py:31`](../../sre_agent/council/panels.py#L31) | [`TRACE_PANEL_PROMPT`](../../sre_agent/council/prompts.py#L18) | `trace_finding` | 22 |
| **metrics_panel** | `fast` | [`panels.py:57`](../../sre_agent/council/panels.py#L57) | [`METRICS_PANEL_PROMPT`](../../sre_agent/council/prompts.py#L51) | `metrics_finding` | 13 |
| **logs_panel** | `fast` | [`panels.py:83`](../../sre_agent/council/panels.py#L83) | [`LOGS_PANEL_PROMPT`](../../sre_agent/council/prompts.py#L83) | `logs_finding` | 8 |
| **alerts_panel** | `fast` | [`panels.py:109`](../../sre_agent/council/panels.py#L109) | [`ALERTS_PANEL_PROMPT`](../../sre_agent/council/prompts.py#L115) | `alerts_finding` | 10 |
| **data_panel** | `fast` | [`panels.py:134`](../../sre_agent/council/panels.py#L134) | [`DATA_PANEL_PROMPT`](../../sre_agent/council/prompts.py#L151) | `data_finding` | 6 |

### Council Meta-Agents (created dynamically)

| Agent | Model | Factory | Prompt | output_key | Purpose |
|:------|:------|:--------|:-------|:-----------|:--------|
| **council_synthesizer** | `deep` | [`synthesizer.py:16`](../../sre_agent/council/synthesizer.py#L16) | [`SYNTHESIZER_PROMPT`](../../sre_agent/council/prompts.py#L248) | `council_synthesis` | Merges all panel findings into unified assessment |
| **council_critic** | `deep` | [`critic.py:14`](../../sre_agent/council/critic.py#L14) | [`CRITIC_PROMPT`](../../sre_agent/council/prompts.py#L202) | `critic_report` | Cross-examines panel findings (debate mode only) |

### Workflow Agents (ADK primitives, no LLM)

| Agent | Type | Code | Purpose |
|:------|:-----|:-----|:--------|
| **parallel_panels** | `ParallelAgent` | [`parallel_council.py:47`](../../sre_agent/council/parallel_council.py#L47) | Runs 5 panels concurrently |
| **council_pipeline** | `SequentialAgent` | [`parallel_council.py:60`](../../sre_agent/council/parallel_council.py#L60) | Panels → Synthesizer |
| **initial_panels** | `ParallelAgent` | [`debate.py:214`](../../sre_agent/council/debate.py#L214) | Initial parallel analysis (debate) |
| **debate_panels** | `ParallelAgent` | [`debate.py:238`](../../sre_agent/council/debate.py#L238) | Re-run panels with critic feedback |
| **debate_loop** | `LoopAgent` | [`debate.py:230`](../../sre_agent/council/debate.py#L230) | Critic → Panels → Synthesizer loop (max 3 iters) |
| **debate_pipeline** | `SequentialAgent` | [`debate.py:257`](../../sre_agent/council/debate.py#L257) | Initial analysis → Debate loop |

---

## Prompt Registry

Every prompt in the system, with location and approximate token count.

| Prompt Constant | Used By | File | Line | Est. Tokens |
|:----------------|:--------|:-----|:-----|:------------|
| [`SRE_AGENT_PROMPT`](../../sre_agent/prompt.py#L30) | `sre_agent` (root) | `prompt.py` | 30 | ~2,500 |
| [`STRICT_ENGLISH_INSTRUCTION`](../../sre_agent/prompt.py#L3) | All agents (via inclusion) | `prompt.py` | 3 | ~50 |
| [`REACT_PATTERN_INSTRUCTION`](../../sre_agent/prompt.py#L8) | All agents (via inclusion) | `prompt.py` | 8 | ~150 |
| [`PROJECT_CONTEXT_INSTRUCTION`](../../sre_agent/prompt.py#L23) | All agents (via inclusion) | `prompt.py` | 23 | ~60 |
| [`CROSS_SIGNAL_CORRELATOR_PROMPT`](../../sre_agent/prompt.py#L323) | (Unused — legacy) | `prompt.py` | 323 | ~300 |
| [`AGGREGATE_ANALYZER_PROMPT`](../../sre_agent/sub_agents/trace.py#L55) | `aggregate_analyzer` | `sub_agents/trace.py` | 55 | ~600 |
| [`TRACE_ANALYST_PROMPT`](../../sre_agent/sub_agents/trace.py#L108) | `trace_analyst` | `sub_agents/trace.py` | 108 | ~600 |
| [`LOG_ANALYST_PROMPT`](../../sre_agent/sub_agents/logs.py#L45) | `log_analyst` | `sub_agents/logs.py` | 45 | ~700 |
| [`METRICS_ANALYZER_PROMPT`](../../sre_agent/sub_agents/metrics.py#L55) | `metrics_analyzer` | `sub_agents/metrics.py` | 55 | ~1,200 |
| [`ALERT_ANALYST_PROMPT`](../../sre_agent/sub_agents/alerts.py#L38) | `alert_analyst` | `sub_agents/alerts.py` | 38 | ~400 |
| [`ROOT_CAUSE_ANALYST_PROMPT`](../../sre_agent/sub_agents/root_cause.py#L48) | `root_cause_analyst` | `sub_agents/root_cause.py` | 48 | ~450 |
| [`AGENT_DEBUGGER_PROMPT`](../../sre_agent/sub_agents/agent_debugger.py#L41) | `agent_debugger` | `sub_agents/agent_debugger.py` | 41 | ~500 |
| [`TRACE_PANEL_PROMPT`](../../sre_agent/council/prompts.py#L18) | `trace_panel` | `council/prompts.py` | 18 | ~350 |
| [`METRICS_PANEL_PROMPT`](../../sre_agent/council/prompts.py#L51) | `metrics_panel` | `council/prompts.py` | 51 | ~300 |
| [`LOGS_PANEL_PROMPT`](../../sre_agent/council/prompts.py#L83) | `logs_panel` | `council/prompts.py` | 83 | ~300 |
| [`ALERTS_PANEL_PROMPT`](../../sre_agent/council/prompts.py#L115) | `alerts_panel` | `council/prompts.py` | 115 | ~300 |
| [`DATA_PANEL_PROMPT`](../../sre_agent/council/prompts.py#L151) | `data_panel` | `council/prompts.py` | 151 | ~350 |
| [`CRITIC_PROMPT`](../../sre_agent/council/prompts.py#L202) | `council_critic` | `council/prompts.py` | 202 | ~300 |
| [`SYNTHESIZER_PROMPT`](../../sre_agent/council/prompts.py#L248) | `council_synthesizer` | `council/prompts.py` | 248 | ~500 |

### Shared Prompt Fragments (included in most prompts via f-string)

```
STRICT_ENGLISH_INSTRUCTION ──┐
PROJECT_CONTEXT_INSTRUCTION ──┼──► Prepended to every sub-agent + panel prompt
REACT_PATTERN_INSTRUCTION ───┘
```

---

## Complete Tool Inventory

### Observability — Data Retrieval (14 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`fetch_trace`](../../sre_agent/tools/clients/trace.py) | `tools/clients/trace.py` | Root, Trace Analyst, Trace Panel, Agent Debugger, Root Cause |
| [`list_traces`](../../sre_agent/tools/clients/trace.py) | `tools/clients/trace.py` | Root, Agg. Analyzer, Trace Panel, Agent Debugger |
| [`get_trace_by_url`](../../sre_agent/tools/clients/trace.py) | `tools/clients/trace.py` | Root |
| [`get_logs_for_trace`](../../sre_agent/tools/clients/trace.py) | `tools/clients/trace.py` | Root |
| [`list_log_entries`](../../sre_agent/tools/clients/logging.py) | `tools/clients/logging.py` | Root, Most sub-agents, Logs/Metrics/Alerts panels |
| [`list_time_series`](../../sre_agent/tools/clients/monitoring.py) | `tools/clients/monitoring.py` | Root, Most sub-agents, All panels |
| [`list_metric_descriptors`](../../sre_agent/tools/clients/monitoring.py) | `tools/clients/monitoring.py` | Root, Metrics Analyzer, Metrics Panel |
| [`query_promql`](../../sre_agent/tools/clients/monitoring.py) | `tools/clients/monitoring.py` | Root, Trace/Metrics/Root Cause sub-agents, Metrics Panel |
| [`list_alerts`](../../sre_agent/tools/clients/monitoring.py) | `tools/clients/monitoring.py` | Root, Alert Analyst, Alerts Panel |
| [`list_alert_policies`](../../sre_agent/tools/clients/monitoring.py) | `tools/clients/monitoring.py` | Root, Alert Analyst, Alerts Panel |
| [`get_alert`](../../sre_agent/tools/clients/monitoring.py) | `tools/clients/monitoring.py` | Root, Alert Analyst, Alerts Panel |
| [`list_slos`](../../sre_agent/tools/clients/monitoring.py) | `tools/clients/monitoring.py` | Root |
| [`list_gcp_projects`](../../sre_agent/tools/clients/resource_manager.py) | `tools/clients/resource_manager.py` | Root |
| [`list_error_events`](../../sre_agent/tools/clients/error_reporting.py) | `tools/clients/error_reporting.py` | Root |

### Trace Analysis (13 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`analyze_trace_comprehensive`](../../sre_agent/tools/analysis/trace/comprehensive.py) | `tools/analysis/trace/comprehensive.py` | Root, Trace Analyst, Trace Panel |
| [`analyze_critical_path`](../../sre_agent/tools/analysis/trace/critical_path.py) | `tools/analysis/trace/critical_path.py` | Root, Trace Analyst, Trace Panel |
| [`calculate_critical_path_contribution`](../../sre_agent/tools/analysis/trace/critical_path.py) | `tools/analysis/trace/critical_path.py` | Root, Trace Analyst, Trace Panel |
| [`calculate_span_durations`](../../sre_agent/tools/analysis/trace/durations.py) | `tools/analysis/trace/durations.py` | Root |
| [`compare_span_timings`](../../sre_agent/tools/analysis/trace/comparison.py) | `tools/analysis/trace/comparison.py` | Root, Trace Analyst, Trace Panel |
| [`find_bottleneck_services`](../../sre_agent/tools/analysis/trace/bottleneck.py) | `tools/analysis/trace/bottleneck.py` | Root, Trace Analyst, Agg. Analyzer, Trace Panel |
| [`analyze_trace_patterns`](../../sre_agent/tools/analysis/trace/patterns.py) | `tools/analysis/trace/patterns.py` | Root |
| [`find_structural_differences`](../../sre_agent/tools/analysis/trace/structure.py) | `tools/analysis/trace/structure.py` | Root |
| [`summarize_trace`](../../sre_agent/tools/analysis/trace/summary.py) | `tools/analysis/trace/summary.py` | Root |
| [`validate_trace_quality`](../../sre_agent/tools/analysis/trace/validation.py) | `tools/analysis/trace/validation.py` | Root |
| [`extract_errors`](../../sre_agent/tools/analysis/trace/errors.py) | `tools/analysis/trace/errors.py` | Root |
| [`build_call_graph`](../../sre_agent/tools/analysis/trace/call_graph.py) | `tools/analysis/trace/call_graph.py` | Root |
| [`compute_latency_statistics`](../../sre_agent/tools/analysis/trace/statistics.py) | `tools/analysis/trace/statistics.py` | Root |

### Metrics Analysis (6 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`detect_metric_anomalies`](../../sre_agent/tools/analysis/metrics/anomaly.py) | `tools/analysis/metrics/anomaly.py` | Root, Metrics Analyzer, Metrics Panel |
| [`compare_metric_windows`](../../sre_agent/tools/analysis/metrics/comparison.py) | `tools/analysis/metrics/comparison.py` | Root, Metrics Analyzer, Metrics Panel |
| [`calculate_series_stats`](../../sre_agent/tools/analysis/metrics/statistics.py) | `tools/analysis/metrics/statistics.py` | Root, Metrics Analyzer, Metrics Panel |
| [`detect_trend_changes`](../../sre_agent/tools/analysis/metrics/trends.py) | `tools/analysis/metrics/trends.py` | Root, Agg. Analyzer, Root Cause, Trace Panel |
| [`detect_latency_anomalies`](../../sre_agent/tools/analysis/metrics/latency.py) | `tools/analysis/metrics/latency.py` | Root, Trace Analyst, Trace Panel |
| [`compare_time_periods`](../../sre_agent/tools/analysis/metrics/periods.py) | `tools/analysis/metrics/periods.py` | Root, Multiple sub-agents, Multiple panels |

### Log Analysis (4 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`extract_log_patterns`](../../sre_agent/tools/analysis/logs/patterns.py) | `tools/analysis/logs/patterns.py` | Root, Log Analyst, Logs Panel |
| [`compare_log_patterns`](../../sre_agent/tools/analysis/logs/comparison.py) | `tools/analysis/logs/comparison.py` | Root |
| [`analyze_log_anomalies`](../../sre_agent/tools/analysis/logs/anomaly.py) | `tools/analysis/logs/anomaly.py` | Root |
| [`analyze_bigquery_log_patterns`](../../sre_agent/tools/analysis/logs/bigquery.py) | `tools/analysis/logs/bigquery.py` | Root, Log Analyst, Logs Panel |

### SLO/SLI Analysis (5 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`analyze_error_budget_burn`](../../sre_agent/tools/analysis/slo/budget.py) | `tools/analysis/slo/budget.py` | Root |
| [`analyze_multi_window_burn_rate`](../../sre_agent/tools/analysis/slo/burn_rate.py) | `tools/analysis/slo/burn_rate.py` | Root |
| [`get_slo_status`](../../sre_agent/tools/analysis/slo/status.py) | `tools/analysis/slo/status.py` | Root |
| [`predict_slo_violation`](../../sre_agent/tools/analysis/slo/prediction.py) | `tools/analysis/slo/prediction.py` | Root |
| [`correlate_incident_with_slo_impact`](../../sre_agent/tools/analysis/slo/correlation.py) | `tools/analysis/slo/correlation.py` | Root |

### Cross-Signal Correlation (7 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`correlate_trace_with_metrics`](../../sre_agent/tools/analysis/correlation/trace_metrics.py) | `tools/analysis/correlation/` | Root, Metrics Analyzer, Root Cause, Metrics Panel |
| [`correlate_metrics_with_traces_via_exemplars`](../../sre_agent/tools/analysis/correlation/exemplars.py) | `tools/analysis/correlation/` | Root, Agg. Analyzer, Metrics Analyzer, Trace/Metrics Panels |
| [`correlate_logs_with_trace`](../../sre_agent/tools/analysis/correlation/logs_trace.py) | `tools/analysis/correlation/` | Root, Trace Analyst, Root Cause, Trace Panel |
| [`correlate_trace_with_kubernetes`](../../sre_agent/tools/analysis/correlation/trace_k8s.py) | `tools/analysis/correlation/` | Root |
| [`build_cross_signal_timeline`](../../sre_agent/tools/analysis/correlation/timeline.py) | `tools/analysis/correlation/` | Root, Root Cause |
| [`analyze_signal_correlation_strength`](../../sre_agent/tools/analysis/correlation/strength.py) | `tools/analysis/correlation/` | Root |
| [`correlate_changes_with_incident`](../../sre_agent/tools/analysis/correlation/changes.py) | `tools/analysis/correlation/` | Root |

### Resiliency Pattern Detection (4 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`detect_all_sre_patterns`](../../sre_agent/tools/analysis/trace/sre_patterns.py) | `tools/analysis/trace/sre_patterns.py` | Root, Trace Analyst, Trace Panel |
| [`detect_retry_storm`](../../sre_agent/tools/analysis/trace/retry.py) | `tools/analysis/trace/retry.py` | Root, Trace Analyst, Trace Panel |
| [`detect_cascading_timeout`](../../sre_agent/tools/analysis/trace/timeout.py) | `tools/analysis/trace/timeout.py` | Root, Trace Analyst, Trace Panel |
| [`detect_connection_pool_issues`](../../sre_agent/tools/analysis/trace/pool.py) | `tools/analysis/trace/pool.py` | Root, Trace Analyst, Trace Panel |

### Dependency & Structure (4 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`build_service_dependency_graph`](../../sre_agent/tools/analysis/correlation/dependencies.py) | `tools/analysis/correlation/` | Root, Agg. Analyzer, Root Cause, Trace Panel |
| [`find_hidden_dependencies`](../../sre_agent/tools/analysis/correlation/dependencies.py) | `tools/analysis/correlation/` | Root |
| [`detect_circular_dependencies`](../../sre_agent/tools/analysis/correlation/dependencies.py) | `tools/analysis/correlation/` | Root |
| [`analyze_upstream_downstream_impact`](../../sre_agent/tools/analysis/correlation/impact.py) | `tools/analysis/correlation/` | Root, Root Cause |

### GKE / Infrastructure (5 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`get_gke_cluster_health`](../../sre_agent/tools/clients/gke.py) | `tools/clients/gke.py` | Root |
| [`analyze_node_conditions`](../../sre_agent/tools/clients/gke.py) | `tools/clients/gke.py` | Root |
| [`analyze_hpa_events`](../../sre_agent/tools/clients/gke.py) | `tools/clients/gke.py` | Root |
| [`get_pod_restart_events`](../../sre_agent/tools/clients/gke.py) | `tools/clients/gke.py` | Root |
| [`get_container_oom_events`](../../sre_agent/tools/clients/gke.py) | `tools/clients/gke.py` | Root |
| [`get_workload_health_summary`](../../sre_agent/tools/clients/gke.py) | `tools/clients/gke.py` | Root |

### Remediation & Postmortem (4 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`generate_remediation_suggestions`](../../sre_agent/tools/analysis/remediation/suggestions.py) | `tools/analysis/remediation/` | Root, Log/Alert/Root Cause sub-agents, Alerts Panel |
| [`estimate_remediation_risk`](../../sre_agent/tools/analysis/remediation/risk.py) | `tools/analysis/remediation/` | Root, Log/Alert/Root Cause sub-agents, Alerts Panel |
| [`generate_postmortem`](../../sre_agent/tools/analysis/remediation/postmortem.py) | `tools/analysis/remediation/` | Root |
| [`get_gcloud_commands`](../../sre_agent/tools/analysis/remediation/commands.py) | `tools/analysis/remediation/` | Root, Log/Alert/Root Cause sub-agents, Alerts Panel |

### BigQuery & MCP (10 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`mcp_execute_sql`](../../sre_agent/tools/mcp/gcp.py) | `tools/mcp/gcp.py` | Root, Agg. Analyzer, Agent Debugger, Trace/Data Panels |
| [`mcp_list_dataset_ids`](../../sre_agent/tools/mcp/gcp.py) | `tools/mcp/gcp.py` | Root |
| [`mcp_list_table_ids`](../../sre_agent/tools/mcp/gcp.py) | `tools/mcp/gcp.py` | Root |
| [`mcp_get_table_info`](../../sre_agent/tools/mcp/gcp.py) | `tools/mcp/gcp.py` | Root |
| [`mcp_list_log_entries`](../../sre_agent/tools/mcp/gcp.py) | `tools/mcp/gcp.py` | Root |
| [`mcp_list_timeseries`](../../sre_agent/tools/mcp/gcp.py) | `tools/mcp/gcp.py` | Root, Metrics Analyzer, Metrics Panel |
| [`mcp_query_range`](../../sre_agent/tools/mcp/gcp.py) | `tools/mcp/gcp.py` | Root, Metrics Analyzer, Metrics Panel |
| [`analyze_aggregate_metrics`](../../sre_agent/tools/bigquery/aggregate.py) | `tools/bigquery/aggregate.py` | Root, Agg. Analyzer, Trace Panel |
| [`find_exemplar_traces`](../../sre_agent/tools/bigquery/exemplars.py) | `tools/bigquery/exemplars.py` | Root, Agg. Analyzer, Trace Panel |
| [`query_data_agent`](../../sre_agent/tools/bigquery/ca_data_agent.py) | `tools/bigquery/ca_data_agent.py` | Root, Data Panel |

### Orchestration Tools (7 tools — invoke sub-agents)

| Tool | Code Path | Invokes |
|:-----|:----------|:--------|
| [`run_aggregate_analysis`](../../sre_agent/agent.py#L558) | `agent.py:558` | `aggregate_analyzer` via `AgentTool` |
| [`run_triage_analysis`](../../sre_agent/agent.py#L637) | `agent.py:637` | `trace_analyst` + `log_analyst` in parallel |
| [`run_deep_dive_analysis`](../../sre_agent/agent.py#L715) | `agent.py:715` | `root_cause_analyst` via `AgentTool` |
| [`run_log_pattern_analysis`](../../sre_agent/agent.py#L780) | `agent.py:780` | `log_analyst` via `AgentTool` |
| [`run_council_investigation`](../../sre_agent/agent.py#L965) | `agent.py:965` | Council pipeline (Standard or Debate) |
| [`classify_investigation_mode`](../../sre_agent/council/mode_router.py#L19) | `council/mode_router.py:19` | Rule-based classifier (no LLM) |
| [`route_request`](../../sre_agent/core/router.py#L44) | `core/router.py:44` | Rule-based 3-tier router (no LLM) |

### Discovery & Exploration (2 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`discover_telemetry_sources`](../../sre_agent/tools/discovery/sources.py) | `tools/discovery/sources.py` | Root, Agg. Analyzer, Agent Debugger, Multiple panels |
| [`explore_project_health`](../../sre_agent/tools/exploration/health.py) | `tools/exploration/health.py` | Root |

### Investigation State & Memory (8 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`update_investigation_state`](../../sre_agent/tools/memory.py) | `tools/memory.py` | Root, All sub-agents, All panels |
| [`get_investigation_summary`](../../sre_agent/tools/memory.py) | `tools/memory.py` | Root, All sub-agents, All panels |
| [`add_finding_to_memory`](../../sre_agent/tools/memory.py) | `tools/memory.py` | Root |
| [`search_memory`](../../sre_agent/tools/memory.py) | `tools/memory.py` | Root |
| [`complete_investigation`](../../sre_agent/tools/memory.py) | `tools/memory.py` | Root |
| [`get_recommended_investigation_strategy`](../../sre_agent/tools/memory.py) | `tools/memory.py` | Root |
| [`analyze_and_learn_from_traces`](../../sre_agent/tools/memory.py) | `tools/memory.py` | Root |
| [`suggest_next_steps`](../../sre_agent/tools/memory.py) | `tools/memory.py` | Root |

### Sandbox Processing (6 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`summarize_metric_descriptors_in_sandbox`](../../sre_agent/tools/sandbox/) | `tools/sandbox/` | Root |
| [`summarize_time_series_in_sandbox`](../../sre_agent/tools/sandbox/) | `tools/sandbox/` | Root |
| [`summarize_log_entries_in_sandbox`](../../sre_agent/tools/sandbox/) | `tools/sandbox/` | Root |
| [`summarize_traces_in_sandbox`](../../sre_agent/tools/sandbox/) | `tools/sandbox/` | Root |
| [`execute_custom_analysis_in_sandbox`](../../sre_agent/tools/sandbox/) | `tools/sandbox/` | Root |
| [`get_sandbox_status`](../../sre_agent/tools/sandbox/) | `tools/sandbox/` | Root |

### Agent Debugging (4 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`list_agent_traces`](../../sre_agent/tools/analysis/agent_trace/tools.py) | `tools/analysis/agent_trace/tools.py` | Root, Agent Debugger |
| [`reconstruct_agent_interaction`](../../sre_agent/tools/analysis/agent_trace/tools.py) | `tools/analysis/agent_trace/tools.py` | Root, Agent Debugger |
| [`analyze_agent_token_usage`](../../sre_agent/tools/analysis/agent_trace/tools.py) | `tools/analysis/agent_trace/tools.py` | Root, Agent Debugger |
| [`detect_agent_anti_patterns`](../../sre_agent/tools/analysis/agent_trace/tools.py) | `tools/analysis/agent_trace/tools.py` | Root, Agent Debugger |

### Miscellaneous (6 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`get_current_time`](../../sre_agent/tools/common/time.py) | `tools/common/time.py` | Root, Agent Debugger |
| [`get_golden_signals`](../../sre_agent/tools/analysis/slo/golden.py) | `tools/analysis/slo/golden.py` | Root |
| [`find_similar_past_incidents`](../../sre_agent/tools/analysis/correlation/incidents.py) | `tools/analysis/correlation/` | Root |
| [`perform_causal_analysis`](../../sre_agent/tools/analysis/correlation/causal.py) | `tools/analysis/correlation/` | Root, Root Cause |
| [`find_example_traces`](../../sre_agent/tools/bigquery/examples.py) | `tools/bigquery/examples.py` | Root |
| [`select_traces_manually`](../../sre_agent/tools/bigquery/selection.py) | `tools/bigquery/selection.py` | Root |
| [`select_traces_from_statistical_outliers`](../../sre_agent/tools/bigquery/selection.py) | `tools/bigquery/selection.py` | Root |
| [`synthesize_report`](../../sre_agent/tools/reporting.py) | `tools/reporting.py` | Root |
| [`preload_memory_tool`](https://google.github.io/adk-docs/) | ADK built-in | Root (auto each turn) |
| [`load_memory_tool`](https://google.github.io/adk-docs/) | ADK built-in | Root (on-demand) |

**Total: ~103 unique tools** registered in [`TOOL_NAME_MAP`](../../sre_agent/agent.py#L1069)

---

## Tool-to-Agent Assignment Matrix

Shows which tools are available to each agent. `R` = Root, `AA` = Aggregate Analyzer, `TA` = Trace Analyst, `LA` = Log Analyst, `MA` = Metrics Analyzer, `AL` = Alert Analyst, `RC` = Root Cause, `AD` = Agent Debugger, `TP` = Trace Panel, `MP` = Metrics Panel, `LP` = Logs Panel, `AP` = Alerts Panel, `DP` = Data Panel.

| Tool Category | R | AA | TA | LA | MA | AL | RC | AD | TP | MP | LP | AP | DP |
|:-----|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| fetch_trace | x | | x | | | | x | x | x | | | | |
| list_traces | x | x | | | | | | x | x | | | | |
| list_log_entries | x | x | x | x | x | x | x | x | | x | x | | |
| list_time_series | x | x | x | x | x | x | x | | | x | x | x | x |
| query_promql | x | x | x | | x | | x | | | x | | | |
| analyze_trace_comprehensive | x | | x | | | | | | x | | | | |
| detect_all_sre_patterns | x | | x | | | | | | x | | | | |
| detect_metric_anomalies | x | | | | x | | | | | x | | | |
| extract_log_patterns | x | | | x | | | | | | | x | | |
| list_alerts | x | | | | | x | | | | | | x | |
| mcp_execute_sql | x | x | | | | | | x | x | | | | x |
| generate_remediation_suggestions | x | | | x | | x | x | | | | | x | |
| discover_telemetry_sources | x | x | | x | | x | | x | x | | x | x | x |
| update_investigation_state | x | x | x | x | x | x | x | x | x | x | x | x | x |
| get_investigation_summary | x | x | x | x | x | x | x | x | x | x | x | x | x |
| query_data_agent | x | | | | | | | | | | | | x |

---

## Data Flow Diagrams

### Standard Council Investigation Flow

```
User Query
    │
    ▼
route_request() ──► decision: "council"
    │                  mode: "standard"
    ▼
run_council_investigation(query, mode="standard")
    │
    ▼
create_council_pipeline()  →  SequentialAgent
    │
    ├─► ParallelAgent (5 panels run concurrently)
    │   ├─► trace_panel    ──► output_key: "trace_finding"    → Session State
    │   ├─► metrics_panel  ──► output_key: "metrics_finding"  → Session State
    │   ├─► logs_panel     ──► output_key: "logs_finding"     → Session State
    │   ├─► alerts_panel   ──► output_key: "alerts_finding"   → Session State
    │   └─► data_panel     ──► output_key: "data_finding"     → Session State
    │
    └─► council_synthesizer
        ├── Reads: trace_finding, metrics_finding, logs_finding,
        │          alerts_finding, data_finding
        └── Writes: "council_synthesis" → Session State
              │
              ▼
        _extract_council_result()  →  BaseToolResponse
              │
              ▼
        Root Agent formats final response to user
```

### Debate Investigation Flow

```
User Query ("root cause of outage")
    │
    ▼
route_request() ──► decision: "council", mode: "debate"
    │
    ▼
run_council_investigation(query, mode="debate")
    │
    ▼
create_debate_pipeline()  →  SequentialAgent
    │
    ├─► STEP 1: initial_panels (ParallelAgent, 5 panels)
    │   └── Each writes to session state
    │
    ├─► STEP 2: initial_synthesizer
    │   └── Writes: "council_synthesis"
    │
    └─► STEP 3: debate_loop (LoopAgent, max_iterations=3)
        │
        ├── before_agent_callback: confidence_gate
        │   └── IF confidence >= 0.85 → STOP loop
        │
        ├── LOOP BODY (SequentialAgent):
        │   ├─► council_critic
        │   │   └── Reads all *_finding, writes: "critic_report"
        │   ├─► debate_panels (ParallelAgent, 5 panels)
        │   │   └── Re-analyze with critic feedback in state
        │   └─► council_synthesizer
        │       └── Re-synthesize with updated findings
        │
        └── after_agent_callback: convergence_tracker
            └── Records: confidence, delta, gaps, contradictions, duration
```

### 3-Stage Pipeline Flow (Legacy/Direct Mode)

```
User Query
    │
    ▼
route_request() ──► decision: "sub_agent" or user calls directly
    │
    ▼
┌─── Stage 0: run_aggregate_analysis ──────────────────────────┐
│   aggregate_analyzer (deep model)                             │
│   BigQuery fleet-wide analysis → exemplar trace IDs          │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌─── Stage 1: run_triage_analysis ─────────────────────────────┐
│   trace_analyst + log_analyst (parallel via asyncio.gather)   │
│   Compare baseline vs target traces + log patterns           │
└──────────────────────────────┬───────────────────────────────┘
                               │
                               ▼
┌─── Stage 2: run_deep_dive_analysis ──────────────────────────┐
│   root_cause_analyst (deep model)                             │
│   Cross-signal synthesis → root cause + remediation          │
└──────────────────────────────────────────────────────────────┘
```

---

## Architecture Analysis & Optimization Recommendations

### Current Architecture Assessment

#### Strengths

1. **Well-designed multi-modal routing**: The 3-tier router (Direct/Sub-Agent/Council) correctly avoids over-engineering simple queries.
2. **Parallel execution**: Council panels run concurrently via `ParallelAgent`, minimizing wall-clock time.
3. **Confidence-gated debate**: The `LoopAgent` with confidence thresholds prevents infinite debate loops.
4. **Structured output schemas**: `PanelFinding` with `output_key` ensures clean inter-agent data flow.
5. **Rule-based routing**: `classify_intent` and `classify_routing` avoid wasting an LLM call on classification.

#### Issues Found

| # | Issue | Severity | Impact |
|:--|:------|:---------|:-------|
| 1 | **Root agent has ~90 tools** — LLMs degrade at tool selection accuracy above ~30 tools | High | Wrong tool picks, wasted tokens |
| 2 | **Root prompt is ~2,500 tokens** of persona/emoji before any useful instruction | High | Tokens wasted on every turn, critical instructions buried |
| 3 | **Duplicate systems**: Sub-agents AND council panels do similar work with different prompts for the same domain | Medium | Maintenance burden, inconsistent behavior |
| 4 | **All panel prompts include ReAct instructions** (~150 tokens each, x5 panels = 750 wasted tokens per council run) | Medium | Gemini natively supports ReAct; explicit instructions are redundant |
| 5 | **`CROSS_SIGNAL_CORRELATOR_PROMPT` in `prompt.py:323` is unused** | Low | Dead code |
| 6 | **Emoji-heavy prompts consume tokens** — ~15% of prompt tokens are emojis and persona text | Medium | Higher cost, slower responses |
| 7 | **Sub-agents use `deep` model unnecessarily** — `log_analyst`, `metrics_analyzer`, `aggregate_analyzer` all use Gemini Pro for tasks that Flash handles well | High | 3-10x cost per sub-agent call |
| 8 | **Tool overlap between root and sub-agents** — Root has tools it never needs directly (e.g., `detect_retry_storm`) when council mode handles them | Medium | Larger tool schema, slower first-token |
| 9 | **No `skip_summarization`** on data-returning tools — Tools returning structured JSON get an extra LLM call for summarization | Medium | Unnecessary latency and cost |
| 10 | **Panel prompts repeat shared instructions** — English, Project Context, and ReAct are copy-pasted into every panel | Low | Maintenance risk, token waste |

---

### Optimization Recommendations

#### OPT-1: Reduce Root Agent Tool Count (HIGH IMPACT)

**Problem**: The root agent presents ~90 tools to Gemini. Research shows LLM tool selection accuracy drops significantly above 20-30 tools.

**Recommendation**: Make `SRE_AGENT_SLIM_TOOLS=true` the default. The slim set (20 tools) focuses on routing and orchestration. All specialist tools are delegated to sub-agents/panels.

```
Current: root has 90 tools → model confused
Target:  root has 20 tools → routes to specialists who have 8-22 focused tools
```

**Expected gain**: Faster first-token latency, better tool selection accuracy, ~50% fewer input tokens per root turn.

#### OPT-2: Compress Root Agent Prompt (HIGH IMPACT)

**Problem**: `SRE_AGENT_PROMPT` is ~2,500 tokens. The first ~800 tokens are persona/emoji that Gemini doesn't need.

**Recommendation**: Restructure using XML tags. Move persona to the end. Put constraints and tool strategy first (where LLMs pay most attention — "primacy bias").

**Before** (current structure):
```
1. Emoji persona (800 tokens)
2. Superpowers list (400 tokens)
3. Memory instructions (500 tokens)
4. Investigation strategy (400 tokens)
5. Constraints (200 tokens)        ← BURIED
6. Error handling (200 tokens)
```

**After** (recommended structure):
```xml
<constraints>                       ← FIRST (60 tokens)
  English only. Respect project context. ISO 8601 timestamps.
</constraints>
<routing>                           ← Tool strategy (200 tokens)
  Call route_request FIRST. Follow tier guidance.
</routing>
<tool_strategy>                     ← Concise (200 tokens)
  Traces: analyze_trace_comprehensive first.
  Logs: analyze_bigquery_log_patterns for scale.
  Metrics: query_promql primary, list_time_series secondary.
</tool_strategy>
<memory>                            ← Key rules only (150 tokens)
  Check preloaded memory. Store findings via add_finding_to_memory.
</memory>
<error_handling>                    ← Compact (100 tokens)
  Non-retryable: stop, pivot. MCP fail: use direct API.
</error_handling>
<output_format>                     ← At end (100 tokens)
  Use tables, headers, bold key findings.
</output_format>
```

**Expected gain**: ~60% token reduction (2,500 → ~1,000 tokens). Critical instructions at top where the model attends most strongly.

#### OPT-3: Remove Redundant ReAct Instructions from Panels (MEDIUM IMPACT)

**Problem**: Every panel includes `REACT_PATTERN_INSTRUCTION` (~150 tokens). Gemini 2.5+ natively implements ReAct when given tools — explicit instructions are redundant and can cause over-verbalization.

**Recommendation**: Remove `{REACT_PATTERN_INSTRUCTION}` from all panel prompts in `council/prompts.py`. Keep it only for the root agent prompt (which handles complex multi-step reasoning).

**Expected gain**: 750 fewer tokens per Standard council run (150 x 5 panels). Panels respond faster without verbose Thought/Action/Observation formatting.

#### OPT-4: Unify Sub-Agents and Council Panels (MEDIUM IMPACT)

**Problem**: The codebase has two parallel systems for the same domains:
- **Sub-agents** (`sub_agents/trace.py`, `sub_agents/logs.py`, etc.) — used by the 3-stage pipeline
- **Council panels** (`council/panels.py`) — used by council mode

They have different prompts and different tool sets for the same domain.

**Recommendation**: Consolidate. Use the council panel factories (`create_trace_panel()`, etc.) as the single source for domain specialists. The 3-stage orchestration tools (`run_triage_analysis`, etc.) should invoke panel agents instead of maintaining separate sub-agent definitions.

**Expected gain**: Single set of prompts to maintain. Consistent behavior regardless of invocation path.

#### OPT-5: Downgrade Sub-Agent Models Where Appropriate (HIGH IMPACT)

**Problem**: Several sub-agents use `deep` (Gemini Pro) that could use `fast` (Gemini Flash):

| Agent | Current | Recommended | Rationale |
|:------|:--------|:------------|:----------|
| `aggregate_analyzer` | deep | deep | Complex SQL generation — keep |
| `log_analyst` | deep | **fast** | Pattern extraction is structured — Flash handles it |
| `metrics_analyzer` | deep | **fast** | PromQL queries are formulaic — Flash is sufficient |
| `root_cause_analyst` | deep | deep | Complex reasoning — keep |
| `council_synthesizer` | deep | deep | Cross-panel synthesis — keep |
| `council_critic` | deep | **fast** | Comparison/checklist task — Flash handles it |

**Expected gain**: 3-10x cost reduction on 3 of 6 LLM-calling agents. Faster responses (Flash is ~3x faster than Pro).

#### OPT-6: Use Positive Framing in Constraints (MEDIUM IMPACT)

**Problem**: Many prompts use negative framing:
- "Do NOT use `gke_container`"
- "NEVER hallucinate trace IDs"
- "Do NOT perform organization-wide sweeps"

Research shows negative instructions are less reliably followed than positive ones.

**Recommendation**: Reframe as positive assertions:
- "Use `k8s_container` as the resource type for GKE."
- "Only fetch trace IDs found in logs, metrics, or list results."
- "Scope all queries to the `[CURRENT PROJECT]` provided."

#### OPT-7: Conditional Tool Instructions (MEDIUM IMPACT)

**Problem**: The root prompt contains detailed instructions for every tool category (traces, logs, metrics, GKE, SLO) even when the user's query only needs one.

**Recommendation**: Build the system prompt dynamically based on `route_request()` result:
- If routing to DIRECT/traces → include only trace tool instructions
- If routing to COUNCIL → include only orchestration instructions
- This can be implemented via ADK's dynamic `instruction` (callable that returns string)

**Expected gain**: 40-60% prompt reduction for simple queries. Model focuses on relevant instructions only.

#### OPT-8: Add `skip_summarization` to Data-Returning Tools (LOW-MEDIUM IMPACT)

**Problem**: Tools like `fetch_trace`, `list_log_entries`, `list_time_series` return structured JSON that doesn't need LLM summarization before the agent processes it.

**Recommendation**: Set `skip_summarization=True` on tools that return structured data intended for agent consumption, not user display.

**Expected gain**: Eliminates one LLM round-trip per tool call for applicable tools.

#### OPT-9: Strengthen Synthesizer Prompt with Cross-Referencing (MEDIUM IMPACT)

**Problem**: The synthesizer prompt instructs "be decisive" but doesn't explicitly require cross-referencing panel findings for contradictions.

**Recommendation**: Add explicit cross-referencing instructions:
```
For each panel finding:
1. Check if other panels corroborate or contradict it
2. Weight evidence by panel confidence scores
3. If panels disagree, explain the contradiction and state which evidence is stronger
4. Frame panel outputs as EVIDENCE to evaluate, not conclusions to accept
```

Research on Mixture-of-Agents shows that framing sub-agent outputs as "evidence" rather than "conclusions" significantly improves aggregation quality.

#### OPT-10: Enable Vertex AI Context Caching (HIGH IMPACT)

**Problem**: Static system prompts (~1,000-2,500 tokens) are re-sent on every turn, paying full input token pricing.

**Recommendation**: Enable Vertex AI context caching for the root agent's system prompt. Cached tokens are priced at 75% discount. The static portion of the prompt (everything except the timestamp) can be cached.

**Expected gain**: Up to 75% cost reduction on system prompt tokens across all turns.

---

### Priority Implementation Order

| Priority | Optimization | Effort | Impact |
|:---------|:-------------|:-------|:-------|
| **P0** | OPT-1: Slim tools default | Low (env var flip) | High |
| **P0** | OPT-2: Compress root prompt | Medium (rewrite) | High |
| **P0** | OPT-5: Downgrade models | Low (3 line changes) | High |
| **P1** | OPT-3: Remove ReAct from panels | Low (delete 5 lines) | Medium |
| **P1** | OPT-6: Positive framing | Medium (audit all prompts) | Medium |
| **P1** | OPT-10: Context caching | Medium (Vertex config) | High |
| **P2** | OPT-7: Conditional instructions | High (dynamic prompt) | Medium |
| **P2** | OPT-4: Unify sub-agents/panels | High (refactor) | Medium |
| **P2** | OPT-9: Strengthen synthesizer | Low (prompt edit) | Medium |
| **P3** | OPT-8: skip_summarization | Low (per-tool flag) | Low |

---

### Token Budget Analysis

**Current estimated tokens per Standard Council investigation:**

| Component | Input Tokens | Output Tokens | LLM Calls |
|:----------|:-------------|:--------------|:----------|
| Root agent (route + orchestrate) | ~4,000 | ~500 | 2 |
| 5 Panel agents (parallel) | 5 x ~2,000 = 10,000 | 5 x ~500 = 2,500 | 5 |
| Synthesizer | ~3,000 | ~800 | 1 |
| Tool summarization overhead | ~2,000 | ~1,000 | ~5 |
| **Total** | **~19,000** | **~4,800** | **~13** |

**After applying P0 optimizations (OPT-1, 2, 5):**

| Component | Input Tokens | Output Tokens | LLM Calls |
|:----------|:-------------|:--------------|:----------|
| Root agent (slim tools + compressed prompt) | ~1,500 | ~300 | 2 |
| 5 Panel agents (no ReAct) | 5 x ~1,200 = 6,000 | 5 x ~500 = 2,500 | 5 |
| Synthesizer | ~3,000 | ~800 | 1 |
| Tool summarization | ~1,000 | ~500 | ~3 |
| **Total** | **~11,500** | **~4,100** | **~11** |

**Estimated savings: ~40% input tokens, ~15% output tokens, ~15% fewer LLM calls.**

---

*Last updated: 2026-02-10 — Generated from codebase analysis*
