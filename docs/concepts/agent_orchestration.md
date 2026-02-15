# Agent Engine & Reasoning

This document explores the "brain" of the SRE Agent, detailing the orchestration logic, the analysis pipeline, the Council of Experts architecture, and the prompt engineering strategies that drive its diagnostic capabilities.

## The Council of Experts Orchestration

The SRE Agent uses a **Council of Experts** pattern, where a central `root_agent` manages a team of specialized sub-agents. This modularity allows for deeper expertise in specific domains (like Traces or Metrics) while maintaining a unified conversational interface.

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
- **Logic**: Analyzes critical path latency, error propagation, and correlating log patterns (Drain3 clustering).

### Stage 2: Deep Dive (Causality & Impact)
- **Sub-Agent**: `root_cause_analyst`
- **Method**: Synthesizes Triage findings. Searches for recent deployments, config changes, or downstream failures.
- **Output**: Root cause hypothesis, blast radius assessment, and remediation plan.

---

## 3-Tier Request Routing

Before the council or pipeline is invoked, the SRE Agent classifies every incoming query through a **3-tier router** (`sre_agent/council/intent_classifier.py :: classify_routing`). This determines how to handle the request at the coarsest level:

| Tier | Decision | Behavior | Example |
| :--- | :--- | :--- | :--- |
| **DIRECT** | Simple data retrieval | Call individual tools directly (no sub-agent) | "Show me the latest alerts", "Get trace abc123" |
| **SUB_AGENT** | Focused analysis | Delegate to a specialist sub-agent | "Analyze the latency in checkout-service" |
| **COUNCIL** | Complex multi-signal | Start a full council investigation | "What caused the P0 outage in production?" |

The router uses keyword matching, pattern rules, and signal-type detection to classify queries. Signal types (trace, metrics, logs, alerts) determine which tools or sub-agents are suggested for the DIRECT and SUB_AGENT tiers. The `RoutingResult` dataclass (`sre_agent/council/schemas.py :: RoutingDecision`) carries the decision, signal type, suggested tools, and suggested agent.

---

## Parallel Council Architecture (Council 2.0)

The **Parallel Council** is a complementary investigation mode that runs alongside the existing 3-stage pipeline. While the pipeline provides sequential depth (Aggregate > Triage > Deep Dive), the council provides **parallel breadth** -- five specialist panels examine the same incident simultaneously, then a synthesizer merges their findings into a unified assessment.

### Specialist Panels

The council dispatches **five** specialist panels via ADK `ParallelAgent`, each with domain-specific tools from the centralized tool registry (`sre_agent/council/tool_registry.py`):

| Panel | Agent ID | Focus | Output Key | Key Tools |
| :--- | :--- | :--- | :--- | :--- |
| **Trace Panel** | `trace_panel` | Distributed trace analysis | `trace_finding` | `analyze_trace_comprehensive`, `analyze_critical_path`, `detect_all_sre_patterns` |
| **Metrics Panel** | `metrics_panel` | Time-series anomaly detection | `metrics_finding` | `query_promql`, `detect_metric_anomalies`, `compare_metric_windows` |
| **Logs Panel** | `logs_panel` | Log pattern recognition | `logs_finding` | `extract_log_patterns`, `analyze_bigquery_log_patterns`, `list_log_entries` |
| **Alerts Panel** | `alerts_panel` | Alert correlation and triage | `alerts_finding` | `list_alerts`, `list_alert_policies`, `get_alert` |
| **Data Panel** | `data_panel` | BigQuery telemetry analytics | `data_finding` | `query_data_agent`, `mcp_execute_sql`, `discover_telemetry_sources` |

Each panel is created by a factory function in `sre_agent/council/panels.py`. All panels:
- Use `get_model_name("fast")` for low-latency responses
- Write structured `PanelFinding` output to session state via `output_key`
- Include `before_model_callback` and `after_model_callback` for cost/token tracking
- Output a validated `PanelFinding` schema (panel identifier, summary, severity, confidence, evidence, recommended actions)

### Tool Registry (OPT-4)

The `sre_agent/council/tool_registry.py` module is the **single source of truth** for all domain-specific tool sets. Both council panels (`council/panels.py`) and sub-agents (`sub_agents/*.py`) import tool lists from here to prevent tool set drift. The registry defines:

- **Panel tool sets**: `TRACE_PANEL_TOOLS`, `METRICS_PANEL_TOOLS`, `LOGS_PANEL_TOOLS`, `ALERTS_PANEL_TOOLS`, `DATA_PANEL_TOOLS`
- **Sub-agent tool sets**: `TRACE_ANALYST_TOOLS`, `AGGREGATE_ANALYZER_TOOLS`, `LOG_ANALYST_TOOLS`, `ALERT_ANALYST_TOOLS`, `METRICS_ANALYZER_TOOLS`, `ROOT_CAUSE_ANALYST_TOOLS`
- **Shared cross-cutting tools**: `SHARED_STATE_TOOLS`, `SHARED_RESEARCH_TOOLS`, `SHARED_GITHUB_TOOLS`, `SHARED_REMEDIATION_TOOLS`
- **Orchestrator tools**: `ORCHESTRATOR_TOOLS` (for the slim root agent, OPT-3)

