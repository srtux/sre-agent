# SRE Agent: Task List

## 🟢 Phase 1: Foundation (COMPLETED)
- [x] **API Refactoring**
  - [x] Create `sre_agent/api/` package structure
  - [x] Extract `health`, `agent`, `tools`, `sessions`, `preferences`, and `permissions` routers
  - [x] Create centralized tool event helpers in `sre_agent/api/helpers/`
  - [x] Bootstrap `server.py` using a FastAPI factory pattern
- [x] **Reasoning Reliability**
  - [x] Define `REACT_PATTERN_INSTRUCTION` in `prompt.py`
  - [x] Inject ReAct pattern into Orchestrator prompt
  - [x] Inject ReAct pattern into all 6 sub-agents (Trace, Root Cause, Logs, Metrics, Aggregate, Alerts)
- [x] **Tool Organization**
  - [x] Refine `ToolCategory` enum to be signal-centric
  - [x] Re-categorize all 70+ tools in `config.py`
- [x] **Stability & Verification**
  - [x] Fix `StorageService` method usage in modular routers
  - [x] Fix mypy type error in GCP client calls
  - [x] Update test collection for GenUI and Widget tests

Summary of Changes (API Modularization)
New Package Structure: Created sre_agent/api/ with separate modules for app initialization, middleware, and dependencies.
Decomposed Routers:
health.py: Health checks and diagnostic endpoints.
agent.py: Principal chat agent logic and streaming response handling.
tools.py: Tool configuration, testing, and execution endpoints.
sessions.py: Session management and history.
GenUI Support: Extracted A2UI protocol helpers into helpers/tool_events.py.
Verified Code Quality: Fixed multiple mypy and ruff errors to ensure the new modules are well-typed and follow project standards.

## 🔵 Phase 2: Memory & State (UPCOMING)
- [ ] **Memory System**
  - [ ] Implement `VertexAiMemoryBankService` for session persistence
  - [ ] Migrate current in-memory storage to the new service
- [ ] **Investigation Orchestration**
  - [ ] Define the Investigation State Machine logic
  - [ ] Implement "Phase-Aware" tool filtering (e.g., only show `TRACE_FETCH` during Triage)
- [ ] **Context Handoff**
  - [ ] Standardize the JSON schema for inter-agent context passing

## 🟡 Phase 3: Diagnostics (PLANNED)
- [ ] Implement cross-signal anomaly correlation
- [ ] Add deep-dive logic for Kubernetes resource exhaustion
- [ ] Enhance service dependency graph visualizations

## ⚪ Phase 4: UX (STRETCH)
- [x] Standardize SRE Report format
- [ ] Add remediation risk assessment tools
