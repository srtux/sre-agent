# Agent Engine & Reasoning

This document explores the "brain" of the SRE Agent, detailing the orchestration logic, the analysis pipeline, and the prompt engineering strategies that drive its diagnostic capabilities.

## The Core Squad Orchestration

The SRE Agent uses a **Core Squad** pattern, where a central `root_agent` manages a team of specialized sub-agents. This modularity allows for deeper expertise in specific domains (like Traces or Metrics) while maintaining a unified conversational interface.

---

## The 3-Stage Analysis Pipeline

To ensure rigorous investigations, the engine follows a structured 3-stage pipeline:

### Stage 0: Aggregate Analysis (Fleet-wide)
- **Sub-Agent**: `aggregate_analyzer`
- **Method**: Queries BigQuery (OpenTelemetry span data) to identify outliers across the entire service fleet.
- **Output**: Identification of outlier service, baseline vs. target trace IDs.

### Stage 1: Triage (Anatomy of a Failure)
- **Sub-Agents**: `trace_analyst`, `log_analyst`
- **Method**: Parallel deep-dive into the "Bad" trace vs. the "Good" baseline.
- **Logic**: Analyzes critical path latency, error propagation, and correlating log patterns ( Drain3 clustering).

### Stage 2: Deep Dive (Causality & Impact)
- **Sub-Agent**: `root_cause_analyst`
- **Method**: Synthesizes Triage findings. Searches for recent deployments, config changes, or downstream failures.
- **Output**: Root cause hypothesis, blast radius assessment, and remediation plan.

---

## Prompt Engineering Strategy

The agent's intelligence is defined in `sre_agent/prompt.py`.

### ReAct Thinking Loop
Every decision is structured via the **ReAct (Reasoning + Acting)** pattern:
- **Thought**: "I see a latency spike in `cart-service`. I suspect `redis-cache` might be the bottleneck."
- **Action**: `analyze_critical_path(trace_id="...")`
- **Observation**: "Observation: `redis-cache` responded in 2ms. However, `auth-service` took 800ms."
- **Answer**: "The bottleneck is actually the `auth` layer, specifically during signature verification."

### Personal Branding & Emojis
The agent is designed to be a "friendly sidekick" with a distinct personality. High emoji density and a helpful tone make complex SRE reports easier to digest for humans.

### Strict EUC Constraints
Prompts strictly enforce **Project Context**. The agent is prohibited from scanning the entire organization unless explicitly commanded, preventing "data tourism" and ensuring performance.

---

## Specialized Sub-Agents

| Agent | Expertise | Primary Tools |
| :--- | :--- | :--- |
| `trace_analyst` | Distributed Tracing | `analyze_trace_comprehensive`, `build_call_graph` |
| `log_analyst` | Pattern Recognition | `extract_log_patterns`, `compare_log_patterns` |
| `metrics_analyzer`| Time-series & SLOs | `query_promql`, `detect_metric_anomalies` |
| `alert_analyst` | Incident Triaging | `list_alerts`, `correlate_incident_with_slo_impact` |
| `root_cause` | Causality & Synthesis | `perform_causal_analysis`, `synthesize_report` |

---

## Memory & Intelligence

### Short-term Memory (ADK Session State)
Tracks findings *within* a conversation (e.g., "The target trace is X").

### Long-term Memory (Vertex AI Memory Bank)
A vector-searchable database where key findings from *all* past investigations are stored. Tools like `search_memory` allow the agent to solve issues faster by recalling similar past incidents.
