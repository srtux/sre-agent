# SRE Agent Project Plan & Living Log

This document is the **Single Source of Truth** for the project's evolution. It tracks completed milestones, active development, and the future roadmap.

---

## 📈 Executive Summary
Auto SRE is an autonomous reliability engine for Google Cloud. We are transitioning from a monolithic, reactive tool into a modular, proactive, and memory-aware diagnostic expert.

---

## ✅ Completed Milestones

### Phase 1: Foundation & Modularization (Jan 2026)
**Goal**: Technical debt reduction and reasoning structure.

*   **Modular API Architecture**:
    *   Refactored the 2400-line monolithic `server.py` into a domain-driven package structure in `sre_agent/api/`.
    *   Created specialized routers for `agent`, `sessions`, `tools`, `health`, and `preferences`.
    *   Implemented a FastAPI factory pattern in `sre_agent/api/app.py`.
*   **ReAct Reasoning Upgrade**:
    *   Implemented the **Reasoning + Acting (ReAct)** pattern across all sub-agents.
    *   Standardized prompts to follow the `Thought -> Action -> Observation` loop.
*   **Tool Taxonomy Refactoring**:
    *   Categorized 70+ tools into Signal-centric groups (Fetch vs. Analyze).
    *   Implemented `ToolCategory` enum to help LLM tool selection.
*   **Production Readiness**:
    *   Implemented End-User Credentials (EUC) propagation from Flutter to the backend.
    *   Unified Local (SQLite) and Remote (Vertex) session persistence logic.
    *   Resolved 600+ linting and type errors (Mypy/Ruff).
*   **Knowledge Compaction & Documentation Refactor**:
    *   Consolidated fragmented tracking files (`TASK_LIST.md`, `IMPLEMENTATION_PLAN.md`, etc.) into this living `PROJECT_PLAN.md`.
    *   Synchronized Mermaid diagrams across `README.md` and architecture docs.
    *   Updated `AGENTS.md` and `CLAUDE.md` to establish the new Project Plan as the primary source of truth.
*   **Minimalist Telemetry Transition**:
    *   Removed 1000+ lines of manual OpenTelemetry and Arize instrumentation logic.
    *   Adopted ADK native tracing and Agent Engine observability for internal agent telemetry.
    *   Reduced package dependencies and resolved OTLP export warnings.
*   **Frontend Testing & Injection Overhaul**:
    *   Migrated 100% of frontend services to the **Provider** pattern, enabling hermetic widget testing.
    *   Created `test_helper.dart` with a standardized `wrapWithProviders` utility.
    *   Fixed a "Zero Broken Windows" regression where dashboard tests were failing due to direct singleton access.

---

## 🏗️ Active Roadmap

### Phase 2: Memory & Proactive State (COMPLETED)
**Goal**: Deep context retention and guided investigations.

- [x] **Vertex AI Memory Integration**: Core integration of `VertexAiMemoryBankService` for long-term incident retention.
- [x] **Proactive Search Logic**: Implemented `InvestigationPattern` system to recommend tools based on similar past incidents.
- [x] **Investigation State Machine**: Added formal `InvestigationPhase` tracking (Initiated → Triage → Deep Dive → Remediation).
- [x] **Self-Improvement Protocol**: Agent now reflects on investigations and reinforces successful patterns.
- [ ] **Cross-Agent Handoffs**: Refine the schema for passing context (including negative findings) between sub-agents.
- [x] **Automated CI/CD (Cloud Build)**: Orchestrate full-stack deployment (Agent Engine + Cloud Run) via GCP native triggers with parallelized tracks.

### User Interface & Experience
- [x] **Investigation Dashboard**: Full-featured Flutter dashboard with:
    - **Live Traces**: Waterfall visualization of agent actions.
    - **Log Explorer**: Real-time log filtering and analysis.
    - **Metrics & Alerts**: Visual timeline of incidents.
    - **Remediation**: Risk-assessed step-by-step guidance.

### Phase 2.5: SRE Reliability Suite (COMPLETED — Feb 2026)
**Goal**: Production-grade resilience patterns and advanced SRE tooling.

