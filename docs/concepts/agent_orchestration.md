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

## Parallel Council Architecture

The **Parallel Council** is a complementary investigation mode that runs alongside the existing 3-stage pipeline. While the pipeline provides sequential depth (Aggregate → Triage → Deep Dive), the council provides **parallel breadth** — four specialist panels examine the same incident simultaneously, then a synthesizer merges their findings into a unified assessment.

### Specialist Panels

The council dispatches four specialist panels via ADK `ParallelAgent`, each with domain-specific tools:

| Panel | Agent ID | Focus | Key Tools |
| :--- | :--- | :--- | :--- |
| **Trace Panel** | `trace_panel` | Distributed trace analysis | `analyze_trace_comprehensive`, `build_call_graph`, `analyze_critical_path` |
| **Metrics Panel** | `metrics_panel` | Time-series anomaly detection | `query_promql`, `detect_metric_anomalies`, `analyze_slo_burn_rate` |
| **Logs Panel** | `logs_panel` | Log pattern recognition | `extract_log_patterns`, `compare_log_patterns`, `search_logs` |
| **Alerts Panel** | `alerts_panel` | Alert correlation and triage | `list_alerts`, `correlate_incident_with_slo_impact`, `get_alert_details` |

### Investigation Modes

The `IntentClassifier` (rule-based) selects one of three modes based on query complexity and urgency:

1. **Fast** (~single panel): For narrowly scoped queries (e.g., "check the latest alerts"). Routes to one relevant panel, skips synthesis. Lowest latency.
2. **Standard** (4 panels + synthesizer): Default mode. All four panels run in parallel via `ParallelAgent`, then a `Synthesizer` agent merges findings into a unified assessment with confidence scores and signal coverage.
3. **Debate** (panels + critic loop): For high-severity or ambiguous incidents. After the parallel panel phase, a `LoopAgent` drives a critic cross-examination cycle. The `Critic` agent challenges panel findings, identifies contradictions, and requests clarification. The loop continues until confidence gating thresholds are met or the maximum iteration count is reached.

### Debate Pipeline

In Debate mode, the investigation follows this sequence:

1. **Panel Phase**: All four panels run in parallel (same as Standard mode).
2. **Critic Loop** (`LoopAgent`): The critic agent examines all panel findings, cross-referencing for contradictions, gaps, and unsupported claims. It produces a `CriticReport` with specific challenges.
3. **Panel Response**: Challenged panels re-examine their evidence and refine findings.
4. **Confidence Gating**: The loop terminates when the synthesized confidence score exceeds the threshold (default: 0.8) or the maximum number of iterations (default: 3) is reached.
5. **Synthesis**: The synthesizer merges all findings into a final `CouncilResult`.

### CouncilOrchestrator

The `CouncilOrchestrator` is a `BaseAgent` subclass that manages the full council lifecycle. It handles mode selection, panel dispatch, debate loops, and synthesis. It is activated via the `SRE_AGENT_COUNCIL_ORCHESTRATOR` feature flag, which replaces the root `LlmAgent` with the orchestrator.

### Feature Flags

| Flag | Description | Default |
| :--- | :--- | :--- |
| `SRE_AGENT_COUNCIL_ORCHESTRATOR` | Replace root LlmAgent with CouncilOrchestrator. Routes queries to parallel panels with debate support. | `false` |
| `SRE_AGENT_SLIM_TOOLS` | Reduce root agent to ~20 orchestration tools. Council panels retain full tool sets. | `true` |

### Relationship to the 3-Stage Pipeline

The council architecture is **complementary**, not a replacement for the 3-stage pipeline:

- The **3-stage pipeline** provides sequential depth: fleet-wide aggregation, then triage, then deep dive into root cause.
- The **parallel council** provides simultaneous breadth: all signal domains are examined at once, with optional adversarial refinement via the debate loop.

When the council orchestrator is active, it can delegate to the existing pipeline stages or run its own parallel investigation, depending on the investigation mode selected by the intent classifier.

---

### Investigation Flow
![Investigation Flow](../images/flow.jpg)

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
| `trace_panel` | Council: Trace Investigation | `analyze_trace_comprehensive`, `build_call_graph`, `analyze_critical_path` |
| `metrics_panel` | Council: Metrics Investigation | `query_promql`, `detect_metric_anomalies`, `analyze_slo_burn_rate` |
| `logs_panel` | Council: Log Investigation | `extract_log_patterns`, `compare_log_patterns`, `search_logs` |
| `alerts_panel` | Council: Alert Investigation | `list_alerts`, `correlate_incident_with_slo_impact`, `get_alert_details` |

---

## Memory & Intelligence

### Short-term Memory (ADK Session State)
Tracks findings *within* a conversation (e.g., "The target trace is X").

### Long-term Memory (Vertex AI Memory Bank)
A vector-searchable database where key findings from *all* past investigations are stored. Tools like `search_memory` allow the agent to solve issues faster by recalling similar past incidents.
