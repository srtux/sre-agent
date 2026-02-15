# SRE Agent Backend

This directory contains the Python backend for the Auto SRE Agent, built using the Google Agent Development Kit (ADK).

## Package Structure

### Root Modules

| Module | Purpose |
|--------|---------|
| `agent.py` | Main entry point. Defines the orchestrator, system instructions, base tools, 3-stage pipeline (Aggregate > Triage > Deep Dive), and Council of Experts initialization. |
| `auth.py` | Authentication and authorization. End-User Credential (EUC) propagation, token validation, ContextVars for project ID and credentials. |
| `schema.py` | Pydantic models (`frozen=True, extra="forbid"`) for structured output: `BaseToolResponse`, `InvestigationPhase`, `Confidence`, `ToolStatus`, and more. |
| `prompt.py` | System prompt and personality for the main orchestrator agent. Includes shared prompt fragments (`PROJECT_CONTEXT_INSTRUCTION`, `STRICT_ENGLISH_INSTRUCTION`, `REACT_PATTERN_INSTRUCTION`). |
| `model_config.py` | Model configuration. `get_model_name("fast"\|"deep")` for dynamic model selection, Vertex AI context caching (OPT-10). |
| `suggestions.py` | Follow-up suggestion generation. LLM-based contextual suggestions from conversation history and active alerts. |
| `version.py` | Build version and metadata. Reads package version from pyproject.toml, git SHA, and build timestamps. |

### Subpackages

| Directory | Purpose |
|-----------|---------|
| `api/` | FastAPI application layer. App factory (`create_app`), middleware (auth, CORS, tracing), dependency injection, HTTP routers (agent, sessions, tools, health, system, permissions, preferences, help), and helpers (dashboard events, memory events). |
| `core/` | Agent execution engine. Runner, context compaction (sliding window), model callbacks (cost/token tracking, budget enforcement), tool output truncation, large payload sandbox handler, circuit breaker, policy engine, prompt composer, summarizer, approval workflow, graph service, and request routing. |
| `council/` | Parallel Council of Experts architecture. Orchestrator (`BaseAgent` subclass), parallel council, debate mode (LoopAgent with critic), 5 specialist panel factories, synthesizer, intent classifier (rule-based + adaptive LLM-augmented), mode router, tool registry (single source of truth for domain tool sets), and council schemas/prompts. |
| `sub_agents/` | Specialist sub-agents: `aggregate_analyzer`, `trace_analyst`, `log_analyst`, `metrics_analyzer`, `alert_analyst`, `root_cause_analyst`, and `agent_debugger` (Vertex Agent Engine interaction analysis). |
| `tools/` | Tool ecosystem (80+ tools across 14 subdirectories). Analysis modules (trace, logs, metrics, SLO, correlation, BigQuery, agent trace, remediation), GCP API clients, MCP integrations, sandbox code execution, GitHub self-healing, online research, playbooks, discovery, exploration, proactive signals, synthetic data, investigation state, memory, and reporting. |
| `services/` | Business services. Session CRUD (`ADKSessionManager` with SQLite/Vertex AI backends), persistence/storage layer (Firestore/SQLite), Agent Engine client (dual-mode local/remote), and memory service management. |
| `memory/` | Memory subsystem. Memory manager, factory, local memory store, callbacks, mistake learner/advisor/store (learning from past investigations), and content sanitizer. |
| `models/` | Data models. `InvestigationPhase`, `InvestigationState`, and related investigation lifecycle models. |
| `resources/` | GCP resources catalog. Common GCP metrics by service (`gcp_metrics.py`) used by the metrics analyzer for smart metric lookup. |

## Key Components

### 1. Orchestrator (`agent.py`)

The `sre_agent` is an `LlmAgent` using Gemini 2.5 Flash/Pro (via `get_model_name()`). It acts as the manager, deciding which sub-agent or tool to call based on the user's request. It supports three execution modes:

- **Local mode** (`SRE_AGENT_ID` not set): Agent runs in-process in FastAPI.
- **Remote mode** (`SRE_AGENT_ID` set): Forwards to Vertex AI Agent Engine.
- **Council mode** (`SRE_AGENT_COUNCIL_ORCHESTRATOR` set): Enables the parallel Council of Experts architecture.

### 2. Council of Experts (`council/`)

An advanced orchestration pattern with three modes:

| Mode | Trigger | Behavior |
|------|---------|----------|
| **Fast** | Narrow-scope queries | Single-panel dispatch |
| **Standard** | Normal investigations | 5 parallel panels > Synthesizer merge |
| **Debate** | High-severity incidents | Panels > Critic LoopAgent > Confidence gating |

### 3. Sub-Agents (`sub_agents/`)

Specialized agents forming the investigation pipeline:

- **Trace Analysis**: `aggregate_analyzer` (BigQuery fleet analysis), `trace_analyst` (latency, errors, structure, resiliency).
- **Log Analysis**: `log_analyst` (Drain3 pattern extraction, BigQuery SQL).
- **Metrics Analysis**: `metrics_analyzer` (PromQL, anomaly detection, exemplar correlation).
- **Alert Triage**: `alert_analyst` (first responder, alert policy analysis).
- **Deep Dive**: `root_cause_analyst` (multi-signal synthesis, causality, impact, change correlation).
- **Agent Debugging**: `agent_debugger` (Vertex Agent Engine interaction analysis, token usage, anti-pattern detection).

### 4. Tool Response Standardization

All tools follow a strict response contract using the `BaseToolResponse` Pydantic model. This ensures:
- **Consistent Error Handling**: The orchestrator and frontend can predictably detect and display errors.
- **Frontend Optimization**: The GenUI adapter can reliably transform tool results into interactive widgets (spans, charts, logs).
- **Type Safety**: MyPy and Pydantic enforce field-level correctness across the analysis pipeline.

### 5. Services (`services/`)

- **Session Management** (`session.py`): Handles conversation history using ADK's `SessionService`. Supports `DatabaseSessionService` (SQLite) for local dev and `VertexAiSessionService` for production.
- **Storage** (`storage.py`): Manages user preferences via Firestore or SQLite.
- **Agent Engine Client** (`agent_engine_client.py`): Dual-mode client for remote Agent Engine communication.
- **Memory Manager** (`memory_manager.py`): Memory service lifecycle management.

### 6. Execution Engine (`core/`)

- **Runner** (`runner.py`): Agent execution logic with context management.
- **Context Compactor** (`context_compactor.py`): Sliding window compaction to keep context within token budgets.
- **Model Callbacks** (`model_callbacks.py`): Token usage tracking, cost estimation, and budget enforcement.
- **Large Payload Handler** (`large_payload_handler.py`): Sandbox processing for oversized tool outputs.
- **Tool Callbacks** (`tool_callbacks.py`): Tool output truncation safety net.
- **Circuit Breaker** (`circuit_breaker.py`): Three-state (CLOSED/OPEN/HALF_OPEN) failure recovery.
- **Policy Engine** (`policy_engine.py`): Safety guardrails for agent actions.
- **Summarizer** (`summarizer.py`): Event and tool output compression.

### 7. Reporting Pipeline

The investigation culminates in a professional SRE report generated via `synthesize_report`. This pipeline:
- Aggregates findings from multiple specialists (Trace, Log, Metrics, Alerts).
- Standardizes formatting (Markdown) for both structured summaries and human-readable narratives.
- Extracts root cause hypotheses and actionable recommendations.
- Supports postmortem generation via `generate_postmortem`.

## Development

The backend is a FastAPI application (via ADK).

### Running Locally
```bash
uv run poe web        # Backend server only (FastAPI on port 8001)
uv run poe dev        # Full stack (backend + frontend)
uv run poe run        # Terminal agent (adk run)
```

### Tests
```bash
uv run poe test       # pytest + 80% coverage gate
uv run poe test-all   # Backend + Flutter tests
```

### Linting
```bash
uv run poe lint       # Ruff format + lint + MyPy + codespell + deptry
uv run poe lint-all   # Backend + Flutter linters
```