- [x] **Circuit Breaker Pattern** (`sre_agent/core/circuit_breaker.py`): Three-state breaker (CLOSED/OPEN/HALF_OPEN) with per-tool configuration and singleton registry. Prevents cascading failures when GCP APIs are degraded. (20 tests)
- [x] **Multi-Window SLO Burn Rate Analyzer** (`sre_agent/tools/analysis/slo/burn_rate.py`): Google SRE Workbook multi-window alerting (1h/6h/24h/72h windows) with error budget projection and urgency classification. (19 tests)
- [x] **Change Correlation Tool** (`sre_agent/tools/analysis/correlation/change_correlation.py`): Queries GCP Audit Logs to find and rank recent changes by temporal proximity to incidents. (17 tests)
- [x] **Automated Postmortem Generator** (`sre_agent/tools/analysis/remediation/postmortem.py`): Google SRE-style blameless postmortem with severity assessment, TTD/TTM metrics, and auto-generated P0-P2 action items. (21 tests)
- [x] **Enhanced Investigation Model** (`sre_agent/models/investigation.py`): Structured findings with confidence levels, signal coverage tracking, and quality scoring (0-100). (28 tests)
- [x] **Flutter UI Widgets**: SLO Burn Rate Card and Postmortem Card with Deep Space aesthetic.

Total: **105 new tests**, all passing.

### Phase 2.75: Parallel Council & Debate Architecture (COMPLETED — Feb 2026)
**Goal**: Parallel multi-signal investigation with adversarial refinement.

- [x] **Council of Experts Architecture**: Five parallel specialist panels (Trace, Metrics, Logs, Alerts, Data) running simultaneously via ADK `ParallelAgent`. Each panel has domain-specific tools and prompts.
- [x] **Debate Pipeline**: Critic cross-examination loop using ADK `LoopAgent`. The critic challenges panel findings, identifies contradictions, and drives iterative refinement until confidence gating thresholds are met.
- [x] **Investigation Modes**: Rule-based `IntentClassifier` selects from three modes:
    - **Fast**: Single-panel dispatch for narrowly scoped queries.
    - **Standard**: Four parallel panels followed by synthesizer merge.
    - **Debate**: Panels + critic loop + confidence gating for high-severity incidents.
- [x] **Slim Tools Feature Flag** (`SRE_AGENT_SLIM_TOOLS`): Reduces root agent from ~50 to ~20 orchestration tools. Council panels retain full domain-specific tool sets.
- [x] **CouncilOrchestrator** (`sre_agent/council/orchestrator.py`): `BaseAgent` subclass managing mode selection, panel dispatch, debate loops, and synthesis. Activated via `SRE_AGENT_COUNCIL_ORCHESTRATOR` feature flag.
- [x] **Council Tab in Investigation Dashboard**: Flutter UI panel displaying council panel findings, debate rounds, and synthesized results.
- [x] **Schemas**: `InvestigationMode`, `PanelFinding`, `CriticReport`, `CouncilResult` Pydantic models with `frozen=True, extra="forbid"`.

Total: **174 new council tests**, all passing. Grand total: **1512 tests**.

### Phase 3: Observability & Advanced Diagnostics (IN PROGRESS — Feb 2026)
**Goal**: ADK-native observability, tool discovery, eval coverage, and resilience patterns.

#### Completed
- [x] **ADK Model Callbacks for Cost/Token Tracking** (`sre_agent/core/model_callbacks.py`):
    - `UsageTracker` with thread-safe singleton accumulator for per-agent and aggregate usage.
    - `before_model_callback` enforces configurable token budget (`SRE_AGENT_TOKEN_BUDGET` env var).
    - `after_model_callback` records input/output tokens, duration, and estimated USD cost per model call.
    - Model-specific pricing for Gemini 2.5 Flash/Pro, with prefix-matching for versioned model IDs.
    - Integrated into root `LlmAgent` via `before_model_callback` and `after_model_callback` parameters.
    - (25 tests)
- [x] **Tool Categorization Registry** (`sre_agent/tools/registry.py`):
    - `ToolRegistry` class wrapping `ToolConfigManager` for higher-level tool queries.
    - Signal-type-based discovery (`get_tools_for_signal("trace" | "metrics" | "logs" | "alerts")`).
    - Keyword search across tool names and descriptions.
    - Category summary statistics and agent instruction generation.
    - Module-level singleton with `get_tool_registry()` accessor.
    - (24 tests)
- [x] **Debate Convergence Tracking** (`sre_agent/council/debate.py`):
    - `_build_convergence_tracker()` ADK `after_agent_callback` on debate `LoopAgent`.
    - Tracks per-round: confidence progression, confidence delta, critic gaps/contradictions, round duration.
    - Records convergence history in session state (`debate_convergence_history` key).
    - (16 tests)
