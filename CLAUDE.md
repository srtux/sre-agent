# CLAUDE.md: Auto SRE — Claude Code Reference

> **Canonical reference**: [`AGENTS.md`](AGENTS.md) is the Single Source of Truth for all coding patterns.
> This file provides a comprehensive overview for Claude Code sessions. For deep dives, consult AGENTS.md.

## Reading Order
1. **[llm.txt](llm.txt)** — High-density context (read first)
2. **[AGENTS.md](AGENTS.md)** — Patterns, checklists, pitfalls
3. **[docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md)** — Roadmap and status
4. Task-specific docs in [`docs/`](docs/README.md)

## Project Overview

Auto SRE is an AI-powered Site Reliability Engineering agent that automates incident investigation on Google Cloud Platform. It uses a **"Council of Experts"** pattern — specialized sub-agents for traces, logs, metrics, alerts, and root cause analysis.

**Version**: 0.2.0 | **License**: Apache-2.0 | **Status**: Phase 3 active (2277+ backend tests, 129 Flutter tests passing)

## Tech Stack
- **Backend**: Python 3.10+ (<3.13), FastAPI, Google ADK 1.23.0, Pydantic 2
- **Frontend**: Flutter Web (Material 3, Deep Space aesthetic)
- **LLM**: Gemini 2.5 Flash/Pro (via `get_model_name("fast"|"deep")`)
- **Storage**: SQLite (dev) / Cloud SQL (prod), Firestore (configs)
- **Telemetry**: Cloud Trace, Cloud Logging, Cloud Monitoring (OTel)
- **Testing**: pytest 8+ (backend), flutter test (frontend), ADK eval (agent quality)
- **Package Management**: uv (Python), Flutter pub (Dart)
- **Task Runner**: poethepoet (22+ tasks)
- **CI/CD**: Google Cloud Build (7-stage pipeline)

## Quick Rules
1. **Read before modifying** — Never propose changes to unread code.
2. **Test first** — Create/update tests *before* implementing logic.
3. **Lint always** — `uv run poe lint-all` must be clean.
4. **Explicit types** — Mandatory type hints, no implicit `Any`.
5. **Coverage** — 80% minimum gate; 100% target on new tools and core logic.
6. **Schemas** — Pydantic `frozen=True, extra="forbid"` on all models.
7. **Async** — All external I/O (GCP, DB, LLM) must be `async/await`.
8. **Imports** — Prefer absolute (`from sre_agent.X import Y`); relative OK within same package.
9. **Tools** — Must use `@adk_tool` decorator and return `BaseToolResponse` JSON.
10. **Compaction** — Update `PROJECT_PLAN.md` and docs after completing major changes.

## Essential Commands
```bash
# Development
uv run poe dev          # Full stack (backend + frontend)
uv run poe web          # Backend server only (FastAPI on port 8001)
uv run poe run          # Terminal agent (adk run)
uv run poe sync         # Install/update all dependencies (uv + flutter)

# Quality
uv run poe lint         # Ruff format + lint + MyPy + codespell + deptry
uv run poe lint-all     # Backend + Flutter linters
uv run poe test         # pytest + 80% coverage gate
uv run poe test-all     # Backend + Flutter tests
uv run poe eval         # Agent evaluations (trajectory + rubrics)

# Deployment
uv run poe deploy       # Backend to Vertex AI Agent Engine
uv run poe deploy-web   # Frontend to Cloud Run
uv run poe deploy-all   # Full stack deployment
uv run poe deploy-gke   # Full stack to GKE

# Utilities
uv run poe list         # List deployed agents
uv run poe pre-commit   # Run all pre-commit hooks
uv run poe format       # Auto-format code (ruff)
```

## Codebase Structure

