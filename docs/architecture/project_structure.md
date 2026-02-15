# Project Structure

This document provides a detailed breakdown of the Auto SRE codebase for developers and AI agents.

## Directory Tree

```text
sre-agent/
├── AGENTS.md                 # Entry point for AI coding agents (SSOT for patterns)
├── CLAUDE.md                 # Claude-specific implementation guide
├── README.md                 # High-level project overview
├── pyproject.toml            # Project dependencies and poe task configuration
├── autosre/                  # Flutter Web Frontend
│   ├── lib/                  # Dart source code
│   │   ├── agent/            # ADK content generator (streaming)
│   │   ├── models/           # ADK schema definitions
│   │   ├── pages/            # Login, Conversation, Tool Config, Help pages
│   │   ├── services/         # Auth, API client, session, dashboard state,
│   │   │                     #   connectivity, explorer query, help, project,
│   │   │                     #   prompt history, tool config, version
│   │   ├── theme/            # Material 3 deep space theme
│   │   ├── utils/            # Utilities (ANSI parser)
│   │   ├── widgets/          # Reusable UI components
│   │   │   ├── auth/         #   Authentication widgets
│   │   │   ├── canvas/       #   Visualization canvases (agent activity,
│   │   │   │                 #     graph, trace, reasoning, alerts, incident
│   │   │   │                 #     timeline, metrics, service topology)
│   │   │   ├── common/       #   Shared widgets (error banner, shimmer,
│   │   │   │                 #     source badge, explorer empty state)
│   │   │   ├── dashboard/    #   Live panels (alerts, charts, council,
│   │   │   │   │             #     logs, metrics, remediation, traces),
│   │   │   │   │             #     visual data explorer, query language
│   │   │   │   │             #     toggle, BigQuery sidebar, SQL results,
│   │   │   │   │             #     manual query bar, autocomplete overlay
│   │   │   │   └── cards/    #   Dashboard card components
│   │   │   └── help/         #   Help center widgets
│   │   ├── app.dart          # Root widget (MultiProvider)
│   │   └── main.dart         # App entry point
│   └── analysis_options.yaml # Linting rules for Dart
├── deploy/                   # Orchestration scripts for Vertex AI & Cloud Run
│   ├── deploy.py             # Agent Engine deployment
│   ├── deploy_web.py         # Cloud Run deployment
│   ├── deploy_all.py         # Full stack deployment
│   ├── deploy_gke.py         # GKE deployment
│   ├── grant_permissions.py  # IAM setup script
│   ├── get_id.py             # Get deployed agent ID
│   ├── run_eval.py           # Run evaluations on deployed agents
│   ├── setup_ca_agent.py     # Cloud Agent setup
│   ├── setup_agent_identity_iam.sh  # Agent identity IAM setup
│   ├── verify_agent_identity.py     # Verify agent identity configuration
│   ├── Dockerfile.unified    # Unified Docker image
│   └── k8s/                  # Kubernetes manifests (deployment, service)
├── docs/                     # Documentation (Architecture, Guides, Reference)
├── eval/                     # Evaluation harness and test cases
├── openspec/                 # OpenSpec specifications and change tracking
├── sre_agent/                # Core Python Backend
│   ├── agent.py              # Root SRE Agent, orchestration tools, tool registry
│   ├── auth.py               # Authentication, EUC, token encryption, ContextVars
│   ├── prompt.py             # Agent personality and system instructions
│   ├── schema.py             # Pydantic models for structured output
│   ├── model_config.py       # Model configuration (get_model_name), context caching
│   ├── suggestions.py        # Follow-up suggestion generation
│   │
│   ├── api/                  # FastAPI application layer
│   │   ├── app.py            #   Factory (create_app), Pydantic monkeypatch
│   │   ├── middleware.py     #   Auth + tracing + CORS middleware
│   │   ├── dependencies.py   #   Dependency injection (session, tool context)
│   │   ├── routers/          #   HTTP handlers
│   │   │   ├── agent.py      #     Main chat and orchestration
│   │   │   ├── sessions.py   #     Conversation history CRUD
│   │   │   ├── tools.py      #     Tool config, testing, query/exploration endpoints
│   │   │   ├── system.py     #     Auth, config, version, suggestions
│   │   │   ├── health.py     #     Health checks
│   │   │   ├── help.py       #     Help center content
│   │   │   ├── permissions.py #    IAM permissions
│   │   │   └── preferences.py #    User preferences
│   │   └── helpers/          #   Tool event streaming (emit_dashboard_event)
│   │
│   ├── core/                 # Agent execution engine
│   │   ├── runner.py         #   Agent execution logic
│   │   ├── runner_adapter.py #   Runner adaptation layer
│   │   ├── router.py         #   3-tier request routing (DIRECT/SUB_AGENT/COUNCIL)
│   │   ├── policy_engine.py  #   Safety guardrails
│   │   ├── prompt_composer.py #  Dynamic prompt composition
│   │   ├── circuit_breaker.py # Three-state failure recovery (CLOSED/OPEN/HALF_OPEN)
│   │   ├── model_callbacks.py # Cost/token tracking, budget enforcement
│   │   ├── context_compactor.py # Context window management
│   │   ├── summarizer.py    #   Response summarization
│   │   ├── approval.py      #   Human approval workflow
│   │   ├── tool_callbacks.py #   Tool output truncation and post-processing
│   │   ├── large_payload_handler.py # Oversized result sandbox offload
│   │   └── graph_service.py  #   Service dependency graph construction
│   │
│   ├── council/              # Parallel Council of Experts architecture
│   │   ├── orchestrator.py   #   CouncilOrchestrator (BaseAgent subclass)
│   │   ├── adaptive_classifier.py # LLM-augmented intent classification
│   │   ├── parallel_council.py #  Standard mode: ParallelAgent -> Synthesizer
│   │   ├── debate.py         #   Debate mode: LoopAgent for critic feedback
│   │   ├── panels.py         #   5 specialist panel factories
│   │   ├── synthesizer.py    #   Unified assessment from all panels
│   │   ├── critic.py         #   Cross-examination of panel findings
│   │   ├── intent_classifier.py # Rule-based investigation mode selection
│   │   ├── mode_router.py    #   @adk_tool wrapper for intent classification
│   │   ├── tool_registry.py  #   Single source of truth for all domain tool sets
│   │   ├── schemas.py        #   InvestigationMode, PanelFinding, CouncilResult, etc.
│   │   └── prompts.py        #   Panel, critic, synthesizer prompts
│   │
│   ├── sub_agents/           # Specialist sub-agents
│   │   ├── trace.py          #   Trace analysis (aggregate_analyzer + trace_analyst)
│   │   ├── logs.py           #   Log pattern analysis (Drain3)
│   │   ├── metrics.py        #   Metrics anomaly detection
│   │   ├── alerts.py         #   Alert investigation
│   │   ├── root_cause.py     #   Multi-signal synthesis for RCA
│   │   └── agent_debugger.py #   Agent execution debugging and inspection
│   │
│   ├── tools/                # Tool ecosystem (100+ tools)
│   │   ├── __init__.py       #   Tool exports (add new tools to __all__ here)
│   │   ├── config.py         #   Tool configuration registry
│   │   ├── registry.py       #   Tool registration and discovery system
│   │   ├── investigation.py  #   Investigation state management tools
│   │   ├── memory.py         #   Memory management tools
│   │   ├── reporting.py      #   Report synthesis tools
│   │   ├── research.py       #   Online research (search_google, fetch_web_page)
│   │   ├── test_functions.py #   Tool testing helpers
│   │   ├── common/           #   Shared utilities (@adk_tool, cache, telemetry,
│   │   │                     #     serialization, time, debug)
│   │   ├── clients/          #   GCP API clients (singleton factory pattern)
│   │   │                     #     trace, logging, monitoring, gke, resource_manager,
│   │   │                     #     error_reporting
│   │   ├── analysis/         #   Pure analysis modules
│   │   │   ├── trace/        #     Trace filtering, comparison, statistics,
│   │   │   │                 #       critical path, bottleneck, patterns, SRE patterns
│   │   │   ├── logs/         #     Pattern extraction, clustering, anomaly
│   │   │   ├── metrics/      #     Anomaly detection, statistics, trends, comparison
│   │   │   ├── slo/          #     SLO burn rate, budget, status, prediction
│   │   │   ├── correlation/  #     Cross-signal, critical path, dependencies,
│   │   │   │                 #       change correlation, causal analysis, impact
│   │   │   ├── bigquery/     #     BigQuery-based OTel/log analysis
│   │   │   ├── agent_trace/  #     Agent self-analysis trace tools
│   │   │   └── remediation/  #     Remediation suggestions, postmortem, gcloud commands
│   │   ├── mcp/              #   Model Context Protocol (BigQuery SQL, heavy queries)
│   │   ├── bigquery/         #   BigQuery client, schemas, query builders,
│   │   │                     #     exemplars, selection, CA data agent
│   │   ├── sandbox/          #   Sandboxed code execution (large data processing)
│   │   ├── discovery/        #   GCP resource discovery
│   │   ├── github/           #   GitHub integration (read, search, PR creation)
│   │   ├── playbooks/        #   Runbook execution (GKE, Cloud Run, SQL,
│   │   │                     #     Pub/Sub, GCE, BigQuery, self-healing)
│   │   ├── proactive/        #   Proactive signal analysis
│   │   ├── exploration/      #   Health check exploration
│   │   └── synthetic/        #   Synthetic data generation for testing
│   │
│   ├── services/             # Business services
│   │   ├── session.py        #   Session CRUD (ADKSessionManager)
│   │   ├── storage.py        #   Persistence layer (Firestore/SQLite)
│   │   ├── agent_engine_client.py # Remote Agent Engine client (dual-mode)
│   │   └── memory_manager.py #   Memory service management
│   │
│   ├── memory/               # Memory subsystem
│   │   ├── manager.py        #   Memory manager
│   │   ├── factory.py        #   Memory manager factory
│   │   ├── local.py          #   Local memory store
│   │   ├── callbacks.py      #   ADK memory callbacks (before/after tool, agent)
│   │   ├── mistake_advisor.py #  Mistake pattern advisor
│   │   ├── mistake_learner.py #  Mistake pattern learner
│   │   ├── mistake_store.py  #   Mistake pattern persistence
│   │   └── sanitizer.py      #   Memory content sanitizer
│   │
│   ├── models/               # Data models (InvestigationPhase, InvestigationState)
│   └── resources/            # GCP resources catalog (metrics by service)
│
├── tests/                    # Comprehensive test suite
│   ├── conftest.py           # Shared fixtures (synthetic OTel data, mock clients)
│   ├── fixtures/             # Synthetic OTel data generator
│   ├── unit/                 # Unit tests (mirrors sre_agent/ structure)
│   │   ├── sre_agent/        #   Backend unit tests
│   │   │   ├── api/          #     API and router tests
│   │   │   ├── core/         #     Core engine tests
│   │   │   ├── council/      #     Council architecture tests
│   │   │   ├── memory/       #     Memory subsystem tests
│   │   │   ├── models/       #     Model tests
│   │   │   ├── services/     #     Service tests
│   │   │   ├── sub_agents/   #     Sub-agent tests
│   │   │   └── tools/        #     Tool tests (analysis, clients, common, etc.)
│   │   └── deploy/           #   Deployment script tests
│   ├── integration/          # Integration tests (auth, pipeline, persistence)
│   ├── e2e/                  # End-to-end tests
│   ├── server/               # FastAPI server tests
│   ├── api/                  # API endpoint tests
│   └── sre_agent/            # Additional agent-level tests (api, core)
└── scripts/                  # Utilities for development and CI
```