- [x] **MCP-to-Direct-API Fallback Chain** (`sre_agent/tools/mcp/fallback.py`):
    - `with_fallback()` async function for transparent MCP-to-direct-API degradation.
    - `_is_mcp_failure()` distinguishes infrastructure errors (connection, session, transport) from user errors (invalid filter, permission denied).
    - Adds `fallback_used` metadata to responses when fallback is triggered.
    - (19 tests)
- [x] **Signal-Type-Aware Intent Classifier** (`sre_agent/council/intent_classifier.py`):
    - `classify_intent_with_signal()` returns `ClassificationResult` with both mode and signal type.
    - `_detect_signal_type()` uses keyword scoring to route FAST queries to the correct panel (TRACE/METRICS/LOGS/ALERTS).
    - Backward-compatible `classify_intent()` wrapper preserved.
    - (28 tests)
- [x] **New Eval Scenarios** (9 cases across 3 files):
    - `eval/kubernetes_debugging.test.json`: Pod CrashLoopBackOff, node pressure, HPA scaling failure.
    - `eval/slo_burn_rate.test.json`: Error budget exhaustion, multi-window SLO violation.
    - `eval/failure_modes.test.json`: Invalid project handling, hallucination resistance, rate limit recovery, cascading multi-service failure.
- [x] **Bug Fixes & Consistency**:
    - Fixed AGENTS.md merge conflict markers (Section 12.1/13).
    - Removed duplicate `correlate_changes_with_incident` from `base_tools`.
    - Removed duplicate project_id discovery in `agent.py`.
    - Added `run_council_investigation` and `classify_investigation_mode` to both `TOOL_NAME_MAP` and `TOOL_DEFINITIONS`.
    - Integrated circuit breaker into `@adk_tool` decorator (was dead code).

Total: **112 new tests** in this phase. Grand total: **1909+** tests passing.

- [x] **Observability Explorer Dashboard Refactor** (Phase 3.5 — Feb 2026):
    Transformed the passive "agent-only" dashboard into an active GCP-style Observability Explorer
    where users can directly query telemetry data alongside agent-provided insights.
    - **Syncfusion Chart Migration**: Replaced `fl_chart` with Syncfusion Community Edition charts (`syncfusion_flutter_charts`, `syncfusion_flutter_datepicker`) for interactive zoom, pan, and trackball tooltips. Created `SyncfusionMetricChart` (line chart with anomaly overlays, trend lines, and stats row) and `SyncfusionTraceWaterfall` (horizontal range bar chart with service color mapping and span detail panel). Deleted 1,935 lines of old FL Chart and custom painter widgets.
    - **Manual Query Capability**: Added `ManualQueryBar` input widget to every dashboard panel (metrics, logs, traces, alerts) so users can directly query GCP telemetry without going through the AI agent.
    - **Backend Query Endpoints**: Added 4 new REST endpoints (`POST /api/tools/metrics/query`, `POST /api/tools/metrics/promql`, `POST /api/tools/alerts/query`, `POST /api/tools/logs/query`) to `sre_agent/api/routers/tools.py`. Fixed all endpoints to properly unwrap `BaseToolResponse` envelopes and apply `genui_adapter.transform_*()` transformations.
    - **Dual Data Source Architecture**: Extended `DashboardState` with `DataSource.agent` / `DataSource.manual` tracking, per-panel loading/error states, `TimeRange` model with preset selectors (1H/6H/1D/1W/Custom), and auto-refresh timer. Created `ExplorerQueryService` as the HTTP client for manual queries.
    - **GCP-Style Toolbar**: Added `SreToolbar` with time range preset chips, custom date range picker, refresh button, and auto-refresh toggle.
    - **Shared UI Components**: Extracted reusable `ErrorBanner`, `SourceBadge`, `ExplorerEmptyState`, and `ShimmerLoading` widgets.
    - **JSON Parsing Hardening**: Applied null-safe defaults (`?? []`, `?? {}`, try-catch on `DateTime.parse`) to 12+ `fromJson` factories in `adk_schema.dart`.
    - **Centralized Chart Theme**: Created `chart_theme.dart` with Deep Space palette integration for all Syncfusion chart elements.
    - 6 new backend API tests, updated existing tests to use `BaseToolResponse` mocks. Grand total: **1989 backend tests**, **129 Flutter tests** passing.