### Investigation Modes

The `IntentClassifier` (`sre_agent/council/intent_classifier.py`) selects one of three investigation modes based on query complexity and urgency. The classification can be done in two ways:

1. **Rule-based** (default): Uses keyword matching and regex patterns. Deterministic with zero latency.
2. **Adaptive/LLM-augmented** (`SRE_AGENT_ADAPTIVE_CLASSIFIER=true`): Uses a lightweight LLM call that considers session history, alert severity, and remaining token budget. Falls back to rule-based on any failure.

Both classifiers produce an `AdaptiveClassificationResult` (`sre_agent/council/schemas.py`) with mode, signal type, confidence, reasoning, and classifier provenance.

#### Mode Details

1. **Fast** (~single panel): For narrowly scoped queries (e.g., "check the latest alerts"). Routes to one relevant panel based on detected signal type, skips synthesis. Lowest latency.
2. **Standard** (5 panels + synthesizer): Default mode. All five panels run in parallel via `ParallelAgent`, then a `Synthesizer` agent (using `get_model_name("deep")`) merges findings into a unified assessment with confidence scores and signal coverage. The synthesizer writes to `council_synthesis` in session state.
3. **Debate** (panels + critic loop): For high-severity or ambiguous incidents. After an initial parallel panel phase and synthesis, a `LoopAgent` drives a critic cross-examination cycle. The `Critic` agent challenges panel findings, identifies contradictions, and requests clarification. The loop continues until confidence gating thresholds are met or the maximum iteration count is reached.

#### Adaptive Classification Features

When `SRE_AGENT_ADAPTIVE_CLASSIFIER=true`, the classifier:
- Considers recent investigation queries from the session
- Factors in alert severity (e.g., critical alerts bias toward DEBATE)
- Respects token budget constraints (low budget downgrades DEBATE to STANDARD)
- Tracks which classifier produced the result (`rule_based`, `llm_augmented`, or `fallback`)
- Falls back gracefully to rule-based on any LLM failure

### Debate Pipeline

In Debate mode, the investigation follows this sequence (implemented in `sre_agent/council/debate.py`):

1. **Initial Panel Phase**: All five panels run in parallel via `ParallelAgent` (same as Standard mode).
2. **Initial Synthesis**: The synthesizer merges the first round of findings.
3. **Debate Loop** (`LoopAgent`): Iteratively:
   a. **Critic**: The `council_critic` agent examines all panel findings, cross-referencing for contradictions, gaps, and unsupported claims. It produces a `CriticReport` (agreements, contradictions, gaps, revised confidence) written to `critic_report` in session state.
   b. **Re-run Panels**: All five panels re-analyze with critic feedback available in session state.
   c. **Re-synthesize**: The synthesizer re-evaluates with updated findings.
4. **Confidence Gating**: The loop terminates when the synthesized confidence score exceeds the threshold (default: 0.85, configurable via `CouncilConfig.confidence_threshold`) or the maximum number of iterations (default: 3, configurable via `CouncilConfig.max_debate_rounds`) is reached.
5. **Convergence Tracking**: An `after_agent_callback` records per-round convergence metrics in session state under `debate_convergence_history`. Each round records: confidence, confidence delta, critic gaps/contradictions counts, round duration, and whether convergence was achieved.

### CouncilOrchestrator

The `CouncilOrchestrator` (`sre_agent/council/orchestrator.py`) is a `BaseAgent` subclass that manages the full council lifecycle. It:

1. Extracts the user query from the `InvocationContext`
2. Classifies intent (rule-based or adaptive)
3. Builds the appropriate pipeline (fast, standard, or debate)
4. Registers the pipeline as a child agent
5. Streams events from the pipeline with deadline enforcement (configurable `timeout_seconds`, default 120s)
6. Emits timeout warnings if the investigation exceeds the deadline

It is activated via the `SRE_AGENT_COUNCIL_ORCHESTRATOR` feature flag, which replaces the root `LlmAgent` with the orchestrator.

### Council Configuration

The `CouncilConfig` schema (`sre_agent/council/schemas.py`) controls council behavior:

| Parameter | Default | Range | Description |
| :--- | :--- | :--- | :--- |
| `mode` | `standard` | fast/standard/debate | Investigation mode |
| `max_debate_rounds` | 3 | 1-10 | Maximum debate iterations |
| `confidence_threshold` | 0.85 | 0.0-1.0 | Confidence level for early debate termination |
| `timeout_seconds` | 120 | 10-600 | Maximum wall-clock time for the investigation |

### Council Activity Graph

The council produces a detailed `CouncilActivityGraph` (`sre_agent/council/schemas.py`) for visualization in the frontend Mission Control UI. This graph tracks:

- All `AgentActivity` records (identity, type, status, tool calls, LLM calls, parent/child relationships)
- Individual `ToolCallRecord` entries (call ID, tool name, args/result summaries, duration, dashboard category)
- Individual `LLMCallRecord` entries (model, input/output tokens, duration)
- Aggregate statistics (total tool calls, total LLM calls, debate rounds)

