# Project Structure

This document provides a detailed breakdown of the Auto SRE codebase for developers and AI agents.

## Directory Tree

```text
sre-agent/
├── AGENTS.md                 # Entry point for AI coding agents
├── CLAUDE.md                 # Claude-specific implementation guide
├── README.md                 # High-level project overview
├── pyproject.toml            # Project dependencies and poe task configuration
├── autosre/                  # Flutter Web Frontend
│   ├── lib/                  # Dart source code
│   │   ├── services/         # API and Auth services
│   │   ├── widgets/          # GenUI components and UI widgets
│   │   └── main.dart         # App entry point
│   └── analysis_options.yaml # Linting rules for Dart
├── deploy/                   # Orchestration scripts for Vertex AI & Cloud Run
│   ├── deploy.py             # Agent Engine deployment
│   ├── deploy_web.py         # Cloud Run deployment
│   └── grant_permissions.py  # IAM setup script
├── docs/                     # Documentation (Architecture, Guides, Reference)
├── eval/                     # Evaluation harness and test cases
├── sre_agent/                # Core Python Backend
│   ├── agent.py              # Root SRE Agent & Orchestration logic
│   ├── auth.py               # Authentication and EUC handling
│   ├── prompt.py             # Agent personality and system instructions
│   ├── schema.py             # Pydantic models for structured output
│   ├── core/                 # Autonomous reliability (Runner, Policy Engine)
│   ├── sub_agents/           # Specialist agents (Trace, Logs, Metrics)
│   ├── tools/                # Tool implementations
│   │   ├── analysis/         # Statistical processing and data transformations
│   │   ├── clients/          # Direct GCP API clients
│   │   ├── common/           # Telemetry, cache, and shared utilities
│   │   └── mcp/              # Model Context Protocol implementations
│   ├── memory/               # Memory subsystem
│   │   ├── manager.py        # MemoryManager (Vertex AI / Local dual-backend)
│   │   ├── factory.py        # Singleton factories (get_memory_manager, etc.)
│   │   ├── local.py          # LocalMemoryService (SQLite fallback)
│   │   ├── callbacks.py      # Auto-learning callbacks (before/after/error)
│   │   ├── mistake_store.py  # Persistent mistake store (MemoryManager-backed)
│   │   ├── mistake_learner.py # Mistake capture & self-correction detection
│   │   └── mistake_advisor.py # Pre-tool advice & prompt lesson injection
│   └── services/             # Session and storage services
├── tests/                    # Comprehensive test suite
│   ├── unit/                 # Isolated logic tests
│   ├── integration/          # Service interaction tests
│   └── server/               # API and routing tests
└── scripts/                  # Utilities for development and CI
```

## Core Modules

### `sre_agent/agent.py`
The central brain of the system. It defines the `root_agent` and manages the delegation to sub-agents. It also serves as the registry for all available tools and their metadata.

### `sre_agent/core/runner.py`
Implements the **Stateful, Event-Driven Harness**. It manages the "Unrolled Codex" loop, reconstructing agent state from event history every turn to support zero-downtime restarts.

### `sre_agent/auth.py`
The "Auth Highway". It handles the extraction of OAuth tokens from request headers, encryption of tokens at rest, and propagation of user context to downstream tools.

### `autosre/lib/widgets/genui/`
Contains the implementation of the **Generative UI** protocol. This layer translates backend `ui_event` payloads into interactive Flutter widgets like waterfall traces and log clusters.