- [x] **Full-Stack Code Audit & Hardening** (Phase 3.6 — Feb 2026):
    Comprehensive 6-layer audit across backend, frontend, council, tools, and tests. Applied 15 fixes across 12 files.
    - **Thread Safety**: Added `threading.Lock` to `CircuitBreakerRegistry` state mutations and double-checked locking to `get_policy_engine()` / `get_prompt_composer()` singletons.
    - **Input Validation**: Replaced raw `dict[str, Any]` payloads with 5 Pydantic request models (`MetricsQueryRequest`, `PromQLQueryRequest`, `AlertsQueryRequest`, `LogsQueryRequest`, `LogAnalyzeRequest`) on query endpoints.
    - **Security Hardening**: Replaced 7 `traceback.print_exc()` calls with `logger.exception()`, hardened help router path traversal with `Path.resolve()` verification, upgraded dev-mode auth bypass log from DEBUG to WARNING.
    - **Schema Compliance**: Added `extra="forbid"` to `InvestigationState`, `frozen=True` to 4 council activity tracking models (`ToolCallRecord`, `LLMCallRecord`, `AgentActivity`, `CouncilActivityGraph`).
    - **Resource Leaks**: Fixed timer leak in `DashboardState.toggleAutoRefresh()`, added `client.close()` to `ExplorerQueryService` HTTP calls.
    - **Data Integrity**: Fixed `genui_adapter.transform_trace()` input mutation (copy-on-write), fixed `datetime.now()` → `datetime.now(timezone.utc)` inconsistency, cleared stale closure in debate convergence tracker, narrowed `_is_tool_failure()` exception catch to `JSONDecodeError/ValueError`.
    - Grand total: **1989 backend tests**, **129 Flutter tests** passing. Lint clean.

#### Remaining
- [ ] **Anomaly Correlation Engine**: Automate "Z-score comparison" across metrics and logs simultaneously.
- [ ] **Microservice Dependency Mapping**: Add graph analysis tools to detect circular dependencies in OTel trace trees.
- [ ] **Resource Saturation Suite**: Deep dive tools for OOMKilled, CPU Throttling, and Connection Pool exhaustion detection.
- [ ] **Messaging & Pub/Sub Tracing**: Extend investigation to dead-letter queues and message lag.

#### Audit Follow-Up Items
- [ ] **Council Intent Classifier**: Deterministic tie-breaking for signal type detection; word-boundary keyword matching to reduce false positives.
- [ ] **Council Debate Validation**: Confidence bounds checking (clamp 0.0-1.0); panel completion validation after `ParallelAgent`; critic output schema enforcement (`CriticReport`).
- [ ] **API Rate Limiting**: Add `slowapi` middleware with per-endpoint rate limits; request size limits on POST endpoints.
- [ ] **CORS Tightening**: Replace `allow_headers=["*"]` with explicit header allowlist; disable `allow_credentials` when `allow_origins=["*"]`.
- [ ] **Sync Tool Circuit Breaker**: Add circuit breaker logic to `sync_wrapper` in `decorators.py` to match async wrapper protection.
- [ ] **Test Quality**: Replace `time.sleep()` in circuit breaker tests with `freezegun`; add health router tests; add playbook module tests; add error/exception fixture suite to `conftest.py`.
- [ ] **genui_adapter Robustness**: Guard `transform_metrics()` PromQL path against `IndexError` on empty results; add `isinstance` check on nested `attributes` dict access.
- [ ] **Token Estimation Consistency**: Align `CHARS_PER_TOKEN` between `context_compactor.py` (4) and `model_callbacks.py` (2.5).
- [ ] **Session State Cleanup**: Add TTL-based cleanup for `_compaction_state` dict in `context_compactor.py` and `_active_executions` in `runner.py`.

---

## 🚀 Future Vision

- [ ] **Runbook Automation**: Execute predefined "Safety-First" runbooks (Restart, Scale, Rollback) with human-in-the-loop approval.
- [ ] **Executive Reporting**: One-click "Post-Mortem" generator that synthesizes the investigation into a professional report.
- [ ] **Structured Knowledge Extraction**: Automatic graph population based on investigation findings (e.g., auto-discovering a new API dependency).
- [ ] **Knowledge Graph for RCA**: Build service dependency graphs from trace data.
- [ ] **Chaos Engineering Sub-Agent**: Validate resilience hypotheses.
- [ ] **Rate Limiting / Backpressure**: Complement circuit breakers with request rate limiting.
- [ ] **Cross-Incident Learning**: Use embeddings to find similar past incidents.
- [ ] **Proactive SLO Forecasting**: Predict violations before they happen using trend analysis.

### Phase 4: Modern & World-Class Agentics (2026 Vision)
**Goal**: Transparency, continuous quality, and elite governance.