### Backend (`sre_agent/`)
```
sre_agent/
├── agent.py              # Main orchestrator — 3-stage pipeline (Aggregate > Triage > Deep Dive)
├── auth.py               # Authentication, EUC, token validation, ContextVars
├── schema.py             # Pydantic models (all frozen=True, extra="forbid")
├── prompt.py             # Agent system instruction / personality
├── model_config.py       # Model configuration (get_model_name("fast"|"deep"), context caching)
├── suggestions.py        # Follow-up suggestion generation
│
├── api/                  # FastAPI application layer
│   ├── app.py            #   Factory (create_app), Pydantic monkeypatch
│   ├── middleware.py      #   Auth + tracing + CORS middleware
│   ├── dependencies.py    #   Dependency injection (session, tool context)
│   ├── routers/           #   HTTP handlers: agent, sessions, tools, health, system, permissions, preferences, help
│   └── helpers/           #   Tool event streaming (emit_dashboard_event)
│
├── core/                 # Agent execution engine
│   ├── runner.py          #   Agent execution logic
│   ├── runner_adapter.py  #   Runner adaptation layer
│   ├── policy_engine.py   #   Safety guardrails
│   ├── prompt_composer.py #   Dynamic prompt composition
│   ├── circuit_breaker.py #   Three-state failure recovery (CLOSED/OPEN/HALF_OPEN)
│   ├── model_callbacks.py #   Cost/token tracking, budget enforcement
│   ├── context_compactor.py # Context window management
│   ├── summarizer.py     #   Response summarization
│   └── approval.py       #   Human approval workflow
│
├── council/              # Parallel Council of Experts architecture
│   ├── orchestrator.py    #   CouncilOrchestrator (BaseAgent subclass)
│   ├── parallel_council.py#   Standard mode: ParallelAgent → Synthesizer
│   ├── debate.py          #   Debate mode: LoopAgent for critic feedback
│   ├── panels.py          #   5 specialist panel factories (trace, metrics, logs, alerts, data)
│   ├── synthesizer.py     #   Unified assessment from all panels
│   ├── critic.py          #   Cross-examination of panel findings
│   ├── intent_classifier.py # Rule-based investigation mode selection
│   ├── mode_router.py    #   @adk_tool wrapper for intent classification
│   ├── tool_registry.py   #   Single source of truth for all domain tool sets (OPT-4)
│   ├── schemas.py         #   InvestigationMode, PanelFinding, CriticReport, CouncilResult
│   └── prompts.py         #   Panel, critic, synthesizer prompts
│
├── sub_agents/           # Specialist sub-agents
│   ├── trace.py           #   Distributed trace analysis
│   ├── logs.py            #   Log pattern analysis (Drain3)
│   ├── metrics.py         #   Metrics anomaly detection
│   ├── alerts.py          #   Alert investigation
│   ├── root_cause.py     #   Multi-signal synthesis for RCA
│   └── agent_debugger.py #   Agent execution debugging and inspection
│
├── tools/                # Tool ecosystem (158+ files)
│   ├── common/            #   Shared utilities (@adk_tool, cache, telemetry, serialization)
│   ├── clients/           #   GCP API clients (singleton factory pattern)
│   ├── analysis/          #   Pure analysis modules
│   │   ├── trace/         #     Trace filtering, comparison, statistics
│   │   ├── logs/          #     Pattern extraction, clustering
│   │   ├── metrics/       #     Anomaly detection, statistics
│   │   ├── slo/           #     SLO burn rate analysis (multi-window)
│   │   ├── correlation/   #     Cross-signal, critical path, dependencies, change correlation
│   │   ├── bigquery/      #     BigQuery-based OTel/log analysis
│   │   └── remediation/   #     Remediation suggestions, postmortem generation
│   ├── mcp/               #   Model Context Protocol (BigQuery SQL, heavy queries)
│   ├── bigquery/          #   BigQuery client, schemas, query builders
│   ├── sandbox/           #   Sandboxed code execution (large data processing)
│   ├── discovery/         #   GCP resource discovery
│   ├── playbooks/         #   Runbook execution (GKE, Cloud Run, SQL, Pub/Sub, GCE, BigQuery)
│   ├── proactive/         #   Proactive signal analysis
│   ├── exploration/       #   Health check exploration
│   ├── synthetic/         #   Synthetic data generation for testing
│   ├── research.py        #   Online research (search_google, fetch_web_page)
│   ├── config.py          #   Tool configuration registry
│   ├── registry.py        #   Tool registration and discovery system
│   ├── memory.py          #   Memory management
│   └── __init__.py        #   Tool exports (add new tools to __all__ here)
│
├── services/             # Business services
│   ├── session.py         #   Session CRUD (ADKSessionManager)
│   ├── storage.py         #   Persistence layer (Firestore/SQLite)
│   ├── agent_engine_client.py # Remote Agent Engine client (dual-mode)
│   └── memory_manager.py #   Memory service management
│
├── memory/               # Memory subsystem (manager, factory, local, callbacks)
├── models/               # Data models (InvestigationPhase, InvestigationState)
└── resources/            # GCP resources catalog (metrics by service)
```