## Core Modules

### `sre_agent/agent.py`
The central brain of the system. It defines the `sre_agent` (root `LlmAgent`) and registers all available tools in `TOOL_NAME_MAP` (~103 tools). Manages delegation to 7 sub-agents. Provides orchestration tools (`run_aggregate_analysis`, `run_triage_analysis`, `run_deep_dive_analysis`, `run_log_pattern_analysis`, `run_council_investigation`). Supports two tool modes: slim (~35 tools, default) and full (~90+ tools, `SRE_AGENT_SLIM_TOOLS=false`).

### `sre_agent/core/router.py`
Implements the **3-Tier Request Router** exposed as an `@adk_tool`. Classifies user queries into DIRECT (simple data retrieval), SUB_AGENT (specialist delegation), or COUNCIL (parallel investigation) tiers using the rule-based `classify_routing()` function from `council/intent_classifier.py`. Called as the first step of every user turn.

### `sre_agent/council/orchestrator.py`
The `CouncilOrchestrator` (`BaseAgent` subclass) replaces the root `LlmAgent` when `SRE_AGENT_COUNCIL_ORCHESTRATOR=true`. Pure routing logic (no LLM) -- classifies intent and delegates to the appropriate pipeline (fast/standard/debate). Supports adaptive classification via LLM augmentation (`SRE_AGENT_ADAPTIVE_CLASSIFIER=true`).