- [x] **Streaming Reasoning (CoT)**: Real-time "Thinking" stream in the UI, exposing the agent's internal chain-of-thought before it acts.
- [x] **CI-Driven Evaluations**: Integrated "LLM-as-a-Judge" into Cloud Build. Regression suites run on every PR to ensure reasoning accuracy never drops.
- [ ] **Observability-on-Self**: Fully link the agent's own trace IDs to the UI. Allow the user to "View Reasoning Trace" in Cloud Trace via deep links, leveraging native ADK instrumentation.
- [ ] **Confirmation Bridge (HITL 2.0)**: Global interceptor for `IMPACT: HIGH` tool calls (e.g., Delete/Modify) that pauses the agent and requests user permission via UI banner.
- [ ] **Zero-Trust Identity propagation**: 1:1 mapping of every tool execution to the *actual* end-user IAM identity, ensuring absolute auditability in massive GCP environments.
- [ ] **System Instruction Optimization**:
    - [ ] **Dynamic Tool Descriptions**: Inject tool docstrings at runtime to prevent hallucination drift and reduce maintenance.
    - [ ] **Dynamic Few-Shot Examples (RAG)**: Inject past successful investigations from Memory Bank into the prompt context to boost problem-solving.
    - [ ] **Token Efficiency**: Move critical invariants (constraints) to the end of the prompt to combat "lost in the middle" phenomenon.
    - [ ] **Documentation Snapshot**: [Captured current state](../docs/architecture/system_instruction_snapshot_v1.md) for future comparison.

### Phase 5: Proactive SRE (Q2 2026)
**Goal**: The agent anticipates problems before users ask.

- [ ] **Proactive Anomaly Detection**: Background monitoring mode — continuously poll key SLO metrics, run Z-score and seasonal decomposition, surface pre-incident warnings, auto-create investigations when thresholds breach.
- [ ] **Cross-Incident Knowledge Graph**: Persistent graph (services, APIs, error types, deployments) auto-populated from investigation findings. Queryable: "What usually causes checkout-service latency?"
- [ ] **Adaptive Panel Selection (Council 2.0)**: Replace rule-based IntentClassifier with LLM-augmented classifier considering investigation history, incident severity, and token budget.
- [ ] **Panel Self-Assessment & Re-Dispatch**: Confidence-aware feedback loop — low-confidence panels get re-dispatched with refined queries; contradicting panels auto-escalate to Debate mode.
- [ ] **Investigation Quality Scoring**: Post-investigation report with signal coverage, aggregate confidence, evidence strength, and suggestions for deeper investigation.
- [ ] **Investigation History & Replay**: Past investigations with timestamps, ability to replay against current data, diff view for "what changed since last investigation."
- [ ] **Graceful Degradation Hierarchy**: Multi-level fallback — Full MCP → Simplified MCP → Direct API → Cached results → Synthetic estimates.
- [ ] **Cost Attribution & Chargeback**: Per-team/per-project cost tracking for LLM tokens and GCP API calls, monthly reports, budget alerts.

### Phase 6: Enterprise & Scale (Q3-Q4 2026)
**Goal**: Multi-team, multi-cloud, production-grade governance.

- [ ] **Confirmation Bridge (HITL 2.0)**: Global interceptor for `IMPACT: HIGH` tool calls that pauses the agent and requests user permission via UI banner.
- [ ] **Zero-Trust Identity Propagation**: 1:1 mapping of every tool execution to the end-user IAM identity for absolute auditability.
- [ ] **Collaborative Investigations**: Multi-user investigation sessions — shared links, real-time cursors, comments/annotations, escalation workflow.
- [ ] **Canary Deployment Pipeline**: Deploy new agent version to 5% of traffic, run automated eval suite, compare quality metrics, auto-promote or rollback.
- [ ] **Prompt A/B Testing**: Track investigation quality per prompt variant, auto-select higher-performing prompts, few-shot examples from memory bank (RAG).
- [ ] **Mobile-Responsive Dashboard**: Responsive breakpoints for tablet/mobile — collapsible sidebar, swipeable panel cards, push notifications.
- [ ] **Chaos Engineering Sub-Agent**: Validate resilience hypotheses with controlled fault injection.
- [ ] **Multi-Cloud Support**: Extend investigation to AWS CloudWatch and Azure Monitor via new client factories.

---

## 🧪 Engineering Standards

*   **Vibe Coding**: Follow the lifecycle: Read Docs → Plan → Test First → Micro-Edit → Record.
*   **Test-Driven**: Every feature must have unit tests mirrored in `tests/unit/`.
*   **Documentation**: This file (`PROJECT_PLAN.md`) must be updated after every significant change or phase transition.

---
*Last updated: 2026-02-11 — Auto SRE Team*
