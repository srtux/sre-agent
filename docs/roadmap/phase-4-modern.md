# Phase 4: Modern & World-Class Agentics

**Period**: February-April 2026 | **Status**: In Progress | **Goal**: Transparency, continuous quality, and elite governance

---

## Overview

Phase 4 focuses on making Auto SRE a best-in-class AI agent system with full reasoning transparency, continuous evaluation, and human-in-the-loop governance. This phase bridges the gap between a capable investigation agent and a production-trusted system.

---

## Tasks

### Completed

| Task | Status | Component | Description |
|------|--------|-----------|-------------|
| Streaming Reasoning (CoT) | done | Flutter Frontend | Real-time "Thinking" stream exposing internal chain-of-thought |
| CI-Driven Evaluations | done | Evaluation | "LLM-as-a-Judge" in Cloud Build, regression suites on every PR |
| Zero Broken Windows | done | Flutter Frontend | Resolved 11+ failing tests, 100% pass rate across all tests |
| Web Renderer Migration | done | Flutter Frontend | Switched to stable CanvasKit renderer |
| Agent Graph Enhancement | done | Flutter Frontend | BQ SQL refactoring, pre-aggregated hourly table, dual-path routing, enhanced canvas |
| Evals Tab | done | AgentOps UI | Eval configurations, agent cards, detail view, setup wizard |

### In Progress

| Task | Status | Component | Description |
|------|--------|-----------|-------------|
| Observability-on-Self | in-progress | Backend Core | Link agent trace IDs to UI, "View Reasoning Trace" deep links |

### Planned

| Task | Status | Component | Description |
|------|--------|-----------|-------------|
| Confirmation Bridge (HITL 2.0) | planned | Backend Core | Global interceptor for HIGH impact tool calls, user permission via UI banner |
| Zero-Trust Identity | planned | Backend Core | 1:1 tool execution to end-user IAM identity mapping |
| Dynamic Tool Descriptions | planned | Backend Core | Inject tool docstrings at runtime to prevent hallucination drift |
| Dynamic Few-Shot Examples | planned | Services & Memory | RAG-based injection of past successful investigations into prompt |
| Token Efficiency Optimization | planned | Backend Core | Move constraints to prompt end to combat "lost in the middle" |
| Cross-Agent Handoffs | planned | Council | Refined schema for passing context (including negative findings) between agents |

---

## Success Criteria

- [ ] Agent reasoning is fully visible in the UI via trace deep links
- [ ] All HIGH impact tool calls require user confirmation before execution
- [ ] Every tool execution is traceable to the end-user IAM identity
- [ ] Evaluation regressions are caught in CI before merge
- [ ] Dynamic tool descriptions eliminate prompt-docstring drift

---

## Dependencies

| Dependency | Blocks | Notes |
|-----------|--------|-------|
| ADK trace ID propagation | Observability-on-Self | Requires ADK to expose trace context |
| Memory Bank search quality | Dynamic Few-Shot | Need good retrieval relevance for RAG |
| Policy engine maturity | Confirmation Bridge | Foundation exists in `core/approval.py` |

---

*Last updated: 2026-02-23*
