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
    *   Expanded `configuration.md` to cover all active environment variables.

---

## 🏗️ Active Roadmap

### Phase 2: Memory & Proactive State (IN PROGRESS)
**Goal**: Deep context retention and guided investigations.

- [x] **Vertex AI Memory Integration**: Core integration of `VertexAiMemoryBankService` for long-term incident retention.
- [ ] **Proactive Search Logic**: Use the Memory Bank to automatically retrieve similar past incidents at the beginning of an investigation.
- [ ] **Investigation State Machine**: Implement a formal state tracker (Triage → Analysis → Root Cause) to guide agent reasoning.
- [ ] **Cross-Agent Handoffs**: Refine the schema for passing context (including negative findings) between sub-agents.
- [x] **Automated CI/CD (Cloud Build)**: Orchestrate full-stack deployment (Agent Engine + Cloud Run) via GCP native triggers with parallelized tracks.

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

- [ ] **Streaming Reasoning (CoT)**: Real-time "Thinking" stream in the UI, exposing the agent's internal chain-of-thought before it acts.
- [ ] **Observability-on-Self**: Fully link the agent's own trace IDs to the UI. Allow the user to "View Reasoning Trace" in Cloud Trace/Arize via deep links.
- [ ] **CI-Driven Evaluations**: Integrate "LLM-as-a-Judge" into Cloud Build. Run regression suites on every PR to ensure reasoning accuracy never drops.
- [ ] **Confirmation Bridge (HITL 2.0)**: Global interceptor for `IMPACT: HIGH` tool calls (e.g., Delete/Modify) that pauses the agent and requests user permission via UI banner.
- [ ] **Zero-Trust Identity propagation**: 1:1 mapping of every tool execution to the *actual* end-user IAM identity, ensuring absolute auditability in massive GCP environments.

---

## 🧪 Engineering Standards

*   **Vibe Coding**: Follow the lifecycle: Read Docs → Plan → Test First → Micro-Edit → Record.
*   **Test-Driven**: Every feature must have unit tests mirrored in `tests/unit/`.
*   **Documentation**: This file (`PROJECT_PLAN.md`) must be updated after every significant change or phase transition.

---
*Last Updated: 2026-01-25 - Auto SRE Team*