### Frontend (`autosre/`)
```
autosre/lib/
├── main.dart             # App entry point
├── app.dart              # Root widget
├── pages/                # Login, Conversation (main UI), Tool Config, Help
├── services/             # Auth, API client, session, dashboard state, connectivity
├── widgets/              # Reusable UI components
│   ├── canvas/           #   Visualization canvases (agent activity, reasoning, topology, etc.)
│   └── dashboard/        #   Live panels (alerts, council, logs, metrics, remediation, traces)
├── models/               # ADK schema definitions
├── theme/                # Material 3 deep space theme
└── utils/                # Utilities (ANSI parser)
```

### Tests (`tests/`)
```
tests/
├── conftest.py           # Shared fixtures (synthetic OTel data, mock clients)
├── fixtures/             # Synthetic OTel data generator
├── unit/                 # Unit tests — mirrors sre_agent/ structure
├── integration/          # Integration tests (auth, pipeline, persistence, middleware)
├── e2e/                  # End-to-end tests
├── server/               # FastAPI server tests
└── api/                  # API endpoint tests
```

### Other Key Directories
- `eval/` — Agent evaluation framework (ADK AgentEvaluator, test scenarios)
- `deploy/` — Deployment scripts (Agent Engine, Cloud Run, GKE) + k8s manifests
- `docs/` — Comprehensive documentation (architecture, concepts, guides, reference)
- `scripts/` — Development utilities (start_dev.py, analyze_health.py)
- `openspec/` — OpenSpec specifications and change tracking

## Key Architecture Patterns

### Council of Experts (3 modes)
| Mode | Trigger | Behavior |
|------|---------|----------|
| **Fast** | Narrow-scope queries | Single-panel dispatch |
| **Standard** | Normal investigations | 5 parallel panels → Synthesizer merge |
| **Debate** | High-severity incidents | Panels → Critic LoopAgent → Confidence gating |

Feature flags: `SRE_AGENT_COUNCIL_ORCHESTRATOR` (enable council), `SRE_AGENT_SLIM_TOOLS` (default `true`, reduces root to ~20 tools).

### Tool Implementation
```python
from sre_agent.tools.common.decorators import adk_tool

@adk_tool
async def my_tool(arg: str, tool_context: ToolContext | None = None) -> str:
    """Tool description."""
    return json.dumps({"status": "success", "result": {...}})
```

Registration checklist: `tools/__init__.py` exports → `agent.py` base_tools + TOOL_NAME_MAP → `tools/config.py` ToolConfig.

### Pydantic Models
```python
class MySchema(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    field: str
```
**Note**: A Pydantic monkeypatch in `sre_agent/api/app.py` resolves ADK 1.23.0 + Pydantic 2.12+ incompatibility. Do not remove until ADK is updated.

### Client Factory (Singletons)
```python
from sre_agent.tools.clients.factory import get_trace_client
client = get_trace_client(tool_context)  # Thread-safe, respects EUC
```

### Dual-Mode Execution
- **Local** (`SRE_AGENT_ID` not set): Agent runs in-process in FastAPI
- **Remote** (`SRE_AGENT_ID` set): Forwards to Vertex AI Agent Engine

### EUC (End-User Credentials)
Frontend sends `Authorization: Bearer <token>` + `X-GCP-Project-ID` headers. Middleware extracts into ContextVars. Tools access via `get_credentials_from_tool_context()`. `STRICT_EUC_ENFORCEMENT=true` blocks ADC fallback.

### MCP vs Direct API
- **MCP** (`tools/mcp/`): BigQuery SQL, complex aggregations, heavy PromQL
- **Direct** (`tools/clients/`): Single trace/log fetches, real-time metrics, low-latency
- **Fallback**: MCP fails → Direct API (via `tools/mcp/fallback.py`)

### Dashboard Data Channel
Backend emits `{"type": "dashboard", ...}` events via `api/helpers/tool_events.py`. Frontend subscribes via `dashboardStream`, decoupled from chat A2UI protocol.

## Testing Conventions
- **Coverage gate**: 80% minimum, 100% target on new code
- **Async tests**: Use `@pytest.mark.asyncio`
- **Mock external APIs**: `patch`, `AsyncMock`, `MagicMock` — never call real GCP in tests
- **Path mirroring**: `sre_agent/tools/clients/trace.py` → `tests/unit/sre_agent/tools/clients/test_trace.py`
- **Test env**: `GOOGLE_CLOUD_PROJECT=test-project`, `DISABLE_TELEMETRY=true`, `STRICT_EUC_ENFORCEMENT=false`
- **Naming**: `test_<function>_<condition>_<expected>` (e.g., `test_fetch_trace_not_found_returns_error`)
- **MCP mocking**: `USE_MOCK_MCP=true`

