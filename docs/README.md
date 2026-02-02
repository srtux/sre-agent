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
| Debug an issue                      | [Debugging Guides](#debugging)                                     |
| Look up environment variables       | [Configuration Reference](reference/configuration.md)              |
| Find available tools                | [Tools Catalog](reference/tools.md)                                |
| Understand security model           | [Security Reference](reference/security.md)                        |
| Check the project roadmap           | [Project Plan](PROJECT_PLAN.md)                                    |

---

## Project Overview

- [README.md](../README.md) — High-level project overview with architecture diagram
- [Project Plan](PROJECT_PLAN.md) — Living roadmap of completed and planned work
- [AGENTS.md](../AGENTS.md) — Universal AI agent standard (single source of truth for coding)
- [CLAUDE.md](../CLAUDE.md) — Quick rules for Claude Code agents
- [llm.txt](../llm.txt) — High-density LLM agent context file

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

---

## Core Concepts

Philosophical and design documents explaining the "why" behind the architecture.

| Document | Description |
|----------|-------------|
| [Autonomous Reliability](concepts/autonomous_reliability.md) | The "Unrolled Codex" pattern and OODA event loop |
| [Agent Orchestration](concepts/agent_orchestration.md) | Council of Experts design — how sub-agents collaborate |
| [Observability Deep Dive](concepts/observability.md) | Traces, spans, metrics analysis theory |
| [Memory & State](concepts/memory.md) | How the agent persists context across sessions |
| [Auth Learnings](concepts/auth_learnings.md) | Evolution of the authentication system |
| [GCP Enhancements Roadmap](concepts/gcp_enhancements.md) | Vision for future capabilities |

---

## Guides

Practical how-to instructions for developers.

### Development
| Guide | Description |
|-------|-------------|
| [Getting Started](guides/getting_started.md) | Installation, configuration, first run |
| [Development Guide](guides/development.md) | "Vibe Coding" handbook — the full development workflow |
| [Testing Strategy](guides/testing.md) | Test levels, style guide, coverage requirements |
| [Linting Rules](guides/linting.md) | Ruff, MyPy, codespell, deptry configuration |
| [Evaluation Guide](guides/evaluation.md) | Agent quality benchmarking with ADK eval |

### Deployment
| Guide | Description |
|-------|-------------|
| [Deployment](guides/deployment.md) | Cloud Run and Vertex AI Agent Engine deployment |

### Debugging {#debugging}
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

## Evaluation & Quality

| Document | Description |
|----------|-------------|
| [Evaluation Standards](EVALUATIONS.md) | Dual-layer eval architecture, rubrics, anti-hallucination |
| [Evaluation Guide](guides/evaluation.md) | Running evals locally and in CI/CD |
| [Observability Guide](OBSERVABILITY.md) | Tracing and logging best practices |

---

## Source Code Map

### Backend (`sre_agent/`)

| Module | Path | Description |
|--------|------|-------------|
| **Orchestrator** | `agent.py` | Main agent with 3-stage pipeline |
| **Authentication** | `auth.py` | OAuth2, EUC, token validation, ContextVars |
| **Schemas** | `schema.py` | Pydantic models (`frozen=True, extra="forbid"`) |
| **System Prompt** | `prompt.py` | Agent personality and instructions |
| **Suggestions** | `suggestions.py` | Follow-up suggestion generation |
| **API Layer** | `api/` | FastAPI app factory, middleware, routers, DI |
| **Core Engine** | `core/` | Runner, policy engine, context compaction, summarizer |
| **Sub-Agents** | `sub_agents/` | Trace, logs, metrics, alerts, root cause specialists |
| **Tools** | `tools/` | Analysis, GCP clients, MCP, BigQuery, discovery |
| **Services** | `services/` | Session management, storage, Agent Engine client |
| **Memory** | `memory/` | Memory manager, local storage, factory |
| **Models** | `models/` | Investigation state and phase management |
| **Resources** | `resources/` | GCP metrics catalog |

### Frontend (`autosre/`)

| Module | Path | Description |
|--------|------|-------------|
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

1. **[llm.txt](../llm.txt)** — High-density context (read first, always)
2. **[AGENTS.md](../AGENTS.md)** — Coding patterns, checklists, pitfalls
3. **[Project Plan](PROJECT_PLAN.md)** — Current roadmap and status
4. **Relevant docs below** — Based on your task:
   - Modifying tools? Read [Tools Catalog](reference/tools.md) + [Development Guide](guides/development.md)
   - Writing tests? Read [Testing Strategy](guides/testing.md)
   - Debugging? Read the appropriate [Debugging Guide](#debugging)
   - Deploying? Read [Deployment Guide](guides/deployment.md)
