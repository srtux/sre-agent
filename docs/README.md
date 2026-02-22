# Auto SRE Documentation Index

This is the central index for all Auto SRE documentation. Use this page to navigate to any topic.

> **For AI agents**: Start with [llm.txt](../llm.txt) for a high-density context summary,
> then [AGENTS.md](../AGENTS.md) for coding patterns, then drill into specific docs below.

---

## Quick Navigation

| I need to...                        | Go to                                                              |
|-------------------------------------|--------------------------------------------------------------------|
| Set up the project locally          | [Getting Started](guides/getting_started.md)                       |
| Understand the architecture         | [System Overview](architecture/system_overview.md)                 |
| Write or modify code                | [Development Guide](guides/development.md)                        |
| Write or run tests                  | [Testing Strategy](guides/testing.md)                              |
| Run or write agent evaluations      | [Evaluation Guide](guides/evaluation.md)                           |
| Deploy to production                | [Deployment Guide](guides/deployment.md)                           |
| Understand deployment architecture  | [Deployment Architecture](infrastructure/DEPLOYMENT.md)            |
| Debug an issue                      | [Debugging Guides](#debugging)                                     |
| Look up environment variables       | [Configuration Reference](reference/configuration.md)              |
| Find available tools                | [Tools Catalog](reference/tools.md)                                |
| Understand security model           | [Security Reference](reference/security.md)                        |
| Check the project roadmap           | [Project Plan](PROJECT_PLAN.md)                                    |
| Troubleshoot Cloud Spanner          | [Spanner Playbook](SPANNER_TROUBLESHOOTING_PLAYBOOK.md)            |
| Browse in-app help topics           | [Help System Content](#help-system-content)                        |

---

## Project Overview

- [README.md](../README.md) -- High-level project overview with architecture diagram
- [Project Plan](PROJECT_PLAN.md) -- Living roadmap of completed and planned work
- [AGENTS.md](../AGENTS.md) -- Universal AI agent standard (single source of truth for coding)
- [CLAUDE.md](../CLAUDE.md) -- Quick rules for Claude Code agents
- [llm.txt](../llm.txt) -- High-density LLM agent context file
- [Documentation Review & Roadmap](DOCUMENTATION_REVIEW_AND_ROADMAP.md) -- Full audit of all docs with future improvement plan

---

## Architecture

System design documents explaining how Auto SRE is built.

| Document | Description |
|----------|-------------|
| [System Overview](architecture/system_overview.md) | High-level topology, component diagrams, data flow |
| [Project Structure](architecture/project_structure.md) | Detailed directory tree and module descriptions |
| [Backend Architecture](architecture/backend.md) | FastAPI application, middleware stack, services layer |
| [Frontend Architecture](architecture/frontend.md) | Flutter Web, state management, GenUI/A2UI protocol |
| [Authentication](architecture/authentication.md) | OAuth2, session management, EUC propagation |
| [Telemetry](architecture/telemetry.md) | OpenTelemetry instrumentation, Cloud Trace export |
| [Architectural Decisions](architecture/decisions.md) | Historic record of design choices and rationale |
| [Help System](architecture/help_system.md) | Context-aware help system architecture |
| [Agents & Tools](architecture/AGENTS_AND_TOOLS.md) | Agent hierarchy and tool registration catalog |
| [System Instruction Snapshot](architecture/system_instruction_snapshot_v1.md) | Captured system instruction baseline for comparison |

---

## AgentOps & Observability

The human-facing operational surfaces for the multi-agent system.

| Document | Description |
|----------|-------------|
| [AgentOps Index](agent_ops/README.md) | Central landing page for all AgentOps ecosystem documentation |
| [AgentOps Dashboard](agent_ops/dashboard.md) | AgentOps Dashboard with KPIs, charts, model/tool tables, and agent logs |
| [Observability Explorer](agent_ops/explorer_ui.md) | Observability Explorer dashboard usage and architecture |
| [Multi-Agent Observability](agent_ops/observability_theory.md) | Theory on how Agent Graph, Dashboards, and logs empower operations |
| [Agent Graph Architecture](agent_ops/architecture.md) | Reasoning trajectories, and BQ Property Graph implementation |
| [BigQuery Graph Setup](agent_ops/bigquery_setup.md) | BigQuery Property Graph visualization and pre-aggregation instructions |
| [BigQuery Schema Details](agent_ops/bq_schema.md) | OpenTelemetry payload extraction definitions |
| [Legacy Dashboards](agent_ops/dashboards_legacy.md) | Perses dashboard fallback compatibility |

---

## Core Concepts

Philosophical and design documents explaining the "why" behind the architecture.

| Document | Description |
|----------|-------------|
| [Autonomous Reliability](concepts/autonomous_reliability.md) | The "Unrolled Codex" pattern and OODA event loop |
| [Agent Orchestration](concepts/agent_orchestration.md) | Council of Experts design -- how sub-agents collaborate |
| [Observability Deep Dive](concepts/observability.md) | Traces, spans, metrics analysis theory |
| [Memory & State](concepts/memory.md) | How the agent persists context across sessions |
| [Online Research & Self-Healing](concepts/online_research_and_self_healing.md) | Web search tools and autonomous self-improvement architecture |
| [Auth Learnings](concepts/auth_learnings.md) | Evolution of the authentication system |
| [GCP Enhancements Roadmap](concepts/gcp_enhancements.md) | Vision for future capabilities |

---

## Guides

Practical how-to instructions for developers.

### Development
| Guide | Description |
|-------|-------------|
| [Getting Started](guides/getting_started.md) | Installation, configuration, first run |
| [Development Guide](guides/development.md) | "Vibe Coding" handbook -- the full development workflow |
| [Testing Strategy](guides/testing.md) | Test levels, style guide, coverage requirements |
| [Linting Rules](guides/linting.md) | Ruff, MyPy, codespell, deptry configuration |
| [Evaluation Guide](guides/evaluation.md) | Agent quality benchmarking with ADK eval |
| [Frontend Testing](guides/frontend_testing.md) | Flutter test strategy with Provider-based injection |
| [Project Selector](guides/project_selector.md) | GCP project picker implementation and data flow |

### Deployment
| Guide | Description |
|-------|-------------|
| [Deployment](guides/deployment.md) | Cloud Run and Vertex AI Agent Engine deployment |

### Debugging
| Guide | Description |
|-------|-------------|
| [Debugging Connectivity](guides/debugging_connectivity.md) | Network, API, and CORS troubleshooting |
| [Debugging Telemetry & Auth](guides/debugging_telemetry_and_auth.md) | Missing traces, auth failures |
| [Debugging GenUI](guides/debugging_genui.md) | Widget rendering and A2UI protocol issues |
| [Rendering Telemetry](guides/rendering_telemetry.md) | GenUI/A2UI widget schemas and data flow |

---

## Reference

API specifications, configuration, and catalogs.

| Document | Description |
|----------|-------------|
| [API Reference](reference/api.md) | Agent API endpoints and protocol specification |
| [Configuration](reference/configuration.md) | Complete environment variable reference |
| [Tools Catalog](reference/tools.md) | All available tools with descriptions and parameters |
| [Security](reference/security.md) | Encryption, key management, data handling policies |

---

## Infrastructure

Deployment infrastructure and CI/CD documentation.

| Document | Description |
|----------|-------------|
| [Deployment Architecture](infrastructure/DEPLOYMENT.md) | Parallel deployment strategy, CI/CD pipeline (Cloud Build), build process |

---

## Knowledge Base

Internal engineering notes and SDK-specific findings.

| Document | Description |
|----------|-------------|
| [Vertex AI SDK Notes](knowledge/vertex_ai_sdk_notes.md) | Agent Engine SDK findings, method availability, migration notes |

---

## Playbooks

Operational runbooks for specific GCP services.

| Document | Description |
|----------|-------------|
| [Spanner Troubleshooting](SPANNER_TROUBLESHOOTING_PLAYBOOK.md) | Query performance, lock contention, hot spotting, and data distribution for Cloud Spanner |

---

## Evaluation & Quality

| Document | Description |
|----------|-------------|
| [Evaluation Standards](EVALUATIONS.md) | Dual-layer eval architecture, rubrics, anti-hallucination |
| [Evaluation Guide](guides/evaluation.md) | Running evals locally and in CI/CD |
| [Observability Guide](OBSERVABILITY.md) | Tracing and logging best practices |

---

## Help System Content

In-app contextual help topics served to users via the help system. These files are managed
through [`help/manifest.json`](help/manifest.json), which defines the topic registry
(IDs, titles, categories, icons). See [Help System Architecture](architecture/help_system.md)
for the design.

| Topic | File | Description |
|-------|------|-------------|
| Traces & Spans | [traces.md](help/content/traces.md) | Getting started with distributed traces and latency visualization |
| Log Intelligence | [logs.md](help/content/logs.md) | AI-powered log clustering and pattern analysis |
| SLO & Metrics | [metrics.md](help/content/metrics.md) | SLO burn rate analysis and error budget tracking |
| Council Investigation | [council.md](help/content/council.md) | Council of Experts parallel investigation workflow |
| Root Cause Analysis | [rca.md](help/content/rca.md) | Structured detective methodology for diagnosing issues |
| Incident Lifecycle | [incident_lifecycle.md](help/content/incident_lifecycle.md) | Standard SRE incident response lifecycle (detect, triage, mitigate, resolve) |
| Incident Correlation | [changes.md](help/content/changes.md) | Change correlation -- audit logs, deployments, feature flags |
| Deployment & Infrastructure | [deployment.md](help/content/deployment.md) | Cloud Run and Agent Engine deployment overview |
| Telemetry Integration | [telemetry_source.md](help/content/telemetry_source.md) | GCP observability stack integration points |
| Model Info | [model_info.md](help/content/model_info.md) | Gemini model capabilities and context window details |
| Debugging the Agent | [debugging_agent.md](help/content/debugging_agent.md) | Troubleshooting agent permission errors, stuck states |
| Circuit Breaker | [circuit_breaker.md](help/content/circuit_breaker.md) | Self-preservation mechanism for API failures |
| Custom Tools | [custom_tools.md](help/content/custom_tools.md) | Extending the agent with Python tools and MCP servers |
| Trust & Safety | [safety.md](help/content/safety.md) | Read-only defaults, audit logging, approval workflow |

---

## Source Code Map

### Backend (`sre_agent/`)

| Module | Path | Description |
|--------|------|-------------|
| **Orchestrator** | `agent.py` | Main agent with 3-stage pipeline |
| **Authentication** | `auth.py` | OAuth2, EUC, token validation, ContextVars |
| **Schemas** | `schema.py` | Pydantic models (`frozen=True, extra="forbid"`) |
| **System Prompt** | `prompt.py` | Agent personality and instructions |
| **Model Config** | `model_config.py` | Model configuration, context caching |
| **Suggestions** | `suggestions.py` | Follow-up suggestion generation |
| **API Layer** | `api/` | FastAPI app factory, middleware, routers, DI |
| **Core Engine** | `core/` | Runner, policy engine, context compaction, summarizer |
| **Council** | `council/` | Council of Experts orchestrator, panels, synthesizer, critic |
| **Sub-Agents** | `sub_agents/` | Trace, logs, metrics, alerts, root cause specialists |
| **Tools** | `tools/` | Analysis, GCP clients, MCP, BigQuery, discovery |
| **Services** | `services/` | Session management, storage, Agent Engine client |
| **Memory** | `memory/` | Memory manager, local storage, factory |
| **Models** | `models/` | Investigation state and phase management |
| **Resources** | `resources/` | GCP metrics catalog |

### Frontend (`autosre/`)

| Module | Path | Description |
|--------|------|-------------|
| **Agent Graph** | `lib/features/agent_graph/` | Multi-trace BQ Property Graph visualization (domain, data, application, presentation) |
| **Pages** | `lib/pages/` | Login, conversation, tool configuration |
| **Services** | `lib/services/` | Auth, API client, session, dashboard state |
| **Widgets** | `lib/widgets/` | Canvas visualizations, dashboard panels, UI components |
| **Models** | `lib/models/` | ADK schema definitions |
| **Theme** | `lib/theme/` | Material 3 deep space theme |

### Tests (`tests/`)

| Level | Path | Description |
|-------|------|-------------|
| **Unit** | `tests/unit/` | Isolated function tests, mirrors source structure |
| **Integration** | `tests/integration/` | Cross-service interaction tests |
| **E2E** | `tests/e2e/` | Full agent workflow and CUJ tests |
| **Server** | `tests/server/` | FastAPI endpoint and WebSocket tests |
| **Fixtures** | `tests/conftest.py` | Shared fixtures (logs, traces, mock clients) |

### Evaluations (`eval/`)

| File | Description |
|------|-------------|
| `test_evaluate.py` | ADK AgentEvaluator runner |
| `test_config.json` | Quality criteria and thresholds |
| `basic_capabilities.test.json` | Agent capability sanity check |
| `tool_selection.test.json` | Tool routing validation |
| `metrics_analysis.test.json` | Metrics analysis evaluation |
| `incident_investigation.test.json` | Multi-stage investigation scenario |

---

## For AI Agents

If you are an LLM agent (Claude Code, Gemini, etc.), follow this reading order:

1. **[llm.txt](../llm.txt)** -- High-density context (read first, always)
2. **[AGENTS.md](../AGENTS.md)** -- Coding patterns, checklists, pitfalls
3. **[Project Plan](PROJECT_PLAN.md)** -- Current roadmap and status
4. **Relevant docs below** -- Based on your task:
   - Modifying tools? Read [Tools Catalog](reference/tools.md) + [Development Guide](guides/development.md)
   - Writing tests? Read [Testing Strategy](guides/testing.md)
   - Debugging? Read the appropriate [Debugging Guide](#debugging)
   - Deploying? Read [Deployment Guide](guides/deployment.md) + [Deployment Architecture](infrastructure/DEPLOYMENT.md)
   - Understanding the help system? Read [Help System Architecture](architecture/help_system.md) + [Help Content](#help-system-content)

---
*Last verified: 2026-02-21 -- Auto SRE Team*