## Linting Stack
- **Ruff** (v0.14.14): Formatting + import sorting + linting (rules: E/F/W/I/B/UP/RUF/D, line-length=88)
- **MyPy**: Strict mode, `disallow_untyped_defs=true`, excludes tests/eval/deploy
- **Codespell**: Spelling checker
- **Deptry**: Dependency checker (unused/missing)
- **detect-secrets**: Secret scanning (baseline in `.secrets.baseline`)
- **Flutter analyze**: Dart linter

## Environment Variables (Key)
| Variable | Purpose | Default |
|----------|---------|---------|
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | required |
| `GOOGLE_CLOUD_LOCATION` | GCP region | us-central1 |
| `SRE_AGENT_ID` | Enables remote mode (Agent Engine) | unset = local |
| `SRE_AGENT_COUNCIL_ORCHESTRATOR` | Enables Council architecture | unset |
| `SRE_AGENT_SLIM_TOOLS` | Reduces root agent tools to ~20 | true |
| `SRE_AGENT_TOKEN_BUDGET` | Max token budget per request | unset |
| `STRICT_EUC_ENFORCEMENT` | Blocks ADC fallback | false |
| `SRE_AGENT_LOCAL_EXECUTION` | Sandbox local mode | false |
| `LOG_LEVEL` | Logging level | INFO |
| `SRE_AGENT_CONTEXT_CACHING` | Enable Vertex AI context caching (OPT-10) | false |
| `USE_MOCK_MCP` | Use mock MCP in tests | false |
| `GOOGLE_CUSTOM_SEARCH_API_KEY` | API key for Google Custom Search (research tools) | unset |
| `GOOGLE_CUSTOM_SEARCH_ENGINE_ID` | Programmable Search Engine ID (research tools) | unset |

See `.env.example` for full list and `docs/reference/configuration.md` for details.

## Key Architecture Pointers
| Pattern | Details in AGENTS.md |
|---------|---------------------|
| Tool decorator (`@adk_tool`) | Section 2 |
| Pydantic schemas (`extra="forbid"`) | Section 1 |
| Client factory (singletons) | Section 4 |
| Session persistence (stale closure) | Section 5 |
| Caching (TTL 300s) | Section 6 |
| Project ID enforcement | Section 7 |
| Mission Control UI (Flutter) | Section 8 |
| MCP vs Direct API | Section 9 |
| Dual-mode execution | Section 10 |
| EUC credential propagation | Section 11 |
| Dashboard data channel | Section 12 |
| Council activity graph events | Section 12.1 |
| Sandbox code execution | Section 13 |

## Adding a New Tool (Checklist)
1. Create function in `sre_agent/tools/` (appropriate subdirectory)
2. Add `@adk_tool` decorator (use `@adk_tool(skip_summarization=True)` for structured data tools)
3. Add docstring with clear description
4. Add to `__all__` in `sre_agent/tools/__init__.py`
5. Add to `base_tools` list in `sre_agent/agent.py`
6. Add to `TOOL_NAME_MAP` in `sre_agent/agent.py`
7. Add `ToolConfig` entry in `sre_agent/tools/config.py`
8. If used by sub-agents/panels: add to relevant tool set in `council/tool_registry.py`
9. Add test in `tests/` (mirror source path)
10. Run `uv run poe lint && uv run poe test`

## Adding a New Sub-Agent (Checklist)
1. Create file in `sre_agent/sub_agents/<name>.py`
2. Define prompt with XML tags (`<role>`, `<tool_strategy>`, `<output_format>`), positive framing
3. Define tool set in `council/tool_registry.py` and import from there
4. Export in `sre_agent/sub_agents/__init__.py`
5. Add to `sub_agents` list in `sre_agent/agent.py`
6. Add test in `tests/`
7. Run `uv run poe lint && uv run poe test`

## Common Pitfalls
- **Missing tool registration**: Check all 4 registration points (exports, base_tools, TOOL_NAME_MAP, ToolConfig)
- **Stale session closure**: Always refresh session from DB inside async generators after `await` calls
- **Pydantic `extra="forbid"` missing**: Causes silent hallucination acceptance
- **Forgetting `await`**: All tool functions are async — `RuntimeWarning: coroutine was never awaited`
- **Import errors**: Run `uv run poe sync` to ensure dependencies are installed
- **GenUI rendering issues**: See `docs/guides/debugging_genui.md`

> [!IMPORTANT]
> **Always refer to [`AGENTS.md`](AGENTS.md) for the single source of truth on coding patterns.**

---
*Last verified: 2026-02-15 — Auto SRE Team*