Agent types tracked: `ROOT`, `ORCHESTRATOR`, `PANEL`, `CRITIC`, `SYNTHESIZER`, `SUB_AGENT`.

### Feature Flags

| Flag | Description | Default |
| :--- | :--- | :--- |
| `SRE_AGENT_COUNCIL_ORCHESTRATOR` | Replace root LlmAgent with CouncilOrchestrator. Routes queries to parallel panels with debate support. | `false` |
| `SRE_AGENT_SLIM_TOOLS` | Reduce root agent to ~20 orchestration tools. Council panels retain full tool sets. | `true` |
| `SRE_AGENT_ADAPTIVE_CLASSIFIER` | Enable LLM-augmented intent classification with session context awareness. | `false` |

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

### Pipeline Sub-Agents

| Agent | Module | Expertise | Primary Tools (from `tool_registry.py`) |
| :--- | :--- | :--- | :--- |
| `aggregate_analyzer` | `sub_agents/trace.py` | Fleet-wide trace analysis (BigQuery) | `mcp_execute_sql`, `analyze_aggregate_metrics`, `find_exemplar_traces` |
| `trace_analyst` | `sub_agents/trace.py` | Distributed tracing & latency | `analyze_trace_comprehensive`, `compare_span_timings`, `analyze_critical_path` |
| `log_analyst` | `sub_agents/logs.py` | Log pattern recognition (Drain3) | `list_log_entries`, `extract_log_patterns`, `analyze_bigquery_log_patterns` |
| `metrics_analyzer` | `sub_agents/metrics.py` | Time-series & SLOs | `query_promql`, `detect_metric_anomalies`, `compare_metric_windows` |
| `metrics_analyst` | `sub_agents/metrics.py` | Metrics analysis (alternative) | `list_time_series`, `query_promql`, `correlate_trace_with_metrics` |
| `alert_analyst` | `sub_agents/alerts.py` | Incident triaging | `list_alerts`, `list_alert_policies`, `get_alert` |
| `root_cause_analyst` | `sub_agents/root_cause.py` | Causality & synthesis | `perform_causal_analysis`, `build_cross_signal_timeline` |
| `agent_debugger` | `sub_agents/agent_debugger.py` | Agent self-analysis | Agent execution debugging and inspection |

### Council Panel Agents

| Agent | Factory | Expertise | Output Key |
| :--- | :--- | :--- | :--- |
| `trace_panel` | `create_trace_panel()` | Trace investigation | `trace_finding` |
| `metrics_panel` | `create_metrics_panel()` | Metrics investigation | `metrics_finding` |
| `logs_panel` | `create_logs_panel()` | Log investigation | `logs_finding` |
| `alerts_panel` | `create_alerts_panel()` | Alert investigation | `alerts_finding` |
| `data_panel` | `create_data_panel()` | BigQuery analytics (CA Data Agent) | `data_finding` |

### Council Support Agents

| Agent | Factory | Role |
| :--- | :--- | :--- |
| `council_synthesizer` | `create_synthesizer()` | Merges panel findings into unified assessment (uses `get_model_name("deep")`) |
| `council_critic` | `create_critic()` | Cross-examines panel findings for contradictions and gaps (uses `get_model_name("fast")`) |

---

## Council Schemas

The council architecture is built on well-defined Pydantic schemas (all `frozen=True, extra="forbid"`):

| Schema | Purpose |
| :--- | :--- |
| `InvestigationMode` | Enum: FAST, STANDARD, DEBATE |
| `RoutingDecision` | Enum: DIRECT, SUB_AGENT, COUNCIL |
| `PanelSeverity` | Enum: CRITICAL, WARNING, INFO, HEALTHY |
| `PanelFinding` | Structured output from each panel (panel ID, summary, severity, confidence, evidence, actions) |
| `CriticReport` | Cross-examination output (agreements, contradictions, gaps, revised confidence) |
| `CouncilResult` | Final merged result (mode, panels, critic report, synthesis, overall severity/confidence, rounds) |
| `CouncilConfig` | Investigation parameters (mode, max rounds, confidence threshold, timeout) |
| `ClassificationContext` | Context for adaptive classification (session history, alert severity, token budget) |
| `AdaptiveClassificationResult` | Classification output with reasoning and provenance |
| `CouncilActivityGraph` | Full activity graph for visualization |
| `AgentActivity` | Per-agent activity record (tool calls, LLM calls, relationships) |

---

## Memory & Intelligence

### Short-term Memory (ADK Session State)
Tracks findings *within* a conversation (e.g., "The target trace is X"). Panel findings, critic reports, and synthesis results are all stored in session state.

### Long-term Memory (Vertex AI Memory Bank)
A vector-searchable database where key findings from *all* past investigations are stored. Tools like `search_memory` allow the agent to solve issues faster by recalling similar past incidents. See [Memory Best Practices](memory.md) for full details.

---

*Last verified: 2026-02-15 -- Auto SRE Team*
