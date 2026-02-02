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

### Phase 3: Advanced Diagnostics (UPCOMING)
**Goal**: Specialized analytical logic for complex failure modes.

- [ ] **Anomaly Correlation Engine**: Automate "Z-score comparison" across metrics and logs simultaneously.
- [ ] **Microservice Dependency Mapping**: Add graph analysis tools to detect circular dependencies in OTel trace trees.
- [ ] **Resource Saturation Suite**: Deep dive tools for OOMKilled, CPU Throttling, and Connection Pool exhaustion detection.
- [ ] **Messaging & Pub/Sub Tracing**: Extend investigation to dead-letter queues and message lag.

---

## 🚀 Future Vision

- [ ] **Runbook Automation**: Execute predefined "Safety-First" runbooks (Restart, Scale, Rollback) with human-in-the-loop approval.
- [ ] **Executive Reporting**: One-click "Post-Mortem" generator that synthesizes the investigation into a professional report.
- [ ] **Structured Knowledge Extraction**: Automatic graph population based on investigation findings (e.g., auto-discovering a new API dependency).

### Phase 5: Modern & World-Class Agentics (2026 Vision)
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

---

## 🧪 Engineering Standards

*   **Vibe Coding**: Follow the lifecycle: Read Docs → Plan → Test First → Micro-Edit → Record.
*   **Test-Driven**: Every feature must have unit tests mirrored in `tests/unit/`.
*   **Documentation**: This file (`PROJECT_PLAN.md`) must be updated after every significant change or phase transition.

---
*Last Updated: 2026-02-01 - Auto SRE Team*
