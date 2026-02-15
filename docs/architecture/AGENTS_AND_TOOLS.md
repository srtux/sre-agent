# Auto SRE: Complete Agent & Tool Architecture

> **Purpose**: Comprehensive map of every agent, sub-agent, panel, and tool — how they connect, which prompts they use, and where the code lives. Includes optimization analysis and implementation status.

---

## Table of Contents

1. [Architecture Diagram](#architecture-diagram)
2. [Agent Hierarchy Table](#agent-hierarchy-table)
3. [Prompt Registry](#prompt-registry)
4. [Complete Tool Inventory](#complete-tool-inventory)
5. [Tool-to-Agent Assignment Matrix](#tool-to-agent-assignment-matrix)
6. [Data Flow Diagrams](#data-flow-diagrams)
7. [Architecture Analysis & Optimization Status](#architecture-analysis--optimization-status)

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
    │                      │  │  :39                     │
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
│                     Model: gemini-2.5-flash                          │
│                     Prompt: SRE_AGENT_PROMPT                        │
│                     Tools: ~39 slim (default) or ~80 full           │
│                            + preload_memory + load_memory           │
│                     Code: sre_agent/agent.py                        │
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
│    │(deep)    │   │(fast)       │  │(fast)    │  │(fast)    │    │
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
│              council/orchestrator.py:39                              │
│              No LLM — pure routing logic                            │
│              (or LLM-augmented with adaptive classifier)            │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │     classify_intent_with_signal() → mode + signal_type      │    │
│  │     (or adaptive_classify() if ADAPTIVE_CLASSIFIER=true)    │    │
│  │     council/intent_classifier.py + adaptive_classifier.py   │    │
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
                    │    Critic (fast)              │
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
| **sre_agent** | `LlmAgent` | `fast` (Gemini 2.5 Flash) | [`agent.py:1554`](../../sre_agent/agent.py#L1554) | [`SRE_AGENT_PROMPT`](../../sre_agent/prompt.py#L31) | Default root agent. Slim tool set (~39, OPT-1), 7 sub-agents, 3-tier router |
| **CouncilOrchestrator** | `BaseAgent` | None (no LLM) | [`council/orchestrator.py:39`](../../sre_agent/council/orchestrator.py#L39) | None | Alternative root. Pure routing to Fast/Standard/Debate pipelines. Supports adaptive classifier (`SRE_AGENT_ADAPTIVE_CLASSIFIER=true`) |

### Sub-Agents (children of sre_agent)

| Agent | Model | Code | Prompt Location | Tools | Purpose |
|:------|:------|:-----|:----------------|:------|:--------|
| **aggregate_analyzer** | `deep` (Gemini Pro) | [`sub_agents/trace.py:122`](../../sre_agent/sub_agents/trace.py#L122) | [`AGGREGATE_ANALYZER_PROMPT`](../../sre_agent/sub_agents/trace.py#L28) | via `AGGREGATE_ANALYZER_TOOLS` (14) | Stage 0: Fleet-wide BigQuery analysis |
| **trace_analyst** | `fast` (Gemini Flash) | [`sub_agents/trace.py:103`](../../sre_agent/sub_agents/trace.py#L103) | [`TRACE_ANALYST_PROMPT`](../../sre_agent/sub_agents/trace.py#L68) | via `TRACE_ANALYST_TOOLS` (16) | Stage 1: Individual trace analysis (latency, errors, structure) |
| **log_analyst** | `fast` (Gemini Flash) | [`sub_agents/logs.py:69`](../../sre_agent/sub_agents/logs.py#L69) | [`LOG_ANALYST_PROMPT`](../../sre_agent/sub_agents/logs.py#L29) | via `LOG_ANALYST_TOOLS` (12) | Log pattern mining via BigQuery/Drain3 (OPT-5: downgraded to Flash) |
| **metrics_analyzer** | `fast` (Gemini Flash) | [`sub_agents/metrics.py:92`](../../sre_agent/sub_agents/metrics.py#L92) | [`METRICS_ANALYZER_PROMPT`](../../sre_agent/sub_agents/metrics.py#L36) | via `METRICS_ANALYZER_TOOLS` (13) | Time-series/PromQL/exemplar correlation (OPT-5: downgraded to Flash) |
| **alert_analyst** | `fast` (Gemini Flash) | [`sub_agents/alerts.py:55`](../../sre_agent/sub_agents/alerts.py#L55) | [`ALERT_ANALYST_PROMPT`](../../sre_agent/sub_agents/alerts.py#L26) | via `ALERT_ANALYST_TOOLS` (11) | Alert triage and incident classification |
| **root_cause_analyst** | `deep` (Gemini Pro) | [`sub_agents/root_cause.py:62`](../../sre_agent/sub_agents/root_cause.py#L62) | [`ROOT_CAUSE_ANALYST_PROMPT`](../../sre_agent/sub_agents/root_cause.py#L29) | via `ROOT_CAUSE_ANALYST_TOOLS` (23) | Stage 2: Multi-signal root cause synthesis + research + GitHub self-healing |
| **agent_debugger** | `fast` (Gemini Flash) | [`sub_agents/agent_debugger.py:89`](../../sre_agent/sub_agents/agent_debugger.py#L89) | [`AGENT_DEBUGGER_PROMPT`](../../sre_agent/sub_agents/agent_debugger.py#L40) | 12 | Debugs Vertex Agent Engine interactions |

### Council Panel Agents (created dynamically by pipeline factories)

| Panel Agent | Model | Factory | Prompt | output_key | Tools |
|:------------|:------|:--------|:-------|:-----------|:------|
| **trace_panel** | `fast` | [`panels.py:31`](../../sre_agent/council/panels.py#L31) | [`TRACE_PANEL_PROMPT`](../../sre_agent/council/prompts.py#L30) | `trace_finding` | 23 |
| **metrics_panel** | `fast` | [`panels.py:57`](../../sre_agent/council/panels.py#L57) | [`METRICS_PANEL_PROMPT`](../../sre_agent/council/prompts.py#L64) | `metrics_finding` | 13 |
| **logs_panel** | `fast` | [`panels.py:83`](../../sre_agent/council/panels.py#L83) | [`LOGS_PANEL_PROMPT`](../../sre_agent/council/prompts.py#L98) | `logs_finding` | 8 |
| **alerts_panel** | `fast` | [`panels.py:109`](../../sre_agent/council/panels.py#L109) | [`ALERTS_PANEL_PROMPT`](../../sre_agent/council/prompts.py#L132) | `alerts_finding` | 11 |
| **data_panel** | `fast` | [`panels.py:134`](../../sre_agent/council/panels.py#L134) | [`DATA_PANEL_PROMPT`](../../sre_agent/council/prompts.py#L170) | `data_finding` | 6 |

### Council Meta-Agents (created dynamically)

| Agent | Model | Factory | Prompt | output_key | Purpose |
|:------|:------|:--------|:-------|:-----------|:--------|
| **council_synthesizer** | `deep` | [`synthesizer.py:16`](../../sre_agent/council/synthesizer.py#L16) | [`SYNTHESIZER_PROMPT`](../../sre_agent/council/prompts.py#L260) | `council_synthesis` | Merges all panel findings into unified assessment (OPT-9: cross-referencing) |
| **council_critic** | `fast` | [`critic.py:14`](../../sre_agent/council/critic.py#L14) | [`CRITIC_PROMPT`](../../sre_agent/council/prompts.py#L218) | `critic_report` | Cross-examines panel findings (OPT-5: downgraded to Flash) |

### Workflow Agents (ADK primitives, no LLM)

| Agent | Type | Code | Purpose |
|:------|:-----|:-----|:--------|
| **parallel_panels** | `ParallelAgent` | [`parallel_council.py:47`](../../sre_agent/council/parallel_council.py#L47) | Runs 5 panels concurrently |
| **council_pipeline** | `SequentialAgent` | [`parallel_council.py:60`](../../sre_agent/council/parallel_council.py#L60) | Panels → Synthesizer |
| **initial_panels** | `ParallelAgent` | [`debate.py:214`](../../sre_agent/council/debate.py#L214) | Initial parallel analysis (debate) |
| **debate_panels** | `ParallelAgent` | [`debate.py:238`](../../sre_agent/council/debate.py#L238) | Re-run panels with critic feedback (inside loop) |
| **debate_loop** | `LoopAgent` | [`debate.py:230`](../../sre_agent/council/debate.py#L230) | Critic → Panels → Synthesizer loop (max 3 iters) |
| **debate_pipeline** | `SequentialAgent` | [`debate.py:257`](../../sre_agent/council/debate.py#L257) | Initial analysis → Debate loop |

---

## Prompt Registry

Every prompt in the system, with location and approximate token count.

| Prompt Constant | Used By | File | Line | Est. Tokens |
|:----------------|:--------|:-----|:-----|:------------|
| [`SRE_AGENT_PROMPT`](../../sre_agent/prompt.py#L31) | `sre_agent` (root) | `prompt.py` | 31 | ~1,000 (OPT-2: compressed from ~2,500) |
| [`STRICT_ENGLISH_INSTRUCTION`](../../sre_agent/prompt.py#L7) | All agents (via inclusion) | `prompt.py` | 7 | ~50 |
| [`REACT_PATTERN_INSTRUCTION`](../../sre_agent/prompt.py#L20) | Root agent only (OPT-3) | `prompt.py` | 20 | ~150 |
| [`PROJECT_CONTEXT_INSTRUCTION`](../../sre_agent/prompt.py#L11) | All agents (via inclusion) | `prompt.py` | 11 | ~60 |
| [`CROSS_SIGNAL_CORRELATOR_PROMPT`](../../sre_agent/prompt.py#L100) | (Unused — legacy) | `prompt.py` | 100 | ~300 |
| [`AGGREGATE_ANALYZER_PROMPT`](../../sre_agent/sub_agents/trace.py#L28) | `aggregate_analyzer` | `sub_agents/trace.py` | 28 | ~400 (OPT-6: XML tags) |
| [`TRACE_ANALYST_PROMPT`](../../sre_agent/sub_agents/trace.py#L68) | `trace_analyst` | `sub_agents/trace.py` | 68 | ~400 (OPT-6: XML tags) |
| [`LOG_ANALYST_PROMPT`](../../sre_agent/sub_agents/logs.py#L29) | `log_analyst` | `sub_agents/logs.py` | 29 | ~400 (OPT-6: compressed from ~700) |
| [`METRICS_ANALYZER_PROMPT`](../../sre_agent/sub_agents/metrics.py#L36) | `metrics_analyzer` | `sub_agents/metrics.py` | 36 | ~700 (OPT-6: compressed from ~1,200) |
| [`ALERT_ANALYST_PROMPT`](../../sre_agent/sub_agents/alerts.py#L26) | `alert_analyst` | `sub_agents/alerts.py` | 26 | ~250 (OPT-6: compressed) |
| [`ROOT_CAUSE_ANALYST_PROMPT`](../../sre_agent/sub_agents/root_cause.py#L29) | `root_cause_analyst` | `sub_agents/root_cause.py` | 29 | ~300 (OPT-6: compressed) |
| [`AGENT_DEBUGGER_PROMPT`](../../sre_agent/sub_agents/agent_debugger.py#L40) | `agent_debugger` | `sub_agents/agent_debugger.py` | 40 | ~350 (OPT-6: compressed from ~500) |
| [`TRACE_PANEL_PROMPT`](../../sre_agent/council/prompts.py#L30) | `trace_panel` | `council/prompts.py` | 30 | ~200 (OPT-3: no ReAct) |
| [`METRICS_PANEL_PROMPT`](../../sre_agent/council/prompts.py#L64) | `metrics_panel` | `council/prompts.py` | 64 | ~150 (OPT-3: no ReAct) |
| [`LOGS_PANEL_PROMPT`](../../sre_agent/council/prompts.py#L98) | `logs_panel` | `council/prompts.py` | 98 | ~150 (OPT-3: no ReAct) |
| [`ALERTS_PANEL_PROMPT`](../../sre_agent/council/prompts.py#L132) | `alerts_panel` | `council/prompts.py` | 132 | ~150 (OPT-3: no ReAct) |
| [`DATA_PANEL_PROMPT`](../../sre_agent/council/prompts.py#L170) | `data_panel` | `council/prompts.py` | 170 | ~200 (OPT-3: no ReAct) |
| [`CRITIC_PROMPT`](../../sre_agent/council/prompts.py#L218) | `council_critic` | `council/prompts.py` | 218 | ~300 |
| [`SYNTHESIZER_PROMPT`](../../sre_agent/council/prompts.py#L260) | `council_synthesizer` | `council/prompts.py` | 260 | ~600 (OPT-9: cross-referencing added) |

### Shared Prompt Fragments

```
STRICT_ENGLISH_INSTRUCTION ──┐
PROJECT_CONTEXT_INSTRUCTION ──┼──► Prepended to every sub-agent + panel prompt
REACT_PATTERN_INSTRUCTION ───┘    (panels no longer include ReAct — OPT-3)
```

### Tool Registry (OPT-4: Single Source of Truth)

All domain-specific tool sets are defined in [`council/tool_registry.py`](../../sre_agent/council/tool_registry.py).
Both sub-agents and council panels import from this single registry to prevent tool set drift.

| Tool Set Constant | Used By | Tool Count |
|:-----------------|:--------|:-----------|
| `TRACE_PANEL_TOOLS` | `trace_panel` | 23 |
| `METRICS_PANEL_TOOLS` | `metrics_panel` | 13 |
| `LOGS_PANEL_TOOLS` | `logs_panel` | 8 |
| `ALERTS_PANEL_TOOLS` | `alerts_panel` | 11 |
| `DATA_PANEL_TOOLS` | `data_panel` | 6 |
| `TRACE_ANALYST_TOOLS` | `trace_analyst` sub-agent | 16 |
| `AGGREGATE_ANALYZER_TOOLS` | `aggregate_analyzer` sub-agent | 14 |
| `LOG_ANALYST_TOOLS` | `log_analyst` sub-agent | 12 |
| `ALERT_ANALYST_TOOLS` | `alert_analyst` sub-agent | 11 |
| `METRICS_ANALYZER_TOOLS` | `metrics_analyzer` sub-agent | 13 |
| `ROOT_CAUSE_ANALYST_TOOLS` | `root_cause_analyst` sub-agent | 23 |
| `ORCHESTRATOR_TOOLS` | Slim root agent (DIRECT tier) | 14 |
| `SHARED_STATE_TOOLS` | All agents (cross-cutting) | 2 |
| `SHARED_REMEDIATION_TOOLS` | Alert/Log/Root Cause agents | 3 |
| `SHARED_RESEARCH_TOOLS` | Root Cause agent | 2 |
| `SHARED_GITHUB_TOOLS` | Root Cause agent | 4 |

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
| [`analyze_trace_comprehensive`](../../sre_agent/tools/analysis/trace_comprehensive.py) | `tools/analysis/trace_comprehensive.py` | Root, Trace Analyst, Trace Panel |
| [`analyze_critical_path`](../../sre_agent/tools/analysis/correlation/critical_path.py) | `tools/analysis/correlation/critical_path.py` | Root, Trace Analyst, Trace Panel |
| [`calculate_critical_path_contribution`](../../sre_agent/tools/analysis/correlation/critical_path.py) | `tools/analysis/correlation/critical_path.py` | Root, Trace Analyst, Trace Panel |
| [`calculate_span_durations`](../../sre_agent/tools/analysis/trace/analysis.py) | `tools/analysis/trace/analysis.py` | Root |
| [`compare_span_timings`](../../sre_agent/tools/analysis/trace/comparison.py) | `tools/analysis/trace/comparison.py` | Root, Trace Analyst, Trace Panel |
| [`find_bottleneck_services`](../../sre_agent/tools/analysis/correlation/critical_path.py) | `tools/analysis/correlation/critical_path.py` | Root, Trace Analyst, Agg. Analyzer, Trace Panel |
| [`analyze_trace_patterns`](../../sre_agent/tools/analysis/trace/statistical_analysis.py) | `tools/analysis/trace/statistical_analysis.py` | Root |
| [`find_structural_differences`](../../sre_agent/tools/analysis/trace/comparison.py) | `tools/analysis/trace/comparison.py` | Root |
| [`summarize_trace`](../../sre_agent/tools/analysis/trace/analysis.py) | `tools/analysis/trace/analysis.py` | Root |
| [`validate_trace_quality`](../../sre_agent/tools/analysis/trace/analysis.py) | `tools/analysis/trace/analysis.py` | Root |
| [`extract_errors`](../../sre_agent/tools/analysis/trace/analysis.py) | `tools/analysis/trace/analysis.py` | Root |
| [`build_call_graph`](../../sre_agent/tools/analysis/trace/analysis.py) | `tools/analysis/trace/analysis.py` | Root |
| [`compute_latency_statistics`](../../sre_agent/tools/analysis/trace/statistical_analysis.py) | `tools/analysis/trace/statistical_analysis.py` | Root |

### Metrics Analysis (6 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`detect_metric_anomalies`](../../sre_agent/tools/analysis/metrics/anomaly_detection.py) | `tools/analysis/metrics/anomaly_detection.py` | Root, Metrics Analyzer, Metrics Panel |
| [`compare_metric_windows`](../../sre_agent/tools/analysis/metrics/anomaly_detection.py) | `tools/analysis/metrics/anomaly_detection.py` | Root, Metrics Analyzer, Metrics Panel |
| [`calculate_series_stats`](../../sre_agent/tools/analysis/metrics/statistics.py) | `tools/analysis/metrics/statistics.py` | Root, Metrics Analyzer, Metrics Panel |
| [`detect_trend_changes`](../../sre_agent/tools/analysis/bigquery/otel.py) | `tools/analysis/bigquery/otel.py` | Root, Agg. Analyzer, Root Cause, Trace Panel |
| [`detect_latency_anomalies`](../../sre_agent/tools/analysis/trace/statistical_analysis.py) | `tools/analysis/trace/statistical_analysis.py` | Root, Trace Analyst, Trace Panel |
| [`compare_time_periods`](../../sre_agent/tools/analysis/bigquery/otel.py) | `tools/analysis/bigquery/otel.py` | Root, Multiple sub-agents, Multiple panels |

### Log Analysis (4 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`extract_log_patterns`](../../sre_agent/tools/analysis/logs/patterns.py) | `tools/analysis/logs/patterns.py` | Root, Log Analyst, Logs Panel |
| [`compare_log_patterns`](../../sre_agent/tools/analysis/logs/patterns.py) | `tools/analysis/logs/patterns.py` | Root |
| [`analyze_log_anomalies`](../../sre_agent/tools/analysis/logs/patterns.py) | `tools/analysis/logs/patterns.py` | Root |
| [`analyze_bigquery_log_patterns`](../../sre_agent/tools/analysis/bigquery/logs.py) | `tools/analysis/bigquery/logs.py` | Root, Log Analyst, Logs Panel |

### SLO/SLI Analysis (5 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`analyze_error_budget_burn`](../../sre_agent/tools/clients/slo.py) | `tools/clients/slo.py` | Root |
| [`analyze_multi_window_burn_rate`](../../sre_agent/tools/analysis/slo/burn_rate.py) | `tools/analysis/slo/burn_rate.py` | Root |
| [`get_slo_status`](../../sre_agent/tools/clients/slo.py) | `tools/clients/slo.py` | Root |
| [`predict_slo_violation`](../../sre_agent/tools/clients/slo.py) | `tools/clients/slo.py` | Root |
| [`correlate_incident_with_slo_impact`](../../sre_agent/tools/clients/slo.py) | `tools/clients/slo.py` | Root |

### Cross-Signal Correlation (7 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`correlate_trace_with_metrics`](../../sre_agent/tools/analysis/correlation/cross_signal.py) | `tools/analysis/correlation/cross_signal.py` | Root, Metrics Analyzer, Root Cause, Metrics Panel |
| [`correlate_metrics_with_traces_via_exemplars`](../../sre_agent/tools/analysis/correlation/cross_signal.py) | `tools/analysis/correlation/cross_signal.py` | Root, Agg. Analyzer, Metrics Analyzer, Trace/Metrics Panels |
| [`correlate_logs_with_trace`](../../sre_agent/tools/analysis/bigquery/otel.py) | `tools/analysis/bigquery/otel.py` | Root, Trace Analyst, Root Cause, Trace Panel |
| [`correlate_trace_with_kubernetes`](../../sre_agent/tools/clients/gke.py) | `tools/clients/gke.py` | Root |
| [`build_cross_signal_timeline`](../../sre_agent/tools/analysis/correlation/cross_signal.py) | `tools/analysis/correlation/cross_signal.py` | Root, Root Cause |
| [`analyze_signal_correlation_strength`](../../sre_agent/tools/analysis/correlation/cross_signal.py) | `tools/analysis/correlation/cross_signal.py` | Root |
| [`correlate_changes_with_incident`](../../sre_agent/tools/analysis/correlation/change_correlation.py) | `tools/analysis/correlation/change_correlation.py` | Root |

### Resiliency Pattern Detection (4 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`detect_all_sre_patterns`](../../sre_agent/tools/analysis/trace/patterns.py) | `tools/analysis/trace/patterns.py` | Root, Trace Analyst, Trace Panel |
| [`detect_retry_storm`](../../sre_agent/tools/analysis/trace/patterns.py) | `tools/analysis/trace/patterns.py` | Root, Trace Analyst, Trace Panel |
| [`detect_cascading_timeout`](../../sre_agent/tools/analysis/trace/patterns.py) | `tools/analysis/trace/patterns.py` | Root, Trace Analyst, Trace Panel |
| [`detect_connection_pool_issues`](../../sre_agent/tools/analysis/trace/patterns.py) | `tools/analysis/trace/patterns.py` | Root, Trace Analyst, Trace Panel |

### Dependency & Structure (4 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`build_service_dependency_graph`](../../sre_agent/tools/analysis/correlation/dependencies.py) | `tools/analysis/correlation/` | Root, Agg. Analyzer, Root Cause, Trace Panel |
| [`find_hidden_dependencies`](../../sre_agent/tools/analysis/correlation/dependencies.py) | `tools/analysis/correlation/` | Root |
| [`detect_circular_dependencies`](../../sre_agent/tools/analysis/correlation/dependencies.py) | `tools/analysis/correlation/` | Root |
| [`analyze_upstream_downstream_impact`](../../sre_agent/tools/analysis/correlation/dependencies.py) | `tools/analysis/correlation/dependencies.py` | Root, Root Cause |

### GKE / Infrastructure (6 tools)

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
| [`generate_remediation_suggestions`](../../sre_agent/tools/analysis/remediation/suggestions.py) | `tools/analysis/remediation/suggestions.py` | Root, Log/Alert/Root Cause sub-agents, Alerts Panel |
| [`estimate_remediation_risk`](../../sre_agent/tools/analysis/remediation/suggestions.py) | `tools/analysis/remediation/suggestions.py` | Root, Log/Alert/Root Cause sub-agents, Alerts Panel |
| [`generate_postmortem`](../../sre_agent/tools/analysis/remediation/postmortem.py) | `tools/analysis/remediation/postmortem.py` | Root |
| [`get_gcloud_commands`](../../sre_agent/tools/analysis/remediation/suggestions.py) | `tools/analysis/remediation/suggestions.py` | Root, Log/Alert/Root Cause sub-agents, Alerts Panel |

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
| [`analyze_aggregate_metrics`](../../sre_agent/tools/analysis/bigquery/otel.py) | `tools/analysis/bigquery/otel.py` | Root, Agg. Analyzer, Trace Panel |
| [`find_exemplar_traces`](../../sre_agent/tools/analysis/bigquery/otel.py) | `tools/analysis/bigquery/otel.py` | Root, Agg. Analyzer, Trace Panel |
| [`query_data_agent`](../../sre_agent/tools/bigquery/ca_data_agent.py) | `tools/bigquery/ca_data_agent.py` | Root, Data Panel |

### Orchestration Tools (7 tools — invoke sub-agents)

| Tool | Code Path | Invokes |
|:-----|:----------|:--------|
| [`run_aggregate_analysis`](../../sre_agent/agent.py#L559) | `agent.py:559` | `aggregate_analyzer` via `AgentTool` |
| [`run_triage_analysis`](../../sre_agent/agent.py#L638) | `agent.py:638` | `trace_analyst` + `log_analyst` in parallel |
| [`run_deep_dive_analysis`](../../sre_agent/agent.py#L716) | `agent.py:716` | `root_cause_analyst` via `AgentTool` |
| [`run_log_pattern_analysis`](../../sre_agent/agent.py#L781) | `agent.py:781` | `log_analyst` via `AgentTool` |
| [`run_council_investigation`](../../sre_agent/agent.py#L966) | `agent.py:966` | Council pipeline (Standard or Debate) |
| [`classify_investigation_mode`](../../sre_agent/council/mode_router.py#L20) | `council/mode_router.py:20` | Rule-based classifier (no LLM) |
| [`route_request`](../../sre_agent/core/router.py#L45) | `core/router.py:45` | Rule-based 3-tier router (no LLM) |

### Discovery & Exploration (2 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`discover_telemetry_sources`](../../sre_agent/tools/discovery/discovery_tool.py) | `tools/discovery/discovery_tool.py` | Root, Agg. Analyzer, Agent Debugger, Multiple panels |
| [`explore_project_health`](../../sre_agent/tools/exploration/explore_health.py) | `tools/exploration/explore_health.py` | Root |

### Investigation State & Memory (8 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`update_investigation_state`](../../sre_agent/tools/investigation.py) | `tools/investigation.py` | Root, All sub-agents, All panels |
| [`get_investigation_summary`](../../sre_agent/tools/investigation.py) | `tools/investigation.py` | Root, All sub-agents, All panels |
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

### Online Research (2 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`search_google`](../../sre_agent/tools/research.py) | `tools/research.py` | Root, Root Cause |
| [`fetch_web_page`](../../sre_agent/tools/research.py) | `tools/research.py` | Root, Root Cause |

### GitHub Self-Healing (4 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`github_read_file`](../../sre_agent/tools/github/tools.py) | `tools/github/tools.py` | Root, Root Cause |
| [`github_search_code`](../../sre_agent/tools/github/tools.py) | `tools/github/tools.py` | Root, Root Cause |
| [`github_list_recent_commits`](../../sre_agent/tools/github/tools.py) | `tools/github/tools.py` | Root, Root Cause |
| [`github_create_pull_request`](../../sre_agent/tools/github/tools.py) | `tools/github/tools.py` | Root, Root Cause |

### Agent Debugging (4 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`list_agent_traces`](../../sre_agent/tools/analysis/agent_trace/tools.py) | `tools/analysis/agent_trace/tools.py` | Root, Agent Debugger |
| [`reconstruct_agent_interaction`](../../sre_agent/tools/analysis/agent_trace/tools.py) | `tools/analysis/agent_trace/tools.py` | Root, Agent Debugger |
| [`analyze_agent_token_usage`](../../sre_agent/tools/analysis/agent_trace/tools.py) | `tools/analysis/agent_trace/tools.py` | Root, Agent Debugger |
| [`detect_agent_anti_patterns`](../../sre_agent/tools/analysis/agent_trace/tools.py) | `tools/analysis/agent_trace/tools.py` | Root, Agent Debugger |

### Miscellaneous (10 tools)

| Tool | Code Path | Used By |
|:-----|:----------|:--------|
| [`get_current_time`](../../sre_agent/tools/common/time.py) | `tools/common/time.py` | Root, Agent Debugger |
| [`get_golden_signals`](../../sre_agent/tools/clients/slo.py) | `tools/clients/slo.py` | Root |
| [`find_similar_past_incidents`](../../sre_agent/tools/analysis/remediation/suggestions.py) | `tools/analysis/remediation/suggestions.py` | Root |
| [`perform_causal_analysis`](../../sre_agent/tools/analysis/trace/statistical_analysis.py) | `tools/analysis/trace/statistical_analysis.py` | Root, Root Cause |
| [`find_example_traces`](../../sre_agent/tools/clients/trace.py) | `tools/clients/trace.py` | Root |
| [`select_traces_manually`](../../sre_agent/tools/analysis/trace/filters.py) | `tools/analysis/trace/filters.py` | Root |
| [`select_traces_from_statistical_outliers`](../../sre_agent/tools/analysis/trace/filters.py) | `tools/analysis/trace/filters.py` | Root |
| [`synthesize_report`](../../sre_agent/tools/reporting.py) | `tools/reporting.py` | Root |
| [`preload_memory_tool`](https://google.github.io/adk-docs/) | ADK built-in | Root (auto each turn) |
| [`load_memory_tool`](https://google.github.io/adk-docs/) | ADK built-in | Root (on-demand) |

**Total: ~118 unique tools** registered in [`TOOL_NAME_MAP`](../../sre_agent/agent.py)

---

## Tool-to-Agent Assignment Matrix

Shows which tools are available to each agent. `R` = Root, `AA` = Aggregate Analyzer, `TA` = Trace Analyst, `LA` = Log Analyst, `MA` = Metrics Analyzer, `AL` = Alert Analyst, `RC` = Root Cause, `AD` = Agent Debugger, `TP` = Trace Panel, `MP` = Metrics Panel, `LP` = Logs Panel, `AP` = Alerts Panel, `DP` = Data Panel. Note: Root Cause now includes research and GitHub self-healing tools.

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
| search_google | x | | | | | | x | | | | | | |
| fetch_web_page | x | | | | | | x | | | | | | |
| github_read_file | x | | | | | | x | | | | | | |
| github_search_code | x | | | | | | x | | | | | | |
| github_list_recent_commits | x | | | | | | x | | | | | | |
| github_create_pull_request | x | | | | | | x | | | | | | |

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

## Architecture Analysis & Optimization Status

### Optimization Implementation Summary

All 10 identified optimizations have been implemented or scaffolded. Here is the status:

| # | Optimization | Status | Files Changed |
|:--|:-------------|:-------|:-------------|
| **OPT-1** | Slim tools default (`SRE_AGENT_SLIM_TOOLS=true`) | **Applied** | `agent.py` |
| **OPT-2** | Compress root prompt (~2,500 → ~1,000 tokens, XML tags, primacy bias) | **Applied** | `prompt.py` |
| **OPT-3** | Remove ReAct from panels (saves ~750 tokens/council run) | **Applied** | `council/prompts.py` |
| **OPT-4** | Unified tool registry (sub-agents + panels share tool sets) | **Applied** | `council/tool_registry.py`, `sub_agents/*.py` |
| **OPT-5** | Downgrade models (log_analyst, metrics_analyzer, critic → Flash) | **Applied** | `sub_agents/logs.py`, `sub_agents/metrics.py`, `council/critic.py` |
| **OPT-6** | Positive framing + XML tags on all prompts | **Applied** | All `sub_agents/*.py`, `council/prompts.py` |
| **OPT-7** | Dynamic root prompt via lambda (timestamp injection) | **Applied** | `agent.py` |
| **OPT-8** | `skip_summarization` support in `@adk_tool` decorator + `prepare_tools()` | **Applied** | `tools/common/decorators.py` |
| **OPT-9** | Synthesizer cross-referencing instructions | **Applied** | `council/prompts.py` |
| **OPT-10** | Context caching config (`SRE_AGENT_CONTEXT_CACHING`) | **Scaffolded** | `model_config.py` |

### Detailed Change Log

#### OPT-1: Slim Tools Default
- **Change**: Flipped `SRE_AGENT_SLIM_TOOLS` default from `"false"` to `"true"` in `agent.py`.
- **Effect**: Root agent now presents ~39 routing/orchestration tools instead of ~80. Specialist tools delegated to sub-agents.
- **Rollback**: Set `SRE_AGENT_SLIM_TOOLS=false` to restore full tool set.

#### OPT-2: Compressed Root Prompt
- **Change**: Rewrote `SRE_AGENT_PROMPT` in `prompt.py` with XML-tagged structure.
- **Structure**: `<constraints>` first (primacy bias), then `<routing>`, `<tool_strategy>`, `<error_handling>`, `<memory>`, `<output_format>`.
- **Token savings**: ~60% reduction (2,500 → ~1,000 tokens per turn).

#### OPT-3: ReAct Removed from Panels
- **Change**: Removed `REACT_PATTERN_INSTRUCTION` from all 5 panel prompts in `council/prompts.py`.
- **Rationale**: Gemini 2.5+ natively implements ReAct when given tools; explicit instructions were redundant and caused over-verbalization.
- **Savings**: ~750 tokens per Standard council run.

#### OPT-4: Unified Tool Registry
- **Change**: Created shared tool set constants in [`council/tool_registry.py`](../../sre_agent/council/tool_registry.py):
  - `TRACE_ANALYST_TOOLS`, `AGGREGATE_ANALYZER_TOOLS`, `LOG_ANALYST_TOOLS`, `ALERT_ANALYST_TOOLS`, `METRICS_ANALYZER_TOOLS`, `ROOT_CAUSE_ANALYST_TOOLS`
  - `SHARED_STATE_TOOLS`, `SHARED_REMEDIATION_TOOLS` for cross-cutting tools
- **Effect**: Sub-agents and panels import from the same source, preventing tool set drift.

#### OPT-5: Model Downgrades
- **Changed**: `log_analyst` (deep → fast), `metrics_analyzer` (deep → fast), `council_critic` (deep → fast).
- **Kept**: `aggregate_analyzer` (deep — complex SQL), `root_cause_analyst` (deep — complex reasoning), `council_synthesizer` (deep — cross-panel synthesis).
- **Savings**: 3-10x cost reduction on 3 agents, ~3x faster response times.

#### OPT-6: Positive Framing + XML Tags
- **Change**: Rewrote all sub-agent prompts with XML tags (`<role>`, `<tool_strategy>`, `<output_format>`).
- **Negative → Positive**: "Do NOT use gke_container" → "Use `k8s_container` for GKE".
- **Removed**: Emojis, verbose persona text.

#### OPT-7: Dynamic Root Prompt
- **Change**: Root agent `instruction` is now a lambda that injects current UTC timestamp.
- **Effect**: Enables future context caching of static prompt prefix.

#### OPT-8: skip_summarization Support
- **Change**: Enhanced `@adk_tool` decorator to accept `skip_summarization` parameter.
- **Usage**: `@adk_tool(skip_summarization=True)` marks tools for direct output (no LLM summarization).
- **Utility**: `prepare_tools()` converts marked functions to `FunctionTool(skip_summarization=True)`.
- **Next step**: Apply `skip_summarization=True` to data-returning tools (`fetch_trace`, `list_log_entries`, etc.).

#### OPT-9: Synthesizer Cross-Referencing
- **Change**: Added `<cross_referencing>` section to `SYNTHESIZER_PROMPT` requiring:
  1. Corroboration/contradiction checks across panels.
  2. Evidence weighting by confidence scores.
  3. Explicit contradiction explanations.
  4. Treating panel outputs as evidence, not conclusions.

#### OPT-10: Context Caching Configuration
- **Change**: Added `is_context_caching_enabled()` and `get_context_cache_config()` to `model_config.py`.
- **Enable**: Set `SRE_AGENT_CONTEXT_CACHING=true` and optionally `SRE_AGENT_CONTEXT_CACHE_TTL=3600`.
- **Status**: Scaffolded — requires ADK-level integration or direct Vertex AI SDK usage for full activation.

---

### Token Budget Analysis (Post-Optimization)

**Estimated tokens per Standard Council investigation (after all optimizations):**

| Component | Before | After | Savings |
|:----------|:-------|:------|:--------|
| Root agent (prompt + tools) | ~4,000 | ~1,500 | -63% |
| 5 Panel agents (prompts) | 5 x ~2,000 = 10,000 | 5 x ~1,200 = 6,000 | -40% |
| Synthesizer | ~3,000 | ~3,000 | 0% |
| Tool summarization overhead | ~2,000 | ~1,000 | -50% |
| **Total** | **~19,000** | **~11,500** | **~40%** |

**Model cost reduction**: 3 agents downgraded from Pro to Flash = ~5x cheaper per call.

---

### Additional Features (Post-OPT)

| Feature | Status | Description |
|:--------|:-------|:------------|
| **Adaptive Classifier** | **Applied** | LLM-augmented intent classification (`council/adaptive_classifier.py`). Considers session history, alert severity, token budget. Feature flag: `SRE_AGENT_ADAPTIVE_CLASSIFIER=true`. |
| **Large Payload Handler** | **Applied** | Auto-summarizes oversized tool outputs via sandbox (`core/large_payload_handler.py`). Sits in `after_tool_callback` chain. |
| **Online Research** | **Applied** | `search_google` and `fetch_web_page` tools (`tools/research.py`). Requires `GOOGLE_CUSTOM_SEARCH_API_KEY` and `GOOGLE_CUSTOM_SEARCH_ENGINE_ID`. |
| **GitHub Self-Healing** | **Applied** | Read, search, list commits, create PRs (`tools/github/`). Available to Root Cause analyst for automated remediation. |
| **Dashboard Explorer** | **Applied** | Direct query endpoints in `api/routers/tools.py` plus NL query translation. Frontend visual data explorer with query language toggle. |
| **Memory Mistake Learning** | **Applied** | `memory/mistake_learner.py`, `mistake_advisor.py`, `mistake_store.py` — continuous learning from investigation patterns. |

*Last updated: 2026-02-15 -- All 10 optimizations applied plus additional features. Tool counts and registry verified against codebase.*
