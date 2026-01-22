# SRE Agent Sub-Agents

This directory contains specialized sub-agents that form the **"Core Squad"** orchestration pattern used by the main SRE Agent.

## Architecture Overview

The SRE Agent uses a multi-stage analysis pipeline where specialized sub-agents handle different aspects of investigation. This consolidation from the previous "Council of Experts" into a "Core Squad" reduces overhead and simplifies orchestration.

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
│  │   trace_analyst   │ │    log_analyst    │ │  metrics_analyzer │  │
│  │ (Latency, Errors, │ │ (Patterns, Regex, │ │ (Anomalies, Promo) │  │
│  │  Resiliency)      │ │  Drain3)          │ │                   │  │
│  └───────────────────┘ └───────────────────┘ └───────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Stage 2: Deep Dive (Synthesis)                                      │
│  ┌───────────────────┐                                               │
│  │root_cause_analyst │                                               │
│  │(Causality, Impact,│                                               │
│  │ Change Correl.)   │                                               │
│  └───────────────────┘                                               │
└─────────────────────────────────────────────────────────────────────┘
```

## Sub-Agent Files

| File | Sub-Agents | Description |
|------|------------|-------------|
| `trace.py` | `aggregate_analyzer`, `trace_analyst` | Core trace analysis pipeline |
| `logs.py` | `log_analyst` | Log pattern analysis |
| `metrics.py` | `metrics_analyzer` | Metrics analysis |
| `alerts.py` | `alert_analyst` | Alert triage (First Responder) |
| `root_cause.py` | `root_cause_analyst` | Root cause synthesis |

## Detailed Sub-Agent Descriptions

### Stage 0: Aggregate Analysis

#### `aggregate_analyzer` (trace.py)
- **Role**: Data Analyst
- **Persona**: "The Big Data Ninja" 🥷🐼
- **Purpose**: Analyze fleet-wide patterns using BigQuery before diving into specific traces.
- **Tools**: `mcp_execute_sql`, `analyze_aggregate_metrics`, `find_exemplar_traces`, `discover_telemetry_sources`, `list_traces`.

#### `alert_analyst` (alerts.py)
- **Role**: First Responder
- **Persona**: "The Dispatcher" 🚨
- **Purpose**: Triage incoming alerts and policy violations.
- **Tools**: `list_alerts`, `get_alert`, `list_alert_policies`.

### Stage 1: Specialized Analysts

#### `trace_analyst` (trace.py)
- **Role**: Trace Expert
- **Persona**: "The Diagnostic Specialist" 🏎️🩺
- **Purpose**: Consolidated analysis of latency, errors, structure, and resiliency.
- **Tools**: `analyze_trace_comprehensive`, `compare_span_timings`, `analyze_critical_path`, `detect_all_sre_patterns`.

#### `log_analyst` (logs.py)
- **Role**: Log Whisperer
- **Persona**: "The Pattern Seeker" 📜
- **Purpose**: Mine error patterns from logs using BigQuery SQL and Drain3.
- **Tools**: `analyze_bigquery_log_patterns`, `extract_log_patterns`, `mcp_list_log_entries`.

#### `metrics_analyzer` (metrics.py)
- **Role**: Metrics Maestro
- **Persona**: "The Number Cruncher" 📊
- **Purpose**: Analyze time-series data and detect metric anomalies.
- **Tools**: `query_promql`, `mcp_list_timeseries`, `mcp_query_range`, `detect_metric_anomalies`.

### Stage 2: Deep Dive Investigation

#### `root_cause_analyst` (root_cause.py)
- **Role**: Consulting Detective
- **Persona**: "The SRE Sherlock" 🕵️‍♂️
- **Purpose**: Synthesize findings across all signals to determine causality, impact, and triggers.
- **Tools**: `analyze_upstream_downstream_impact`, `perform_causal_analysis`, `correlate_logs_with_trace`.

## Orchestration Functions

The main agent uses these orchestration functions in `agent.py` to invoke the Core Squad:

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