### `sre_agent/council/tool_registry.py`
**Single source of truth** for all domain-specific tool sets. Both council panels and sub-agents import from this registry to prevent tool set drift. Defines tool sets for each domain (trace, metrics, logs, alerts, data) plus shared cross-cutting tools (state, remediation, research, GitHub).

### `sre_agent/core/large_payload_handler.py`
Intercepts oversized tool outputs in the `after_tool_callback` chain. Auto-summarizes results via sandbox processing before they consume context window space. Falls back to code-generation prompts for unknown data shapes.

### `sre_agent/auth.py`
The "Auth Highway". Handles extraction of OAuth tokens from request headers, AES-256 encryption of tokens at rest, OIDC ID token validation, and propagation of user context to downstream tools via ContextVars.

### `sre_agent/tools/research.py`
Online research tools (`search_google`, `fetch_web_page`) that augment the agent's knowledge during investigations. Search results are automatically persisted to memory for future reference. Requires `GOOGLE_CUSTOM_SEARCH_API_KEY` and `GOOGLE_CUSTOM_SEARCH_ENGINE_ID`.

### `sre_agent/tools/github/`
GitHub self-healing tools (`github_read_file`, `github_search_code`, `github_list_recent_commits`, `github_create_pull_request`) that enable the agent to read source code, search for relevant code patterns, and create pull requests for automated remediation.

### `autosre/lib/agent/adk_content_generator.dart`
The ADK content generator that handles low-level HTTP streaming and transforms the NDJSON stream into a high-level conversation model. Provides a dedicated `dashboardStream` for the investigation dashboard, decoupled from the chat protocol.

### `autosre/lib/widgets/dashboard/`
The Investigation Dashboard subsystem, including the **Visual Data Explorer** (`visual_data_explorer.dart`) with structured query endpoints, query language toggle, autocomplete overlay, BigQuery sidebar, and SQL results table. Supports both structured queries and natural language query translation.
