# Phase 3: Observability & Advanced Diagnostics

**Period**: February 2026 | **Status**: Completed | **Goal**: ADK-native observability, tool discovery, eval coverage, resilience patterns, sandbox execution, self-healing, and advanced routing

---

## Overview

Phase 3 was the largest phase, spanning 17 sub-phases (3.0-3.17). It transformed Auto SRE from a reactive investigation tool into a full-featured observability platform with sandbox execution, self-healing, playbooks, and a comprehensive evaluation framework.

---

## Tasks

### Phase 3.0: Core Observability & Evaluation

| Task | Status | Component | Description |
|------|--------|-----------|-------------|
| ADK Model Callbacks | done | Backend Core | `UsageTracker` with thread-safe singleton, token budget enforcement, per-model pricing |
| Tool Categorization Registry | done | Tools | `ToolRegistry` with signal-type discovery and keyword search (24 tests) |
| Debate Convergence Tracking | done | Council | Per-round confidence progression, delta, gaps tracking in session state (16 tests) |
| MCP-to-Direct-API Fallback | done | Tools | `with_fallback()` for transparent MCP degradation (19 tests) |
| Signal-Type Intent Classifier | done | Council | `classify_intent_with_signal()` with keyword-scored signal routing (28 tests) |
| Evaluation Framework | done | Evaluation | 9 eval scenarios, shared conftest, AgentEvaluator integration |
| Bug Fixes & Consistency | done | Backend Core | Fixed merge conflicts, duplicate tools, dead code integration |

### Phase 3.5: Observability Explorer Dashboard

| Task | Status | Component | Description |
|------|--------|-----------|-------------|
| Syncfusion Chart Migration | done | Flutter Frontend | Replaced fl_chart, deleted 1,935 lines of old widgets |
| Manual Query Capability | done | Flutter Frontend | `ManualQueryBar` for direct GCP telemetry querying |
| Backend Query Endpoints | done | Backend Core | 4 new REST endpoints for metrics, PromQL, alerts, logs |
| Dual Data Source Architecture | done | Flutter Frontend | `DataSource.agent` / `DataSource.manual` per-panel tracking |
| GCP-Style Toolbar | done | Flutter Frontend | Time range presets, custom date picker, auto-refresh |
| Cross-Platform Threading | done | Flutter Frontend | `AppIsolate` wrapper for background JSON parsing |

### Phase 3.6-3.7: Code Audit & Hardening

| Task | Status | Component | Description |
|------|--------|-----------|-------------|
| Thread Safety Fixes | done | Backend Core | Locks on CircuitBreakerRegistry, singleton double-checked locking |
| Input Validation | done | Backend Core | 5 Pydantic request models on query endpoints |
| Security Hardening | done | Backend Core | Replaced traceback.print_exc(), hardened path traversal, auth bypass logging |
| Schema Compliance | done | Backend Core | `extra="forbid"` on InvestigationState, `frozen=True` on council models |
| Resource Leak Fixes | done | Flutter Frontend | Timer leak in DashboardState, client.close() in ExplorerQueryService |
| Critical Bug Fix | done | Backend Core | Fixed AttributeError in run_aggregate_analysis() |
| Cache Memory Leak | done | Backend Core | Added evict_expired() to DataCache |

### Phase 3.8: Council 2.0 Adaptive Classification

| Task | Status | Component | Description |
|------|--------|-----------|-------------|
| Adaptive Intent Classifier | done | Council | LLM-augmented classification with rule-based fallback |
| ClassificationContext Schema | done | Council | Session history, alert severity, token budget, previous modes |
| Budget-Aware Override | done | Council | Auto-downgrade DEBATE to STANDARD when tokens low |
| Feature Flag | done | Council | `SRE_AGENT_ADAPTIVE_CLASSIFIER=true` |

**Tests**: 57 (45 unit + 12 integration)

### Phase 3.9: 3-Tier Request Router

| Task | Status | Component | Description |
|------|--------|-----------|-------------|
| Request Router | done | Backend Core | DIRECT/SUB_AGENT/COUNCIL classification for every query |
| RoutingDecision Enum | done | Backend Core | In `council/schemas.py` |
| route_request Tool | done | Backend Core | `@adk_tool` wrapper for first-step routing |

**Tests**: 38 (15 router + 23 routing classifier)

### Phase 3.10-3.11: External Integrations

| Task | Status | Component | Description |
|------|--------|-----------|-------------|
| GitHub Read File | done | Tools | Read files from agent's repository |
| GitHub Search Code | done | Tools | Search codebase for patterns |
| GitHub List Commits | done | Tools | List commits with file path filtering |
| GitHub Create PR | done | Tools | Draft PRs with auto-fix/ prefix, safety validation |
| Google Custom Search | done | Tools | search_google with site restriction |
| Web Page Fetching | done | Tools | HTML-to-text extraction with truncation |

**Tests**: 63 (35 GitHub + 28 research)

### Phase 3.12: Large Payload & Sandbox

| Task | Status | Component | Description |
|------|--------|-----------|-------------|
| Large Payload Handler | done | Backend Core | Auto-intercept oversized tool outputs with 3-tier processing |
| Sandbox Executor | done | Tools | Agent Engine + LocalCodeExecutor with data processors |
| Sandbox Schemas | done | Tools | SandboxConfig, MachineConfig, CodeExecutionOutput |

**Tests**: 157 (63 payload + 94 sandbox)

### Phase 3.13-3.17: Advanced Features

| Task | Status | Component | Description |
|------|--------|-----------|-------------|
| Context Caching | done | Backend Core | Vertex AI static prompt caching, 75% input token cost reduction |
| Service Dependency Graph | done | Backend Core | DependencyGraph with BlastRadiusReport for RCA (28 tests) |
| Playbook System | done | Tools | 7 service playbooks with OODA self-healing (50 tests) |
| Human Approval Workflow | done | Backend Core | Foundation in core/approval.py |
| Custom Dashboard Modernization | done | Flutter Frontend | Feature-First migration, Riverpod 3.0, Dio integration |

---

## Key Metrics

- Total tests at Phase 3 end: 2312 backend, 74 Flutter
- New features: 15+ major features across 17 sub-phases
- New tools added: 20+ (GitHub, research, sandbox, playbooks)
- Code audit: 15 fixes across 12 files

---

*Phase completed: February 2026*
